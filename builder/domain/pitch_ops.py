"""Pitch conversion operations.

Category A: Pure functions, no validation, no I/O.
Assumes all inputs are valid — validation happens in orchestrators.

Functions:
    compute_midi_from_diatonic — Convert diatonic to MIDI pitch
    compute_note_name          — Convert MIDI pitch to note name string
"""
from shared.constants import MAJOR_SCALE

NOTE_NAMES: tuple[str, ...] = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def compute_midi_from_diatonic(diatonic: int, key_offset: int = 0) -> int:
    """Convert diatonic pitch to MIDI.

    Diatonic pitch = octave * 7 + degree_index (0-6)
    - diatonic 28 = octave 4, degree 0 = C4 = MIDI 60
    - diatonic 32 = octave 4, degree 4 = G4 = MIDI 67

    Args:
        diatonic: Diatonic pitch number (octave * 7 + degree_index)
        key_offset: Semitones to transpose (0 for C major)

    Returns:
        MIDI pitch number (0-127)
    """
    octave: int = diatonic // 7
    degree_idx: int = diatonic % 7
    midi_base: int = (octave + 1) * 12
    return midi_base + MAJOR_SCALE[degree_idx] + key_offset


def compute_note_name(midi: int) -> str:
    """Convert MIDI pitch to note name with octave (e.g., 60 -> C4).

    Args:
        midi: MIDI pitch number

    Returns:
        Note name string like "C4", "F#5", etc.
    """
    octave: int = (midi // 12) - 1
    note_idx: int = midi % 12
    return f"{NOTE_NAMES[note_idx]}{octave}"
