"""Load and query schema definitions from YAML.

Schemas are galante harmonic blueprints encoding soprano/bass degrees at each
stage. Format conforms to architecture.md and schemas.yaml.
"""
import re
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
    soprano_directions: tuple[str | None, ...]  # up/down/same/None per degree
    bass_degrees: tuple[int, ...]
    bass_directions: tuple[str | None, ...]  # up/down/same/None per degree
    entry: Arrival  # derived from first degrees
    exit: Arrival  # derived from last degrees
    min_bars: int
    max_bars: int
    position: str  # opening, riposte, continuation, pre_cadential, cadential, post_cadential
    sequential: bool
    direction: str | None  # ascending, descending for sequential schemas
    segment_direction: str | None  # up/down between segments for sequential schemas
    segments: int  # number of segments for sequential schemas
    pedal: str | None  # dominant, tonic, subdominant
    chromatic: bool  # has chromatic alterations
    figuration_profile: str  # figuration profile name from figuration_profiles.yaml
    cadence_approach: bool  # whether final connection uses cadential patterns
    typical_keys: tuple[str, ...] | None  # key journey for sequential schemas

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


@lru_cache(maxsize=1)
def _load_transitions() -> dict[str, Any]:
    """Load schema transitions YAML (cached)."""
    return _load_yaml(name="schemas/schema_transitions.yaml")


def _parse_signed_degree(raw: str | int | float, is_first: bool) -> tuple[int, str | None]:
    """Parse a signed degree string into (degree, direction).
    
    Format:
        First degree: unsigned (starting point), direction=None
        Subsequent: -N = down to N, N = same, +N = up to N
    """
    if isinstance(raw, (int, float)):
        degree = int(abs(raw))
        direction = None if is_first else "same"
        return degree, direction
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
    degree = int(float(degree_str))
    return degree, direction


def _parse_signed_degrees(raw_list: list) -> tuple[tuple[int, ...], tuple[str | None, ...]]:
    """Parse a list of signed degrees into degrees and directions."""
    degrees: list[int] = []
    directions: list[str | None] = []
    for i, raw in enumerate(raw_list):
        degree, direction = _parse_signed_degree(raw=raw, is_first=(i == 0))
        degrees.append(degree)
        directions.append(direction)
    return tuple(degrees), tuple(directions)


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


def _parse_schema(name: str, data: dict[str, Any]) -> Schema:
    """Parse a single schema entry from YAML."""
    # Handle sequential schemas with segment sub-structure
    if "segment" in data:
        segment = data["segment"]
        raw_soprano = segment.get("soprano_degrees", [])
        raw_bass = segment.get("bass_degrees", [])
    else:
        raw_soprano = data.get("soprano_degrees", [])
        raw_bass = data.get("bass_degrees", [])
    soprano_degrees, soprano_directions = _parse_signed_degrees(raw_list=raw_soprano)
    bass_degrees, bass_directions = _parse_signed_degrees(raw_list=raw_bass)
    min_bars, max_bars = _parse_bars(data=data["bars"])
    # Derive entry/exit from first/last degrees
    entry = Arrival(soprano=soprano_degrees[0], bass=bass_degrees[0])
    exit = Arrival(soprano=soprano_degrees[-1], bass=bass_degrees[-1])
    return Schema(
        name=name,
        soprano_degrees=soprano_degrees,
        soprano_directions=soprano_directions,
        bass_degrees=bass_degrees,
        bass_directions=bass_directions,
        entry=entry,
        exit=exit,
        min_bars=min_bars,
        max_bars=max_bars,
        position=data.get("position", "continuation"),
        sequential=data.get("sequential", False),
        direction=data.get("direction"),
        segment_direction=data.get("segment_direction"),
        segments=_parse_segments(data=data.get("segments", 1)),
        pedal=data.get("pedal"),
        chromatic=data.get("chromatic", False),
        figuration_profile=data.get("figuration_profile", "galant_general"),
        cadence_approach=data.get("cadence_approach", False),
        typical_keys=_parse_typical_keys(raw=data.get("typical_keys")),
    )


@lru_cache(maxsize=1)
def load_schemas() -> dict[str, Schema]:
    """Load all schemas from data/schemas/schemas.yaml."""
    raw = _load_yaml(name="schemas/schemas.yaml")
    schemas: dict[str, Schema] = {}
    for name, data in raw.items():
        if not isinstance(data, dict):
            continue
        if "soprano_degrees" not in data and "segment" not in data:
            continue
        schemas[name] = _parse_schema(name=name, data=data)
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
    return get_schemas_by_position(position="opening")


def get_riposte_schemas() -> list[str]:
    """Return schema names valid for riposte."""
    return get_schemas_by_position(position="riposte")


def get_continuation_schemas() -> list[str]:
    """Return schema names valid for continuation."""
    return get_schemas_by_position(position="continuation")


def get_pre_cadential_schemas() -> list[str]:
    """Return schema names valid for pre-cadential."""
    return get_schemas_by_position(position="pre_cadential")


def get_cadential_schemas() -> list[str]:
    """Return schema names valid for cadence."""
    return get_schemas_by_position(position="cadential")


def get_sequential_schemas() -> list[str]:
    """Return sequential schema names (Monte, Fonte)."""
    schemas = load_schemas()
    return [name for name, s in schemas.items() if s.sequential]


def get_typical_position(schema_name: str) -> str:
    """Get the typical formal position for a schema."""
    schema = get_schema(name=schema_name)
    return schema.position


def schema_fits_bars(schema_name: str, available_bars: int) -> bool:
    """Check if schema can fit within available bars.

    A schema fits if its min_bars <= available_bars.
    The schema will use between min_bars and min(max_bars, available_bars).
    """
    schema = get_schema(name=schema_name)
    return schema.min_bars <= available_bars


def can_connect_direct(from_schema: str, to_schema: str) -> bool:
    """Check if two schemas can connect directly (no free passage).

    Direct connection requires one of:
    1. Identity: exit.bass == entry.bass
    2. Step: |exit.bass - entry.bass| == 1
    3. Dominant resolution: exit.bass == 5 and entry.bass == 1
    """
    from_s = get_schema(name=from_schema)
    to_s = get_schema(name=to_schema)
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
    """Return valid successor schemas from transitions YAML.
    
    Reads allowed_next from schema_transitions.yaml.
    Asserts if schema not defined — missing definitions are errors.
    """
    transitions = _load_transitions()
    assert schema_name in transitions, (
        f"Schema '{schema_name}' not in schema_transitions.yaml. "
        f"Add allowed_next definition for this schema."
    )
    schema_data = transitions[schema_name]
    assert isinstance(schema_data, dict), (
        f"Schema '{schema_name}' in schema_transitions.yaml is not a dict"
    )
    assert "allowed_next" in schema_data, (
        f"Schema '{schema_name}' missing 'allowed_next' in schema_transitions.yaml"
    )
    allowed = schema_data["allowed_next"]
    return [s for s in allowed if isinstance(s, str) and not s.startswith("#")]


def get_schema_figuration_profile(schema_name: str) -> str:
    """Get figuration profile name for a schema."""
    schema = get_schema(name=schema_name)
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
    schema = get_schema(name=schema_name)
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


def get_typical_keys(schema_name: str) -> tuple[str, ...] | None:
    """Get key journey for a sequential schema."""
    schema = get_schema(name=schema_name)
    return schema.typical_keys
