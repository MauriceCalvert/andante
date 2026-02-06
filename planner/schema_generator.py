"""Schema chain generation: fill bars between cadences with schemas.

The schema chain is the "harmonic DNA" of the piece. Schemas are selected
from the transition graph to land on cadence points, with texture and
treatment assigned per genre conventions.
"""
import logging
import random
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger: logging.Logger = logging.getLogger(__name__)

from planner.genre_loader import load_genre_template
from planner.plannertypes import CadencePoint, SchemaSlot, TonalSection
from planner.schema_loader import (
    get_allowed_next,
    get_cadential_schemas,
    get_opening_schemas,
    get_schema,
    get_sequential_schemas,
    get_typical_position,
    schema_fits_bars,
)
from shared.constants import DUX_VOICES, SCHEMA_TEXTURES, SCHEMA_TREATMENTS


DATA_DIR: Path = Path(__file__).parent.parent / "data"


@lru_cache(maxsize=1)
def _load_schema_transitions() -> dict[str, Any]:
    """Load schema transitions YAML (cached)."""
    path = DATA_DIR / "schemas" / "schema_transitions.yaml"
    assert path.exists(), f"Schema transitions file not found: {path}"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_schema_preferences(genre: str) -> dict[str, list[str]]:
    """Get schema preferences for a genre.

    Uses load_genre_template which merges genre-specific over _default.yaml.

    Returns:
        Dict with keys: opening, riposte, continuation, pre_cadential, cadential
    """
    genre_data = load_genre_template(genre=genre)
    return genre_data["schema_preferences"]


def get_genre_texture(genre: str) -> str:
    """Get default texture for a genre.

    Uses load_genre_template which merges genre-specific over _default.yaml.

    Returns:
        Texture string: imitative, melody_bass, or free
    """
    genre_data = load_genre_template(genre=genre)
    return genre_data["texture"]


def select_schema_for_position(
    position: str,
    prev_schema: str | None,
    available_bars: int,
    history: list[str],
    genre_prefs: dict[str, list[str]],
    rng: random.Random,
) -> tuple[str, int]:
    """Select a schema and bar count for a position.

    Args:
        position: 'opening', 'continuation', or 'cadential'
        prev_schema: Previous schema name (for transition validation)
        available_bars: Maximum bars this schema can span
        history: List of previously selected schema names
        genre_prefs: Genre schema preferences
        rng: Random number generator

    Returns:
        (schema_name, bars) tuple
    """
    # Get candidates based on position
    if position == "opening":
        candidates = genre_prefs.get("opening", get_opening_schemas())
    elif position == "cadential":
        candidates = genre_prefs.get("cadential", get_cadential_schemas())
    else:
        candidates = genre_prefs.get("continuation", get_sequential_schemas())

    # Filter by transition validity (if not opening)
    if prev_schema is not None:
        allowed = set(get_allowed_next(schema_name=prev_schema))
        candidates = [c for c in candidates if c in allowed]

    # Filter by bar fit
    candidates = [c for c in candidates if schema_fits_bars(schema_name=c, available_bars=available_bars)]

    # Soft constraint: prefer schemas not repeated more than twice
    schema_counts = {s: history.count(s) for s in set(history)}
    preferred = [c for c in candidates if schema_counts.get(c, 0) < 2]
    if preferred:
        candidates = preferred

    # Broadened search: if no candidates from genre prefs, try any schema
    if not candidates:
        logger.warning(
            "No genre-preferred schema for position=%s, prev=%s, "
            "available_bars=%d; broadening to all schemas",
            position, prev_schema, available_bars,
        )
        all_schemas = get_opening_schemas() + get_sequential_schemas() + get_cadential_schemas()
        if prev_schema:
            allowed = set(get_allowed_next(schema_name=prev_schema))
            candidates = [s for s in all_schemas if s in allowed and schema_fits_bars(schema_name=s, available_bars=available_bars)]
        if not candidates:
            candidates = [s for s in all_schemas if schema_fits_bars(schema_name=s, available_bars=available_bars)]

    assert candidates, (
        f"No valid schema found for position={position}, prev={prev_schema}, "
        f"available_bars={available_bars}"
    )

    # Select randomly from candidates
    schema_name = rng.choice(candidates)

    # Determine bar count within schema's range, constrained by available
    schema = get_schema(name=schema_name)
    min_bars = schema.min_bars
    max_bars = min(schema.max_bars, available_bars)

    # Prefer 2 bars if in range, else max available within range
    if min_bars <= 2 <= max_bars:
        bars = 2
    else:
        bars = max_bars

    return schema_name, bars


def assign_treatment(
    schema_type: str,
    position_in_section: int,
    total_in_section: int,
    texture: str,
) -> str:
    """Assign contrapuntal treatment from 5-option vocabulary.

    Rules:
    - First schema in section: statement
    - Second in imitative texture: imitation
    - Sequential schemas (fonte, monte): sequence
    - After midpoint with imitative texture: may use inversion/stretto

    Args:
        schema_type: Schema name
        position_in_section: 0-indexed position of this schema in section
        total_in_section: Total schemas planned for section
        texture: Texture type

    Returns:
        Treatment string from SCHEMA_TREATMENTS
    """
    # Check if schema is sequential
    schema = get_schema(name=schema_type)
    is_sequential = schema.sequential

    # First schema: statement
    if position_in_section == 0:
        return "statement"

    # Second schema in imitative: imitation
    if position_in_section == 1 and texture == "imitative":
        return "imitation"

    # Sequential schemas: transposition treatment
    if is_sequential:
        return "transposition"

    # Later positions in imitative: consider inversion/stretto
    if texture == "imitative":
        midpoint = total_in_section // 2
        if position_in_section > midpoint:
            # Stretto near end for climactic effect
            if position_in_section >= total_in_section - 2:
                return "stretto"
            return "inversion"

    # Default: statement
    return "statement"


def assign_dux_voice(
    position_in_section: int,
    texture: str,
    prev_dux_voice: str | None,
) -> str:
    """Determine which voice presents the subject first (dux voice).

    Rules:
    - First entry: soprano (conventional)
    - Subsequent in imitative: alternate soprano/bass

    Args:
        position_in_section: 0-indexed position
        texture: Texture type
        prev_dux_voice: Previous dux voice (for alternation)

    Returns:
        Dux voice: 'soprano' or 'bass'
    """
    if position_in_section == 0:
        return "soprano"

    if texture == "imitative" and prev_dux_voice:
        # Alternate voices
        return "bass" if prev_dux_voice == "soprano" else "soprano"

    # Default: soprano
    return "soprano"


def _compute_stretto_overlap(
    treatment: str,
    bar_duration: Fraction,
    rng: random.Random,
) -> Fraction | None:
    """Compute stretto overlap amount for stretto treatment.

    Args:
        treatment: Treatment type
        bar_duration: Duration of one bar in whole notes
        rng: Random number generator

    Returns:
        Overlap in whole notes, or None if not stretto treatment
    """
    if treatment != "stretto":
        return None

    # Overlap is typically 1-2 beats in 4/4
    # For other metres, scale proportionally
    min_overlap = Fraction(1, 4)  # 1 beat minimum
    max_overlap = bar_duration / 2  # Half bar maximum

    # Choose randomly within range
    options = [Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)]
    valid_options = [o for o in options if min_overlap <= o <= max_overlap]

    if not valid_options:
        return min_overlap

    return rng.choice(valid_options)


def _compute_sequence_reps(
    treatment: str,
    slot_bars: int,
    schema_bars: int,
    rng: random.Random,
) -> int | None:
    """Compute number of sequence repetitions.

    Args:
        treatment: Treatment type
        slot_bars: Total bars in slot
        schema_bars: Base bars of schema
        rng: Random number generator

    Returns:
        Number of repetitions, or None if not sequence treatment
    """
    if treatment != "transposition":
        return None

    # Number of times the head repeats
    # Head is ~1 bar, so repetitions = slot_bars approximately
    return max(2, slot_bars)  # At least 2 repetitions for audible sequence


def generate_schema_chain(
    tonal_sections: tuple[TonalSection, ...],
    cadence_plan: tuple[CadencePoint, ...],
    genre: str,
    mode: str,
    total_bars: int,
    seed: int | None = None,
) -> tuple[SchemaSlot, ...]:
    """Generate complete schema chain for piece with key area propagation.

    Algorithm:
    1. Start with opening schema
    2. Fill each tonal section with schemas using allowed_next transitions
    3. Approach each cadence with pre-cadential schema
    4. Assign texture per genre
    5. Assign treatment per position in section
    6. Propagate key_area from TonalSection to each SchemaSlot

    Args:
        tonal_sections: Tuple of TonalSection from tonal_planner
        cadence_plan: Tuple of CadencePoint from cadence_planner
        genre: Genre name for preferences
        mode: 'major' or 'minor'
        total_bars: Total bars in piece
        seed: Random seed for reproducibility

    Returns:
        Tuple of SchemaSlot covering all bars with key_area set
    """
    assert tonal_sections, "tonal_sections cannot be empty"
    assert cadence_plan, "cadence_plan cannot be empty"
    assert total_bars > 0, f"total_bars must be positive, got {total_bars}"

    rng = random.Random(seed)
    genre_prefs = get_schema_preferences(genre=genre)
    texture = get_genre_texture(genre=genre)

    slots: list[SchemaSlot] = []
    history: list[str] = []
    current_bar = 1
    prev_schema: str | None = None
    prev_dux_voice: str | None = None

    # Build cadence lookup by bar
    cadence_by_bar: dict[int, CadencePoint] = {cp.bar: cp for cp in cadence_plan}

    # Process each tonal section
    for section_idx, tonal_section in enumerate(tonal_sections):
        section_start = tonal_section.start_bar
        section_end = tonal_section.end_bar
        section_bars = section_end - section_start + 1
        key_area = tonal_section.key_area

        # Find cadence for this section (at section end)
        cadence = cadence_by_bar.get(section_end)

        # Estimate schemas needed for this section
        estimated_schemas = max(1, section_bars // 2)

        # Generate schemas for this section
        section_slots: list[SchemaSlot] = []
        remaining_bars = section_bars

        while remaining_bars > 0:
            # Determine position type
            is_first = len(section_slots) == 0
            is_approaching_cadence = remaining_bars <= 2

            if is_first and current_bar == 1:
                position = "opening"
            elif is_approaching_cadence:
                position = "cadential"
            else:
                position = "continuation"

            # Select schema
            schema_name, bars = select_schema_for_position(
                position=position,
                prev_schema=prev_schema,
                available_bars=remaining_bars,
                history=history,
                genre_prefs=genre_prefs,
                rng=rng,
            )

            # Determine if this schema lands on the cadence
            lands_on_cadence = cadence is not None and (current_bar + bars - 1) == section_end

            # Assign treatment
            treatment = assign_treatment(
                schema_type=schema_name,
                position_in_section=len(section_slots),
                total_in_section=estimated_schemas,
                texture=texture,
            )

            # Assign dux voice
            dux_voice = assign_dux_voice(
                position_in_section=len(section_slots),
                texture=texture,
                prev_dux_voice=prev_dux_voice,
            )

            # Get schema base bars for sequence calculation
            schema = get_schema(name=schema_name)
            schema_bars = schema.min_bars

            # Compute stretto overlap and sequence repetitions
            # Use Fraction(1, 1) as default bar_duration (4/4 time)
            bar_duration = Fraction(1, 1)
            stretto_overlap = _compute_stretto_overlap(treatment=treatment, bar_duration=bar_duration, rng=rng)
            sequence_reps = _compute_sequence_reps(treatment=treatment, slot_bars=bars, schema_bars=schema_bars, rng=rng)

            # Create slot with key_area from tonal section
            slot = SchemaSlot(
                type=schema_name,
                bars=bars,
                texture=texture,
                treatment=treatment,
                dux_voice=dux_voice,
                cadence=cadence.type if lands_on_cadence else None,
                key_area=key_area,
                stretto_overlap_beats=stretto_overlap,
                sequence_repetitions=sequence_reps,
            )

            section_slots.append(slot)
            history.append(schema_name)
            prev_schema = schema_name
            prev_dux_voice = dux_voice
            current_bar += bars
            remaining_bars -= bars

        slots.extend(section_slots)

    return tuple(slots)


def compute_actual_bars(schema_chain: tuple[SchemaSlot, ...]) -> int:
    """Compute total bars from schema chain.

    Args:
        schema_chain: Tuple of SchemaSlot

    Returns:
        Total bar count
    """
    return sum(slot.bars for slot in schema_chain)
