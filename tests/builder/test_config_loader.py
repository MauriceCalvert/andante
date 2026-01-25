"""Tests for builder.config_loader module.

Category A tests: Pure functions, specification-based.

Tests that config files load correctly and produce valid config objects.
"""
import pytest

from builder.config_loader import (
    _compute_slots_per_bar,
    load_affect,
    load_all_schemas,
    load_configs,
    load_form,
    load_genre,
    load_key,
)
from builder.types import (
    AffectConfig,
    FormConfig,
    GenreConfig,
    KeyConfig,
    MotiveWeights,
    SchemaConfig,
)


class TestLoadGenre:
    """Tests for load_genre function."""

    def test_load_invention(self) -> None:
        genre = load_genre("invention")
        assert genre.name == "invention"
        assert genre.voices == 2
        assert genre.metre == "4/4"
        assert genre.form == "through_composed"

    def test_invention_has_sections(self) -> None:
        genre = load_genre("invention")
        assert len(genre.sections) >= 4
        section_names = [s["name"] for s in genre.sections]
        assert "exordium" in section_names

    def test_missing_genre_raises(self) -> None:
        with pytest.raises(AssertionError):
            load_genre("nonexistent_genre")


class TestLoadAllSchemas:
    """Tests for load_all_schemas function."""

    def test_loads_core_schemas(self) -> None:
        schemas = load_all_schemas()
        assert "do_re_mi" in schemas
        assert "prinner" in schemas
        assert "monte" in schemas
        assert "fonte" in schemas
        assert "cadenza_semplice" in schemas

    def test_do_re_mi_structure(self) -> None:
        schemas = load_all_schemas()
        drm = schemas["do_re_mi"]
        assert drm.soprano_degrees == (1, 2, 3)
        assert drm.bass_degrees == (1, 7, 1)
        assert drm.position == "opening"

    def test_monte_is_sequential(self) -> None:
        schemas = load_all_schemas()
        monte = schemas["monte"]
        assert monte.sequential is True
        assert monte.direction == "ascending"


class TestLoadKey:
    """Tests for load_key function."""

    def test_load_c_major(self) -> None:
        key = load_key("c_major")
        assert key.name == "C Major"
        assert key.pitch_class_set == frozenset({0, 2, 4, 5, 7, 9, 11})

    def test_c_major_bridge_set(self) -> None:
        key = load_key("c_major")
        assert key.bridge_pitch_set == frozenset({0, 2, 4, 7, 9})

    def test_load_g_major(self) -> None:
        key = load_key("g_major")
        assert key.name == "G Major"
        assert key.pitch_class_set == frozenset({7, 9, 11, 0, 2, 4, 6})

    def test_load_a_minor(self) -> None:
        key = load_key("a_minor")
        assert key.name == "A Minor"
        assert key.pitch_class_set == frozenset({9, 11, 0, 2, 4, 5, 7})

    def test_invalid_key_raises(self) -> None:
        with pytest.raises(ValueError):
            load_key("invalid")

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError):
            load_key("c_dorian")


class TestLoadAffect:
    """Tests for load_affect function."""

    def test_load_default(self) -> None:
        affect = load_affect("default")
        assert affect.name == "default"
        assert affect.density == "high"
        assert affect.answer_interval == 7  # Perfect 5th

    def test_default_motive_weights(self) -> None:
        affect = load_affect("default")
        weights = affect.motive_weights
        assert weights.step == 0.2
        assert weights.skip == 0.4
        assert weights.leap == 0.8
        assert weights.large_leap == 1.5

    def test_default_tonal_path(self) -> None:
        affect = load_affect("default")
        assert "narratio" in affect.tonal_path
        assert affect.tonal_path["narratio"] == ("V", "vi", "IV")

    def test_missing_affect_raises(self) -> None:
        with pytest.raises(AssertionError):
            load_affect("nonexistent_affect")


class TestLoadForm:
    """Tests for load_form function."""

    def test_load_through_composed(self) -> None:
        form = load_form("through_composed")
        assert form.name == "through_composed"
        assert form.minimum_bars == 20

    def test_through_composed_bar_allocation(self) -> None:
        form = load_form("through_composed")
        assert "exordium" in form.bar_allocation
        assert form.bar_allocation["exordium"] == (1, 4)

    def test_missing_form_raises(self) -> None:
        with pytest.raises(AssertionError):
            load_form("nonexistent_form")


class TestLoadConfigs:
    """Tests for load_configs combined loader."""

    def test_loads_all_configs(self) -> None:
        config = load_configs("invention", "c_major", "default")
        assert "genre" in config
        assert "key" in config
        assert "affect" in config
        assert "form" in config
        assert "schemas" in config

    def test_config_types_correct(self) -> None:
        config = load_configs("invention", "c_major", "default")
        assert isinstance(config["genre"], GenreConfig)
        assert isinstance(config["key"], KeyConfig)
        assert isinstance(config["affect"], AffectConfig)
        assert isinstance(config["form"], FormConfig)

    def test_computed_fields(self) -> None:
        config = load_configs("invention", "c_major", "default")
        assert "tempo" in config
        assert "total_slots" in config
        # invention: 20 bars * (4/4 metre / 1/16 primary) = 20 * 16 = 320
        assert config["total_slots"] == 20 * 16


class TestComputeSlotsPerBar:
    """Tests for _compute_slots_per_bar helper."""

    def test_4_4_sixteenths(self) -> None:
        """4/4 with 1/16 grid = 16 slots per bar."""
        assert _compute_slots_per_bar("4/4", "1/16") == 16

    def test_3_4_sixteenths(self) -> None:
        """3/4 with 1/16 grid = 12 slots per bar."""
        assert _compute_slots_per_bar("3/4", "1/16") == 12

    def test_6_8_sixteenths(self) -> None:
        """6/8 with 1/16 grid = 12 slots per bar."""
        assert _compute_slots_per_bar("6/8", "1/16") == 12

    def test_4_4_eighths(self) -> None:
        """4/4 with 1/8 grid = 8 slots per bar."""
        assert _compute_slots_per_bar("4/4", "1/8") == 8

    def test_2_4_sixteenths(self) -> None:
        """2/4 with 1/16 grid = 8 slots per bar."""
        assert _compute_slots_per_bar("2/4", "1/16") == 8
