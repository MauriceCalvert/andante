"""Load and query schema definitions from YAML.

Schemas are partimento-style harmonic blueprints that encode bass degrees,
soprano degrees, and durations. The transition graph defines valid schema
sequences based on Gjerdingen (2007) and Rabinovitch & Carter-Enyi (2024).
"""
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


DATA_DIR: Path = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class Schema:
    """Loaded schema definition from schemas.yaml."""
    name: str
    bass_degrees: tuple[int, ...]
    soprano_degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    bars: int
    opening: bool
    cadence_approach: bool
    sequential: bool
    direction: str | None  # ascending, descending for sequential schemas


@dataclass(frozen=True)
class SchemaTransition:
    """Transition rules for a schema from schema_transitions.yaml."""
    name: str
    typical_position: str  # opening, riposte, continuation, pre_cadential, cadential
    allowed_next: tuple[str, ...]


def _load_yaml(name: str) -> dict[str, Any]:
    """Load YAML file from data directory."""
    path = DATA_DIR / name
    assert path.exists(), f"YAML file not found: {path}"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_degree(value: int | dict[str, Any]) -> int:
    """Parse a degree value which may be plain int or dict with alterations.

    Examples:
        5 -> 5
        {degree: 4, alter: 1} -> 4 (alteration tracked separately if needed)
    """
    if isinstance(value, int):
        return value
    assert isinstance(value, dict), f"Degree must be int or dict, got {type(value)}"
    return value["degree"]


def _parse_duration(value: str | int | float) -> Fraction:
    """Parse duration value from YAML."""
    if isinstance(value, str):
        return Fraction(value)
    return Fraction(value)


def _parse_schema(name: str, data: dict[str, Any]) -> Schema:
    """Parse a single schema entry from YAML."""
    bass_degrees = tuple(_parse_degree(d) for d in data["bass_degrees"])
    soprano_degrees = tuple(_parse_degree(d) for d in data["soprano_degrees"])
    durations = tuple(_parse_duration(d) for d in data["durations"])
    bars = data.get("bars", 1)

    return Schema(
        name=name,
        bass_degrees=bass_degrees,
        soprano_degrees=soprano_degrees,
        durations=durations,
        bars=bars,
        opening=data.get("opening", False),
        cadence_approach=data.get("cadence_approach", False),
        sequential=data.get("sequential", False),
        direction=data.get("direction"),
    )


def _parse_transition(name: str, data: dict[str, Any]) -> SchemaTransition:
    """Parse a single transition entry from YAML."""
    return SchemaTransition(
        name=name,
        typical_position=data.get("typical_position", "continuation"),
        allowed_next=tuple(data.get("allowed_next", [])),
    )


@lru_cache(maxsize=1)
def load_schemas() -> dict[str, Schema]:
    """Load all schemas from data/schemas.yaml.

    Returns:
        Dict mapping schema name to Schema dataclass.
    """
    raw = _load_yaml("schemas.yaml")
    schemas: dict[str, Schema] = {}

    for name, data in raw.items():
        # Skip non-schema entries (comments, metadata)
        if not isinstance(data, dict) or "bass_degrees" not in data:
            continue
        schemas[name] = _parse_schema(name, data)

    return schemas


@lru_cache(maxsize=1)
def load_transitions() -> dict[str, SchemaTransition]:
    """Load transition rules from data/schema_transitions.yaml.

    Returns:
        Dict mapping schema name to SchemaTransition with allowed_next.
    """
    raw = _load_yaml("schema_transitions.yaml")
    transitions: dict[str, SchemaTransition] = {}

    for name, data in raw.items():
        # Skip non-schema entries (metadata sections like typical_exposition_stages)
        if not isinstance(data, dict) or "allowed_next" not in data:
            continue
        transitions[name] = _parse_transition(name, data)

    return transitions


def get_schema(name: str) -> Schema:
    """Get a single schema by name.

    Raises:
        AssertionError: If schema not found.
    """
    schemas = load_schemas()
    assert name in schemas, f"Unknown schema: {name}. Available: {sorted(schemas.keys())}"
    return schemas[name]


def get_opening_schemas() -> list[str]:
    """Return schema names valid for opening a section.

    Based on 'opening: true' in schemas.yaml.
    """
    schemas = load_schemas()
    return [name for name, schema in schemas.items() if schema.opening]


def get_cadential_schemas() -> list[str]:
    """Return schema names suitable for approaching cadences.

    Based on 'cadence_approach: true' in schemas.yaml.
    """
    schemas = load_schemas()
    return [name for name, schema in schemas.items() if schema.cadence_approach]


def get_sequential_schemas() -> list[str]:
    """Return schema names for continuation/sequence.

    Based on 'sequential: true' in schemas.yaml.
    """
    schemas = load_schemas()
    return [name for name, schema in schemas.items() if schema.sequential]


def get_allowed_next(schema_name: str) -> list[str]:
    """Return valid successor schemas from transition graph.

    Args:
        schema_name: Current schema name.

    Returns:
        List of schema names that can follow the current schema.
    """
    transitions = load_transitions()
    if schema_name not in transitions:
        # Schema not in transition graph - allow all openings as fallback
        return get_opening_schemas()
    return list(transitions[schema_name].allowed_next)


def get_typical_position(schema_name: str) -> str:
    """Get the typical formal position for a schema.

    Returns:
        Position string: opening, riposte, continuation, pre_cadential, cadential
    """
    transitions = load_transitions()
    if schema_name not in transitions:
        return "continuation"  # default
    return transitions[schema_name].typical_position


def schema_fits_bars(schema_name: str, target_bars: int) -> bool:
    """Check if schema can be stretched to fit target bars.

    Stretching works by multiplying all durations by (target_bars / base_bars).
    Any positive integer multiple of base_bars is valid.

    Args:
        schema_name: Name of schema to check.
        target_bars: Desired bar count.

    Returns:
        True if schema can be stretched to target_bars.
    """
    schema = get_schema(schema_name)
    # Any positive integer multiple works
    return target_bars >= schema.bars and target_bars % schema.bars == 0


def stretch_durations(schema_name: str, target_bars: int) -> tuple[Fraction, ...]:
    """Stretch schema durations to fit target bars.

    Formula: actual_duration[i] = base_durations[i] * (target_bars / base_bars)

    Args:
        schema_name: Name of schema.
        target_bars: Desired bar count.

    Returns:
        Tuple of stretched durations.
    """
    schema = get_schema(schema_name)
    assert schema_fits_bars(schema_name, target_bars), (
        f"Schema {schema_name} (base {schema.bars} bars) cannot stretch to {target_bars} bars"
    )
    multiplier = Fraction(target_bars, schema.bars)
    return tuple(d * multiplier for d in schema.durations)
