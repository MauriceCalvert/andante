"""100% coverage tests for engine.episode.

Tests import only:
- engine.episode (module under test)
- shared (pitch, timed_material)
- stdlib

Episodes are functional units within phrases that provide treatment and rhythm defaults.
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Rest

from engine.episode import (
    EPISODES,
    extract_intervals,
    generate_interval_episode,
    get_energy_profile,
    get_episode,
    get_rhythm_durations,
    notes_for_bars,
    resolve_rhythm,
    resolve_treatment,
)


class TestEpisodesConstant:
    """Test EPISODES data loaded from YAML."""

    def test_episodes_is_dict(self) -> None:
        """EPISODES is a dictionary."""
        assert isinstance(EPISODES, dict)

    def test_contains_standard_episodes(self) -> None:
        """EPISODES contains standard episode types."""
        standard: list[str] = [
            "statement", "response", "continuation", "cadential",
            "climax", "release", "scalar", "cadenza"
        ]
        for name in standard:
            assert name in EPISODES, f"Missing episode: {name}"

    def test_episode_has_description(self) -> None:
        """Each episode has a description."""
        for name, ep in EPISODES.items():
            assert "description" in ep, f"Episode {name} missing description"

    def test_episode_has_treatment(self) -> None:
        """Each episode has a treatment."""
        for name, ep in EPISODES.items():
            assert "treatment" in ep, f"Episode {name} missing treatment"

    def test_episode_has_energy_profile(self) -> None:
        """Each episode has an energy_profile."""
        for name, ep in EPISODES.items():
            assert "energy_profile" in ep, f"Episode {name} missing energy_profile"


class TestGetEpisode:
    """Test get_episode function."""

    def test_returns_episode_dict(self) -> None:
        """Returns episode dictionary."""
        result: dict = get_episode("statement")
        assert isinstance(result, dict)

    def test_contains_expected_keys(self) -> None:
        """Returned dict has expected keys."""
        result: dict = get_episode("statement")
        assert "description" in result
        assert "treatment" in result
        assert "energy_profile" in result

    def test_statement_treatment_is_statement(self) -> None:
        """statement episode has treatment 'statement'."""
        result: dict = get_episode("statement")
        assert result["treatment"] == "statement"

    def test_continuation_treatment_is_sequence(self) -> None:
        """continuation episode has treatment 'sequence'."""
        result: dict = get_episode("continuation")
        assert result["treatment"] == "sequence"

    def test_unknown_episode_asserts(self) -> None:
        """Unknown episode name raises AssertionError."""
        with pytest.raises(AssertionError, match="Unknown episode"):
            get_episode("nonexistent_episode_xyz")

    def test_release_has_rhythm(self) -> None:
        """release episode has rhythm 'straight'."""
        result: dict = get_episode("release")
        assert result.get("rhythm") == "straight"

    def test_scalar_has_running_rhythm(self) -> None:
        """scalar episode has rhythm 'running'."""
        result: dict = get_episode("scalar")
        assert result.get("rhythm") == "running"


class TestResolveTreatment:
    """Test resolve_treatment function."""

    def test_non_statement_treatment_preserved(self) -> None:
        """Non-statement phrase treatment takes priority."""
        result: str = resolve_treatment("augmentation", "continuation")
        assert result == "augmentation"

    def test_statement_falls_back_to_episode(self) -> None:
        """statement treatment falls back to episode's treatment."""
        # continuation has treatment 'sequence'
        result: str = resolve_treatment("statement", "continuation")
        assert result == "sequence"

    def test_statement_with_none_episode_stays_statement(self) -> None:
        """statement with no episode stays statement."""
        result: str = resolve_treatment("statement", None)
        assert result == "statement"

    def test_sequence_not_overridden(self) -> None:
        """sequence treatment not overridden by episode."""
        result: str = resolve_treatment("sequence", "climax")
        assert result == "sequence"

    def test_inversion_not_overridden(self) -> None:
        """inversion treatment not overridden."""
        result: str = resolve_treatment("inversion", "release")
        assert result == "inversion"

    def test_climax_episode_gives_augmentation(self) -> None:
        """climax episode provides augmentation for statement."""
        result: str = resolve_treatment("statement", "climax")
        assert result == "augmentation"

    def test_response_episode_gives_inversion(self) -> None:
        """response episode provides inversion for statement."""
        result: str = resolve_treatment("statement", "response")
        assert result == "inversion"


class TestResolveRhythm:
    """Test resolve_rhythm function."""

    def test_phrase_rhythm_takes_priority(self) -> None:
        """Phrase rhythm takes priority over episode."""
        result: str | None = resolve_rhythm("dotted", "scalar")
        assert result == "dotted"

    def test_none_phrase_uses_episode(self) -> None:
        """None phrase rhythm uses episode's rhythm."""
        # scalar has rhythm 'running'
        result: str | None = resolve_rhythm(None, "scalar")
        assert result == "running"

    def test_none_phrase_none_episode_returns_none(self) -> None:
        """None phrase and None episode returns None."""
        result: str | None = resolve_rhythm(None, None)
        assert result is None

    def test_episode_without_rhythm_returns_none(self) -> None:
        """Episode with null rhythm returns None."""
        # statement has rhythm: null
        result: str | None = resolve_rhythm(None, "statement")
        assert result is None

    def test_release_provides_straight(self) -> None:
        """release episode provides 'straight' rhythm."""
        result: str | None = resolve_rhythm(None, "release")
        assert result == "straight"

    def test_transition_provides_running(self) -> None:
        """transition episode provides 'running' rhythm."""
        result: str | None = resolve_rhythm(None, "transition")
        assert result == "running"


class TestGetEnergyProfile:
    """Test get_energy_profile function."""

    def test_none_episode_returns_stable(self) -> None:
        """None episode returns 'stable'."""
        result: str = get_energy_profile(None)
        assert result == "stable"

    def test_statement_returns_stable(self) -> None:
        """statement episode returns 'stable'."""
        result: str = get_energy_profile("statement")
        assert result == "stable"

    def test_continuation_returns_rising(self) -> None:
        """continuation episode returns 'rising'."""
        result: str = get_energy_profile("continuation")
        assert result == "rising"

    def test_climax_returns_peak(self) -> None:
        """climax episode returns 'peak'."""
        result: str = get_energy_profile("climax")
        assert result == "peak"

    def test_release_returns_falling(self) -> None:
        """release episode returns 'falling'."""
        result: str = get_energy_profile("release")
        assert result == "falling"

    def test_cadential_returns_resolving(self) -> None:
        """cadential episode returns 'resolving'."""
        result: str = get_energy_profile("cadential")
        assert result == "resolving"

    def test_retransition_returns_suspenseful(self) -> None:
        """retransition episode returns 'suspenseful'."""
        result: str = get_energy_profile("retransition")
        assert result == "suspenseful"


class TestExtractIntervals:
    """Test extract_intervals function."""

    def test_ascending_scale(self) -> None:
        """Ascending scale produces +1 intervals."""
        pitches: tuple[FloatingNote, ...] = tuple(
            FloatingNote(i) for i in [1, 2, 3, 4]
        )
        result: tuple[int, ...] = extract_intervals(pitches)
        assert result == (1, 1, 1)

    def test_descending_scale(self) -> None:
        """Descending scale produces -1 intervals."""
        pitches: tuple[FloatingNote, ...] = tuple(
            FloatingNote(i) for i in [4, 3, 2, 1]
        )
        result: tuple[int, ...] = extract_intervals(pitches)
        assert result == (-1, -1, -1)

    def test_mixed_intervals(self) -> None:
        """Mixed motion produces varied intervals."""
        pitches: tuple[FloatingNote, ...] = (
            FloatingNote(1), FloatingNote(3), FloatingNote(2), FloatingNote(5)
        )
        result: tuple[int, ...] = extract_intervals(pitches)
        assert result == (2, -1, 3)

    def test_single_pitch_empty_intervals(self) -> None:
        """Single pitch produces empty interval tuple."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        result: tuple[int, ...] = extract_intervals(pitches)
        assert result == ()

    def test_empty_pitches_empty_intervals(self) -> None:
        """Empty pitch tuple produces empty intervals."""
        pitches: tuple[FloatingNote, ...] = ()
        result: tuple[int, ...] = extract_intervals(pitches)
        assert result == ()

    def test_rest_treated_as_degree_1(self) -> None:
        """Rest (no degree attr) treated as degree 1."""
        pitches: tuple[FloatingNote | Rest, ...] = (
            FloatingNote(3), Rest()
        )
        result: tuple[int, ...] = extract_intervals(pitches)
        # 3 to 1 = -2
        assert result == (-2,)


class TestNotesForBars:
    """Test notes_for_bars function."""

    def test_running_16_per_bar(self) -> None:
        """Running rhythm has 16 notes per bar."""
        result: int = notes_for_bars(2, "running")
        assert result == 32

    def test_dotted_8_per_bar(self) -> None:
        """Dotted rhythm has 8 notes per bar (4 pairs of long-short)."""
        result: int = notes_for_bars(2, "dotted")
        assert result == 16

    def test_straight_4_per_bar(self) -> None:
        """Straight rhythm has 4 notes per bar."""
        result: int = notes_for_bars(3, "straight")
        assert result == 12

    def test_lombardic_8_per_bar(self) -> None:
        """Lombardic rhythm has 8 notes per bar."""
        result: int = notes_for_bars(2, "lombardic")
        assert result == 16

    def test_unknown_rhythm_8_per_bar(self) -> None:
        """Unknown rhythm defaults to 8 notes per bar."""
        result: int = notes_for_bars(2, "unknown_rhythm")
        assert result == 16

    def test_one_bar(self) -> None:
        """Single bar calculation."""
        result: int = notes_for_bars(1, "running")
        assert result == 16


class TestGetRhythmDurations:
    """Test get_rhythm_durations function."""

    def test_running_sixteenths(self) -> None:
        """Running rhythm produces sixteenth notes."""
        result: tuple[Fraction, ...] = get_rhythm_durations("running", 1)
        assert all(d == Fraction(1, 16) for d in result)
        assert sum(result) == Fraction(1)

    def test_straight_quarters(self) -> None:
        """Straight rhythm produces quarter notes."""
        result: tuple[Fraction, ...] = get_rhythm_durations("straight", 1)
        assert all(d == Fraction(1, 4) for d in result)
        assert sum(result) == Fraction(1)

    def test_dotted_pattern(self) -> None:
        """Dotted rhythm alternates 3/16 and 1/16."""
        result: tuple[Fraction, ...] = get_rhythm_durations("dotted", 1)
        # Pattern: 3/16, 1/16, 3/16, 1/16 = 1
        assert result[0] == Fraction(3, 16)
        assert result[1] == Fraction(1, 16)
        assert sum(result) == Fraction(1)

    def test_lombardic_pattern(self) -> None:
        """Lombardic rhythm alternates 1/16 and 3/16."""
        result: tuple[Fraction, ...] = get_rhythm_durations("lombardic", 1)
        # Pattern: 1/16, 3/16, 1/16, 3/16 = 1
        assert result[0] == Fraction(1, 16)
        assert result[1] == Fraction(3, 16)
        assert sum(result) == Fraction(1)

    def test_unknown_rhythm_eighths(self) -> None:
        """Unknown rhythm defaults to eighth notes."""
        result: tuple[Fraction, ...] = get_rhythm_durations("unknown", 1)
        assert all(d == Fraction(1, 8) for d in result)
        assert sum(result) == Fraction(1)

    def test_two_bars(self) -> None:
        """Multiple bars produces correct total duration."""
        result: tuple[Fraction, ...] = get_rhythm_durations("straight", 2)
        assert sum(result) == Fraction(2)

    def test_partial_last_duration(self) -> None:
        """Last duration can be partial to fill budget exactly."""
        # 3/16 + 1/16 = 1/4, so 4 complete patterns = 1 bar
        # For budget=1, dotted should fit exactly
        result: tuple[Fraction, ...] = get_rhythm_durations("dotted", 1)
        assert sum(result) == Fraction(1)


class TestGenerateIntervalEpisode:
    """Test generate_interval_episode function."""

    def test_returns_timed_material(self) -> None:
        """Returns TimedMaterial instance."""
        from shared.timed_material import TimedMaterial
        intervals: tuple[int, ...] = (1, 2, -1)
        result = generate_interval_episode(intervals, 1, "running", 1)
        assert isinstance(result, TimedMaterial)

    def test_budget_matches_bars(self) -> None:
        """Budget equals number of bars."""
        intervals: tuple[int, ...] = (1, -1)
        result = generate_interval_episode(intervals, 1, "running", 2)
        assert result.budget == Fraction(2)

    def test_durations_sum_to_budget(self) -> None:
        """Durations sum to budget."""
        intervals: tuple[int, ...] = (1, 2)
        result = generate_interval_episode(intervals, 1, "straight", 2)
        assert sum(result.durations) == result.budget

    def test_pitches_count_matches_durations(self) -> None:
        """Pitch count matches duration count."""
        intervals: tuple[int, ...] = (1,)
        result = generate_interval_episode(intervals, 1, "running", 1)
        assert len(result.pitches) == len(result.durations)

    def test_all_pitches_are_floating_notes(self) -> None:
        """All pitches are FloatingNote instances."""
        intervals: tuple[int, ...] = (1, 2, 3)
        result = generate_interval_episode(intervals, 1, "running", 1)
        for pitch in result.pitches:
            assert isinstance(pitch, FloatingNote)

    def test_degrees_wrapped_to_1_7(self) -> None:
        """All degrees are in valid range 1-7."""
        intervals: tuple[int, ...] = (5, 5, 5)  # Will overflow
        result = generate_interval_episode(intervals, 7, "running", 1)
        for pitch in result.pitches:
            assert 1 <= pitch.degree <= 7

    def test_different_phrase_index_different_start(self) -> None:
        """Different phrase_index produces different starting points."""
        intervals: tuple[int, ...] = (1,)
        r1 = generate_interval_episode(intervals, 1, "straight", 1, phrase_index=0)
        r2 = generate_interval_episode(intervals, 1, "straight", 1, phrase_index=1)
        # Different phrase_index should produce different sequences
        d1: list[int] = [p.degree for p in r1.pitches]
        d2: list[int] = [p.degree for p in r2.pitches]
        assert d1 != d2

    def test_phrase_index_affects_direction(self) -> None:
        """Even phrase_index ascends, odd descends."""
        intervals: tuple[int, ...] = (1,)
        r0 = generate_interval_episode(intervals, 4, "straight", 1, phrase_index=0)
        r1 = generate_interval_episode(intervals, 4, "straight", 1, phrase_index=1)
        # Even phrase ascends (+1), odd descends (-1)
        d0: list[int] = [p.degree for p in r0.pitches]
        d1: list[int] = [p.degree for p in r1.pitches]
        # Direction should differ
        # r0 should tend up (intervals * 1), r1 should tend down (intervals * -1)
        assert d0 != d1

    def test_empty_intervals_uses_step_of_1(self) -> None:
        """Empty intervals tuple uses step of 1."""
        intervals: tuple[int, ...] = ()
        result = generate_interval_episode(intervals, 1, "straight", 1)
        # Should still produce notes (using default interval of 1)
        assert len(result.pitches) > 0

    def test_running_rhythm_produces_many_notes(self) -> None:
        """Running rhythm produces 16 notes per bar."""
        intervals: tuple[int, ...] = (1, 2)
        result = generate_interval_episode(intervals, 1, "running", 1)
        assert len(result.pitches) == 16

    def test_straight_rhythm_produces_4_notes(self) -> None:
        """Straight rhythm produces 4 notes per bar."""
        intervals: tuple[int, ...] = (1,)
        result = generate_interval_episode(intervals, 1, "straight", 1)
        assert len(result.pitches) == 4

    def test_phrase_index_advances_interval_iterator(self) -> None:
        """Non-zero phrase_index advances through interval cycle.

        With intervals=(1, 2, 3) and phrase_index=1, start_offset=1,
        so iterator advances once before generating notes.
        """
        intervals: tuple[int, ...] = (1, 2, 3)
        # phrase_index=0: starts at interval[0]=1
        r0 = generate_interval_episode(intervals, 4, "straight", 1, phrase_index=0)
        # phrase_index=1: start_offset=1%3=1, advances once, starts at interval[1]=2
        r1 = generate_interval_episode(intervals, 4, "straight", 1, phrase_index=1)
        # phrase_index=2: start_offset=2%3=2, advances twice, starts at interval[2]=3
        r2 = generate_interval_episode(intervals, 4, "straight", 1, phrase_index=2)
        # The sequences should differ due to different starting points in cycle
        d0: list[int] = [p.degree for p in r0.pitches]
        d1: list[int] = [p.degree for p in r1.pitches]
        d2: list[int] = [p.degree for p in r2.pitches]
        # All three should be different sequences
        assert d0 != d1
        assert d1 != d2
        assert d0 != d2


class TestIntegration:
    """Integration tests for episode module."""

    def test_episode_to_material_workflow(self) -> None:
        """Complete workflow from episode to material."""
        # Get episode definition
        ep: dict = get_episode("scalar")
        # Resolve treatment and rhythm
        treatment: str = resolve_treatment("statement", "scalar")
        rhythm: str | None = resolve_rhythm(None, "scalar")
        energy: str = get_energy_profile("scalar")
        # Generate material
        assert treatment == "sequence"
        assert rhythm == "running"
        assert energy == "rising"
        # Generate episode material
        intervals: tuple[int, ...] = (1, 2, -1)
        result = generate_interval_episode(intervals, 1, rhythm, 2)
        assert result.budget == Fraction(2)

    def test_all_episodes_have_valid_energy_profiles(self) -> None:
        """All episodes have valid energy profile values."""
        valid_profiles: set[str] = {
            "stable", "rising", "peak", "falling",
            "resolving", "suspenseful", "plateau", "intensification"
        }
        for name in EPISODES:
            profile: str = get_energy_profile(name)
            assert profile in valid_profiles, f"Invalid profile for {name}: {profile}"

    def test_generate_with_all_rhythm_types(self) -> None:
        """Generate interval episode with all rhythm types."""
        intervals: tuple[int, ...] = (1, -1)
        rhythms: list[str] = ["running", "dotted", "straight", "lombardic"]
        for rhythm in rhythms:
            result = generate_interval_episode(intervals, 1, rhythm, 1)
            assert sum(result.durations) == Fraction(1)
            assert len(result.pitches) == len(result.durations)
