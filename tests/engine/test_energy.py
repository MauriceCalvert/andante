"""100% coverage tests for engine.energy.

Tests import only:
- engine.energy (module under test)
- stdlib
"""
import pytest
from engine.energy import (
    ENERGY_LEVELS,
    get_energy_level,
    get_register_shift,
    get_rhythm_override,
    get_articulation,
)


class TestEnergyLevelsData:
    """Test ENERGY_LEVELS data structure."""

    def test_energy_levels_is_dict(self) -> None:
        assert isinstance(ENERGY_LEVELS, dict)

    def test_all_energy_levels_present(self) -> None:
        expected = {"low", "stable", "moderate", "rising", "peak", "falling", "suspenseful", "resolving", "plateau", "intensification"}
        assert set(ENERGY_LEVELS.keys()) == expected

    def test_all_levels_have_description(self) -> None:
        for name, level in ENERGY_LEVELS.items():
            assert "description" in level, f"{name} missing description"


class TestGetEnergyLevel:
    """Test get_energy_level function."""

    def test_low_level(self) -> None:
        level = get_energy_level("low")
        assert level["register_shift"] == -3
        assert level["rhythm_override"] == "straight"
        assert level["articulation"] == "legato"

    def test_stable_level(self) -> None:
        level = get_energy_level("stable")
        assert level["register_shift"] == 0
        assert level["rhythm_override"] is None
        assert level["articulation"] is None

    def test_peak_level(self) -> None:
        level = get_energy_level("peak")
        assert level["register_shift"] == 5
        assert level["articulation"] == "accent"

    def test_suspenseful_level(self) -> None:
        level = get_energy_level("suspenseful")
        assert level["articulation"] == "staccato"

    def test_unknown_level_raises(self) -> None:
        with pytest.raises(AssertionError, match="Unknown energy level"):
            get_energy_level("nonexistent")

    def test_all_levels_valid(self) -> None:
        for name in ENERGY_LEVELS:
            level = get_energy_level(name)
            assert isinstance(level, dict)


class TestGetRegisterShift:
    """Test get_register_shift function."""

    def test_low_negative_shift(self) -> None:
        assert get_register_shift("low") == -3

    def test_stable_zero_shift(self) -> None:
        assert get_register_shift("stable") == 0

    def test_moderate_zero_shift(self) -> None:
        assert get_register_shift("moderate") == 0

    def test_rising_positive_shift(self) -> None:
        assert get_register_shift("rising") == 2

    def test_peak_positive_shift(self) -> None:
        assert get_register_shift("peak") == 5

    def test_falling_negative_shift(self) -> None:
        assert get_register_shift("falling") == -2

    def test_resolving_negative_shift(self) -> None:
        assert get_register_shift("resolving") == -2

    def test_suspenseful_zero_shift(self) -> None:
        assert get_register_shift("suspenseful") == 0


class TestGetRhythmOverride:
    """Test get_rhythm_override function."""

    def test_low_straight_override(self) -> None:
        assert get_rhythm_override("low") == "straight"

    def test_stable_no_override(self) -> None:
        assert get_rhythm_override("stable") is None

    def test_moderate_no_override(self) -> None:
        assert get_rhythm_override("moderate") is None

    def test_rising_no_override(self) -> None:
        assert get_rhythm_override("rising") is None

    def test_peak_no_override(self) -> None:
        assert get_rhythm_override("peak") is None

    def test_falling_straight_override(self) -> None:
        assert get_rhythm_override("falling") == "straight"

    def test_resolving_straight_override(self) -> None:
        assert get_rhythm_override("resolving") == "straight"


class TestGetArticulation:
    """Test get_articulation function."""

    def test_low_legato(self) -> None:
        assert get_articulation("low") == "legato"

    def test_stable_no_articulation(self) -> None:
        assert get_articulation("stable") is None

    def test_peak_accent(self) -> None:
        assert get_articulation("peak") == "accent"

    def test_suspenseful_staccato(self) -> None:
        assert get_articulation("suspenseful") == "staccato"

    def test_falling_legato(self) -> None:
        assert get_articulation("falling") == "legato"

    def test_resolving_legato(self) -> None:
        assert get_articulation("resolving") == "legato"
