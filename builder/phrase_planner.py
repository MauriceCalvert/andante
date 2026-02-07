"""Phrase planner: converts Layer 4 output into PhrasePlan objects.

One PhrasePlan per schema in the chain. Makes zero compositional choices
about notes - only determines where schema degrees fall in time and
what ranges/keys apply.
"""
from fractions import Fraction
from builder.cadence_writer import get_schema_bars, load_cadence_templates, CadenceTemplate
from builder.phrase_types import BeatPosition, PhrasePlan
from builder.types import Anchor, GenreConfig, SchemaChain
from shared.schema_types import Schema
from shared.constants import CADENTIAL_POSITION, VOICE_RANGES
from shared.key import Key
from shared.music_math import parse_metre
from shared.voice_types import Range


def build_phrase_plans(
    schema_chain: SchemaChain,
    anchors: list[Anchor],
    genre_config: GenreConfig,
    schemas: dict[str, Schema],
    total_bars: int,
) -> tuple[PhrasePlan, ...]:
    """Build PhrasePlan objects from schema chain and anchors."""
    bar_length, beat_unit = parse_metre(metre=genre_config.metre)
    upbeat: Fraction = genre_config.upbeat
    assert len(anchors) > 0, "Cannot build phrase plans with no anchors"
    home_key: Key = anchors[0].local_key
    anchor_groups: list[list[Anchor]] = _group_anchors_by_schema(
        anchors=anchors,
        schema_chain=schema_chain,
    )
    upper_range: Range = Range(low=VOICE_RANGES[0][0], high=VOICE_RANGES[0][1])
    lower_range: Range = Range(low=VOICE_RANGES[3][0], high=VOICE_RANGES[3][1])
    upper_median: int = (upper_range.low + upper_range.high) // 2
    lower_median: int = (lower_range.low + lower_range.high) // 2
    cumulative_bar: int = 1
    plans: list[PhrasePlan] = []
    for i, schema_name in enumerate(schema_chain.schemas):
        schema_def: Schema = schemas[schema_name]
        assert i < len(anchor_groups), (
            f"Schema index {i} ({schema_name}) has no anchor group; "
            f"anchor_groups has {len(anchor_groups)} entries"
        )
        anchor_group: list[Anchor] = anchor_groups[i]
        section_name: str = _section_for_schema_index(
            index=i,
            boundaries=schema_chain.section_boundaries,
            genre_config=genre_config,
        )
        plan: PhrasePlan = _build_single_plan(
            schema_name=schema_name,
            schema_def=schema_def,
            anchor_group=anchor_group,
            schema_index=i,
            schema_chain=schema_chain,
            genre_config=genre_config,
            bar_length=bar_length,
            beat_unit=beat_unit,
            upbeat=upbeat,
            section_name=section_name,
            upper_range=upper_range,
            lower_range=lower_range,
            upper_median=upper_median,
            lower_median=lower_median,
            cumulative_bar=cumulative_bar,
            home_key=home_key,
        )
        plans.append(plan)
        cumulative_bar += plan.bar_span
    _validate_plans(plans=plans, schema_chain=schema_chain)
    return tuple(plans)


def _build_single_plan(
    schema_name: str,
    schema_def: Schema,
    anchor_group: list[Anchor],
    schema_index: int,
    schema_chain: SchemaChain,
    genre_config: GenreConfig,
    bar_length: Fraction,
    beat_unit: Fraction,
    upbeat: Fraction,
    section_name: str,
    upper_range: Range,
    lower_range: Range,
    upper_median: int,
    lower_median: int,
    cumulative_bar: int,
    home_key: Key,
) -> PhrasePlan:
    """Build a single PhrasePlan for one schema."""
    bar_span: int = _compute_bar_span(schema_def=schema_def, schema_name=schema_name, metre=genre_config.metre)
    is_cadential: bool = schema_def.position == CADENTIAL_POSITION
    # Resolve per-schema key from chain key_areas (canonical source of truth)
    local_key: Key = _resolve_local_key(
        schema_index=schema_index,
        schema_chain=schema_chain,
        home_key=home_key,
    )
    cadence_template: CadenceTemplate | None = None
    degrees_upper: tuple[int, ...]
    degrees_lower: tuple[int, ...]
    degree_keys: tuple[Key, ...] | None = None
    seq_positions: tuple[BeatPosition, ...] | None = None
    if is_cadential:
        cadence_template = _get_cadential_template(
            schema_name=schema_name,
            metre=genre_config.metre,
        )
    if cadence_template is not None:
        degrees_upper = cadence_template.soprano_degrees
        degrees_lower = cadence_template.bass_degrees
    elif schema_def.sequential:
        degrees_upper, degrees_lower, seq_positions, degree_keys = _expand_sequential_degrees(
            schema_def=schema_def,
            bar_span=bar_span,
            home_key=local_key,
            metre=genre_config.metre,
        )
    else:
        degrees_upper = schema_def.soprano_degrees
        degrees_lower = schema_def.bass_degrees
    first_bar: int = cumulative_bar
    first_beat: int = 1
    degree_positions: tuple[BeatPosition, ...]
    if cadence_template is not None:
        degree_positions = _cadential_degree_positions(
            template=cadence_template,
            beat_unit=beat_unit,
        )
    elif schema_def.sequential:
        assert seq_positions is not None, (
            f"Sequential schema '{schema_name}' has no seq_positions; "
            f"_expand_sequential_degrees was not called"
        )
        degree_positions = seq_positions
    else:
        degree_positions = tuple(
            BeatPosition(bar=stage + 1, beat=1)
            for stage in range(len(degrees_upper))
        )
    start_offset: Fraction = _compute_start_offset(
        bar=first_bar,
        beat=first_beat,
        bar_length=bar_length,
        beat_unit=beat_unit,
        upbeat=upbeat,
    )
    phrase_duration: Fraction = bar_span * bar_length
    cadence_type: str | None = None
    if is_cadential and schema_index < len(schema_chain.cadences):
        cadence_type = schema_chain.cadences[schema_index]
    bass_texture: str = _get_section_bass_texture(
        section_name=section_name,
        genre_config=genre_config,
    )
    character: str = _get_section_character(
        section_name=section_name,
        genre_config=genre_config,
    )
    return PhrasePlan(
        schema_name=schema_name,
        degrees_upper=degrees_upper,
        degrees_lower=degrees_lower,
        degree_positions=degree_positions,
        local_key=local_key,
        bar_span=bar_span,
        start_bar=first_bar,
        start_offset=start_offset,
        phrase_duration=phrase_duration,
        metre=genre_config.metre,
        rhythm_profile=genre_config.name,
        is_cadential=is_cadential,
        cadence_type=cadence_type,
        prev_exit_upper=None,
        prev_exit_lower=None,
        section_name=section_name,
        upper_range=upper_range,
        lower_range=lower_range,
        upper_median=upper_median,
        lower_median=lower_median,
        bass_texture=bass_texture,
        bass_pattern=genre_config.bass_pattern,
        degree_keys=degree_keys,
        character=character,
    )


def _get_cadential_template(
    schema_name: str,
    metre: str,
) -> CadenceTemplate | None:
    """Look up cadence template, returning None if not found."""
    templates: dict[tuple[str, str], CadenceTemplate] = load_cadence_templates()
    return templates.get((schema_name, metre))


def _cadential_degree_positions(
    template: CadenceTemplate,
    beat_unit: Fraction,
) -> tuple[BeatPosition, ...]:
    """Compute degree positions from template durations."""
    positions: list[BeatPosition] = []
    bar_length: Fraction = Fraction(*[int(x) for x in template.metre.split("/")])
    offset: Fraction = Fraction(0)
    for dur in template.soprano_durations:
        bar: int = int(offset // bar_length) + 1
        beat_offset: Fraction = offset - (bar - 1) * bar_length
        beat: int = int(beat_offset // beat_unit) + 1
        positions.append(BeatPosition(bar=bar, beat=beat))
        offset += dur
    return tuple(positions)


def _compute_bar_span(
    schema_def: Schema,
    schema_name: str,
    metre: str,
) -> int:
    """Compute how many bars a schema occupies."""
    return get_schema_bars(
        schema_name=schema_name,
        schema_def=schema_def,
        metre=metre,
    )


def _compute_start_offset(
    bar: int,
    beat: int,
    bar_length: Fraction,
    beat_unit: Fraction,
    upbeat: Fraction,
) -> Fraction:
    """Convert bar.beat to absolute offset in whole notes."""
    offset: Fraction = (bar - 1) * bar_length + (beat - 1) * beat_unit
    if upbeat > 0 and bar == 0:
        offset = -upbeat + (beat - 1) * beat_unit
    return offset


def _group_anchors_by_schema(
    anchors: list[Anchor],
    schema_chain: SchemaChain,
) -> list[list[Anchor]]:
    """Group anchors into sublists, one per schema in the chain."""
    schema_count: int = len(schema_chain.schemas)
    groups: list[list[Anchor]] = [[] for _ in range(schema_count)]
    filtered: list[Anchor] = [
        a for a in anchors
        if not a.schema.startswith("piece_") and not a.schema.startswith("section_cadence")
    ]
    instance_lists: dict[str, list[list[Anchor]]] = {}
    for anchor in filtered:
        if anchor.schema not in instance_lists:
            instance_lists[anchor.schema] = []
        instances: list[list[Anchor]] = instance_lists[anchor.schema]
        if anchor.stage == 1:
            instances.append([anchor])
        elif instances:
            instances[-1].append(anchor)
    schema_instance_count: dict[str, int] = {}
    for i, schema_name in enumerate(schema_chain.schemas):
        instance_idx: int = schema_instance_count.get(schema_name, 0)
        schema_instance_count[schema_name] = instance_idx + 1
        if schema_name not in instance_lists:
            continue
        instances = instance_lists[schema_name]
        if instance_idx < len(instances):
            groups[i] = instances[instance_idx]
    return groups


def _get_section_bass_texture(
    section_name: str,
    genre_config: GenreConfig,
) -> str:
    """Look up accompany_texture from genre section data (A003)."""
    for section in genre_config.sections:
        if section.get("name") == section_name:
            return section.get("accompany_texture", "pillar")
    return "pillar"


def _get_section_character(
    section_name: str,
    genre_config: GenreConfig,
) -> str:
    """Look up character from genre section data (A003)."""
    for section in genre_config.sections:
        if section.get("name") == section_name:
            return section.get("character", "plain")
    return "plain"


def _resolve_local_key(
    schema_index: int,
    schema_chain: SchemaChain,
    home_key: Key,
) -> Key:
    """Resolve local key from chain key_areas (canonical source of truth)."""
    if schema_index < len(schema_chain.key_areas):
        area: str = schema_chain.key_areas[schema_index]
        if area == "I":
            return home_key
        return home_key.modulate_to(target=area)
    return home_key


def _section_for_schema_index(
    index: int,
    boundaries: tuple[int, ...],
    genre_config: GenreConfig,
) -> str:
    """Return section name for schema at given chain index."""
    for section_idx, boundary in enumerate(boundaries):
        if index < boundary:
            return genre_config.sections[section_idx]["name"]
    return genre_config.sections[-1]["name"] if genre_config.sections else ""


def _expand_sequential_degrees(
    schema_def: Schema,
    bar_span: int,
    home_key: Key,
    metre: str,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[BeatPosition, ...], tuple[Key, ...]]:
    """Expand per-segment degrees into full-phrase degrees for sequential schemas."""
    segment_count: int = bar_span  # 1 bar per segment for sequential schemas
    per_seg_upper: tuple[int, ...] = schema_def.soprano_degrees
    per_seg_lower: tuple[int, ...] = schema_def.bass_degrees
    assert len(per_seg_upper) == len(per_seg_lower), (
        f"Sequential schema '{schema_def.name}': soprano degree count "
        f"{len(per_seg_upper)} != bass degree count {len(per_seg_lower)}"
    )
    degrees_per_seg: int = len(per_seg_upper)
    assert degrees_per_seg >= 1, (
        f"Sequential schema '{schema_def.name}': no per-segment degrees"
    )
    typical_keys: tuple[str, ...] | None = schema_def.typical_keys
    beats_per_bar: int = int(metre.split("/")[0])
    all_upper: list[int] = []
    all_lower: list[int] = []
    all_positions: list[BeatPosition] = []
    all_keys: list[Key] = []
    for seg_idx in range(segment_count):
        seg_key: Key = _get_sequential_segment_key(
            home_key=home_key,
            segment_index=seg_idx,
            typical_keys=typical_keys,
        )
        bar_num: int = seg_idx + 1
        for deg_idx in range(degrees_per_seg):
            all_upper.append(per_seg_upper[deg_idx])
            all_lower.append(per_seg_lower[deg_idx])
            beat: int = (deg_idx * beats_per_bar) // degrees_per_seg + 1
            all_positions.append(BeatPosition(bar=bar_num, beat=beat))
            all_keys.append(seg_key)
    return tuple(all_upper), tuple(all_lower), tuple(all_positions), tuple(all_keys)


def _get_sequential_segment_key(
    home_key: Key,
    segment_index: int,
    typical_keys: tuple[str, ...] | None,
) -> Key:
    """Get local key for a sequential schema segment."""
    if typical_keys is None or len(typical_keys) == 0:
        return home_key
    key_idx: int = min(segment_index, len(typical_keys) - 1)
    key_area: str = typical_keys[key_idx]
    if key_area == "I" or key_area == "i":
        return home_key
    return home_key.modulate_to(target=key_area)


def _validate_plans(
    plans: list[PhrasePlan],
    schema_chain: SchemaChain,
) -> None:
    """Validate postconditions on phrase plans."""
    assert len(plans) == len(schema_chain.schemas), (
        f"Plan count {len(plans)} != schema count {len(schema_chain.schemas)}"
    )
    for i, plan in enumerate(plans):
        for j in range(len(plan.degree_positions) - 1):
            pos_a: BeatPosition = plan.degree_positions[j]
            pos_b: BeatPosition = plan.degree_positions[j + 1]
            assert (pos_a.bar, pos_a.beat) <= (pos_b.bar, pos_b.beat), (
                f"Plan {i} degree_positions not chronological: {pos_a} > {pos_b}"
            )
