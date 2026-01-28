"""Layer 4: Metric planning orchestration."""
from fractions import Fraction

from builder.types import Anchor, FormConfig, GenreConfig, KeyConfig, SchemaConfig
from planner.metric.distribution import bar_beat_to_float
from planner.metric.schema_anchors import generate_schema_anchors
from shared.key import Key
from shared.tracer import get_tracer


def get_schema_stages(schema_name: str, schemas: dict[str, SchemaConfig]) -> int:
    """Get number of bars a schema occupies (1 stage = 1 bar)."""
    if schema_name not in schemas or schema_name == "episode":
        return 0
    schema_def: SchemaConfig = schemas[schema_name]
    if schema_def.sequential:
        segments: tuple[int, ...] = schema_def.segments or (2,)
        return max(segments) if isinstance(segments, (list, tuple)) else segments
    return len(schema_def.soprano_degrees)


def layer_4_metric(
    schema_chain: SchemaConfig,
    genre_config: GenreConfig,
    form_config: FormConfig,
    key_config: KeyConfig | None = None,
    schemas: dict[str, SchemaConfig] | None = None,
    tonal_plan: dict[str, tuple[str, ...]] | None = None,
    answer_interval: int = 7,
    modality: str = "diatonic",
) -> tuple[dict[str, tuple[int, int]], list[Anchor], int]:
    """Execute Layer 4 metric planning."""
    tracer = get_tracer()
    if schemas is None:
        schemas = {}
    bar_assignments: dict[str, tuple[int, int]] = _build_bar_assignments(
        genre_config, schemas,
    )
    total_bars: int = max(end for _, end in bar_assignments.values()) if bar_assignments else 0
    if key_config is None:
        return bar_assignments, [], total_bars
    key: Key = _key_config_to_key(key_config)
    if tonal_plan is None:
        tonal_plan = {}
    anchors: list[Anchor] = _generate_section_anchors(
        genre_config.sections, schemas, key,
        genre_config.metre, tonal_plan, answer_interval, modality,
        bar_assignments, genre_config.upbeat,
    )
    anchors.sort(key=lambda a: (bar_beat_to_float(a.bar_beat), a.upper_degree))
    for a in anchors:
        tracer.anchor(a.bar_beat, a.upper_degree, a.lower_degree, a.local_key.tonic, a.schema, a.stage, a.section)
    return bar_assignments, anchors, total_bars


def _build_bar_assignments(
    genre_config: GenreConfig,
    schemas: dict[str, SchemaConfig],
) -> dict[str, tuple[int, int]]:
    """Build bar assignments by computing section lengths from schema stages."""
    assignments: dict[str, tuple[int, int]] = {}
    current_bar: int = 1
    is_first_section: bool = True
    for section in genre_config.sections:
        section_name: str = section["name"]
        schema_sequence: list[str] = section.get("schema_sequence", [])
        section_bars: int = sum(
            get_schema_stages(name, schemas)
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


def _generate_section_anchors(
    sections: tuple[dict, ...],
    schemas: dict[str, SchemaConfig],
    key: Key,
    metre: str,
    tonal_plan: dict[str, tuple[str, ...]],
    answer_interval: int,
    modality: str,
    bar_assignments: dict[str, tuple[int, int]],
    upbeat: Fraction = Fraction(0),
) -> list[Anchor]:
    """Generate anchors for all sections."""
    anchors: list[Anchor] = []
    is_first_section: bool = True
    for section in sections:
        section_name: str = section["name"]
        start_bar, _ = bar_assignments[section_name]
        section_upbeat: Fraction = upbeat if is_first_section else Fraction(0)
        section_anchors: list[Anchor] = _generate_single_section_anchors(
            section, schemas, key, metre, tonal_plan, answer_interval, modality,
            start_bar, section_upbeat,
        )
        anchors.extend(section_anchors)
        is_first_section = False
    return anchors


def _generate_single_section_anchors(
    section: dict,
    schemas: dict[str, SchemaConfig],
    home_key: Key,
    metre: str,
    tonal_plan: dict[str, tuple[str, ...]],
    answer_interval: int,
    modality: str,
    start_bar: int,
    upbeat: Fraction = Fraction(0),
) -> list[Anchor]:
    """Generate anchors for a single section."""
    section_name: str = section["name"]
    schema_sequence: list[str] = section.get("schema_sequence", [])
    real_schemas: list[str] = [s for s in schema_sequence if s != "episode"]
    if not real_schemas:
        return []
    key_areas: tuple[str, ...] = tonal_plan.get(section_name, ("I",))
    is_exordium: bool = section_name == "exordium"
    anchors: list[Anchor] = []
    current_bar: int = start_bar
    is_first_schema: bool = True
    for i, schema_name in enumerate(real_schemas):
        if schema_name not in schemas:
            continue
        schema_def: SchemaConfig = schemas[schema_name]
        stages: int = get_schema_stages(schema_name, schemas)
        schema_end: int = current_bar + stages - 1
        local_key: Key = _get_local_key(
            home_key, i, is_exordium, key_areas, answer_interval, modality,
        )
        schema_upbeat: Fraction = upbeat if is_first_schema else Fraction(0)
        if schema_upbeat > 0:
            schema_end -= 1
        schema_anchors: list[Anchor] = generate_schema_anchors(
            schema_name, schema_def, current_bar, schema_end,
            local_key, metre, schema_upbeat, section_name,
        )
        anchors.extend(schema_anchors)
        current_bar = schema_end + 1
        is_first_schema = False
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
