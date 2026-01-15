"""Output interface using music21 for MIDI and MusicXML export."""
from abc import ABC, abstractmethod
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING

from music21 import clef, expressions, instrument, key, meter, note, stream, tempo

from engine.note import Note

MIDI_REST: int = 20
NOTE_NAMES: tuple[str, ...] = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi_to_note_octave(midi_number: int, tonic: str | None = None, mode: str | None = None) -> str:
    """Convert MIDI number to note name with octave."""
    if midi_number < 0 or midi_number > 127:
        return f"MIDI{midi_number}"
    octave: int = (midi_number // 12) - 1
    note_idx: int = midi_number % 12
    return f"{NOTE_NAMES[note_idx]}{octave}"

if TYPE_CHECKING:
    from engine.engine_types import Annotation

BASS_CLEF_THRESHOLD: int = 60


class OutputWriter(ABC):
    """Abstract base for music output."""

    @abstractmethod
    def write(self, path: str, notes: list[Note], **kwargs) -> None:
        """Write notes to file."""
        pass


class Music21Writer(OutputWriter):
    """Export to MIDI and MusicXML via music21."""

    # MIDI program numbers for keyboard instruments
    INSTRUMENT_PROGRAMS: dict[str, int] = {
        "piano": 0,        # Acoustic Grand Piano
        "harpsichord": 6,  # Harpsichord
        "clavichord": 7,   # Clavichord
    }

    def _build_stream(
        self,
        notes: list[Note],
        timenum: int,
        timeden: int,
        tonic: str,
        mode: str,
        bpm: int,
        upbeat: Fraction,
        annotations: tuple["Annotation", ...] = (),
        midi_instrument: str | None = None,
    ) -> stream.Score:
        """Build music21 Score from notes with optional annotations."""
        score: stream.Score = stream.Score()
        tracks: dict[int, list[Note]] = {}
        for n in notes:
            tracks.setdefault(n.track, []).append(n)
        for track_num in sorted(tracks.keys()):
            part: stream.Part = stream.Part()
            part.id = f"Part{track_num + 1}"
            # Set instrument if specified
            if midi_instrument and midi_instrument in self.INSTRUMENT_PROGRAMS:
                inst = instrument.Instrument()
                inst.midiProgram = self.INSTRUMENT_PROGRAMS[midi_instrument]
                inst.instrumentName = midi_instrument.capitalize()
                part.insert(0, inst)
            ts: meter.TimeSignature = meter.TimeSignature(f"{timenum}/{timeden}")
            part.insert(0, ts)
            ky: key.Key = key.Key(tonic, mode)
            part.insert(0, ky)
            if track_num == 0:
                mm: tempo.MetronomeMark = tempo.MetronomeMark(number=bpm)
                part.insert(0, mm)
                for ann in annotations:
                    te: expressions.TextExpression = expressions.TextExpression(ann.text)
                    te.style.fontStyle = "bold" if ann.level == "section" else "normal"
                    part.insert(float(ann.offset) * 4, te)
            track_notes: list[Note] = sorted(tracks[track_num], key=lambda x: x.Offset)
            avg_pitch: float = sum(n.midiNote for n in track_notes) / len(track_notes)
            if avg_pitch < BASS_CLEF_THRESHOLD:
                part.insert(0, clef.BassClef())
            else:
                part.insert(0, clef.TrebleClef())
            for n in track_notes:
                m21_note: note.Note = note.Note(n.midiNote)
                m21_note.quarterLength = float(n.Duration) * 4
                m21_note.volume.velocity = n.velocity  # Use note's velocity
                step: str = m21_note.pitch.step
                key_acc = ky.accidentalByStep(step)
                note_acc = m21_note.pitch.accidental
                if note_acc and key_acc:
                    if note_acc.name == key_acc.name:
                        m21_note.pitch.accidental = None
                elif note_acc and note_acc.name == "natural" and key_acc is None:
                    m21_note.pitch.accidental = None
                if n.lyric:
                    m21_note.lyric = n.lyric
                part.insert(float(n.Offset) * 4, m21_note)
            part.makeRests(fillGaps=True, inPlace=True)
            part.makeMeasures(inPlace=True)
            score.insert(0, part)
        return score

    def write(
        self,
        path: str,
        notes: list[Note],
        timenum: int = 4,
        timeden: int = 4,
        tonic: str = "C",
        mode: str = "major",
        bpm: int = 120,
        upbeat: Fraction = Fraction(0),
        annotations: tuple["Annotation", ...] = (),
        midi_only: bool = False,
        midi_instrument: str | None = None,
    ) -> None:
        """Write MIDI and MusicXML files with optional annotations.

        Args:
            midi_only: If True, skip MusicXML export (for humanised output
                       with fractional durations that MusicXML can't handle)
            midi_instrument: Instrument name for MIDI program (piano, harpsichord, clavichord)
        """
        score: stream.Score = self._build_stream(
            notes, timenum, timeden, tonic, mode, bpm, upbeat, annotations, midi_instrument
        )
        base: Path = Path(path)
        midi_path: Path = base.with_suffix(".midi")
        score.write("midi", fp=str(midi_path))
        if not midi_only:
            score.write("musicxml", fp=str(base.with_suffix(".musicxml")), makeNotation=True)


class NoteFileWriter(OutputWriter):
    """Export to .note CSV format."""

    def _note_csv(self, n: Note, tonic: str, mode: str) -> str:
        """Generate CSV line with key-aware pitch spelling."""
        if n.midiNote == MIDI_REST:
            note_name = "REST"
        else:
            note_name = midi_to_note_octave(n.midiNote, tonic, mode)
        length: str = f"{n.Length:.6g}" if n.Length else ""
        bar: str = f"{n.bar}" if n.bar and n.bar >= 1 else ""
        beat: str = f"{n.beat}" if n.beat and n.beat >= 1 else ""
        lyric: str = f"{n.lyric}" if n.lyric else ""
        return (f"{n.Offset:.6g},{n.midiNote},{n.Duration:.6g},{n.track},"
                f"{length},{bar},{beat},{note_name},{lyric},{n.velocity}")

    def write(self, path: str, notes: list[Note], **kwargs) -> None:
        """Write notes to .note file."""
        base: Path = Path(path)
        tonic: str = kwargs.get("tonic", "C")
        mode: str = kwargs.get("mode", "major")
        lines: list[str] = [Note.csv_header()]
        for n in sorted(notes, key=lambda x: (x.Offset, -x.midiNote)):
            lines.append(self._note_csv(n, tonic, mode))
        base.with_suffix(".note").write_text("\n".join(lines))


class CompositeWriter(OutputWriter):
    """Combine multiple writers."""

    def __init__(self, writers: list[OutputWriter]) -> None:
        self._writers: list[OutputWriter] = writers

    def write(self, path: str, notes: list[Note], **kwargs) -> None:
        """Write to all formats."""
        for w in self._writers:
            w.write(path, notes, **kwargs)


def create_writer() -> OutputWriter:
    """Create default writer (MIDI + MusicXML + .note)."""
    return CompositeWriter([Music21Writer(), NoteFileWriter()])
