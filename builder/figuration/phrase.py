"""Phrase structure analysis for figuration."""
import random
from typing import Sequence

from builder.figuration.selector import determine_phrase_position
from builder.figuration.types import PhrasePosition
from builder.types import Anchor

# Constants
MIN_SCHEMA_SECTION_ANCHORS: int = 2
MAX_SCHEMA_SECTION_ANCHORS: int = 4
DEFORMATION_PROBABILITY: float = 0.15


def detect_schema_sections(anchors: Sequence[Anchor]) -> list[tuple[int, int]]:
    """Detect contiguous schema sections in anchor sequence.

    Any run of 2+ anchors with the same schema name forms a section.
    This enables schema-aware figuration for ALL schemas, not just sequential ones.

    Returns:
        List of (start_idx, end_idx) tuples. end_idx is exclusive.
    """
    sections: list[tuple[int, int]] = []
    i = 0
    while i < len(anchors):
        schema = anchors[i].schema.lower() if anchors[i].schema else ""
        if not schema:
            i += 1
            continue
        start = i
        while i < len(anchors) and anchors[i].schema and anchors[i].schema.lower() == schema:
            if i - start >= MAX_SCHEMA_SECTION_ANCHORS:
                break
            i += 1
        if i - start >= MIN_SCHEMA_SECTION_ANCHORS:
            sections.append((start, i))
    return sections


def in_schema_section(idx: int, sections: list[tuple[int, int]]) -> tuple[int, int] | None:
    """Check if index is start of a schema section."""
    for start, end in sections:
        if idx == start:
            return (start, end)
    return None


def select_phrase_deformation(rng: random.Random, total_bars: int) -> str | None:
    """Select phrase deformation type with low probability."""
    if total_bars < 6:
        return None
    if rng.random() > DEFORMATION_PROBABILITY:
        return None
    return rng.choice(["early_cadence", "extended_continuation"])


def determine_position_with_deformation(
    bar: int,
    total_bars: int,
    schema_type: str | None,
    deformation: str | None,
) -> PhrasePosition:
    """Determine phrase position accounting for deformation."""
    base_pos = determine_phrase_position(bar, total_bars, schema_type)
    if deformation is None:
        return base_pos
    if deformation == "early_cadence":
        cadence_start = max(2, (3 * total_bars) // 4)
        if bar == cadence_start - 1:
            return PhrasePosition(
                position="cadence",
                bars=(cadence_start - 1, total_bars),
                character="plain",
                sequential=False,
            )
    elif deformation == "extended_continuation":
        cadence_start = max(2, (3 * total_bars) // 4)
        if bar == cadence_start:
            return PhrasePosition(
                position="continuation",
                bars=(base_pos.bars[0], cadence_start),
                character="energetic",
                sequential=base_pos.sequential,
            )
    return base_pos
