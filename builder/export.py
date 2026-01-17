"""Export tree to MIDI and .note files."""
from fractions import Fraction
from pathlib import Path
from typing import Any

from builder.tree import Node
from shared.constants import MAJOR_SCALE, VOICE_TRACKS
from shared.midi_writer import SimpleNote, write_midi_notes

# Note names for .note file output
NOTE_NAMES: tuple[str, ...] = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi_to_note_name(midi: int) -> str:
    """Convert MIDI pitch to note name with octave (e.g., 60 -> C4)."""
    if midi < 0 or midi > 127:
        return f"MIDI{midi}"
    octave: int = (midi // 12) - 1
    note_idx: int = midi % 12
    return f"{NOTE_NAMES[note_idx]}{octave}"


def diatonic_to_midi(diatonic: int, key_offset: int = 0) -> int:
    """Convert diatonic pitch to MIDI.

    Diatonic pitch = octave * 7 + degree_index (0-6)
    - diatonic 28 = octave 4, degree 0 = C4 = MIDI 60
    - diatonic 32 = octave 4, degree 4 = G4 = MIDI 67

    Args:
        diatonic: Diatonic pitch number
        key_offset: Semitones to transpose (0 for C major)

    Returns:
        MIDI pitch number (0-127)
    """
    octave: int = diatonic // 7
    degree_idx: int = diatonic % 7
    midi_base: int = (octave + 1) * 12
    midi: int = midi_base + MAJOR_SCALE[degree_idx] + key_offset
    assert 0 <= midi <= 127, f"MIDI pitch {midi} out of range (diatonic={diatonic}, key_offset={key_offset})"
    return midi


def collect_notes(tree: Node) -> list[tuple[str, int, Fraction, Fraction]]:
    """Walk tree and collect all notes.

    Returns:
        List of (role, diatonic, duration, offset) tuples
    """
    notes: list[tuple[str, int, Fraction, Fraction]] = []
    _collect_notes_recursive(tree, Fraction(0), notes)
    return notes


def _collect_notes_recursive(
    node: Node,
    bar_offset: Fraction,
    notes: list[tuple[str, int, Fraction, Fraction]],
    current_role: str | None = None
) -> Fraction:
    """Recursively collect notes from tree.

    Returns the offset after processing this node's subtree.
    """
    if node.key == 'bars':
        offset: Fraction = bar_offset
        bar_node: Node
        for bar_node in node.children:
            offset = _collect_notes_recursive(bar_node, offset, notes, current_role)
        return offset

    if isinstance(node.key, int) and 'voices' in node:
        # Calculate bar duration from first voice's notes (all voices have same duration)
        bar_duration: Fraction = Fraction(0)
        voice_node: Node
        for voice_node in node['voices'].children:
            _collect_notes_recursive(voice_node, bar_offset, notes, current_role)
            # Sum durations from first voice only (others are parallel)
            if bar_duration == 0 and 'notes' in voice_node:
                note_node: Node
                for note_node in voice_node['notes'].children:
                    assert 'duration' in note_node, f"Note missing 'duration' at {note_node.path_string()}"
                    dur_val: Any = note_node['duration'].value
                    assert isinstance(dur_val, (int, float, str)), (
                        f"Duration must be numeric or string at {note_node.path_string()}, got {type(dur_val).__name__}"
                    )
                    bar_duration += Fraction(dur_val)
        return bar_offset + bar_duration

    if isinstance(node.key, int) and 'role' in node:
        role_val: Any = node['role'].value
        assert isinstance(role_val, str), f"Role must be string at {node.path_string()}, got {type(role_val).__name__}"
        role: str = role_val
        if 'notes' in node:
            offset = bar_offset
            note_node: Node
            for note_node in node['notes'].children:
                assert 'diatonic' in note_node, f"Note missing 'diatonic' at {note_node.path_string()}"
                assert 'duration' in note_node, f"Note missing 'duration' at {note_node.path_string()}"
                diatonic_val: Any = note_node['diatonic'].value
                assert isinstance(diatonic_val, int), (
                    f"Diatonic must be int at {note_node.path_string()}, got {type(diatonic_val).__name__}"
                )
                diatonic: int = diatonic_val
                dur_val: Any = note_node['duration'].value
                assert isinstance(dur_val, (int, float, str)), (
                    f"Duration must be numeric or string at {note_node.path_string()}, got {type(dur_val).__name__}"
                )
                dur: Fraction = Fraction(dur_val)
                notes.append((role, diatonic, dur, offset))
                offset += dur
        return bar_offset

    child: Node
    for child in node.children:
        bar_offset = _collect_notes_recursive(child, bar_offset, notes, current_role)

    return bar_offset


def export_midi(
    tree: Node,
    output_path: str,
    key_offset: int = 0,
    tempo: int = 80,
    time_signature: tuple[int, int] = (4, 4),
) -> bool:
    """Export tree to MIDI file.

    Args:
        tree: Elaborated tree with notes at leaves
        output_path: Output file path
        key_offset: Semitones to transpose (0 for C major)
        tempo: BPM
        time_signature: Tuple of (numerator, denominator)

    Returns:
        True if successful
    """
    assert tempo > 0, f"tempo must be positive, got {tempo}"
    assert len(time_signature) == 2, f"time_signature must be (num, den), got {time_signature}"
    assert time_signature[0] > 0, f"time_signature numerator must be positive, got {time_signature[0]}"
    assert time_signature[1] > 0, f"time_signature denominator must be positive, got {time_signature[1]}"

    collected: list[tuple[str, int, Fraction, Fraction]] = collect_notes(tree)
    assert collected, f"No notes found in tree"

    simple_notes: list[SimpleNote] = []
    role: str
    diatonic: int
    duration: Fraction
    offset: Fraction
    for role, diatonic, duration, offset in collected:
        midi_pitch: int = diatonic_to_midi(diatonic, key_offset)
        assert role in VOICE_TRACKS, f"Unknown voice role: '{role}'. Valid: {sorted(VOICE_TRACKS.keys())}"
        track: int = VOICE_TRACKS[role]
        simple_notes.append(SimpleNote(
            pitch=midi_pitch,
            offset=float(offset),
            duration=float(duration),
            velocity=80,
            track=track,
        ))

    return write_midi_notes(
        output_path,
        simple_notes,
        tempo=tempo,
        time_signature=time_signature,
    )


def export_note(
    tree: Node,
    output_path: str,
    key_offset: int = 0,
    time_signature: tuple[int, int] = (4, 4),
) -> bool:
    """Export tree to .note CSV file.

    Args:
        tree: Elaborated tree with notes at leaves
        output_path: Output file path (will add .note extension)
        key_offset: Semitones to transpose (0 for C major)
        time_signature: Tuple of (numerator, denominator)

    Returns:
        True if successful
    """
    collected: list[tuple[str, int, Fraction, Fraction]] = collect_notes(tree)
    if not collected:
        return False

    bar_duration: Fraction = Fraction(time_signature[0], time_signature[1])

    # Sort by offset, then by descending pitch (soprano before bass at same offset)
    sorted_notes: list[tuple[str, int, Fraction, Fraction]] = sorted(
        collected,
        key=lambda x: (x[3], -x[1])  # (offset, -diatonic)
    )

    lines: list[str] = ["Offset,midiNote,Duration,track,Length,bar,beat,noteName,lyric,velocity"]

    role: str
    diatonic: int
    duration: Fraction
    offset: Fraction
    for role, diatonic, duration, offset in sorted_notes:
        midi_pitch: int = diatonic_to_midi(diatonic, key_offset)
        track: int = VOICE_TRACKS.get(role, 0)

        # Calculate bar and beat (1-indexed)
        bar: int = int(offset // bar_duration) + 1
        beat_offset: Fraction = offset % bar_duration
        beat: float = float(beat_offset / Fraction(1, time_signature[1])) + 1

        note_name: str = midi_to_note_name(midi_pitch)

        line: str = (
            f"{float(offset):.6g},{midi_pitch},{float(duration):.6g},{track},"
            f",{bar},{beat:.4g},{note_name},,80"
        )
        lines.append(line)

    path: Path = Path(output_path).with_suffix(".note")
    path.write_text("\n".join(lines))
    return True
