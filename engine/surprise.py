"""Surprise handler: strategic deviations from expectation."""
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"
SURPRISES: dict = yaml.safe_load(open(DATA_DIR / "surprises.yaml", encoding="utf-8"))


def get_surprise(name: str) -> dict:
    """Get surprise definition by name."""
    types: dict = SURPRISES["types"]
    assert name in types, f"Unknown surprise: {name}"
    return types[name]


def get_register_shift(surprise: str | None) -> int:
    """Get register shift for surprise (semitones)."""
    if surprise is None:
        return 0
    return get_surprise(surprise).get("register_shift", 0)


def get_cadence_override(surprise: str | None) -> str | None:
    """Get cadence override for surprise."""
    if surprise is None:
        return None
    return get_surprise(surprise).get("cadence_override")


def get_treatment_override(surprise: str | None) -> str | None:
    """Get treatment override for surprise."""
    if surprise is None:
        return None
    return get_surprise(surprise).get("treatment_override")


def get_rhythm_override(surprise: str | None) -> str | None:
    """Get rhythm override for surprise."""
    if surprise is None:
        return None
    return get_surprise(surprise).get("rhythm_override")


def get_fill_override(surprise: str | None) -> str | None:
    """Get fill override for surprise (e.g., sequence_break)."""
    if surprise is None:
        return None
    return get_surprise(surprise).get("fill_override")
