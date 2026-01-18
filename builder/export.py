"""Export tree to MIDI and .note files.
This module provides backward compatibility by delegating to the new adapters.
Functions here accept tree structures and convert to domain data before export.
"""
from fractions import Fraction
from pathlib import Path
from builder.adapters.file_export import (
    collect_notes_from_tree,
    export_midi_from_collected,
    export_note_from_collected,
)
from builder.domain.pitch_ops import compute_midi_from_diatonic, compute_note_name
from builder.tree import Node

def midi_to_note_name(midi: int) -> str:
    """Convert MIDI pitch to note name with octave (e.g., 60 -> C4).
    Backward compatibility wrapper for domain function.
    """
    if midi < 0 or midi > 127:
        return f"MIDI{midi}"
    return compute_note_name(midi)

def diatonic_to_midi(diatonic: int, key_offset: int = 0) -> int:
    """Convert diatonic pitch to MIDI.
    Backward compatibility wrapper for domain function.
    """
    midi: int = compute_midi_from_diatonic(diatonic, key_offset)
    if not 0 <= midi <= 127:
        raise ValueError(f"MIDI pitch {midi} out of range (diatonic={diatonic})")
    return midi

def collect_notes(tree: Node) -> list[tuple[str, int, Fraction, Fraction]]:
    """Walk tree and collect all notes.
    Backward compatibility wrapper for adapter function.
    Returns:
        List of (role, diatonic, duration, offset) tuples
    """
    return collect_notes_from_tree(tree)

def export_midi(
    tree: Node,
    output_path: str,
    key_offset: int = 0,
    tempo: int = 80,
    time_signature: tuple[int, int] = (4, 4),
) -> bool:
    """Export tree to MIDI file.
    Backward compatibility wrapper for adapter function.
    """
    if tempo <= 0:
        raise ValueError(f"tempo must be positive, got {tempo}")
    if len(time_signature) != 2:
        raise ValueError(f"time_signature must be (num, den), got {time_signature}")
    if time_signature[0] <= 0 or time_signature[1] <= 0:
        raise ValueError(f"time_signature values must be positive: {time_signature}")
    collected: list[tuple[str, int, Fraction, Fraction]] = collect_notes_from_tree(tree)
    if not collected:
        raise ValueError("No notes found in tree")
    return export_midi_from_collected(
        collected, output_path, key_offset, tempo, time_signature
    )

def export_note(
    tree: Node,
    output_path: str,
    key_offset: int = 0,
    time_signature: tuple[int, int] = (4, 4),
) -> bool:
    """Export tree to .note CSV file.
    Backward compatibility wrapper for adapter function.
    """
    collected: list[tuple[str, int, Fraction, Fraction]] = collect_notes_from_tree(tree)
    if not collected:
        return False
    return export_note_from_collected(
        collected, output_path, key_offset, time_signature
    )
