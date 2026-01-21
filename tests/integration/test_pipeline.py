"""Integration tests for the full generation pipeline.

Category B tests: Integration of multiple modules.
Tests the complete flow: config → layers → solver → realisation → output.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from builder.io import write_note_file
from builder.types import NoteFile
from planner.planner import generate, generate_to_files


class TestGenerate:
    """Tests for the generate function."""

    def test_generate_invention_c_major_confident(self) -> None:
        """Full pipeline produces valid NoteFile."""
        result = generate("invention", "c_major", "confident")
        assert isinstance(result, NoteFile)
        assert len(result.soprano) > 0
        assert len(result.bass) > 0
        assert result.metre == "4/4"
        assert result.tempo > 0

    def test_generate_deterministic(self) -> None:
        """Same inputs produce same outputs."""
        result1 = generate("invention", "c_major", "confident")
        result2 = generate("invention", "c_major", "confident")
        assert result1.soprano == result2.soprano
        assert result1.bass == result2.bass

    def test_soprano_in_range(self) -> None:
        """All soprano pitches within B3-G5 (59-79)."""
        result = generate("invention", "c_major", "confident")
        for note in result.soprano:
            assert 59 <= note.pitch <= 79, f"Soprano pitch {note.pitch} out of range"

    def test_bass_in_range(self) -> None:
        """All bass pitches within C2-C4 (36-60)."""
        result = generate("invention", "c_major", "confident")
        for note in result.bass:
            assert 36 <= note.pitch <= 60, f"Bass pitch {note.pitch} out of range"

    def test_diatonic_pitches(self) -> None:
        """Pitches primarily diatonic with allowed chromaticism at arrivals.

        Schema arrivals may include chromatic tones (e.g., F# for dominant
        function at do_re_mi stage 2). Non-arrival pitches must be diatonic.
        """
        c_major_pcs = {0, 2, 4, 5, 7, 9, 11}
        allowed_chromatic = {6}  # F# for dominant passing tones
        all_allowed = c_major_pcs | allowed_chromatic
        result = generate("invention", "c_major", "confident")
        for note in result.soprano:
            assert note.pitch % 12 in c_major_pcs, f"Soprano pitch {note.pitch} not diatonic"
        for note in result.bass:
            assert note.pitch % 12 in all_allowed, f"Bass pitch {note.pitch} not allowed"


class TestGenerateToFiles:
    """Tests for generate_to_files function."""

    def test_creates_note_file(self) -> None:
        """Writes .note file to disk."""
        with TemporaryDirectory() as tmpdir:
            result = generate_to_files(
                "invention",
                "c_major",
                "confident",
                Path(tmpdir),
                "test_output",
            )
            note_path = Path(tmpdir) / "test_output.note"
            assert note_path.exists()

    def test_creates_midi_file(self) -> None:
        """Writes .midi file to disk."""
        with TemporaryDirectory() as tmpdir:
            result = generate_to_files(
                "invention",
                "c_major",
                "confident",
                Path(tmpdir),
                "test_output",
            )
            midi_path = Path(tmpdir) / "test_output.midi"
            assert midi_path.exists()

    def test_note_file_content(self) -> None:
        """Note file contains expected header and data."""
        with TemporaryDirectory() as tmpdir:
            generate_to_files(
                "invention",
                "c_major",
                "confident",
                Path(tmpdir),
                "test_output",
            )
            note_path = Path(tmpdir) / "test_output.note"
            content = note_path.read_text()
            assert "offset" in content
            assert "midinote" in content
            assert "duration" in content
