"""Tests for builder.figuration.types module."""
from fractions import Fraction

import pytest

from builder.figuration.types import (
    CadentialFigure,
    Figure,
    FiguredBar,
    PhrasePosition,
    RhythmTemplate,
    SelectionContext,
)


class TestFigure:
    """Tests for Figure dataclass."""

    def test_valid_figure_creation(self) -> None:
        """Figure with valid fields should create successfully."""
        fig = Figure(
            name="test_figure",
            degrees=(0, 1, 2),
            contour="ascending",
            polarity="upper",
            arrival="stepwise",
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
        assert fig.name == "test_figure"
        assert fig.degrees == (0, 1, 2)
        assert fig.weight == 1.0

    def test_empty_name_rejected(self) -> None:
        """Figure with empty name should be rejected."""
        with pytest.raises(AssertionError, match="name cannot be empty"):
            Figure(
                name="",
                degrees=(0, 1),
                contour="test",
                polarity="upper",
                arrival="direct",
                placement="span",
                character="plain",
                harmonic_tension="low",
                max_density="low",
                cadential_safe=True,
                repeatable=True,
                requires_compensation=False,
                compensation_direction=None,
                is_compound=False,
                minor_safe=True,
                requires_leading_tone=False,
                weight=1.0,
            )

    def test_single_degree_rejected(self) -> None:
        """Figure with only one degree should be rejected."""
        with pytest.raises(AssertionError, match="at least 2 degrees"):
            Figure(
                name="bad",
                degrees=(0,),
                contour="test",
                polarity="upper",
                arrival="direct",
                placement="span",
                character="plain",
                harmonic_tension="low",
                max_density="low",
                cadential_safe=True,
                repeatable=True,
                requires_compensation=False,
                compensation_direction=None,
                is_compound=False,
                minor_safe=True,
                requires_leading_tone=False,
                weight=1.0,
            )

    def test_invalid_polarity_rejected(self) -> None:
        """Figure with invalid polarity should be rejected."""
        with pytest.raises(AssertionError, match="Invalid polarity"):
            Figure(
                name="bad",
                degrees=(0, 1),
                contour="test",
                polarity="sideways",
                arrival="direct",
                placement="span",
                character="plain",
                harmonic_tension="low",
                max_density="low",
                cadential_safe=True,
                repeatable=True,
                requires_compensation=False,
                compensation_direction=None,
                is_compound=False,
                minor_safe=True,
                requires_leading_tone=False,
                weight=1.0,
            )

    def test_invalid_arrival_rejected(self) -> None:
        """Figure with invalid arrival should be rejected."""
        with pytest.raises(AssertionError, match="Invalid arrival"):
            Figure(
                name="bad",
                degrees=(0, 1),
                contour="test",
                polarity="upper",
                arrival="jumping",
                placement="span",
                character="plain",
                harmonic_tension="low",
                max_density="low",
                cadential_safe=True,
                repeatable=True,
                requires_compensation=False,
                compensation_direction=None,
                is_compound=False,
                minor_safe=True,
                requires_leading_tone=False,
                weight=1.0,
            )

    def test_invalid_character_rejected(self) -> None:
        """Figure with invalid character should be rejected."""
        with pytest.raises(AssertionError, match="Invalid character"):
            Figure(
                name="bad",
                degrees=(0, 1),
                contour="test",
                polarity="upper",
                arrival="direct",
                placement="span",
                character="boring",
                harmonic_tension="low",
                max_density="low",
                cadential_safe=True,
                repeatable=True,
                requires_compensation=False,
                compensation_direction=None,
                is_compound=False,
                minor_safe=True,
                requires_leading_tone=False,
                weight=1.0,
            )

    def test_zero_weight_rejected(self) -> None:
        """Figure with zero weight should be rejected."""
        with pytest.raises(AssertionError, match="Weight must be positive"):
            Figure(
                name="bad",
                degrees=(0, 1),
                contour="test",
                polarity="upper",
                arrival="direct",
                placement="span",
                character="plain",
                harmonic_tension="low",
                max_density="low",
                cadential_safe=True,
                repeatable=True,
                requires_compensation=False,
                compensation_direction=None,
                is_compound=False,
                minor_safe=True,
                requires_leading_tone=False,
                weight=0.0,
            )

    def test_figure_is_frozen(self) -> None:
        """Figure should be immutable."""
        fig = Figure(
            name="test",
            degrees=(0, 1),
            contour="test",
            polarity="upper",
            arrival="direct",
            placement="span",
            character="plain",
            harmonic_tension="low",
            max_density="low",
            cadential_safe=True,
            repeatable=True,
            requires_compensation=False,
            compensation_direction=None,
            is_compound=False,
            minor_safe=True,
            requires_leading_tone=False,
            weight=1.0,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            fig.name = "changed"  # type: ignore


class TestCadentialFigure:
    """Tests for CadentialFigure dataclass."""

    def test_valid_cadential_figure(self) -> None:
        """CadentialFigure with valid fields should create successfully."""
        fig = CadentialFigure(
            name="trill_resolution",
            degrees=(0, 1, 0, 1, 0, -1),
            contour="trilled_resolution",
            trill_position=0,
            hemiola=False,
        )
        assert fig.name == "trill_resolution"
        assert fig.trill_position == 0
        assert not fig.hemiola

    def test_null_trill_position_valid(self) -> None:
        """CadentialFigure with null trill_position should be valid."""
        fig = CadentialFigure(
            name="simple",
            degrees=(0, -1),
            contour="descending",
            trill_position=None,
            hemiola=False,
        )
        assert fig.trill_position is None

    def test_invalid_trill_position_rejected(self) -> None:
        """CadentialFigure with out-of-range trill_position should be rejected."""
        with pytest.raises(AssertionError, match="trill_position.*out of range"):
            CadentialFigure(
                name="bad",
                degrees=(0, 1),
                contour="test",
                trill_position=5,
                hemiola=False,
            )

    def test_empty_name_rejected(self) -> None:
        """CadentialFigure with empty name should be rejected."""
        with pytest.raises(AssertionError, match="name cannot be empty"):
            CadentialFigure(
                name="",
                degrees=(0, 1),
                contour="test",
                trill_position=None,
                hemiola=False,
            )


class TestPhrasePosition:
    """Tests for PhrasePosition dataclass."""

    def test_valid_phrase_position(self) -> None:
        """PhrasePosition with valid fields should create successfully."""
        pos = PhrasePosition(
            position="opening",
            bars=(1, 2),
            character="plain",
            sequential=False,
        )
        assert pos.position == "opening"
        assert pos.bars == (1, 2)
        assert not pos.sequential

    def test_invalid_position_rejected(self) -> None:
        """PhrasePosition with invalid position should be rejected."""
        with pytest.raises(AssertionError, match="Invalid position"):
            PhrasePosition(
                position="middle",
                bars=(1, 2),
                character="plain",
                sequential=False,
            )

    def test_invalid_bar_range_rejected(self) -> None:
        """PhrasePosition with invalid bar range should be rejected."""
        with pytest.raises(AssertionError, match="Invalid bar range"):
            PhrasePosition(
                position="opening",
                bars=(5, 2),  # End before start
                character="plain",
                sequential=False,
            )

    def test_invalid_character_rejected(self) -> None:
        """PhrasePosition with invalid character should be rejected."""
        with pytest.raises(AssertionError, match="Invalid character"):
            PhrasePosition(
                position="opening",
                bars=(1, 2),
                character="boring",
                sequential=False,
            )


class TestRhythmTemplate:
    """Tests for RhythmTemplate dataclass."""

    def test_valid_rhythm_template(self) -> None:
        """RhythmTemplate with valid fields should create successfully."""
        template = RhythmTemplate(
            note_count=3,
            metre="4/4",
            durations=(Fraction(2), Fraction(1), Fraction(1)),
            overdotted=False,
        )
        assert template.note_count == 3
        assert template.metre == "4/4"
        assert len(template.durations) == 3

    def test_mismatched_count_rejected(self) -> None:
        """RhythmTemplate with mismatched duration count should be rejected."""
        with pytest.raises(AssertionError, match="durations length.*!= note_count"):
            RhythmTemplate(
                note_count=3,
                metre="4/4",
                durations=(Fraction(2), Fraction(2)),  # Only 2 durations
                overdotted=False,
            )

    def test_zero_duration_rejected(self) -> None:
        """RhythmTemplate with zero duration should be rejected."""
        with pytest.raises(AssertionError, match="All durations must be positive"):
            RhythmTemplate(
                note_count=2,
                metre="4/4",
                durations=(Fraction(2), Fraction(0)),
                overdotted=False,
            )

    def test_single_note_rejected(self) -> None:
        """RhythmTemplate with single note should be rejected."""
        with pytest.raises(AssertionError, match="note_count must be >= 2"):
            RhythmTemplate(
                note_count=1,
                metre="4/4",
                durations=(Fraction(4),),
                overdotted=False,
            )


class TestFiguredBar:
    """Tests for FiguredBar dataclass."""

    def test_valid_figured_bar(self) -> None:
        """FiguredBar with valid fields should create successfully."""
        bar = FiguredBar(
            bar=1,
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            figure_name="test_figure",
        )
        assert bar.bar == 1
        assert bar.degrees == (1, 2, 3)
        assert len(bar.durations) == 3

    def test_bar_zero_rejected(self) -> None:
        """FiguredBar with bar 0 should be rejected."""
        with pytest.raises(AssertionError, match="bar must be >= 1"):
            FiguredBar(
                bar=0,
                degrees=(1, 2),
                durations=(Fraction(1, 2), Fraction(1, 2)),
                figure_name="test",
            )

    def test_mismatched_lengths_rejected(self) -> None:
        """FiguredBar with mismatched degrees and durations should be rejected."""
        with pytest.raises(AssertionError, match="degrees length.*!= durations length"):
            FiguredBar(
                bar=1,
                degrees=(1, 2, 3),
                durations=(Fraction(1, 2), Fraction(1, 2)),
                figure_name="test",
            )

    def test_invalid_degree_rejected(self) -> None:
        """FiguredBar with degree outside 1-7 should be rejected."""
        with pytest.raises(AssertionError, match="degrees must be in range 1-7"):
            FiguredBar(
                bar=1,
                degrees=(0, 1, 2),  # 0 is invalid
                durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
                figure_name="test",
            )


class TestSelectionContext:
    """Tests for SelectionContext dataclass."""

    def test_valid_selection_context(self) -> None:
        """SelectionContext with valid fields should create successfully."""
        ctx = SelectionContext(
            interval="step_up",
            ascending=True,
            harmonic_tension="low",
            character="plain",
            density="medium",
            is_minor=False,
            prev_leaped=False,
            leap_direction=None,
            bar_in_phrase=1,
            total_bars_in_phrase=8,
            schema_type="do_re_mi",
            phrase_deformation=None,
            seed=42,
        )
        assert ctx.interval == "step_up"
        assert ctx.ascending
        assert ctx.seed == 42

    def test_invalid_interval_rejected(self) -> None:
        """SelectionContext with invalid interval should be rejected."""
        with pytest.raises(AssertionError, match="Invalid interval"):
            SelectionContext(
                interval="octave_sideways",
                ascending=True,
                harmonic_tension="low",
                character="plain",
                density="medium",
                is_minor=False,
                prev_leaped=False,
                leap_direction=None,
                bar_in_phrase=1,
                total_bars_in_phrase=8,
                schema_type=None,
                phrase_deformation=None,
                seed=42,
            )

    def test_invalid_tension_rejected(self) -> None:
        """SelectionContext with invalid harmonic_tension should be rejected."""
        with pytest.raises(AssertionError, match="Invalid harmonic_tension"):
            SelectionContext(
                interval="step_up",
                ascending=True,
                harmonic_tension="extreme",
                character="plain",
                density="medium",
                is_minor=False,
                prev_leaped=False,
                leap_direction=None,
                bar_in_phrase=1,
                total_bars_in_phrase=8,
                schema_type=None,
                phrase_deformation=None,
                seed=42,
            )

    def test_invalid_phrase_deformation_rejected(self) -> None:
        """SelectionContext with invalid phrase_deformation should be rejected."""
        with pytest.raises(AssertionError, match="Invalid phrase_deformation"):
            SelectionContext(
                interval="step_up",
                ascending=True,
                harmonic_tension="low",
                character="plain",
                density="medium",
                is_minor=False,
                prev_leaped=False,
                leap_direction=None,
                bar_in_phrase=1,
                total_bars_in_phrase=8,
                schema_type=None,
                phrase_deformation="weird_ending",
                seed=42,
            )
