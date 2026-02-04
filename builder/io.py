"""I/O utilities for MIDI, MusicXML, and note file export.

Category A: Pure functions for formatting.
Category B: File I/O operations.

Note file format:
offset,midinote,duration,track,length,bar,beat,notename,lyric
"""
from fractions import Fraction
from pathlib import Path

from builder.types import Composition, Note
from shared.constants import NOTE_NAMES


def note_name(midi: int) -> str:
    """Convert MIDI number to note name (e.g., 60 → C4)."""
    octave: int = (midi // 12) - 1
    pc: int = midi % 12
    return f"{NOTE_NAMES[pc]}{octave}"


def bar_beat(offset: Fraction, metre: str, upbeat: Fraction = Fraction(0)) -> tuple[int, Fraction]:
    """Convert offset to bar number and beat position.

    Subtracts upbeat before computing so bar/beat labels match the
    musical score (bar 0 = anacrusis, bar 1 = first full bar).
    """
    if metre == "4/4":
        beats_per_bar: int = 4
    elif metre == "3/4":
        beats_per_bar = 3
    else:
        beats_per_bar = 4
    total_beats: Fraction = (offset - upbeat) * 4
    bar: int = int(total_beats // beats_per_bar) + 1
    beat_in_bar: Fraction = (total_beats % beats_per_bar) + 1
    return bar, beat_in_bar


def format_note_line(note: Note, metre: str, upbeat: Fraction = Fraction(0)) -> str:
    """Format a single note as CSV line."""
    bar, beat = bar_beat(offset=note.offset, metre=metre, upbeat=upbeat)
    return (
        f"{float(note.offset)},"
        f"{note.pitch},"
        f"{note.duration},"
        f"{note.voice},"
        f","
        f"{bar},"
        f"{float(beat)},"
        f"{note_name(midi=note.pitch)}"
    )


def _all_notes_sorted(comp: Composition) -> list[Note]:
    """Collect all notes from all voices, sorted by offset then voice."""
    all_notes: list[Note] = []
    for voice_notes in comp.voices.values():
        all_notes.extend(voice_notes)
    all_notes.sort(key=lambda n: (float(n.offset), n.voice))
    return all_notes


def write_note_file(comp: Composition, path: Path) -> None:
    """Write notes to .note CSV file."""
    lines: list[str] = ["offset,midinote,duration,track,length,bar,beat,notename"]
    for note in _all_notes_sorted(comp=comp):
        lines.append(format_note_line(note=note, metre=comp.metre, upbeat=comp.upbeat))
    path.write_text("\n".join(lines), encoding="utf-8")


def write_midi_file(
    comp: Composition,
    path: Path,
    *,
    tonic: str = "C",
    mode: str = "major",
) -> None:
    """Write notes to MIDI file."""
    from shared.midi_writer import SimpleNote, write_midi_notes
    all_notes: list[Note] = _all_notes_sorted(comp=comp)
    all_offsets: list[Fraction] = [n.offset for n in all_notes]
    min_offset: Fraction = min(all_offsets) if all_offsets else Fraction(0)
    shift: Fraction = -min_offset if min_offset < 0 else Fraction(0)
    midi_notes: list[SimpleNote] = []
    for note in all_notes:
        midi_notes.append(SimpleNote(
            pitch=note.pitch,
            offset=float(note.offset + shift),
            duration=float(note.duration),
            velocity=80,
            track=note.voice,
        ))
    time_sig = _parse_time_signature(metre=comp.metre)
    write_midi_notes(
        path=str(path),
        notes=midi_notes,
        tempo=comp.tempo,
        time_signature=time_sig,
        tonic=tonic,
        mode=mode,
    )


def _parse_time_signature(metre: str) -> tuple[int, int]:
    """Parse metre string to time signature tuple."""
    parts = metre.split("/")
    return (int(parts[0]), int(parts[1]))


def write_musicxml_file(
    comp: Composition,
    path: Path,
    *,
    tonic: str = "C",
    mode: str = "major",
) -> bool:
    """Write notes to MusicXML file."""
    from builder.musicxml_writer import write_musicxml
    return write_musicxml(comp=comp, path=path, tonic=tonic, mode=mode)
