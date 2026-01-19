"""Export domain data to MIDI and .note files.
Adapters translate domain data to file formats.
This module accepts domain data (collected notes), not tree structures.
SIZE: 157 lines — Contains three distinct responsibilities: MIDI export,
.note CSV export, and tree collection. Each requires complete implementation.
Splitting would create artificial boundaries in the export pipeline.
Functions:
    export_midi_from_collected — Write collected notes to MIDI file
    export_note_from_collected — Write collected notes to .note CSV file
    collect_notes_from_tree    — Extract notes from tree as domain data
"""
from fractions import Fraction
from pathlib import Path
from builder.domain.pitch_ops import compute_midi_from_diatonic, compute_note_name
from builder.tree import Node
from builder.types import CollectedNote
from shared.constants import VOICE_TRACKS
from shared.midi_writer import SimpleNote, write_midi_notes

def export_midi_from_collected(
    collected: list[CollectedNote],
    output_path: str,
    key_offset: int = 0,
    tempo: int = 80,
    time_signature: tuple[int, int] = (4, 4),
) -> bool:
    """Export collected notes to MIDI file.
    Args:
        collected: List of CollectedNote
        output_path: Output file path
        key_offset: Semitones to transpose (0 for C major)
        tempo: BPM
        time_signature: Tuple of (numerator, denominator)
    Returns:
        True if successful
    """
    simple_notes: list[SimpleNote] = []
    for note in collected:
        midi_pitch: int = compute_midi_from_diatonic(note.diatonic, key_offset)
        track: int = VOICE_TRACKS.get(note.role, 0)
        simple_notes.append(
            SimpleNote(
                pitch=midi_pitch,
                offset=float(note.offset),
                duration=float(note.duration),
                velocity=80,
                track=track,
            )
        )
    return write_midi_notes(
        output_path,
        simple_notes,
        tempo=tempo,
        time_signature=time_signature,
    )

def export_note_from_collected(
    collected: list[CollectedNote],
    output_path: str,
    key_offset: int = 0,
    time_signature: tuple[int, int] = (4, 4),
) -> bool:
    """Export collected notes to .note CSV file.
    Args:
        collected: List of CollectedNote
        output_path: Output file path
        key_offset: Semitones to transpose (0 for C major)
        time_signature: Tuple of (numerator, denominator)
    Returns:
        True if successful
    """
    if not collected:
        return False
    bar_duration: Fraction = Fraction(time_signature[0], time_signature[1])
    sorted_notes: list[CollectedNote] = sorted(
        collected, key=lambda n: (n.offset, -n.diatonic)
    )
    lines: list[str] = ["Offset,midiNote,Duration,track,Length,bar,beat,noteName,lyric"]
    for note in sorted_notes:
        midi_pitch: int = compute_midi_from_diatonic(note.diatonic, key_offset)
        track: int = VOICE_TRACKS.get(note.role, 0)
        bar: int = int(note.offset // bar_duration) + 1
        beat_offset: Fraction = note.offset % bar_duration
        beat: float = float(beat_offset / Fraction(1, time_signature[1])) + 1
        note_name: str = compute_note_name(midi_pitch)
        line: str = (
            f"{float(note.offset):.6g},{midi_pitch},{float(note.duration):.6g},{track},"
            f",{bar},{beat:.4g},{note_name}"
        )
        lines.append(line)
    path: Path = Path(output_path).with_suffix(".note")
    path.write_text("\n".join(lines))
    return True

def collect_notes_from_tree(tree: Node) -> list[CollectedNote]:
    """Walk tree and collect all notes as domain data.
    Args:
        tree: Elaborated tree with notes at leaves
    Returns:
        List of CollectedNote
    """
    # Extract bar duration from frame.metre
    bar_duration: Fraction = Fraction(1)  # default 4/4
    if "frame" in tree and "metre" in tree["frame"]:
        metre_str: str = tree["frame"]["metre"].value
        parts: list[str] = metre_str.split("/")
        bar_duration = Fraction(int(parts[0]), int(parts[1]))
    notes: list[CollectedNote] = []
    _collect_recursive(tree, Fraction(0), bar_duration, notes)
    return notes

def _collect_recursive(
    node: Node,
    bar_offset: Fraction,
    bar_duration: Fraction,
    notes: list[CollectedNote],
) -> Fraction:
    """Recursively collect notes from tree."""
    if node.key == "bars":
        offset: Fraction = bar_offset
        for bar_node in node.children:
            offset = _collect_recursive(bar_node, offset, bar_duration, notes)
        return offset
    if isinstance(node.key, int) and "voices" in node:
        for voice_node in node["voices"].children:
            _collect_recursive(voice_node, bar_offset, bar_duration, notes)
        return bar_offset + bar_duration
    if isinstance(node.key, int) and "role" in node:
        role: str = node["role"].value
        if "notes" in node:
            offset = bar_offset
            for note_node in node["notes"].children:
                diatonic: int = note_node["diatonic"].value
                dur: Fraction = Fraction(note_node["duration"].value)
                notes.append(CollectedNote(role=role, diatonic=diatonic, duration=dur, offset=offset))
                offset += dur
        return bar_offset
    for child in node.children:
        bar_offset = _collect_recursive(child, bar_offset, bar_duration, notes)
    return bar_offset
