"""I/O utilities for MIDI, MusicXML, and note file export.

Category A: Pure functions for formatting.
Category B: File I/O operations.

Note file writing is in builder/note_writer.py.
"""
from fractions import Fraction
from pathlib import Path

from builder.types import Composition, Note
from shared.constants import METRE_BAR_LENGTH
from shared.music_math import parse_metre
from shared.pitch import midi_to_name as note_name


def bar_beat(offset: Fraction, metre: str, upbeat: Fraction = Fraction(0)) -> tuple[int, Fraction]:
    """Convert offset to bar number and beat position.

    Subtracts upbeat before computing so bar/beat labels match the
    musical score (bar 0 = anacrusis, bar 1 = first full bar).
    """
    assert metre in METRE_BAR_LENGTH, (
        f"Unknown metre '{metre}' in bar_beat(); "
        f"known metres: {sorted(METRE_BAR_LENGTH.keys())}"
    )
    num_str, den_str = metre.split("/")
    beats_per_bar: int = int(num_str)
    beat_value: int = int(den_str)
    total_beats: Fraction = (offset - upbeat) * beat_value
    bar: int = int(total_beats // beats_per_bar) + 1
    beat_in_bar: Fraction = (total_beats % beats_per_bar) + 1
    return bar, beat_in_bar


def all_notes_sorted(comp: Composition) -> list[Note]:
    """Collect all notes from all voices, sorted by offset then MIDI descending."""
    all_notes: list[Note] = []
    for voice_notes in comp.voices.values():
        all_notes.extend(voice_notes)
    all_notes.sort(key=lambda n: (float(n.offset), -n.pitch))
    return all_notes


def write_midi_file(
    comp: Composition,
    path: Path,
    *,
    tonic: str = "C",
    mode: str = "major",
) -> None:
    """Write notes to MIDI file."""
    from shared.midi_writer import SimpleNote, write_midi_notes
    all_notes: list[Note] = all_notes_sorted(comp=comp)
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
    _bar_len, _beat_unit = parse_metre(metre=comp.metre)
    time_sig: tuple[int, int] = (int(_bar_len / _beat_unit), int(1 / _beat_unit))
    write_midi_notes(
        path=str(path),
        notes=midi_notes,
        tempo=comp.tempo,
        time_signature=time_sig,
        tonic=tonic,
        mode=mode,
    )


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
