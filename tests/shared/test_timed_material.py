"""Tests for shared.timed_material.

Tests TimedMaterial class and its transformations.
"""
from fractions import Fraction

import pytest

from shared.pitch import FloatingNote, Rest
from shared.timed_material import TimedMaterial


class TestTimedMaterialConstruction:
    """Test TimedMaterial construction and invariants."""

    def test_valid_construction(self) -> None:
        """Valid construction succeeds."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(3)),
            durations=(Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1, 2),
        )
        assert len(tm) == 2

    def test_budget_mismatch_raises(self) -> None:
        """Budget mismatch raises ValueError."""
        with pytest.raises(ValueError, match="invariant violated"):
            TimedMaterial(
                pitches=(FloatingNote(1),),
                durations=(Fraction(1, 4),),
                budget=Fraction(1, 2),
            )

    def test_length_mismatch_raises(self) -> None:
        """Length mismatch raises ValueError."""
        with pytest.raises(ValueError, match="Length mismatch"):
            TimedMaterial(
                pitches=(FloatingNote(1), FloatingNote(2)),
                durations=(Fraction(1, 4),),
                budget=Fraction(1, 4),
            )

    def test_non_positive_duration_raises(self) -> None:
        """Non-positive duration raises ValueError."""
        with pytest.raises(ValueError, match="Non-positive duration"):
            TimedMaterial(
                pitches=(FloatingNote(1),),
                durations=(Fraction(0),),
                budget=Fraction(0),
            )

    def test_len(self) -> None:
        """__len__ returns note count."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3)),
            durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 4)),
            budget=Fraction(1, 2),
        )
        assert len(tm) == 3


class TestRepeatToBudget:
    """Test repeat_to_budget class method."""

    def test_exact_fill(self) -> None:
        """Pattern fills budget exactly."""
        tm: TimedMaterial = TimedMaterial.repeat_to_budget(
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(1, 4), Fraction(1, 4)],
            budget=Fraction(1, 1),
        )
        assert sum(tm.durations) == Fraction(1, 1)
        assert len(tm) == 4

    def test_with_shift(self) -> None:
        """Shift applies to repeated notes."""
        tm: TimedMaterial = TimedMaterial.repeat_to_budget(
            pitches=[FloatingNote(1)],
            durations=[Fraction(1, 4)],
            budget=Fraction(1, 2),
            shift=2,
        )
        assert all(p.degree == 3 for p in tm.pitches if isinstance(p, FloatingNote))

    def test_rest_not_shifted(self) -> None:
        """Rests are not affected by shift."""
        tm: TimedMaterial = TimedMaterial.repeat_to_budget(
            pitches=[Rest(), FloatingNote(1)],
            durations=[Fraction(1, 4), Fraction(1, 4)],
            budget=Fraction(1, 2),
            shift=2,
        )
        assert isinstance(tm.pitches[0], Rest)

    def test_empty_material_raises(self) -> None:
        """Empty material raises ValueError."""
        with pytest.raises(ValueError, match="empty material"):
            TimedMaterial.repeat_to_budget([], [], Fraction(1, 1))

    def test_partial_note_truncated(self) -> None:
        """Last note truncated to fit budget."""
        tm: TimedMaterial = TimedMaterial.repeat_to_budget(
            pitches=[FloatingNote(1)],
            durations=[Fraction(1, 4)],
            budget=Fraction(3, 8),
        )
        assert sum(tm.durations) == Fraction(3, 8)


class TestShift:
    """Test shift transformation."""

    def test_shift_positive(self) -> None:
        """Positive shift increases degrees."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(3)),
            durations=(Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1, 2),
        )
        shifted: TimedMaterial = tm.shift(2)
        assert shifted.pitches[0].degree == 3
        assert shifted.pitches[1].degree == 5

    def test_shift_wraps(self) -> None:
        """Shift wraps around 1-7."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(6),),
            durations=(Fraction(1, 4),),
            budget=Fraction(1, 4),
        )
        shifted: TimedMaterial = tm.shift(3)
        assert shifted.pitches[0].degree == 2

    def test_shift_preserves_rests(self) -> None:
        """Shift preserves rests."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(Rest(),),
            durations=(Fraction(1, 4),),
            budget=Fraction(1, 4),
        )
        shifted: TimedMaterial = tm.shift(5)
        assert isinstance(shifted.pitches[0], Rest)

    def test_shift_preserves_budget(self) -> None:
        """Shift preserves budget."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1),),
            durations=(Fraction(1, 4),),
            budget=Fraction(1, 4),
        )
        shifted: TimedMaterial = tm.shift(2)
        assert shifted.budget == Fraction(1, 4)


class TestInvert:
    """Test invert transformation."""

    def test_invert_around_default_axis(self) -> None:
        """Invert around default axis (4)."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(5)),
            durations=(Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1, 2),
        )
        inverted: TimedMaterial = tm.invert()
        assert inverted.pitches[0].degree == 7
        assert inverted.pitches[1].degree == 3

    def test_invert_around_custom_axis(self) -> None:
        """Invert around custom axis."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1),),
            durations=(Fraction(1, 4),),
            budget=Fraction(1, 4),
        )
        inverted: TimedMaterial = tm.invert(axis=3)
        assert inverted.pitches[0].degree == 5

    def test_invert_preserves_rests(self) -> None:
        """Invert preserves rests."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(Rest(),),
            durations=(Fraction(1, 4),),
            budget=Fraction(1, 4),
        )
        inverted: TimedMaterial = tm.invert()
        assert isinstance(inverted.pitches[0], Rest)


class TestRetrograde:
    """Test retrograde transformation."""

    def test_retrograde_reverses_pitches(self) -> None:
        """Retrograde reverses pitch order."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3)),
            durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 4)),
            budget=Fraction(1, 2),
        )
        retro: TimedMaterial = tm.retrograde()
        assert retro.pitches[0].degree == 3
        assert retro.pitches[2].degree == 1

    def test_retrograde_reverses_durations(self) -> None:
        """Retrograde reverses duration order."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2)),
            durations=(Fraction(1, 8), Fraction(3, 8)),
            budget=Fraction(1, 2),
        )
        retro: TimedMaterial = tm.retrograde()
        assert retro.durations[0] == Fraction(3, 8)
        assert retro.durations[1] == Fraction(1, 8)

    def test_retrograde_preserves_budget(self) -> None:
        """Retrograde preserves budget."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2)),
            durations=(Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1, 2),
        )
        retro: TimedMaterial = tm.retrograde()
        assert retro.budget == Fraction(1, 2)


class TestHeadTail:
    """Test head and tail fragment methods."""

    def test_head_returns_first_n(self) -> None:
        """Head returns first n notes."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            budget=Fraction(1, 1),
        )
        head: TimedMaterial = tm.head(2)
        assert len(head) == 2
        assert head.pitches[0].degree == 1
        assert head.budget == Fraction(1, 2)

    def test_tail_returns_last_n(self) -> None:
        """Tail returns last n notes."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            budget=Fraction(1, 1),
        )
        tail: TimedMaterial = tm.tail(2)
        assert len(tail) == 2
        assert tail.pitches[0].degree == 2
        assert tail.budget == Fraction(3, 4)

    def test_head_invalid_raises(self) -> None:
        """Invalid head size raises AssertionError."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1),),
            durations=(Fraction(1, 4),),
            budget=Fraction(1, 4),
        )
        with pytest.raises(AssertionError):
            tm.head(0)

    def test_tail_invalid_raises(self) -> None:
        """Invalid tail size raises AssertionError."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1),),
            durations=(Fraction(1, 4),),
            budget=Fraction(1, 4),
        )
        with pytest.raises(AssertionError):
            tm.tail(5)


class TestAugmentDiminish:
    """Test augment and diminish transformations."""

    def test_augment_doubles_durations(self) -> None:
        """Augment doubles all durations."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2)),
            durations=(Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1, 2),
        )
        aug: TimedMaterial = tm.augment()
        assert aug.durations[0] == Fraction(1, 2)
        assert aug.budget == Fraction(1, 1)

    def test_diminish_halves_durations(self) -> None:
        """Diminish halves all durations."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2)),
            durations=(Fraction(1, 2), Fraction(1, 2)),
            budget=Fraction(1, 1),
        )
        dim: TimedMaterial = tm.diminish()
        assert dim.durations[0] == Fraction(1, 4)
        assert dim.budget == Fraction(1, 2)

    def test_diminish_with_floor(self) -> None:
        """Diminish respects minimum duration floor."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1),),
            durations=(Fraction(1, 8),),
            budget=Fraction(1, 8),
        )
        dim: TimedMaterial = tm.diminish(min_dur=Fraction(1, 8))
        assert dim.durations[0] == Fraction(1, 8)

    def test_augment_preserves_pitches(self) -> None:
        """Augment preserves pitch sequence."""
        tm: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(5)),
            durations=(Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1, 2),
        )
        aug: TimedMaterial = tm.augment()
        assert aug.pitches[0].degree == 1
        assert aug.pitches[1].degree == 5
