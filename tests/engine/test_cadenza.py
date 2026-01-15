"""100% coverage tests for engine.cadenza.

Tests import only:
- engine.cadenza (module under test)
- shared (pitch, timed_material)
- stdlib

Cadenzas are quasi-improvisatory virtuosic passages with a dramatic arc:
ascent → intensification → climax → descent → resolution.

Deterministic: planner selects pattern, executor applies it.
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote
from shared.timed_material import TimedMaterial

from engine.cadenza import (
    _apply_multipliers,
    _arpeggio_segment,
    _load_patterns,
    _scalar_segment,
    generate_cadenza,
    generate_cadenza_bass,
)


class TestLoadPatterns:
    """Test _load_patterns function."""

    def test_returns_dict(self) -> None:
        """Returns dictionary of patterns."""
        patterns: dict = _load_patterns()
        assert isinstance(patterns, dict)

    def test_contains_flourish_a(self) -> None:
        """Contains default flourish_a pattern."""
        patterns: dict = _load_patterns()
        assert "flourish_a" in patterns

    def test_pattern_has_required_keys(self) -> None:
        """Each pattern has required phase keys."""
        patterns: dict = _load_patterns()
        required: set[str] = {"ascent", "broken", "climax", "descent", "resolution"}
        for name, pat in patterns.items():
            for key in required:
                assert key in pat, f"Pattern {name} missing {key}"

    def test_caching_works(self) -> None:
        """Patterns are cached (same object returned)."""
        p1: dict = _load_patterns()
        p2: dict = _load_patterns()
        assert p1 is p2


class TestScalarSegment:
    """Test _scalar_segment function."""

    def test_ascending_from_root(self) -> None:
        """Ascending scalar from root 1."""
        result: list[int] = _scalar_segment(1, 1, 4)
        assert result == [1, 2, 3, 4]

    def test_descending_from_peak(self) -> None:
        """Descending scalar from peak 8."""
        result: list[int] = _scalar_segment(8, -1, 4)
        assert result == [8, 7, 6, 5]

    def test_single_note(self) -> None:
        """Single note returns just start."""
        result: list[int] = _scalar_segment(5, 1, 1)
        assert result == [5]

    def test_zero_count(self) -> None:
        """Zero count returns empty list."""
        result: list[int] = _scalar_segment(1, 1, 0)
        assert result == []


class TestArpeggioSegment:
    """Test _arpeggio_segment function."""

    def test_ascending_arpeggio(self) -> None:
        """Ascending arpeggio from root."""
        result: list[int] = _arpeggio_segment(1, 1, 4)
        # Steps are [0, 2, 4, 7, ...], so degrees are [1, 3, 5, 8]
        assert result == [1, 3, 5, 8]

    def test_descending_arpeggio(self) -> None:
        """Descending arpeggio from peak."""
        result: list[int] = _arpeggio_segment(8, -1, 4)
        # Steps are [0, 2, 4, 7], so degrees are [8, 6, 4, 1]
        assert result == [8, 6, 4, 1]

    def test_wraps_steps_cyclically(self) -> None:
        """Steps wrap cyclically for long arpeggios."""
        result: list[int] = _arpeggio_segment(1, 1, 8)
        # Steps: [0, 2, 4, 7, 9, 11, 14, 0, ...]
        assert len(result) == 8
        assert result[7] == 1  # Wraps back to step 0


class TestApplyMultipliers:
    """Test _apply_multipliers function."""

    def test_basic_application(self) -> None:
        """Applies multipliers to base duration."""
        base: Fraction = Fraction(1, 16)
        mults: list[int] = [1, 2]
        result: list[Fraction] = _apply_multipliers(base, mults, 4)
        assert result == [Fraction(1, 16), Fraction(1, 8), Fraction(1, 16), Fraction(1, 8)]

    def test_cycles_multipliers(self) -> None:
        """Multipliers cycle when count exceeds length."""
        base: Fraction = Fraction(1, 16)
        mults: list[int] = [1, 2, 4]
        result: list[Fraction] = _apply_multipliers(base, mults, 5)
        assert result == [
            Fraction(1, 16), Fraction(1, 8), Fraction(1, 4),
            Fraction(1, 16), Fraction(1, 8),
        ]

    def test_single_multiplier(self) -> None:
        """Single multiplier repeated."""
        base: Fraction = Fraction(1, 8)
        result: list[Fraction] = _apply_multipliers(base, [2], 3)
        assert result == [Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)]


class TestGenerateCadenza:
    """Test generate_cadenza function."""

    def test_budget_must_be_at_least_2(self) -> None:
        """Budget < 2 raises AssertionError."""
        with pytest.raises(AssertionError, match="budget >= 2"):
            generate_cadenza(Fraction(1), root=1)

    def test_budget_exactly_filled(self) -> None:
        """Total duration equals budget exactly."""
        budget: Fraction = Fraction(4)
        result: TimedMaterial = generate_cadenza(budget, root=1)
        assert result.budget == budget
        assert sum(result.durations) == budget

    def test_returns_timed_material(self) -> None:
        """Returns TimedMaterial instance."""
        result: TimedMaterial = generate_cadenza(Fraction(2), root=1)
        assert isinstance(result, TimedMaterial)

    def test_all_pitches_are_floating_notes(self) -> None:
        """All pitches are FloatingNote instances."""
        result: TimedMaterial = generate_cadenza(Fraction(2), root=1)
        for pitch in result.pitches:
            assert isinstance(pitch, FloatingNote)

    def test_degrees_wrapped_to_1_7(self) -> None:
        """All degrees are in valid range 1-7."""
        result: TimedMaterial = generate_cadenza(Fraction(4), root=1)
        for pitch in result.pitches:
            assert 1 <= pitch.degree <= 7

    def test_deterministic_same_pattern(self) -> None:
        """Same pattern produces identical results."""
        result1: TimedMaterial = generate_cadenza(Fraction(2), root=1, pattern="flourish_a")
        result2: TimedMaterial = generate_cadenza(Fraction(2), root=1, pattern="flourish_a")
        assert result1.pitches == result2.pitches
        assert result1.durations == result2.durations

    def test_different_patterns_produce_different_results(self) -> None:
        """Different patterns produce different rhythmic patterns."""
        result1: TimedMaterial = generate_cadenza(Fraction(2), root=1, pattern="flourish_a")
        result2: TimedMaterial = generate_cadenza(Fraction(2), root=1, pattern="steady")
        # Different patterns have different duration multipliers
        assert result1.durations != result2.durations

    def test_default_pattern_is_flourish_a(self) -> None:
        """Default pattern is flourish_a."""
        result_default: TimedMaterial = generate_cadenza(Fraction(2), root=1)
        result_explicit: TimedMaterial = generate_cadenza(Fraction(2), root=1, pattern="flourish_a")
        assert result_default.pitches == result_explicit.pitches
        assert result_default.durations == result_explicit.durations

    def test_unknown_pattern_falls_back_to_flourish_a(self) -> None:
        """Unknown pattern name falls back to flourish_a."""
        result_unknown: TimedMaterial = generate_cadenza(Fraction(2), root=1, pattern="nonexistent")
        result_default: TimedMaterial = generate_cadenza(Fraction(2), root=1, pattern="flourish_a")
        assert result_unknown.pitches == result_default.pitches
        assert result_unknown.durations == result_default.durations

    def test_different_roots_transpose(self) -> None:
        """Different root transposes the entire cadenza."""
        result1: TimedMaterial = generate_cadenza(Fraction(2), root=1)
        result5: TimedMaterial = generate_cadenza(Fraction(2), root=5)
        assert result1.pitches[0].degree != result5.pitches[0].degree

    def test_resolution_ends_on_root(self) -> None:
        """Cadenza resolution ends on root degree."""
        result: TimedMaterial = generate_cadenza(Fraction(4), root=1)
        last_degree: int = result.pitches[-1].degree
        assert last_degree == 1

    def test_resolution_with_different_root(self) -> None:
        """Resolution ends on specified root."""
        result: TimedMaterial = generate_cadenza(Fraction(4), root=5)
        last_degree: int = result.pitches[-1].degree
        assert last_degree == 5

    def test_minimum_note_count(self) -> None:
        """Cadenza has minimum notes even with moderate budget."""
        result: TimedMaterial = generate_cadenza(Fraction(2), root=1)
        assert len(result.pitches) >= 10

    def test_budget_adjustment_when_short(self) -> None:
        """When generated content is short, last duration extended."""
        budget: Fraction = Fraction(8)
        result: TimedMaterial = generate_cadenza(budget, root=1)
        assert sum(result.durations) == budget

    def test_budget_adjustment_when_long(self) -> None:
        """When generated content is long, durations reduced."""
        budget: Fraction = Fraction(2)
        result: TimedMaterial = generate_cadenza(budget, root=1)
        assert sum(result.durations) == budget

    def test_flourish_b_pattern(self) -> None:
        """Flourish_b pattern works."""
        result: TimedMaterial = generate_cadenza(Fraction(3), root=1, pattern="flourish_b")
        assert sum(result.durations) == Fraction(3)

    def test_rubato_pattern(self) -> None:
        """Rubato pattern works."""
        result: TimedMaterial = generate_cadenza(Fraction(3), root=1, pattern="rubato")
        assert sum(result.durations) == Fraction(3)

    def test_steady_pattern(self) -> None:
        """Steady pattern produces uniform rhythms."""
        result: TimedMaterial = generate_cadenza(Fraction(4), root=1, pattern="steady")
        assert sum(result.durations) == Fraction(4)


class TestGenerateCadenzaBass:
    """Test generate_cadenza_bass function."""

    def test_budget_exactly_filled(self) -> None:
        """Total duration equals budget exactly."""
        budget: Fraction = Fraction(4)
        result: TimedMaterial = generate_cadenza_bass(budget, root=1)
        assert result.budget == budget
        assert sum(result.durations) == budget

    def test_returns_timed_material(self) -> None:
        """Returns TimedMaterial instance."""
        result: TimedMaterial = generate_cadenza_bass(Fraction(2), root=1)
        assert isinstance(result, TimedMaterial)

    def test_mostly_root_pedal(self) -> None:
        """Most of bass is root pedal (75%)."""
        result: TimedMaterial = generate_cadenza_bass(Fraction(4), root=1)
        root_notes: int = sum(1 for p in result.pitches if p.degree == 1)
        assert root_notes >= len(result.pitches) // 2

    def test_ends_on_root(self) -> None:
        """Bass ends on root degree."""
        result: TimedMaterial = generate_cadenza_bass(Fraction(2), root=1)
        assert result.pitches[-1].degree == 1

    def test_ends_on_specified_root(self) -> None:
        """Bass ends on specified root degree."""
        result: TimedMaterial = generate_cadenza_bass(Fraction(2), root=5)
        assert result.pitches[-1].degree == 5

    def test_penultimate_is_fourth_above_root(self) -> None:
        """Penultimate note is 4th degree above root (subdominant motion)."""
        result: TimedMaterial = generate_cadenza_bass(Fraction(2), root=1)
        penultimate_degree: int = result.pitches[-2].degree
        assert penultimate_degree == 4

    def test_fourth_above_root_5(self) -> None:
        """Fourth above root=5 is 1 (5+3=8, wrapped to 1)."""
        result: TimedMaterial = generate_cadenza_bass(Fraction(2), root=5)
        penultimate_degree: int = result.pitches[-2].degree
        assert penultimate_degree == 1

    def test_uses_half_note_pulse(self) -> None:
        """Main section uses half-note pulse."""
        result: TimedMaterial = generate_cadenza_bass(Fraction(4), root=1)
        main_durs = result.durations[:-2]
        for dur in main_durs:
            assert dur <= Fraction(1, 2)

    def test_tail_is_quarter_of_budget(self) -> None:
        """Tail section is 25% of budget."""
        budget: Fraction = Fraction(4)
        result: TimedMaterial = generate_cadenza_bass(budget, root=1)
        expected_tail_dur: Fraction = budget / 4
        actual_tail_dur: Fraction = result.durations[-1] + result.durations[-2]
        assert actual_tail_dur == expected_tail_dur

    def test_small_budget_still_works(self) -> None:
        """Small budget produces valid bass."""
        budget: Fraction = Fraction(1, 2)
        result: TimedMaterial = generate_cadenza_bass(budget, root=1)
        assert result.budget == budget
        assert sum(result.durations) == budget

    def test_all_pitches_are_floating_notes(self) -> None:
        """All pitches are FloatingNote instances."""
        result: TimedMaterial = generate_cadenza_bass(Fraction(2), root=1)
        for pitch in result.pitches:
            assert isinstance(pitch, FloatingNote)

    def test_deterministic(self) -> None:
        """Bass generation is deterministic."""
        result1: TimedMaterial = generate_cadenza_bass(Fraction(2), root=1)
        result2: TimedMaterial = generate_cadenza_bass(Fraction(2), root=1)
        assert result1.pitches == result2.pitches
        assert result1.durations == result2.durations


class TestCadenzaIntegration:
    """Integration tests for cadenza module."""

    def test_cadenza_soprano_and_bass_same_budget(self) -> None:
        """Soprano and bass cadenzas have matching budgets."""
        budget: Fraction = Fraction(4)
        soprano: TimedMaterial = generate_cadenza(budget, root=1)
        bass: TimedMaterial = generate_cadenza_bass(budget, root=1)
        assert soprano.budget == bass.budget
        assert sum(soprano.durations) == sum(bass.durations)

    def test_cadenza_dramatic_arc(self) -> None:
        """Cadenza has dramatic arc structure."""
        result: TimedMaterial = generate_cadenza(Fraction(4), root=1)
        degrees = [p.degree for p in result.pitches]
        unique_degrees: int = len(set(degrees))
        assert unique_degrees >= 4

    def test_cadenza_not_too_repetitive(self) -> None:
        """Cadenza avoids excessive repetition."""
        result: TimedMaterial = generate_cadenza(Fraction(4), root=1)
        degrees = [p.degree for p in result.pitches]
        max_consecutive: int = 1
        consecutive: int = 1
        for i in range(1, len(degrees)):
            if degrees[i] == degrees[i - 1]:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 1
        assert max_consecutive <= 4

    def test_bass_provides_harmonic_foundation(self) -> None:
        """Bass pedal provides stable harmonic foundation."""
        result: TimedMaterial = generate_cadenza_bass(Fraction(4), root=1)
        degrees = [p.degree for p in result.pitches]
        root_count: int = degrees.count(1)
        assert root_count > len(degrees) // 2
