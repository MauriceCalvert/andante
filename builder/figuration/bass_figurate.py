"""Bass-specific figuration using bass_diminutions.yaml.

Unlike soprano figuration which uses scaled durations, bass figuration
uses fixed durations from bass_diminutions.yaml to ensure valid baroque
note values and continuous motor rhythm.
"""
import random
from fractions import Fraction
from pathlib import Path
from typing import Sequence

import yaml

from builder.figuration.bar_context import (
    compute_beat_class,
    is_motor_context,
    reduce_density,
    should_generate_anacrusis,
)
from builder.figuration.phrase import detect_schema_sections
from builder.figuration.selector import compute_interval
from builder.figuration.types import FiguredBar
from builder.types import Anchor, PassageAssignment

_bass_diminutions: dict | None = None


def _load_bass_diminutions() -> dict:
    """Load bass_diminutions.yaml, caching result."""
    global _bass_diminutions
    if _bass_diminutions is None:
        path = Path(__file__).parent.parent.parent / "data" / "figuration" / "bass_diminutions.yaml"
        with open(path, "r") as f:
            _bass_diminutions = yaml.safe_load(f)
    return _bass_diminutions


def _parse_bar_beat(bar_beat: str) -> tuple[int, float]:
    """Parse bar.beat string into (bar, beat) tuple."""
    parts = bar_beat.split(".")
    bar = int(parts[0])
    beat = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar, beat)


def _get_degree(anchor: Anchor) -> int:
    """Get bass degree from anchor."""
    return anchor.lower_degree


def _select_bass_figure(
    interval: str,
    is_motor: bool,
    density: str,
    seed: int,
) -> dict | None:
    """Select a bass figure based on interval and context.

    Args:
        interval: Interval name (step_up, third_down, etc.)
        is_motor: Whether we're in motor rhythm context
        density: Density level (high, medium, low)
        seed: Random seed for selection

    Returns:
        Figure dict from bass_diminutions.yaml, or None.
    """
    diminutions = _load_bass_diminutions()
    # Handle interval mapping for larger intervals
    if interval not in diminutions:
        if interval.endswith("_up"):
            interval = "step_up"
        elif interval.endswith("_down"):
            interval = "step_down"
        else:
            interval = "unison"
    figures = diminutions.get(interval, [])
    if not figures:
        return None
    # Filter by motor rhythm preference
    if is_motor:
        motor_figures = [f for f in figures if f.get("motor", False)]
        if motor_figures:
            figures = motor_figures
    # Filter by density/character preference
    if density == "high":
        preferred_chars = ["energetic", "plain"]
    elif density == "medium":
        preferred_chars = ["plain", "sustained"]
    else:
        preferred_chars = ["sustained", "plain"]
    char_figures = [f for f in figures if f.get("character", "plain") in preferred_chars]
    if char_figures:
        figures = char_figures
    if not figures:
        return None
    rng = random.Random(seed)
    return rng.choice(figures)


def _figure_to_figured_bar(
    figure: dict,
    bar: int,
    start_degree: int,
    start_beat: int,
) -> FiguredBar:
    """Convert a bass figure dict to FiguredBar.

    Args:
        figure: Figure dict from bass_diminutions.yaml
        bar: Bar number
        start_degree: Starting scale degree (1-7)
        start_beat: Which beat to start on (1 or 2)

    Returns:
        FiguredBar with absolute degrees and fixed durations.
    """
    relative_degrees = figure["degrees"]
    absolute_degrees: list[int] = []
    for rel in relative_degrees:
        absolute = start_degree + rel
        while absolute < 1:
            absolute += 7
        while absolute > 7:
            absolute -= 7
        absolute_degrees.append(absolute)
    durations: list[Fraction] = []
    for dur_str in figure["durations"]:
        if isinstance(dur_str, str):
            parts = dur_str.split("/")
            durations.append(Fraction(int(parts[0]), int(parts[1])))
        else:
            durations.append(Fraction(dur_str))
    return FiguredBar(
        bar=bar,
        degrees=tuple(absolute_degrees),
        durations=tuple(durations),
        figure_name=figure["name"],
        start_beat=start_beat,
    )


def _generate_anacrusis(
    target_degree: int,
    seed: int,
) -> FiguredBar:
    """Generate a 4-note anacrusis leading to target degree.

    The anacrusis is a scalar run of 16th notes leading up or down
    to the target degree, placed in bar 0 (the upbeat bar).

    Args:
        target_degree: The degree to arrive at on beat 1 of bar 1
        seed: Random seed

    Returns:
        FiguredBar for bar 0 with anacrusis.
    """
    rng = random.Random(seed)
    # 60% ascending approach, 40% descending
    if rng.random() < 0.6:
        degrees = [target_degree - 3, target_degree - 2, target_degree - 1, target_degree]
    else:
        degrees = [target_degree + 3, target_degree + 2, target_degree + 1, target_degree]
    normalized: list[int] = []
    for d in degrees:
        while d < 1:
            d += 7
        while d > 7:
            d -= 7
        normalized.append(d)
    return FiguredBar(
        bar=0,
        degrees=tuple(normalized),
        durations=(Fraction(1, 16), Fraction(1, 16), Fraction(1, 16), Fraction(1, 16)),
        figure_name="anacrusis_run",
        start_beat=1,
    )


def figurate_bass(
    anchors: Sequence[Anchor],
    metre: str,
    seed: int,
    density: str = "medium",
    passage_assignments: Sequence[PassageAssignment] | None = None,
) -> list[FiguredBar]:
    """Figurate bass voice using bass-specific patterns.

    Unlike soprano figuration, this uses:
    - Fixed durations from bass_diminutions.yaml (no scaling)
    - Motor rhythm detection for continuous patterns
    - Beat-class for accompanying voice timing

    Args:
        anchors: Schema anchors
        metre: Time signature string like "4/4"
        seed: Random seed
        density: Density level from affect
        passage_assignments: Passage assignments with lead_voice info

    Returns:
        List of FiguredBar for bass voice.
    """
    if len(anchors) < 2:
        return []
    sorted_anchors = sorted(anchors, key=lambda a: _parse_bar_beat(a.bar_beat))
    schema_sections = detect_schema_sections(sorted_anchors)
    figured_bars: list[FiguredBar] = []
    # Check if first bar needs anacrusis
    first_bar = _parse_bar_beat(sorted_anchors[0].bar_beat)[0]
    if should_generate_anacrusis(first_bar, "bass", passage_assignments):
        anacrusis_bar = _generate_anacrusis(
            target_degree=_get_degree(sorted_anchors[0]),
            seed=seed,
        )
        figured_bars.append(anacrusis_bar)
    for i in range(len(sorted_anchors) - 1):
        anchor_a = sorted_anchors[i]
        anchor_b = sorted_anchors[i + 1]
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
        start_beat = compute_beat_class("bass", bar_num, passage_assignments)
        effective_density = density
        if start_beat == 2:
            effective_density = reduce_density(density)
        is_motor = is_motor_context(bar_num, schema_sections, sorted_anchors)
        degree_a = _get_degree(anchor_a)
        degree_b = _get_degree(anchor_b)
        interval = compute_interval(degree_a, degree_b)
        figure = _select_bass_figure(
            interval=interval,
            is_motor=is_motor,
            density=effective_density,
            seed=seed + i,
        )
        if figure is None:
            figure = {
                "name": "bass_fallback",
                "degrees": [0],
                "durations": ["1/2"],
                "character": "sustained",
                "direction": "static",
                "motor": False,
            }
        figured_bar = _figure_to_figured_bar(
            figure=figure,
            bar=bar_num,
            start_degree=degree_a,
            start_beat=start_beat,
        )
        figured_bars.append(figured_bar)
    return figured_bars
