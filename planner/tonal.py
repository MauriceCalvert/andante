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
    modality: str = "diatonic"
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



def _assign_key_areas(
    sections: tuple[dict, ...],
    density: str,
    rng: Random,
) -> list[str]:
    """Assign key areas to sections based on position.

    V-T004: no consecutive identical non-tonic keys (enforced inline).
    """
    count: int = len(sections)
    key_areas: list[str] = []
    for i in range(count):
        if i == 0:
            key_areas.append(_FIRST_KEY)
        elif i == count - 1:
            key_areas.append(_FINAL_KEY)
        elif i == count - 2 and count > 2:
            penultimate: str = _PENULTIMATE_KEY
            prev_key: str = key_areas[i - 1]
            # V-T004: no consecutive identical non-tonic keys
            if prev_key == penultimate and prev_key != "I":
                penultimate = "IV"
            key_areas.append(penultimate)
        else:
            pool: tuple[str, ...] = _ODD_KEY_CANDIDATES if i % 2 == 1 else _EVEN_KEY_CANDIDATES
            prev_key: str = key_areas[i - 1]
            # V-T004: exclude previous key if non-tonic to prevent consecutive identical non-tonic
            if prev_key != "I":
                candidates: list[str] = [k for k in pool if k != prev_key]
            else:
                candidates = list(pool)
            if density == "low":
                key_areas.append(candidates[0])
            else:
                key_areas.append(rng.choice(candidates))
    return key_areas


def _assign_cadences(
    sections: tuple[dict, ...],
    rng: Random,
) -> list[str]:
    """Assign cadence types to sections based on position.

    V-T003 constraints enforced inline:
    - No consecutive half cadences
    - At most one interior authentic cadence
    """
    count: int = len(sections)
    cadences: list[str] = []
    has_interior_authentic: bool = False
    for i in range(count):
        if i == count - 1:
            cadences.append(_FINAL_CADENCE)
            continue
        if i == 0:
            pool: tuple[str, ...] = _FIRST_CADENCES
        elif i == count - 2 and count > 2:
            pool = _PENULTIMATE_CADENCES
        else:
            pool = _INTERIOR_CADENCES
        candidates: list[str] = list(pool)
        # V-T003: no consecutive half cadences
        if cadences and cadences[-1] == "half":
            candidates = [c for c in candidates if c != "half"]
        # V-T003: at most one interior authentic (interior = not final)
        if has_interior_authentic:
            candidates = [c for c in candidates if c != "authentic"]
        assert len(candidates) > 0, (
            f"No valid cadence candidates for section {i}; "
            f"previous={cadences[-1] if cadences else None}, "
            f"has_interior_authentic={has_interior_authentic}"
        )
        choice: str = rng.choice(candidates)
        if choice == "authentic":
            has_interior_authentic = True
        cadences.append(choice)
    return cadences
