"""Tests for builder.io module.

Category A tests: Pure functions for formatting.

Specification source: architecture.md
- Note file format: offset,midinote,duration,track,length,bar,beat,notename,lyric
- Bar/beat calculation from offset
- Note name conversion (MIDI to pitch name)
"""
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from builder.io import (
    bar_beat,
    format_note_line,
    note_name,
    write_midi_file,
    write_note_file,
)
from builder.types import Note, NoteFile


class TestNoteName:
    """Tests for note_name function."""

    def test_middle_c(self) -> None:
        assert note_name(60) == "C4"

    def test_c_sharp_4(self) -> None:
        assert note_name(61) == "C#4"

    def test_d4(self) -> None:
        assert note_name(62) == "D4"

    def test_a4(self) -> None:
        assert note_name(69) == "A4"

    def test_c5(self) -> None:
        assert note_name(72) == "C5"

    def test_c3(self) -> None:
        assert note_name(48) == "C3"

    def test_b_flat_3(self) -> None:
        assert note_name(58) == "A#3"


class TestBarBeat:
    """Tests for bar_beat function."""

    def test_offset_zero_is_bar_1_beat_1(self) -> None:
        bar, beat = bar_beat(Fraction(0), "4/4")
        assert bar == 1
        assert beat == Fraction(1)

    def test_quarter_note_is_beat_2(self) -> None:
        bar, beat = bar_beat(Fraction(1, 4), "4/4")
        assert bar == 1
        assert beat == Fraction(2)

    def test_half_note_is_beat_3(self) -> None:
        bar, beat = bar_beat(Fraction(1, 2), "4/4")
        assert bar == 1
        assert beat == Fraction(3)

    def test_bar_2_beat_1(self) -> None:
        bar, beat = bar_beat(Fraction(1), "4/4")
        assert bar == 2
        assert beat == Fraction(1)

    def test_bar_3_beat_3(self) -> None:
        bar, beat = bar_beat(Fraction(5, 2), "4/4")
        assert bar == 3
        assert beat == Fraction(3)

    def test_3_4_metre_bar_2(self) -> None:
        bar, beat = bar_beat(Fraction(3, 4), "3/4")
        assert bar == 2
        assert beat == Fraction(1)


class TestFormatNoteLine:
    """Tests for format_note_line function."""

    def test_basic_note(self) -> None:
        note = Note(Fraction(0), 60, Fraction(1, 4), 0, "")
        line = format_note_line(note, "4/4")
        parts = line.split(",")
        assert parts[0] == "0.0"
        assert parts[1] == "60"
        assert parts[2] == "1/4"
        assert parts[3] == "0"
        assert parts[5] == "1"
        assert parts[6] == "1.0"
        assert parts[7] == "C4"

    def test_note_with_lyric(self) -> None:
        note = Note(Fraction(0), 64, Fraction(1, 8), 0, "do_re_mi_3")
        line = format_note_line(note, "4/4")
        assert "do_re_mi_3" in line

    def test_bass_note(self) -> None:
        note = Note(Fraction(1), 48, Fraction(1, 4), 1, "")
        line = format_note_line(note, "4/4")
        parts = line.split(",")
        assert parts[3] == "1"
        assert parts[7] == "C3"


class TestWriteNoteFile:
    """Tests for write_note_file function."""

    def test_creates_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.note"
            notes = NoteFile(
                soprano=(Note(Fraction(0), 60, Fraction(1, 4), 0),),
                bass=(Note(Fraction(0), 48, Fraction(1, 4), 1),),
                metre="4/4",
                tempo=80,
            )
            write_note_file(notes, path)
            assert path.exists()

    def test_file_has_header(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.note"
            notes = NoteFile(
                soprano=(Note(Fraction(0), 60, Fraction(1, 4), 0),),
                bass=(),
                metre="4/4",
                tempo=80,
            )
            write_note_file(notes, path)
            content = path.read_text()
            assert content.startswith("offset,midinote,duration,track,length,bar,beat,notename,lyric")

    def test_file_has_data_lines(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.note"
            notes = NoteFile(
                soprano=(
                    Note(Fraction(0), 60, Fraction(1, 4), 0),
                    Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
                ),
                bass=(Note(Fraction(0), 48, Fraction(1, 2), 1),),
                metre="4/4",
                tempo=80,
            )
            write_note_file(notes, path)
            lines = path.read_text().strip().split("\n")
            assert len(lines) == 4

    def test_notes_sorted_by_offset(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.note"
            notes = NoteFile(
                soprano=(Note(Fraction(1, 4), 64, Fraction(1, 4), 0),),
                bass=(Note(Fraction(0), 48, Fraction(1, 4), 1),),
                metre="4/4",
                tempo=80,
            )
            write_note_file(notes, path)
            lines = path.read_text().strip().split("\n")
            data_lines = lines[1:]
            first_offset = float(data_lines[0].split(",")[0])
            second_offset = float(data_lines[1].split(",")[0])
            assert first_offset <= second_offset


class TestWriteMidiFile:
    """Tests for write_midi_file function."""

    def test_creates_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.midi"
            notes = NoteFile(
                soprano=(Note(Fraction(0), 60, Fraction(1, 4), 0),),
                bass=(Note(Fraction(0), 48, Fraction(1, 4), 1),),
                metre="4/4",
                tempo=80,
            )
            write_midi_file(notes, path)
            assert path.exists()

    def test_file_not_empty(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.midi"
            notes = NoteFile(
                soprano=(Note(Fraction(0), 60, Fraction(1, 4), 0),),
                bass=(),
                metre="4/4",
                tempo=80,
            )
            write_midi_file(notes, path)
            assert path.stat().st_size > 0
