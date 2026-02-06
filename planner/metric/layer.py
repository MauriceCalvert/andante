"""Layer 4: Metric planning orchestration.

Generates bar assignments and hierarchical anchors from SchemaChain.
Three anchor levels:
  1. Piece-level: tonic departure and return
  2. Section-level: cadence targets
  3. Phrase-level: schema stage arrivals (delegated to schema_anchors.py)
"""
from fractions import Fraction

from builder.types import (
    Anchor,
    FormConfig,
    GenreConfig,
    KeyConfig,
    SchemaChain,
    TonalPlan,
)
from shared.schema_types import Schema
from planner.metric.distribution import bar_beat_to_float
from planner.metric.schema_anchors import compute_upbeat_bar_beat, generate_schema_anchors
from shared.constants import CADENCE_DEGREES
from shared.key import Key
from shared.tracer import get_tracer


def get_schema_stages(
    schema_name: str,
    schemas: dict[str, Schema],
    metre: str | None = None,
) -> int:
    """Get number of bars a schema occupies (1 stage = 1 bar)."""
    if schema_name not in schemas or schema_name == "episode":
        return 0
    from builder.cadence_writer import get_schema_bars
    return get_schema_bars(
        schema_name=schema_name,
        schema_def=schemas[schema_name],
        metre=metre,
    )


def layer_4_metric(
    schema_chain: SchemaChain,
    genre_config: GenreConfig,
    form_config: FormConfig,
    key_config: KeyConfig | None = None,
    schemas: dict[str, Schema] | None = None,
    tonal_plan: TonalPlan | dict | None = None,
    answer_interval: int = 7,
    modality: str = "diatonic",
) -> tuple[dict[str, tuple[int, int]], list[Anchor], int]:
    """Execute Layer 4 metric planning."""
    tracer = get_tracer()
    if schemas is None:
        schemas = {}
    tonal_plan_obj: TonalPlan | None = tonal_plan if isinstance(tonal_plan, TonalPlan) else None
    tonal_plan_dict: dict[str, tuple[str, ...]] = _tonal_plan_to_dict(
        tonal_plan=tonal_plan,
    )
    bar_assignments: dict[str, tuple[int, int]] = _build_bar_assignments(
        schema_chain=schema_chain,
        genre_config=genre_config,
        schemas=schemas,
    )
    total_bars: int = max(end for _, end in bar_assignments.values()) if bar_assignments else 0
    if key_config is None:
        return bar_assignments, [], total_bars
    key: Key = _key_config_to_key(key_config=key_config)
    if tonal_plan_dict is None:
        tonal_plan_dict = {}
    anchors: list[Anchor] = _generate_all_anchors(
        schema_chain=schema_chain,
        genre_config=genre_config,
        schemas=schemas,
        home_key=key,
        tonal_plan_dict=tonal_plan_dict,
        tonal_plan_obj=tonal_plan_obj,
        answer_interval=answer_interval,
        modality=modality,
        bar_assignments=bar_assignments,
        total_bars=total_bars,
    )
    anchors.sort(key=lambda a: (bar_beat_to_float(bar_beat=a.bar_beat), a.upper_degree))
    anchors = _deduplicate_anchors(anchors=anchors)
    for a in anchors:
        tracer.anchor(bar_beat=a.bar_beat, upper=a.upper_degree, lower=a.lower_degree, key=a.local_key.tonic, schema=a.schema, stage=a.stage, section=a.section)
    return bar_assignments, anchors, total_bars


def _tonal_plan_to_dict(
    tonal_plan: TonalPlan | dict | None,
) -> dict[str, tuple[str, ...]]:
    """Convert tonal plan to legacy dict format for backward compatibility."""
    if tonal_plan is None:
        return {}
    if isinstance(tonal_plan, dict):
        return tonal_plan
    result: dict[str, tuple[str, ...]] = {}
    for section in tonal_plan.sections:
        result[section.name] = (section.key_area,)
    return result


def _build_bar_assignments(
    schema_chain: SchemaChain,
    genre_config: GenreConfig,
    schemas: dict[str, Schema],
) -> dict[str, tuple[int, int]]:
    """Build bar assignments from SchemaChain and section boundaries."""
    if not schema_chain.section_boundaries:
        return _build_bar_assignments_legacy(
            genre_config=genre_config,
            schemas=schemas,
        )
    assignments: dict[str, tuple[int, int]] = {}
    current_bar: int = 1
    prev_boundary: int = 0
    is_first_section: bool = True
    for section_idx, section in enumerate(genre_config.sections):
        section_name: str = section["name"]
        boundary: int = schema_chain.section_boundaries[section_idx] if section_idx < len(schema_chain.section_boundaries) else len(schema_chain.schemas)
        section_schemas: tuple[str, ...] = schema_chain.schemas[prev_boundary:boundary]
        section_bars: int = sum(
            get_schema_stages(schema_name=name, schemas=schemas, metre=genre_config.metre)
            for name in section_schemas
        )
        if section_bars == 0:
            section_bars = 1
        start_bar: int = current_bar
        end_bar: int = current_bar + section_bars - 1
        if is_first_section and genre_config.upbeat > 0:
            end_bar -= 1
        assignments[section_name] = (start_bar, end_bar)
        current_bar = end_bar + 1
        prev_boundary = boundary
        is_first_section = False
    return assignments


def _build_bar_assignments_legacy(
    genre_config: GenreConfig,
    schemas: dict[str, Schema],
) -> dict[str, tuple[int, int]]:
    """Legacy bar assignment from genre_config sections (backward compat)."""
    assignments: dict[str, tuple[int, int]] = {}
    current_bar: int = 1
    is_first_section: bool = True
    for section in genre_config.sections:
        section_name: str = section["name"]
        schema_sequence: list[str] = section.get("schema_sequence", [])
        section_bars: int = sum(
            get_schema_stages(schema_name=name, schemas=schemas, metre=genre_config.metre)
            for name in schema_sequence
        )
        assert section_bars > 0, f"Section '{section_name}' has no stages"
        start_bar: int = current_bar
        end_bar: int = current_bar + section_bars - 1
        if is_first_section and genre_config.upbeat > 0:
            end_bar -= 1
        assignments[section_name] = (start_bar, end_bar)
        current_bar = end_bar + 1
        is_first_section = False
    return assignments


def _generate_all_anchors(
    schema_chain: SchemaChain,
    genre_config: GenreConfig,
    schemas: dict[str, Schema],
    home_key: Key,
    tonal_plan_dict: dict[str, tuple[str, ...]],
    tonal_plan_obj: TonalPlan | None,
    answer_interval: int,
    modality: str,
    bar_assignments: dict[str, tuple[int, int]],
    total_bars: int,
) -> list[Anchor]:
    """Generate all three levels of anchors."""
    anchors: list[Anchor] = []
    # Level 1: Piece-level anchors
    piece_anchors: list[Anchor] = _generate_piece_anchors(
        home_key=home_key,
        total_bars=total_bars,
        metre=genre_config.metre,
        upbeat=genre_config.upbeat,
    )
    anchors.extend(piece_anchors)
    # Level 2: Section-level anchors (cadence targets)
    if tonal_plan_obj is not None:
        section_anchors: list[Anchor] = _generate_section_anchors_from_plan(
            tonal_plan=tonal_plan_obj,
            home_key=home_key,
            bar_assignments=bar_assignments,
        )
        anchors.extend(section_anchors)
    # Level 3: Phrase-level anchors (schema stages)
    phrase_anchors: list[Anchor] = _generate_phrase_anchors(
        schema_chain=schema_chain,
        genre_config=genre_config,
        schemas=schemas,
        home_key=home_key,
        tonal_plan_dict=tonal_plan_dict,
        answer_interval=answer_interval,
        modality=modality,
        bar_assignments=bar_assignments,
    )
    anchors.extend(phrase_anchors)
    return anchors


def _generate_piece_anchors(
    home_key: Key,
    total_bars: int,
    metre: str,
    upbeat: Fraction,
) -> list[Anchor]:
    """Level 1: piece start and end anchors."""
    if total_bars < 1:
        return []
    start_bar, start_beat = compute_upbeat_bar_beat(
        start_bar=1,
        upbeat=upbeat,
        metre=metre,
    )
    return [
        Anchor(
            bar_beat=f"{start_bar}.{start_beat}",
            upper_degree=1,
            lower_degree=1,
            local_key=home_key,
            schema="piece_start",
            stage=1,
            section="piece",
        ),
        Anchor(
            bar_beat=f"{total_bars}.1",
            upper_degree=1,
            lower_degree=1,
            local_key=home_key,
            schema="piece_end",
            stage=1,
            section="piece",
        ),
    ]


def _generate_section_anchors_from_plan(
    tonal_plan: TonalPlan,
    home_key: Key,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[Anchor]:
    """Level 2: section cadence target anchors."""
    anchors: list[Anchor] = []
    for section in tonal_plan.sections:
        if section.name not in bar_assignments:
            continue
        _, end_bar = bar_assignments[section.name]
        cadence_type: str = section.cadence_type
        degrees: tuple[int, int] = CADENCE_DEGREES.get(cadence_type, (1, 1))
        soprano_deg: int = degrees[0]
        bass_deg: int = degrees[1]
        section_key: Key = home_key
        if section.key_area != "I":
            section_key = home_key.modulate_to(target=section.key_area)
        anchors.append(Anchor(
            bar_beat=f"{end_bar}.1",
            upper_degree=soprano_deg,
            lower_degree=bass_deg,
            local_key=section_key if cadence_type != "authentic" else home_key,
            schema=f"section_cadence_{cadence_type}",
            stage=1,
            upper_direction="down" if soprano_deg < 5 else None,
            lower_direction="up" if bass_deg == 1 else None,
            section=section.name,
        ))
    return anchors


def _generate_phrase_anchors(
    schema_chain: SchemaChain,
    genre_config: GenreConfig,
    schemas: dict[str, Schema],
    home_key: Key,
    tonal_plan_dict: dict[str, tuple[str, ...]],
    answer_interval: int,
    modality: str,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[Anchor]:
    """Level 3: phrase-level schema stage anchors."""
    if schema_chain.section_boundaries:
        return _phrase_anchors_from_chain(
            schema_chain=schema_chain,
            genre_config=genre_config,
            schemas=schemas,
            home_key=home_key,
            tonal_plan_dict=tonal_plan_dict,
            answer_interval=answer_interval,
            modality=modality,
            bar_assignments=bar_assignments,
        )
    return _phrase_anchors_legacy(
        genre_config=genre_config,
        schemas=schemas,
        home_key=home_key,
        tonal_plan_dict=tonal_plan_dict,
        answer_interval=answer_interval,
        modality=modality,
        bar_assignments=bar_assignments,
    )


def _phrase_anchors_from_chain(
    schema_chain: SchemaChain,
    genre_config: GenreConfig,
    schemas: dict[str, Schema],
    home_key: Key,
    tonal_plan_dict: dict[str, tuple[str, ...]],
    answer_interval: int,
    modality: str,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[Anchor]:
    """Generate phrase anchors from SchemaChain with section boundaries."""
    anchors: list[Anchor] = []
    prev_boundary: int = 0
    is_first_section: bool = True
    for section_idx, section in enumerate(genre_config.sections):
        section_name: str = section["name"]
        if section_name not in bar_assignments:
            continue
        boundary: int = schema_chain.section_boundaries[section_idx] if section_idx < len(schema_chain.section_boundaries) else len(schema_chain.schemas)
        section_schemas: list[str] = list(schema_chain.schemas[prev_boundary:boundary])
        start_bar: int = bar_assignments[section_name][0]
        key_areas: tuple[str, ...] = tonal_plan_dict.get(section_name, ("I",))
        is_exordium: bool = section_name == "exordium"
        section_upbeat: Fraction = genre_config.upbeat if is_first_section else Fraction(0)
        current_bar: int = start_bar
        is_first_schema: bool = True
        for i, schema_name in enumerate(section_schemas):
            if schema_name not in schemas:
                continue
            schema_def: Schema = schemas[schema_name]
            stages: int = get_schema_stages(schema_name=schema_name, schemas=schemas, metre=genre_config.metre)
            schema_end: int = current_bar + stages - 1
            local_key: Key = _get_local_key(
                home_key=home_key,
                schema_index=i,
                is_exordium=is_exordium,
                key_areas=key_areas,
                answer_interval=answer_interval,
                modality=modality,
            )
            schema_upbeat: Fraction = section_upbeat if is_first_schema else Fraction(0)
            if schema_upbeat > 0:
                schema_end -= 1
            schema_anchors: list[Anchor] = generate_schema_anchors(
                schema_name=schema_name,
                schema_def=schema_def,
                start_bar=current_bar,
                end_bar=schema_end,
                home_key=local_key,
                metre=genre_config.metre,
                upbeat=schema_upbeat,
                section=section_name,
                expected_stages=stages,
            )
            assert len(schema_anchors) == stages, (
                f"Schema '{schema_name}' produced {len(schema_anchors)} anchors "
                f"but was allocated {stages} bars (bars {current_bar}-{schema_end})"
            )
            anchors.extend(schema_anchors)
            current_bar = schema_end + 1
            is_first_schema = False
        prev_boundary = boundary
        is_first_section = False
    return anchors


def _phrase_anchors_legacy(
    genre_config: GenreConfig,
    schemas: dict[str, Schema],
    home_key: Key,
    tonal_plan_dict: dict[str, tuple[str, ...]],
    answer_interval: int,
    modality: str,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[Anchor]:
    """Legacy phrase anchor generation from genre_config sections."""
    anchors: list[Anchor] = []
    is_first_section: bool = True
    for section in genre_config.sections:
        section_name: str = section["name"]
        if section_name not in bar_assignments:
            continue
        start_bar: int = bar_assignments[section_name][0]
        schema_sequence: list[str] = section.get("schema_sequence", [])
        real_schemas: list[str] = [s for s in schema_sequence if s != "episode"]
        key_areas: tuple[str, ...] = tonal_plan_dict.get(section_name, ("I",))
        is_exordium: bool = section_name == "exordium"
        section_upbeat: Fraction = genre_config.upbeat if is_first_section else Fraction(0)
        current_bar: int = start_bar
        is_first_schema: bool = True
        for i, schema_name in enumerate(real_schemas):
            if schema_name not in schemas:
                continue
            schema_def: Schema = schemas[schema_name]
            stages: int = get_schema_stages(schema_name=schema_name, schemas=schemas, metre=genre_config.metre)
            schema_end: int = current_bar + stages - 1
            local_key: Key = _get_local_key(
                home_key=home_key,
                schema_index=i,
                is_exordium=is_exordium,
                key_areas=key_areas,
                answer_interval=answer_interval,
                modality=modality,
            )
            schema_upbeat: Fraction = section_upbeat if is_first_schema else Fraction(0)
            if schema_upbeat > 0:
                schema_end -= 1
            schema_anchors: list[Anchor] = generate_schema_anchors(
                schema_name=schema_name,
                schema_def=schema_def,
                start_bar=current_bar,
                end_bar=schema_end,
                home_key=local_key,
                metre=genre_config.metre,
                upbeat=schema_upbeat,
                section=section_name,
                expected_stages=stages,
            )
            assert len(schema_anchors) == stages, (
                f"Schema '{schema_name}' produced {len(schema_anchors)} anchors "
                f"but was allocated {stages} bars (bars {current_bar}-{schema_end})"
            )
            anchors.extend(schema_anchors)
            current_bar = schema_end + 1
            is_first_schema = False
        is_first_section = False
    return anchors


def _get_local_key(
    home_key: Key,
    schema_index: int,
    is_exordium: bool,
    key_areas: tuple[str, ...],
    answer_interval: int,
    modality: str,
) -> Key:
    """Determine local key for schema at given index."""
    if modality == "diatonic":
        return home_key
    if is_exordium and schema_index == 1:
        return home_key.modulate_to(target="V")
    if schema_index < len(key_areas):
        area: str = key_areas[schema_index]
        if area == "I":
            return home_key
        return home_key.modulate_to(target=area)
    area = key_areas[-1]
    if area == "I":
        return home_key
    return home_key.modulate_to(target=area)


def _deduplicate_anchors(anchors: list[Anchor]) -> list[Anchor]:
    """Remove anchors at duplicate bar_beat positions, keeping the most important."""
    seen: dict[str, Anchor] = {}
    for anchor in anchors:
        existing: Anchor | None = seen.get(anchor.bar_beat)
        if existing is None:
            seen[anchor.bar_beat] = anchor
        elif anchor.schema.startswith("piece_"):
            seen[anchor.bar_beat] = anchor  # piece boundaries enforce tonic, always win
        elif existing.schema.startswith("piece_"):
            pass  # keep piece boundary anchor
        elif anchor.schema.startswith("section_cadence"):
            seen[anchor.bar_beat] = anchor  # cadence targets take priority over schema
    result: list[Anchor] = list(seen.values())
    result.sort(key=lambda a: bar_beat_to_float(bar_beat=a.bar_beat))
    return result


def _key_config_to_key(key_config: KeyConfig) -> Key:
    """Convert KeyConfig to Key object."""
    parts: list[str] = key_config.name.split()
    tonic: str = parts[0]
    mode: str = parts[1].lower() if len(parts) > 1 else "major"
    return Key(tonic=tonic, mode=mode)
