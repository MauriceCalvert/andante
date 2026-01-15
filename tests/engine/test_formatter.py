"""Tests for engine.formatter.

Category A tests: verify formatter conversion of realised phrases to Note objects.
Tests import only:
- engine.formatter (module under test)
- engine.types (RealisedNote, RealisedPhrase, RealisedVoice)
- engine.note (Note type)
- stdlib
"""
from fractions import Fraction

import pytest
from engine.formatter import format_notes, tempo_from_name
from engine.note import Note
from engine.engine_types import RealisedNote, RealisedPhrase, RealisedVoice


def make_realised_note(offset: Fraction, pitch: int, duration: Fraction, voice: str = "soprano") -> RealisedNote:
    """Create a test note."""
    return RealisedNote(offset=offset, pitch=pitch, duration=duration, voice=voice)


def make_realised_voice(index: int, notes: list[tuple[Fraction, int, Fraction]]) -> RealisedVoice:
    """Create a test voice."""
    realised_notes: list[RealisedNote] = [
        RealisedNote(offset=offset, pitch=pitch, duration=dur, voice=f"voice_{index}")
        for offset, pitch, dur in notes
    ]
    return RealisedVoice(voice_index=index, notes=realised_notes)


def make_realised_phrase(index: int, soprano_notes: list[tuple[Fraction, int, Fraction]], bass_notes: list[tuple[Fraction, int, Fraction]]) -> RealisedPhrase:
    """Create a test phrase with soprano and bass."""
    soprano: RealisedVoice = make_realised_voice(0, soprano_notes)
    bass: RealisedVoice = make_realised_voice(1, bass_notes)
    return RealisedPhrase(index=index, voices=[soprano, bass])


class TestTempoFromName:
    """Test tempo_from_name function."""

    def test_adagio(self) -> None:
        """Adagio returns 66 BPM."""
        assert tempo_from_name("adagio") == 66

    def test_andante(self) -> None:
        """Andante returns 80 BPM."""
        assert tempo_from_name("andante") == 80

    def test_allegro(self) -> None:
        """Allegro returns 120 BPM."""
        assert tempo_from_name("allegro") == 120

    def test_presto(self) -> None:
        """Presto returns 140 BPM."""
        assert tempo_from_name("presto") == 140

    def test_unknown_returns_default(self) -> None:
        """Unknown tempo returns 90 BPM default."""
        assert tempo_from_name("unknown") == 90
        assert tempo_from_name("") == 90


class TestFormatNotesBasic:
    """Test format_notes basic functionality."""

    def test_empty_phrases(self) -> None:
        """Empty phrases returns empty list."""
        result: list[Note] = format_notes([], "4/4")
        assert result == []

    def test_single_note(self) -> None:
        """Single note converted correctly."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 60, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert len(result) == 1
        assert result[0].midiNote == 60

    def test_note_offset_preserved(self) -> None:
        """Note offset is preserved."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(1, 2), 60, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].Offset == 0.5

    def test_note_duration_preserved(self) -> None:
        """Note duration is preserved."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 60, Fraction(1, 2))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].Duration == 0.5


class TestFormatNotesTrack:
    """Test format_notes track assignment."""

    def test_soprano_track_zero(self) -> None:
        """Soprano gets track 0."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 60, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].track == 0

    def test_bass_track_one(self) -> None:
        """Bass gets track 1."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [],
            [(Fraction(0), 48, Fraction(1, 4))],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].track == 1

    def test_multiple_voices_correct_tracks(self) -> None:
        """Multiple voices have correct tracks."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 60, Fraction(1, 4))],
            [(Fraction(0), 48, Fraction(1, 4))],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        tracks: set[int] = {n.track for n in result}
        assert tracks == {0, 1}


class TestFormatNotesBarBeat:
    """Test format_notes bar and beat calculation."""

    def test_bar_one_at_offset_zero(self) -> None:
        """Offset 0 is bar 1."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 60, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].bar == 1

    def test_bar_two_at_offset_one(self) -> None:
        """Offset 1 (in 4/4) is bar 2."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(1), 60, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].bar == 2

    def test_beat_one_at_bar_start(self) -> None:
        """Beat 1 at start of bar."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 60, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].beat == 1.0

    def test_beat_two_at_quarter(self) -> None:
        """Beat 2 at quarter note offset."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(1, 4), 60, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].beat == 2.0

    def test_beat_three_at_half(self) -> None:
        """Beat 3 at half note offset."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(1, 2), 60, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].beat == 3.0

    def test_beat_calculation_3_4_metre(self) -> None:
        """Beat calculation in 3/4 metre."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(1, 4), 60, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "3/4")
        assert result[0].beat == 2.0


class TestFormatNotesSorting:
    """Test format_notes sorting."""

    def test_sorted_by_offset(self) -> None:
        """Notes sorted by offset."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(1, 2), 60, Fraction(1, 4)), (Fraction(0), 62, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        assert result[0].Offset < result[1].Offset

    def test_sorted_by_track_within_offset(self) -> None:
        """Notes at same offset sorted by track."""
        phrase: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 60, Fraction(1, 4))],
            [(Fraction(0), 48, Fraction(1, 4))],
        )
        result: list[Note] = format_notes([phrase], "4/4")
        # Both at offset 0, track 0 should come first
        assert result[0].track == 0
        assert result[1].track == 1


class TestFormatNotesMultiplePhrases:
    """Test format_notes with multiple phrases."""

    def test_multiple_phrases_combined(self) -> None:
        """Multiple phrases combined into single list."""
        phrase1: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 60, Fraction(1, 4))],
            [],
        )
        phrase2: RealisedPhrase = make_realised_phrase(
            1,
            [(Fraction(1), 62, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase1, phrase2], "4/4")
        assert len(result) == 2

    def test_multiple_phrases_sorted(self) -> None:
        """Multiple phrases sorted by offset."""
        phrase1: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(1), 60, Fraction(1, 4))],
            [],
        )
        phrase2: RealisedPhrase = make_realised_phrase(
            1,
            [(Fraction(0), 62, Fraction(1, 4))],
            [],
        )
        result: list[Note] = format_notes([phrase1, phrase2], "4/4")
        assert result[0].Offset == 0.0
        assert result[1].Offset == 1.0
