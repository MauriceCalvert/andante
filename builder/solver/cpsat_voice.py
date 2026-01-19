"""CP-SAT Voice Generator for full melodic lines.

Generates voices with rhythmic structure matching soprano, optimizing for:
- Consonance with existing voices (hard constraint on strong beats)
- No parallel fifths/octaves (hard constraint)
- Good voice leading (minimize large leaps)
- Chord tone preference (soft constraint)

Uses Google OR-Tools CP-SAT solver for global optimization across the phrase.
"""
from fractions import Fraction
from typing import NamedTuple

from ortools.sat.python import cp_model

from builder.types import Notes
from shared.constants import DIATONIC_DEFAULTS, TONAL_ROOTS
from shared.errors import VoiceGenerationError


# Consonance in diatonic space: 2nds (interval 1) and 7ths (interval 6) are dissonant
DISSONANT_INTERVALS: frozenset[int] = frozenset({1, 6})

# Voice leading costs
STATIC_COST: int = 15       # Same pitch (drone) - discourage
STEP_REWARD: int = -5       # Step motion (1 degree) - reward
SMALL_LEAP_COST: int = 0    # 2 degrees
MEDIUM_LEAP_COST: int = 5   # 3 degrees
LARGE_LEAP_COST: int = 15   # 4+ degrees
HUGE_LEAP_COST: int = 50    # 5+ degrees

# Parallel motion costs (hard constraints use high values)
PARALLEL_FIFTH_COST: int = 10000
PARALLEL_OCTAVE_COST: int = 10000

# Chord tone preference
NON_CHORD_TONE_COST: int = 20
NON_CHORD_STRONG_BEAT_COST: int = 100  # Extra penalty on strong beats


class AttackPoint(NamedTuple):
    """A point where a note attacks."""
    offset: Fraction
    is_strong_beat: bool


class VoiceNote(NamedTuple):
    """A note in a voice with pitch and duration."""
    pitch: int  # Diatonic pitch
    duration: Fraction


def generate_voice_cpsat(
    existing_voices: list[Notes],
    harmony: tuple[str, ...],
    voice_role: str,
    bar_duration: Fraction,
    timeout_seconds: float = 5.0,
) -> Notes:
    """Generate a voice using CP-SAT optimization.

    The generated voice matches the rhythmic structure of the first existing voice
    (typically soprano), selecting pitches that:
    - Are consonant with all existing voices
    - Avoid parallel fifths/octaves
    - Have good voice leading (prefer steps over leaps)
    - Prefer chord tones, especially on strong beats

    Args:
        existing_voices: Already decided voices (e.g., [soprano] for bass).
        harmony: Chord symbols per bar (e.g., ("I", "V", "I")).
        voice_role: Voice being generated ("bass", "alto", "tenor").
        bar_duration: Duration of one bar.
        timeout_seconds: Solver time limit.

    Returns:
        Notes with generated pitches and durations.

    Raises:
        VoiceGenerationError: If no valid solution exists.
    """
    assert voice_role in DIATONIC_DEFAULTS, f"Unknown voice role: {voice_role}"
    assert len(existing_voices) > 0, "Need at least one existing voice"
    assert len(harmony) > 0, "Need at least one chord in harmony"

    soprano: Notes = existing_voices[0]

    # Build attack points from soprano rhythm
    attacks: list[AttackPoint] = _build_attack_points(soprano, bar_duration)

    if not attacks:
        raise VoiceGenerationError(
            f"Cannot generate {voice_role}: no attack points found in soprano"
        )

    # Build candidate pitches for each attack point
    base_octave: int = DIATONIC_DEFAULTS[voice_role] // 7
    candidates: list[tuple[int, ...]] = _build_candidates(
        attacks, harmony, bar_duration, base_octave
    )

    # Build CP-SAT model
    model = cp_model.CpModel()

    # Variables: one pitch per attack point
    pitch_vars: list[cp_model.IntVar] = []
    for i, cands in enumerate(candidates):
        assert len(cands) > 0, f"No candidates at attack {i}"
        var = model.NewIntVar(0, len(cands) - 1, f"p_{i}")
        pitch_vars.append(var)

    # === HARD CONSTRAINTS ===

    # 1. Consonance with soprano at each attack point
    _add_consonance_constraints(
        model, pitch_vars, candidates, attacks, soprano, bar_duration
    )

    # 2. No parallel fifths/octaves with soprano
    _add_parallel_constraints(
        model, pitch_vars, candidates, soprano
    )

    # 3. Consonance with other existing voices (if any)
    for voice in existing_voices[1:]:
        _add_consonance_constraints(
            model, pitch_vars, candidates, attacks, voice, bar_duration
        )
        _add_parallel_constraints(model, pitch_vars, candidates, voice)

    # === SOFT CONSTRAINTS (optimization) ===
    costs: list = []

    # Voice leading costs
    _add_voice_leading_costs(model, pitch_vars, candidates, costs)

    # Chord tone preference
    _add_chord_tone_costs(
        model, pitch_vars, candidates, attacks, harmony, bar_duration, costs
    )

    # Minimize total cost
    if costs:
        model.Minimize(cp_model.LinearExpr.Sum(costs))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Build detailed error message
        soprano_info: list[str] = [
            f"{_diatonic_to_name(soprano.pitches[i])}@{float(attacks[i].offset):.2f}"
            for i in range(min(len(attacks), len(soprano.pitches)))
        ]
        raise VoiceGenerationError(
            f"Cannot generate {voice_role}: CP-SAT solver found no solution. "
            f"Soprano: {soprano_info[:8]}{'...' if len(soprano_info) > 8 else ''}. "
            f"Harmony: {harmony}"
        )

    # Extract solution
    pitches: list[int] = []
    durations: list[Fraction] = []

    for i, var in enumerate(pitch_vars):
        idx = solver.Value(var)
        pitches.append(candidates[i][idx])
        durations.append(soprano.durations[i])

    return Notes(tuple(pitches), tuple(durations))


def _build_attack_points(
    soprano: Notes,
    bar_duration: Fraction,
) -> list[AttackPoint]:
    """Build attack points from soprano rhythm."""
    attacks: list[AttackPoint] = []
    offset: Fraction = Fraction(0)

    for dur in soprano.durations:
        # Determine if this is a strong beat
        bar_position: Fraction = offset % bar_duration
        is_strong: bool = (
            bar_position == Fraction(0) or
            bar_position == bar_duration / 2
        )

        attacks.append(AttackPoint(offset=offset, is_strong_beat=is_strong))
        offset += dur

    return attacks


def _build_candidates(
    attacks: list[AttackPoint],
    harmony: tuple[str, ...],
    bar_duration: Fraction,
    base_octave: int,
) -> list[tuple[int, ...]]:
    """Build candidate pitches for each attack point.

    Candidates include:
    - All chord tones for the current bar's chord
    - Scale tones (for passing tones on weak beats)
    """
    candidates: list[tuple[int, ...]] = []

    for attack in attacks:
        bar_idx: int = int(attack.offset // bar_duration)
        chord: str = harmony[min(bar_idx, len(harmony) - 1)]

        # Get chord tones
        root_degree: int = TONAL_ROOTS.get(chord, 1) - 1  # 0-indexed
        chord_tone_degrees: list[int] = [
            root_degree,
            (root_degree + 2) % 7,  # Third
            (root_degree + 4) % 7,  # Fifth
        ]

        # Convert to diatonic pitches in voice range
        cands: list[int] = []

        # Add chord tones (primary candidates)
        for deg in chord_tone_degrees:
            pitch = base_octave * 7 + deg
            cands.append(pitch)
            # Also add octave below for bass flexibility
            if base_octave > 2:
                cands.append((base_octave - 1) * 7 + deg)

        # Add scale tones for weak beats (passing tones)
        if not attack.is_strong_beat:
            for deg in range(7):
                if deg not in chord_tone_degrees:
                    pitch = base_octave * 7 + deg
                    if pitch not in cands:
                        cands.append(pitch)

        candidates.append(tuple(sorted(cands)))

    return candidates


def _add_consonance_constraints(
    model: cp_model.CpModel,
    pitch_vars: list[cp_model.IntVar],
    candidates: list[tuple[int, ...]],
    attacks: list[AttackPoint],
    reference_voice: Notes,
    bar_duration: Fraction,
) -> None:
    """Add consonance constraints with reference voice.

    On strong beats: FORBID dissonance (hard constraint)
    On weak beats: Allow dissonance (passing tones)
    """
    for i, attack in enumerate(attacks):
        ref_pitch: int = reference_voice.pitches[i] if i < len(reference_voice.pitches) else reference_voice.pitches[-1]
        ref_degree: int = ref_pitch % 7

        # On strong beats, forbid dissonant intervals
        if attack.is_strong_beat:
            forbidden_indices: list[int] = []
            for ci, cand_pitch in enumerate(candidates[i]):
                cand_degree: int = cand_pitch % 7
                interval: int = abs(ref_degree - cand_degree)
                interval = min(interval, 7 - interval)  # Handle inversion

                if interval in DISSONANT_INTERVALS:
                    forbidden_indices.append(ci)

            # Forbid dissonant candidates
            for ci in forbidden_indices:
                model.Add(pitch_vars[i] != ci)


def _add_parallel_constraints(
    model: cp_model.CpModel,
    pitch_vars: list[cp_model.IntVar],
    candidates: list[tuple[int, ...]],
    reference_voice: Notes,
) -> None:
    """Add constraints to forbid parallel fifths and octaves."""
    for i in range(1, len(pitch_vars)):
        prev_ref: int = reference_voice.pitches[i - 1] if i - 1 < len(reference_voice.pitches) else reference_voice.pitches[-1]
        curr_ref: int = reference_voice.pitches[i] if i < len(reference_voice.pitches) else reference_voice.pitches[-1]

        ref_motion: int = curr_ref - prev_ref

        # Skip if reference voice is static (no parallel motion possible)
        if ref_motion == 0:
            continue

        prev_cands = candidates[i - 1]
        curr_cands = candidates[i]

        # Find forbidden (prev, curr) pairs
        forbidden: list[tuple[int, int]] = []

        for pi, prev_pitch in enumerate(prev_cands):
            for ci, curr_pitch in enumerate(curr_cands):
                voice_motion: int = curr_pitch - prev_pitch

                # Skip if this voice is static
                if voice_motion == 0:
                    continue

                # Check if both voices move in same direction
                same_direction: bool = (ref_motion > 0) == (voice_motion > 0)
                if not same_direction:
                    continue

                # Check intervals
                prev_interval: int = abs(prev_ref - prev_pitch) % 7
                curr_interval: int = abs(curr_ref - curr_pitch) % 7

                # Parallel fifth: both intervals are 4 (diatonic fifth)
                is_parallel_fifth: bool = prev_interval == 4 and curr_interval == 4

                # Parallel octave: both intervals are 0 (unison/octave)
                is_parallel_octave: bool = prev_interval == 0 and curr_interval == 0

                if is_parallel_fifth or is_parallel_octave:
                    forbidden.append((pi, ci))

        # Add forbidden assignments
        if forbidden:
            model.AddForbiddenAssignments(
                [pitch_vars[i - 1], pitch_vars[i]],
                forbidden
            )


def _add_voice_leading_costs(
    model: cp_model.CpModel,
    pitch_vars: list[cp_model.IntVar],
    candidates: list[tuple[int, ...]],
    costs: list,
) -> None:
    """Add voice leading costs (prefer stepwise motion)."""
    for i in range(1, len(pitch_vars)):
        prev_cands = candidates[i - 1]
        curr_cands = candidates[i]

        for pi, prev_pitch in enumerate(prev_cands):
            for ci, curr_pitch in enumerate(curr_cands):
                motion: int = abs(curr_pitch - prev_pitch)

                # Determine cost based on interval size
                if motion == 0:
                    cost = STATIC_COST
                elif motion == 1:
                    cost = STEP_REWARD
                elif motion == 2:
                    cost = SMALL_LEAP_COST
                elif motion == 3:
                    cost = MEDIUM_LEAP_COST
                elif motion == 4:
                    cost = LARGE_LEAP_COST
                else:
                    cost = HUGE_LEAP_COST

                if cost != 0:
                    # Create indicator for this transition
                    b_prev = model.NewBoolVar(f"vl_prev_{i}_{pi}")
                    b_curr = model.NewBoolVar(f"vl_curr_{i}_{ci}")

                    model.Add(pitch_vars[i - 1] == pi).OnlyEnforceIf(b_prev)
                    model.Add(pitch_vars[i - 1] != pi).OnlyEnforceIf(b_prev.Not())
                    model.Add(pitch_vars[i] == ci).OnlyEnforceIf(b_curr)
                    model.Add(pitch_vars[i] != ci).OnlyEnforceIf(b_curr.Not())

                    # Both conditions
                    b_both = model.NewBoolVar(f"vl_both_{i}_{pi}_{ci}")
                    model.AddBoolAnd([b_prev, b_curr]).OnlyEnforceIf(b_both)
                    model.AddBoolOr([b_prev.Not(), b_curr.Not()]).OnlyEnforceIf(b_both.Not())

                    costs.append(cost * b_both)


def _add_chord_tone_costs(
    model: cp_model.CpModel,
    pitch_vars: list[cp_model.IntVar],
    candidates: list[tuple[int, ...]],
    attacks: list[AttackPoint],
    harmony: tuple[str, ...],
    bar_duration: Fraction,
    costs: list,
) -> None:
    """Add costs for non-chord tones (prefer chord tones, especially on strong beats)."""
    for i, attack in enumerate(attacks):
        bar_idx: int = int(attack.offset // bar_duration)
        chord: str = harmony[min(bar_idx, len(harmony) - 1)]

        # Get chord tone degrees
        root_degree: int = TONAL_ROOTS.get(chord, 1) - 1
        chord_tone_degrees: frozenset[int] = frozenset({
            root_degree,
            (root_degree + 2) % 7,
            (root_degree + 4) % 7,
        })

        for ci, cand_pitch in enumerate(candidates[i]):
            cand_degree: int = cand_pitch % 7

            if cand_degree not in chord_tone_degrees:
                # Non-chord tone: penalize
                indicator = model.NewBoolVar(f"nct_{i}_{ci}")
                model.Add(pitch_vars[i] == ci).OnlyEnforceIf(indicator)
                model.Add(pitch_vars[i] != ci).OnlyEnforceIf(indicator.Not())

                cost = NON_CHORD_STRONG_BEAT_COST if attack.is_strong_beat else NON_CHORD_TONE_COST
                costs.append(cost * indicator)


def _diatonic_to_name(diatonic: int) -> str:
    """Convert diatonic pitch to note name for error messages."""
    names: tuple[str, ...] = ("C", "D", "E", "F", "G", "A", "B")
    octave: int = diatonic // 7
    degree: int = diatonic % 7
    return f"{names[degree]}{octave}"
