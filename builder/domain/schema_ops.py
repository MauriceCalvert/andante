"""Schema operations: load, stretch, realise.

Loads schema definitions from data/schemas.yaml and provides operations
for stretching durations and extracting degree sequences.
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


def stretch_schema(schema: dict, target_bars: int) -> dict:
    """Stretch schema durations to fill target_bars.

    The skeleton (degree sequence) stays identical; only timing changes.

    Args:
        schema: Schema dict with bass_degrees, soprano_degrees, durations, bars
        target_bars: Number of bars to stretch to

    Returns:
        Dict with stretched durations
    """
    base_bars = schema.get("bars", 1)
    multiplier = Fraction(target_bars, base_bars)
    stretched = [_parse_duration(d) * multiplier for d in schema["durations"]]

    return {
        "bass_degrees": schema["bass_degrees"],
        "soprano_degrees": schema["soprano_degrees"],
        "durations": stretched,
        "bars": target_bars,
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
