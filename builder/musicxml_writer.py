"""MusicXML output using music21.

Category B: File I/O operations.
"""
from fractions import Fraction
from pathlib import Path

from builder.types import Composition, Note
from shared.constants import BASS_CLEF_THRESHOLD

try:
    from music21 import clef, key, meter, note, stream, tempo
    from music21.note import Lyric
    MUSIC21_AVAILABLE: bool = True
except ImportError:
    MUSIC21_AVAILABLE = False


def write_musicxml(comp: Composition, path: Path, tonic: str = "C", mode: str = "major") -> bool:
    """Write composition to MusicXML file."""
    if not MUSIC21_AVAILABLE:
        print(f"Warning: music21 not installed, cannot write {path}")
        return False
    score: stream.Score = _build_score(comp=comp, tonic=tonic, mode=mode)
    xml_path: Path = path.with_suffix(".musicxml")
    score.write("musicxml", fp=str(xml_path), makeNotation=True)
    return True


def _build_score(comp: Composition, tonic: str, mode: str) -> stream.Score:
    """Build music21 Score from Composition."""
    score: stream.Score = stream.Score()
    timenum, timeden = _parse_metre(metre=comp.metre)
    all_notes: list[Note] = []
    for voice_notes in comp.voices.values():
        all_notes.extend(voice_notes)
    all_offsets: list[Fraction] = [n.offset for n in all_notes]
    min_offset: Fraction = min(all_offsets) if all_offsets else Fraction(0)
    shift: Fraction = -min_offset if min_offset < 0 else Fraction(0)
    first_voice: bool = True
    for voice_id, voice_notes in comp.voices.items():
        part: stream.Part = _build_part(
            notes=voice_notes,
            part_id=voice_id.capitalize(),
            timenum=timenum,
            timeden=timeden,
            tonic=tonic,
            mode=mode,
            bpm=comp.tempo,
            include_tempo=first_voice,
            shift=shift,
        )
        score.insert(0, part)
        first_voice = False
    return score


def _add_stacked_lyrics(m21_note: note.Note, lyric_text: str) -> None:
    """Add multiple lyrics as stacked verses."""
    if not lyric_text:
        return
    parts: list[str] = lyric_text.split("/")
    for i, part in enumerate(parts):
        if part:
            lyric_obj = Lyric(text=part, number=i + 1)
            m21_note.lyrics.append(lyric_obj)


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
            _add_stacked_lyrics(m21_note=m21_note, lyric_text=n.lyric)
        _clean_accidental(m21_note=m21_note, ky=ky)
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
