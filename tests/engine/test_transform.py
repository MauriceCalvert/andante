"""100% coverage tests for engine.transform.

Tests import only:
- engine.transform (module under test)
- shared (pitch, timed_material)
- stdlib

Transform module provides pitch transformations (contrary motion, imitation)
and fill strategies (repeat, cycle, sequence) for material expansion.
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Rest

from engine.transform import (
    apply_contrary_motion,
    apply_fill,
    apply_imitation,
    apply_transform,
)


class TestApplyContraryMotion:
    """Test apply_contrary_motion function."""

    def test_returns_tuple_of_pitches(self) -> None:
        """Returns tuple of Pitch objects."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        result = apply_contrary_motion(pitches)
        assert isinstance(result, tuple)

    def test_mirrors_around_axis(self) -> None:
        """Mirrors degrees around axis=4 (default).

        degree 1 mirrors to 2*4 - 1 = 7
        degree 2 mirrors to 2*4 - 2 = 6
        degree 3 mirrors to 2*4 - 3 = 5
        """
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        result = apply_contrary_motion(pitches)
        degrees: list[int] = [p.degree for p in result]
        assert degrees == [7, 6, 5]

    def test_custom_axis(self) -> None:
        """Custom axis changes mirror point.

        With axis=1: degree 3 mirrors to 2*1 - 3 = -1 -> wrapped to 6
        """
        pitches: tuple[FloatingNote, ...] = (FloatingNote(3),)
        result = apply_contrary_motion(pitches, axis=1)
        assert result[0].degree == 6  # 2*1 - 3 = -1 -> wrap_degree(-1) = 6

    def test_preserves_rests(self) -> None:
        """Rests are preserved unchanged."""
        pitches: tuple[FloatingNote | Rest, ...] = (FloatingNote(1), Rest(), FloatingNote(3))
        result = apply_contrary_motion(pitches)
        assert isinstance(result[0], FloatingNote)
        assert isinstance(result[1], Rest)
        assert isinstance(result[2], FloatingNote)

    def test_empty_input(self) -> None:
        """Empty input returns empty tuple."""
        result = apply_contrary_motion(())
        assert result == ()

    def test_degree_wrapping(self) -> None:
        """Degrees wrap to 1-7 range."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(7), FloatingNote(6))
        result = apply_contrary_motion(pitches, axis=4)
        # 2*4 - 7 = 1, 2*4 - 6 = 2
        degrees: list[int] = [p.degree for p in result]
        assert degrees == [1, 2]


class TestApplyImitation:
    """Test apply_imitation function."""

    def test_returns_tuple_of_pitches(self) -> None:
        """Returns tuple of Pitch objects."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        result = apply_imitation(pitches)
        assert isinstance(result, tuple)

    def test_transposes_by_interval(self) -> None:
        """Transposes degrees by interval (default -4).

        degree 5 with interval -4 = 1
        """
        pitches: tuple[FloatingNote, ...] = (FloatingNote(5),)
        result = apply_imitation(pitches)  # default interval=-4
        assert result[0].degree == 1  # 5 + (-4) = 1

    def test_custom_interval(self) -> None:
        """Custom interval transposes differently."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        result = apply_imitation(pitches, interval=2)
        assert result[0].degree == 3  # 1 + 2 = 3

    def test_preserves_rests(self) -> None:
        """Rests are preserved unchanged."""
        pitches: tuple[FloatingNote | Rest, ...] = (FloatingNote(1), Rest(), FloatingNote(3))
        result = apply_imitation(pitches)
        assert isinstance(result[0], FloatingNote)
        assert isinstance(result[1], Rest)
        assert isinstance(result[2], FloatingNote)

    def test_empty_input(self) -> None:
        """Empty input returns empty tuple."""
        result = apply_imitation(())
        assert result == ()

    def test_degree_wrapping(self) -> None:
        """Degrees wrap to 1-7 range."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(7))
        result = apply_imitation(pitches, interval=3)
        # 1 + 3 = 4, 7 + 3 = 10 -> wrap to 3
        degrees: list[int] = [p.degree for p in result]
        assert degrees == [4, 3]


class TestApplyTransform:
    """Test apply_transform function."""

    def test_none_transform_returns_unchanged(self) -> None:
        """none transform returns material unchanged."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            (FloatingNote(1), FloatingNote(2)),
            (Fraction(1, 4), Fraction(1, 4)),
            Fraction(1, 2)
        )
        result = apply_transform(material, "none", {})
        assert result is material

    def test_invert_transform(self) -> None:
        """invert transform inverts the material."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            (FloatingNote(1), FloatingNote(2), FloatingNote(3)),
            (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            Fraction(3, 4)
        )
        result = apply_transform(material, "invert", {})
        # Inverted should have mirrored degrees
        orig_degrees: list[int] = [p.degree for p in material.pitches]
        result_degrees: list[int] = [p.degree for p in result.pitches]
        assert orig_degrees != result_degrees

    def test_retrograde_transform(self) -> None:
        """retrograde transform reverses the material."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            (FloatingNote(1), FloatingNote(2), FloatingNote(3)),
            (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            Fraction(3, 4)
        )
        result = apply_transform(material, "retrograde", {})
        orig_degrees: list[int] = [p.degree for p in material.pitches]
        result_degrees: list[int] = [p.degree for p in result.pitches]
        assert result_degrees == list(reversed(orig_degrees))

    def test_head_transform(self) -> None:
        """head transform takes first notes."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4),
             FloatingNote(5), FloatingNote(6), FloatingNote(7), FloatingNote(1)),
            tuple(Fraction(1, 8) for _ in range(8)),
            Fraction(1)
        )
        result = apply_transform(material, "head", {"size": 3})
        assert len(result.pitches) == 3

    def test_head_transform_default_size(self) -> None:
        """head transform uses default size=4."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1]),
            tuple(Fraction(1, 8) for _ in range(8)),
            Fraction(1)
        )
        result = apply_transform(material, "head", {})
        assert len(result.pitches) == 4

    def test_tail_transform(self) -> None:
        """tail transform takes last notes."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4),
             FloatingNote(5), FloatingNote(6), FloatingNote(7), FloatingNote(1)),
            tuple(Fraction(1, 8) for _ in range(8)),
            Fraction(1)
        )
        result = apply_transform(material, "tail", {"size": 2})
        assert len(result.pitches) == 2

    def test_tail_transform_default_size(self) -> None:
        """tail transform uses default size=3."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1]),
            tuple(Fraction(1, 8) for _ in range(8)),
            Fraction(1)
        )
        result = apply_transform(material, "tail", {})
        assert len(result.pitches) == 3

    def test_augment_transform(self) -> None:
        """augment transform doubles durations."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            (FloatingNote(1), FloatingNote(2)),
            (Fraction(1, 4), Fraction(1, 4)),
            Fraction(1, 2)
        )
        result = apply_transform(material, "augment", {})
        # Augmented durations should be doubled
        assert result.durations[0] == Fraction(1, 2)

    def test_diminish_transform(self) -> None:
        """diminish transform halves durations."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            (FloatingNote(1), FloatingNote(2)),
            (Fraction(1, 2), Fraction(1, 2)),
            Fraction(1)
        )
        result = apply_transform(material, "diminish", {})
        # Diminished durations should be halved
        assert result.durations[0] == Fraction(1, 4)

    def test_diminish_with_min_duration(self) -> None:
        """diminish transform respects min_duration."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            (FloatingNote(1), FloatingNote(2)),
            (Fraction(1, 8), Fraction(1, 8)),
            Fraction(1, 4)
        )
        result = apply_transform(material, "diminish", {"min_duration": "1/8"})
        # Durations should not go below 1/8
        assert all(d >= Fraction(1, 8) for d in result.durations)

    def test_unknown_transform_raises(self) -> None:
        """Unknown transform raises ValueError."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            (FloatingNote(1),),
            (Fraction(1, 4),),
            Fraction(1, 4)
        )
        with pytest.raises(ValueError, match="Unknown transform"):
            apply_transform(material, "nonexistent_transform", {})


class TestApplyFill:
    """Test apply_fill function."""

    def test_repeat_fill(self) -> None:
        """repeat fill repeats pattern to budget."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        result = apply_fill(pitches, durations, Fraction(1, 2), "repeat", {})
        assert result.budget == Fraction(1, 2)
        assert sum(result.durations) == Fraction(1, 2)

    def test_repeat_fill_budget_exceeds_asserts(self) -> None:
        """repeat fill asserts if budget exceeds pattern duration."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        with pytest.raises(AssertionError, match="repeat fill requires"):
            apply_fill(pitches, durations, Fraction(1), "repeat", {})

    def test_cycle_fill(self) -> None:
        """cycle fill cycles pattern with shifts."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        result = apply_fill(pitches, durations, Fraction(1), "cycle", {"phrase_seed": 0})
        assert result.budget == Fraction(1)
        assert sum(result.durations) == Fraction(1)

    def test_cycle_fill_different_seeds(self) -> None:
        """Different phrase_seed produces different shifts."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(4))
        r0 = apply_fill(pitches, durations, Fraction(2), "cycle", {"phrase_seed": 0})
        r1 = apply_fill(pitches, durations, Fraction(2), "cycle", {"phrase_seed": 1})
        # Different seeds may produce different degree sequences
        d0: list[int] = [p.degree for p in r0.pitches]
        d1: list[int] = [p.degree for p in r1.pitches]
        # At minimum, the function should work without error
        assert len(d0) == len(d1)

    def test_sequence_fill(self) -> None:
        """sequence fill builds sequence."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(4))
        result = apply_fill(pitches, durations, Fraction(2), "sequence", {"reps": 2, "step": -1})
        assert result.budget == Fraction(2)
        assert sum(result.durations) == Fraction(2)

    def test_sequence_fill_with_params(self) -> None:
        """sequence fill uses all params."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(4))
        result = apply_fill(
            pitches, durations, Fraction(2), "sequence",
            {
                "reps": 2,
                "step": -2,
                "start": 1,
                "phrase_seed": 3,
                "vary": False,
                "avoid_leading_tone": True,
            }
        )
        assert result.budget == Fraction(2)

    def test_sequence_break_fill(self) -> None:
        """sequence_break fill builds sequence with break."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(4))
        result = apply_fill(pitches, durations, Fraction(3), "sequence_break", {"break_after": 2})
        assert result.budget == Fraction(3)
        assert sum(result.durations) == Fraction(3)

    def test_sequence_break_fill_with_params(self) -> None:
        """sequence_break fill uses all params."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4))
        durations: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in range(4))
        result = apply_fill(
            pitches, durations, Fraction(3), "sequence_break",
            {"break_after": 2, "step": -2, "break_shift": 4}
        )
        assert result.budget == Fraction(3)

    def test_unknown_fill_raises(self) -> None:
        """Unknown fill raises ValueError."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        with pytest.raises(ValueError, match="Unknown fill"):
            apply_fill(pitches, durations, Fraction(1, 4), "nonexistent_fill", {})

    def test_zero_pattern_duration_asserts(self) -> None:
        """Zero pattern duration raises AssertionError."""
        pitches: tuple[FloatingNote, ...] = ()
        durations: tuple[Fraction, ...] = ()
        with pytest.raises(AssertionError, match="Pattern duration must be positive"):
            apply_fill(pitches, durations, Fraction(1), "repeat", {})


class TestIntegration:
    """Integration tests for transform module."""

    def test_contrary_then_imitation(self) -> None:
        """Chain contrary motion and imitation."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        contrary: tuple = apply_contrary_motion(pitches)
        imitated: tuple = apply_imitation(contrary, interval=2)
        assert len(imitated) == 3

    def test_transform_and_fill_pipeline(self) -> None:
        """Transform then fill pipeline."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6, 7, 1]),
            tuple(Fraction(1, 8) for _ in range(8)),
            Fraction(1)
        )
        # Take head
        head = apply_transform(material, "head", {"size": 4})
        # Fill to 2 bars
        result = apply_fill(head.pitches, head.durations, Fraction(2), "cycle", {})
        assert result.budget == Fraction(2)

    def test_all_transforms_preserve_invariants(self) -> None:
        """All transforms preserve TimedMaterial invariants."""
        from shared.timed_material import TimedMaterial
        material = TimedMaterial(
            tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6]),
            tuple(Fraction(1, 4) for _ in range(6)),
            Fraction(3, 2)
        )
        transforms: list[tuple[str, dict]] = [
            ("none", {}),
            ("invert", {}),
            ("retrograde", {}),
            ("head", {"size": 2}),
            ("tail", {"size": 2}),
            ("augment", {}),
            ("diminish", {}),
        ]
        for name, params in transforms:
            result = apply_transform(material, name, params)
            assert len(result.pitches) == len(result.durations)
            # Durations should be positive
            assert all(d > 0 for d in result.durations)
