"""I/O utilities for MIDI and note file export.

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


def bar_beat(offset: Fraction, metre: str) -> tuple[int, Fraction]:
    """Convert offset to bar number and beat position."""
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


def format_note_line(note: Note, metre: str) -> str:
    """Format a single note as CSV line."""
    bar, beat = bar_beat(note.offset, metre)
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
        lines.append(format_note_line(note, notes.metre))
    path.write_text("\n".join(lines), encoding="utf-8")


def write_midi_file(notes: NoteFile, path: Path) -> None:
    """Write notes to MIDI file."""
    from shared.midi_writer import SimpleNote, write_midi_notes
    midi_notes: list[SimpleNote] = []
    for note in notes.soprano:
        midi_notes.append(SimpleNote(
            pitch=note.pitch,
            offset=float(note.offset),
            duration=float(note.duration),
            velocity=80,
            track=0,
        ))
    for note in notes.bass:
        midi_notes.append(SimpleNote(
            pitch=note.pitch,
            offset=float(note.offset),
            duration=float(note.duration),
            velocity=80,
            track=1,
        ))
    write_midi_notes(str(path), midi_notes, tempo=notes.tempo)
