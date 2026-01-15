"""Tests for interleaved (Goldberg-style) counterpoint treatment.

Category B tests: verify interleaved crossing behavior and shared tessitura.
Tests import only:
- engine modules (module under test)
- shared types
- stdlib
"""
from fractions import Fraction
import pytest
from engine.slice_solver import (
    _check_voice_crossings,
    _score_configuration,
    get_voice_range,
    INTERLEAVED_RANGES,
    VOICE_CROSSING_PENALTY,
    VOICE_CROSSING_REWARD,
)
from engine.voice_config import (
    create_interleaved_voices,
    INTERLEAVED_RANGES as VC_INTERLEAVED_RANGES,
    VoiceSet,
)
from planner.cs_generator import (
    generate_countersubject,
    Subject,
    _interval_class,
    MAJOR_SCALE,
)


class TestInterleavedRanges:
    """Test interleaved voice ranges are shared."""

    def test_interleaved_ranges_loaded(self) -> None:
        """Interleaved ranges are loaded from predicates.yaml."""
        assert "voice_1" in INTERLEAVED_RANGES
        assert "voice_2" in INTERLEAVED_RANGES

    def test_interleaved_ranges_equal(self) -> None:
        """Both interleaved voices share the same range."""
        assert INTERLEAVED_RANGES["voice_1"] == INTERLEAVED_RANGES["voice_2"]

    def test_interleaved_range_reasonable(self) -> None:
        """Interleaved range spans a reasonable tessitura."""
        range_1 = INTERLEAVED_RANGES["voice_1"]
        span = range_1[1] - range_1[0]
        assert span >= 12  # At least an octave
        assert span <= 24  # At most two octaves


class TestGetVoiceRangeInterleaved:
    """Test get_voice_range with interleaved=True."""

    def test_interleaved_voice_0(self) -> None:
        """Voice 0 uses interleaved range when flag set."""
        normal_range = get_voice_range(0, 2, interleaved=False)
        interleaved_range = get_voice_range(0, 2, interleaved=True)
        assert interleaved_range != normal_range
        assert interleaved_range == INTERLEAVED_RANGES["voice_1"]

    def test_interleaved_voice_1(self) -> None:
        """Voice 1 uses interleaved range when flag set."""
        normal_range = get_voice_range(1, 2, interleaved=False)
        interleaved_range = get_voice_range(1, 2, interleaved=True)
        assert interleaved_range != normal_range
        assert interleaved_range == INTERLEAVED_RANGES["voice_2"]

    def test_interleaved_both_same(self) -> None:
        """Both voices have same range in interleaved mode."""
        range_0 = get_voice_range(0, 2, interleaved=True)
        range_1 = get_voice_range(1, 2, interleaved=True)
        assert range_0 == range_1

    def test_non_interleaved_different(self) -> None:
        """Normal mode has different ranges for soprano/bass."""
        range_0 = get_voice_range(0, 2, interleaved=False)
        range_1 = get_voice_range(1, 2, interleaved=False)
        assert range_0 != range_1


class TestCreateInterleavedVoices:
    """Test create_interleaved_voices factory."""

    def test_creates_two_voices(self) -> None:
        """Factory creates exactly 2 voices."""
        vs = create_interleaved_voices()
        assert vs.count == 2

    def test_voice_names(self) -> None:
        """Voices are named voice_1 and voice_2."""
        vs = create_interleaved_voices()
        assert vs.by_index(0).name == "voice_1"
        assert vs.by_index(1).name == "voice_2"

    def test_medians_similar(self) -> None:
        """Both voice medians are within shared range."""
        vs = create_interleaved_voices()
        range_low = VC_INTERLEAVED_RANGES["voice_1"][0]
        range_high = VC_INTERLEAVED_RANGES["voice_1"][1]
        assert range_low <= vs.by_index(0).median <= range_high
        assert range_low <= vs.by_index(1).median <= range_high


class TestCrossingModes:
    """Test voice crossing penalty/reward modes."""

    def test_penalize_mode_positive_cost(self) -> None:
        """Penalize mode returns positive cost for crossing."""
        config = (60, 65)  # Higher index (65) above lower index (60) = crossing
        cost = _check_voice_crossings(config, crossing_mode="penalize")
        assert cost > 0
        assert cost == VOICE_CROSSING_PENALTY

    def test_reward_mode_negative_cost(self) -> None:
        """Reward mode returns negative cost (reward) for crossing."""
        config = (60, 65)  # Crossing
        cost = _check_voice_crossings(config, crossing_mode="reward")
        assert cost < 0
        assert cost == VOICE_CROSSING_REWARD

    def test_allow_mode_zero_cost(self) -> None:
        """Allow mode returns zero cost for crossing."""
        config = (60, 65)  # Crossing
        cost = _check_voice_crossings(config, crossing_mode="allow")
        assert cost == 0

    def test_no_crossing_zero_cost(self) -> None:
        """No crossing returns zero cost in all modes."""
        config = (72, 60)  # No crossing (higher index lower pitch)
        assert _check_voice_crossings(config, crossing_mode="penalize") == 0
        assert _check_voice_crossings(config, crossing_mode="reward") == 0
        assert _check_voice_crossings(config, crossing_mode="allow") == 0

    def test_multiple_crossings_accumulate(self) -> None:
        """Multiple crossings accumulate cost/reward."""
        # 4-voice config with 2 crossings: (60, 65, 70, 55)
        # Index 1 (65) > Index 0 (60) = crossing
        # Index 2 (70) > Index 1 (65) = crossing
        # Index 3 (55) < Index 2 (70) = no crossing
        config = (60, 65, 70, 55)
        penalty_cost = _check_voice_crossings(config, crossing_mode="penalize")
        reward_cost = _check_voice_crossings(config, crossing_mode="reward")
        assert penalty_cost == 2 * VOICE_CROSSING_PENALTY
        assert reward_cost == 2 * VOICE_CROSSING_REWARD


class TestScoreConfigurationCrossingMode:
    """Test _score_configuration with crossing_mode parameter."""

    def test_default_penalizes_crossing(self) -> None:
        """Default mode penalizes voice crossing."""
        config = (60, 65)  # Crossing
        chord_tones = {0, 4, 7}
        score_default = _score_configuration(config, None, chord_tones)
        score_reward = _score_configuration(config, None, chord_tones, "reward")
        assert score_default > score_reward

    def test_reward_mode_prefers_crossing(self) -> None:
        """Reward mode prefers configurations with crossings."""
        crossing_config = (60, 65)  # Crossing
        normal_config = (65, 60)  # No crossing
        chord_tones = {0, 4, 7}
        score_crossing = _score_configuration(crossing_config, None, chord_tones, "reward")
        score_normal = _score_configuration(normal_config, None, chord_tones, "reward")
        # Crossing should score better (lower) in reward mode
        assert score_crossing < score_normal


class TestInterleavedInvertibilityConstraints:
    """Test invertibility constraints for interleaved counterpoint."""

    def test_seconds_are_bad_intervals(self) -> None:
        """Seconds (1, 2 semitones) should be avoided in interleaved mode."""
        # Check interval class calculation
        assert _interval_class(1, 2, MAJOR_SCALE) == 2  # C to D = major 2nd
        assert _interval_class(3, 4, MAJOR_SCALE) == 1  # E to F = minor 2nd (1 semitone)

    def test_thirds_sixths_good_intervals(self) -> None:
        """Thirds and sixths are good for invertibility."""
        # Minor 3rd = 3 semitones, Major 3rd = 4 semitones
        # Minor 6th = 8 semitones, Major 6th = 9 semitones
        ic_third = _interval_class(1, 3, MAJOR_SCALE)  # C to E = major 3rd
        assert ic_third in {3, 4}

    def test_generate_cs_interleaved(self) -> None:
        """Counter-subject generation with interleaved flag runs without error."""
        subject = Subject(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 4),) * 5,
            mode="major",
        )
        cs = generate_countersubject(subject, timeout_seconds=5.0, interleaved=True)
        # Should produce a result (may be None if constraints too tight)
        # The key test is that it doesn't crash
        assert cs is None or len(cs.degrees) > 0


class TestInterleavedTextureYaml:
    """Test interleaved texture loaded from textures.yaml."""

    def test_texture_exists(self) -> None:
        """Interleaved texture exists in textures.yaml."""
        from pathlib import Path
        import yaml
        textures_path = Path(__file__).parent.parent.parent / "data" / "textures.yaml"
        with open(textures_path, encoding="utf-8") as f:
            textures = yaml.safe_load(f)
        assert "interleaved" in textures

    def test_texture_has_offset_time_relation(self) -> None:
        """Interleaved texture has time_relation: offset."""
        from pathlib import Path
        import yaml
        textures_path = Path(__file__).parent.parent.parent / "data" / "textures.yaml"
        with open(textures_path, encoding="utf-8") as f:
            textures = yaml.safe_load(f)
        interleaved = textures["interleaved"]
        assert interleaved.get("time_relation") == "offset"

    def test_texture_has_overlapping_tessitura(self) -> None:
        """Interleaved texture has tessitura: overlapping in parameters."""
        from pathlib import Path
        import yaml
        textures_path = Path(__file__).parent.parent.parent / "data" / "textures.yaml"
        with open(textures_path, encoding="utf-8") as f:
            textures = yaml.safe_load(f)
        interleaved = textures["interleaved"]
        params = interleaved.get("parameters", {})
        assert params.get("tessitura") == "overlapping"
