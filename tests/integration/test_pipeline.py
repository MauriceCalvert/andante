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

    def test_generate_invention_c_major_default(self) -> None:
        """Full pipeline produces valid NoteFile."""
        result = generate("invention", "default", key="c_major")
        assert isinstance(result, NoteFile)
        assert len(result.soprano) > 0
        assert len(result.bass) > 0
        assert result.metre == "4/4"
        assert result.tempo > 0

    def test_generate_deterministic(self) -> None:
        """Same inputs produce same outputs."""
        result1 = generate("invention", "default", key="c_major")
        result2 = generate("invention", "default", key="c_major")
        assert result1.soprano == result2.soprano
        assert result1.bass == result2.bass

    def test_generate_without_key(self) -> None:
        """Generate without key derives from affect per Mattheson."""
        result = generate("invention", "default")
        assert isinstance(result, NoteFile)
        assert len(result.soprano) > 0
        assert len(result.bass) > 0

    def test_soprano_in_range(self) -> None:
        """All soprano pitches within extended range (52-88).

        With TESSITURA_SPAN=18 and median ~70, range is 52-88.
        Anchors may be transposed, so allow generous bounds.
        """
        result = generate("invention", "default", key="c_major")
        for note in result.soprano:
            assert 52 <= note.pitch <= 88, f"Soprano pitch {note.pitch} out of range"

    def test_bass_in_range(self) -> None:
        """All bass pitches within extended range (30-66).

        With TESSITURA_SPAN=18 and median ~48, range is 30-66.
        Anchors may be transposed, so allow generous bounds.
        """
        result = generate("invention", "default", key="c_major")
        for note in result.bass:
            assert 30 <= note.pitch <= 66, f"Bass pitch {note.pitch} out of range"

    def test_diatonic_pitches(self) -> None:
        """Pitches primarily diatonic with allowed chromaticism.

        With key area modulation (tonal_path includes V, vi, IV), transposed
        schemas may introduce chromatic tones. We check that the majority
        of pitches are diatonic C major.
        """
        c_major_pcs = {0, 2, 4, 5, 7, 9, 11}
        result = generate("invention", "default", key="c_major")

        # Count diatonic pitches
        soprano_total = len(result.soprano)
        soprano_diatonic = sum(1 for n in result.soprano if n.pitch % 12 in c_major_pcs)
        bass_total = len(result.bass)
        bass_diatonic = sum(1 for n in result.bass if n.pitch % 12 in c_major_pcs)

        # At least 85% should be diatonic (allows for modulations to V, vi, IV)
        assert soprano_diatonic / soprano_total >= 0.85, (
            f"Only {soprano_diatonic}/{soprano_total} soprano pitches diatonic"
        )
        assert bass_diatonic / bass_total >= 0.85, (
            f"Only {bass_diatonic}/{bass_total} bass pitches diatonic"
        )


class TestGenerateToFiles:
    """Tests for generate_to_files function."""

    def test_creates_note_file(self) -> None:
        """Writes .note file to disk."""
        with TemporaryDirectory() as tmpdir:
            result = generate_to_files(
                "invention",
                "default",
                Path(tmpdir),
                "test_output",
                key="c_major",
            )
            note_path = Path(tmpdir) / "test_output.note"
            assert note_path.exists()

    def test_creates_midi_file(self) -> None:
        """Writes .midi file to disk."""
        with TemporaryDirectory() as tmpdir:
            result = generate_to_files(
                "invention",
                "default",
                Path(tmpdir),
                "test_output",
                key="c_major",
            )
            midi_path = Path(tmpdir) / "test_output.midi"
            assert midi_path.exists()

    def test_note_file_content(self) -> None:
        """Note file contains expected header and data."""
        with TemporaryDirectory() as tmpdir:
            generate_to_files(
                "invention",
                "default",
                Path(tmpdir),
                "test_output",
                key="c_major",
            )
            note_path = Path(tmpdir) / "test_output.note"
            content = note_path.read_text()
            assert "offset" in content
            assert "midinote" in content
            assert "duration" in content
