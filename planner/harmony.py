"""Harmonic architecture planning.

Plans key schemes, modulations, and cadences based on:
- Rhetorical structure (where in the piece)
- Archetype (what dramatic arc)
- Tension curve (how intense)
"""
from typing import Dict, List, Tuple

from planner.dramaturgy import get_key_scheme, get_section_at_bar
from planner.plannertypes import (
    HarmonicTarget, HarmonicPlan, RhetoricalStructure, TensionCurve
)


# Cadence types by rhetorical position and tension
CADENCE_BY_POSITION: Dict[str, Dict[str, str]] = {
    "exordium": {
        "low": "half",
        "medium": "half",
        "high": "imperfect",
    },
    "narratio": {
        "low": "half",
        "medium": "imperfect",
        "high": "perfect",
    },
    "confutatio": {
        "low": "deceptive",
        "medium": "half",
        "high": "half",
    },
    "confirmatio": {
        "low": "imperfect",
        "medium": "perfect",
        "high": "perfect",
    },
    "peroratio": {
        "low": "perfect",
        "medium": "perfect",
        "high": "perfect",
    },
}


def tension_category(level: float) -> str:
    """Categorize tension level."""
    if level < 0.4:
        return "low"
    elif level < 0.7:
        return "medium"
    else:
        return "high"


def plan_harmony(
    rhetoric: RhetoricalStructure,
    tension_curve: TensionCurve,
    mode: str,
    total_bars: int,
) -> HarmonicPlan:
    """Plan harmonic architecture for the piece.

    Args:
        rhetoric: Rhetorical structure with section boundaries
        tension_curve: Tension curve with per-bar levels
        mode: "major" or "minor"
        total_bars: Total bars in piece

    Returns:
        HarmonicPlan with targets and modulations
    """
    # Get key scheme for this archetype and mode
    key_scheme = get_key_scheme(archetype=rhetoric.archetype, mode=mode)

    targets: List[HarmonicTarget] = []
    modulations: List[Tuple[int, str, str]] = []

    # Plan targets at section boundaries
    prev_key = key_scheme.get("exordium", "I" if mode == "major" else "i")

    for section in rhetoric.sections:
        section_key = key_scheme.get(section.name, prev_key)

        # Get tension at section end
        section_position = section.end_bar / total_bars
        tension = _get_tension_at_position(tension_curve=tension_curve, position=section_position)
        t_cat = tension_category(level=tension)

        # Select cadence type
        cadence = CADENCE_BY_POSITION.get(
            section.name, {"low": "half", "medium": "half", "high": "perfect"}
        ).get(t_cat, "half")

        # Add target at section end
        targets.append(HarmonicTarget(
            key_area=section_key,
            cadence_type=cadence,
            bar=section.end_bar,
        ))

        # Record modulation if key changed
        if section_key != prev_key:
            modulations.append((
                section.start_bar,
                prev_key,
                section_key,
            ))
            prev_key = section_key

    # Add internal targets at phrase boundaries (every 4 bars or so)
    internal_targets = _plan_internal_targets(
        rhetoric=rhetoric, tension_curve=tension_curve, key_scheme=key_scheme, total_bars=total_bars
    )
    targets.extend(internal_targets)

    # Sort targets by bar
    targets.sort(key=lambda t: t.bar)

    return HarmonicPlan(
        targets=tuple(targets),
        modulations=tuple(modulations),
    )


def _plan_internal_targets(
    rhetoric: RhetoricalStructure,
    tension_curve: TensionCurve,
    key_scheme: Dict[str, str],
    total_bars: int,
) -> List[HarmonicTarget]:
    """Plan internal harmonic targets within sections."""
    targets: List[HarmonicTarget] = []

    for section in rhetoric.sections:
        section_bars = section.end_bar - section.start_bar + 1
        section_key = key_scheme.get(section.name, "I")

        # Add targets every 4 bars within section
        if section_bars >= 8:
            internal_bars = list(range(
                section.start_bar + 4,
                section.end_bar,
                4
            ))

            for bar in internal_bars:
                # Get tension at this bar
                tension = _get_tension_at_bar(tension_curve=tension_curve, bar=bar, total_bars=total_bars)
                t_cat = tension_category(level=tension)

                # Internal targets use half or imperfect cadences
                if t_cat == "high":
                    cadence = "half"
                elif t_cat == "medium":
                    cadence = "imperfect"
                else:
                    cadence = "half"

                targets.append(HarmonicTarget(
                    key_area=section_key,
                    cadence_type=cadence,
                    bar=bar,
                ))

    return targets


def _get_tension_at_position(
    tension_curve: TensionCurve,
    position: float,
) -> float:
    """Get tension level at a specific position."""
    best_dist = float("inf")
    best_level = 0.5

    for point in tension_curve.points:
        dist = abs(point.position - position)
        if dist < best_dist:
            best_dist = dist
            best_level = point.level

    return best_level


def _get_tension_at_bar(
    tension_curve: TensionCurve,
    bar: int,
    total_bars: int,
) -> float:
    """Get tension level at a specific bar."""
    position = bar / total_bars
    return _get_tension_at_position(tension_curve=tension_curve, position=position)


def get_key_at_bar(
    harmonic_plan: HarmonicPlan,
    bar: int,
) -> str:
    """Get the key area at a specific bar."""
    current_key = "I"

    for target in harmonic_plan.targets:
        if target.bar <= bar:
            current_key = target.key_area
        else:
            break

    return current_key


def get_cadence_at_bar(
    harmonic_plan: HarmonicPlan,
    bar: int,
) -> str | None:
    """Get the cadence type at a specific bar, if any."""
    for target in harmonic_plan.targets:
        if target.bar == bar:
            return target.cadence_type
    return None
