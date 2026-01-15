"""100% coverage tests for engine.hemiola.

Tests import only:
- engine.hemiola (module under test)
- shared (pitch, timed_material)
- stdlib

Hemiola is a baroque rhythmic technique where two bars of triple metre
(e.g., 3/4) are regrouped as three groups of two beats, creating
metric tension before cadences or at climax points.
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote
from shared.timed_material import TimedMaterial

from engine.hemiola import (
    HemiolaPattern,
    HEMIOLA_PATTERNS,
    can_apply_hemiola,
    apply_hemiola,
    detect_hemiola_trigger,
)


class TestHemiolaPatternDataclass:
    """Test HemiolaPattern dataclass."""

    def test_construction(self) -> None:
        """HemiolaPattern can be constructed."""
        pattern: HemiolaPattern = HemiolaPattern(
            name="test",
            input_metre="3/4",
            regrouping="3_to_2",
            duration_bars=2,
            trigger="manual",
        )
        assert pattern.name == "test"
        assert pattern.input_metre == "3/4"
        assert pattern.regrouping == "3_to_2"
        assert pattern.duration_bars == 2
        assert pattern.trigger == "manual"

    def test_frozen(self) -> None:
        """HemiolaPattern is immutable."""
        pattern: HemiolaPattern = HemiolaPattern(
            name="test", input_metre="3/4", regrouping="3_to_2",
            duration_bars=2, trigger="manual"
        )
        with pytest.raises(Exception):
            pattern.name = "modified"


class TestHemiolaPatternsConstant:
    """Test HEMIOLA_PATTERNS constant."""

    def test_cadential_pattern_exists(self) -> None:
        """Cadential hemiola pattern is defined."""
        assert "cadential" in HEMIOLA_PATTERNS

    def test_climax_pattern_exists(self) -> None:
        """Climax hemiola pattern is defined."""
        assert "climax" in HEMIOLA_PATTERNS

    def test_cadential_is_3_to_2(self) -> None:
        """Cadential pattern uses standard 3-to-2 regrouping."""
        pattern: HemiolaPattern = HEMIOLA_PATTERNS["cadential"]
        assert pattern.regrouping == "3_to_2"

    def test_cadential_spans_two_bars(self) -> None:
        """Cadential pattern spans 2 bars."""
        pattern: HemiolaPattern = HEMIOLA_PATTERNS["cadential"]
        assert pattern.duration_bars == 2

    def test_climax_trigger(self) -> None:
        """Climax pattern triggered at climax."""
        pattern: HemiolaPattern = HEMIOLA_PATTERNS["climax"]
        assert pattern.trigger == "climax"

    def test_cadential_trigger(self) -> None:
        """Cadential pattern triggered pre-cadence."""
        pattern: HemiolaPattern = HEMIOLA_PATTERNS["cadential"]
        assert pattern.trigger == "pre_cadence"


class TestCanApplyHemiola:
    """Test can_apply_hemiola function."""

    def test_3_4_is_triple(self) -> None:
        """3/4 metre supports hemiola."""
        assert can_apply_hemiola("3/4") is True

    def test_6_8_is_triple(self) -> None:
        """6/8 metre supports hemiola (6 % 3 == 0)."""
        assert can_apply_hemiola("6/8") is True

    def test_9_8_is_triple(self) -> None:
        """9/8 metre supports hemiola."""
        assert can_apply_hemiola("9/8") is True

    def test_12_8_is_triple(self) -> None:
        """12/8 metre supports hemiola."""
        assert can_apply_hemiola("12/8") is True

    def test_4_4_not_triple(self) -> None:
        """4/4 metre does not support hemiola."""
        assert can_apply_hemiola("4/4") is False

    def test_2_4_not_triple(self) -> None:
        """2/4 metre does not support hemiola."""
        assert can_apply_hemiola("2/4") is False

    def test_5_4_not_triple(self) -> None:
        """5/4 metre does not support hemiola."""
        assert can_apply_hemiola("5/4") is False

    def test_invalid_format_raises(self) -> None:
        """Invalid metre format raises AssertionError."""
        with pytest.raises(AssertionError, match="Invalid metre format"):
            can_apply_hemiola("3-4")


class TestApplyHemiola:
    """Test apply_hemiola function."""

    def test_3_to_2_regrouping_note_count(self) -> None:
        """3-to-2 regrouping in 3/4: 6 quarter notes become 3 half notes."""
        # 2 bars of 3/4 = 6 quarter notes
        pitches = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6])
        durations = tuple(Fraction(1, 4) for _ in range(6))
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(3, 2))
        result: TimedMaterial = apply_hemiola(material, "cadential", "3/4")
        # Should now have 3 notes with half-note durations
        assert len(result.pitches) == 3

    def test_budget_preserved(self) -> None:
        """Total duration unchanged after hemiola."""
        pitches = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6])
        durations = tuple(Fraction(1, 4) for _ in range(6))
        budget: Fraction = Fraction(3, 2)
        material: TimedMaterial = TimedMaterial(pitches, durations, budget)
        result: TimedMaterial = apply_hemiola(material, "cadential", "3/4")
        assert result.budget == budget
        assert sum(result.durations) == budget

    def test_structural_pitches_selected(self) -> None:
        """First and last pitches preserved in regrouping."""
        pitches = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6])
        durations = tuple(Fraction(1, 4) for _ in range(6))
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(3, 2))
        result: TimedMaterial = apply_hemiola(material, "cadential", "3/4")
        # First pitch should be preserved
        assert result.pitches[0].degree == 1
        # Last pitch should be preserved
        assert result.pitches[-1].degree == 6

    def test_unknown_pattern_raises(self) -> None:
        """Unknown pattern name raises AssertionError."""
        material: TimedMaterial = TimedMaterial(
            (FloatingNote(1),), (Fraction(1),), Fraction(1)
        )
        with pytest.raises(AssertionError, match="Unknown hemiola pattern"):
            apply_hemiola(material, "unknown", "3/4")

    def test_non_triple_metre_raises(self) -> None:
        """Non-triple metre raises AssertionError."""
        material: TimedMaterial = TimedMaterial(
            (FloatingNote(1),), (Fraction(1),), Fraction(1)
        )
        with pytest.raises(AssertionError, match="Hemiola requires triple metre"):
            apply_hemiola(material, "cadential", "4/4")

    def test_short_material_returned_unchanged(self) -> None:
        """Material shorter than one group returned unchanged."""
        # Very short material - less than one half-note group
        material: TimedMaterial = TimedMaterial(
            (FloatingNote(1),), (Fraction(1, 4),), Fraction(1, 4)
        )
        result: TimedMaterial = apply_hemiola(material, "cadential", "3/4")
        # Should return unchanged since can't fit even one group
        assert result.pitches == material.pitches
        assert result.durations == material.durations

    def test_6_8_metre_regrouping(self) -> None:
        """Hemiola in 6/8 uses eighth-note beat value."""
        # 6/8: beat_value = 1/8, new_group_dur = 2/8 = 1/4
        pitches = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6])
        durations = tuple(Fraction(1, 8) for _ in range(6))
        budget: Fraction = Fraction(6, 8)  # 3/4 = 6/8
        material: TimedMaterial = TimedMaterial(pitches, durations, budget)
        result: TimedMaterial = apply_hemiola(material, "cadential", "6/8")
        # Should regroup into 3 groups of 1/4 each
        assert result.budget == budget

    def test_climax_pattern_applies(self) -> None:
        """Climax pattern applies correctly."""
        pitches = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6])
        durations = tuple(Fraction(1, 4) for _ in range(6))
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(3, 2))
        result: TimedMaterial = apply_hemiola(material, "climax", "3/4")
        assert len(result.pitches) == 3

    def test_2_to_3_regrouping_uses_different_duration(self) -> None:
        """Non-3_to_2 regrouping uses 3/2 beat_value multiplier.

        Note: Currently no patterns use 2_to_3, but the code path exists.
        We test this by temporarily modifying HEMIOLA_PATTERNS.
        """
        # Create a custom pattern with 2_to_3 regrouping via module access
        from engine import hemiola
        original_patterns = dict(hemiola.HEMIOLA_PATTERNS)
        try:
            # Add test pattern with 2_to_3 regrouping
            hemiola.HEMIOLA_PATTERNS["test_2_to_3"] = HemiolaPattern(
                name="test_2_to_3",
                input_metre="3/4",
                regrouping="2_to_3",
                duration_bars=2,
                trigger="manual",
            )
            pitches = tuple(FloatingNote(i) for i in [1, 2, 3, 4])
            durations = tuple(Fraction(3, 8) for _ in range(4))  # 4 * 3/8 = 3/2
            material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(3, 2))
            result: TimedMaterial = apply_hemiola(material, "test_2_to_3", "3/4")
            # With 2_to_3: beat_value=1/4, new_group_dur=1/4 * 3/2 = 3/8
            # budget 3/2 / 3/8 = 4 groups
            assert result.budget == Fraction(3, 2)
        finally:
            hemiola.HEMIOLA_PATTERNS.clear()
            hemiola.HEMIOLA_PATTERNS.update(original_patterns)

    def test_remaining_duration_added_to_last(self) -> None:
        """Remaining duration added to last group."""
        # 7 eighth notes in 6/8 = 7/8 budget
        # Groups of 1/4 each: 3 groups = 3/4, remaining 1/8
        pitches = tuple(FloatingNote(i) for i in range(1, 8))
        durations = tuple(Fraction(1, 8) for _ in range(7))
        budget: Fraction = Fraction(7, 8)
        material: TimedMaterial = TimedMaterial(pitches, durations, budget)
        result: TimedMaterial = apply_hemiola(material, "cadential", "6/8")
        # Last duration should include the remainder
        assert sum(result.durations) == budget


class TestSelectStructuralPitches:
    """Test pitch selection for hemiola regrouping (via apply_hemiola)."""

    def test_fewer_pitches_than_groups_pads(self) -> None:
        """When fewer pitches than groups, last pitch repeated."""
        # 2 pitches, need 3 groups
        pitches = (FloatingNote(1), FloatingNote(5))
        durations = (Fraction(3, 4), Fraction(3, 4))
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(3, 2))
        result: TimedMaterial = apply_hemiola(material, "cadential", "3/4")
        # Should pad with last pitch
        assert len(result.pitches) == 3
        assert result.pitches[2].degree == 5  # Last pitch repeated

    def test_single_pitch_creates_single_group(self) -> None:
        """Single pitch with single group works."""
        material: TimedMaterial = TimedMaterial(
            (FloatingNote(3),), (Fraction(1, 2),), Fraction(1, 2)
        )
        result: TimedMaterial = apply_hemiola(material, "cadential", "3/4")
        assert result.pitches[0].degree == 3

    def test_evenly_spaced_selection(self) -> None:
        """Pitches selected at evenly spaced intervals."""
        # 6 pitches selecting 3: indices 0, 2.5->3, 5
        pitches = tuple(FloatingNote(i) for i in [1, 2, 3, 4, 5, 6])
        durations = tuple(Fraction(1, 4) for _ in range(6))
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(3, 2))
        result: TimedMaterial = apply_hemiola(material, "cadential", "3/4")
        # First: degree 1, middle: degree 3 or 4, last: degree 6
        assert result.pitches[0].degree == 1
        assert result.pitches[-1].degree == 6


class TestDetectHemiolaTrigger:
    """Test detect_hemiola_trigger function."""

    def test_climax_triggers_climax_pattern(self) -> None:
        """Climax phrase triggers climax hemiola."""
        result: str | None = detect_hemiola_trigger(
            phrase_index=5, total_phrases=10, is_climax=True, cadence=None
        )
        assert result == "climax"

    def test_climax_overrides_cadence(self) -> None:
        """Climax takes priority over cadence trigger."""
        result: str | None = detect_hemiola_trigger(
            phrase_index=9, total_phrases=10, is_climax=True, cadence="authentic"
        )
        assert result == "climax"

    def test_authentic_cadence_near_end_triggers(self) -> None:
        """Authentic cadence in last 2 phrases triggers cadential hemiola."""
        result: str | None = detect_hemiola_trigger(
            phrase_index=8, total_phrases=10, is_climax=False, cadence="authentic"
        )
        assert result == "cadential"

    def test_half_cadence_near_end_triggers(self) -> None:
        """Half cadence in last 2 phrases triggers cadential hemiola."""
        result: str | None = detect_hemiola_trigger(
            phrase_index=9, total_phrases=10, is_climax=False, cadence="half"
        )
        assert result == "cadential"

    def test_cadence_early_in_piece_no_trigger(self) -> None:
        """Cadence early in piece doesn't trigger hemiola."""
        result: str | None = detect_hemiola_trigger(
            phrase_index=2, total_phrases=10, is_climax=False, cadence="authentic"
        )
        assert result is None

    def test_deceptive_cadence_no_trigger(self) -> None:
        """Deceptive cadence doesn't trigger hemiola."""
        result: str | None = detect_hemiola_trigger(
            phrase_index=9, total_phrases=10, is_climax=False, cadence="deceptive"
        )
        assert result is None

    def test_no_cadence_no_climax_no_trigger(self) -> None:
        """Regular phrase without cadence or climax doesn't trigger."""
        result: str | None = detect_hemiola_trigger(
            phrase_index=5, total_phrases=10, is_climax=False, cadence=None
        )
        assert result is None

    def test_penultimate_phrase_with_cadence(self) -> None:
        """Penultimate phrase (index = total - 2) with cadence triggers."""
        result: str | None = detect_hemiola_trigger(
            phrase_index=8, total_phrases=10, is_climax=False, cadence="authentic"
        )
        assert result == "cadential"

    def test_last_phrase_with_cadence(self) -> None:
        """Last phrase (index = total - 1) with cadence triggers."""
        result: str | None = detect_hemiola_trigger(
            phrase_index=9, total_phrases=10, is_climax=False, cadence="half"
        )
        assert result == "cadential"


class TestHemiolaIntegration:
    """Integration tests for hemiola module."""

    def test_full_cadential_hemiola_workflow(self) -> None:
        """Complete workflow: detect trigger, check metre, apply hemiola."""
        # Detect trigger
        trigger: str | None = detect_hemiola_trigger(
            phrase_index=7, total_phrases=8, is_climax=False, cadence="authentic"
        )
        assert trigger == "cadential"
        # Check metre
        metre: str = "3/4"
        assert can_apply_hemiola(metre) is True
        # Apply hemiola
        pitches = tuple(FloatingNote(i) for i in [1, 3, 5, 1, 3, 5])
        durations = tuple(Fraction(1, 4) for _ in range(6))
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(3, 2))
        result: TimedMaterial = apply_hemiola(material, trigger, metre)
        # Verify result
        assert result.budget == Fraction(3, 2)
        assert len(result.pitches) == 3

    def test_climax_hemiola_in_9_8(self) -> None:
        """Climax hemiola in compound triple metre (9/8)."""
        trigger: str | None = detect_hemiola_trigger(
            phrase_index=5, total_phrases=10, is_climax=True, cadence=None
        )
        assert trigger == "climax"
        metre: str = "9/8"
        assert can_apply_hemiola(metre) is True
        # 9 eighth notes
        pitches = tuple(FloatingNote(i % 7 + 1) for i in range(9))
        durations = tuple(Fraction(1, 8) for _ in range(9))
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(9, 8))
        result: TimedMaterial = apply_hemiola(material, trigger, metre)
        assert result.budget == Fraction(9, 8)

    def test_no_hemiola_in_4_4(self) -> None:
        """Hemiola not applicable in duple metre."""
        metre: str = "4/4"
        assert can_apply_hemiola(metre) is False
        # Even with trigger, can't apply
        trigger: str | None = detect_hemiola_trigger(
            phrase_index=7, total_phrases=8, is_climax=True, cadence="authentic"
        )
        assert trigger == "climax"  # Trigger detected
        # But application would fail
        material: TimedMaterial = TimedMaterial(
            (FloatingNote(1), FloatingNote(2)),
            (Fraction(1, 2), Fraction(1, 2)),
            Fraction(1),
        )
        with pytest.raises(AssertionError):
            apply_hemiola(material, trigger, metre)
