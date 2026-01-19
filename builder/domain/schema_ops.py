"""Schema operations: load, tile, realise.

Loads schema definitions from data/schemas.yaml and provides operations
for tiling schemas and extracting degree sequences.
"""
from fractions import Fraction
from pathlib import Path

import yaml

DATA_DIR: Path = Path(__file__).parent.parent.parent / "data"
_SCHEMAS: dict | None = None


def load_schemas() -> dict:
    """Load schemas from data/schemas.yaml (cached)."""
    global _SCHEMAS
    if _SCHEMAS is None:
        path = DATA_DIR / "schemas.yaml"
        assert path.exists(), f"Missing {path}"
        with open(path, encoding="utf-8") as f:
            _SCHEMAS = yaml.safe_load(f)
    return _SCHEMAS


def clear_cache() -> None:
    """Clear schema cache. Used in tests."""
    global _SCHEMAS
    _SCHEMAS = None


def get_schema(name: str) -> dict:
    """Get schema by name."""
    schemas = load_schemas()
    assert name in schemas, f"Unknown schema: {name}. Valid: {sorted(schemas.keys())}"
    return schemas[name]


def tile_schema(schema: dict, repetitions: int) -> dict:
    """Tile schema by repeating degree sequences and durations.

    Pure tiling: repeat schema N times = N times the notes with same durations.
    This preserves the musical character better than stretching durations.

    Args:
        schema: Schema dict with bass_degrees, soprano_degrees, durations, bars
        repetitions: Number of times to repeat the schema

    Returns:
        Dict with tiled content (more notes, same individual durations)
    """
    assert repetitions >= 1, f"repetitions must be >= 1, got {repetitions}"

    base_bars = schema.get("bars", 1)
    bass = schema["bass_degrees"]
    soprano = schema["soprano_degrees"]
    durations = [_parse_duration(d) for d in schema["durations"]]

    return {
        "bass_degrees": bass * repetitions,
        "soprano_degrees": soprano * repetitions,
        "durations": durations * repetitions,
        "bars": base_bars * repetitions,
    }


def extract_degree(d: int | dict) -> tuple[int, int]:
    """Extract (degree, alteration) from degree spec.

    Handles both simple degrees (int) and altered degrees (dict with degree/alter).

    Args:
        d: Either an int (scale degree 1-7) or dict like {degree: 4, alter: 1}

    Returns:
        (degree, alteration) where alteration is semitones
    """
    if isinstance(d, dict):
        return d["degree"], d.get("alter", 0)
    return d, 0


def degrees_to_diatonic(
    degrees: list,
    durations: list[Fraction],
    octave: int,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Convert scale degrees to diatonic pitches.

    Args:
        degrees: List of scale degrees (1-7) or dicts with alter
        durations: List of durations
        octave: Base octave (0-indexed, where octave 4 = middle C area)

    Returns:
        (pitches, durations) where pitches are diatonic pitch numbers
    """
    pitches: list[int] = []
    for d in degrees:
        deg, alter = extract_degree(d)
        # degree 1 → diatonic 0 in octave, degree 7 → diatonic 6
        # Diatonic pitch = (degree - 1) + (octave * 7)
        diatonic = (deg - 1) + (octave * 7)
        # Note: alter stored but not applied here (chromatic adjustment in MIDI export)
        pitches.append(diatonic)

    return tuple(pitches), tuple(durations)


def _parse_duration(d: str | Fraction | int) -> Fraction:
    """Parse duration to Fraction."""
    if isinstance(d, Fraction):
        return d
    if isinstance(d, str) and "/" in d:
        num, den = d.split("/")
        return Fraction(int(num), int(den))
    return Fraction(d)
