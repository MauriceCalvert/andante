"""MusicXML output using music21.

Category B: File I/O operations.
"""
from fractions import Fraction
from pathlib import Path

from builder.types import Note, NoteFile

try:
    from music21 import clef, expressions, key, meter, note, stream, tempo
    MUSIC21_AVAILABLE: bool = True
except ImportError:
    MUSIC21_AVAILABLE = False

BASS_CLEF_THRESHOLD: int = 60


def write_musicxml_file(notes: NoteFile, path: Path, tonic: str = "C", mode: str = "major") -> bool:
    """Write notes to MusicXML file.
    
    Args:
        notes: NoteFile with soprano and bass
        path: Output path (will use .musicxml extension)
        tonic: Key tonic (e.g., "C", "G", "Bb")
        mode: Key mode ("major" or "minor")
    
    Returns:
        True if successful, False if music21 not available
    """
    if not MUSIC21_AVAILABLE:
        print(f"Warning: music21 not installed, cannot write {path}")
        return False
    score: stream.Score = _build_score(notes, tonic, mode)
    xml_path: Path = path.with_suffix(".musicxml")
    score.write("musicxml", fp=str(xml_path), makeNotation=True)
    return True


def _build_score(notes: NoteFile, tonic: str, mode: str) -> stream.Score:
    """Build music21 Score from NoteFile."""
    score: stream.Score = stream.Score()
    timenum, timeden = _parse_metre(notes.metre)
    all_offsets = [n.offset for n in notes.soprano] + [n.offset for n in notes.bass]
    min_offset = min(all_offsets) if all_offsets else Fraction(0)
    shift: Fraction = -min_offset if min_offset < 0 else Fraction(0)
    soprano_part: stream.Part = _build_part(
        notes.soprano,
        part_id="Soprano",
        timenum=timenum,
        timeden=timeden,
        tonic=tonic,
        mode=mode,
        bpm=notes.tempo,
        include_tempo=True,
        shift=shift,
    )
    score.insert(0, soprano_part)
    bass_part: stream.Part = _build_part(
        notes.bass,
        part_id="Bass",
        timenum=timenum,
        timeden=timeden,
        tonic=tonic,
        mode=mode,
        bpm=notes.tempo,
        include_tempo=False,
        shift=shift,
    )
    score.insert(0, bass_part)
    return score


def _build_part(
    notes: tuple[Note, ...],
    part_id: str,
    timenum: int,
    timeden: int,
    tonic: str,
    mode: str,
    bpm: int,
    include_tempo: bool,
    shift: Fraction = Fraction(0),
) -> stream.Part:
    """Build a single Part from notes."""
    part: stream.Part = stream.Part()
    part.id = part_id
    ts: meter.TimeSignature = meter.TimeSignature(f"{timenum}/{timeden}")
    part.insert(0, ts)
    ky: key.Key = key.Key(tonic, mode)
    part.insert(0, ky)
    if include_tempo:
        mm: tempo.MetronomeMark = tempo.MetronomeMark(number=bpm)
        part.insert(0, mm)
    if notes:
        avg_pitch: float = sum(n.pitch for n in notes) / len(notes)
        if avg_pitch < BASS_CLEF_THRESHOLD:
            part.insert(0, clef.BassClef())
        else:
            part.insert(0, clef.TrebleClef())
    for n in notes:
        m21_note: note.Note = note.Note(n.pitch)
        m21_note.quarterLength = float(n.duration) * 4
        if n.lyric:
            m21_note.lyric = n.lyric
        _clean_accidental(m21_note, ky)
        offset_quarters: float = float(n.offset + shift) * 4
        part.insert(offset_quarters, m21_note)
    part.makeRests(fillGaps=True, inPlace=True)
    part.makeMeasures(inPlace=True)
    return part


def _clean_accidental(m21_note: note.Note, ky: key.Key) -> None:
    """Remove redundant accidentals implied by key signature."""
    step: str = m21_note.pitch.step
    key_acc = ky.accidentalByStep(step)
    note_acc = m21_note.pitch.accidental
    if note_acc and key_acc:
        if note_acc.name == key_acc.name:
            m21_note.pitch.accidental = None
    elif note_acc and note_acc.name == "natural" and key_acc is None:
        m21_note.pitch.accidental = None


def _parse_metre(metre: str) -> tuple[int, int]:
    """Parse metre string like '4/4' to (numerator, denominator)."""
    parts: list[str] = metre.split("/")
    return int(parts[0]), int(parts[1])
