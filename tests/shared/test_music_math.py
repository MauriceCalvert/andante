"""Tests for shared.music_math.

Tests musical arithmetic using exact fractions.
"""
from fractions import Fraction

import pytest

from shared.music_math import (
    MusicMathError,
    VALID_DURATIONS,
    VALID_DURATIONS_SORTED,
    bar_duration,
    beat_duration,
    build_offsets,
    fill_slot,
    is_valid_duration,
    repeat_to_fill,
)


class TestValidDurations:
    """Test VALID_DURATIONS constant."""

    def test_contains_whole(self) -> None:
        """Contains whole note."""
        assert Fraction(1, 1) in VALID_DURATIONS

    def test_contains_half(self) -> None:
        """Contains half note."""
        assert Fraction(1, 2) in VALID_DURATIONS

    def test_contains_quarter(self) -> None:
        """Contains quarter note."""
        assert Fraction(1, 4) in VALID_DURATIONS

    def test_contains_eighth(self) -> None:
        """Contains eighth note."""
        assert Fraction(1, 8) in VALID_DURATIONS

    def test_contains_sixteenth(self) -> None:
        """Contains sixteenth note."""
        assert Fraction(1, 16) in VALID_DURATIONS

    def test_contains_dotted_quarter(self) -> None:
        """Contains dotted quarter."""
        assert Fraction(3, 8) in VALID_DURATIONS

    def test_sorted_descending(self) -> None:
        """VALID_DURATIONS_SORTED is descending."""
        durations: list[Fraction] = list(VALID_DURATIONS_SORTED)
        assert durations == sorted(durations, reverse=True)


class TestIsValidDuration:
    """Test is_valid_duration function."""

    def test_valid_quarter(self) -> None:
        """Quarter note is valid."""
        assert is_valid_duration(Fraction(1, 4)) is True

    def test_valid_dotted(self) -> None:
        """Dotted eighth is valid."""
        assert is_valid_duration(Fraction(3, 16)) is True

    def test_invalid_triplet(self) -> None:
        """Triplet eighth is invalid."""
        assert is_valid_duration(Fraction(1, 12)) is False

    def test_invalid_fraction(self) -> None:
        """Arbitrary fraction is invalid."""
        assert is_valid_duration(Fraction(5, 7)) is False


class TestBarDuration:
    """Test bar_duration function."""

    def test_4_4(self) -> None:
        """4/4 bar is one whole note."""
        assert bar_duration(4, 4) == Fraction(1, 1)

    def test_3_4(self) -> None:
        """3/4 bar is 3/4."""
        assert bar_duration(3, 4) == Fraction(3, 4)

    def test_6_8(self) -> None:
        """6/8 bar is 3/4."""
        assert bar_duration(6, 8) == Fraction(3, 4)

    def test_2_4(self) -> None:
        """2/4 bar is 1/2."""
        assert bar_duration(2, 4) == Fraction(1, 2)


class TestBeatDuration:
    """Test beat_duration function."""

    def test_quarter_beat(self) -> None:
        """Beat in /4 time is quarter note."""
        assert beat_duration(4) == Fraction(1, 4)

    def test_eighth_beat(self) -> None:
        """Beat in /8 time is eighth note."""
        assert beat_duration(8) == Fraction(1, 8)

    def test_half_beat(self) -> None:
        """Beat in /2 time is half note."""
        assert beat_duration(2) == Fraction(1, 2)


class TestFillSlot:
    """Test fill_slot function."""

    def test_uniform_quarter_notes(self) -> None:
        """Fill bar with 4 quarter notes."""
        result: list[Fraction] = fill_slot(Fraction(1, 1), 4, "uniform")
        assert sum(result) == Fraction(1, 1)
        assert all(d == Fraction(1, 4) for d in result)

    def test_uniform_eighth_notes(self) -> None:
        """Fill bar with 8 eighth notes."""
        result: list[Fraction] = fill_slot(Fraction(1, 1), 8, "uniform")
        assert sum(result) == Fraction(1, 1)

    def test_uniform_fallback(self) -> None:
        """Uniform falls back to varied when exact division impossible."""
        result: list[Fraction] = fill_slot(Fraction(1, 1), 3, "uniform")
        assert sum(result) == Fraction(1, 1)

    def test_varied_greedy(self) -> None:
        """Varied uses greedy selection."""
        result: list[Fraction] = fill_slot(Fraction(1, 1), 1, "varied")
        assert sum(result) == Fraction(1, 1)

    def test_long_short_dotted(self) -> None:
        """Long-short creates dotted pattern."""
        result: list[Fraction] = fill_slot(Fraction(1, 2), 2, "long_short")
        assert sum(result) == Fraction(1, 2)

    def test_invalid_note_count_raises(self) -> None:
        """Zero or negative note count raises."""
        with pytest.raises(MusicMathError):
            fill_slot(Fraction(1, 1), 0, "uniform")

    def test_unknown_style_raises(self) -> None:
        """Unknown style raises."""
        with pytest.raises(MusicMathError):
            fill_slot(Fraction(1, 1), 4, "unknown")


class TestRepeatToFill:
    """Test repeat_to_fill function."""

    def test_exact_division(self) -> None:
        """Motif divides target exactly."""
        degrees: list[int] = [1, 3]
        durations: list[Fraction] = [Fraction(1, 4), Fraction(1, 4)]
        new_deg, new_dur = repeat_to_fill(Fraction(1, 1), degrees, durations)
        assert sum(new_dur) == Fraction(1, 1)
        assert len(new_deg) == 4

    def test_single_repeat(self) -> None:
        """Single motif fills target."""
        degrees: list[int] = [1, 2, 3, 4]
        durations: list[Fraction] = [Fraction(1, 4)] * 4
        new_deg, new_dur = repeat_to_fill(Fraction(1, 1), degrees, durations)
        assert new_deg == [1, 2, 3, 4]

    def test_multiple_repeats(self) -> None:
        """Motif repeated multiple times."""
        degrees: list[int] = [1, 2]
        durations: list[Fraction] = [Fraction(1, 8), Fraction(1, 8)]
        new_deg, new_dur = repeat_to_fill(Fraction(1, 1), degrees, durations)
        assert len(new_deg) == 8

    def test_empty_motif_raises(self) -> None:
        """Empty motif raises."""
        with pytest.raises(MusicMathError):
            repeat_to_fill(Fraction(1, 1), [], [])

    def test_indivisible_raises(self) -> None:
        """Target not divisible by motif raises."""
        degrees: list[int] = [1, 2, 3]
        durations: list[Fraction] = [Fraction(1, 4)] * 3
        with pytest.raises(MusicMathError):
            repeat_to_fill(Fraction(1, 1), degrees, durations)


class TestBuildOffsets:
    """Test build_offsets function."""

    def test_from_zero(self) -> None:
        """Offsets from start position 0."""
        durations: list[Fraction] = [Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)]
        offsets: list[Fraction] = build_offsets(Fraction(0), durations)
        assert offsets == [Fraction(0), Fraction(1, 4), Fraction(1, 2)]

    def test_from_nonzero(self) -> None:
        """Offsets from non-zero start."""
        durations: list[Fraction] = [Fraction(1, 4), Fraction(1, 4)]
        offsets: list[Fraction] = build_offsets(Fraction(1, 2), durations)
        assert offsets == [Fraction(1, 2), Fraction(3, 4)]

    def test_empty_durations(self) -> None:
        """Empty durations returns empty offsets."""
        offsets: list[Fraction] = build_offsets(Fraction(0), [])
        assert offsets == []


class TestMusicMathError:
    """Test MusicMathError exception."""

    def test_is_exception(self) -> None:
        """MusicMathError is an Exception."""
        assert issubclass(MusicMathError, Exception)

    def test_can_raise(self) -> None:
        """Can raise with message."""
        with pytest.raises(MusicMathError, match="test error"):
            raise MusicMathError("test error")
