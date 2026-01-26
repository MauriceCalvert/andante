"""Tests for builder.figuration.sequencer module."""
import pytest

from builder.figuration.sequencer import (
    SequencerState,
    accelerate_to_cadence,
    apply_fortspinnung,
    compute_transposition_interval,
    create_sequence_figures,
    detect_melodic_rhyme,
    fragment_figure,
    should_break_sequence,
    transpose_figure,
)
from builder.figuration.types import Figure
from shared.constants import MAX_SEQUENCE_REPETITIONS


def make_figure(
    name: str = "test",
    degrees: tuple[int, ...] = (0, 1, 2),
    repeatable: bool = True,
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
        repeatable=repeatable,
        requires_compensation=False,
        compensation_direction=None,
        is_compound=False,
        minor_safe=True,
        requires_leading_tone=False,
        weight=1.0,
    )


class TestTransposeFigure:
    """Tests for transpose_figure function."""

    def test_transpose_up_by_step(self) -> None:
        """Transposing up by 1 should add 1 to all degrees."""
        fig = make_figure(degrees=(0, 1, 2))
        result = transpose_figure(fig, 1)
        assert result.degrees == (1, 2, 3)

    def test_transpose_down_by_step(self) -> None:
        """Transposing down by 1 should subtract 1 from all degrees."""
        fig = make_figure(degrees=(2, 3, 4))
        result = transpose_figure(fig, -1)
        assert result.degrees == (1, 2, 3)

    def test_transpose_up_by_third(self) -> None:
        """Transposing up by 2 (third) should add 2 to all degrees."""
        fig = make_figure(degrees=(0, 1, 2))
        result = transpose_figure(fig, 2)
        assert result.degrees == (2, 3, 4)

    def test_preserves_shape(self) -> None:
        """Transposition should preserve relative intervals."""
        fig = make_figure(degrees=(0, 2, 1, 3))  # Various intervals
        result = transpose_figure(fig, 3)

        # Check relative intervals are preserved
        orig_intervals = [fig.degrees[i + 1] - fig.degrees[i] for i in range(len(fig.degrees) - 1)]
        new_intervals = [result.degrees[i + 1] - result.degrees[i] for i in range(len(result.degrees) - 1)]
        assert orig_intervals == new_intervals

    def test_name_reflects_transposition(self) -> None:
        """Transposed figure name should indicate transposition."""
        fig = make_figure(name="original")
        result = transpose_figure(fig, 2)
        assert "+2" in result.name

    def test_preserves_properties(self) -> None:
        """Transposition should preserve other figure properties."""
        fig = make_figure(name="test")
        result = transpose_figure(fig, 3)

        assert result.polarity == fig.polarity
        assert result.character == fig.character
        assert result.weight == fig.weight


class TestShouldBreakSequence:
    """Tests for should_break_sequence function."""

    def test_first_repetition_no_break(self) -> None:
        """First repetition should not break."""
        assert not should_break_sequence(0)
        assert not should_break_sequence(1)

    def test_third_repetition_breaks(self) -> None:
        """Third repetition (Rule of Three) should break."""
        assert should_break_sequence(MAX_SEQUENCE_REPETITIONS)

    def test_beyond_max_breaks(self) -> None:
        """Beyond max repetitions should also break."""
        assert should_break_sequence(MAX_SEQUENCE_REPETITIONS + 1)


class TestFragmentFigure:
    """Tests for fragment_figure function."""

    def test_fragment_shortens_figure(self) -> None:
        """Fragmentation should produce shorter figure."""
        fig = make_figure(degrees=(0, 1, 2, 3, 4, 5))
        result = fragment_figure(fig)
        assert len(result.degrees) < len(fig.degrees)

    def test_fragment_at_least_2_notes(self) -> None:
        """Fragment should have at least 2 notes."""
        fig = make_figure(degrees=(0, 1, 2))
        result = fragment_figure(fig)
        assert len(result.degrees) >= 2

    def test_fragment_preserves_start(self) -> None:
        """Fragment should preserve opening gesture."""
        fig = make_figure(degrees=(0, 2, 1, 3, 2, 4))
        result = fragment_figure(fig)
        # First note should match
        assert result.degrees[0] == fig.degrees[0]

    def test_fragment_name_indicates_fragment(self) -> None:
        """Fragment name should indicate fragmentation."""
        fig = make_figure(name="original")
        result = fragment_figure(fig)
        assert "frag" in result.name.lower()

    def test_fragment_not_cadential_safe(self) -> None:
        """Fragments should not be cadential safe."""
        fig = make_figure()
        result = fragment_figure(fig)
        assert not result.cadential_safe


class TestComputeTranspositionInterval:
    """Tests for compute_transposition_interval function."""

    def test_step_up(self) -> None:
        """1 to 2 should be interval of 1."""
        assert compute_transposition_interval(1, 2) == 1

    def test_step_down(self) -> None:
        """3 to 2 should be interval of -1."""
        assert compute_transposition_interval(3, 2) == -1

    def test_third_up(self) -> None:
        """1 to 3 should be interval of 2."""
        assert compute_transposition_interval(1, 3) == 2

    def test_same_degree(self) -> None:
        """Same degree should be interval of 0."""
        assert compute_transposition_interval(5, 5) == 0


class TestApplyFortspinnung:
    """Tests for apply_fortspinnung function."""

    def test_empty_targets_returns_empty(self) -> None:
        """Empty target list should return empty."""
        fig = make_figure()
        state = SequencerState()
        result = apply_fortspinnung(fig, [], state)
        assert result == []

    def test_single_target_returns_original(self) -> None:
        """Single target should return original figure."""
        fig = make_figure()
        state = SequencerState()
        result = apply_fortspinnung(fig, [1], state)
        assert len(result) == 1
        assert result[0] == fig

    def test_multiple_targets_transposes(self) -> None:
        """Multiple targets should produce transposed figures."""
        fig = make_figure(degrees=(0, 1, 2))
        state = SequencerState()
        result = apply_fortspinnung(fig, [1, 2, 3], state)

        assert len(result) == 3
        # First is original
        assert result[0].degrees == (0, 1, 2)
        # Second transposed up by 1
        assert result[1].degrees == (1, 2, 3)
        # Third transposed up by 1 more
        assert result[2].degrees == (2, 3, 4)

    def test_rule_of_three_fragments(self) -> None:
        """After max repetitions, should fragment."""
        fig = make_figure(degrees=(0, 1, 2, 3, 4, 5))
        state = SequencerState()

        # 4 targets = 3 repetitions, should trigger Rule of Three
        targets = [1, 2, 3, 4]
        result = apply_fortspinnung(fig, targets, state)

        # Last figure should be shorter (fragmented)
        assert len(result[-1].degrees) < len(fig.degrees)


class TestDetectMelodicRhyme:
    """Tests for detect_melodic_rhyme function."""

    def test_exact_transposition_detected(self) -> None:
        """Exact transposition by 4 should be detected."""
        bar_1 = make_figure(degrees=(0, 1, 2))
        bar_5 = make_figure(degrees=(4, 5, 6))  # Up 4

        assert detect_melodic_rhyme(bar_5, bar_1, transposition=4)

    def test_different_shape_not_rhyme(self) -> None:
        """Different shapes should not be rhyme."""
        bar_1 = make_figure(degrees=(0, 1, 2))
        bar_5 = make_figure(degrees=(4, 6, 5))  # Different shape

        assert not detect_melodic_rhyme(bar_5, bar_1)

    def test_different_length_not_rhyme(self) -> None:
        """Different lengths should not be rhyme."""
        bar_1 = make_figure(degrees=(0, 1, 2))
        bar_5 = make_figure(degrees=(4, 5))  # Shorter

        assert not detect_melodic_rhyme(bar_5, bar_1)


class TestCreateSequenceFigures:
    """Tests for create_sequence_figures function."""

    def test_ascending_sequence(self) -> None:
        """Ascending sequence should step up."""
        fig = make_figure(degrees=(0, 1))
        result = create_sequence_figures(fig, 3, "ascending", step_size=1)

        assert len(result) == 3
        assert result[0].degrees[0] == 0
        assert result[1].degrees[0] == 1
        assert result[2].degrees[0] == 2

    def test_descending_sequence(self) -> None:
        """Descending sequence should step down."""
        fig = make_figure(degrees=(4, 5))
        result = create_sequence_figures(fig, 3, "descending", step_size=1)

        assert len(result) == 3
        assert result[0].degrees[0] == 4
        assert result[1].degrees[0] == 3
        assert result[2].degrees[0] == 2

    def test_step_size_respected(self) -> None:
        """Step size should be respected."""
        fig = make_figure(degrees=(0, 1))
        result = create_sequence_figures(fig, 3, "ascending", step_size=2)

        assert result[0].degrees[0] == 0
        assert result[1].degrees[0] == 2
        assert result[2].degrees[0] == 4


class TestAccelerateToCadence:
    """Tests for accelerate_to_cadence function."""

    def test_zero_bars_returns_empty(self) -> None:
        """Zero remaining bars should return empty."""
        fig = make_figure(degrees=(0, 1, 2, 3, 4))
        result = accelerate_to_cadence(fig, 0)
        assert result == []

    def test_returns_correct_count(self) -> None:
        """Should return one figure per remaining bar."""
        fig = make_figure(degrees=(0, 1, 2, 3, 4))
        result = accelerate_to_cadence(fig, 3)
        assert len(result) == 3

    def test_progressive_fragmentation(self) -> None:
        """Later figures should be shorter (more fragmented)."""
        fig = make_figure(degrees=(0, 1, 2, 3, 4, 5, 6))
        result = accelerate_to_cadence(fig, 4)

        # Each subsequent figure should be same length or shorter
        for i in range(1, len(result)):
            assert len(result[i].degrees) <= len(result[i - 1].degrees)


class TestSequencerState:
    """Tests for SequencerState dataclass."""

    def test_initial_state(self) -> None:
        """Initial state should have zero counts."""
        state = SequencerState()
        assert state.current_figure is None
        assert state.repetition_count == 0
        assert state.transposition_interval == 0

    def test_reset(self) -> None:
        """Reset should clear state."""
        state = SequencerState()
        state.current_figure = make_figure()
        state.repetition_count = 5
        state.transposition_interval = 3

        state.reset()

        assert state.current_figure is None
        assert state.repetition_count == 0
        assert state.transposition_interval == 0
