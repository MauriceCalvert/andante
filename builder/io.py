"""I/O utilities for MIDI, MusicXML, and note file export.

Category A: Pure functions for formatting.
Category B: File I/O operations.

Note file format:
offset,midinote,duration,track,length,bar,beat,notename,lyric
"""
from fractions import Fraction
from pathlib import Path

from builder.types import Note, NoteFile
from shared.constants import NOTE_NAMES


def note_name(midi: int) -> str:
    """Convert MIDI number to note name (e.g., 60 → C4)."""
    octave: int = (midi // 12) - 1
    pc: int = midi % 12
    return f"{NOTE_NAMES[pc]}{octave}"


def bar_beat(offset: Fraction, metre: str, upbeat: Fraction = Fraction(0)) -> tuple[int, Fraction]:
    """Convert offset to bar number and beat position.
    
    Handles negative offsets for anacrusis (bar 0).
    For offset=-0.5 in 4/4: returns (0, 3) meaning bar 0, beat 3.
    """
    if metre == "4/4":
        beats_per_bar: int = 4
    elif metre == "3/4":
        beats_per_bar = 3
    else:
        beats_per_bar = 4
    total_beats: Fraction = offset * 4
    bar: int = int(total_beats // beats_per_bar) + 1
    beat_in_bar: Fraction = (total_beats % beats_per_bar) + 1
    return bar, beat_in_bar


def format_note_line(note: Note, metre: str, upbeat: Fraction = Fraction(0)) -> str:
    """Format a single note as CSV line."""
    bar, beat = bar_beat(note.offset, metre, upbeat)
    return (
        f"{float(note.offset)},"
        f"{note.pitch},"
        f"{note.duration},"
        f"{note.voice},"
        f","
        f"{bar},"
        f"{float(beat)},"
        f"{note_name(note.pitch)},"
        f"{note.lyric}"
    )


def write_note_file(notes: NoteFile, path: Path) -> None:
    """Write notes to .note CSV file."""
    lines: list[str] = ["offset,midinote,duration,track,length,bar,beat,notename,lyric"]
    all_notes: list[Note] = []
    all_notes.extend(notes.soprano)
    all_notes.extend(notes.bass)
    all_notes.sort(key=lambda n: (float(n.offset), n.voice))
    for note in all_notes:
        lines.append(format_note_line(note, notes.metre, notes.upbeat))
    path.write_text("\n".join(lines), encoding="utf-8")


def write_midi_file(notes: NoteFile, path: Path) -> None:
    """Write notes to MIDI file.
    
    Auto-shifts all notes forward if any have negative offsets (anacrusis).
    """
    from shared.midi_writer import SimpleNote, write_midi_notes
    all_offsets: list[Fraction] = [n.offset for n in notes.soprano] + [n.offset for n in notes.bass]
    min_offset: Fraction = min(all_offsets) if all_offsets else Fraction(0)
    shift: Fraction = -min_offset if min_offset < 0 else Fraction(0)
    midi_notes: list[SimpleNote] = []
    for note in notes.soprano:
        midi_notes.append(SimpleNote(
            pitch=note.pitch,
            offset=float(note.offset + shift),
            duration=float(note.duration),
            velocity=80,
            track=0,
        ))
    for note in notes.bass:
        midi_notes.append(SimpleNote(
            pitch=note.pitch,
            offset=float(note.offset + shift),
            duration=float(note.duration),
            velocity=80,
            track=3,
        ))
    time_sig = _parse_time_signature(notes.metre)
    write_midi_notes(str(path), midi_notes, tempo=notes.tempo, time_signature=time_sig)


def _parse_time_signature(metre: str) -> tuple[int, int]:
    """Parse metre string to time signature tuple."""
    parts = metre.split("/")
    return (int(parts[0]), int(parts[1]))


def write_musicxml_file(notes: NoteFile, path: Path, tonic: str = "C", mode: str = "major") -> bool:
    """Write notes to MusicXML file.
    
    Returns True if successful, False if music21 not available.
    """
    from builder.musicxml_writer import write_musicxml_file as _write_xml
    return _write_xml(notes, path, tonic, mode)
