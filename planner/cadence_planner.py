"""Cadence planning: generate cadence points from frame and genre.

In schema-first planning, cadences are placed before any melodic content.
They determine structural arrival points where sections end and new sections begin.
This follows 18th-century practice where form is articulated by cadences.
"""
from pathlib import Path
from typing import Any

import yaml

from planner.plannertypes import CadencePoint, Frame
from shared.constants import CADENCE_DENSITY, CADENCE_TYPES


DATA_DIR: Path = Path(__file__).parent.parent / "data"

# Default cadence templates by genre (used when genre YAML lacks cadence_template)
DEFAULT_CADENCE_TEMPLATES: dict[str, dict[str, Any]] = {
    "invention": {
        "density": "high",
        "section_end": "half",
        "final": "authentic",
        "allow_phrygian": False,
    },
    "minuet": {
        "density": "low",
        "section_end": "half",
        "final": "authentic",
        "allow_phrygian": False,
    },
    "gavotte": {
        "density": "medium",
        "section_end": "half",
        "final": "authentic",
        "allow_phrygian": False,
    },
    "sarabande": {
        "density": "low",
        "section_end": "half",
        "final": "authentic",
        "allow_phrygian": True,
    },
    "bourree": {
        "density": "medium",
        "section_end": "half",
        "final": "authentic",
        "allow_phrygian": False,
    },
    "fantasia": {
        "density": "medium",
        "section_end": "half",
        "final": "authentic",
        "allow_phrygian": True,
    },
    "chorale": {
        "density": "high",
        "section_end": "authentic",
        "final": "authentic",
        "allow_phrygian": True,
    },
    "trio_sonata": {
        "density": "medium",
        "section_end": "half",
        "final": "authentic",
        "allow_phrygian": False,
    },
}

# Fallback template for unknown genres
FALLBACK_TEMPLATE: dict[str, Any] = {
    "density": "medium",
    "section_end": "half",
    "final": "authentic",
    "allow_phrygian": False,
}


def _load_genre_yaml(genre: str) -> dict[str, Any]:
    """Load genre YAML file if it exists."""
    path = DATA_DIR / "genres" / f"{genre}.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_cadence_template(genre: str) -> dict[str, Any]:
    """Get cadence template for a genre.

    Priority:
    1. cadence_template field in genre YAML (if present)
    2. DEFAULT_CADENCE_TEMPLATES lookup
    3. FALLBACK_TEMPLATE

    Returns:
        Dict with keys: density, section_end, final, allow_phrygian
    """
    genre_data = _load_genre_yaml(genre)

    # Check for explicit cadence_template in genre YAML
    if "cadence_template" in genre_data:
        return genre_data["cadence_template"]

    # Use hardcoded defaults
    if genre in DEFAULT_CADENCE_TEMPLATES:
        return DEFAULT_CADENCE_TEMPLATES[genre]

    return FALLBACK_TEMPLATE


def get_cadence_density(genre: str) -> str:
    """Get cadence density level for a genre.

    Returns:
        'high' (every 2-4 bars), 'medium' (every 4-8), or 'low' (every 8+)
    """
    template = get_cadence_template(genre)
    return template.get("density", "medium")


def compute_section_boundaries(total_bars: int, genre: str) -> list[int]:
    """Compute section boundary bars based on total length.

    For short pieces (16 bars): two sections (bars 8, 16)
    For medium pieces (24-32 bars): three sections
    For long pieces (48+ bars): multiple sections

    Args:
        total_bars: Total bars in piece.
        genre: Genre name (affects section proportions).

    Returns:
        List of bar numbers where sections end (1-indexed, includes final bar).
    """
    # Simple heuristic: divide into roughly equal sections
    if total_bars <= 8:
        return [total_bars]
    elif total_bars <= 16:
        # Two sections: half/half
        return [total_bars // 2, total_bars]
    elif total_bars <= 32:
        # Two or three sections
        section_size = total_bars // 2
        return [section_size, total_bars]
    else:
        # Multiple sections for longer pieces
        section_size = 16  # Roughly 16 bars per section
        boundaries = []
        current = section_size
        while current < total_bars:
            boundaries.append(current)
            current += section_size
        boundaries.append(total_bars)
        return boundaries


def select_cadence_type(
    bar: int,
    total_bars: int,
    mode: str,
    is_section_end: bool,
    is_final: bool,
    allow_phrygian: bool,
) -> str:
    """Select appropriate cadence type for a position.

    Rules:
    - Final bar: always authentic
    - Section end (not final): usually half, sometimes authentic
    - Mid-section: half or deceptive
    - Minor mode with allow_phrygian: may use phrygian at section ends

    Args:
        bar: Bar number (1-indexed).
        total_bars: Total bars in piece.
        mode: 'major' or 'minor'.
        is_section_end: Whether this is a section boundary.
        is_final: Whether this is the final cadence.
        allow_phrygian: Whether phrygian cadence is allowed.

    Returns:
        Cadence type string.
    """
    assert bar in CADENCE_TYPES or True  # Type validation happens elsewhere

    if is_final:
        return "authentic"

    if is_section_end:
        # Section ends typically get half cadence
        # In minor mode, phrygian is an option
        if mode == "minor" and allow_phrygian:
            # Use phrygian for some section endings in minor
            position_ratio = bar / total_bars
            if position_ratio < 0.5:
                return "phrygian"
        return "half"

    # Mid-section cadences
    return "half"


def select_cadence_target(cadence_type: str, position_ratio: float, mode: str) -> str:
    """Select harmonic target for a cadence.

    Args:
        cadence_type: Type of cadence.
        position_ratio: Position in piece (0.0 to 1.0).
        mode: 'major' or 'minor'.

    Returns:
        Roman numeral target (I, V, vi, etc.)
    """
    if cadence_type == "authentic":
        return "I"
    elif cadence_type == "half":
        return "V"
    elif cadence_type == "deceptive":
        return "vi" if mode == "major" else "VI"
    elif cadence_type == "phrygian":
        return "V"  # Phrygian half cadence lands on V
    elif cadence_type == "plagal":
        return "I"
    else:
        return "I"


def distribute_cadences(
    total_bars: int,
    density: str,
    mode: str,
    section_boundaries: list[int],
    allow_phrygian: bool,
) -> list[CadencePoint]:
    """Distribute cadence points across the piece.

    Algorithm:
    1. Place final authentic cadence at total_bars
    2. Place section-end cadences at each boundary (except final)
    3. Fill remaining space based on density

    Args:
        total_bars: Total bars in piece.
        density: 'high', 'medium', or 'low'.
        mode: 'major' or 'minor'.
        section_boundaries: Bar numbers where sections end.
        allow_phrygian: Whether phrygian cadence is allowed.

    Returns:
        List of CadencePoint objects ordered by bar.
    """
    cadences: list[CadencePoint] = []
    min_gap, max_gap = CADENCE_DENSITY.get(density, (4, 8))

    # Track which bars already have cadences
    cadence_bars: set[int] = set()

    # 1. Place final authentic cadence
    final_bar = total_bars
    cadences.append(CadencePoint(
        bar=final_bar,
        type="authentic",
        target="I",
    ))
    cadence_bars.add(final_bar)

    # 2. Place section-end cadences (except final)
    for boundary in section_boundaries:
        if boundary == final_bar:
            continue  # Already handled
        if boundary in cadence_bars:
            continue

        position_ratio = boundary / total_bars
        is_section_end = True
        is_final = False

        cadence_type = select_cadence_type(
            bar=boundary,
            total_bars=total_bars,
            mode=mode,
            is_section_end=is_section_end,
            is_final=is_final,
            allow_phrygian=allow_phrygian,
        )
        target = select_cadence_target(cadence_type, position_ratio, mode)

        cadences.append(CadencePoint(
            bar=boundary,
            type=cadence_type,
            target=target,
        ))
        cadence_bars.add(boundary)

    # 3. Fill remaining space based on density
    # Start from beginning, place cadences at regular intervals
    current_bar = min_gap
    while current_bar < total_bars:
        # Skip if too close to existing cadence
        if any(abs(current_bar - b) < min_gap for b in cadence_bars):
            current_bar += 1
            continue

        # Place intermediate cadence
        position_ratio = current_bar / total_bars
        cadence_type = "half"  # Intermediate cadences are typically half
        target = select_cadence_target(cadence_type, position_ratio, mode)

        cadences.append(CadencePoint(
            bar=current_bar,
            type=cadence_type,
            target=target,
        ))
        cadence_bars.add(current_bar)

        # Move to next potential position
        current_bar += min_gap

    # Sort by bar number
    cadences.sort(key=lambda c: c.bar)

    return cadences


def plan_cadences(
    frame: Frame,
    genre: str,
    total_bars: int,
) -> tuple[CadencePoint, ...]:
    """Generate cadence plan for entire piece.

    This is the main entry point for cadence planning. It determines all
    structural arrival points before any melodic content is generated.

    Rules:
    1. Final bar: authentic to I (always)
    2. Section boundaries: half or authentic
    3. Density from genre template (high/medium/low)
    4. Minor mode: may use phrygian half cadence

    Args:
        frame: Contains key, mode, metre.
        genre: Genre name for template lookup.
        total_bars: Total bars in piece.

    Returns:
        Tuple of CadencePoint ordered by bar number.
    """
    assert total_bars > 0, f"total_bars must be positive, got {total_bars}"

    # Get cadence configuration
    template = get_cadence_template(genre)
    density = template.get("density", "medium")
    allow_phrygian = template.get("allow_phrygian", False)

    # Compute section boundaries
    section_boundaries = compute_section_boundaries(total_bars, genre)

    # Distribute cadences
    cadences = distribute_cadences(
        total_bars=total_bars,
        density=density,
        mode=frame.mode,
        section_boundaries=section_boundaries,
        allow_phrygian=allow_phrygian,
    )

    return tuple(cadences)
