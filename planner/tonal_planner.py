"""Tonal journey planner: key area sections from genre proportions.

The tonal journey defines where the piece spends time in different key areas.
This drives structure before cadences or schemas are placed.
"""
import logging
from pathlib import Path
from typing import Any

import yaml

from builder.domain.transpose import KEY_AREA_OFFSETS, normalise_key_area
from planner.plannertypes import TonalSection
from shared.constants import MIN_TONAL_SECTION_BARS, TONAL_PROPORTION_TOLERANCE


logger = logging.getLogger(__name__)

DATA_DIR: Path = Path(__file__).parent.parent / "data"


def _load_genre_template(genre: str) -> dict[str, Any]:
    """Load genre template, falling back to default if needed."""
    # Try genre-specific first
    genre_path = DATA_DIR / "genres" / f"{genre}.yaml"
    if genre_path.exists():
        with open(genre_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if "tonal_journey" in data:
                return data

    # Fall back to default
    default_path = DATA_DIR / "genres" / "_default.yaml"
    assert default_path.exists(), f"Default genre file not found: {default_path}"
    with open(default_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _validate_tonal_template(template: list[dict], total_bars: int) -> None:
    """Validate tonal journey template.

    Args:
        template: List of journey steps [{proportion, area, relationship}, ...]
        total_bars: Total bars in piece (unused but kept for spec compliance)

    Raises:
        AssertionError: If validation fails
    """
    # 1. Check proportions sum
    total = sum(t["proportion"] for t in template)
    assert 1.0 - TONAL_PROPORTION_TOLERANCE <= total <= 1.0 + TONAL_PROPORTION_TOLERANCE, (
        f"Proportions sum to {total}, expected 1.0"
    )

    # 2. Check all positive
    for t in template:
        assert t["proportion"] > 0, f"Proportion must be positive: {t}"

    # 3. Check valid key areas
    for t in template:
        normalised = normalise_key_area(t["area"]).upper()
        assert normalised in KEY_AREA_OFFSETS, f"Unknown key area: {t['area']}"

    # 4. Check tonic bookends
    assert template[0]["area"] in ("I", "i"), "First section must be tonic"
    assert template[-1]["area"] in ("I", "i"), "Last section must be tonic"


def plan_tonal_journey(
    genre: str,
    mode: str,
    total_bars: int,
    seed: int | None = None,
) -> tuple[TonalSection, ...]:
    """Plan tonal sections for a piece.

    Args:
        genre: Genre name (e.g., "invention")
        mode: "major" or "minor"
        total_bars: Total bars in piece
        seed: Random seed (reserved for future use)

    Returns:
        Tuple of TonalSection covering all bars
    """
    # 1. Load template
    template = _load_genre_template(genre)
    journey_template = template["tonal_journey"][mode]

    # 2. Validate template
    _validate_tonal_template(journey_template, total_bars)

    # 3. Compute bar boundaries
    sections: list[TonalSection] = []
    cumulative_proportion = 0.0
    prev_end = 0

    for i, entry in enumerate(journey_template):
        cumulative_proportion += entry["proportion"]

        if i == len(journey_template) - 1:
            end_bar = total_bars  # Last section ends at total_bars exactly
        else:
            end_bar = round(cumulative_proportion * total_bars)

        start_bar = prev_end + 1

        if end_bar >= start_bar:  # Valid section
            sections.append(TonalSection(
                start_bar=start_bar,
                end_bar=end_bar,
                key_area=entry["area"],
                relationship=entry["relationship"],
            ))

        prev_end = end_bar

    # 4. Merge short sections
    merged: list[TonalSection] = []
    for section in sections:
        length = section.end_bar - section.start_bar + 1

        if length < MIN_TONAL_SECTION_BARS and len(merged) > 0:
            # Merge with previous section
            prev = merged[-1]
            merged[-1] = TonalSection(
                start_bar=prev.start_bar,
                end_bar=section.end_bar,
                key_area=prev.key_area,
                relationship=prev.relationship,
            )
            logger.warning(f"Merged short section ({length} bars) into previous")
        else:
            merged.append(section)

    sections = merged

    # 5. Validate result
    assert len(sections) >= 1, "Must have at least one section"
    assert sections[0].key_area in ("I", "i"), "First section must be tonic"
    assert sections[-1].key_area in ("I", "i"), "Last section must be tonic"
    assert sections[0].start_bar == 1, "First section must start at bar 1"
    assert sections[-1].end_bar == total_bars, "Last section must end at total_bars"

    return tuple(sections)
