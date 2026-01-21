"""Tests for builder.config_loader module.

Category A tests: Pure functions, specification-based.

Tests that config files load correctly and produce valid config objects.
"""
import pytest

from builder.config_loader import (
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
        with pytest.raises(FileNotFoundError):
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

    def test_c_major_registers(self) -> None:
        key = load_key("c_major")
        assert key.registers["soprano"] == (59, 79)  # Extended for leading tone
        assert key.registers["bass"] == (36, 60)

    def test_c_major_has_arrivals(self) -> None:
        key = load_key("c_major")
        assert "confident" in key.arrivals
        arrivals = key.arrivals["confident"]
        assert len(arrivals) > 0

    def test_missing_key_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_key("nonexistent_key")


class TestLoadAffect:
    """Tests for load_affect function."""

    def test_load_confident(self) -> None:
        affect = load_affect("confident")
        assert affect.name == "confident"
        assert affect.density == "high"
        assert affect.answer_interval == 5

    def test_confident_motive_weights(self) -> None:
        affect = load_affect("confident")
        weights = affect.motive_weights
        assert weights.step == 0.2
        assert weights.skip == 0.4
        assert weights.leap == 0.8
        assert weights.large_leap == 1.5

    def test_confident_tonal_path(self) -> None:
        affect = load_affect("confident")
        assert "narratio" in affect.tonal_path
        assert affect.tonal_path["narratio"] == ("I", "V", "vi")

    def test_missing_affect_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
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
        with pytest.raises(FileNotFoundError):
            load_form("nonexistent_form")


class TestLoadConfigs:
    """Tests for load_configs combined loader."""

    def test_loads_all_configs(self) -> None:
        config = load_configs("invention", "c_major", "confident")
        assert "genre" in config
        assert "key" in config
        assert "affect" in config
        assert "form" in config
        assert "schemas" in config

    def test_config_types_correct(self) -> None:
        config = load_configs("invention", "c_major", "confident")
        assert isinstance(config["genre"], GenreConfig)
        assert isinstance(config["key"], KeyConfig)
        assert isinstance(config["affect"], AffectConfig)
        assert isinstance(config["form"], FormConfig)

    def test_computed_fields(self) -> None:
        config = load_configs("invention", "c_major", "confident")
        assert "tempo" in config
        assert "total_slots" in config
        assert config["total_slots"] == 20 * 16
