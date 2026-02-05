"""Layer 2: Tonal planning.

Assigns key areas and cadence types to form sections.
Input: AffectConfig, GenreConfig
Output: TonalPlan

RNG lives here per A005; downstream is deterministic.
"""
from random import Random

from builder.types import AffectConfig, GenreConfig, SectionTonalPlan, TonalPlan
from planner.variety import validate_cadence_variety, validate_tonal_path_variety
from shared.constants import TONAL_CADENCE_TYPES, VALID_KEY_AREAS


# Key area candidates by section position
_FIRST_KEY: str = "I"
_FINAL_KEY: str = "I"
_PENULTIMATE_KEY: str = "V"
_ODD_KEY_CANDIDATES: tuple[str, ...] = ("V", "IV", "vi")
_EVEN_KEY_CANDIDATES: tuple[str, ...] = ("IV", "ii", "vi")

# Cadence candidates by section position
_FINAL_CADENCE: str = "authentic"
_PENULTIMATE_CADENCES: tuple[str, ...] = ("half", "authentic")
_INTERIOR_CADENCES: tuple[str, ...] = ("half", "deceptive", "open")
_FIRST_CADENCES: tuple[str, ...] = ("open", "half")


def layer_2_tonal(
    affect_config: AffectConfig,
    genre_config: GenreConfig,
    seed: int = 42,
) -> TonalPlan:
    """Execute Layer 2: generate tonal plan with key areas and cadences."""
    sections: tuple[dict, ...] = genre_config.sections
    assert len(sections) > 0, "Genre has no sections"
    rng: Random = Random(seed)
    density: str = affect_config.density
    modality: str = _choose_modality(affect_config=affect_config)
    key_areas: list[str] = _assign_key_areas(
        sections=sections,
        density=density,
        rng=rng,
    )
    cadences: list[str] = _assign_cadences(
        sections=sections,
        rng=rng,
    )
    validate_tonal_path_variety(key_areas=tuple(key_areas))
    validate_cadence_variety(cadences=tuple(cadences))
    section_plans: list[SectionTonalPlan] = []
    for i, section in enumerate(sections):
        section_plans.append(SectionTonalPlan(
            name=section["name"],
            key_area=key_areas[i],
            cadence_type=cadences[i],
        ))
    return TonalPlan(
        sections=tuple(section_plans),
        home_key=affect_config.tonal_path.get("exordium", ("I",))[0] if affect_config.tonal_path else "I",
        modality=modality,
        density=density,
    )


def _choose_modality(affect_config: AffectConfig) -> str:
    """Determine modality from affect."""
    if hasattr(affect_config, "rhythm_states") and affect_config.rhythm_states:
        return "diatonic"
    return "diatonic"


def _assign_key_areas(
    sections: tuple[dict, ...],
    density: str,
    rng: Random,
) -> list[str]:
    """Assign key areas to sections based on position."""
    count: int = len(sections)
    key_areas: list[str] = []
    for i in range(count):
        if i == 0:
            key_areas.append(_FIRST_KEY)
        elif i == count - 1:
            key_areas.append(_FINAL_KEY)
        elif i == count - 2 and count > 2:
            key_areas.append(_PENULTIMATE_KEY)
        elif i % 2 == 1:
            candidates: tuple[str, ...] = _ODD_KEY_CANDIDATES
            if density == "low":
                key_areas.append(candidates[0])
            else:
                key_areas.append(rng.choice(candidates))
        else:
            candidates = _EVEN_KEY_CANDIDATES
            if density == "low":
                key_areas.append(candidates[0])
            else:
                key_areas.append(rng.choice(candidates))
    _fix_consecutive_non_tonic(key_areas=key_areas, rng=rng)
    return key_areas


def _fix_consecutive_non_tonic(
    key_areas: list[str],
    rng: Random,
) -> None:
    """Ensure V-T004: no consecutive identical non-tonic keys (in-place)."""
    for i in range(len(key_areas) - 1):
        if key_areas[i] != "I" and key_areas[i] == key_areas[i + 1]:
            alternatives: list[str] = [
                k for k in ("IV", "ii", "vi", "V")
                if k != key_areas[i]
            ]
            key_areas[i + 1] = rng.choice(alternatives)


def _assign_cadences(
    sections: tuple[dict, ...],
    rng: Random,
) -> list[str]:
    """Assign cadence types to sections based on position."""
    count: int = len(sections)
    cadences: list[str] = []
    for i in range(count):
        if i == count - 1:
            cadences.append(_FINAL_CADENCE)
        elif i == 0:
            cadences.append(rng.choice(_FIRST_CADENCES))
        elif i == count - 2 and count > 2:
            cadences.append(rng.choice(_PENULTIMATE_CADENCES))
        else:
            cadences.append(rng.choice(_INTERIOR_CADENCES))
    _fix_consecutive_half_cadences(cadences=cadences, rng=rng)
    _fix_interior_authentic_overuse(cadences=cadences, rng=rng)
    return cadences


def _fix_consecutive_half_cadences(
    cadences: list[str],
    rng: Random,
) -> None:
    """Ensure V-T003: no consecutive half cadences (in-place)."""
    for i in range(len(cadences) - 1):
        if cadences[i] == "half" and cadences[i + 1] == "half":
            alternatives: list[str] = [c for c in ("open", "deceptive") if c != cadences[i]]
            cadences[i + 1] = rng.choice(alternatives)


def _fix_interior_authentic_overuse(
    cadences: list[str],
    rng: Random,
) -> None:
    """Ensure V-T003: at most one interior authentic cadence (in-place)."""
    interior: list[int] = [i for i in range(len(cadences) - 1) if cadences[i] == "authentic"]
    while len(interior) > 1:
        idx: int = interior.pop()
        cadences[idx] = rng.choice(["half", "open"])
        interior = [i for i in range(len(cadences) - 1) if cadences[i] == "authentic"]
