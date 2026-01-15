"""Energy handler: dynamic character effects on phrases."""
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"
ENERGY_LEVELS: dict = yaml.safe_load(open(DATA_DIR / "energy.yaml", encoding="utf-8"))["levels"]


def get_energy_level(name: str) -> dict:
    """Get energy level definition by name."""
    assert name in ENERGY_LEVELS, f"Unknown energy level: {name}"
    return ENERGY_LEVELS[name]


def get_register_shift(energy: str) -> int:
    """Get register shift for energy level (scale degrees)."""
    level: dict = get_energy_level(energy)
    return level.get("register_shift", 0)


def get_rhythm_override(energy: str) -> str | None:
    """Get rhythm override for energy level."""
    level: dict = get_energy_level(energy)
    return level.get("rhythm_override")


def get_articulation(energy: str) -> str | None:
    """Get articulation tendency for energy level."""
    level: dict = get_energy_level(energy)
    return level.get("articulation")
