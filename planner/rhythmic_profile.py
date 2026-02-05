"""Section-level rhythmic profile assignment.

Maps affect + section function to a RhythmicProfile that constrains
phrase and gap rhythm planning downstream.
"""
import logging
from pathlib import Path
from typing import Any
import yaml
from builder.types import RhythmicProfile
from shared.constants import (
    SECTION_CLIMAX_POSITION,
    VALID_DENSITY_TRAJECTORIES,
    VALID_DEVELOPMENT_PLANS,
    VALID_MOTIF_CHARACTERS,
)

logger = logging.getLogger(__name__)

_DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "rhythm"
_AFFECT_PROFILES_FILE: str = "affect_profiles.yaml"
_DENSITY_LEVELS: tuple[str, ...] = ("low", "medium", "high")
_DENSITY_INDEX: dict[str, int] = {level: i for i, level in enumerate(_DENSITY_LEVELS)}
_TRIPLE_METRES: frozenset[str] = frozenset({"3/4", "6/8", "3/2"})


def _load_affect_profiles() -> dict[str, Any]:
    """Load affect_profiles.yaml."""
    path: Path = _DATA_DIR / _AFFECT_PROFILES_FILE
    assert path.exists(), f"Missing affect profiles: {path}"
    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    assert "affect_profiles" in data, f"Missing 'affect_profiles' key in {path}"
    assert "section_modifiers" in data, f"Missing 'section_modifiers' key in {path}"
    return data


def _validate_affect_entry(
    name: str,
    entry: dict[str, Any],
) -> None:
    """Assert that an affect profile entry is well-formed."""
    assert "base_density" in entry, f"Affect '{name}': missing 'base_density'"
    assert entry["base_density"] in _DENSITY_INDEX, (
        f"Affect '{name}': invalid base_density '{entry['base_density']}'"
    )
    assert "character" in entry, f"Affect '{name}': missing 'character'"
    assert entry["character"] in VALID_MOTIF_CHARACTERS, (
        f"Affect '{name}': invalid character '{entry['character']}'"
    )


def _compute_density_trajectory(section_length: int) -> str:
    """Compute density trajectory from section length in bars."""
    if section_length <= 4:
        return "constant"
    if section_length <= 8:
        return "arc"
    return "arc"


def _compute_hemiola_zones(
    metre: str,
    section_start_bar: int,
    section_end_bar: int,
    has_cadence: bool,
) -> tuple[tuple[int, int], ...]:
    """Identify hemiola zones for triple-metre sections near cadences."""
    if metre not in _TRIPLE_METRES:
        return ()
    if not has_cadence:
        return ()
    cadence_bar: int = section_end_bar
    hemiola_start: int = max(section_start_bar, cadence_bar - 2)
    return ((hemiola_start, cadence_bar),)


def _coordinate_density(
    tonal_density: str,
    modifier: int,
) -> str:
    """Combine tonal density with section function modifier."""
    base_idx: int = _DENSITY_INDEX.get(tonal_density, 1)
    combined: int = max(0, min(2, base_idx + modifier))
    return _DENSITY_LEVELS[combined]


def compute_section_profile(
    affect_name: str,
    section_function: str,
    section_start_bar: int,
    section_end_bar: int,
    metre: str,
    tonal_density: str,
    has_cadence: bool,
) -> RhythmicProfile:
    """Compute a RhythmicProfile for one section.

    Combines affect character with section function modifiers
    and tonal density coordination.
    """
    data: dict[str, Any] = _load_affect_profiles()
    affect_profiles: dict[str, Any] = data["affect_profiles"]
    section_modifiers: dict[str, Any] = data["section_modifiers"]
    affect_key: str = affect_name if affect_name in affect_profiles else "default"
    affect_entry: dict[str, Any] = affect_profiles[affect_key]
    _validate_affect_entry(name=affect_key, entry=affect_entry)
    modifier_key: str = section_function if section_function in section_modifiers else "default"
    modifier_entry: dict[str, Any] = section_modifiers[modifier_key]
    density_modifier: int = modifier_entry.get("density_modifier", 0)
    development_plan: str = modifier_entry.get("development_plan", "intensifying")
    assert development_plan in VALID_DEVELOPMENT_PLANS, (
        f"Section '{section_function}': invalid development_plan '{development_plan}'"
    )
    base_density: str = _coordinate_density(
        tonal_density=affect_entry["base_density"],
        modifier=density_modifier,
    )
    section_length: int = section_end_bar - section_start_bar + 1
    assert section_length > 0, (
        f"Invalid section: start={section_start_bar}, end={section_end_bar}"
    )
    climax_bar: int = section_start_bar + int(section_length * SECTION_CLIMAX_POSITION)
    density_trajectory: str = _compute_density_trajectory(section_length=section_length)
    hemiola_zones: tuple[tuple[int, int], ...] = _compute_hemiola_zones(
        metre=metre,
        section_start_bar=section_start_bar,
        section_end_bar=section_end_bar,
        has_cadence=has_cadence,
    )
    return RhythmicProfile(
        affect=affect_key,
        base_density=base_density,
        hemiola_zones=hemiola_zones,
        climax_bar=climax_bar,
        density_trajectory=density_trajectory,
        development_plan=development_plan,
    )
