"""Tests for engine.backtrack.

Category A pure function tests: verify backtracking for constraint satisfaction.
Tests import only:
- engine.backtrack (module under test)
- stdlib
"""
import pytest
from engine.backtrack import (
    BacktrackState,
    Choice,
    choose_octave,
    octave_alternatives,
)


class TestChoice:
    """Test Choice dataclass."""

    def test_current_returns_first(self) -> None:
        """Current returns first alternative initially."""
        choice: Choice = Choice(location="test", alternatives=[60, 72, 48])
        assert choice.current == 60

    def test_exhausted_false_initially(self) -> None:
        """Not exhausted when alternatives remain."""
        choice: Choice = Choice(location="test", alternatives=[60, 72])
        assert not choice.exhausted

    def test_exhausted_true_single(self) -> None:
        """Exhausted with single alternative."""
        choice: Choice = Choice(location="test", alternatives=[60])
        assert choice.exhausted

    def test_next_advances(self) -> None:
        """Next advances to next alternative."""
        choice: Choice = Choice(location="test", alternatives=[60, 72, 48])
        result: int | None = choice.next()
        assert result == 72
        assert choice.current == 72

    def test_next_returns_none_when_exhausted(self) -> None:
        """Next returns None when exhausted."""
        choice: Choice = Choice(location="test", alternatives=[60])
        result: int | None = choice.next()
        assert result is None

    def test_next_exhausts_after_all(self) -> None:
        """Choice exhausted after all alternatives tried."""
        choice: Choice = Choice(location="test", alternatives=[60, 72])
        choice.next()
        assert choice.exhausted


class TestBacktrackState:
    """Test BacktrackState dataclass."""

    def test_initial_empty(self) -> None:
        """State starts with no choices."""
        state: BacktrackState = BacktrackState()
        assert state.choices == []
        assert state.backtrack_count == 0

    def test_add_choice_returns_first(self) -> None:
        """Add choice returns first alternative."""
        state: BacktrackState = BacktrackState()
        result: int = state.add_choice("loc1", [60, 72, 48])
        assert result == 60

    def test_add_choice_appends(self) -> None:
        """Add choice appends to choices list."""
        state: BacktrackState = BacktrackState()
        state.add_choice("loc1", [60, 72])
        state.add_choice("loc2", [48, 36])
        assert len(state.choices) == 2

    def test_backtrack_advances_last_choice(self) -> None:
        """Backtrack advances most recent choice."""
        state: BacktrackState = BacktrackState()
        state.add_choice("loc1", [60, 72])
        state.add_choice("loc2", [48, 36])
        result: bool = state.backtrack()
        assert result is True
        assert state.choices[-1].current == 36

    def test_backtrack_pops_exhausted(self) -> None:
        """Backtrack pops exhausted choices."""
        state: BacktrackState = BacktrackState()
        state.add_choice("loc1", [60, 72])
        state.add_choice("loc2", [48])  # Single alternative
        result: bool = state.backtrack()
        assert result is True
        assert len(state.choices) == 1
        assert state.choices[0].current == 72

    def test_backtrack_returns_false_all_exhausted(self) -> None:
        """Backtrack returns False when all exhausted."""
        state: BacktrackState = BacktrackState()
        state.add_choice("loc1", [60])
        result: bool = state.backtrack()
        assert result is False
        assert len(state.choices) == 0

    def test_backtrack_increments_count(self) -> None:
        """Backtrack increments backtrack_count."""
        state: BacktrackState = BacktrackState()
        state.add_choice("loc1", [60, 72])
        state.backtrack()
        assert state.backtrack_count == 1

    def test_backtrack_respects_max(self) -> None:
        """Backtrack stops at max_backtracks."""
        state: BacktrackState = BacktrackState(max_backtracks=2)
        state.add_choice("loc1", [60, 72, 48, 36])
        state.backtrack()
        state.backtrack()
        result: bool = state.backtrack()
        assert result is False

    def test_clear_resets_state(self) -> None:
        """Clear resets all state."""
        state: BacktrackState = BacktrackState()
        state.add_choice("loc1", [60, 72])
        state.backtrack()
        state.clear()
        assert state.choices == []
        assert state.backtrack_count == 0


class TestOctaveAlternatives:
    """Test octave_alternatives function."""

    def test_returns_base_pitch(self) -> None:
        """Base pitch is always included."""
        result: list[int] = octave_alternatives(60, 60)
        assert 60 in result

    def test_includes_octave_above(self) -> None:
        """Includes octave above when valid."""
        result: list[int] = octave_alternatives(60, 60)
        assert 72 in result

    def test_includes_octave_below(self) -> None:
        """Includes octave below when valid."""
        result: list[int] = octave_alternatives(60, 60)
        assert 48 in result

    def test_excludes_below_midi_range(self) -> None:
        """Excludes pitches below MIDI 21."""
        result: list[int] = octave_alternatives(30, 30)
        assert 18 not in result  # 30 - 12

    def test_excludes_above_midi_range(self) -> None:
        """Excludes pitches above MIDI 108."""
        result: list[int] = octave_alternatives(100, 100)
        assert 112 not in result  # 100 + 12

    def test_sorted_by_distance_from_median(self) -> None:
        """Results sorted by distance from median."""
        result: list[int] = octave_alternatives(60, 65)
        # 60 is closest to 65, then 72 (dist 7), then 48 (dist 17)
        assert result[0] == 60

    def test_median_60_prefers_base(self) -> None:
        """With median 60, base 60 comes first."""
        result: list[int] = octave_alternatives(60, 60)
        assert result[0] == 60

    def test_high_median_prefers_higher_octave(self) -> None:
        """Higher median prefers higher octave."""
        result: list[int] = octave_alternatives(60, 80)
        # 60+24=84 is closest to 80 (dist 4), then 72 (dist 8), then 60 (dist 20)
        assert result[0] == 84


class TestChooseOctave:
    """Test choose_octave function."""

    def test_returns_first_alternative(self) -> None:
        """Returns first alternative (closest to median)."""
        state: BacktrackState = BacktrackState()
        result: int = choose_octave(state, "test", 60, 60)
        assert result == 60

    def test_adds_choice_to_state(self) -> None:
        """Adds choice to state."""
        state: BacktrackState = BacktrackState()
        choose_octave(state, "loc1", 60, 60)
        assert len(state.choices) == 1
        assert state.choices[0].location == "loc1"

    def test_low_pitch_finds_higher_alternatives(self) -> None:
        """Low pitch finds valid higher octave alternatives."""
        state: BacktrackState = BacktrackState()
        # Pitch 10 has alternatives at 10+12=22 and 10+24=34
        result: int = choose_octave(state, "test", 10, 10)
        assert result == 22  # Closest valid to median 10

    def test_choice_added_for_low_pitch(self) -> None:
        """Choice added even for low pitch with higher alternatives."""
        state: BacktrackState = BacktrackState()
        choose_octave(state, "test", 10, 10)
        assert len(state.choices) == 1
        assert 22 in state.choices[0].alternatives

    def test_backtrack_changes_octave(self) -> None:
        """Backtracking changes chosen octave."""
        state: BacktrackState = BacktrackState()
        first: int = choose_octave(state, "test", 60, 60)
        state.backtrack()
        second: int = state.choices[0].current
        assert first != second

    def test_multiple_choices_independent(self) -> None:
        """Multiple choose_octave calls create independent choices."""
        state: BacktrackState = BacktrackState()
        choose_octave(state, "loc1", 60, 60)
        choose_octave(state, "loc2", 72, 72)
        assert len(state.choices) == 2
        assert state.choices[0].location == "loc1"
        assert state.choices[1].location == "loc2"


class TestBacktrackIntegration:
    """Integration tests for backtracking workflow."""

    def test_full_backtrack_workflow(self) -> None:
        """Test complete backtrack workflow."""
        state: BacktrackState = BacktrackState()
        # Make two choices
        p1: int = choose_octave(state, "phrase1", 60, 60)
        p2: int = choose_octave(state, "phrase2", 72, 72)
        # Both should return closest to median
        assert p1 == 60
        assert p2 == 72
        # Backtrack should try next alternative for phrase2
        assert state.backtrack()
        assert state.choices[-1].current != 72

    def test_clear_allows_fresh_start(self) -> None:
        """Clear allows completely fresh backtracking."""
        state: BacktrackState = BacktrackState()
        choose_octave(state, "loc1", 60, 60)
        state.backtrack()
        state.clear()
        # Should start fresh
        result: int = choose_octave(state, "loc2", 60, 60)
        assert result == 60
        assert len(state.choices) == 1

    def test_max_backtracks_limits_exploration(self) -> None:
        """Max backtracks limits total exploration."""
        state: BacktrackState = BacktrackState(max_backtracks=3)
        choose_octave(state, "loc1", 60, 60)  # Has 5 alternatives
        for _ in range(3):
            assert state.backtrack()
        # Fourth backtrack should fail
        assert not state.backtrack()
