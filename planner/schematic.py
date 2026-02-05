"""Layer 3: Schematic planning.

Generates schema chains via graph walk over schema_transitions.yaml.
Input: TonalPlan, GenreConfig, FormConfig, schemas dict
Output: SchemaChain with schemas, key areas, cadences, free passages

RNG lives here per A005; downstream is deterministic.
"""
import logging
from random import Random
from typing import Any

from builder.types import (
    FormConfig,
    GenreConfig,
    SchemaChain,
    SchemaConfig,
    SectionTonalPlan,
    TonalPlan,
)
from planner.schema_loader import (
    can_connect_direct,
    get_allowed_next,
    get_schema,
    get_schemas_by_position,
    load_schemas as load_schema_defs,
    schema_fits_bars,
)
from planner.variety import (
    OPENING_SCHEMAS,
    validate_no_adjacent_schema_repetition,
    validate_opening_placement,
)


logger = logging.getLogger(__name__)

# Position required for section function
_SECTION_POSITIONS: dict[str, tuple[str, ...]] = {
    "exordium": ("opening",),
    "narratio": ("continuation", "opening"),
    "confutatio": ("continuation",),
    "confirmatio": ("continuation", "opening"),
    "peroratio": ("pre_cadential", "cadential"),
    "coda": ("cadential", "post_cadential"),
    "episode": ("continuation",),
    "cadential": ("pre_cadential", "cadential"),
}

# Cadence type to required final schema position
_CADENCE_SCHEMA_POSITIONS: dict[str, tuple[str, ...]] = {
    "authentic": ("cadential",),
    "half": ("cadential",),
    "deceptive": ("cadential",),
    "open": ("continuation", "opening", "cadential"),
}


def layer_3_schematic(
    tonal_plan: TonalPlan,
    genre_config: GenreConfig,
    form_config: FormConfig,
    schemas: dict[str, SchemaConfig],
    seed: int = 42,
) -> SchemaChain:
    """Execute Layer 3: generate schema chain via graph walk."""
    rng: Random = Random(seed)
    schema_defs = load_schema_defs()
    all_schemas: list[str] = []
    all_key_areas: list[str] = []
    all_cadences: list[str | None] = []
    section_boundaries: list[int] = []
    for section_idx, section_plan in enumerate(tonal_plan.sections):
        genre_section: dict[str, Any] = _find_genre_section(
            genre_config=genre_config,
            section_name=section_plan.name,
        )
        bar_budget: int = _compute_section_bar_budget(
            genre_section=genre_section,
            schemas=schemas,
        )
        section_schemas: list[str] = _generate_section_schemas(
            section_plan=section_plan,
            bar_budget=bar_budget,
            schema_defs=schema_defs,
            rng=rng,
            is_first_section=section_idx == 0,
            is_final_section=section_idx == len(tonal_plan.sections) - 1,
        )
        for i, schema_name in enumerate(section_schemas):
            all_schemas.append(schema_name)
            all_key_areas.append(section_plan.key_area)
            is_last_in_section: bool = i == len(section_schemas) - 1
            all_cadences.append(section_plan.cadence_type if is_last_in_section else None)
        section_boundaries.append(len(all_schemas))
    free_passages: set[tuple[int, int]] = _mark_free_passages(
        schemas=all_schemas,
    )
    chain: SchemaChain = SchemaChain(
        schemas=tuple(all_schemas),
        key_areas=tuple(all_key_areas),
        free_passages=frozenset(free_passages),
        cadences=tuple(all_cadences),
        section_boundaries=tuple(section_boundaries),
    )
    _validate_chain(chain=chain)
    return chain


def _find_genre_section(
    genre_config: GenreConfig,
    section_name: str,
) -> dict[str, Any]:
    """Find genre section by name."""
    for section in genre_config.sections:
        if section.get("name") == section_name:
            return section
    assert False, (
        f"Section '{section_name}' not found in genre '{genre_config.name}'. "
        f"Available: {[s.get('name') for s in genre_config.sections]}"
    )


def _compute_section_bar_budget(
    genre_section: dict[str, Any],
    schemas: dict[str, SchemaConfig],
) -> int:
    """Compute bar budget from original schema sequence."""
    schema_sequence: list[str] = genre_section.get("schema_sequence", [])
    total: int = 0
    for name in schema_sequence:
        if name == "episode" or name not in schemas:
            continue
        schema_def: SchemaConfig = schemas[name]
        if schema_def.sequential:
            segments: tuple[int, ...] = schema_def.segments or (2,)
            total += max(segments) if isinstance(segments, (list, tuple)) else segments
        else:
            total += len(schema_def.soprano_degrees)
    assert total > 0, (
        f"Section '{genre_section.get('name')}' has zero bar budget. "
        f"Schema sequence: {schema_sequence}"
    )
    return total


def _generate_section_schemas(
    section_plan: SectionTonalPlan,
    bar_budget: int,
    schema_defs: dict,
    rng: Random,
    is_first_section: bool,
    is_final_section: bool,
) -> list[str]:
    """Generate schema sequence for a section via graph walk."""
    positions: tuple[str, ...] = _SECTION_POSITIONS.get(
        section_plan.name, ("continuation", "opening"),
    )
    opening_schema: str | None = _select_opening_schema(
        positions=positions,
        schema_defs=schema_defs,
        bar_budget=bar_budget,
        rng=rng,
    )
    assert opening_schema is not None, (
        f"No valid opening schema for section '{section_plan.name}' "
        f"with positions {positions} and budget {bar_budget} bars"
    )
    result: list[str] = [opening_schema]
    bars_used: int = _schema_bars(schema_name=opening_schema, schema_defs=schema_defs)
    max_iterations: int = 20
    iteration: int = 0
    while bars_used < bar_budget:
        assert iteration < max_iterations, (
            f"Schema walk exceeded {max_iterations} iterations for section "
            f"'{section_plan.name}'. Schemas so far: {result}, bars: {bars_used}/{bar_budget}"
        )
        iteration += 1
        remaining: int = bar_budget - bars_used
        next_schema: str | None = _select_next_schema(
            current=result[-1],
            remaining_bars=remaining,
            cadence_type=section_plan.cadence_type,
            schema_defs=schema_defs,
            previous_schemas=result,
            is_final_section=is_final_section,
            rng=rng,
        )
        if next_schema is None:
            break
        result.append(next_schema)
        bars_used += _schema_bars(schema_name=next_schema, schema_defs=schema_defs)
    return result


def _select_opening_schema(
    positions: tuple[str, ...],
    schema_defs: dict,
    bar_budget: int,
    rng: Random,
) -> str | None:
    """Select first schema for a section from valid positions."""
    candidates: list[str] = []
    for pos in positions:
        candidates.extend(get_schemas_by_position(position=pos))
    candidates = [
        c for c in candidates
        if c in schema_defs and _schema_bars(schema_name=c, schema_defs=schema_defs) <= bar_budget
    ]
    if not candidates:
        return None
    return rng.choice(candidates)


def _select_next_schema(
    current: str,
    remaining_bars: int,
    cadence_type: str,
    schema_defs: dict,
    previous_schemas: list[str],
    is_final_section: bool,
    rng: Random,
) -> str | None:
    """Select next schema from transitions graph."""
    allowed: list[str] = get_allowed_next(schema_name=current)
    candidates: list[str] = [
        s for s in allowed
        if s in schema_defs
        and _schema_bars(schema_name=s, schema_defs=schema_defs) <= remaining_bars
    ]
    if not candidates:
        return None
    # V-T001: no adjacent repetition
    candidates = [s for s in candidates if s != current]
    if not candidates:
        return None
    # V-T002: opening schemas only at section starts, not mid-section
    candidates = [s for s in candidates if s not in OPENING_SCHEMAS]
    if not candidates:
        return None
    # Prefer cadential schemas when near end and cadence required
    if remaining_bars <= 4 and cadence_type in ("authentic", "half"):
        cadential: list[str] = [
            s for s in candidates
            if _is_cadential_position(schema_name=s, schema_defs=schema_defs)
        ]
        if cadential:
            candidates = cadential
    # Prefer schemas not recently used (soft variety)
    recent: set[str] = set(previous_schemas[-3:]) if len(previous_schemas) >= 3 else set(previous_schemas)
    fresh: list[str] = [s for s in candidates if s not in recent]
    if fresh:
        candidates = fresh
    return rng.choice(candidates)


def _schema_bars(schema_name: str, schema_defs: dict) -> int:
    """Get minimum bar count for a schema."""
    schema = schema_defs[schema_name]
    if schema.sequential:
        return schema.segments
    return len(schema.soprano_degrees)


def _is_cadential_position(schema_name: str, schema_defs: dict) -> bool:
    """Check if schema is in cadential or pre-cadential position."""
    schema = schema_defs[schema_name]
    return schema.position in ("cadential", "pre_cadential")


def _mark_free_passages(schemas: list[str]) -> set[tuple[int, int]]:
    """Mark schema junctions that need free passages."""
    free: set[tuple[int, int]] = set()
    for i in range(len(schemas) - 1):
        if not can_connect_direct(from_schema=schemas[i], to_schema=schemas[i + 1]):
            free.add((i, i + 1))
    return free


def _validate_chain(chain: SchemaChain) -> None:
    """Validate schema chain against variety rules."""
    if len(chain.schemas) < 2:
        return
    validate_no_adjacent_schema_repetition(schemas=chain.schemas)
    validate_opening_placement(
        schemas=chain.schemas,
        section_boundaries=chain.section_boundaries,
    )
