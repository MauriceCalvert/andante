"""Configuration loader for YAML files.

Category B: Orchestrator with file I/O.
Loads from data/ directory (single source of truth per L017):
- data/genres/*.yaml
- data/schemas/schemas.yaml
- data/rhetoric/affects.yaml
- data/forms/*.yaml

Keys are computed from (tonic, mode) parameters, not loaded from YAML.
"""
import re
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from builder.types import (
    AffectConfig, FormConfig, GenreConfig,
    KeyConfig, MotiveWeights, SchemaConfig,
)
from shared.key import Key


DATA_DIR: Path = Path(__file__).parent.parent / "data"
_genre_cache: dict[str, dict] = {}


def load_genre_raw(name: str) -> dict:
    """Load genre YAML as raw dict (cached).

    Use this for simple field access without validation.
    For typed access, use load_genre() instead.
    """
    if name in _genre_cache:
        return _genre_cache[name]
    path: Path = DATA_DIR / "genres" / f"{name}.yaml"
    if path.exists():
        data: dict = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        data = {}
    _genre_cache[name] = data
    return data


def clear_genre_cache() -> None:
    """Clear genre cache. Used in tests."""
    _genre_cache.clear()


def _parse_typical_keys(raw: str | None) -> tuple[str, ...] | None:
    """Parse typical_keys string into tuple of key areas.
    
    Examples:
        "IV -> V (-> vi)" -> ("IV", "V", "vi")
        "ii -> I" -> ("ii", "I")
        None -> None
    """
    if raw is None:
        return None
    pattern = r'[iIvV]+|[iI]{1,3}|[vV]{1,3}'
    matches: list[str] = re.findall(pattern, raw)
    if not matches:
        return None
    return tuple(matches)


def load_genre(name: str) -> GenreConfig:
    """Load genre configuration from data/genres/."""
    path: Path = DATA_DIR / "genres" / f"{name}.yaml"
    assert path.exists(), f"Genre not found: {path}"
    data: dict = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _validate_genre(data=data)


def load_all_schemas() -> dict[str, SchemaConfig]:
    """Load all schema definitions from data/schemas/schemas.yaml (authoritative source)."""
    path: Path = DATA_DIR / "schemas" / "schemas.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Schema config not found: {path}")
    data: dict = yaml.safe_load(path.read_text(encoding="utf-8"))
    result: dict[str, SchemaConfig] = {}
    for name, schema_data in data.items():
        if not isinstance(schema_data, dict):
            continue
        if "soprano_degrees" not in schema_data and "segment" not in schema_data:
            continue
        schema: SchemaConfig | None = _validate_schema(name=name, data=schema_data)
        if schema is not None:
            result[name] = schema
    return result


def load_schemas() -> dict[str, SchemaConfig]:
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


def _get_schema_stages(schema_name: str, schemas: dict[str, SchemaConfig]) -> int:
    """Get number of bars a schema occupies."""
    if schema_name not in schemas:
        return 0
    schema_def: SchemaConfig = schemas[schema_name]
    if schema_def.sequential:
        return max(schema_def.segments) if schema_def.segments else 2
    return len(schema_def.soprano_degrees)


def _compute_total_bars(
    genre_config: GenreConfig,
    schemas: dict[str, SchemaConfig],
) -> int:
    """Compute total bars from schema stages in all sections."""
    total: int = 0
    for section in genre_config.sections:
        schema_sequence: list[str] = section.get("schema_sequence", [])
        for name in schema_sequence:
            total += _get_schema_stages(schema_name=name, schemas=schemas)
    return total


def load_configs(genre: str, key: str, affect: str) -> dict[str, Any]:
    """Load all required configurations."""
    genre_config: GenreConfig = load_genre(name=genre)
    key_config: KeyConfig = load_key(name=key)
    affect_config: AffectConfig = load_affect(name=affect)
    form_config: FormConfig = load_form(name=genre_config.form)
    schemas: dict[str, SchemaConfig] = load_all_schemas()
    tempo: int = genre_config.tempo + affect_config.tempo_modifier
    total_bars: int = _compute_total_bars(genre_config=genre_config, schemas=schemas)
    slots_per_bar: int = _compute_slots_per_bar(metre=genre_config.metre, rhythmic_unit=genre_config.rhythmic_unit)
    total_slots: int = total_bars * slots_per_bar
    return {
        "genre": genre_config,
        "key": key_config,
        "affect": affect_config,
        "form": form_config,
        "schemas": schemas,
        "tempo": tempo,
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
        sections=tuple(data.get("sections", [])),
        upbeat=upbeat,
    )


VALID_DIRECTIONS: frozenset[str] = frozenset({"up", "down", "same"})


def _parse_signed_degree(raw: str | int | float, is_first: bool) -> tuple[int, str | None]:
    """Parse a signed degree string into (degree, direction).
    
    Format:
        First degree: unsigned (starting point), direction=None
        Subsequent: -N = down to N, N = same, +N = up to N
    
    Args:
        raw: Degree value as string ("+2", "-7", "1") or number.
        is_first: True if this is the first degree (no direction).
    
    Returns:
        (degree, direction) where degree is 1-7 and direction is up/down/same/None.
    """
    if isinstance(raw, (int, float)):
        # Numeric value - treat as unsigned
        degree = int(abs(raw))
        direction = None if is_first else "same"
        return degree, direction
    # String value
    raw_str = str(raw).strip()
    if not raw_str:
        return 1, None
    if raw_str.startswith("+"):
        degree_str = raw_str[1:]
        direction = None if is_first else "up"
    elif raw_str.startswith("-"):
        degree_str = raw_str[1:]
        direction = None if is_first else "down"
    else:
        degree_str = raw_str
        direction = None if is_first else "same"
    # Handle chromatic (e.g., "4.5" for raised 4)
    degree = int(float(degree_str))
    return degree, direction


def _parse_signed_degrees(raw_list: list) -> tuple[tuple[int, ...], tuple[str | None, ...]]:
    """Parse a list of signed degrees into degrees and directions.
    
    Args:
        raw_list: List of signed degree values.
    
    Returns:
        (degrees, directions) tuples.
    """
    degrees: list[int] = []
    directions: list[str | None] = []
    for i, raw in enumerate(raw_list):
        degree, direction = _parse_signed_degree(raw=raw, is_first=(i == 0))
        degrees.append(degree)
        directions.append(direction)
    return tuple(degrees), tuple(directions)


def _validate_schema(name: str, data: dict) -> SchemaConfig:
    """Validate schema YAML against schema."""
    if not isinstance(data, dict):
        # Skip non-dict entries (comments, etc.)
        return None
    bars: list = data.get("bars", [1, 2])
    segments: Any = data.get("segments", [1])
    if isinstance(segments, int):
        segments = [segments]
    # Handle sequential schemas with segment sub-structure
    if "segment" in data:
        segment: dict = data["segment"]
        raw_soprano = segment.get("soprano_degrees", [])
        raw_bass = segment.get("bass_degrees", [])
    else:
        raw_soprano = data.get("soprano_degrees", [])
        raw_bass = data.get("bass_degrees", [])
    soprano_degrees, soprano_directions = _parse_signed_degrees(raw_list=raw_soprano)
    bass_degrees, bass_directions = _parse_signed_degrees(raw_list=raw_bass)
    typical_keys: tuple[str, ...] | None = _parse_typical_keys(raw=data.get("typical_keys"))
    # Derive entry/exit from first/last degrees (single source of truth)
    entry_soprano: int = soprano_degrees[0] if soprano_degrees else 1
    entry_bass: int = bass_degrees[0] if bass_degrees else 1
    exit_soprano: int = soprano_degrees[-1] if soprano_degrees else 1
    exit_bass: int = bass_degrees[-1] if bass_degrees else 1
    return SchemaConfig(
        name=name,
        soprano_degrees=soprano_degrees,
        soprano_directions=soprano_directions,
        bass_degrees=bass_degrees,
        bass_directions=bass_directions,
        entry_soprano=entry_soprano,
        entry_bass=entry_bass,
        exit_soprano=exit_soprano,
        exit_bass=exit_bass,
        bars_min=bars[0],
        bars_max=bars[1] if len(bars) > 1 else bars[0],
        position=data.get("position", "continuation"),
        cadential_state=data.get("cadential_state", "open"),
        sequential=data.get("sequential", False),
        segments=tuple(segments),
        direction=data.get("direction"),
        segment_direction=data.get("segment_direction"),
        typical_keys=typical_keys,
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
