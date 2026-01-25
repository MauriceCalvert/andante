"""Tests for builder.costs module.

Category A tests: Pure functions, no mocks, specification-based.

Specification source: solver_specs.md
- Step (0-2 semitones): configurable weight
- Skip (3-4 semitones): configurable weight
- Leap (5-7 semitones): configurable weight
- Large leap (8+ semitones): configurable weight
- Leap recovery: leaps >4 semitones should resolve by contrary step
- Counter-motion: bonus for contrary (-0.2), penalty for similar (+0.3)
"""
from fractions import Fraction

import pytest

from builder.costs import (
    VoiceMode,
    melodic_motion_category,
    cost_melodic_motion,
    cost_leap_recovery,
    cost_tessitura_deviation,
    cost_voice_motion,
    cost_voice_crossing,
    cost_bass_motion,
    cost_directional,
    compute_total_cost,
    TESSITURA_SPAN,
    TESSITURA_BEYOND_COST,
    DIRECTION_THRESHOLD,
)
from builder.slice import Slice, extract_slices


DEFAULT_WEIGHTS: dict[str, float] = {
    "unison": 2.2,  # ~11x step (corpus-derived ratio)
    "step": 0.2,
    "skip": 0.4,
    "leap": 0.8,
    "large_leap": 1.5,
}


class TestMelodicMotionCategory:
    """Tests for melodic_motion_category classification."""

    def test_unison_is_unison(self) -> None:
        assert melodic_motion_category(0) == "unison"

    def test_semitone_is_step(self) -> None:
        assert melodic_motion_category(1) == "step"

    def test_whole_tone_is_step(self) -> None:
        assert melodic_motion_category(2) == "step"

    def test_minor_third_is_skip(self) -> None:
        assert melodic_motion_category(3) == "skip"

    def test_major_third_is_skip(self) -> None:
        assert melodic_motion_category(4) == "skip"

    def test_fourth_is_leap(self) -> None:
        assert melodic_motion_category(5) == "leap"

    def test_fifth_is_leap(self) -> None:
        assert melodic_motion_category(7) == "leap"

    def test_sixth_is_large_leap(self) -> None:
        assert melodic_motion_category(8) == "large_leap"

    def test_octave_is_large_leap(self) -> None:
        assert melodic_motion_category(12) == "large_leap"


class TestCostMelodicMotion:
    """Tests for cost_melodic_motion function."""

    def _make_slices(self, pitches: list[int], voice: int = 0, voice_count: int = 2) -> list[Slice]:
        """Helper to create slices from pitch sequence."""
        pitch_dict: dict[tuple[Fraction, int], int] = {}
        for i, pitch in enumerate(pitches):
            offset = Fraction(i, 4)  # Quarter note spacing
            pitch_dict[(offset, voice)] = pitch
            # Add placeholder for other voices
            for v in range(voice_count):
                if v != voice and (offset, v) not in pitch_dict:
                    pitch_dict[(offset, v)] = 60  # placeholder
        return extract_slices(pitch_dict, voice_count)

    def test_stepwise_sequence_low_cost(self) -> None:
        slices = self._make_slices([60, 62, 64, 65, 67])  # All steps
        cost = cost_melodic_motion(slices, voice=0, motive_weights=DEFAULT_WEIGHTS)
        # 4 intervals, all steps at 0.2 each
        assert cost == pytest.approx(0.8, rel=0.01)

    def test_leapy_sequence_high_cost(self) -> None:
        slices = self._make_slices([60, 67, 72, 79, 84])  # Leaps and large leaps
        cost = cost_melodic_motion(slices, voice=0, motive_weights=DEFAULT_WEIGHTS)
        # Higher cost than stepwise
        stepwise_cost = cost_melodic_motion(
            self._make_slices([60, 62, 64, 65, 67]), voice=0, motive_weights=DEFAULT_WEIGHTS
        )
        assert cost > stepwise_cost

    def test_empty_slices(self) -> None:
        cost = cost_melodic_motion([], voice=0, motive_weights=DEFAULT_WEIGHTS)
        assert cost == 0.0


class TestCostLeapRecovery:
    """Tests for cost_leap_recovery function."""

    def _make_slices(self, pitches: list[int]) -> list[Slice]:
        """Helper to create slices from pitch sequence."""
        pitch_dict: dict[tuple[Fraction, int], int] = {}
        for i, pitch in enumerate(pitches):
            pitch_dict[(Fraction(i, 4), 0)] = pitch
            pitch_dict[(Fraction(i, 4), 1)] = 48  # bass placeholder
        return extract_slices(pitch_dict, voice_count=2)

    def test_no_penalty_small_intervals(self) -> None:
        slices = self._make_slices([60, 62, 64])  # All steps
        cost = cost_leap_recovery(slices, voice=0)
        assert cost == 0.0

    def test_no_penalty_correct_recovery(self) -> None:
        slices = self._make_slices([60, 67, 65])  # Leap up, step down
        cost = cost_leap_recovery(slices, voice=0)
        assert cost == 0.0

    def test_penalty_no_recovery(self) -> None:
        slices = self._make_slices([60, 67, 69])  # Leap up, continue up
        cost = cost_leap_recovery(slices, voice=0)
        assert cost > 0.0

    def test_penalty_same_direction(self) -> None:
        slices = self._make_slices([60, 67, 72])  # Leap up, leap up again
        cost = cost_leap_recovery(slices, voice=0)
        assert cost > 0.0


class TestCostTessituraDeviation:
    """Tests for cost_tessitura_deviation function (two-tier model)."""

    def _make_slices(self, pitches: list[int]) -> list[Slice]:
        pitch_dict: dict[tuple[Fraction, int], int] = {}
        for i, pitch in enumerate(pitches):
            pitch_dict[(Fraction(i, 4), 0)] = pitch
            pitch_dict[(Fraction(i, 4), 1)] = 48
        return extract_slices(pitch_dict, voice_count=2)

    def test_within_span_zero_cost(self) -> None:
        """Notes within span (<=7 from median) have zero cost."""
        median = 70
        slices = self._make_slices([70, 72, 68, 77, 63])  # All within 7 of 70
        cost = cost_tessitura_deviation(slices, voice=0, median=median)
        assert cost == 0.0

    def test_at_span_boundary_zero_cost(self) -> None:
        """Notes exactly at span boundary (7 from median) have zero cost."""
        median = 70
        slices = self._make_slices([77, 63])  # Exactly 7 away
        cost = cost_tessitura_deviation(slices, voice=0, median=median)
        assert cost == 0.0

    def test_beyond_span_has_cost(self) -> None:
        """Notes beyond span incur penalty."""
        median = 70
        slices = self._make_slices([78])  # 8 semitones from median, 1 beyond span
        cost = cost_tessitura_deviation(slices, voice=0, median=median)
        assert cost == TESSITURA_BEYOND_COST  # 1 * 100 = 100

    def test_far_beyond_span_high_cost(self) -> None:
        """Notes far beyond span incur escalating penalty."""
        median = 70
        slices = self._make_slices([80])  # 10 semitones from median, 3 beyond span
        cost = cost_tessitura_deviation(slices, voice=0, median=median)
        assert cost == 3 * TESSITURA_BEYOND_COST  # 3 * 100 = 300

    def test_multiple_notes_beyond_span(self) -> None:
        """Multiple notes beyond span accumulate cost."""
        median = 70
        slices = self._make_slices([78, 79])  # 1 beyond + 2 beyond
        cost = cost_tessitura_deviation(slices, voice=0, median=median)
        assert cost == 3 * TESSITURA_BEYOND_COST  # (1 + 2) * 100 = 300


class TestCostVoiceMotion:
    """Tests for cost_voice_motion function."""

    def _make_slices(self, soprano: list[int], bass: list[int]) -> list[Slice]:
        assert len(soprano) == len(bass)
        pitch_dict: dict[tuple[Fraction, int], int] = {}
        for i, (s, b) in enumerate(zip(soprano, bass)):
            pitch_dict[(Fraction(i, 4), 0)] = s
            pitch_dict[(Fraction(i, 4), 1)] = b
        return extract_slices(pitch_dict, voice_count=2)

    def test_contrary_motion_negative_cost(self) -> None:
        # Soprano up, bass down
        slices = self._make_slices([60, 62, 64], [48, 47, 45])
        cost = cost_voice_motion(slices, voice_a=0, voice_b=1)
        assert cost < 0  # Contrary motion gives reward

    def test_similar_motion_positive_cost(self) -> None:
        # Both voices up
        slices = self._make_slices([60, 62, 64], [48, 50, 52])
        cost = cost_voice_motion(slices, voice_a=0, voice_b=1)
        assert cost > 0  # Similar/parallel motion penalised


class TestCostVoiceCrossing:
    """Tests for cost_voice_crossing function."""

    def _make_slices(self, soprano: list[int], bass: list[int]) -> list[Slice]:
        pitch_dict: dict[tuple[Fraction, int], int] = {}
        for i, (s, b) in enumerate(zip(soprano, bass)):
            pitch_dict[(Fraction(i, 4), 0)] = s
            pitch_dict[(Fraction(i, 4), 1)] = b
        return extract_slices(pitch_dict, voice_count=2)

    def test_no_crossing_zero_cost(self) -> None:
        slices = self._make_slices([72, 74, 76], [48, 50, 52])
        cost = cost_voice_crossing(slices, voice_upper=0, voice_lower=1, voice_mode=VoiceMode.STANDARD)
        assert cost == 0.0

    def test_crossing_positive_cost_standard(self) -> None:
        # Bass crosses above soprano
        slices = self._make_slices([60, 60, 60], [65, 65, 65])
        cost = cost_voice_crossing(slices, voice_upper=0, voice_lower=1, voice_mode=VoiceMode.STANDARD)
        assert cost > 0  # Penalised in standard mode

    def test_crossing_negative_cost_interleaved(self) -> None:
        # Bass crosses above soprano
        slices = self._make_slices([60, 60, 60], [65, 65, 65])
        cost = cost_voice_crossing(slices, voice_upper=0, voice_lower=1, voice_mode=VoiceMode.INTERLEAVED)
        assert cost < 0  # Rewarded in interleaved mode


class TestCostDirectional:
    """Tests for cost_directional function (escalating penalty)."""

    def _make_slices(self, pitches: list[int]) -> list[Slice]:
        pitch_dict: dict[tuple[Fraction, int], int] = {}
        for i, pitch in enumerate(pitches):
            pitch_dict[(Fraction(i, 4), 0)] = pitch
            pitch_dict[(Fraction(i, 4), 1)] = 48
        return extract_slices(pitch_dict, voice_count=2)

    def test_four_steps_same_direction_no_cost(self) -> None:
        """First 4 consecutive steps in same direction have no penalty."""
        slices = self._make_slices([60, 62, 64, 66, 68])  # 4 steps up
        cost = cost_directional(slices, voice=0)
        assert cost == 0.0

    def test_five_steps_same_direction_has_cost(self) -> None:
        """5th consecutive step incurs penalty."""
        slices = self._make_slices([60, 62, 64, 66, 68, 70])  # 5 steps up
        cost = cost_directional(slices, voice=0)
        assert cost == 100.0  # (5-4) * 100

    def test_six_steps_escalates(self) -> None:
        """6th consecutive step adds more penalty."""
        slices = self._make_slices([60, 62, 64, 66, 68, 70, 72])  # 6 steps up
        cost = cost_directional(slices, voice=0)
        # 5th step: 100, 6th step: 200 = 300 total
        assert cost == 300.0

    def test_direction_change_resets(self) -> None:
        """Changing direction resets the counter."""
        slices = self._make_slices([60, 62, 64, 66, 68, 66, 64, 62, 60, 58])  # 4 up, 5 down
        cost = cost_directional(slices, voice=0)
        assert cost == 100.0  # Only the 5th down step incurs cost

    def test_unison_does_not_break_or_continue(self) -> None:
        """Unison doesn't count as direction change or continuation."""
        slices = self._make_slices([60, 62, 64, 64, 66, 68, 70])  # 3 up, unison, 2 up = 5 up total
        cost = cost_directional(slices, voice=0)
        # 5 steps up total (unison ignored), so 5th step costs 100
        assert cost == 100.0

    def test_descending_same_as_ascending(self) -> None:
        """Descending motion is treated same as ascending."""
        slices = self._make_slices([70, 68, 66, 64, 62, 60])  # 5 steps down
        cost = cost_directional(slices, voice=0)
        assert cost == 100.0


class TestCostBassMotion:
    """Tests for cost_bass_motion function."""

    def _make_slices(self, bass: list[int]) -> list[Slice]:
        pitch_dict: dict[tuple[Fraction, int], int] = {}
        for i, b in enumerate(bass):
            pitch_dict[(Fraction(i, 4), 0)] = 72  # soprano placeholder
            pitch_dict[(Fraction(i, 4), 1)] = b
        return extract_slices(pitch_dict, voice_count=2)

    def test_stepwise_bass_low_cost(self) -> None:
        slices = self._make_slices([48, 50, 52, 50, 48])  # Steps
        cost = cost_bass_motion(slices, bass_voice=1)
        leapy_cost = cost_bass_motion(self._make_slices([48, 55, 60, 67, 72]), bass_voice=1)
        assert cost < leapy_cost


class TestComputeTotalCost:
    """Tests for compute_total_cost aggregate function."""

    def _make_slices(self, soprano: list[int], bass: list[int]) -> list[Slice]:
        pitch_dict: dict[tuple[Fraction, int], int] = {}
        for i, (s, b) in enumerate(zip(soprano, bass)):
            pitch_dict[(Fraction(i, 4), 0)] = s
            pitch_dict[(Fraction(i, 4), 1)] = b
        return extract_slices(pitch_dict, voice_count=2)

    def test_stepwise_lower_than_leapy(self) -> None:
        stepwise = self._make_slices([60, 62, 64, 65, 67], [48, 47, 48, 47, 48])
        leapy = self._make_slices([60, 67, 72, 79, 84], [48, 55, 60, 67, 72])
        medians = {0: 70, 1: 48}
        cost_step = compute_total_cost(stepwise, 2, medians, DEFAULT_WEIGHTS, VoiceMode.STANDARD)
        cost_leap = compute_total_cost(leapy, 2, medians, DEFAULT_WEIGHTS, VoiceMode.STANDARD)
        assert cost_step < cost_leap

    def test_empty_sequences(self) -> None:
        cost = compute_total_cost([], 2, {0: 70, 1: 48}, DEFAULT_WEIGHTS, VoiceMode.STANDARD)
        assert cost == 0.0
