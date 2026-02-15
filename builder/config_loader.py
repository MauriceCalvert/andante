"""Configuration loader for YAML files.

Category B: Orchestrator with file I/O.
Loads from data/ directory (single source of truth per L017):
- data/genres/*.yaml
- data/schemas/schemas.yaml
- data/rhetoric/affects.yaml
- data/forms/*.yaml

Keys are computed from (tonic, mode) parameters, not loaded from YAML.
"""
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from builder.types import (
    AffectConfig, FormConfig, GenreConfig,
    KeyConfig, MotiveWeights,
)
from shared.key import Key
from shared.schema_types import Schema


DATA_DIR: Path = Path(__file__).parent.parent / "data"


def load_genre(name: str) -> GenreConfig:
    """Load genre configuration from data/genres/."""
    path: Path = DATA_DIR / "genres" / f"{name}.yaml"
    assert path.exists(), f"Genre not found: {path}"
    data: dict = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _validate_genre(data=data)


def load_all_schemas() -> dict[str, Schema]:
    """Load all schema definitions. Delegates to planner/schema_loader (L017)."""
    from planner.schema_loader import load_schemas as _load_schemas
    return _load_schemas()


def load_schemas() -> dict[str, Schema]:
    """Alias for load_all_schemas."""
    return load_all_schemas()


def load_key(name: str) -> KeyConfig:
    """Create key configuration from key name (e.g., 'c_major', 'g_minor')."""
    tonic, mode = _parse_key_name(name=name)
    key: Key = Key(tonic=tonic, mode=mode)
    return KeyConfig(
        name=f"{tonic} {mode.capitalize()}",
        pitch_class_set=key.pitch_class_set,
        bridge_pitch_set=key.bridge_pitch_set,
    )


def _parse_key_name(name: str) -> tuple[str, str]:
    """Parse key name like 'c_major' into (tonic, mode)."""
    name = name.lower().replace(" ", "_")
    if "_" not in name:
        raise ValueError(f"Invalid key name '{name}': expected format 'tonic_mode' (e.g., 'c_major')")
    parts: list[str] = name.split("_")
    tonic_raw: str = parts[0]
    mode: str = parts[1]
    tonic_map: dict[str, str] = {
        "c": "C", "d": "D", "e": "E", "f": "F", "g": "G", "a": "A", "b": "B",
        "cb": "Cb", "db": "Db", "eb": "Eb", "fb": "Fb", "gb": "Gb", "ab": "Ab", "bb": "Bb",
        "c#": "C#", "d#": "D#", "e#": "E#", "f#": "F#", "g#": "G#", "a#": "A#", "b#": "B#",
    }
    tonic: str = tonic_map.get(tonic_raw, tonic_raw.capitalize())
    if mode not in ("major", "minor"):
        raise ValueError(f"Invalid mode '{mode}': expected 'major' or 'minor'")
    return tonic, mode


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning new dict."""
    result: dict = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(base=result[key], override=value)
        else:
            result[key] = value
    return result


def load_affect(name: str) -> AffectConfig:
    """Load affect configuration, merging with default."""
    path: Path = DATA_DIR / "rhetoric" / "affects.yaml"
    assert path.exists(), f"Affects file not found: {path}"
    data: dict = yaml.safe_load(path.read_text(encoding="utf-8"))
    all_affects: dict = data.get("affects", {})
    # Start with default
    assert "default" in all_affects, "affects.yaml must have 'default' entry in 'affects' section"
    base_data: dict = dict(all_affects["default"])
    # Case-insensitive lookup for requested affect
    name_lower: str = name.lower()
    if name_lower != "default":
        canonical_name: str | None = None
        for key in all_affects:
            if key.lower() == name_lower:
                canonical_name = key
                break
        assert canonical_name is not None, f"Affect '{name}' not found in {path}. Available: {list(all_affects.keys())}"
        override_data: dict = all_affects[canonical_name]
        data: dict = _deep_merge(base=base_data, override=override_data)
        data["name"] = canonical_name
    else:
        data = base_data
        data["name"] = "default"
    return _validate_affect(data=data)


def load_form(name: str) -> FormConfig:
    """Load form template from data/forms/."""
    path: Path = DATA_DIR / "forms" / f"{name}.yaml"
    assert path.exists(), f"Form not found: {path}"
    data: dict = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _validate_form(data=data)


def _compute_slots_per_bar(metre: str, rhythmic_unit: str) -> int:
    """Compute slots per bar from metre and primary value."""
    num_str, den_str = metre.split("/")
    bar_length: Fraction = Fraction(int(num_str), int(den_str))
    slot_size: Fraction = Fraction(rhythmic_unit)
    slots: Fraction = bar_length / slot_size
    assert slots.denominator == 1, f"Non-integer slots: {metre} / {rhythmic_unit} = {slots}"
    return int(slots)


def _compute_total_bars(
    genre_config: GenreConfig,
    schemas: dict[str, Schema],
) -> int:
    """Compute total bars from schema stages in all sections."""
    from builder.cadence_writer import get_schema_bars
    total: int = 0
    for section in genre_config.sections:
        schema_sequence: list[str] = section.get("schema_sequence", [])
        for name in schema_sequence:
            if name not in schemas:
                continue
            total += get_schema_bars(
                schema_name=name,
                schema_def=schemas[name],
                metre=genre_config.metre,
            )
    return total


def load_configs(genre: str, key: str, affect: str) -> dict[str, Any]:
    """Load all required configurations."""
    genre_config: GenreConfig = load_genre(name=genre)
    key_config: KeyConfig = load_key(name=key)
    affect_config: AffectConfig = load_affect(name=affect)
    form_config: FormConfig = load_form(name=genre_config.form)
    schemas: dict[str, Schema] = load_all_schemas()
    total_bars: int = _compute_total_bars(genre_config=genre_config, schemas=schemas)
    slots_per_bar: int = _compute_slots_per_bar(metre=genre_config.metre, rhythmic_unit=genre_config.rhythmic_unit)
    total_slots: int = total_bars * slots_per_bar
    return {
        "genre": genre_config,
        "key": key_config,
        "affect": affect_config,
        "form": form_config,
        "schemas": schemas,
        "total_bars": total_bars,
        "total_slots": total_slots,
    }


def _validate_genre(data: dict) -> GenreConfig:
    """Validate genre YAML against schema."""
    from builder.figuration.bass import validate_bass_treatment
    genre_name: str = data.get("name", "<unknown>")
    assert "tempo" in data, f"Genre '{genre_name}' missing 'tempo'"
    sections: list[dict] = data.get("sections", [])
    for section in sections:
        section_name: str = section.get("name", "<unnamed>")
        assert "schema_sequence" in section, f"Section '{section_name}' missing 'schema_sequence'"
        assert len(section["schema_sequence"]) > 0, f"Section '{section_name}' has empty schema_sequence"
    bass_treatment: str | None = data.get("bass_treatment")
    bass_mode: str = data.get("bass_mode", "pattern")
    bass_pattern: str | None = data.get("bass_pattern")
    validate_bass_treatment(bass_treatment=bass_treatment, bass_mode=bass_mode, bass_pattern=bass_pattern, genre_name=genre_name)
    upbeat_raw = data.get("upbeat", 0)
    upbeat = Fraction(upbeat_raw) if isinstance(upbeat_raw, str) else Fraction(upbeat_raw)
    tension: str | None = data.get("tension")
    composition_model: str = data.get("composition_model", "galant")
    assert composition_model in ("galant", "imitative"), (
        f"Genre '{genre_name}': composition_model must be 'galant' or 'imitative', "
        f"got '{composition_model}'"
    )
    return GenreConfig(
        name=genre_name,
        voices=data["voices"],
        form=data["form"],
        metre=data["metre"],
        rhythmic_unit=data["rhythmic_unit"],
        tempo=data["tempo"],
        bass_treatment=bass_treatment,
        bass_mode=bass_mode,
        bass_pattern=bass_pattern,
        composition_model=composition_model,
        sections=tuple(data.get("sections", [])),
        tension=tension,
        upbeat=upbeat,
    )


def _validate_affect(data: dict) -> AffectConfig:
    """Validate affect YAML against schema."""
    mw: dict = data.get("motive_weights", {})
    tonal_path_raw: dict = data.get("tonal_path", {})
    tonal_path: dict[str, tuple[str, ...]] = {}
    for section, areas in tonal_path_raw.items():
        tonal_path[section] = tuple(areas)
    return AffectConfig(
        name=data["name"],
        density=data.get("density", "medium"),
        articulation=data.get("articulation", "normal"),
        tempo_modifier=data.get("tempo_modifier", 0),
        tonal_path=tonal_path,
        answer_interval=data.get("answer_interval", 5),
        anacrusis=data.get("anacrusis", False),
        motive_weights=MotiveWeights(
            step=mw.get("step", 0.2),
            skip=mw.get("skip", 0.4),
            leap=mw.get("leap", 0.8),
            large_leap=mw.get("large_leap", 1.5),
        ),
        direction_limit=data.get("direction_limit", 4),
        density_minimum=data.get("density_minimum", 0.5),
        rhythm_states=data.get("rhythm_states", {}),
    )


def _validate_form(data: dict) -> FormConfig:
    """Validate form YAML against schema."""
    return FormConfig(name=data["name"])
