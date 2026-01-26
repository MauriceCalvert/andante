"""Layer 4: Metric planning orchestration."""
from builder.types import Anchor, FormConfig, GenreConfig, KeyConfig, SchemaConfig
from planner.metric.bridge_anchors import generate_bridge_anchors
from planner.metric.distribution import bar_beat_to_float
from planner.metric.schema_anchors import generate_schema_anchors
from shared.key import Key


def layer_4_metric(
    schema_chain: SchemaConfig,
    genre_config: GenreConfig,
    form_config: FormConfig,
    key_config: KeyConfig | None = None,
    schemas: dict[str, SchemaConfig] | None = None,
    tonal_plan: dict[str, tuple[str, ...]] | None = None,
    answer_interval: int = 7,
) -> tuple[dict[str, tuple[int, int]], list[Anchor], int]:
    """Execute Layer 4 metric planning."""
    bar_assignments: dict[str, tuple[int, int]] = _build_bar_assignments(genre_config)
    total_bars: int = form_config.minimum_bars
    if key_config is None or schemas is None:
        return bar_assignments, [], total_bars
    key: Key = _key_config_to_key(key_config)
    if tonal_plan is None:
        tonal_plan = {}
    section_anchors: list[Anchor] = _generate_section_anchors(
        genre_config.sections, schemas, key,
        genre_config.metre, tonal_plan, answer_interval,
    )
    anchors: list[Anchor] = section_anchors
    covered_bars: set[int] = _get_covered_bars(anchors)
    bridge_anchors: list[Anchor] = generate_bridge_anchors(
        total_bars, covered_bars, anchors, key, genre_config.metre,
    )
    anchors.extend(bridge_anchors)
    anchors.sort(key=lambda a: (bar_beat_to_float(a.bar_beat), a.soprano_degree))
    return bar_assignments, anchors, total_bars


def _build_bar_assignments(genre_config: GenreConfig) -> dict[str, tuple[int, int]]:
    """Build bar assignments from genre sections."""
    assignments: dict[str, tuple[int, int]] = {}
    for section in genre_config.sections:
        section_name: str = section["name"]
        bars: list[int] = section["bars"]
        assignments[section_name] = (bars[0], bars[1])
    return assignments


def _generate_section_anchors(
    sections: tuple[dict, ...],
    schemas: dict[str, SchemaConfig],
    key: Key,
    metre: str,
    tonal_plan: dict[str, tuple[str, ...]],
    answer_interval: int,
) -> list[Anchor]:
    """Generate anchors for all sections with transposition."""
    anchors: list[Anchor] = []
    for section in sections:
        section_anchors: list[Anchor] = _generate_single_section_anchors(
            section, schemas, key, metre, tonal_plan, answer_interval,
        )
        anchors.extend(section_anchors)
    return anchors


def _generate_single_section_anchors(
    section: dict,
    schemas: dict[str, SchemaConfig],
    home_key: Key,
    metre: str,
    tonal_plan: dict[str, tuple[str, ...]],
    answer_interval: int,
) -> list[Anchor]:
    """Generate anchors for a single section."""
    section_name: str = section["name"]
    bars: list[int] = section["bars"]
    start_bar: int = bars[0]
    end_bar: int = bars[1]
    schema_sequence: list[str] = section.get("schema_sequence", [])
    real_schemas: list[str] = [s for s in schema_sequence if s != "episode"]
    if not real_schemas:
        return []
    key_areas: tuple[str, ...] = tonal_plan.get(section_name, ("I",))
    is_exordium: bool = section_name == "exordium"
    bar_ranges: list[tuple[int, int]] = _allocate_bars_by_stages(
        real_schemas, schemas, start_bar, end_bar,
    )
    anchors: list[Anchor] = []
    for i, schema_name in enumerate(real_schemas):
        if schema_name not in schemas:
            continue
        schema_start, schema_end = bar_ranges[i]
        local_key: Key = _get_local_key(home_key, i, is_exordium, key_areas, answer_interval)
        schema_anchors: list[Anchor] = generate_schema_anchors(
            schema_name, schemas[schema_name], schema_start, schema_end,
            local_key, metre,
        )
        anchors.extend(schema_anchors)
    return anchors


def _allocate_bars_by_stages(
    schema_names: list[str],
    schemas: dict[str, SchemaConfig],
    start_bar: int,
    end_bar: int,
) -> list[tuple[int, int]]:
    """Allocate bars to schemas proportional to stage count."""
    stage_counts: list[int] = []
    for name in schema_names:
        if name not in schemas:
            stage_counts.append(1)
            continue
        schema_def: SchemaConfig = schemas[name]
        if schema_def.sequential:
            segments: tuple[int, ...] = schema_def.segments or (2,)
            stage_counts.append(max(segments) * 2)
        else:
            stage_counts.append(len(schema_def.soprano_degrees))
    total_stages: int = sum(stage_counts)
    section_bars: int = end_bar - start_bar + 1
    bar_ranges: list[tuple[int, int]] = []
    current_bar: int = start_bar
    for i, stages in enumerate(stage_counts):
        is_last: bool = i == len(stage_counts) - 1
        if is_last:
            schema_bars = end_bar - current_bar + 1
        else:
            schema_bars = max(1, round(section_bars * stages / total_stages))
        schema_end: int = min(current_bar + schema_bars - 1, end_bar)
        bar_ranges.append((current_bar, schema_end))
        current_bar = schema_end + 1
    return bar_ranges


def _get_covered_bars(anchors: list[Anchor]) -> set[int]:
    """Get set of bars that have at least one anchor."""
    covered: set[int] = set()
    for anchor in anchors:
        bar: int = int(anchor.bar_beat.split(".")[0])
        covered.add(bar)
    return covered


def _get_local_key(
    home_key: Key,
    schema_index: int,
    is_exordium: bool,
    key_areas: tuple[str, ...],
    answer_interval: int,
) -> Key:
    """Determine local key for schema at given index."""
    if is_exordium and schema_index == 1:
        return home_key.modulate_to("V")
    if schema_index < len(key_areas):
        area: str = key_areas[schema_index]
        if area == "I":
            return home_key
        return home_key.modulate_to(area)
    area = key_areas[-1]
    if area == "I":
        return home_key
    return home_key.modulate_to(area)


def _key_config_to_key(key_config: KeyConfig) -> Key:
    """Convert KeyConfig to Key object."""
    parts: list[str] = key_config.name.split()
    tonic: str = parts[0]
    mode: str = parts[1].lower() if len(parts) > 1 else "major"
    return Key(tonic=tonic, mode=mode)
