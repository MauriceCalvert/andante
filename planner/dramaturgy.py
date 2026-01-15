"""Dramaturgy module: rhetorical structure and tension curves.

Maps affects to dramaturgical archetypes and computes:
- Rhetorical structure (exordium, narratio, confutatio, confirmatio, peroratio)
- Tension curves (per-bar tension levels)
- Climax positioning
"""
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from planner.plannertypes import (
    RhetoricalSection, RhetoricalStructure, TensionPoint, TensionCurve
)


DATA_DIR: Path = Path(__file__).parent.parent / "data"

# Rhetorical function descriptions
RHETORICAL_FUNCTIONS: Dict[str, str] = {
    "exordium": "Opening - captures attention, establishes affect",
    "narratio": "Exposition - presents main thematic material",
    "confutatio": "Development - confronts, contrasts, develops",
    "confirmatio": "Proof - confirms, resolves, builds to climax",
    "peroratio": "Conclusion - summarizes, brings closure",
}

# Default archetype for unknown affects
DEFAULT_ARCHETYPE = "assertion_confirmation"


def load_archetypes() -> Dict[str, dict]:
    """Load archetype definitions from YAML."""
    path = DATA_DIR / "archetypes.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_affects() -> Dict[str, dict]:
    """Load affect definitions from YAML."""
    path = DATA_DIR / "affects.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def select_archetype(affect: str) -> str:
    """Select appropriate archetype for the given affect.

    Uses the archetype mapping in affects.yaml, falling back to
    compatible_affects in archetypes.yaml, then to default.
    """
    affects = load_affects()
    archetypes = load_archetypes()

    # Check if affect has explicit archetype mapping
    if affect in affects:
        affect_data = affects[affect]
        if "archetype" in affect_data:
            archetype = affect_data["archetype"]
            if archetype in archetypes:
                return archetype

    # Fall back to compatible_affects search
    for arch_name, arch_data in archetypes.items():
        compatible = arch_data.get("compatible_affects", [])
        if affect in compatible:
            return arch_name

    return DEFAULT_ARCHETYPE


def compute_rhetorical_structure(
    archetype: str,
    total_bars: int,
) -> RhetoricalStructure:
    """Compute rhetorical section boundaries for the piece.

    Args:
        archetype: Name of the dramaturgical archetype
        total_bars: Total number of bars in the piece

    Returns:
        RhetoricalStructure with section boundaries
    """
    archetypes = load_archetypes()

    if archetype not in archetypes:
        archetype = DEFAULT_ARCHETYPE

    arch_data = archetypes[archetype]
    proportions = arch_data.get("rhetorical_sections", {})
    climax_pos = arch_data.get("climax_position", 0.7)

    # Default proportions if not specified
    default_props = {
        "exordium": 0.12,
        "narratio": 0.23,
        "confutatio": 0.30,
        "confirmatio": 0.20,
        "peroratio": 0.15,
    }

    # Merge with defaults
    for key in default_props:
        if key not in proportions:
            proportions[key] = default_props[key]

    # Normalize proportions
    total_prop = sum(proportions.values())
    proportions = {k: v / total_prop for k, v in proportions.items()}

    # Compute bar boundaries
    sections: List[RhetoricalSection] = []
    current_bar = 1
    section_order = ["exordium", "narratio", "confutatio", "confirmatio", "peroratio"]

    for section_name in section_order:
        prop = proportions.get(section_name, 0.2)
        section_bars = max(1, round(total_bars * prop))

        # Adjust last section to fill remaining bars
        if section_name == "peroratio":
            section_bars = total_bars - current_bar + 1

        end_bar = min(current_bar + section_bars - 1, total_bars)

        sections.append(RhetoricalSection(
            name=section_name,
            start_bar=current_bar,
            end_bar=end_bar,
            function=RHETORICAL_FUNCTIONS.get(section_name, ""),
            proportion=prop,
        ))

        current_bar = end_bar + 1
        if current_bar > total_bars:
            break

    # Compute climax bar
    climax_bar = max(1, min(total_bars, round(total_bars * climax_pos)))

    return RhetoricalStructure(
        archetype=archetype,
        sections=tuple(sections),
        climax_position=climax_pos,
        climax_bar=climax_bar,
    )


def compute_tension_curve(
    archetype: str,
    total_bars: int,
) -> TensionCurve:
    """Compute tension curve for the piece.

    Interpolates between control points defined in the archetype.

    Args:
        archetype: Name of the dramaturgical archetype
        total_bars: Total number of bars in the piece

    Returns:
        TensionCurve with interpolated per-bar tension values
    """
    archetypes = load_archetypes()

    if archetype not in archetypes:
        archetype = DEFAULT_ARCHETYPE

    arch_data = archetypes.get(archetype, {})
    raw_curve = arch_data.get("tension_curve", [
        [0.0, 0.3],
        [0.5, 0.7],
        [0.8, 0.9],
        [1.0, 0.4],
    ])
    climax_pos = arch_data.get("climax_position", 0.7)

    # Convert to TensionPoints
    control_points: List[Tuple[float, float]] = [
        (float(p[0]), float(p[1])) for p in raw_curve
    ]

    # Ensure we have start and end points
    if control_points[0][0] > 0:
        control_points.insert(0, (0.0, control_points[0][1]))
    if control_points[-1][0] < 1.0:
        control_points.append((1.0, control_points[-1][1]))

    # Interpolate to get per-bar values
    points: List[TensionPoint] = []
    max_tension = 0.0
    max_position = 0.0

    for bar in range(1, total_bars + 1):
        position = bar / total_bars
        tension = _interpolate_tension(position, control_points)

        points.append(TensionPoint(position=position, level=tension))

        if tension > max_tension:
            max_tension = tension
            max_position = position

    return TensionCurve(
        points=tuple(points),
        climax_position=max_position,
        climax_level=max_tension,
    )


def _interpolate_tension(
    position: float,
    control_points: List[Tuple[float, float]],
) -> float:
    """Linear interpolation between control points."""
    # Find surrounding control points
    for i in range(len(control_points) - 1):
        p1_pos, p1_level = control_points[i]
        p2_pos, p2_level = control_points[i + 1]

        if p1_pos <= position <= p2_pos:
            # Linear interpolation
            if p2_pos == p1_pos:
                return p1_level
            t = (position - p1_pos) / (p2_pos - p1_pos)
            return p1_level + t * (p2_level - p1_level)

    # If position is beyond control points, use nearest
    if position <= control_points[0][0]:
        return control_points[0][1]
    return control_points[-1][1]


def get_tension_at_bar(
    tension_curve: TensionCurve,
    bar: int,
    total_bars: int,
) -> float:
    """Get tension level at a specific bar."""
    position = bar / total_bars
    return _get_tension_at_position(tension_curve, position)


def _get_tension_at_position(
    tension_curve: TensionCurve,
    position: float,
) -> float:
    """Get tension level at a specific position (0.0 to 1.0)."""
    # Find nearest point
    best_dist = float("inf")
    best_level = 0.5

    for point in tension_curve.points:
        dist = abs(point.position - position)
        if dist < best_dist:
            best_dist = dist
            best_level = point.level

    return best_level


def get_section_at_bar(
    rhetoric: RhetoricalStructure,
    bar: int,
) -> RhetoricalSection | None:
    """Get the rhetorical section containing a specific bar."""
    for section in rhetoric.sections:
        if section.start_bar <= bar <= section.end_bar:
            return section
    return None


def get_key_scheme(
    archetype: str,
    mode: str,
) -> Dict[str, str]:
    """Get the key scheme for an archetype and mode.

    Args:
        archetype: Name of the archetype
        mode: "major" or "minor"

    Returns:
        Dict mapping rhetorical section names to key areas (Roman numerals)
    """
    archetypes = load_archetypes()

    if archetype not in archetypes:
        archetype = DEFAULT_ARCHETYPE

    arch_data = archetypes.get(archetype, {})

    scheme_key = f"key_scheme_{mode}"
    if scheme_key not in arch_data:
        scheme_key = "key_scheme_major" if mode == "major" else "key_scheme_minor"

    scheme = arch_data.get(scheme_key, {})

    # Default scheme if not specified
    if not scheme:
        if mode == "minor":
            scheme = {
                "exordium": "i",
                "narratio": "III",
                "confutatio": "iv",
                "confirmatio": "V",
                "peroratio": "i",
            }
        else:
            scheme = {
                "exordium": "I",
                "narratio": "V",
                "confutatio": "IV",
                "confirmatio": "V",
                "peroratio": "I",
            }

    return scheme
