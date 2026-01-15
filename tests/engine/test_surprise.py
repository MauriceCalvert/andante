"""100% coverage tests for engine.surprise.

Tests import only:
- engine.surprise (module under test)
- stdlib
"""
import pytest
from engine.surprise import (
    SURPRISES,
    get_surprise,
    get_register_shift,
    get_cadence_override,
    get_treatment_override,
    get_rhythm_override,
    get_fill_override,
)


class TestSurprisesData:
    """Test SURPRISES data structure."""

    def test_surprises_has_types(self) -> None:
        assert "types" in SURPRISES
        assert isinstance(SURPRISES["types"], dict)

    def test_all_surprise_types_present(self) -> None:
        types = SURPRISES["types"]
        expected = {
            "deceptive_cadence",
            "evaded_cadence",
            "registral_displacement",
            "subito_piano",
            "subito_forte",
            "sequence_break",
            "hemiola",
        }
        assert set(types.keys()) == expected


class TestGetSurprise:
    """Test get_surprise function."""

    def test_deceptive_cadence(self) -> None:
        surprise = get_surprise("deceptive_cadence")
        assert surprise["category"] == "harmonic"
        assert surprise["cadence_override"] == "deceptive"
        assert surprise["register_shift"] == 0

    def test_registral_displacement(self) -> None:
        surprise = get_surprise("registral_displacement")
        assert surprise["category"] == "melodic"
        assert surprise["register_shift"] == 7

    def test_hemiola(self) -> None:
        surprise = get_surprise("hemiola")
        assert surprise["category"] == "rhythmic"
        assert surprise["rhythm_override"] == "hemiola"

    def test_sequence_break(self) -> None:
        surprise = get_surprise("sequence_break")
        assert surprise["fill_override"] == "sequence_break"

    def test_unknown_surprise_raises(self) -> None:
        with pytest.raises(AssertionError, match="Unknown surprise"):
            get_surprise("nonexistent")

    def test_all_surprises_valid(self) -> None:
        for name in SURPRISES["types"]:
            surprise = get_surprise(name)
            assert isinstance(surprise, dict)
            assert "description" in surprise


class TestGetRegisterShift:
    """Test get_register_shift function."""

    def test_none_returns_zero(self) -> None:
        assert get_register_shift(None) == 0

    def test_deceptive_cadence_zero_shift(self) -> None:
        assert get_register_shift("deceptive_cadence") == 0

    def test_registral_displacement_positive_shift(self) -> None:
        assert get_register_shift("registral_displacement") == 7

    def test_subito_piano_negative_shift(self) -> None:
        assert get_register_shift("subito_piano") == -5

    def test_subito_forte_positive_shift(self) -> None:
        assert get_register_shift("subito_forte") == 5

    def test_evaded_cadence_default_zero(self) -> None:
        assert get_register_shift("evaded_cadence") == 0


class TestGetCadenceOverride:
    """Test get_cadence_override function."""

    def test_none_returns_none(self) -> None:
        assert get_cadence_override(None) is None

    def test_deceptive_cadence_override(self) -> None:
        assert get_cadence_override("deceptive_cadence") == "deceptive"

    def test_evaded_cadence_no_override(self) -> None:
        # evaded_cadence has cadence_override: null in YAML
        assert get_cadence_override("evaded_cadence") is None

    def test_registral_displacement_no_override(self) -> None:
        assert get_cadence_override("registral_displacement") is None

    def test_hemiola_no_override(self) -> None:
        assert get_cadence_override("hemiola") is None


class TestGetTreatmentOverride:
    """Test get_treatment_override function."""

    def test_none_returns_none(self) -> None:
        assert get_treatment_override(None) is None

    def test_deceptive_cadence_no_treatment_override(self) -> None:
        # No treatment_override defined
        assert get_treatment_override("deceptive_cadence") is None

    def test_all_surprises_no_treatment_override(self) -> None:
        # Current data has no treatment_override for any surprise
        for name in SURPRISES["types"]:
            assert get_treatment_override(name) is None


class TestGetRhythmOverride:
    """Test get_rhythm_override function."""

    def test_none_returns_none(self) -> None:
        assert get_rhythm_override(None) is None

    def test_hemiola_rhythm_override(self) -> None:
        assert get_rhythm_override("hemiola") == "hemiola"

    def test_deceptive_cadence_no_rhythm_override(self) -> None:
        assert get_rhythm_override("deceptive_cadence") is None

    def test_registral_displacement_no_rhythm_override(self) -> None:
        assert get_rhythm_override("registral_displacement") is None


class TestGetFillOverride:
    """Test get_fill_override function."""

    def test_none_returns_none(self) -> None:
        assert get_fill_override(None) is None

    def test_sequence_break_fill_override(self) -> None:
        assert get_fill_override("sequence_break") == "sequence_break"

    def test_deceptive_cadence_no_fill_override(self) -> None:
        assert get_fill_override("deceptive_cadence") is None

    def test_hemiola_no_fill_override(self) -> None:
        assert get_fill_override("hemiola") is None
