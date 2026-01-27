"""Tests for builder.figuration.selector module."""
import pytest

from builder.figuration.loader import clear_cache, get_diminutions
from builder.figuration.selector import (
    apply_misbehaviour,
    compute_interval,
    determine_phrase_position,
    filter_by_character,
    filter_by_compensation,
    filter_by_density,
    filter_by_direction,
    filter_by_minor_safety,
    filter_by_tension,
    filter_cadential_safe,
    get_figures_for_interval,
    select_figure,
    select_figure_for_bar,
    sort_by_weight,
)
from shared.constants import MISBEHAVIOUR_PROBABILITY
from builder.figuration.types import Figure, SelectionContext
from builder.types import Anchor
from shared.key import Key


def make_figure(
    name: str = "test",
    degrees: tuple[int, ...] = (0, 1),
    polarity: str = "balanced",
    character: str = "plain",
    harmonic_tension: str = "low",
    max_density: str = "medium",
    cadential_safe: bool = True,
    minor_safe: bool = True,
    requires_compensation: bool = False,
    compensation_direction: str | None = None,
    weight: float = 1.0,
) -> Figure:
    """Helper to create test figures."""
    return Figure(
        name=name,
        degrees=degrees,
        contour="test",
        polarity=polarity,
        arrival="direct",
        placement="span",
        character=character,
        harmonic_tension=harmonic_tension,
        max_density=max_density,
        cadential_safe=cadential_safe,
        repeatable=True,
        requires_compensation=requires_compensation,
        compensation_direction=compensation_direction,
        is_compound=False,
        minor_safe=minor_safe,
        requires_leading_tone=False,
        weight=weight,
    )


class TestComputeInterval:
    """Tests for compute_interval function."""

    def test_unison(self) -> None:
        """Same degree should return unison."""
        assert compute_interval(1, 1) == "unison"
        assert compute_interval(5, 5) == "unison"

    def test_step_up(self) -> None:
        """Degree +1 should return step_up."""
        assert compute_interval(1, 2) == "step_up"
        assert compute_interval(3, 4) == "step_up"

    def test_step_down(self) -> None:
        """Degree -1 should return step_down."""
        assert compute_interval(2, 1) == "step_down"
        assert compute_interval(5, 4) == "step_down"

    def test_third_up(self) -> None:
        """Degree +2 should return third_up."""
        assert compute_interval(1, 3) == "third_up"
        assert compute_interval(3, 5) == "third_up"

    def test_third_down(self) -> None:
        """Degree -2 should return third_down."""
        assert compute_interval(3, 1) == "third_down"
        assert compute_interval(5, 3) == "third_down"

    def test_fourth_up(self) -> None:
        """Degree +3 should return fourth_up."""
        assert compute_interval(1, 4) == "fourth_up"

    def test_fourth_down(self) -> None:
        """Degree -3 should return fourth_down."""
        assert compute_interval(4, 1) == "fourth_down"

    def test_fifth_up(self) -> None:
        """Degree +4 should return fifth_up."""
        assert compute_interval(1, 5) == "fifth_up"

    def test_fifth_down(self) -> None:
        """Degree -4 should return fifth_down."""
        assert compute_interval(5, 1) == "fifth_down"

    def test_sixth_up(self) -> None:
        """Degree +5 should return sixth_up."""
        assert compute_interval(1, 6) == "sixth_up"

    def test_sixth_down(self) -> None:
        """Degree -5 should return sixth_down."""
        assert compute_interval(6, 1) == "sixth_down"

    def test_octave_up(self) -> None:
        """Large upward interval should return octave_up."""
        assert compute_interval(1, 7) == "octave_up"

    def test_octave_down(self) -> None:
        """Large downward interval should return octave_down."""
        assert compute_interval(7, 1) == "octave_down"


class TestFilterByDirection:
    """Tests for filter_by_direction function."""

    def test_ascending_keeps_upper_and_balanced(self) -> None:
        """Ascending context should keep upper and balanced polarity."""
        figs = [
            make_figure("upper", polarity="upper"),
            make_figure("lower", polarity="lower"),
            make_figure("balanced", polarity="balanced"),
        ]
        result = filter_by_direction(figs, ascending=True)
        names = [f.name for f in result]
        assert "upper" in names
        assert "balanced" in names
        assert "lower" not in names

    def test_descending_keeps_lower_and_balanced(self) -> None:
        """Descending context should keep lower and balanced polarity."""
        figs = [
            make_figure("upper", polarity="upper"),
            make_figure("lower", polarity="lower"),
            make_figure("balanced", polarity="balanced"),
        ]
        result = filter_by_direction(figs, ascending=False)
        names = [f.name for f in result]
        assert "lower" in names
        assert "balanced" in names
        assert "upper" not in names

    def test_empty_returns_empty(self) -> None:
        """Empty input should return empty."""
        assert filter_by_direction([], True) == []

    def test_all_filtered_returns_original(self) -> None:
        """If all filtered, return original (soft filter)."""
        figs = [make_figure("only_lower", polarity="lower")]
        result = filter_by_direction(figs, ascending=True)
        # Should return original since all would be filtered
        assert len(result) == 1


class TestFilterByTension:
    """Tests for filter_by_tension function."""

    def test_low_tension_accepts_low_and_medium(self) -> None:
        """Low tension should accept low and medium."""
        figs = [
            make_figure("low", harmonic_tension="low"),
            make_figure("medium", harmonic_tension="medium"),
            make_figure("high", harmonic_tension="high"),
        ]
        result = filter_by_tension(figs, "low")
        names = [f.name for f in result]
        assert "low" in names
        assert "medium" in names
        assert "high" not in names

    def test_medium_tension_accepts_all(self) -> None:
        """Medium tension should accept all levels."""
        figs = [
            make_figure("low", harmonic_tension="low"),
            make_figure("medium", harmonic_tension="medium"),
            make_figure("high", harmonic_tension="high"),
        ]
        result = filter_by_tension(figs, "medium")
        assert len(result) == 3

    def test_high_tension_accepts_medium_and_high(self) -> None:
        """High tension should accept medium and high."""
        figs = [
            make_figure("low", harmonic_tension="low"),
            make_figure("medium", harmonic_tension="medium"),
            make_figure("high", harmonic_tension="high"),
        ]
        result = filter_by_tension(figs, "high")
        names = [f.name for f in result]
        assert "high" in names
        assert "medium" in names
        assert "low" not in names


class TestFilterByCharacter:
    """Tests for filter_by_character function."""

    def test_plain_accepts_plain_and_expressive(self) -> None:
        """Plain character should accept plain and expressive."""
        figs = [
            make_figure("plain", character="plain"),
            make_figure("expressive", character="expressive"),
            make_figure("energetic", character="energetic"),
        ]
        result = filter_by_character(figs, "plain")
        names = [f.name for f in result]
        assert "plain" in names
        assert "expressive" in names
        assert "energetic" not in names

    def test_energetic_accepts_bold_and_energetic(self) -> None:
        """Energetic character should accept energetic and bold."""
        figs = [
            make_figure("plain", character="plain"),
            make_figure("energetic", character="energetic"),
            make_figure("bold", character="bold"),
        ]
        result = filter_by_character(figs, "energetic")
        names = [f.name for f in result]
        assert "energetic" in names
        assert "bold" in names


class TestFilterByDensity:
    """Tests for filter_by_density function."""

    def test_high_density_accepts_all_densities(self) -> None:
        """High density allows all figures."""
        figs = [
            make_figure("low", max_density="low"),
            make_figure("medium", max_density="medium"),
            make_figure("high", max_density="high"),
        ]
        result = filter_by_density(figs, "high")
        assert len(result) == 3

    def test_low_density_only_accepts_low(self) -> None:
        """Low density only accepts figures with low max_density."""
        figs = [
            make_figure("low", max_density="low"),
            make_figure("medium", max_density="medium"),
            make_figure("high", max_density="high"),
        ]
        result = filter_by_density(figs, "low")
        # Only figures that can work at low density
        # Note: target >= max_density, so low density only matches low
        assert len(result) == 1
        assert result[0].name == "low"


class TestFilterByMinorSafety:
    """Tests for filter_by_minor_safety function."""

    def test_minor_key_filters_unsafe(self) -> None:
        """Minor key should filter unsafe figures."""
        figs = [
            make_figure("safe", minor_safe=True),
            make_figure("unsafe", minor_safe=False),
        ]
        result = filter_by_minor_safety(figs, is_minor=True)
        names = [f.name for f in result]
        assert "safe" in names
        assert "unsafe" not in names

    def test_major_key_keeps_all(self) -> None:
        """Major key should keep all figures."""
        figs = [
            make_figure("safe", minor_safe=True),
            make_figure("unsafe", minor_safe=False),
        ]
        result = filter_by_minor_safety(figs, is_minor=False)
        assert len(result) == 2


class TestFilterByCompensation:
    """Tests for filter_by_compensation function."""

    def test_no_prev_leap_keeps_all(self) -> None:
        """No previous leap keeps all figures."""
        figs = [
            make_figure("needs_comp", requires_compensation=True),
            make_figure("no_comp", requires_compensation=False),
        ]
        result = filter_by_compensation(figs, prev_leaped=False, leap_direction=None)
        assert len(result) == 2

    def test_prev_leap_up_prefers_down_compensation(self) -> None:
        """Previous upward leap should prefer downward compensation."""
        figs = [
            make_figure("comp_down", requires_compensation=True, compensation_direction="down"),
            make_figure("comp_up", requires_compensation=True, compensation_direction="up"),
            make_figure("no_comp", requires_compensation=False),
        ]
        result = filter_by_compensation(figs, prev_leaped=True, leap_direction="up")
        names = [f.name for f in result]
        assert "no_comp" in names
        assert "comp_down" in names


class TestFilterCadentialSafe:
    """Tests for filter_cadential_safe function."""

    def test_near_cadence_filters_unsafe(self) -> None:
        """Near cadence should filter unsafe figures."""
        figs = [
            make_figure("safe", cadential_safe=True),
            make_figure("unsafe", cadential_safe=False),
        ]
        result = filter_cadential_safe(figs, near_cadence=True)
        names = [f.name for f in result]
        assert "safe" in names
        assert "unsafe" not in names

    def test_not_near_cadence_keeps_all(self) -> None:
        """Not near cadence should keep all."""
        figs = [
            make_figure("safe", cadential_safe=True),
            make_figure("unsafe", cadential_safe=False),
        ]
        result = filter_cadential_safe(figs, near_cadence=False)
        assert len(result) == 2


class TestSortByWeight:
    """Tests for sort_by_weight function."""

    def test_sorts_by_weight_descending(self) -> None:
        """Should sort by weight descending."""
        figs = [
            make_figure("low", weight=0.5),
            make_figure("high", weight=1.0),
            make_figure("medium", weight=0.7),
        ]
        result = sort_by_weight(figs)
        assert result[0].name == "high"
        assert result[1].name == "medium"
        assert result[2].name == "low"

    def test_equal_weights_sort_by_name(self) -> None:
        """Equal weights should sort alphabetically by name."""
        figs = [
            make_figure("zebra", weight=1.0),
            make_figure("alpha", weight=1.0),
            make_figure("beta", weight=1.0),
        ]
        result = sort_by_weight(figs)
        assert result[0].name == "alpha"
        assert result[1].name == "beta"
        assert result[2].name == "zebra"


class TestSelectFigure:
    """Tests for select_figure function."""

    def test_empty_returns_none(self) -> None:
        """Empty list should return None."""
        assert select_figure([], seed=42) is None

    def test_single_figure_returns_it(self) -> None:
        """Single figure should be returned."""
        fig = make_figure("only")
        result = select_figure([fig], seed=42)
        assert result is fig

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed should produce same result."""
        figs = [
            make_figure("a", weight=1.0),
            make_figure("b", weight=1.0),
            make_figure("c", weight=1.0),
        ]
        result1 = select_figure(figs, seed=42)
        result2 = select_figure(figs, seed=42)
        assert result1 == result2

    def test_different_seeds_may_differ(self) -> None:
        """Different seeds may produce different results."""
        figs = [
            make_figure("a", weight=1.0),
            make_figure("b", weight=1.0),
            make_figure("c", weight=1.0),
        ]
        results = set()
        for seed in range(100):
            result = select_figure(figs, seed=seed)
            if result:
                results.add(result.name)
        # Should eventually select different figures
        assert len(results) > 1


class TestDeterminePhrasePosition:
    """Tests for determine_phrase_position function."""

    def test_opening_position(self) -> None:
        """Early bars should be opening position."""
        pos = determine_phrase_position(bar=1, total_bars=8)
        assert pos.position == "opening"

    def test_continuation_position(self) -> None:
        """Middle bars should be continuation position."""
        pos = determine_phrase_position(bar=4, total_bars=8)
        assert pos.position == "continuation"

    def test_cadence_position(self) -> None:
        """Final bars should be cadence position."""
        pos = determine_phrase_position(bar=7, total_bars=8)
        assert pos.position == "cadence"

    def test_sequential_schema_enables_sequential(self) -> None:
        """Sequential schemas should enable sequential flag."""
        pos = determine_phrase_position(bar=4, total_bars=8, schema_type="monte")
        assert pos.sequential

    def test_non_sequential_schema_disables_sequential(self) -> None:
        """Non-sequential schemas should disable sequential flag."""
        pos = determine_phrase_position(bar=4, total_bars=8, schema_type="do_re_mi")
        assert not pos.sequential


class TestSelectFigureForBar:
    """Tests for select_figure_for_bar function."""

    def test_returns_figure_for_valid_context(self) -> None:
        """Should return a figure for valid selection context."""
        clear_cache()

        context = SelectionContext(
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
            phrase_deformation=None,
            seed=42,
        )

        key = Key(tonic="C", mode="major")
        anchor_a = Anchor(
            bar_beat="1.1",
            soprano_degree=1,
            bass_degree=1,
            local_key=key,
            schema="test",
            stage=1,
        )
        anchor_b = Anchor(
            bar_beat="2.1",
            soprano_degree=2,
            bass_degree=5,
            local_key=key,
            schema="test",
            stage=2,
        )

        result = select_figure_for_bar(anchor_a, anchor_b, context)
        assert result is not None
        assert isinstance(result, Figure)

    def test_deterministic_selection(self) -> None:
        """Same context and seed should produce same result."""
        clear_cache()

        context = SelectionContext(
            interval="third_up",
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
            seed=123,
        )

        key = Key(tonic="C", mode="major")
        anchor_a = Anchor(
            bar_beat="1.1",
            soprano_degree=1,
            bass_degree=1,
            local_key=key,
            schema="test",
            stage=1,
        )
        anchor_b = Anchor(
            bar_beat="2.1",
            soprano_degree=3,
            bass_degree=1,
            local_key=key,
            schema="test",
            stage=2,
        )

        result1 = select_figure_for_bar(anchor_a, anchor_b, context)
        result2 = select_figure_for_bar(anchor_a, anchor_b, context)
        assert result1 == result2


class TestGetFiguresForInterval:
    """Tests for get_figures_for_interval function."""

    def test_returns_figures_for_valid_interval(self) -> None:
        """Should return figures for valid interval."""
        clear_cache()
        figures = get_figures_for_interval("step_up")
        assert len(figures) > 0
        for fig in figures:
            assert isinstance(fig, Figure)

    def test_invalid_interval_raises(self) -> None:
        """Invalid interval should raise AssertionError."""
        with pytest.raises(AssertionError, match="Invalid interval"):
            get_figures_for_interval("invalid_interval")


class TestApplyMisbehaviour:
    """Tests for apply_misbehaviour function."""

    def test_returns_filtered_normally(self) -> None:
        """With low misbehaviour probability, should return filtered list."""
        filtered = [make_figure("a")]
        all_figs = [make_figure("a"), make_figure("b"), make_figure("c")]
        # Use seed that doesn't trigger misbehaviour (probability 5%)
        result = apply_misbehaviour(filtered, all_figs, seed=42, probability=0.0)
        assert len(result) == 1
        assert result[0].name == "a"

    def test_returns_all_on_misbehaviour(self) -> None:
        """With 100% probability, should return all figures."""
        filtered = [make_figure("a")]
        all_figs = [make_figure("a"), make_figure("b"), make_figure("c")]
        result = apply_misbehaviour(filtered, all_figs, seed=42, probability=1.0)
        assert len(result) == 3

    def test_empty_filtered_returns_empty(self) -> None:
        """Empty filtered list should return empty."""
        all_figs = [make_figure("a"), make_figure("b")]
        result = apply_misbehaviour([], all_figs, seed=42, probability=1.0)
        assert result == []

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed should produce same result."""
        filtered = [make_figure("a")]
        all_figs = [make_figure("a"), make_figure("b"), make_figure("c")]
        result1 = apply_misbehaviour(filtered, all_figs, seed=123)
        result2 = apply_misbehaviour(filtered, all_figs, seed=123)
        assert len(result1) == len(result2)
