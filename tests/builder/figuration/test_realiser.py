"""Tests for builder.figuration.realiser module."""
from fractions import Fraction

import pytest

from builder.figuration.loader import clear_cache
from builder.figuration.realiser import (
    apply_augmentation,
    apply_diminution,
    beats_to_whole_notes,
    compute_bar_duration,
    compute_gap_duration,
    generate_default_durations,
    get_hemiola_template,
    get_rhythm_template,
    is_anacrusis_beat,
    realise_figure_to_bar,
    realise_rhythm,
)
from builder.figuration.types import Figure, RhythmTemplate


def make_figure(
    name: str = "test",
    degrees: tuple[int, ...] = (0, 1),
) -> Figure:
    """Helper to create test figures."""
    return Figure(
        name=name,
        degrees=degrees,
        contour="test",
        polarity="balanced",
        arrival="direct",
        placement="span",
        character="plain",
        harmonic_tension="low",
        max_density="medium",
        cadential_safe=True,
        repeatable=True,
        requires_compensation=False,
        compensation_direction=None,
        is_compound=False,
        minor_safe=True,
        requires_leading_tone=False,
        weight=1.0,
    )


class TestGetRhythmTemplate:
    """Tests for get_rhythm_template function."""

    def test_returns_template_for_valid_params(self) -> None:
        """Should return template for valid parameters."""
        clear_cache()
        template = get_rhythm_template(4, "4/4", False)
        assert template is not None
        assert template.note_count == 4
        assert template.metre == "4/4"

    def test_returns_none_for_invalid_params(self) -> None:
        """Should return None for invalid parameters."""
        template = get_rhythm_template(100, "99/99", False)
        assert template is None

    def test_fallback_to_standard_if_overdotted_missing(self) -> None:
        """Should fall back to standard if overdotted not available."""
        # Most note counts have standard, some don't have overdotted
        template = get_rhythm_template(5, "4/4", overdotted=True)
        # Should get standard version if overdotted missing
        if template:
            assert template.note_count == 5


class TestApplyAugmentation:
    """Tests for apply_augmentation function."""

    def test_doubles_durations(self) -> None:
        """Factor 2 should double all durations."""
        template = RhythmTemplate(
            note_count=2,
            metre="4/4",
            durations=(Fraction(1), Fraction(1)),
            overdotted=False,
        )
        result = apply_augmentation(template, 2)
        assert result.durations == (Fraction(2), Fraction(2))

    def test_preserves_note_count(self) -> None:
        """Augmentation should preserve note count."""
        template = RhythmTemplate(
            note_count=3,
            metre="3/4",
            durations=(Fraction(1), Fraction(1), Fraction(1)),
            overdotted=False,
        )
        result = apply_augmentation(template, 2)
        assert result.note_count == 3
        assert len(result.durations) == 3

    def test_zero_factor_rejected(self) -> None:
        """Zero factor should raise."""
        template = RhythmTemplate(
            note_count=2,
            metre="4/4",
            durations=(Fraction(1), Fraction(1)),
            overdotted=False,
        )
        with pytest.raises(AssertionError, match="positive"):
            apply_augmentation(template, 0)


class TestApplyDiminution:
    """Tests for apply_diminution function."""

    def test_halves_durations(self) -> None:
        """Factor 2 should halve all durations."""
        template = RhythmTemplate(
            note_count=2,
            metre="4/4",
            durations=(Fraction(2), Fraction(2)),
            overdotted=False,
        )
        result = apply_diminution(template, 2)
        assert result.durations == (Fraction(1), Fraction(1))


class TestComputeBarDuration:
    """Tests for compute_bar_duration function."""

    def test_four_four(self) -> None:
        """4/4 should be 1 whole note."""
        assert compute_bar_duration("4/4") == Fraction(1)

    def test_three_four(self) -> None:
        """3/4 should be 3/4 of a whole note."""
        assert compute_bar_duration("3/4") == Fraction(3, 4)

    def test_two_four(self) -> None:
        """2/4 should be 1/2 of a whole note."""
        assert compute_bar_duration("2/4") == Fraction(1, 2)

    def test_six_eight(self) -> None:
        """6/8 should be 3/4 of a whole note."""
        assert compute_bar_duration("6/8") == Fraction(6, 8)


class TestBeatsToWholeNotes:
    """Tests for beats_to_whole_notes function."""

    def test_four_four_one_beat(self) -> None:
        """1 beat in 4/4 = 1/4 whole note."""
        assert beats_to_whole_notes(Fraction(1), "4/4") == Fraction(1, 4)

    def test_three_four_one_beat(self) -> None:
        """1 beat in 3/4 = 1/4 whole note."""
        assert beats_to_whole_notes(Fraction(1), "3/4") == Fraction(1, 4)

    def test_six_eight_one_beat(self) -> None:
        """1 beat in 6/8 = 1/8 whole note."""
        assert beats_to_whole_notes(Fraction(1), "6/8") == Fraction(1, 8)


class TestGenerateDefaultDurations:
    """Tests for generate_default_durations function."""

    def test_even_distribution(self) -> None:
        """Should evenly distribute duration."""
        result = generate_default_durations(4, Fraction(1))
        assert result == (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))

    def test_sums_to_total(self) -> None:
        """Result should sum to bar duration."""
        result = generate_default_durations(3, Fraction(3, 4))
        assert sum(result) == Fraction(3, 4)


class TestRealiseRhythm:
    """Tests for realise_rhythm function."""

    def test_returns_correct_count(self) -> None:
        """Should return correct number of durations."""
        clear_cache()
        figure = make_figure(degrees=(0, 1, 2))
        result = realise_rhythm(
            figure=figure,
            gap_duration=Fraction(1),
            metre="4/4",
            bar_function="passing",
            rhythmic_unit=Fraction(1, 4),
            next_anchor_strength="strong",
        )
        assert len(result) == 3

    def test_sums_to_gap(self) -> None:
        """Durations should sum to gap duration."""
        figure = make_figure(degrees=(0, 1, 2, 3))
        gap = Fraction(3, 4)
        result = realise_rhythm(
            figure=figure,
            gap_duration=gap,
            metre="3/4",
            bar_function="passing",
            rhythmic_unit=Fraction(1, 4),
            next_anchor_strength="strong",
        )
        assert sum(result) == gap

    def test_all_durations_positive(self) -> None:
        """All durations should be positive."""
        figure = make_figure(degrees=(0, 1, 2))
        result = realise_rhythm(
            figure=figure,
            gap_duration=Fraction(1),
            metre="4/4",
            bar_function="passing",
            rhythmic_unit=Fraction(1, 4),
            next_anchor_strength="strong",
        )
        assert all(d > 0 for d in result)


class TestRealiseFigureToBar:
    """Tests for realise_figure_to_bar function."""

    def test_returns_figured_bar(self) -> None:
        """Should return FiguredBar."""
        figure = make_figure(degrees=(0, 1))
        result = realise_figure_to_bar(
            figure=figure,
            bar=1,
            start_degree=1,
            gap_duration=Fraction(1),
            metre="4/4",
        )
        assert result.bar == 1
        assert result.figure_name == "test"

    def test_absolute_degrees_correct(self) -> None:
        """Absolute degrees should be correctly computed."""
        figure = make_figure(degrees=(0, 1, 2))  # relative: start, +1, +2
        result = realise_figure_to_bar(
            figure=figure,
            bar=1,
            start_degree=3,  # Start on degree 3
            gap_duration=Fraction(1),
            metre="4/4",
        )
        # 3 + 0 = 3, 3 + 1 = 4, 3 + 2 = 5
        assert result.degrees == (3, 4, 5)

    def test_degrees_wrap_correctly(self) -> None:
        """Degrees should wrap around 1-7 range."""
        figure = make_figure(degrees=(0, 1, 2))
        result = realise_figure_to_bar(
            figure=figure,
            bar=1,
            start_degree=6,  # Start on degree 6
            gap_duration=Fraction(1),
            metre="4/4",
        )
        # 6 + 0 = 6, 6 + 1 = 7, 6 + 2 = 8 -> 1
        assert result.degrees == (6, 7, 1)

    def test_durations_match_count(self) -> None:
        """Duration count should match degree count."""
        figure = make_figure(degrees=(0, 1, 2, 3))
        result = realise_figure_to_bar(
            figure=figure,
            bar=1,
            start_degree=1,
            gap_duration=Fraction(1),
            metre="4/4",
        )
        assert len(result.durations) == len(result.degrees)


class TestComputeGapDuration:
    """Tests for compute_gap_duration function."""

    def test_positive_gap(self) -> None:
        """Should compute positive gap."""
        gap = compute_gap_duration(Fraction(0), Fraction(1))
        assert gap == Fraction(1)

    def test_fractional_gap(self) -> None:
        """Should handle fractional values."""
        gap = compute_gap_duration(Fraction(1, 4), Fraction(3, 4))
        assert gap == Fraction(1, 2)

    def test_zero_gap_rejected(self) -> None:
        """Zero or negative gap should raise."""
        with pytest.raises(AssertionError, match="positive"):
            compute_gap_duration(Fraction(1), Fraction(1))


class TestIsAnacrusis:
    """Tests for is_anacrusis_beat function."""

    def test_beat_3_in_3_4_with_strong_next(self) -> None:
        """Beat 3 in 3/4 should be anacrusis if next is strong."""
        assert is_anacrusis_beat(Fraction(1, 2), "3/4", "strong")

    def test_beat_1_in_3_4_not_anacrusis(self) -> None:
        """Beat 1 in 3/4 should not be anacrusis."""
        assert not is_anacrusis_beat(Fraction(0), "3/4", "strong")

    def test_any_beat_weak_next_not_anacrusis(self) -> None:
        """Any beat with weak next anchor should not be anacrusis."""
        assert not is_anacrusis_beat(Fraction(1, 2), "3/4", "weak")

    def test_beat_4_in_4_4_with_strong_next(self) -> None:
        """Beat 4 in 4/4 should be anacrusis if next is strong."""
        assert is_anacrusis_beat(Fraction(3, 4), "4/4", "strong")
