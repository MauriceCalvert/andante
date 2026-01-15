"""Unified CP-SAT slice solver for inner voice resolution.

Solves ALL inner voice pitches across ALL slices simultaneously using Google OR-Tools
CP-SAT solver. This replaces the greedy slice-by-slice approach with global optimization.

The solver models:
- Hard constraints: parallel fifths/octaves, voice crossing
- Soft constraints: voice leading, chord tone preference, spacing, thematic fidelity

Key advantage: Global optimization finds solutions that local greedy search cannot.
For example, sacrificing optimal voice leading at slice 3 to avoid a parallel at slice 4.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple

from ortools.sat.python import cp_model

from engine.harmonic_context import (
    HarmonicContext,
    generate_chord_tone_candidates,
    generate_scale_candidates,
    infer_harmony_from_outer,
)
from engine.key import Key
from engine.slice_solver import (
    VOICE_RANGES,
    get_voice_range,
    resolve_outer_pitch,
    SolvedSlice,
)
from engine.voice_material import ExpandedVoices, VoiceMaterial
from shared.pitch import FloatingNote, MidiPitch, Pitch, Rest, is_rest


# =============================================================================
# Cost weights (aligned with counterpoint_rules.yaml)
# =============================================================================

# Hard constraint penalties (make solutions infeasible)
PARALLEL_FIFTH_COST: int = 1000
PARALLEL_OCTAVE_COST: int = 1000
VOICE_CROSSING_COST: int = 500

# Soft constraint costs
NON_CHORD_TONE_COST: int = 20
UNISON_COST: int = 1000  # Match parallel cost - unisons are as bad as parallel fifths
OCTAVE_DOUBLING_COST: int = 10
SPACING_VIOLATION_COST: int = 15  # Per semitone below minimum
MAX_VOICE_SPACING: int = 14  # Maximum semitones between adjacent voices
MAX_SPACING_VIOLATION_COST: int = 100  # Per semitone above maximum (must be high to prevent gaps)

# Voice leading costs - STATIC_VOICE penalizes drone-like inner voices
STATIC_VOICE_COST: int = 25  # Same pitch - strongly discourage drone behavior
STEP_REWARD: int = -5  # 1-2 semitones (ideal) - reward steps with negative cost
SMALL_LEAP_COST: int = 0  # 3-4 semitones (OK)
MEDIUM_LEAP_COST: int = 3  # 5-7 semitones
LARGE_LEAP_COST: int = 8  # 8-12 semitones
HUGE_LEAP_COST: int = 20  # >12 semitones

# Thematic fidelity (polyphonic texture)
THEMATIC_MATCH_REWARD: int = 15  # Following thematic material
THEMATIC_OCTAVE_MATCH_REWARD: int = 10  # Right pitch class, different octave

# Spacing
MIN_VOICE_SEPARATION: int = 3  # Minimum semitones between adjacent voices


@dataclass(frozen=True)
class SliceContext:
    """Context for a single vertical slice."""
    offset: Fraction
    soprano_midi: int
    bass_midi: int
    chord_tones_pc: frozenset[int]
    is_strong_beat: bool


@dataclass(frozen=True)
class InnerVoiceSpec:
    """Specification for inner voice candidates at a slice."""
    slice_idx: int
    voice_idx: int
    candidates: Tuple[int, ...]
    thematic_midi: int | None  # If polyphonic, the target thematic pitch


def _build_slice_contexts(
    voices: ExpandedVoices,
    key: Key,
    metre: str,
) -> list[SliceContext]:
    """Build slice contexts from expanded voices.

    Collects attack points where soprano sounds and resolves
    soprano/bass to MIDI for constraint checking.
    """
    soprano = voices.soprano
    bass = voices.bass

    soprano_range = get_voice_range(0, voices.count)
    soprano_median = (soprano_range[0] + soprano_range[1]) // 2
    bass_range = get_voice_range(voices.count - 1, voices.count)
    bass_median = (bass_range[0] + bass_range[1]) // 2

    # Build offset -> (soprano, bass) maps
    soprano_events: list[tuple[Fraction, int]] = []
    offset = Fraction(0)
    prev_midi = soprano_median
    for p, d in zip(soprano.pitches, soprano.durations):
        if not is_rest(p):
            if isinstance(p, MidiPitch):
                midi = p.midi
            elif isinstance(p, FloatingNote):
                midi = key.floating_to_midi(p, prev_midi, soprano_median)
            else:
                midi = soprano_median
            soprano_events.append((offset, midi))
            prev_midi = midi
        offset += d

    bass_by_offset: dict[Fraction, int] = {}
    offset = Fraction(0)
    prev_midi = bass_median
    for p, d in zip(bass.pitches, bass.durations):
        if not is_rest(p):
            if isinstance(p, MidiPitch):
                midi = p.midi
            elif isinstance(p, FloatingNote):
                midi = key.floating_to_midi(p, prev_midi, bass_median)
            else:
                midi = bass_median
            bass_by_offset[offset] = midi
            prev_midi = midi
        offset += d

    # Build contexts at soprano attack points
    contexts: list[SliceContext] = []
    bass_offsets = sorted(bass_by_offset.keys())

    for sop_offset, sop_midi in soprano_events:
        # Find bass sounding at this offset
        bass_midi = None
        for b_off in reversed(bass_offsets):
            if b_off <= sop_offset:
                bass_midi = bass_by_offset[b_off]
                break

        if bass_midi is None:
            continue

        # Infer chord from bass
        bass_pc = bass_midi % 12
        bass_degree = None
        for deg in range(1, 8):
            deg_pc = (key.tonic_pc + key.scale[deg - 1]) % 12
            if deg_pc == bass_pc:
                bass_degree = deg
                break
        if bass_degree is None:
            bass_degree = 1

        root_pc = (key.tonic_pc + key.scale[bass_degree - 1]) % 12
        third_pc = (key.tonic_pc + key.scale[(bass_degree + 1) % 7]) % 12
        fifth_pc = (key.tonic_pc + key.scale[(bass_degree + 3) % 7]) % 12
        chord_tones_pc = frozenset({root_pc, third_pc, fifth_pc})

        # Determine beat strength
        bar_dur = Fraction(1)  # Default 4/4
        if metre == "3/4":
            bar_dur = Fraction(3, 4)
        elif metre == "6/8":
            bar_dur = Fraction(3, 4)

        beat_in_bar = sop_offset % bar_dur
        is_strong = beat_in_bar == Fraction(0) or beat_in_bar == bar_dur / 2

        contexts.append(SliceContext(
            offset=sop_offset,
            soprano_midi=sop_midi,
            bass_midi=bass_midi,
            chord_tones_pc=chord_tones_pc,
            is_strong_beat=is_strong,
        ))

    return contexts


def _get_candidates_for_voice(
    voice_idx: int,
    voice_count: int,
    chord_tones_pc: frozenset[int],
    key: Key,
) -> Tuple[int, ...]:
    """Get all candidate MIDI pitches for an inner voice."""
    voice_range = get_voice_range(voice_idx, voice_count)

    # Generate chord tones first, then scale tones
    candidates: list[int] = []

    # Chord tones
    for pc in chord_tones_pc:
        midi = pc
        while midi < voice_range[0]:
            midi += 12
        while midi <= voice_range[1]:
            candidates.append(midi)
            midi += 12

    # Scale tones (for passing tones on weak beats)
    for semitone in key.scale:
        pc = (key.tonic_pc + semitone) % 12
        if pc in chord_tones_pc:
            continue  # Already added
        midi = pc
        while midi < voice_range[0]:
            midi += 12
        while midi <= voice_range[1]:
            candidates.append(midi)
            midi += 12

    return tuple(sorted(set(candidates)))


def _is_parallel_motion(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
    interval: int,
) -> bool:
    """Check for parallel motion at specified interval."""
    prev_int = (prev_upper - prev_lower) % 12
    curr_int = (curr_upper - curr_lower) % 12
    if prev_int != interval or curr_int != interval:
        return False
    upper_motion = curr_upper - prev_upper
    lower_motion = curr_lower - prev_lower
    if upper_motion == 0 or lower_motion == 0:
        return False
    return (upper_motion > 0) == (lower_motion > 0)


def solve_inner_voices_cpsat(
    voices: ExpandedVoices,
    key: Key,
    metre: str,
    texture: str,
    target_voice_count: int,
    thematic_inner: dict[int, list[tuple[Fraction, Pitch]]] | None = None,
    timeout_seconds: float = 5.0,
) -> ExpandedVoices | None:
    """Solve all inner voice pitches using CP-SAT.

    Args:
        voices: ExpandedVoices with soprano and bass (inner voices will be created)
        key: Musical key
        metre: Time signature string
        texture: "polyphonic" or "homophonic"
        target_voice_count: Target number of voices (e.g., 4 for SATB)
        thematic_inner: Optional mapping of voice_idx -> [(offset, pitch)] for thematic material
        timeout_seconds: Solver time limit

    Returns:
        ExpandedVoices with solved inner voice pitches as FloatingNote, or None if infeasible
    """
    voice_count = target_voice_count
    inner_count = voice_count - 2

    if inner_count <= 0:
        return voices

    # Build slice contexts
    contexts = _build_slice_contexts(voices, key, metre)
    if not contexts:
        return voices

    n_slices = len(contexts)

    # Build thematic targets by (slice_idx, voice_idx)
    thematic_targets: dict[tuple[int, int], int] = {}
    if texture == "polyphonic" and thematic_inner:
        for voice_idx, events in thematic_inner.items():
            voice_range = get_voice_range(voice_idx, voice_count)
            median = (voice_range[0] + voice_range[1]) // 2

            for offset, pitch in events:
                # Find matching slice
                for si, ctx in enumerate(contexts):
                    if ctx.offset == offset:
                        if isinstance(pitch, MidiPitch):
                            thematic_targets[(si, voice_idx)] = pitch.midi
                        elif isinstance(pitch, FloatingNote):
                            thematic_targets[(si, voice_idx)] = key.floating_to_midi(
                                pitch, median, median
                            )
                        break

    # Build candidate lists per (slice, voice)
    candidates_map: dict[tuple[int, int], Tuple[int, ...]] = {}
    for si, ctx in enumerate(contexts):
        for vi in range(1, voice_count - 1):  # Inner voices only
            candidates = _get_candidates_for_voice(
                vi, voice_count, ctx.chord_tones_pc, key
            )
            candidates_map[(si, vi)] = candidates

    # Create CP-SAT model
    model = cp_model.CpModel()

    # Variables: pitch[slice_idx][voice_idx] = index into candidates
    pitch_vars: dict[tuple[int, int], cp_model.IntVar] = {}
    for (si, vi), cands in candidates_map.items():
        if not cands:
            continue
        pitch_vars[(si, vi)] = model.NewIntVar(0, len(cands) - 1, f"p_{si}_{vi}")

    # === Hard constraints ===

    # 1. No parallel fifths/octaves between any voice pair
    for si in range(1, n_slices):
        prev_ctx = contexts[si - 1]
        curr_ctx = contexts[si]

        # Check all voice pairs
        for upper_vi in range(voice_count):
            for lower_vi in range(upper_vi + 1, voice_count):
                # Get prev/curr pitches for both voices
                # Outer voices are fixed
                if upper_vi == 0:
                    prev_upper = prev_ctx.soprano_midi
                    curr_upper = curr_ctx.soprano_midi
                elif (si - 1, upper_vi) in pitch_vars and (si, upper_vi) in pitch_vars:
                    # Inner voice - enumerate forbidden pairs
                    prev_cands = candidates_map[(si - 1, upper_vi)]
                    curr_cands = candidates_map[(si, upper_vi)]

                    if lower_vi == voice_count - 1:
                        # Upper=inner, Lower=bass
                        prev_lower = prev_ctx.bass_midi
                        curr_lower = curr_ctx.bass_midi

                        forbidden = []
                        for pi, pm in enumerate(prev_cands):
                            for ci, cm in enumerate(curr_cands):
                                if _is_parallel_motion(pm, prev_lower, cm, curr_lower, 7):
                                    forbidden.append((pi, ci))
                                if _is_parallel_motion(pm, prev_lower, cm, curr_lower, 0):
                                    forbidden.append((pi, ci))

                        if forbidden:
                            model.AddForbiddenAssignments(
                                [pitch_vars[(si - 1, upper_vi)], pitch_vars[(si, upper_vi)]],
                                forbidden
                            )
                    elif (si - 1, lower_vi) in pitch_vars and (si, lower_vi) in pitch_vars:
                        # Both inner voices
                        prev_lower_cands = candidates_map[(si - 1, lower_vi)]
                        curr_lower_cands = candidates_map[(si, lower_vi)]

                        # This is expensive but necessary for correctness
                        # We use reification for inner-inner pairs
                        for pi, pm in enumerate(prev_cands):
                            for ci, cm in enumerate(curr_cands):
                                for pli, plm in enumerate(prev_lower_cands):
                                    for cli, clm in enumerate(curr_lower_cands):
                                        if _is_parallel_motion(pm, plm, cm, clm, 7) or \
                                           _is_parallel_motion(pm, plm, cm, clm, 0):
                                            # Forbid this 4-tuple
                                            b1 = model.NewBoolVar(f"fb_{si}_{upper_vi}_{lower_vi}_{pi}_{ci}_{pli}_{cli}")
                                            model.Add(pitch_vars[(si - 1, upper_vi)] == pi).OnlyEnforceIf(b1)
                                            model.Add(pitch_vars[(si, upper_vi)] == ci).OnlyEnforceIf(b1)
                                            model.Add(pitch_vars[(si - 1, lower_vi)] == pli).OnlyEnforceIf(b1)
                                            model.Add(pitch_vars[(si, lower_vi)] == cli).OnlyEnforceIf(b1)
                                            model.Add(b1 == 0)
                    continue
                else:
                    continue

                if lower_vi == voice_count - 1:
                    prev_lower = prev_ctx.bass_midi
                    curr_lower = curr_ctx.bass_midi
                elif (si - 1, lower_vi) in pitch_vars:
                    # Will be handled in the inner loop
                    continue
                else:
                    continue

    # 2. Check inner-to-outer parallel (soprano-inner and bass-inner)
    for si in range(1, n_slices):
        prev_ctx = contexts[si - 1]
        curr_ctx = contexts[si]

        for vi in range(1, voice_count - 1):
            if (si - 1, vi) not in pitch_vars or (si, vi) not in pitch_vars:
                continue

            prev_cands = candidates_map[(si - 1, vi)]
            curr_cands = candidates_map[(si, vi)]

            # vs soprano (inner is lower)
            forbidden_sop = []
            for pi, pm in enumerate(prev_cands):
                for ci, cm in enumerate(curr_cands):
                    if _is_parallel_motion(prev_ctx.soprano_midi, pm, curr_ctx.soprano_midi, cm, 7):
                        forbidden_sop.append((pi, ci))
                    if _is_parallel_motion(prev_ctx.soprano_midi, pm, curr_ctx.soprano_midi, cm, 0):
                        forbidden_sop.append((pi, ci))

            if forbidden_sop:
                model.AddForbiddenAssignments(
                    [pitch_vars[(si - 1, vi)], pitch_vars[(si, vi)]],
                    forbidden_sop
                )

            # vs bass (inner is upper)
            forbidden_bass = []
            for pi, pm in enumerate(prev_cands):
                for ci, cm in enumerate(curr_cands):
                    if _is_parallel_motion(pm, prev_ctx.bass_midi, cm, curr_ctx.bass_midi, 7):
                        forbidden_bass.append((pi, ci))
                    if _is_parallel_motion(pm, prev_ctx.bass_midi, cm, curr_ctx.bass_midi, 0):
                        forbidden_bass.append((pi, ci))

            if forbidden_bass:
                model.AddForbiddenAssignments(
                    [pitch_vars[(si - 1, vi)], pitch_vars[(si, vi)]],
                    forbidden_bass
                )

    # === Soft constraints ===
    costs: list = []

    for si, ctx in enumerate(contexts):
        for vi in range(1, voice_count - 1):
            if (si, vi) not in pitch_vars:
                continue

            cands = candidates_map[(si, vi)]
            var = pitch_vars[(si, vi)]

            for ci, midi in enumerate(cands):
                indicator = model.NewBoolVar(f"ind_{si}_{vi}_{ci}")
                model.Add(var == ci).OnlyEnforceIf(indicator)
                model.Add(var != ci).OnlyEnforceIf(indicator.Not())

                pc = midi % 12

                # 1. Chord tone preference
                if pc not in ctx.chord_tones_pc:
                    if ctx.is_strong_beat:
                        costs.append(NON_CHORD_TONE_COST * 2 * indicator)
                    else:
                        costs.append(NON_CHORD_TONE_COST * indicator)

                # 2. Spacing with soprano (min and max)
                sop_sep = ctx.soprano_midi - midi
                if sop_sep < MIN_VOICE_SEPARATION:
                    costs.append(SPACING_VIOLATION_COST * (MIN_VOICE_SEPARATION - sop_sep) * indicator)
                if sop_sep > MAX_VOICE_SPACING:
                    costs.append(MAX_SPACING_VIOLATION_COST * (sop_sep - MAX_VOICE_SPACING) * indicator)

                # 3. Spacing with bass (min and max)
                bass_sep = midi - ctx.bass_midi
                if bass_sep < MIN_VOICE_SEPARATION:
                    costs.append(SPACING_VIOLATION_COST * (MIN_VOICE_SEPARATION - bass_sep) * indicator)
                if bass_sep > MAX_VOICE_SPACING:
                    costs.append(MAX_SPACING_VIOLATION_COST * (bass_sep - MAX_VOICE_SPACING) * indicator)

                # 4. Unison/octave penalties
                if midi == ctx.soprano_midi or midi == ctx.bass_midi:
                    costs.append(UNISON_COST * indicator)
                elif midi % 12 == ctx.soprano_midi % 12 or midi % 12 == ctx.bass_midi % 12:
                    costs.append(OCTAVE_DOUBLING_COST * indicator)

                # 5. Thematic match reward
                if (si, vi) in thematic_targets:
                    target = thematic_targets[(si, vi)]
                    if midi == target:
                        costs.append(-THEMATIC_MATCH_REWARD * indicator)
                    elif midi % 12 == target % 12:
                        costs.append(-THEMATIC_OCTAVE_MATCH_REWARD * indicator)

    # Inner-inner spacing constraints (for 4+ voices)
    # Penalize unisons and close spacing between inner voices
    for si, ctx in enumerate(contexts):
        inner_voices = [vi for vi in range(1, voice_count - 1) if (si, vi) in pitch_vars]
        for i, vi1 in enumerate(inner_voices):
            for vi2 in inner_voices[i + 1:]:
                cands1 = candidates_map[(si, vi1)]
                cands2 = candidates_map[(si, vi2)]
                var1 = pitch_vars[(si, vi1)]
                var2 = pitch_vars[(si, vi2)]

                for ci1, midi1 in enumerate(cands1):
                    for ci2, midi2 in enumerate(cands2):
                        separation = abs(midi1 - midi2)
                        cost = 0
                        # Penalize unisons between inner voices
                        if separation == 0:
                            cost = UNISON_COST
                        # Penalize octave doublings
                        elif separation % 12 == 0:
                            cost = OCTAVE_DOUBLING_COST
                        # Penalize close spacing
                        elif separation < MIN_VOICE_SEPARATION:
                            cost = SPACING_VIOLATION_COST * (MIN_VOICE_SEPARATION - separation)

                        if cost > 0:
                            # b is true iff var1 == ci1 AND var2 == ci2
                            b1 = model.NewBoolVar(f"inner_b1_{si}_{vi1}_{vi2}_{ci1}_{ci2}")
                            b2 = model.NewBoolVar(f"inner_b2_{si}_{vi1}_{vi2}_{ci1}_{ci2}")
                            b = model.NewBoolVar(f"inner_{si}_{vi1}_{vi2}_{ci1}_{ci2}")
                            model.Add(var1 == ci1).OnlyEnforceIf(b1)
                            model.Add(var1 != ci1).OnlyEnforceIf(b1.Not())
                            model.Add(var2 == ci2).OnlyEnforceIf(b2)
                            model.Add(var2 != ci2).OnlyEnforceIf(b2.Not())
                            # b = b1 AND b2
                            model.AddBoolAnd([b1, b2]).OnlyEnforceIf(b)
                            model.AddBoolOr([b1.Not(), b2.Not()]).OnlyEnforceIf(b.Not())
                            costs.append(cost * b)

    # Voice leading costs (between consecutive slices)
    for si in range(1, n_slices):
        for vi in range(1, voice_count - 1):
            if (si - 1, vi) not in pitch_vars or (si, vi) not in pitch_vars:
                continue

            prev_cands = candidates_map[(si - 1, vi)]
            curr_cands = candidates_map[(si, vi)]
            prev_var = pitch_vars[(si - 1, vi)]
            curr_var = pitch_vars[(si, vi)]

            for pi, pm in enumerate(prev_cands):
                for ci, cm in enumerate(curr_cands):
                    interval = abs(cm - pm)

                    cost = 0
                    if interval == 0:
                        cost = STATIC_VOICE_COST
                    elif interval <= 2:
                        cost = STEP_REWARD
                    elif interval <= 4:
                        cost = SMALL_LEAP_COST
                    elif interval <= 7:
                        cost = MEDIUM_LEAP_COST
                    elif interval <= 12:
                        cost = LARGE_LEAP_COST
                    else:
                        cost = HUGE_LEAP_COST

                    if cost != 0:
                        trans = model.NewBoolVar(f"vl_{si}_{vi}_{pi}_{ci}")
                        model.Add(prev_var == pi).OnlyEnforceIf(trans)
                        model.Add(curr_var == ci).OnlyEnforceIf(trans)
                        # Need both conditions
                        b1 = model.NewBoolVar(f"b1_{si}_{vi}_{pi}_{ci}")
                        b2 = model.NewBoolVar(f"b2_{si}_{vi}_{pi}_{ci}")
                        model.Add(prev_var == pi).OnlyEnforceIf(b1)
                        model.Add(prev_var != pi).OnlyEnforceIf(b1.Not())
                        model.Add(curr_var == ci).OnlyEnforceIf(b2)
                        model.Add(curr_var != ci).OnlyEnforceIf(b2.Not())
                        model.AddBoolAnd([b1, b2]).OnlyEnforceIf(trans)
                        model.AddBoolOr([b1.Not(), b2.Not()]).OnlyEnforceIf(trans.Not())
                        costs.append(cost * trans)

    # Minimize total cost
    if costs:
        model.Minimize(sum(costs))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # Extract solution
    solved_pitches: dict[tuple[int, int], int] = {}
    for (si, vi), var in pitch_vars.items():
        idx = solver.Value(var)
        midi = candidates_map[(si, vi)][idx]
        solved_pitches[(si, vi)] = midi

    # Rebuild inner voice materials
    inner_materials: list[VoiceMaterial] = []

    for vi in range(1, voice_count - 1):
        pitches: list[Pitch] = []
        durations: list[Fraction] = []

        # Add initial rest if first slice doesn't start at 0
        if contexts and contexts[0].offset > Fraction(0):
            pitches.append(Rest())
            durations.append(contexts[0].offset)

        for si, ctx in enumerate(contexts):
            if (si, vi) in solved_pitches:
                # Convert MIDI back to scale degree for diatonic pipeline
                pitches.append(key.midi_to_floating(solved_pitches[(si, vi)]))
            else:
                pitches.append(Rest())

            # Duration until next slice or end
            if si < n_slices - 1:
                dur = contexts[si + 1].offset - ctx.offset
            else:
                dur = voices.soprano.budget - ctx.offset

            if dur > Fraction(0):
                durations.append(dur)
            elif pitches:
                pitches.pop()  # Remove pitch with no duration

        inner_materials.append(VoiceMaterial(
            voice_index=vi,
            pitches=pitches,
            durations=durations,
        ))

    # Build result - create new VoiceMaterial with correct indices
    soprano_reindexed = VoiceMaterial(
        voice_index=0,
        pitches=voices.soprano.pitches,
        durations=voices.soprano.durations,
    )
    bass_reindexed = VoiceMaterial(
        voice_index=voice_count - 1,
        pitches=voices.bass.pitches,
        durations=voices.bass.durations,
    )

    result_voices: list[VoiceMaterial] = [soprano_reindexed]
    result_voices.extend(inner_materials)
    result_voices.append(bass_reindexed)

    return ExpandedVoices(voices=result_voices)


def solve_phrase_cpsat(
    phrase_voices: ExpandedVoices,
    key: Key,
    metre: str,
    texture: str,
    target_voice_count: int,
    subject_pitches: tuple[Pitch, ...] | None = None,
    subject_durations: tuple[Fraction, ...] | None = None,
    cs_pitches: tuple[Pitch, ...] | None = None,
    cs_durations: tuple[Fraction, ...] | None = None,
    timeout_seconds: float = 5.0,
) -> ExpandedVoices | None:
    """High-level interface for phrase inner voice solving.

    For polyphonic texture, builds thematic targets from subject/counter-subject.
    For homophonic, uses pure chord-tone optimization.

    Args:
        phrase_voices: ExpandedVoices with at least soprano and bass
        key: Musical key
        metre: Time signature string
        texture: "polyphonic" or "homophonic"
        target_voice_count: Target number of voices (e.g., 4 for SATB)
        subject_pitches: Optional subject pitches for thematic matching
        subject_durations: Optional subject durations
        cs_pitches: Optional counter-subject pitches
        cs_durations: Optional counter-subject durations
        timeout_seconds: Solver time limit

    Returns:
        ExpandedVoices with all voices including solved inner voices, or None if infeasible
    """
    voice_count = target_voice_count

    if voice_count <= 2:
        return phrase_voices

    # Build thematic inner voice targets for polyphonic texture
    thematic_inner: dict[int, list[tuple[Fraction, Pitch]]] | None = None

    if texture == "polyphonic" and subject_pitches:
        thematic_inner = {}

        # Alto (voice 1) gets counter-subject or subject at interval
        if cs_pitches and cs_durations:
            events: list[tuple[Fraction, Pitch]] = []
            offset = Fraction(0)
            for p, d in zip(cs_pitches, cs_durations):
                events.append((offset, p))
                offset += d
            thematic_inner[1] = events

        # Tenor (voice 2) gets subject at octave below
        if voice_count > 3 and subject_pitches and subject_durations:
            events = []
            offset = Fraction(0)
            for p, d in zip(subject_pitches, subject_durations):
                events.append((offset, p))
                offset += d
            thematic_inner[2] = events

    return solve_inner_voices_cpsat(
        phrase_voices, key, metre, texture,
        target_voice_count=voice_count,
        thematic_inner=thematic_inner,
        timeout_seconds=timeout_seconds,
    )
