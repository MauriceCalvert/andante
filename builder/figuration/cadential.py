"""Cadential figure selection."""
import random

from builder.figuration.loader import get_cadential
from builder.figuration.types import CadentialFigure, Figure

CADENTIAL_UNDERSTATEMENT_PROBABILITY: float = 0.10


def select_cadential_figure(
    to_degree: int,
    interval: str,
    is_minor: bool,
    seed: int,
    rng: random.Random,
) -> Figure | None:
    """Select from cadential table for phrase endings."""
    if rng.random() < CADENTIAL_UNDERSTATEMENT_PROBABILITY:
        return None
    cadential = get_cadential()
    if to_degree == 1:
        target = "target_1"
    elif to_degree == 5:
        target = "target_5"
    else:
        return None
    if target not in cadential:
        return None
    approaches = cadential[target]
    approach_key = interval_to_approach_key(interval)
    if approach_key not in approaches:
        if "unison" in approaches:
            approach_key = "unison"
        else:
            return None
    cadential_figures = approaches[approach_key]
    if not cadential_figures:
        return None
    if is_minor:
        cadential_figures = [cf for cf in cadential_figures if cadential_minor_safe(cf)]
        if not cadential_figures:
            cadential_figures = approaches[approach_key]
    rng_local = random.Random(seed)
    selected_cf = rng_local.choice(cadential_figures)
    return cadential_to_figure(selected_cf)


def cadential_to_figure(cf: CadentialFigure) -> Figure:
    """Convert CadentialFigure to regular Figure for realisation."""
    return Figure(
        name=cf.name,
        degrees=cf.degrees,
        contour=cf.contour,
        polarity="balanced",
        arrival="stepwise" if len(cf.degrees) > 2 else "direct",
        placement="end",
        character="plain",
        harmonic_tension="low",
        max_density="high" if len(cf.degrees) > 4 else "medium",
        cadential_safe=True,
        repeatable=False,
        requires_compensation=False,
        compensation_direction=None,
        is_compound=False,
        minor_safe=True,
        requires_leading_tone=cf.contour in ("trilled_resolution", "leading_tone_resolution"),
        weight=1.0,
    )


def cadential_minor_safe(cf: CadentialFigure) -> bool:
    """Check if cadential figure is safe in minor key."""
    return cf.contour not in ("trilled_resolution",)


def interval_to_approach_key(interval: str) -> str:
    """Map interval name to cadential approach key."""
    mapping = {
        "unison": "unison",
        "step_up": "step_up",
        "step_down": "step_down",
        "third_up": "third_up",
        "third_down": "third_down",
        "fourth_up": "fourth_up",
        "fourth_down": "fourth_down",
        "fifth_up": "fifth_up",
        "fifth_down": "fifth_down",
    }
    return mapping.get(interval, "step_down")
