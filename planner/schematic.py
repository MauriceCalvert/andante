"""Layer 3: Schematic planning.

Generates schema chains via graph walk over schema_transitions.yaml.
Input: TonalPlan, GenreConfig, FormConfig, schemas dict
Output: SchemaChain with schemas, key areas, cadences, free passages

RNG lives here per A005; downstream is deterministic.
"""
import logging
from random import Random
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)

from builder.types import (
    FormConfig,
    GenreConfig,
    SchemaChain,
    SectionTonalPlan,
    TonalPlan,
)
from shared.schema_types import Schema
from planner.schema_loader import (
    can_connect_direct,
    get_allowed_next,
    get_genre_preferred,
    get_schemas_by_position,
    load_schemas as load_schema_defs,
)
from planner.variety import (
    OPENING_SCHEMAS,
    validate_no_adjacent_schema_repetition,
    validate_opening_placement,
)



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
    schemas: dict[str, Schema],
    seed: int = 42,
) -> SchemaChain:
    """Execute Layer 3: generate schema chain via graph walk."""
    rng: Random = Random(seed)
    schema_defs = load_schema_defs()
    all_schemas: list[str] = []
    all_key_areas: list[str] = []
    all_cadences: list[str | None] = []
    section_boundaries: list[int] = []
    prev_destination: str = "I"
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
            genre_name=genre_config.name,
            genre_section=genre_section,
        )
        schema_key_areas: list[str] = _distribute_section_key_areas(
            schema_count=len(section_schemas),
            start_key_area=prev_destination,
            destination_key_area=section_plan.key_area,
        )
        for i, schema_name in enumerate(section_schemas):
            all_schemas.append(schema_name)
            all_key_areas.append(schema_key_areas[i])
            is_last_in_section: bool = i == len(section_schemas) - 1
            all_cadences.append(section_plan.cadence_type if is_last_in_section else None)
        section_boundaries.append(len(all_schemas))
        prev_destination = section_plan.key_area
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
    schemas: dict[str, Schema],
) -> int:
    """Compute bar budget from original schema sequence."""
    schema_sequence: list[str] = genre_section.get("schema_sequence", [])
    total: int = 0
    for name in schema_sequence:
        if name == "episode" or name not in schemas:
            continue
        schema_def: Schema = schemas[name]
        if schema_def.sequential:
            total += max(schema_def.segments)
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
    genre_name: str,
    genre_section: dict[str, Any] | None = None,
) -> list[str]:
    """Generate schema sequence for a section.

    Uses declared schema_sequence from genre section if available and valid.
    Falls back to graph walk otherwise.
    """
    # Phase 3: use declared schema_sequence if present and fully resolvable
    use_declared: bool = False
    if genre_section is not None:
        declared: list[str] = genre_section.get("schema_sequence", [])
        if declared:
            missing: list[str] = [s for s in declared if s not in schema_defs]
            if missing:
                logger.warning(
                    "Section '%s' schema_sequence has unknown schemas %s — "
                    "falling back to graph walk",
                    section_plan.name,
                    missing,
                )
            else:
                use_declared = True

    if use_declared:
        result: list[str] = list(declared)
        bars_used: int = sum(
            _schema_bars(schema_name=s, schema_defs=schema_defs)
            for s in declared
        )
    else:
        # Fallback: graph walk
        positions: tuple[str, ...] = _SECTION_POSITIONS.get(
            section_plan.name, ("continuation", "opening"),
        )
        opening_schema: str | None = _select_opening_schema(
            positions=positions,
            schema_defs=schema_defs,
            bar_budget=bar_budget,
            rng=rng,
            genre_name=genre_name,
        )
        assert opening_schema is not None, (
            f"No valid opening schema for section '{section_plan.name}' "
            f"with positions {positions} and budget {bar_budget} bars"
        )
        result = [opening_schema]
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
                genre_name=genre_name,
            )
            if next_schema is None:
                break
            result.append(next_schema)
            bars_used += _schema_bars(schema_name=next_schema, schema_defs=schema_defs)
    # Enforce minimum non-cadential schema count (11a: invention exordium)
    min_non_cad: int = 0
    if genre_section is not None:
        min_non_cad = genre_section.get("min_non_cadential", 0)
    if min_non_cad > 0:
        non_cad_count: int = sum(
            1 for s in result
            if schema_defs[s].position != "cadential"
        )
        while non_cad_count < min_non_cad:
            remaining: int = bar_budget - bars_used
            if remaining <= 0:
                logger.warning(
                    "Section '%s' min_non_cadential=%d: bar budget ran out with only %d non-cadential schemas",
                    section_plan.name, min_non_cad, non_cad_count,
                )
                break
            continuation_schema: str | None = _select_next_schema(
                current=result[-1],
                remaining_bars=remaining,
                cadence_type=section_plan.cadence_type,
                schema_defs=schema_defs,
                previous_schemas=result,
                is_final_section=is_final_section,
                rng=rng,
                genre_name=genre_name,
            )
            if continuation_schema is None:
                logger.warning(
                    "Section '%s' min_non_cadential=%d: no continuation schema can follow '%s' with %d bars left",
                    section_plan.name, min_non_cad, result[-1], remaining,
                )
                break
            result.append(continuation_schema)
            bars_used += _schema_bars(schema_name=continuation_schema, schema_defs=schema_defs)
            if schema_defs[continuation_schema].position != "cadential":
                non_cad_count += 1
    # Guarantee final cadential schema for sections that require it.
    # If the last schema is not cadential-position and cadence_type demands
    # one, pop the last schema and replace with a cadential match.
    if section_plan.cadence_type in ("authentic", "half"):
        last: str = result[-1]
        if not _is_final_cadence(
            schema_name=last,
            cadence_type=section_plan.cadence_type,
            schema_defs=schema_defs,
        ):
            assert len(result) >= 2, (
                f"Section '{section_plan.name}' has only one schema ({last}) "
                f"and it is not cadential — cannot guarantee final cadence"
            )
            popped: str = result.pop()
            popped_bars: int = _schema_bars(schema_name=popped, schema_defs=schema_defs)
            available: int = bar_budget - bars_used + popped_bars
            predecessor: str = result[-1]
            # Prefer cadential schemas reachable via the transition graph
            allowed: list[str] = get_allowed_next(schema_name=predecessor)
            cadential_candidates: list[str] = [
                s for s in allowed
                if s in schema_defs
                and _is_final_cadence(
                    schema_name=s,
                    cadence_type=section_plan.cadence_type,
                    schema_defs=schema_defs,
                )
                and _schema_bars(schema_name=s, schema_defs=schema_defs) <= available
            ]
            # Fallback: any fitting cadential schema (free passage will bridge)
            if not cadential_candidates:
                cadential_candidates = [
                    s for s in schema_defs
                    if _is_final_cadence(
                        schema_name=s,
                        cadence_type=section_plan.cadence_type,
                        schema_defs=schema_defs,
                    )
                    and _schema_bars(schema_name=s, schema_defs=schema_defs) <= available
                ]
            assert cadential_candidates, (
                f"No cadential schema fits section '{section_plan.name}' "
                f"(cadence_type='{section_plan.cadence_type}'). "
                f"Predecessor: {predecessor}, available: {available} bars, "
                f"allowed_next: {allowed}"
            )
            result.append(rng.choice(cadential_candidates))
    return result


def _select_opening_schema(
    positions: tuple[str, ...],
    schema_defs: dict,
    bar_budget: int,
    rng: Random,
    genre_name: str,
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
    # Soft genre preference: prefer genre-preferred opening schemas
    preferred: list[str] = get_genre_preferred(
        genre_name=genre_name,
        position="opening",
    )
    genre_candidates: list[str] = [c for c in candidates if c in preferred]
    if genre_candidates:
        return rng.choice(genre_candidates)
    return rng.choice(candidates)


def _select_next_schema(
    current: str,
    remaining_bars: int,
    cadence_type: str,
    schema_defs: dict,
    previous_schemas: list[str],
    is_final_section: bool,
    rng: Random,
    genre_name: str,
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
    # Hard filter: cadential and post-cadential schemas only eligible near
    # section end (remaining_bars <= 3). Pre-cadential schemas (passo_indietro,
    # indugio) are allowed mid-section — they prepare the cadential approach.
    # Soft guard: if all candidates are punctuation, fall back to unfiltered.
    if remaining_bars > 3:
        non_punctuation: list[str] = [
            s for s in candidates
            if schema_defs[s].position not in ("cadential", "post_cadential")
        ]
        if non_punctuation:
            candidates = non_punctuation
    # Prefer cadential schemas when near section end and cadence required
    if remaining_bars <= 3 and cadence_type in ("authentic", "half"):
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
    # Soft genre preference: prefer genre-preferred schemas for their position
    genre_candidates: list[str] = []
    for c in candidates:
        c_position: str = schema_defs[c].position
        preferred: list[str] = get_genre_preferred(
            genre_name=genre_name,
            position=c_position,
        )
        if c in preferred:
            genre_candidates.append(c)
    if genre_candidates:
        return rng.choice(genre_candidates)
    return rng.choice(candidates)


def _distribute_section_key_areas(
    schema_count: int,
    start_key_area: str,
    destination_key_area: str,
) -> list[str]:
    """Distribute key areas across schemas within a section.

    The section starts in start_key_area (inherited from previous section)
    and arrives at destination_key_area by the cadential schema.
    The cadence effects the modulation, so it and any post-cadential
    schemas are in the destination key.
    """
    assert schema_count > 0, "Cannot distribute key areas to zero schemas"
    if start_key_area == destination_key_area:
        return [start_key_area] * schema_count
    if schema_count == 1:
        return [destination_key_area]
    if schema_count == 2:
        return [start_key_area, destination_key_area]
    # Cadential + post-cadential schemas (last 2) get destination key;
    # departure schemas stay in start key
    dest_count: int = min(2, schema_count)
    return [start_key_area] * (schema_count - dest_count) + [destination_key_area] * dest_count


def _schema_bars(schema_name: str, schema_defs: dict) -> int:
    """Get minimum bar count for a schema."""
    schema = schema_defs[schema_name]
    if schema.sequential:
        return max(schema.segments)
    return len(schema.soprano_degrees)


def _is_cadential_position(schema_name: str, schema_defs: dict) -> bool:
    """Check if schema is in cadential or pre-cadential position."""
    schema = schema_defs[schema_name]
    return schema.position in ("cadential", "pre_cadential")


def _is_final_cadence(schema_name: str, cadence_type: str, schema_defs: dict) -> bool:
    """Check if schema qualifies as a section-final cadence.

    For authentic: cadential-position schemas except half_cadence
    (cadenza_semplice, cadenza_composta, comma).
    For half: only half_cadence.
    """
    schema = schema_defs[schema_name]
    if cadence_type == "half":
        return schema_name == "half_cadence"
    # authentic / deceptive: any cadential-position schema except half_cadence
    return schema.position == "cadential" and schema_name != "half_cadence"


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
