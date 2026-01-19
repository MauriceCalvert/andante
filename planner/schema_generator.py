"""Schema chain generation: fill bars between cadences with schemas.

The schema chain is the "harmonic DNA" of the piece. Schemas are selected
from the transition graph to land on cadence points, with texture and
treatment assigned per genre conventions.
"""
import random
from pathlib import Path
from typing import Any

import yaml

from planner.plannertypes import CadencePoint, SchemaSlot
from planner.schema_loader import (
    get_allowed_next,
    get_cadential_schemas,
    get_opening_schemas,
    get_schema,
    get_sequential_schemas,
    get_typical_position,
    schema_fits_bars,
)
from shared.constants import SCHEMA_TEXTURES, SCHEMA_TREATMENTS, VOICE_ENTRIES


DATA_DIR: Path = Path(__file__).parent.parent / "data"

# Default schema preferences by genre (used when genre YAML lacks schema_preferences)
DEFAULT_SCHEMA_PREFERENCES: dict[str, dict[str, list[str]]] = {
    "invention": {
        "opening": ["romanesca", "do_re_mi"],
        "continuation": ["fonte", "monte", "fenaroli"],
        "cadential": ["prinner", "sol_fa_mi"],
    },
    "minuet": {
        "opening": ["do_re_mi", "romanesca"],
        "continuation": ["fonte"],
        "cadential": ["prinner"],
    },
    "gavotte": {
        "opening": ["romanesca", "do_re_mi"],
        "continuation": ["fonte", "monte"],
        "cadential": ["prinner", "sol_fa_mi"],
    },
    "sarabande": {
        "opening": ["romanesca"],
        "continuation": ["fonte"],
        "cadential": ["prinner"],
    },
    "bourree": {
        "opening": ["do_re_mi", "romanesca"],
        "continuation": ["fonte", "monte"],
        "cadential": ["prinner"],
    },
    "fantasia": {
        "opening": ["romanesca", "do_re_mi", "meyer"],
        "continuation": ["fonte", "monte", "fenaroli"],
        "cadential": ["prinner", "sol_fa_mi"],
    },
    "chorale": {
        "opening": ["do_re_mi"],
        "continuation": ["fenaroli"],
        "cadential": ["prinner", "sol_fa_mi"],
    },
    "trio_sonata": {
        "opening": ["romanesca", "do_re_mi"],
        "continuation": ["fonte", "monte"],
        "cadential": ["prinner", "sol_fa_mi"],
    },
}

# Fallback preferences
FALLBACK_PREFERENCES: dict[str, list[str]] = {
    "opening": ["romanesca", "do_re_mi"],
    "continuation": ["fonte", "monte"],
    "cadential": ["prinner", "sol_fa_mi"],
}

# Default textures by genre
DEFAULT_TEXTURES: dict[str, str] = {
    "invention": "imitative",
    "minuet": "melody_bass",
    "gavotte": "melody_bass",
    "sarabande": "melody_bass",
    "bourree": "melody_bass",
    "fantasia": "imitative",
    "chorale": "free",
    "trio_sonata": "imitative",
}


def _load_genre_yaml(genre: str) -> dict[str, Any]:
    """Load genre YAML file if it exists."""
    path = DATA_DIR / "genres" / f"{genre}.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_schema_preferences(genre: str) -> dict[str, list[str]]:
    """Get schema preferences for a genre.

    Priority:
    1. schema_preferences field in genre YAML (if present)
    2. DEFAULT_SCHEMA_PREFERENCES lookup
    3. FALLBACK_PREFERENCES

    Returns:
        Dict with keys: opening, continuation, cadential
    """
    genre_data = _load_genre_yaml(genre)

    if "schema_preferences" in genre_data:
        return genre_data["schema_preferences"]

    if genre in DEFAULT_SCHEMA_PREFERENCES:
        return DEFAULT_SCHEMA_PREFERENCES[genre]

    return FALLBACK_PREFERENCES


def get_genre_texture(genre: str) -> str:
    """Get default texture for a genre.

    Returns:
        Texture string: imitative, melody_bass, or free
    """
    genre_data = _load_genre_yaml(genre)

    if "texture" in genre_data:
        return genre_data["texture"]

    return DEFAULT_TEXTURES.get(genre, "imitative")


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
        allowed = set(get_allowed_next(prev_schema))
        candidates = [c for c in candidates if c in allowed]

    # Filter by bar fit
    candidates = [c for c in candidates if schema_fits_bars(c, available_bars)]

    # Soft constraint: prefer schemas not repeated more than twice
    schema_counts = {s: history.count(s) for s in set(history)}
    preferred = [c for c in candidates if schema_counts.get(c, 0) < 2]
    if preferred:
        candidates = preferred

    # Fallback: if no candidates, try any schema that fits
    if not candidates:
        all_schemas = get_opening_schemas() + get_sequential_schemas() + get_cadential_schemas()
        if prev_schema:
            allowed = set(get_allowed_next(prev_schema))
            candidates = [s for s in all_schemas if s in allowed and schema_fits_bars(s, available_bars)]
        if not candidates:
            candidates = [s for s in all_schemas if schema_fits_bars(s, available_bars)]

    assert candidates, (
        f"No valid schema found for position={position}, prev={prev_schema}, "
        f"available_bars={available_bars}"
    )

    # Select randomly from candidates
    schema_name = rng.choice(candidates)

    # Determine bar count: prefer 2 bars, but can use 1 or match available
    schema = get_schema(schema_name)
    base_bars = schema.bars

    # Try 2 bars first (common case), then 1, then available
    possible_bars = []
    for mult in [2, 1, 4]:
        target = base_bars * mult
        if target <= available_bars:
            possible_bars.append(target)

    # Default to base_bars if nothing works
    if not possible_bars:
        possible_bars = [base_bars]

    # Prefer larger bar counts for smoother flow
    bars = max(possible_bars)

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
    schema = get_schema(schema_type)
    is_sequential = schema.sequential

    # First schema: statement
    if position_in_section == 0:
        return "statement"

    # Second schema in imitative: imitation
    if position_in_section == 1 and texture == "imitative":
        return "imitation"

    # Sequential schemas: sequence treatment
    if is_sequential:
        return "sequence"

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


def assign_voice_entry(
    position_in_section: int,
    texture: str,
    prev_voice_entry: str | None,
) -> str:
    """Determine which voice carries the subject.

    Rules:
    - First entry: soprano (conventional)
    - Subsequent in imitative: alternate soprano/bass

    Args:
        position_in_section: 0-indexed position
        texture: Texture type
        prev_voice_entry: Previous voice entry (for alternation)

    Returns:
        Voice entry: 'soprano' or 'bass'
    """
    if position_in_section == 0:
        return "soprano"

    if texture == "imitative" and prev_voice_entry:
        # Alternate voices
        return "bass" if prev_voice_entry == "soprano" else "soprano"

    # Default: soprano
    return "soprano"


def generate_schema_chain(
    cadence_plan: tuple[CadencePoint, ...],
    genre: str,
    mode: str,
    total_bars: int,
    seed: int | None = None,
) -> tuple[SchemaSlot, ...]:
    """Generate complete schema chain for piece.

    Algorithm:
    1. Start with opening schema
    2. Fill space between cadences using allowed_next transitions
    3. Approach each cadence with pre-cadential schema
    4. Assign texture per genre
    5. Assign treatment per position in section

    Args:
        cadence_plan: Tuple of CadencePoint from cadence_planner
        genre: Genre name for preferences
        mode: 'major' or 'minor'
        total_bars: Total bars in piece
        seed: Random seed for reproducibility

    Returns:
        Tuple of SchemaSlot covering all bars
    """
    assert cadence_plan, "cadence_plan cannot be empty"
    assert total_bars > 0, f"total_bars must be positive, got {total_bars}"

    rng = random.Random(seed)
    genre_prefs = get_schema_preferences(genre)
    texture = get_genre_texture(genre)

    slots: list[SchemaSlot] = []
    history: list[str] = []
    current_bar = 1
    prev_schema: str | None = None
    prev_voice_entry: str | None = None

    # Process each section (delimited by cadences)
    cadence_bars = [cp.bar for cp in cadence_plan]
    section_start = 1
    section_idx = 0

    for cadence_idx, cadence in enumerate(cadence_plan):
        section_end = cadence.bar
        section_bars = section_end - section_start + 1

        # Estimate schemas needed for this section
        # Rough estimate: 2 bars per schema
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
            lands_on_cadence = (current_bar + bars - 1) == section_end

            # Assign treatment and voice entry
            treatment = assign_treatment(
                schema_type=schema_name,
                position_in_section=len(section_slots),
                total_in_section=estimated_schemas,
                texture=texture,
            )

            voice_entry = assign_voice_entry(
                position_in_section=len(section_slots),
                texture=texture,
                prev_voice_entry=prev_voice_entry,
            )

            # Create slot
            slot = SchemaSlot(
                type=schema_name,
                bars=bars,
                texture=texture,
                treatment=treatment,
                voice_entry=voice_entry,
                cadence=cadence.type if lands_on_cadence else None,
            )

            section_slots.append(slot)
            history.append(schema_name)
            prev_schema = schema_name
            prev_voice_entry = voice_entry
            current_bar += bars
            remaining_bars -= bars

        slots.extend(section_slots)
        section_start = section_end + 1
        section_idx += 1

    return tuple(slots)


def compute_actual_bars(schema_chain: tuple[SchemaSlot, ...]) -> int:
    """Compute total bars from schema chain.

    Args:
        schema_chain: Tuple of SchemaSlot

    Returns:
        Total bar count
    """
    return sum(slot.bars for slot in schema_chain)
