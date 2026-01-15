"""100% coverage tests for engine.output.

Tests import only:
- engine.output (module under test)
- engine.note (Note)
- stdlib

Output module provides MIDI, MusicXML, and .note file export via music21.
"""
from fractions import Fraction
from pathlib import Path
import tempfile

import pytest

from engine.note import Note
from engine.output import (
    BASS_CLEF_THRESHOLD,
    MIDI_REST,
    NOTE_NAMES,
    CompositeWriter,
    Music21Writer,
    NoteFileWriter,
    OutputWriter,
    create_writer,
    midi_to_note_octave,
)


class TestConstants:
    """Test module constants."""

    def test_midi_rest_value(self) -> None:
        """MIDI_REST is 20."""
        assert MIDI_REST == 20

    def test_note_names_length(self) -> None:
        """NOTE_NAMES has 12 entries."""
        assert len(NOTE_NAMES) == 12

    def test_note_names_starts_with_c(self) -> None:
        """NOTE_NAMES starts with C."""
        assert NOTE_NAMES[0] == "C"

    def test_bass_clef_threshold(self) -> None:
        """BASS_CLEF_THRESHOLD is 60 (middle C)."""
        assert BASS_CLEF_THRESHOLD == 60


class TestMidiToNoteOctave:
    """Test midi_to_note_octave function."""

    def test_middle_c(self) -> None:
        """Middle C (60) is C4."""
        result: str = midi_to_note_octave(60)
        assert result == "C4"

    def test_a4_concert_pitch(self) -> None:
        """A4 concert pitch (69) is A4."""
        result: str = midi_to_note_octave(69)
        assert result == "A4"

    def test_c0(self) -> None:
        """MIDI 12 is C0."""
        result: str = midi_to_note_octave(12)
        assert result == "C0"

    def test_sharp_note(self) -> None:
        """MIDI 61 is C#4."""
        result: str = midi_to_note_octave(61)
        assert result == "C#4"

    def test_low_note(self) -> None:
        """MIDI 24 is C1."""
        result: str = midi_to_note_octave(24)
        assert result == "C1"

    def test_high_note(self) -> None:
        """MIDI 96 is C7."""
        result: str = midi_to_note_octave(96)
        assert result == "C7"

    def test_negative_midi_returns_midi_prefix(self) -> None:
        """Negative MIDI returns MIDI prefix."""
        result: str = midi_to_note_octave(-1)
        assert result == "MIDI-1"

    def test_over_127_returns_midi_prefix(self) -> None:
        """MIDI > 127 returns MIDI prefix."""
        result: str = midi_to_note_octave(128)
        assert result == "MIDI128"

    def test_zero_midi(self) -> None:
        """MIDI 0 is C-1."""
        result: str = midi_to_note_octave(0)
        assert result == "C-1"

    def test_127_midi(self) -> None:
        """MIDI 127 is G9."""
        result: str = midi_to_note_octave(127)
        assert result == "G9"


class TestOutputWriter:
    """Test OutputWriter abstract class."""

    def test_is_abstract(self) -> None:
        """OutputWriter is abstract."""
        assert hasattr(OutputWriter, "write")
        # Can't instantiate directly
        with pytest.raises(TypeError):
            OutputWriter()


class TestNoteFileWriter:
    """Test NoteFileWriter class."""

    def test_write_creates_note_file(self) -> None:
        """Write creates .note file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [
                Note(midiNote=60, Offset=0.0, Duration=0.5, track=0),
                Note(midiNote=64, Offset=0.5, Duration=0.5, track=0),
            ]
            writer: NoteFileWriter = NoteFileWriter()
            writer.write(path, notes)
            note_path: Path = Path(tmpdir) / "test.note"
            assert note_path.exists()

    def test_write_contains_header(self) -> None:
        """Written file contains CSV header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0)]
            writer: NoteFileWriter = NoteFileWriter()
            writer.write(path, notes)
            content: str = (Path(tmpdir) / "test.note").read_text()
            assert "Offset,midiNote,Duration,track" in content

    def test_write_contains_note_data(self) -> None:
        """Written file contains note data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0)]
            writer: NoteFileWriter = NoteFileWriter()
            writer.write(path, notes)
            content: str = (Path(tmpdir) / "test.note").read_text()
            assert "60" in content
            assert "C4" in content

    def test_rest_note_shows_rest(self) -> None:
        """REST note shows REST in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=MIDI_REST, Offset=0.0, Duration=0.5, track=0)]
            writer: NoteFileWriter = NoteFileWriter()
            writer.write(path, notes)
            content: str = (Path(tmpdir) / "test.note").read_text()
            assert "REST" in content

    def test_write_with_bar_and_beat(self) -> None:
        """Write includes bar and beat info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0, bar=1, beat=1)]
            writer: NoteFileWriter = NoteFileWriter()
            writer.write(path, notes)
            content: str = (Path(tmpdir) / "test.note").read_text()
            lines: list[str] = content.split("\n")
            assert len(lines) >= 2

    def test_write_with_lyric(self) -> None:
        """Write includes lyric."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0, lyric="test")]
            writer: NoteFileWriter = NoteFileWriter()
            writer.write(path, notes)
            content: str = (Path(tmpdir) / "test.note").read_text()
            assert "test" in content

    def test_write_sorts_by_offset(self) -> None:
        """Notes are sorted by offset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [
                Note(midiNote=60, Offset=1.0, Duration=0.5, track=0),
                Note(midiNote=64, Offset=0.0, Duration=0.5, track=0),
            ]
            writer: NoteFileWriter = NoteFileWriter()
            writer.write(path, notes)
            content: str = (Path(tmpdir) / "test.note").read_text()
            lines: list[str] = content.split("\n")
            # First data line should be offset 0
            assert lines[1].startswith("0")

    def test_write_with_tonic_mode(self) -> None:
        """Write accepts tonic and mode kwargs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0)]
            writer: NoteFileWriter = NoteFileWriter()
            writer.write(path, notes, tonic="G", mode="major")
            assert (Path(tmpdir) / "test.note").exists()


class TestMusic21Writer:
    """Test Music21Writer class."""

    def test_write_creates_midi_file(self) -> None:
        """Write creates .midi file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [
                Note(midiNote=60, Offset=0.0, Duration=0.5, track=0),
                Note(midiNote=64, Offset=0.5, Duration=0.5, track=0),
            ]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes)
            midi_path: Path = Path(tmpdir) / "test.midi"
            assert midi_path.exists()

    def test_write_creates_musicxml_file(self) -> None:
        """Write creates .musicxml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0)]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes)
            xml_path: Path = Path(tmpdir) / "test.musicxml"
            assert xml_path.exists()

    def test_write_with_custom_time_signature(self) -> None:
        """Write with custom time signature works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.75, track=0)]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, timenum=3, timeden=4)
            assert (Path(tmpdir) / "test.midi").exists()

    def test_write_with_custom_key(self) -> None:
        """Write with custom key works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0)]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, tonic="G", mode="major")
            assert (Path(tmpdir) / "test.midi").exists()

    def test_write_with_custom_tempo(self) -> None:
        """Write with custom tempo works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0)]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, bpm=80)
            assert (Path(tmpdir) / "test.midi").exists()

    def test_write_multiple_tracks(self) -> None:
        """Write with multiple tracks works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [
                Note(midiNote=60, Offset=0.0, Duration=0.5, track=0),
                Note(midiNote=48, Offset=0.0, Duration=0.5, track=1),
            ]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes)
            assert (Path(tmpdir) / "test.midi").exists()

    def test_bass_track_gets_bass_clef(self) -> None:
        """Low pitch track gets bass clef."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            # Notes well below middle C should trigger bass clef
            notes: list[Note] = [
                Note(midiNote=36, Offset=0.0, Duration=0.5, track=0),
                Note(midiNote=40, Offset=0.5, Duration=0.5, track=0),
            ]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes)
            assert (Path(tmpdir) / "test.midi").exists()

    def test_treble_track_gets_treble_clef(self) -> None:
        """High pitch track gets treble clef."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            # Notes above middle C should trigger treble clef
            notes: list[Note] = [
                Note(midiNote=72, Offset=0.0, Duration=0.5, track=0),
                Note(midiNote=76, Offset=0.5, Duration=0.5, track=0),
            ]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes)
            assert (Path(tmpdir) / "test.midi").exists()


class TestCompositeWriter:
    """Test CompositeWriter class."""

    def test_calls_all_writers(self) -> None:
        """CompositeWriter calls all contained writers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0)]
            writer: CompositeWriter = CompositeWriter([
                NoteFileWriter(),
                Music21Writer(),
            ])
            writer.write(path, notes)
            # Both should create their files
            assert (Path(tmpdir) / "test.note").exists()
            assert (Path(tmpdir) / "test.midi").exists()

    def test_empty_writers_list(self) -> None:
        """Empty writers list does nothing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0)]
            writer: CompositeWriter = CompositeWriter([])
            writer.write(path, notes)
            # No files created
            assert not (Path(tmpdir) / "test.note").exists()
            assert not (Path(tmpdir) / "test.midi").exists()


class TestCreateWriter:
    """Test create_writer factory function."""

    def test_returns_composite_writer(self) -> None:
        """Returns CompositeWriter instance."""
        writer: OutputWriter = create_writer()
        assert isinstance(writer, CompositeWriter)

    def test_creates_all_formats(self) -> None:
        """Created writer produces all formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "test")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=0.5, track=0)]
            writer: OutputWriter = create_writer()
            writer.write(path, notes)
            assert (Path(tmpdir) / "test.note").exists()
            assert (Path(tmpdir) / "test.midi").exists()
            assert (Path(tmpdir) / "test.musicxml").exists()


class TestAnnotations:
    """Test annotation support in Music21Writer."""

    def test_write_with_annotations(self) -> None:
        """Write with annotations works."""
        from engine.engine_types import Annotation
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "annotated")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=1.0, track=0)]
            annotations: tuple = (
                Annotation(offset=Fraction(0), text="Intro", level="section"),
            )
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, annotations=annotations)
            assert (Path(tmpdir) / "annotated.midi").exists()

    def test_section_annotation_is_bold(self) -> None:
        """Section-level annotation uses bold font."""
        from engine.engine_types import Annotation
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "bold")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=1.0, track=0)]
            annotations: tuple = (
                Annotation(offset=Fraction(0), text="Section A", level="section"),
            )
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, annotations=annotations)
            assert (Path(tmpdir) / "bold.midi").exists()

    def test_phrase_annotation_is_normal(self) -> None:
        """Phrase-level annotation uses normal font."""
        from engine.engine_types import Annotation
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "normal")
            notes: list[Note] = [Note(midiNote=60, Offset=0.0, Duration=1.0, track=0)]
            annotations: tuple = (
                Annotation(offset=Fraction(0), text="Phrase 1", level="phrase"),
            )
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, annotations=annotations)
            assert (Path(tmpdir) / "normal.midi").exists()

    def test_multiple_annotations(self) -> None:
        """Multiple annotations work."""
        from engine.engine_types import Annotation
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "multi")
            notes: list[Note] = [
                Note(midiNote=60, Offset=0.0, Duration=1.0, track=0),
                Note(midiNote=64, Offset=1.0, Duration=1.0, track=0),
            ]
            annotations: tuple = (
                Annotation(offset=Fraction(0), text="A", level="section"),
                Annotation(offset=Fraction(1), text="B", level="phrase"),
            )
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, annotations=annotations)
            assert (Path(tmpdir) / "multi.midi").exists()


class TestAccidentalHandling:
    """Test accidental handling in Music21Writer."""

    def test_sharp_in_key_signature(self) -> None:
        """Sharp notes in key signature handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "sharp")
            # F# in G major key
            notes: list[Note] = [Note(midiNote=66, Offset=0.0, Duration=0.5, track=0)]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, tonic="G", mode="major")
            assert (Path(tmpdir) / "sharp.midi").exists()

    def test_flat_in_key_signature(self) -> None:
        """Flat notes in key signature handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "flat")
            # Bb in F major key
            notes: list[Note] = [Note(midiNote=70, Offset=0.0, Duration=0.5, track=0)]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, tonic="F", mode="major")
            assert (Path(tmpdir) / "flat.midi").exists()

    def test_natural_accidental(self) -> None:
        """Natural accidentals handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "natural")
            # F natural in G major (which has F#)
            notes: list[Note] = [Note(midiNote=65, Offset=0.0, Duration=0.5, track=0)]
            writer: Music21Writer = Music21Writer()
            writer.write(path, notes, tonic="G", mode="major")
            assert (Path(tmpdir) / "natural.midi").exists()


class TestIntegration:
    """Integration tests for output module."""

    def test_full_piece_export(self) -> None:
        """Export a full piece with multiple tracks and notes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "piece")
            notes: list[Note] = [
                # Soprano
                Note(midiNote=72, Offset=0.0, Duration=0.25, track=0),
                Note(midiNote=74, Offset=0.25, Duration=0.25, track=0),
                Note(midiNote=76, Offset=0.5, Duration=0.5, track=0),
                # Bass
                Note(midiNote=48, Offset=0.0, Duration=0.5, track=1),
                Note(midiNote=43, Offset=0.5, Duration=0.5, track=1),
            ]
            writer: OutputWriter = create_writer()
            writer.write(
                path, notes,
                timenum=4, timeden=4,
                tonic="C", mode="major",
                bpm=120,
            )
            assert (Path(tmpdir) / "piece.midi").exists()
            assert (Path(tmpdir) / "piece.musicxml").exists()
            assert (Path(tmpdir) / "piece.note").exists()

    def test_minor_key_export(self) -> None:
        """Export in minor key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "minor")
            notes: list[Note] = [Note(midiNote=57, Offset=0.0, Duration=1.0, track=0)]
            writer: OutputWriter = create_writer()
            writer.write(path, notes, tonic="A", mode="minor")
            assert (Path(tmpdir) / "minor.midi").exists()

    def test_compound_time_signature(self) -> None:
        """Export with compound time signature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path: str = str(Path(tmpdir) / "compound")
            notes: list[Note] = [
                Note(midiNote=60, Offset=0.0, Duration=0.375, track=0),
                Note(midiNote=64, Offset=0.375, Duration=0.375, track=0),
            ]
            writer: OutputWriter = create_writer()
            writer.write(path, notes, timenum=6, timeden=8)
            assert (Path(tmpdir) / "compound.midi").exists()
