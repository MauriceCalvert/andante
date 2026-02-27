"""Unit tests for shared/music_math.py — duration arithmetic."""
from fractions import Fraction

from shared.music_math import (
    VALID_DURATIONS,
    VALID_DURATIONS_SORTED,
    parse_fraction,
    parse_metre,
)


# =========================================================================
# VALID_DURATIONS invariants
# =========================================================================


def test_valid_durations_all_positive() -> None:
    """Every valid duration is positive."""
    for dur in VALID_DURATIONS:
        assert dur > 0, f"Duration {dur} is not positive"


def test_valid_durations_sorted_descending() -> None:
    """VALID_DURATIONS_SORTED is strictly descending."""
    for i in range(len(VALID_DURATIONS_SORTED) - 1):
        assert VALID_DURATIONS_SORTED[i] > VALID_DURATIONS_SORTED[i + 1]


def test_valid_durations_sorted_matches_set() -> None:
    """Sorted tuple contains same elements as the frozenset."""
    assert frozenset(VALID_DURATIONS_SORTED) == VALID_DURATIONS


# =========================================================================
# parse_fraction
# =========================================================================


class TestParseFraction:
    def test_quarter(self) -> None:
        assert parse_fraction("1/4") == Fraction(1, 4)

    def test_whole(self) -> None:
        assert parse_fraction("1") == Fraction(1)

    def test_dotted_half(self) -> None:
        assert parse_fraction("3/4") == Fraction(3, 4)

    def test_sixteenth(self) -> None:
        assert parse_fraction("1/16") == Fraction(1, 16)

    def test_integer_string(self) -> None:
        assert parse_fraction("2") == Fraction(2)


# =========================================================================
# parse_metre
# =========================================================================


class TestParseMetre:
    def test_four_four(self) -> None:
        bar_length, beat_unit = parse_metre("4/4")
        assert bar_length == Fraction(1)
        assert beat_unit == Fraction(1, 4)

    def test_three_four(self) -> None:
        bar_length, beat_unit = parse_metre("3/4")
        assert bar_length == Fraction(3, 4)
        assert beat_unit == Fraction(1, 4)

    def test_six_eight(self) -> None:
        bar_length, beat_unit = parse_metre("6/8")
        assert bar_length == Fraction(3, 4)
        assert beat_unit == Fraction(1, 8)

    def test_two_four(self) -> None:
        bar_length, beat_unit = parse_metre("2/4")
        assert bar_length == Fraction(1, 2)
        assert beat_unit == Fraction(1, 4)

    def test_two_two(self) -> None:
        bar_length, beat_unit = parse_metre("2/2")
        assert bar_length == Fraction(1)
        assert beat_unit == Fraction(1, 2)
