"""Integration tests for engine.pipeline.

Category B orchestrator tests: verify full pipeline orchestration.
Tests import only:
- engine.pipeline (module under test)
- engine.types (data types)
- engine.note (Note type)
- stdlib
"""
from fractions import Fraction

import pytest
from engine.note import Note
from engine.pipeline import execute, execute_and_export
from engine.engine_types import PieceAST


def minimal_yaml() -> str:
    """Create minimal valid YAML for testing."""
    return """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4, 5]
    durations: ["1/4", "1/8", "1/8", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""


def two_phrase_yaml() -> str:
    """Create YAML with two phrases."""
    return """
frame:
  key: G
  mode: major
  metre: "4/4"
  tempo: andante
  voices: 2
material:
  subject:
    degrees: [1, 3, 5, 3]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I, V]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
            - index: 1
              bars: 2
              tonal_target: V
              treatment: sequence
              cadence: authentic
"""


def minor_mode_yaml() -> str:
    """Create YAML in minor mode."""
    return """
frame:
  key: A
  mode: minor
  metre: "4/4"
  tempo: adagio
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [i]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: i
              treatment: statement
              cadence: authentic
"""


def triple_metre_yaml() -> str:
    """Create YAML in triple metre."""
    return """
frame:
  key: D
  mode: major
  metre: "3/4"
  tempo: moderato
  voices: 2
material:
  subject:
    degrees: [1, 2, 3]
    durations: ["1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""


class TestExecuteBasic:
    """Test basic execute functionality."""

    def test_execute_returns_notes_and_piece(self) -> None:
        """execute returns tuple of notes and PieceAST."""
        notes, piece = execute(minimal_yaml())
        assert isinstance(notes, list)
        assert isinstance(piece, PieceAST)

    def test_execute_produces_notes(self) -> None:
        """execute produces Note instances."""
        notes, _ = execute(minimal_yaml())
        assert len(notes) > 0
        for note in notes:
            assert isinstance(note, Note)

    def test_execute_notes_have_midi_pitch(self) -> None:
        """Notes have valid MIDI pitch values."""
        notes, _ = execute(minimal_yaml())
        for note in notes:
            assert isinstance(note.midiNote, int)
            assert 0 <= note.midiNote <= 127

    def test_execute_notes_have_onset(self) -> None:
        """Notes have valid onset values."""
        notes, _ = execute(minimal_yaml())
        for note in notes:
            assert hasattr(note, 'Offset')
            assert note.Offset >= 0

    def test_execute_notes_have_duration(self) -> None:
        """Notes have valid duration values."""
        notes, _ = execute(minimal_yaml())
        for note in notes:
            assert hasattr(note, 'Duration')
            assert note.Duration > 0


class TestExecutePieceAST:
    """Test PieceAST in execute output."""

    def test_execute_piece_has_key(self) -> None:
        """Returned PieceAST has correct key."""
        _, piece = execute(minimal_yaml())
        assert piece.key == "C"

    def test_execute_piece_has_mode(self) -> None:
        """Returned PieceAST has correct mode."""
        _, piece = execute(minimal_yaml())
        assert piece.mode == "major"

    def test_execute_piece_has_metre(self) -> None:
        """Returned PieceAST has correct metre."""
        _, piece = execute(minimal_yaml())
        assert piece.metre == "4/4"

    def test_execute_piece_has_tempo(self) -> None:
        """Returned PieceAST has correct tempo."""
        _, piece = execute(minimal_yaml())
        assert piece.tempo == "allegro"

    def test_execute_piece_has_voices(self) -> None:
        """Returned PieceAST has correct voice count."""
        _, piece = execute(minimal_yaml())
        assert piece.voices == 2

    def test_execute_piece_has_sections(self) -> None:
        """Returned PieceAST has sections."""
        _, piece = execute(minimal_yaml())
        assert len(piece.sections) > 0


class TestExecuteMultiplePhrases:
    """Test execute with multiple phrases."""

    def test_execute_two_phrases(self) -> None:
        """Two-phrase piece produces notes."""
        notes, piece = execute(two_phrase_yaml())
        assert len(notes) > 0

    def test_execute_preserves_phrase_count(self) -> None:
        """Correct number of phrases in piece."""
        _, piece = execute(two_phrase_yaml())
        total_phrases = sum(
            len(ep.phrases)
            for sec in piece.sections
            for ep in sec.episodes
        )
        assert total_phrases == 2


class TestExecuteMinorMode:
    """Test execute in minor mode."""

    def test_execute_minor_mode(self) -> None:
        """Minor mode piece executes successfully."""
        notes, piece = execute(minor_mode_yaml())
        assert piece.mode == "minor"
        assert len(notes) > 0


class TestExecuteTripleMetre:
    """Test execute in triple metre."""

    def test_execute_triple_metre(self) -> None:
        """Triple metre piece executes successfully."""
        notes, piece = execute(triple_metre_yaml())
        assert piece.metre == "3/4"
        assert len(notes) > 0


class TestExecuteNoteOrder:
    """Test note ordering in execute output."""

    def test_notes_ordered_by_onset(self) -> None:
        """Notes are ordered by onset time."""
        notes, _ = execute(minimal_yaml())
        for i in range(len(notes) - 1):
            assert notes[i].Offset <= notes[i + 1].Offset


class TestExecuteVoices:
    """Test voice handling in execute."""

    def test_notes_have_track_attribute(self) -> None:
        """Notes have track attribute."""
        notes, _ = execute(minimal_yaml())
        for note in notes:
            assert hasattr(note, 'track')

    def test_multiple_tracks_present(self) -> None:
        """Notes from multiple tracks are present."""
        notes, _ = execute(minimal_yaml())
        tracks = set(note.track for note in notes)
        assert len(tracks) >= 2  # At least soprano and bass


class TestExecuteAndExport:
    """Test execute_and_export functionality."""

    def test_execute_and_export_returns_notes(self, tmp_path) -> None:
        """execute_and_export returns notes."""
        output = tmp_path / "test_output"
        notes = execute_and_export(minimal_yaml(), str(output))
        assert isinstance(notes, list)
        assert len(notes) > 0

    def test_execute_and_export_creates_midi_file(self, tmp_path) -> None:
        """execute_and_export creates MIDI file."""
        output = tmp_path / "test_output"
        execute_and_export(minimal_yaml(), str(output))
        midi_path = tmp_path / "test_output.midi"
        assert midi_path.exists()

    def test_execute_and_export_creates_trace_file(self, tmp_path) -> None:
        """execute_and_export creates trace file."""
        output = tmp_path / "test_output"
        execute_and_export(minimal_yaml(), str(output))
        trace_path = tmp_path / "test_output.trace"
        assert trace_path.exists()


class TestExecutePipelineIntegrity:
    """Test data integrity through full pipeline."""

    def test_pipeline_key_preserved(self) -> None:
        """Key is preserved through pipeline."""
        yaml_str = """
frame:
  key: Bb
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""
        _, piece = execute(yaml_str)
        assert piece.key == "Bb"

    def test_pipeline_tempo_preserved(self) -> None:
        """Tempo is preserved through pipeline."""
        yaml_str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: presto
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""
        _, piece = execute(yaml_str)
        assert piece.tempo == "presto"


class TestExecuteComplexPieces:
    """Test execute with more complex structures."""

    def test_execute_with_cadence(self) -> None:
        """Piece with cadence executes successfully."""
        yaml_str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I, V]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: half
            - index: 1
              bars: 2
              tonal_target: V
              treatment: sequence
              cadence: authentic
"""
        notes, piece = execute(yaml_str)
        assert len(notes) > 0

    def test_execute_with_rhythm(self) -> None:
        """Piece with rhythm specification executes successfully."""
        yaml_str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              rhythm: dotted
              cadence: authentic
"""
        notes, piece = execute(yaml_str)
        assert len(notes) > 0

    def test_execute_with_device(self) -> None:
        """Piece with device specification executes successfully."""
        yaml_str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              device: stretto
              cadence: authentic
"""
        notes, piece = execute(yaml_str)
        assert len(notes) > 0


class TestExecuteNoteAttributes:
    """Test that Note objects have all required attributes."""

    def test_note_has_all_attributes(self) -> None:
        """Note has midiNote, Offset, Duration, track."""
        notes, _ = execute(minimal_yaml())
        note = notes[0]
        assert hasattr(note, 'midiNote')
        assert hasattr(note, 'Offset')
        assert hasattr(note, 'Duration')
        assert hasattr(note, 'track')

    def test_note_midi_is_int(self) -> None:
        """Note midiNote is integer."""
        notes, _ = execute(minimal_yaml())
        for note in notes:
            assert isinstance(note.midiNote, int)

    def test_note_duration_is_positive(self) -> None:
        """Note Duration is positive."""
        notes, _ = execute(minimal_yaml())
        for note in notes:
            assert note.Duration > 0
