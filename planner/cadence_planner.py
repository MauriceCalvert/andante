"""Cadence planning from tonal sections.

In schema-first planning, cadences are placed at tonal section boundaries.
The cadence type is determined by the transition between key areas.
"""
import logging
from pathlib import Path
from random import Random

import yaml

from planner.plannertypes import CadencePoint, TonalSection


logger = logging.getLogger(__name__)

DATA_DIR: Path = Path(__file__).parent.parent / "data"

# Cache for cadence transitions
_CADENCE_TRANSITIONS: dict[str, dict[str, str]] | None = None


def _load_cadence_transitions() -> dict[str, dict[str, str]]:
    """Load cadence transition rules from YAML."""
    global _CADENCE_TRANSITIONS
    if _CADENCE_TRANSITIONS is not None:
        return _CADENCE_TRANSITIONS

    path = DATA_DIR / "cadence_transitions.yaml"
    assert path.exists(), f"Cadence transitions file not found: {path}"

    with open(path, encoding="utf-8") as f:
        _CADENCE_TRANSITIONS = yaml.safe_load(f)

    return _CADENCE_TRANSITIONS


def _cadence_target(cadence_type: str, mode: str) -> str:
    """Determine harmonic target for a cadence type.

    Args:
        cadence_type: Type of cadence (authentic, half, deceptive, phrygian, plagal)
        mode: "major" or "minor"

    Returns:
        Roman numeral target (I, V, vi, etc.)
    """
    if cadence_type == "authentic":
        return "I" if mode == "major" else "i"
    elif cadence_type == "half":
        return "V"
    elif cadence_type == "deceptive":
        return "vi" if mode == "major" else "VI"
    elif cadence_type == "phrygian":
        return "V"
    elif cadence_type == "plagal":
        return "I" if mode == "major" else "i"
    else:
        return "I"


def plan_cadences(
    tonal_sections: tuple[TonalSection, ...],
    mode: str,
    seed: int | None = None,
) -> tuple[CadencePoint, ...]:
    """Plan cadences at tonal section boundaries.

    Places one cadence at the end of each tonal section. The cadence type
    is determined by the transition from the current key area to the next.

    Args:
        tonal_sections: Tuple of TonalSection from tonal_planner
        mode: "major" or "minor"
        seed: Random seed (reserved for future use)

    Returns:
        Tuple of CadencePoint, one per section boundary
    """
    # 1. Load transitions
    transitions = _load_cadence_transitions()

    # 2. Create RNG
    rng = Random(seed)

    # 3. Generate cadences
    cadences: list[CadencePoint] = []

    for i, section in enumerate(tonal_sections):
        is_final = (i == len(tonal_sections) - 1)

        if is_final:
            # Final cadence: always authentic to tonic
            cadences.append(CadencePoint(
                bar=section.end_bar,
                type="authentic",
                target="I" if mode == "major" else "i",
                in_key_area=section.key_area,
                beat=None,
            ))
        else:
            # Transition cadence
            next_section = tonal_sections[i + 1]
            from_area = section.key_area.upper().replace("O", "")
            to_area = next_section.key_area.upper().replace("O", "")

            transition_key = f"{from_area}_to_{to_area}"

            if transition_key in transitions[mode]:
                cadence_type = transitions[mode][transition_key]
            else:
                cadence_type = transitions[mode]["_default"]
                logger.warning(f"No cadence transition for {transition_key}, using default")

            target = _cadence_target(cadence_type, mode)

            cadences.append(CadencePoint(
                bar=section.end_bar,
                type=cadence_type,
                target=target,
                in_key_area=section.key_area,
                beat=None,
            ))

    return tuple(cadences)
