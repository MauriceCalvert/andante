"""Inner voice generation: phrase-level branch-and-bound search.

Phrase-level approach (correct for counterpoint):
1. Soprano phrase is fixed
2. Bass phrase is fixed (from pattern expansion)
3. Generate candidate phrases for each inner voice (alto, tenor)
4. Branch-and-bound search: for each alto → for each tenor
5. Score combinations holistically, prune branches exceeding best-so-far
6. Return optimal combination that passes all guards

This avoids slice-level oscillation that causes endless trills.
"""
from fractions import Fraction
from dataclasses import dataclass
from typing import Callable

from shared.pitch import FloatingNote, MidiPitch, Pitch, Rest, is_rest
from engine.arc_loader import get_default_treatment_for_voice
from engine.key import Key
from engine.slice_solver import (
    SolvedSlice,
    get_voice_range,
    resolve_outer_pitch,
    infer_chord_from_bass_midi,
    _score_configuration,
)
from engine.transform import apply_imitation
from engine.engine_types import ExpandedPhrase, MotifAST
from engine.voice_config import VoiceSet
from engine.voice_entry import VoiceTreatmentSpec
from engine.voice_material import ExpandedVoices, VoiceMaterial


# =============================================================================
# Phrase candidate generation
# =============================================================================

@dataclass(frozen=True)
class PhraseCandidate:
    """A candidate phrase for an inner voice."""
    voice_index: int
    interval: int
    delay: Fraction
    source: str  # "subject" or "counter_subject"
    pitches: tuple[Pitch, ...]
    durations: tuple[Fraction, ...]

    @property
    def budget(self) -> Fraction:
        return sum(self.durations, Fraction(0))


def _generate_phrase_candidates(
    phrase_index: int,
    voice_index: int,
    voice_count: int,
    subject: MotifAST,
    counter_subject: MotifAST | None,
    budget: Fraction,
    bar_dur: Fraction,
) -> list[PhraseCandidate]:
    """Generate multiple phrase candidates for an inner voice.

    Variations include:
    - Different intervals: unison, 3rd, 4th, 5th, 6th, octave (up/down)
    - Different delays: 0, 1/4, 1/2, 3/4, 1 bar
    - Different sources: subject vs counter_subject

    Returns candidates ordered by priority (best baroque conventions first).
    """
    candidates: list[PhraseCandidate] = []

    # Priority intervals for baroque imitation (inner voices typically below soprano)
    # Alto: typically 3rd-5th below soprano
    # Tenor: typically 5th-octave below soprano
    if voice_index == 1:  # Alto
        intervals = [-3, -4, 0, -2, -5, 3, 4, -7]  # 4th below, 5th below, unison, 3rd, 6th, up 4th/5th, octave
        delays = [Fraction(1, 2), Fraction(0), Fraction(1, 4), Fraction(3, 4), Fraction(1)]
    else:  # Tenor (voice_index == 2)
        intervals = [-4, -7, -3, -5, 0, -2, 4]  # 5th below, octave, 4th, 6th, unison, 3rd, up 5th
        delays = [Fraction(1), Fraction(1, 2), Fraction(3, 4), Fraction(0), Fraction(1, 4)]

    sources = ["subject"]
    if counter_subject is not None and not _is_degenerate_motif(counter_subject.pitches):
        sources.append("counter_subject")

    for source in sources:
        for delay in delays:
            if delay >= budget:
                continue
            for interval in intervals:
                cand = _build_phrase_candidate(
                    phrase_index, voice_index, subject, counter_subject,
                    budget, bar_dur, interval, delay, source
                )
                if cand is not None:
                    candidates.append(cand)

    return candidates


def _build_phrase_candidate(
    phrase_index: int,
    voice_index: int,
    subject: MotifAST,
    counter_subject: MotifAST | None,
    budget: Fraction,
    bar_dur: Fraction,
    interval: int,
    delay: Fraction,
    source: str,
) -> PhraseCandidate | None:
    """Build a single phrase candidate with given parameters."""
    delay_dur: Fraction = delay * bar_dur
    if delay_dur >= budget:
        return None

    # Select source material
    use_cs = source == "counter_subject" and counter_subject is not None
    if use_cs:
        source_p: tuple[Pitch, ...] = counter_subject.pitches
        source_d: tuple[Fraction, ...] = counter_subject.durations
    else:
        source_p = subject.pitches
        source_d = subject.durations

    # Apply interval transposition
    if interval != 0:
        source_p = apply_imitation(source_p, interval)

    # Build phrase with delay
    pitches: list[Pitch] = []
    durations: list[Fraction] = []

    if delay_dur > Fraction(0):
        pitches.append(Rest())
        durations.append(delay_dur)

    thematic_budget: Fraction = budget - delay_dur
    thematic_dur: Fraction = sum(source_d, Fraction(0))

    if thematic_dur <= thematic_budget:
        # Thematic material fits - use it once
        pitches.extend(source_p)
        durations.extend(source_d)
        remaining: Fraction = thematic_budget - thematic_dur
        if remaining > Fraction(0):
            # Hold final note (baroque style)
            final_pitch: Pitch = source_p[-1] if source_p else Rest()
            if is_rest(final_pitch):
                pitches.append(Rest())
            else:
                pitches.append(final_pitch)
            durations.append(remaining)
    else:
        # Truncate to fit
        accumulated: Fraction = Fraction(0)
        for p, d in zip(source_p, source_d):
            if accumulated + d > thematic_budget:
                remaining_time: Fraction = thematic_budget - accumulated
                if remaining_time > Fraction(0):
                    pitches.append(p)
                    durations.append(remaining_time)
                break
            pitches.append(p)
            durations.append(d)
            accumulated += d

    return PhraseCandidate(
        voice_index=voice_index,
        interval=interval,
        delay=delay,
        source=source,
        pitches=tuple(pitches),
        durations=tuple(durations),
    )


def _is_degenerate_motif(pitches: tuple[Pitch, ...]) -> bool:
    """Check if motif has degenerate repetition (>50% same degree)."""
    if len(pitches) < 4:
        return False
    degrees: list[int] = [p.degree for p in pitches if hasattr(p, 'degree')]
    if not degrees:
        return True
    from collections import Counter
    counter = Counter(degrees)
    most_common_count: int = counter.most_common(1)[0][1]
    return most_common_count > len(degrees) // 2


def _generate_chordal_candidates(
    voice_index: int,
    voice_count: int,
    soprano: VoiceMaterial,
    bass: VoiceMaterial,
    key: Key,
    budget: Fraction,
) -> list[PhraseCandidate]:
    """Generate chord-tone based candidates for homophonic texture.

    For each attack point in soprano/bass, picks a chord tone in the
    inner voice range. Generates multiple candidates with different
    chord-tone choices (root, third, fifth).
    """
    voice_range = get_voice_range(voice_index, voice_count)
    median = (voice_range[0] + voice_range[1]) // 2

    # Collect attack points from soprano
    attack_points: list[tuple[Fraction, int, int]] = []  # (offset, soprano_midi, bass_midi)
    soprano_offset = Fraction(0)
    bass_offset = Fraction(0)

    # Build offset->pitch maps
    soprano_by_offset: dict[Fraction, int] = {}
    for p, d in zip(soprano.pitches, soprano.durations):
        if isinstance(p, MidiPitch):
            soprano_by_offset[soprano_offset] = p.midi
        soprano_offset += d

    bass_by_offset: dict[Fraction, int] = {}
    for p, d in zip(bass.pitches, bass.durations):
        if isinstance(p, MidiPitch):
            bass_by_offset[bass_offset] = p.midi
        bass_offset += d

    # Collect attacks
    for offset in sorted(soprano_by_offset.keys()):
        soprano_midi = soprano_by_offset[offset]
        # Find bass at this offset
        bass_midi = None
        for b_off in sorted(bass_by_offset.keys(), reverse=True):
            if b_off <= offset:
                bass_midi = bass_by_offset[b_off]
                break
        if bass_midi is not None:
            attack_points.append((offset, soprano_midi, bass_midi))

    if not attack_points:
        return []

    # Generate candidates for different chord-tone preferences
    # 0 = prefer root, 1 = prefer third, 2 = prefer fifth
    candidates: list[PhraseCandidate] = []

    for preference in range(3):
        pitches: list[Pitch] = []
        durations: list[Fraction] = []
        prev_offset = Fraction(0)

        for i, (offset, soprano_midi, bass_midi) in enumerate(attack_points):
            # Add gap if needed
            if offset > prev_offset:
                gap = offset - prev_offset
                if pitches:
                    # Extend previous note
                    durations[-1] += gap
                else:
                    pitches.append(Rest())
                    durations.append(gap)

            # Infer chord from bass
            chord_tones = infer_chord_from_bass_midi(bass_midi, key)
            chord_pc = {ct % 12 for ct in chord_tones}

            # Find chord tones in range
            available: list[int] = []
            for pc in chord_pc:
                midi = pc
                while midi < voice_range[0]:
                    midi += 12
                while midi <= voice_range[1]:
                    available.append(midi)
                    midi += 12

            if not available:
                available = [median]

            # Select based on preference with voice leading
            if len(pitches) > 0 and not is_rest(pitches[-1]):
                prev_midi = pitches[-1].midi if isinstance(pitches[-1], MidiPitch) else median
                # Sort by distance to previous pitch, then by preference
                available.sort(key=lambda m: (abs(m - prev_midi), (m % 12 - preference * 4) % 12))
            else:
                # Sort by preference and distance to median
                available.sort(key=lambda m: ((m % 12 - preference * 4) % 12, abs(m - median)))

            selected = available[0]
            pitches.append(MidiPitch(selected))

            # Duration until next attack or end
            if i < len(attack_points) - 1:
                dur = attack_points[i + 1][0] - offset
            else:
                dur = budget - offset

            durations.append(dur)
            prev_offset = offset + dur

        candidates.append(PhraseCandidate(
            voice_index=voice_index,
            interval=0,
            delay=Fraction(0),
            source=f"chordal_{preference}",
            pitches=tuple(pitches),
            durations=tuple(durations),
        ))

    return candidates


# =============================================================================
# Phrase-level scoring
# =============================================================================

def _resolve_phrase_to_midi(
    phrase: PhraseCandidate | VoiceMaterial,
    key: Key,
    voice_count: int,
) -> list[tuple[Fraction, int, Fraction]]:
    """Resolve phrase to (offset, midi, duration) tuples.

    Skips rests (they don't contribute to vertical sonority).
    """
    if isinstance(phrase, PhraseCandidate):
        pitches = phrase.pitches
        durations = phrase.durations
        voice_index = phrase.voice_index
    else:
        pitches = phrase.pitches
        durations = phrase.durations
        voice_index = phrase.voice_index

    voice_range = get_voice_range(voice_index, voice_count)
    median = (voice_range[0] + voice_range[1]) // 2

    result: list[tuple[Fraction, int, Fraction]] = []
    offset = Fraction(0)
    prev_midi = median

    for p, d in zip(pitches, durations):
        if not is_rest(p):
            if isinstance(p, MidiPitch):
                midi = p.midi
            elif isinstance(p, FloatingNote):
                midi = key.floating_to_midi(p, prev_midi, median)
            else:
                midi = median
            result.append((offset, midi, d))
            prev_midi = midi
        offset += d

    return result


def _get_sounding_pitch(
    notes: list[tuple[Fraction, int, Fraction]],
    offset: Fraction,
) -> int | None:
    """Get sounding MIDI pitch at offset, or None if rest/gap."""
    for note_offset, midi, dur in reversed(notes):
        if note_offset <= offset < note_offset + dur:
            return midi
    return None


def _score_phrase_combination(
    soprano: VoiceMaterial,
    bass: VoiceMaterial,
    inner_phrases: list[PhraseCandidate],
    key: Key,
    voice_count: int,
) -> float:
    """Score a complete phrase combination.

    Evaluates all vertical slices and voice-leading between them.
    Lower score is better.
    """
    # Resolve all phrases to MIDI note sequences
    soprano_notes = _resolve_phrase_to_midi(
        VoiceMaterial(voice_index=0, pitches=list(soprano.pitches), durations=list(soprano.durations)),
        key, voice_count
    )
    bass_notes = _resolve_phrase_to_midi(
        VoiceMaterial(voice_index=voice_count - 1, pitches=list(bass.pitches), durations=list(bass.durations)),
        key, voice_count
    )

    inner_notes: list[list[tuple[Fraction, int, Fraction]]] = []
    for phrase in inner_phrases:
        inner_notes.append(_resolve_phrase_to_midi(phrase, key, voice_count))

    # Collect all attack points
    attack_offsets: set[Fraction] = set()
    for off, _, _ in soprano_notes:
        attack_offsets.add(off)
    for off, _, _ in bass_notes:
        attack_offsets.add(off)
    for notes in inner_notes:
        for off, _, _ in notes:
            attack_offsets.add(off)

    sorted_offsets = sorted(attack_offsets)
    if not sorted_offsets:
        return 0.0

    total_cost = 0.0
    prev_config: tuple[int, ...] | None = None

    for offset in sorted_offsets:
        # Build vertical configuration
        soprano_midi = _get_sounding_pitch(soprano_notes, offset)
        bass_midi = _get_sounding_pitch(bass_notes, offset)

        if soprano_midi is None or bass_midi is None:
            continue

        # Get inner voice pitches
        inner_midis: list[int] = []
        for notes in inner_notes:
            inner_midi = _get_sounding_pitch(notes, offset)
            inner_midis.append(inner_midi if inner_midi is not None else -1)

        # Build configuration tuple
        config: tuple[int, ...] = (soprano_midi,) + tuple(inner_midis) + (bass_midi,)

        # Infer chord from bass
        chord_tones = infer_chord_from_bass_midi(bass_midi, key)
        chord_pc = {ct % 12 for ct in chord_tones}

        # Score this slice
        slice_cost = _score_configuration(config, prev_config, chord_pc)
        total_cost += slice_cost
        prev_config = config

    return total_cost


# =============================================================================
# Guard validation
# =============================================================================

def validate_nvoice_guards(
    phrase: ExpandedPhrase,
    key: Key,
    bar_dur: Fraction,
    metre: str,
    phrase_offset: Fraction,
) -> list:
    """Validate N-voice phrase by realising and checking all voice pair guards.

    Public API for external callers (e.g., expander.py).
    Returns list of blocker violations.
    """
    from engine.realiser import realise_phrase
    from engine.voice_pair import VoicePairSet
    from engine.guards.registry import create_guards, run_guards

    realised = realise_phrase(phrase, key, phrase_offset, bar_dur, metre, False)
    guards = create_guards()
    voice_count: int = len(realised.voices)
    pairs: VoicePairSet = VoicePairSet.compute(voice_count)
    violations: list = []

    for pair in pairs.pairs:
        upper = [(n.offset, n.pitch) for n in realised.voices[pair.upper_index].notes]
        lower = [(n.offset, n.pitch) for n in realised.voices[pair.lower_index].notes]
        location: str = f"phrase {phrase.index} voices {pair.upper_index}-{pair.lower_index}"
        diags = run_guards(guards, upper, lower, location, bar_dur, metre)
        # Exclude final offset for cadence phrases
        if phrase.cadence is not None and upper:
            final_offset: Fraction = upper[-1][0]
            diags = [d for d in diags if d.offset != final_offset]
        violations.extend([d for d in diags if d.severity == "blocker"])

    return violations


# Alias for internal use
_validate_phrase_guards = validate_nvoice_guards


# =============================================================================
# Branch-and-bound search
# =============================================================================

def _branch_and_bound_search(
    soprano: VoiceMaterial,
    bass: VoiceMaterial,
    inner_candidates: list[list[PhraseCandidate]],
    key: Key,
    voice_count: int,
    phrase: ExpandedPhrase,
    bar_dur: Fraction,
    metre: str,
    phrase_offset: Fraction,
) -> tuple[list[PhraseCandidate], float]:
    """Find optimal inner voice combination using branch-and-bound.

    Args:
        soprano: Fixed soprano phrase
        bass: Fixed bass phrase
        inner_candidates: List of candidate lists, one per inner voice
        key: Musical key
        voice_count: Number of voices
        phrase: Original phrase for guard validation
        bar_dur: Bar duration for guards
        metre: Time signature for guards
        phrase_offset: Absolute offset for guards

    Returns:
        Tuple of (best inner phrase list, best score)
    """
    inner_count = len(inner_candidates)
    if inner_count == 0:
        return [], 0.0

    best_score = float('inf')
    best_combination: list[PhraseCandidate] = []

    def search(
        depth: int,
        current_selection: list[PhraseCandidate],
        partial_score: float,
    ) -> None:
        nonlocal best_score, best_combination

        # Prune if partial score already exceeds best
        if partial_score >= best_score:
            return

        if depth == inner_count:
            # Complete combination - validate with guards
            voices = _build_voices_from_phrases(soprano, bass, current_selection, voice_count)
            candidate_phrase = _make_phrase_with_voices(phrase, voices)
            violations = _validate_phrase_guards(
                candidate_phrase, key, bar_dur, metre, phrase_offset
            )

            if not violations:
                # Valid combination - compute full score
                full_score = _score_phrase_combination(
                    soprano, bass, current_selection, key, voice_count
                )
                if full_score < best_score:
                    best_score = full_score
                    best_combination = list(current_selection)
            return

        # Try each candidate at this depth
        for candidate in inner_candidates[depth]:
            # Compute incremental score for this addition
            current_plus_new = current_selection + [candidate]
            incremental_score = _score_phrase_combination(
                soprano, bass, current_plus_new, key, voice_count
            )

            # Recurse with updated partial score
            search(depth + 1, current_plus_new, incremental_score)

    # Start search
    search(0, [], 0.0)

    # If no valid combination found, return first candidates as fallback
    if not best_combination:
        best_combination = [cands[0] for cands in inner_candidates if cands]
        best_score = float('inf')

    return best_combination, best_score


# =============================================================================
# Voice building helpers
# =============================================================================

def _build_voices_from_phrases(
    soprano: VoiceMaterial,
    bass: VoiceMaterial,
    inner_phrases: list[PhraseCandidate],
    voice_count: int,
) -> ExpandedVoices:
    """Build ExpandedVoices from soprano, bass, and inner phrase candidates.

    Creates VoiceMaterial for each voice with correct indices:
    - Soprano: index 0
    - Inner voices: indices 1 to voice_count-2
    - Bass: index voice_count-1
    """
    # Build list by index position, not by appending
    materials: list[VoiceMaterial] = []

    # Soprano at index 0
    materials.append(VoiceMaterial(
        voice_index=0,
        pitches=list(soprano.pitches),
        durations=list(soprano.durations),
    ))

    # Inner voices at indices 1 to voice_count-2
    for i, phrase in enumerate(inner_phrases):
        materials.append(VoiceMaterial(
            voice_index=i + 1,  # Use sequential index, not phrase.voice_index
            pitches=list(phrase.pitches),
            durations=list(phrase.durations),
        ))

    # Bass at index voice_count-1
    materials.append(VoiceMaterial(
        voice_index=voice_count - 1,
        pitches=list(bass.pitches),
        durations=list(bass.durations),
    ))

    return ExpandedVoices(voices=materials)


def _make_phrase_with_voices(phrase: ExpandedPhrase, voices: ExpandedVoices) -> ExpandedPhrase:
    """Create ExpandedPhrase with given voices."""
    return ExpandedPhrase(
        index=phrase.index, bars=phrase.bars, voices=voices, cadence=phrase.cadence,
        tonal_target=phrase.tonal_target, is_climax=phrase.is_climax,
        articulation=phrase.articulation, gesture=phrase.gesture,
        energy=phrase.energy or "moderate", surprise=phrase.surprise,
        texture=phrase.texture, episode_type=phrase.episode_type,
        treatment=phrase.treatment,
    )


# =============================================================================
# Main entry point
# =============================================================================

def add_inner_voices_with_backtracking(
    phrase: ExpandedPhrase,
    key: Key,
    texture: str,
    voice_set: VoiceSet,
    bar_dur: Fraction,
    metre: str,
    phrase_offset: Fraction,
    subject: MotifAST | None = None,
    counter_subject: MotifAST | None = None,
    max_backtracks: int = 1000,  # Unused - kept for API compatibility
) -> ExpandedPhrase:
    """Add inner voices using phrase-level branch-and-bound search.

    Phrase-level approach:
    1. Soprano and bass are fixed
    2. Generate candidate phrases for each inner voice (variations in interval/delay)
    3. Branch-and-bound search through combinations
    4. Score each combination holistically (all slices + voice leading)
    5. Prune branches exceeding best-so-far score
    6. Validate winning combination with guards
    7. Return optimal phrase that passes all guards

    For polyphonic texture, inner voices use thematic material (subject/counter_subject
    at intervals). For homophonic, uses chord tones (single candidate per voice).
    """
    inner_count: int = voice_set.count - 2
    if inner_count <= 0:
        return phrase

    soprano: VoiceMaterial = phrase.voices.soprano
    bass: VoiceMaterial = phrase.voices.bass
    budget: Fraction = soprano.budget
    voice_count: int = voice_set.count
    use_thematic: bool = texture == "polyphonic" and subject is not None

    # Generate phrase candidates for each inner voice
    inner_candidates: list[list[PhraseCandidate]] = []

    for i in range(inner_count):
        inner_idx: int = i + 1  # 1 = alto, 2 = tenor

        if use_thematic:
            # Generate multiple thematic candidates with different intervals/delays
            candidates = _generate_phrase_candidates(
                phrase.index, inner_idx, voice_count,
                subject, counter_subject, budget, bar_dur
            )
        else:
            # Homophonic or no subject: generate chord-tone based candidates
            candidates = _generate_chordal_candidates(
                inner_idx, voice_count, soprano, bass, key, budget
            )

        if not candidates:
            # Fallback: rest for entire phrase
            candidates = [PhraseCandidate(
                voice_index=inner_idx,
                interval=0,
                delay=Fraction(0),
                source="rest",
                pitches=(Rest(),),
                durations=(budget,),
            )]

        inner_candidates.append(candidates)

    # Branch-and-bound search for optimal combination
    best_phrases, best_score = _branch_and_bound_search(
        soprano, bass, inner_candidates,
        key, voice_count,
        phrase, bar_dur, metre, phrase_offset,
    )

    # Classify result quality
    if best_score == float('inf'):
        quality = "FAILED"
    elif best_score < 150:
        quality = "good"
    elif best_score < 350:
        quality = "acceptable"
    else:
        quality = "problematic"

    cand_counts = [len(c) for c in inner_candidates]
    total_searched = 1
    for c in cand_counts:
        total_searched *= c
    start_bar = int(phrase_offset / bar_dur) + 1  # 1-based bar numbers
    end_bar = start_bar + phrase.bars - 1
    bar_range = f"bar {start_bar}" if phrase.bars == 1 else f"bars {start_bar}-{end_bar}"
    print(f"  phrase {phrase.index} ({bar_range}): {quality} (score={best_score:.0f}, searched {total_searched} combinations)")

    # Build final phrase with optimal inner voices
    voices = _build_voices_from_phrases(soprano, bass, best_phrases, voice_count)
    return _make_phrase_with_voices(phrase, voices)


def add_inner_voices_cpsat(
    phrase: ExpandedPhrase,
    key: Key,
    texture: str,
    voice_set: VoiceSet,
    bar_dur: Fraction,
    metre: str,
    phrase_offset: Fraction,
    subject: MotifAST | None = None,
    counter_subject: MotifAST | None = None,
    timeout_seconds: float = 5.0,
) -> ExpandedPhrase:
    """Add inner voices using CP-SAT constraint solver.

    This is the preferred method for inner voice generation. It solves all inner
    voice pitches across all slices simultaneously, guaranteeing global optimality
    within the constraint model.

    Falls back to branch-and-bound if CP-SAT fails to find a solution.

    Args:
        phrase: ExpandedPhrase with soprano and bass
        key: Musical key
        texture: "polyphonic" or "homophonic"
        voice_set: Voice configuration
        bar_dur: Bar duration for position calculation
        metre: Time signature string
        phrase_offset: Absolute offset of phrase start
        subject: Optional subject motif for polyphonic texture
        counter_subject: Optional counter-subject for polyphonic texture
        timeout_seconds: CP-SAT solver time limit

    Returns:
        ExpandedPhrase with solved inner voices
    """
    from engine.cpsat_slice_solver import solve_phrase_cpsat

    inner_count: int = voice_set.count - 2
    if inner_count <= 0:
        return phrase

    # Extract subject/CS pitches and durations for thematic guidance
    subject_pitches = subject.pitches if subject else None
    subject_durations = subject.durations if subject else None
    cs_pitches = counter_subject.pitches if counter_subject else None
    cs_durations = counter_subject.durations if counter_subject else None

    # Attempt CP-SAT solving
    start_bar = int(phrase_offset / bar_dur) + 1
    end_bar = start_bar + phrase.bars - 1
    bar_range = f"bar {start_bar}" if phrase.bars == 1 else f"bars {start_bar}-{end_bar}"

    result = solve_phrase_cpsat(
        phrase.voices,
        key,
        metre,
        texture,
        target_voice_count=voice_set.count,
        subject_pitches=subject_pitches,
        subject_durations=subject_durations,
        cs_pitches=cs_pitches,
        cs_durations=cs_durations,
        timeout_seconds=timeout_seconds,
    )

    if result is not None:
        # CP-SAT succeeded - validate with guards
        candidate_phrase = _make_phrase_with_voices(phrase, result)
        violations = _validate_phrase_guards(
            candidate_phrase, key, bar_dur, metre, phrase_offset
        )

        if not violations:
            print(f"  phrase {phrase.index} ({bar_range}): CP-SAT optimal")
            return candidate_phrase
        else:
            print(f"  phrase {phrase.index} ({bar_range}): CP-SAT found violations ({len(violations)}), falling back")

    # Fallback to branch-and-bound
    print(f"  phrase {phrase.index} ({bar_range}): CP-SAT infeasible, using branch-and-bound")
    return add_inner_voices_with_backtracking(
        phrase, key, texture, voice_set, bar_dur, metre, phrase_offset,
        subject, counter_subject, max_backtracks=1000
    )
