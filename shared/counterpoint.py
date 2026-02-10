"""Counterpoint validation and correction utilities."""
from fractions import Fraction

from builder.types import Note
from shared.constants import CROSS_RELATION_PAIRS
from shared.key import Key


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
