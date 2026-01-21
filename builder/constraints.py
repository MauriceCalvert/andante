"""Hard constraint definitions for counterpoint solver."""

from fractions import Fraction

from builder.slice import (
    Slice,
    SlicePair,
    simple_interval,
    melodic_interval,
    motion_type,
    extract_slice_pairs,
)
from shared.parallels import is_parallel_fifth, is_parallel_octave

# Interval constants (semitones)
PERFECT_UNISON: int = 0
MINOR_SECOND: int = 1
MAJOR_SECOND: int = 2
MINOR_THIRD: int = 3
MAJOR_THIRD: int = 4
PERFECT_FOURTH: int = 5
TRITONE: int = 6
PERFECT_FIFTH: int = 7
MINOR_SIXTH: int = 8
MAJOR_SIXTH: int = 9
MINOR_SEVENTH: int = 10
MAJOR_SEVENTH: int = 11
PERFECT_OCTAVE: int = 12

# Interval sets
PERFECT_CONSONANCES: frozenset[int] = frozenset({
    PERFECT_UNISON, PERFECT_FIFTH, PERFECT_OCTAVE
})

IMPERFECT_CONSONANCES: frozenset[int] = frozenset({
    MINOR_THIRD, MAJOR_THIRD, MINOR_SIXTH, MAJOR_SIXTH
})

CONSONANCES: frozenset[int] = PERFECT_CONSONANCES | IMPERFECT_CONSONANCES

DISSONANCES: frozenset[int] = frozenset({
    MINOR_SECOND, MAJOR_SECOND, PERFECT_FOURTH,
    TRITONE, MINOR_SEVENTH, MAJOR_SEVENTH
})

# Intervals forbidden in invertible counterpoint at the tenth
# P5 inverts to P4 (dissonant in two-part)
FORBIDDEN_AT_TENTH: frozenset[int] = frozenset({PERFECT_FIFTH})

# Intervals forbidden in invertible counterpoint at the twelfth
# m6 inverts to M7, M6 inverts to m7
FORBIDDEN_AT_TWELFTH: frozenset[int] = frozenset({MINOR_SIXTH, MAJOR_SIXTH})


# =============================================================================
# H01: Pitch Class Membership
# =============================================================================


def check_pitch_class(
    pitch: int,
    pitch_class_set: frozenset[int],
) -> bool:
    """
    H01: Check pitch belongs to valid pitch class set.

    Args:
        pitch: MIDI pitch (0-127)
        pitch_class_set: Valid pitch classes (0-11)

    Returns:
        True if pitch % 12 in pitch_class_set.
    """
    return (pitch % 12) in pitch_class_set


# =============================================================================
# H02-H04: Parallel Perfect Intervals
# =============================================================================


def check_no_parallel_unisons(pair: SlicePair, voice_a: int, voice_b: int) -> bool:
    """
    H02: No consecutive unisons between voice pair.

    Delegates to shared.parallels.is_parallel_octave (which checks interval 0,
    covering both unisons and octaves).

    Returns:
        True if no parallel unisons detected.
    """
    pitch_a_first = pair.first.pitches[voice_a]
    pitch_b_first = pair.first.pitches[voice_b]
    pitch_a_second = pair.second.pitches[voice_a]
    pitch_b_second = pair.second.pitches[voice_b]

    assert pitch_a_first is not None, "voice_a must have pitch in first slice"
    assert pitch_b_first is not None, "voice_b must have pitch in first slice"
    assert pitch_a_second is not None, "voice_a must have pitch in second slice"
    assert pitch_b_second is not None, "voice_b must have pitch in second slice"

    return not is_parallel_octave(
        pitch_a_first,
        pitch_b_first,
        pitch_a_second,
        pitch_b_second,
    )


def check_no_parallel_fifths(pair: SlicePair, voice_a: int, voice_b: int) -> bool:
    """
    H03: No consecutive perfect fifths between voice pair.

    Delegates to shared.parallels.is_parallel_fifth.

    Returns:
        True if no parallel fifths detected.
    """
    pitch_a_first = pair.first.pitches[voice_a]
    pitch_b_first = pair.first.pitches[voice_b]
    pitch_a_second = pair.second.pitches[voice_a]
    pitch_b_second = pair.second.pitches[voice_b]

    assert pitch_a_first is not None, "voice_a must have pitch in first slice"
    assert pitch_b_first is not None, "voice_b must have pitch in first slice"
    assert pitch_a_second is not None, "voice_a must have pitch in second slice"
    assert pitch_b_second is not None, "voice_b must have pitch in second slice"

    return not is_parallel_fifth(
        pitch_a_first,
        pitch_b_first,
        pitch_a_second,
        pitch_b_second,
    )


def check_no_parallel_octaves(pair: SlicePair, voice_a: int, voice_b: int) -> bool:
    """
    H04: No consecutive perfect octaves between voice pair.

    Delegates to shared.parallels.is_parallel_octave.

    Returns:
        True if no parallel octaves detected.
    """
    pitch_a_first = pair.first.pitches[voice_a]
    pitch_b_first = pair.first.pitches[voice_b]
    pitch_a_second = pair.second.pitches[voice_a]
    pitch_b_second = pair.second.pitches[voice_b]

    assert pitch_a_first is not None, "voice_a must have pitch in first slice"
    assert pitch_b_first is not None, "voice_b must have pitch in first slice"
    assert pitch_a_second is not None, "voice_a must have pitch in second slice"
    assert pitch_b_second is not None, "voice_b must have pitch in second slice"

    return not is_parallel_octave(
        pitch_a_first,
        pitch_b_first,
        pitch_a_second,
        pitch_b_second,
    )


# =============================================================================
# H05-H06: Direct (Hidden) Fifths and Octaves
# =============================================================================


def check_no_direct_fifth(
    pair: SlicePair,
    soprano_voice: int,
    other_voice: int,
) -> bool:
    """
    H05: No similar motion into perfect fifth with soprano leap.

    Args:
        pair: Two consecutive slices
        soprano_voice: Index of soprano (always 0)
        other_voice: Index of other voice

    Returns:
        False if ALL of:
        - Motion is "similar" between soprano and other voice
        - Resulting interval is perfect fifth (simple_interval == 7)
        - Soprano moves by leap (abs(melodic_interval) > 2)
        True otherwise.

    Definition of leap: > 2 semitones (larger than major second)
    """
    soprano_from = pair.first.pitches[soprano_voice]
    soprano_to = pair.second.pitches[soprano_voice]
    other_from = pair.first.pitches[other_voice]
    other_to = pair.second.pitches[other_voice]

    assert soprano_from is not None, "soprano must have pitch in first slice"
    assert soprano_to is not None, "soprano must have pitch in second slice"
    assert other_from is not None, "other voice must have pitch in first slice"
    assert other_to is not None, "other voice must have pitch in second slice"

    motion = motion_type(soprano_from, soprano_to, other_from, other_to)
    if motion != "similar":
        return True

    resulting_interval: int = simple_interval(soprano_to, other_to)
    if resulting_interval != PERFECT_FIFTH:
        return True

    soprano_motion: int = abs(melodic_interval(soprano_from, soprano_to))
    if soprano_motion <= MAJOR_SECOND:
        return True

    return False


def check_no_direct_octave(
    pair: SlicePair,
    soprano_voice: int,
    other_voice: int,
) -> bool:
    """
    H06: No similar motion into perfect octave with soprano leap.

    Same logic as H05 but checking for octave (simple_interval == 12).
    """
    soprano_from = pair.first.pitches[soprano_voice]
    soprano_to = pair.second.pitches[soprano_voice]
    other_from = pair.first.pitches[other_voice]
    other_to = pair.second.pitches[other_voice]

    assert soprano_from is not None, "soprano must have pitch in first slice"
    assert soprano_to is not None, "soprano must have pitch in second slice"
    assert other_from is not None, "other voice must have pitch in first slice"
    assert other_to is not None, "other voice must have pitch in second slice"

    motion = motion_type(soprano_from, soprano_to, other_from, other_to)
    if motion != "similar":
        return True

    resulting_interval: int = simple_interval(soprano_to, other_to)
    if resulting_interval != PERFECT_OCTAVE:
        return True

    soprano_motion: int = abs(melodic_interval(soprano_from, soprano_to))
    if soprano_motion <= MAJOR_SECOND:
        return True

    return False


# =============================================================================
# H07-H09: Dissonance Treatment
# =============================================================================


def is_strong_beat(offset: Fraction, metre_numerator: int) -> bool:
    """
    Determine if offset falls on a strong beat.

    Args:
        offset: Position in whole notes
        metre_numerator: Beats per bar (4 for 4/4, 3 for 3/4)

    Returns:
        True if offset is a strong beat.

    Strong beat definition:
        - 4/4: beats 1 and 3 (offsets 0, 0.5 within each bar)
        - 3/4: beat 1 only (offset 0 within each bar)
    """
    bar_position: Fraction = offset % 1  # Position within bar (0.0 to 1.0)
    if metre_numerator == 4:
        return bar_position in {Fraction(0), Fraction(1, 2)}
    if metre_numerator == 3:
        return bar_position == Fraction(0)
    # Default: beat 1 only
    return bar_position == Fraction(0)


def check_strong_beat_consonance(
    slice_: Slice,
    outer_voices: tuple[int, int],
    metre_numerator: int,
) -> bool:
    """
    H07: Outer voices consonant on strong beats.

    Args:
        slice_: Vertical slice to check
        outer_voices: (soprano_index, bass_index), typically (0, voice_count-1)
        metre_numerator: For strong beat determination

    Returns:
        True if:
        - Offset is not a strong beat, OR
        - Interval between outer voices is consonant
    """
    if not is_strong_beat(slice_.offset, metre_numerator):
        return True
    soprano = slice_.pitches[outer_voices[0]]
    bass = slice_.pitches[outer_voices[1]]
    if soprano is None or bass is None:
        return True  # No attack, no constraint
    interval: int = simple_interval(soprano, bass)
    return interval in CONSONANCES


def check_dissonance_prepared(
    slices: list[Slice],
    slice_index: int,
    outer_voices: tuple[int, int],
    metre_numerator: int,
) -> bool:
    """
    H08: Dissonance on strong beat must be prepared.

    Args:
        slices: All slices in phrase
        slice_index: Index of slice to check
        outer_voices: (soprano_index, bass_index)
        metre_numerator: For strong beat determination

    Returns:
        True if:
        - Slice is not on strong beat, OR
        - Interval is consonant, OR
        - Dissonant note present in immediately preceding slice

    Preparation rule:
        The dissonant pitch must sound in the same voice on the
        immediately preceding slice (suspension preparation).
    """
    slice_ = slices[slice_index]
    if not is_strong_beat(slice_.offset, metre_numerator):
        return True
    soprano_idx, bass_idx = outer_voices
    soprano = slice_.pitches[soprano_idx]
    bass = slice_.pitches[bass_idx]
    if soprano is None or bass is None:
        return True
    interval: int = simple_interval(soprano, bass)
    if interval in CONSONANCES:
        return True
    # Dissonant: check preparation
    if slice_index == 0:
        return False  # No preceding slice, cannot be prepared
    prev = slices[slice_index - 1]
    # Dissonant note is the one that moved; prepared note must be stationary
    # Convention: soprano is the suspended voice
    prev_soprano = prev.pitches[soprano_idx]
    return prev_soprano == soprano


def check_dissonance_resolved(
    slices: list[Slice],
    slice_index: int,
    outer_voices: tuple[int, int],
    metre_numerator: int,
) -> bool:
    """
    H09: Dissonance on strong beat must resolve by step.

    Args:
        slices: All slices in phrase
        slice_index: Index of slice to check
        outer_voices: (soprano_index, bass_index)
        metre_numerator: For strong beat determination

    Returns:
        True if:
        - Slice is not on strong beat, OR
        - Interval is consonant, OR
        - Suspended voice moves by step (1-2 semitones) in next slice

    Resolution rule:
        The suspended voice must descend by step to a consonance.
    """
    slice_ = slices[slice_index]
    if not is_strong_beat(slice_.offset, metre_numerator):
        return True
    soprano_idx, bass_idx = outer_voices
    soprano = slice_.pitches[soprano_idx]
    bass = slice_.pitches[bass_idx]
    if soprano is None or bass is None:
        return True
    interval: int = simple_interval(soprano, bass)
    if interval in CONSONANCES:
        return True
    # Dissonant: check resolution
    if slice_index >= len(slices) - 1:
        return False  # No following slice, cannot resolve
    next_slice = slices[slice_index + 1]
    next_soprano = next_slice.pitches[soprano_idx]
    if next_soprano is None:
        return False
    step: int = abs(melodic_interval(soprano, next_soprano))
    return step in {1, 2}  # Semitone or whole tone


# =============================================================================
# H10: Anchor Preservation (forward reference to Anchor type from solver)
# =============================================================================


def check_anchor_preserved(
    pitches: dict[tuple[Fraction, int], int],
    anchors: list,  # list[Anchor] - forward reference
) -> bool:
    """
    H10: All anchors use exactly specified MIDI pitch.

    Args:
        pitches: Solution pitch assignments
        anchors: Required fixed pitches (list of Anchor objects with offset, voice, midi)

    Returns:
        True if for every anchor, pitches[(anchor.offset, anchor.voice)] == anchor.midi.
    """
    for anchor in anchors:
        key = (anchor.offset, anchor.voice)
        if key not in pitches:
            return False
        if pitches[key] != anchor.midi:
            return False
    return True


# =============================================================================
# H11: Invertible Counterpoint
# =============================================================================


def check_invertible(
    slices: list[Slice],
    voice_a: int,
    voice_b: int,
    invertible_at: int,
) -> bool:
    """
    H11: All intervals between voice pair are invertible.

    Args:
        slices: All slices in phrase
        voice_a: First voice index
        voice_b: Second voice index
        invertible_at: Inversion interval (10 or 12)

    Returns:
        True if no slice contains a forbidden interval between the voices.
    """
    assert invertible_at in {10, 12}, f"invertible_at must be 10 or 12, got {invertible_at}"

    if invertible_at == 10:
        forbidden = FORBIDDEN_AT_TENTH
    else:
        forbidden = FORBIDDEN_AT_TWELFTH

    for slice_ in slices:
        pitch_a = slice_.pitches[voice_a]
        pitch_b = slice_.pitches[voice_b]
        if pitch_a is None or pitch_b is None:
            continue
        interval: int = simple_interval(pitch_a, pitch_b)
        if interval in forbidden:
            return False
    return True


# =============================================================================
# Aggregate Checker
# =============================================================================


def check_all_hard_constraints(
    pitches: dict[tuple[Fraction, int], int],
    anchors: list,  # list[Anchor]
    pitch_class_set: frozenset[int],
    voice_count: int,
    metre_numerator: int,
    invertible_at: int | None,
) -> tuple[bool, str | None]:
    """
    Check all hard constraints.

    Args:
        pitches: Candidate solution
        anchors: Fixed pitches
        pitch_class_set: Valid pitch classes
        voice_count: Number of voices
        metre_numerator: Time signature numerator
        invertible_at: Inversion interval (10, 12, or None)

    Returns:
        (True, None) if all constraints satisfied.
        (False, violation_id) if any constraint violated.
        violation_id is one of: "H01", "H02", ..., "H11"

    Check order:
        H10 first (anchor preservation)
        H01 (pitch class)
        H02-H04 (parallels) for each voice pair
        H05-H06 (direct motion) for soprano vs each other voice
        H07-H09 (dissonance) for outer voices
        H11 (invertibility) if configured
    """
    from builder.slice import extract_slices

    # H10: Anchor preservation
    if not check_anchor_preserved(pitches, anchors):
        return (False, "H10")

    # H01: Pitch class membership
    for (offset, voice), pitch in pitches.items():
        if not check_pitch_class(pitch, pitch_class_set):
            return (False, "H01")

    # Extract slices for remaining checks
    slices = extract_slices(pitches, voice_count)
    outer_voices: tuple[int, int] = (0, voice_count - 1)

    # H02-H04: Parallel checks for each voice pair
    for voice_a in range(voice_count):
        for voice_b in range(voice_a + 1, voice_count):
            pairs = extract_slice_pairs(slices, voice_a, voice_b)
            for pair in pairs:
                if not check_no_parallel_unisons(pair, voice_a, voice_b):
                    return (False, "H02")
                if not check_no_parallel_fifths(pair, voice_a, voice_b):
                    return (False, "H03")
                if not check_no_parallel_octaves(pair, voice_a, voice_b):
                    return (False, "H04")

    # H05-H06: Direct motion for soprano vs each other voice
    soprano_voice: int = 0
    for other_voice in range(1, voice_count):
        pairs = extract_slice_pairs(slices, soprano_voice, other_voice)
        for pair in pairs:
            if not check_no_direct_fifth(pair, soprano_voice, other_voice):
                return (False, "H05")
            if not check_no_direct_octave(pair, soprano_voice, other_voice):
                return (False, "H06")

    # H07-H09: Dissonance treatment for outer voices
    for i, slice_ in enumerate(slices):
        if not check_strong_beat_consonance(slice_, outer_voices, metre_numerator):
            # Could be acceptable if prepared (H08) and resolved (H09)
            if not check_dissonance_prepared(slices, i, outer_voices, metre_numerator):
                return (False, "H08")
            if not check_dissonance_resolved(slices, i, outer_voices, metre_numerator):
                return (False, "H09")

    # H11: Invertibility
    if invertible_at is not None:
        for voice_a in range(voice_count):
            for voice_b in range(voice_a + 1, voice_count):
                if not check_invertible(slices, voice_a, voice_b, invertible_at):
                    return (False, "H11")

    return (True, None)
