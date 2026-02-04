"""Device assignment: assigns musical figures to phrases.

Uses the Figurenlehre (baroque figure theory) to assign appropriate
musical figures based on:
- Affect (emotional content)
- Rhetorical position (where in the piece)
- Tension level (intensity at that moment)
"""
from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml

from planner.plannertypes import (
    Structure, Section, Episode, Phrase, TensionCurve, RhetoricalStructure
)
from planner.dramaturgy import get_section_at_bar


DATA_DIR: Path = Path(__file__).parent.parent / "data"


def load_figurae() -> Dict[str, Dict[str, dict]]:
    """Load figure definitions from YAML."""
    path = DATA_DIR / "rhetoric" / "figurae.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_eligible_figures(
    affect: str,
    rhetoric_position: str,
    tension: float,
) -> List[Tuple[str, str, dict]]:
    """Get figures eligible for given context.

    Args:
        affect: Target affect (Sehnsucht, Klage, etc.)
        rhetoric_position: Section name (exordium, narratio, etc.)
        tension: Tension level (0.0 to 1.0)

    Returns:
        List of (category, figure_name, figure_data) tuples
    """
    figurae = load_figurae()
    eligible: List[Tuple[str, str, dict]] = []

    for category, figures in figurae.items():
        for fig_name, fig_data in figures.items():
            # Check affect compatibility
            affects = fig_data.get("affects", [])
            if affect not in affects:
                continue

            # Check rhetoric position
            positions = fig_data.get("rhetoric_positions", [])
            if rhetoric_position not in positions:
                continue

            # Check tension range
            tension_range = fig_data.get("tension_range", [0.0, 1.0])
            if not (tension_range[0] <= tension <= tension_range[1]):
                continue

            eligible.append((category, fig_name, fig_data))

    return eligible


def select_figures_for_phrase(
    affect: str,
    rhetoric_position: str,
    tension: float,
    phrase_bars: int,
    is_climax: bool = False,
    max_figures: int = 2,
) -> List[str]:
    """Select appropriate figures for a phrase.

    Args:
        affect: Target affect
        rhetoric_position: Rhetorical section name
        tension: Tension level at this phrase
        phrase_bars: Number of bars in phrase
        is_climax: Whether this is the climax phrase
        max_figures: Maximum figures to assign

    Returns:
        List of figure names to apply
    """
    eligible = get_eligible_figures(affect=affect, rhetoric_position=rhetoric_position, tension=tension)

    if not eligible:
        return []

    selected: List[str] = []
    used_categories: Set[str] = set()

    # Sort by relevance (figures with narrower tension range are more specific)
    def specificity(fig: Tuple[str, str, dict]) -> float:
        tr = fig[2].get("tension_range", [0.0, 1.0])
        return tr[1] - tr[0]  # Narrower = more specific = smaller value

    eligible.sort(key=specificity)

    # At climax, prefer intense figures
    if is_climax:
        eligible.sort(key=lambda f: -f[2].get("tension_range", [0, 0])[1])

    for category, name, data in eligible:
        if len(selected) >= max_figures:
            break

        # Prefer variety - don't repeat categories
        if category in used_categories and len(selected) >= 1:
            continue

        selected.append(name)
        used_categories.add(category)

    return selected


def assign_devices(
    structure: Structure,
    affect: str,
    tension_curve: TensionCurve,
    rhetoric: RhetoricalStructure,
    total_bars: int,
) -> Structure:
    """Assign musical devices/figures to all phrases in structure.

    Returns a new Structure with devices assigned to phrases.

    Note: This creates a new Structure with updated Phrase objects that
    include device assignments in the 'treatment' field.
    """
    new_sections: List[Section] = []
    current_bar = 1

    for section in structure.sections:
        new_episodes: List[Episode] = []

        for episode in section.episodes:
            new_phrases: List[Phrase] = []

            for phrase in episode.phrases:
                # Get rhetorical position
                rhet_section = get_section_at_bar(rhetoric=rhetoric, bar=current_bar)
                position = rhet_section.name if rhet_section else "narratio"

                # Get tension at phrase midpoint
                mid_bar = current_bar + phrase.bars // 2
                tension = _get_tension_at_bar(
                    tension_curve=tension_curve, bar=mid_bar, total_bars=total_bars
                )

                # Is this the climax?
                is_climax = abs(current_bar - rhetoric.climax_bar) <= 2

                # Select figures
                figures = select_figures_for_phrase(
                    affect=affect,
                    rhetoric_position=position,
                    tension=tension,
                    phrase_bars=phrase.bars,
                    is_climax=is_climax,
                )

                # Update phrase with devices in treatment
                if figures:
                    device_str = "+".join(figures)
                    new_treatment = f"{phrase.treatment}[{device_str}]"
                else:
                    new_treatment = phrase.treatment

                new_phrase = Phrase(
                    index=phrase.index,
                    bars=phrase.bars,
                    tonal_target=phrase.tonal_target,
                    cadence=phrase.cadence,
                    treatment=new_treatment,
                    surprise=phrase.surprise,
                    is_climax=is_climax or phrase.is_climax,
                    energy=phrase.energy,
                    harmony=phrase.harmony,
                )
                new_phrases.append(new_phrase)
                current_bar += phrase.bars

            new_episode = Episode(
                type=episode.type,
                bars=episode.bars,
                texture=episode.texture,
                phrases=tuple(new_phrases),
                is_transition=episode.is_transition,
            )
            new_episodes.append(new_episode)

        new_section = Section(
            label=section.label,
            tonal_path=section.tonal_path,
            final_cadence=section.final_cadence,
            episodes=tuple(new_episodes),
        )
        new_sections.append(new_section)

    return Structure(
        sections=tuple(new_sections),
        arc=structure.arc,
    )


def _get_tension_at_bar(
    tension_curve: TensionCurve,
    bar: int,
    total_bars: int,
) -> float:
    """Get tension level at a specific bar."""
    position = bar / total_bars

    best_dist = float("inf")
    best_level = 0.5

    for point in tension_curve.points:
        dist = abs(point.position - position)
        if dist < best_dist:
            best_dist = dist
            best_level = point.level

    return best_level


def get_figures_for_affect(affect: str) -> Dict[str, List[str]]:
    """Get all figures compatible with an affect, grouped by category."""
    figurae = load_figurae()
    result: Dict[str, List[str]] = {}

    for category, figures in figurae.items():
        compatible = []
        for fig_name, fig_data in figures.items():
            if affect in fig_data.get("affects", []):
                compatible.append(fig_name)
        if compatible:
            result[category] = compatible

    return result
