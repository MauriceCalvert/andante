"""Load and query schema definitions from YAML.

Schemas are galante harmonic blueprints encoding soprano/bass degrees at each
stage. Format conforms to architecture.md and schemas.yaml.
"""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


DATA_DIR: Path = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class Arrival:
    """Entry or exit point: soprano and bass degree."""
    soprano: int
    bass: int


@dataclass(frozen=True)
class Schema:
    """Schema definition from schemas.yaml."""
    name: str
    soprano_degrees: tuple[int, ...]
    bass_degrees: tuple[int, ...]
    entry: Arrival
    exit: Arrival
    min_bars: int
    max_bars: int
    position: str  # opening, riposte, continuation, pre_cadential, cadential, post_cadential
    sequential: bool
    direction: str | None  # ascending, descending for sequential schemas
    segments: int  # number of segments for sequential schemas
    pedal: str | None  # dominant, tonic, subdominant
    chromatic: bool  # has chromatic alterations
    figuration_profile: str  # figuration profile name from figuration_profiles.yaml
    cadence_approach: bool  # whether final connection uses cadential patterns

    @property
    def stage_count(self) -> int:
        """Number of stages. For sequential, multiply by segments."""
        base = len(self.soprano_degrees)
        if self.sequential:
            return base * self.segments
        return base


def _load_yaml(name: str) -> dict[str, Any]:
    """Load YAML file from data directory."""
    path = DATA_DIR / name
    assert path.exists(), f"YAML file not found: {path}"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_degree(value: int | float) -> int:
    """Parse degree, handling float encoding for chromatic (e.g., 4.5 = #4)."""
    if isinstance(value, float):
        return int(value)  # 4.5 -> 4; chromatic flag handles alteration
    return value


def _parse_arrival(data: dict[str, Any]) -> Arrival:
    """Parse entry/exit dict to Arrival."""
    return Arrival(soprano=data["soprano"], bass=data["bass"])


def _parse_bars(data: Any) -> tuple[int, int]:
    """Parse bars field which may be [min, max] or single int."""
    if isinstance(data, list):
        return (data[0], data[1])
    return (data, data)


def _parse_segments(data: Any) -> int:
    """Parse segments field which may be int or list."""
    if isinstance(data, list):
        return data[0]  # Use minimum
    if isinstance(data, int):
        return data
    return 1


def _parse_schema(name: str, data: dict[str, Any]) -> Schema:
    """Parse a single schema entry from YAML."""
    # Handle sequential schemas with segment sub-structure
    if "segment" in data:
        soprano_degrees = tuple(_parse_degree(d) for d in data["segment"]["soprano_degrees"])
        bass_degrees = tuple(_parse_degree(d) for d in data["segment"]["bass_degrees"])
    else:
        soprano_degrees = tuple(_parse_degree(d) for d in data["soprano_degrees"])
        bass_degrees = tuple(_parse_degree(d) for d in data["bass_degrees"])
    min_bars, max_bars = _parse_bars(data["bars"])
    return Schema(
        name=name,
        soprano_degrees=soprano_degrees,
        bass_degrees=bass_degrees,
        entry=_parse_arrival(data["entry"]),
        exit=_parse_arrival(data["exit"]),
        min_bars=min_bars,
        max_bars=max_bars,
        position=data.get("position", "continuation"),
        sequential=data.get("sequential", False),
        direction=data.get("direction"),
        segments=_parse_segments(data.get("segments", 1)),
        pedal=data.get("pedal"),
        chromatic=data.get("chromatic", False),
        figuration_profile=data.get("figuration_profile", "galant_general"),
        cadence_approach=data.get("cadence_approach", False),
    )


@lru_cache(maxsize=1)
def load_schemas() -> dict[str, Schema]:
    """Load all schemas from data/schemas/schemas.yaml."""
    raw = _load_yaml("schemas/schemas.yaml")
    schemas: dict[str, Schema] = {}
    for name, data in raw.items():
        if not isinstance(data, dict):
            continue
        if "soprano_degrees" not in data and "segment" not in data:
            continue
        schemas[name] = _parse_schema(name, data)
    return schemas


def get_schema(name: str) -> Schema:
    """Get a single schema by name."""
    schemas = load_schemas()
    assert name in schemas, f"Unknown schema: {name}. Available: {sorted(schemas.keys())}"
    return schemas[name]


def get_schemas_by_position(position: str) -> list[str]:
    """Return schema names for a given position."""
    schemas = load_schemas()
    return [name for name, s in schemas.items() if s.position == position]


def get_opening_schemas() -> list[str]:
    """Return schema names valid for opening."""
    return get_schemas_by_position("opening")


def get_riposte_schemas() -> list[str]:
    """Return schema names valid for riposte."""
    return get_schemas_by_position("riposte")


def get_continuation_schemas() -> list[str]:
    """Return schema names valid for continuation."""
    return get_schemas_by_position("continuation")


def get_pre_cadential_schemas() -> list[str]:
    """Return schema names valid for pre-cadential."""
    return get_schemas_by_position("pre_cadential")


def get_cadential_schemas() -> list[str]:
    """Return schema names valid for cadence."""
    return get_schemas_by_position("cadential")


def get_sequential_schemas() -> list[str]:
    """Return sequential schema names (Monte, Fonte)."""
    schemas = load_schemas()
    return [name for name, s in schemas.items() if s.sequential]


def get_typical_position(schema_name: str) -> str:
    """Get the typical formal position for a schema."""
    schema = get_schema(schema_name)
    return schema.position


def schema_fits_bars(schema_name: str, available_bars: int) -> bool:
    """Check if schema can fit within available bars.

    A schema fits if its min_bars <= available_bars.
    The schema will use between min_bars and min(max_bars, available_bars).
    """
    schema = get_schema(schema_name)
    return schema.min_bars <= available_bars


def can_connect_direct(from_schema: str, to_schema: str) -> bool:
    """Check if two schemas can connect directly (no free passage).

    Direct connection requires one of:
    1. Identity: exit.bass == entry.bass
    2. Step: |exit.bass - entry.bass| == 1
    3. Dominant resolution: exit.bass == 5 and entry.bass == 1
    """
    from_s = get_schema(from_schema)
    to_s = get_schema(to_schema)
    exit_bass = from_s.exit.bass
    entry_bass = to_s.entry.bass
    if exit_bass == entry_bass:
        return True
    if abs(exit_bass - entry_bass) == 1:
        return True
    if exit_bass == 5 and entry_bass == 1:
        return True
    return False


def get_allowed_next(schema_name: str) -> list[str]:
    """Return valid successor schemas based on connection rules.

    Uses bass degree connection rules from architecture.md:
    1. Identity: exit.bass == entry.bass
    2. Step: |exit.bass - entry.bass| == 1
    3. Dominant: exit.bass == 5 and entry.bass == 1

    Returns all schemas that can connect, or all schemas if none connect.
    """
    schemas = load_schemas()
    from_schema = get_schema(schema_name)
    exit_bass = from_schema.exit.bass
    allowed: list[str] = []
    for name, to_schema in schemas.items():
        entry_bass = to_schema.entry.bass
        if exit_bass == entry_bass:
            allowed.append(name)
        elif abs(exit_bass - entry_bass) == 1:
            allowed.append(name)
        elif exit_bass == 5 and entry_bass == 1:
            allowed.append(name)
    return allowed if allowed else list(schemas.keys())


def get_schema_figuration_profile(schema_name: str) -> str:
    """Get figuration profile name for a schema."""
    schema = get_schema(schema_name)
    return schema.figuration_profile


def get_schema_profiles() -> dict[str, str]:
    """Get mapping of all schema names to their figuration profiles."""
    schemas = load_schemas()
    return {name: s.figuration_profile for name, s in schemas.items()}


def get_arrival_beats(schema_name: str, bars: int, metre: tuple[int, int] = (4, 4)) -> list[float]:
    """Calculate arrival beat positions for a schema.

    Arrivals fall on strong beats, distributed evenly.
    In 4/4: beats 1 and 3 are strong.
    In 3/4: beat 1 is strong.

    Args:
        schema_name: Name of schema.
        bars: Number of bars allocated.
        metre: Time signature as (numerator, denominator).

    Returns:
        List of beat positions as bar.beat (e.g., 1.1, 1.3, 2.1).
    """
    schema = get_schema(schema_name)
    num_arrivals = schema.stage_count
    if metre[0] == 4:
        strong_beats = [1, 3]
    elif metre[0] == 3:
        strong_beats = [1]
    else:
        strong_beats = [1]
    positions: list[float] = []
    for bar in range(1, bars + 1):
        for beat in strong_beats:
            if len(positions) < num_arrivals:
                positions.append(float(f"{bar}.{beat}"))
    # If still need arrivals, use beat 4 of last bar for cadential
    while len(positions) < num_arrivals:
        positions.append(float(f"{bars}.4"))
    return positions[:num_arrivals]
