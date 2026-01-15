"""Contour dynamics model for humanisation.

Higher notes are naturally played slightly louder.
"""
from engine.note import Note
from humanisation.context.types import DynamicsProfile


def compute_contour_offset(
    notes: list[Note],
    profile: DynamicsProfile,
) -> list[int]:
    """Compute velocity offset based on pitch height.

    Higher notes are naturally louder on keyboard instruments
    due to finger/voice tendency. Maps typical range (C4-C6)
    to the configured contour range.

    Args:
        notes: Original Note objects (needed for pitch)
        profile: Dynamics parameters

    Returns:
        List of velocity offsets (integers)
    """
    if not notes:
        return []

    offsets: list[int] = []
    contour_range = profile.contour_range

    # Reference pitch: C4 = MIDI 60
    ref_pitch = 60
    # Range: two octaves (24 semitones)
    pitch_range = 24

    for note in notes:
        # Normalize pitch to 0-1 range relative to C4-C6
        normalized = (note.midiNote - ref_pitch) / pitch_range
        # Clamp to reasonable bounds
        normalized = max(-1.0, min(1.0, normalized))

        # Map to velocity offset
        offset = int(normalized * contour_range)
        offsets.append(offset)

    return offsets
