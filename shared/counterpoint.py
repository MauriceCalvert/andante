"""Counterpoint validation and correction utilities."""
from fractions import Fraction

from builder.types import Note
from shared.constants import (
    CROSS_RELATION_PAIRS,
    PERFECT_INTERVALS,
    SKIP_SEMITONES,
    STEP_SEMITONES,
    UGLY_INTERVALS,
)
from shared.key import Key


def find_non_parallel_pitch(
    pitch: int,
    offset: Fraction,
    other_voice_notes: tuple[Note, ...],
    own_previous_note: Note | None,
    tolerance: frozenset[int],
    key: Key,
    pitch_range: tuple[int, int],
) -> int | None:
    """Suggest an alternative pitch that avoids parallel perfects."""
    if not has_parallel_perfect(
        pitch=pitch,
        offset=offset,
        other_voice_notes=other_voice_notes,
        own_previous_note=own_previous_note,
        tolerance=tolerance,
    ):
        return pitch

    # Try diatonic ±1, ±2 from key
    for step_dir in (-1, +1, -2, +2):
        alt: int = key.diatonic_step(midi=pitch, steps=step_dir)

        if alt < pitch_range[0] or alt > pitch_range[1]:
            continue

        if not has_parallel_perfect(
            pitch=alt,
            offset=offset,
            other_voice_notes=other_voice_notes,
            own_previous_note=own_previous_note,
            tolerance=tolerance,
        ):
            return alt

    # Try octave ±12
    for octave_shift in (-12, +12):
        alt = pitch + octave_shift

        if alt < pitch_range[0] or alt > pitch_range[1]:
            continue

        if not has_parallel_perfect(
            pitch=alt,
            offset=offset,
            other_voice_notes=other_voice_notes,
            own_previous_note=own_previous_note,
            tolerance=tolerance,
        ):
            return alt

    return None


def has_consecutive_leaps(
    prev_prev_pitch: int | None,
    prev_pitch: int,
    candidate_pitch: int,
    threshold: int = SKIP_SEMITONES,
) -> bool:
    """Return True if both intervals exceed threshold in same direction."""
    if prev_prev_pitch is None:
        return False

    int1: int = prev_pitch - prev_prev_pitch
    int2: int = candidate_pitch - prev_pitch

    if abs(int1) <= threshold or abs(int2) <= threshold:
        return False

    same_direction: bool = (int1 > 0) == (int2 > 0)
    return same_direction


def has_cross_relation(
    pitch: int,
    other_notes: tuple[Note, ...],
    offset: Fraction,
    beat_unit: Fraction,
) -> bool:
    """Return True if pitch creates a cross-relation with nearby notes in other voice.

    A cross-relation occurs when the same letter-name is chromatically altered
    between voices within a beat (e.g., F4 in one voice against F#3 in the other).
    This is checked by comparing pitch classes within a beat_unit window.
    """
    pc: int = pitch % 12
    for note in other_notes:
        if abs(note.offset - offset) <= beat_unit:
            other_pc: int = note.pitch % 12
            pair: tuple[int, int] = (min(pc, other_pc), max(pc, other_pc))
            if pair in CROSS_RELATION_PAIRS:
                return True
    return False


def prevent_cross_relation(
    pitch: int,
    other_notes: tuple[Note, ...],
    offset: Fraction,
    beat_unit: Fraction,
    key: Key,
    pitch_range: tuple[int, int],
    ceiling: int | None,
) -> int:
    """Select an alternative pitch to avoid cross-relation with nearby notes in other voice.

    Part of the generation/selection flow (D010: generators prevent).
    Returns original pitch if no cross-relation exists or no alternative found.

    Args:
        pitch: The candidate pitch to check
        other_notes: Notes from the other voice to check against
        offset: The offset of the candidate pitch
        beat_unit: The beat unit for determining "nearby" (within one beat)
        key: The current key for diatonic stepping
        pitch_range: The allowed MIDI range (low, high) for this voice
        ceiling: Optional upper bound (used when bass must stay below soprano)

    Returns:
        Either the original pitch (if no cross-relation) or a diatonic step away
        that avoids the cross-relation. If no alternative found, returns original.
    """
    if not has_cross_relation(
        pitch=pitch,
        other_notes=other_notes,
        offset=offset,
        beat_unit=beat_unit,
    ):
        return pitch

    # Try diatonic step -1, then +1
    for step_dir in (-1, +1):
        alt: int = key.diatonic_step(midi=pitch, steps=step_dir)

        # Check range constraints
        if alt < pitch_range[0] or alt > pitch_range[1]:
            continue

        # Check optional ceiling constraint
        if ceiling is not None and alt > ceiling:
            continue

        # Check if alternative avoids cross-relation
        if not has_cross_relation(
            pitch=alt,
            other_notes=other_notes,
            offset=offset,
            beat_unit=beat_unit,
        ):
            return alt

    # No alternative found — return original pitch (rare structural clash)
    return pitch


def has_parallel_perfect(
    pitch: int,
    offset: Fraction,
    other_voice_notes: tuple[Note, ...],
    own_previous_note: Note | None,
    tolerance: frozenset[int] = frozenset(),
) -> bool:
    """Return True if parallel perfect interval by similar motion detected."""
    if own_previous_note is None:
        return False

    # Find other voice's pitch at candidate offset
    other_pitch_at_offset: int | None = None
    for note in other_voice_notes:
        if note.offset == offset:
            other_pitch_at_offset = note.pitch
            break

    if other_pitch_at_offset is None:
        return False  # No common onset

    # Find other voice's pitch at own_previous_note's offset
    other_pitch_at_previous: int | None = None
    for note in other_voice_notes:
        if note.offset == own_previous_note.offset:
            other_pitch_at_previous = note.pitch
            break

    if other_pitch_at_previous is None:
        return False  # No previous common onset

    # Compute simple intervals (mod 12)
    prev_ic: int = abs(own_previous_note.pitch - other_pitch_at_previous) % 12
    curr_ic: int = abs(pitch - other_pitch_at_offset) % 12

    # Check if both intervals are perfect and equal (after subtracting tolerance)
    effective_perfects: frozenset[int] = PERFECT_INTERVALS - tolerance
    if prev_ic not in effective_perfects or curr_ic != prev_ic:
        return False

    # Check motion type: both must move in same direction (similar motion)
    own_motion: int = pitch - own_previous_note.pitch
    other_motion: int = other_pitch_at_offset - other_pitch_at_previous

    if own_motion == 0 or other_motion == 0:
        return False  # Static motion — not parallel

    same_direction: bool = (own_motion > 0) == (other_motion > 0)
    return same_direction


def is_cross_bar_repetition(
    pitch: int,
    offset: Fraction,
    previous_note: Note | None,
    bar_length: Fraction,
    phrase_start: Fraction,
    structural_offsets: frozenset[Fraction],
) -> bool:
    """Return True if pitch repeats across bar boundary at non-structural offsets."""
    if previous_note is None:
        return False

    if pitch != previous_note.pitch:
        return False

    # Check if either offset is structural — exempt
    if offset in structural_offsets or previous_note.offset in structural_offsets:
        return False

    # Compute bar numbers
    prev_bar: int = int((previous_note.offset - phrase_start) // bar_length)
    curr_bar: int = int((offset - phrase_start) // bar_length)

    return prev_bar != curr_bar


def is_ugly_melodic_interval(
    from_pitch: int,
    to_pitch: int,
) -> bool:
    """Return True if interval is augmented 2nd, tritone, or major 7th."""
    interval: int = abs(to_pitch - from_pitch)
    simple: int = interval % 12
    return simple in UGLY_INTERVALS and interval > STEP_SEMITONES


def needs_step_recovery(
    previous_notes: tuple[Note, ...],
    candidate_pitch: int,
    structural_offsets: frozenset[Fraction],
) -> bool:
    """Return True if last interval was leap without contrary stepwise recovery."""
    if len(previous_notes) < 1:
        return False

    last_note: Note = previous_notes[-1]

    # Check if we have a note before the last
    if len(previous_notes) < 2:
        return False

    prev_note: Note = previous_notes[-2]

    # Last interval
    last_interval: int = abs(last_note.pitch - prev_note.pitch)

    # If last interval was a step, no recovery needed
    if last_interval <= STEP_SEMITONES:
        return False

    # Exempt structural-to-structural leaps
    if prev_note.offset in structural_offsets and last_note.offset in structural_offsets:
        return False

    # Check if candidate provides contrary stepwise recovery
    candidate_interval: int = abs(candidate_pitch - last_note.pitch)
    if candidate_interval > STEP_SEMITONES:
        return True  # Not a step

    # Check if contrary direction
    leap_direction: int = last_note.pitch - prev_note.pitch
    recovery_direction: int = candidate_pitch - last_note.pitch

    if (leap_direction > 0) != (recovery_direction > 0):
        return False  # Contrary step — recovery provided

    return True  # Same direction or static — no recovery


def would_cross_voice(
    pitch: int,
    other_voice_pitch: int,
    voice_id: int,
    other_voice_id: int,
) -> bool:
    """Return True if pitch would cross the other voice."""
    if voice_id == other_voice_id:
        return False

    # Lower voice_id means higher tessitura
    if voice_id < other_voice_id:
        # This voice should be above
        return pitch < other_voice_pitch
    else:
        # This voice should be below
        return pitch > other_voice_pitch
