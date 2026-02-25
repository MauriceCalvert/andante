"""Unit tests for shared/music_math.py — duration arithmetic."""
import pytest
from fractions import Fraction

from shared.music_math import (
    MusicMathError,
    VALID_DURATIONS,
    VALID_DURATIONS_SORTED,
    fill_slot,
    is_valid_duration,
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


# =========================================================================
# is_valid_duration
# =========================================================================


@pytest.mark.parametrize("dur, expected", [
    (Fraction(1, 4), True),    # quarter
    (Fraction(1, 2), True),    # half
    (Fraction(1, 1), True),    # whole
    (Fraction(3, 8), True),    # dotted quarter
    (Fraction(1, 8), True),    # eighth
    (Fraction(1, 16), True),   # sixteenth
    (Fraction(1, 32), True),   # thirty-second
    (Fraction(3, 4), True),    # dotted half
    (Fraction(3, 16), True),   # dotted eighth
    (Fraction(3, 32), True),   # dotted sixteenth
    (Fraction(2, 1), True),    # breve
    (Fraction(3, 2), True),    # dotted whole
    (Fraction(1, 3), False),   # triplet — not valid
    (Fraction(1, 5), False),   # quintuplet — not valid
    (Fraction(2, 3), False),   # not a standard duration
    (Fraction(5, 8), False),   # no such duration
])
def test_is_valid_duration(dur: Fraction, expected: bool) -> None:
    """Duration validity check."""
    assert is_valid_duration(duration=dur) is expected


# =========================================================================
# fill_slot — uniform
# =========================================================================


@pytest.mark.parametrize("target, note_count, expected", [
    # exact division: 1/2 into 2 quarters
    (Fraction(1, 2), 2, [Fraction(1, 4)] * 2),
    # exact division: 1/4 into 2 eighths
    (Fraction(1, 4), 2, [Fraction(1, 8)] * 2),
    # exact: whole note as 4 quarters
    (Fraction(1, 1), 4, [Fraction(1, 4)] * 4),
    # exact: 3/4 bar as 3 quarters
    (Fraction(3, 4), 3, [Fraction(1, 4)] * 3),
])
def test_fill_slot_uniform_exact(
    target: Fraction,
    note_count: int,
    expected: list[Fraction],
) -> None:
    """Uniform fill with exact division."""
    result: list[Fraction] = fill_slot(
        target=target,
        note_count=note_count,
        style="uniform",
    )
    assert result == expected


def test_fill_slot_uniform_fallback_to_nearby_count() -> None:
    """Uniform fill that can't divide exactly tries nearby counts."""
    result: list[Fraction] = fill_slot(
        target=Fraction(1, 2),
        note_count=3,
        style="uniform",
    )
    assert sum(result) == Fraction(1, 2)
    assert all(is_valid_duration(duration=d) for d in result)


def test_fill_slot_uniform_fallback_to_greedy() -> None:
    """Uniform fill that can't find exact or nearby falls back to greedy."""
    result: list[Fraction] = fill_slot(
        target=Fraction(3, 4),
        note_count=5,
        style="uniform",
    )
    assert sum(result) == Fraction(3, 4)
    assert all(is_valid_duration(duration=d) for d in result)


# =========================================================================
# fill_slot — long_short
# =========================================================================


def test_fill_slot_long_short_dotted_quarter() -> None:
    """Long-short with dotted quarter + eighth pair."""
    result: list[Fraction] = fill_slot(
        target=Fraction(1, 2),
        note_count=2,
        style="long_short",
    )
    assert sum(result) == Fraction(1, 2)
    assert all(is_valid_duration(duration=d) for d in result)


def test_fill_slot_long_short_fallback() -> None:
    """Long-short falls back to uniform when no pair fits."""
    result: list[Fraction] = fill_slot(
        target=Fraction(1, 4),
        note_count=2,
        style="long_short",
    )
    assert sum(result) == Fraction(1, 4)
    assert all(is_valid_duration(duration=d) for d in result)


# =========================================================================
# fill_slot — varied
# =========================================================================


def test_fill_slot_varied_greedy() -> None:
    """Varied fills greedily with largest valid durations."""
    result: list[Fraction] = fill_slot(
        target=Fraction(3, 4),
        note_count=2,
        style="varied",
    )
    assert sum(result) == Fraction(3, 4)
    assert all(is_valid_duration(duration=d) for d in result)
    # greedy picks largest first
    for i in range(len(result) - 1):
        assert result[i] >= result[i + 1]


# =========================================================================
# fill_slot — error cases
# =========================================================================


def test_fill_slot_zero_count_raises() -> None:
    """Zero note count raises."""
    with pytest.raises(MusicMathError, match="note_count must be positive"):
        fill_slot(target=Fraction(1, 4), note_count=0)


def test_fill_slot_negative_count_raises() -> None:
    """Negative note count raises."""
    with pytest.raises(MusicMathError, match="note_count must be positive"):
        fill_slot(target=Fraction(1, 4), note_count=-1)


def test_fill_slot_unknown_style_raises() -> None:
    """Unknown style raises."""
    with pytest.raises(MusicMathError, match="Unknown fill style"):
        fill_slot(target=Fraction(1, 4), note_count=2, style="swing")


# =========================================================================
# fill_slot — sum invariant across all styles
# =========================================================================


@pytest.mark.parametrize("target", [
    Fraction(1, 4),
    Fraction(1, 2),
    Fraction(3, 4),
    Fraction(1, 1),
])
@pytest.mark.parametrize("style", ["uniform", "long_short", "varied"])
def test_fill_slot_sum_invariant(target: Fraction, style: str) -> None:
    """Result always sums exactly to target regardless of style."""
    result: list[Fraction] = fill_slot(
        target=target,
        note_count=2,
        style=style,
    )
    assert sum(result) == target
    assert all(is_valid_duration(duration=d) for d in result)
