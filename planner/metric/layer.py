"""Layer 4: Metric planning orchestration."""
from builder.types import Anchor, FormConfig, GenreConfig, KeyConfig, SchemaConfig
from planner.metric.bridge_anchors import generate_bridge_anchors
from planner.metric.constants import KEY_AREA_SEMITONES
from planner.metric.distribution import bar_beat_to_float, get_final_strong_beat
from planner.metric.pitch import compute_base_octave, degree_to_midi
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
    soprano_median: int = genre_config.tessitura.get("soprano", 70)
    bass_median: int = genre_config.tessitura.get("bass", 48)
    if tonal_plan is None:
        tonal_plan = {}
    section_anchors: list[Anchor] = _generate_section_anchors(
        genre_config.sections, schemas, key, soprano_median, bass_median,
        genre_config.metre, tonal_plan, answer_interval,
    )
    final_anchor: Anchor = _generate_final_cadence_anchor(
        total_bars, key, soprano_median, bass_median, genre_config.metre,
    )
    anchors: list[Anchor] = section_anchors + [final_anchor]
    covered_bars: set[int] = _get_covered_bars(anchors)
    bridge_anchors: list[Anchor] = generate_bridge_anchors(
        total_bars, covered_bars, anchors, key, soprano_median, bass_median, genre_config.metre,
    )
    anchors.extend(bridge_anchors)
    anchors.sort(key=lambda a: (bar_beat_to_float(a.bar_beat), a.soprano_midi))
    return bar_assignments, anchors, total_bars


def _build_bar_assignments(genre_config: GenreConfig) -> dict[str, tuple[int, int]]:
    """Build bar assignments from genre sections."""
    assignments: dict[str, tuple[int, int]] = {}
    for section in genre_config.sections:
        section_name: str = section["name"]
        bars: list[int] = section["bars"]
        assignments[section_name] = (bars[0], bars[1])
    return assignments


def _generate_final_cadence_anchor(
    total_bars: int,
    key: Key,
    soprano_median: int,
    bass_median: int,
    metre: str,
) -> Anchor:
    """Generate final tonic cadence anchor."""
    s_octave: int = compute_base_octave(key, 1, soprano_median)
    b_octave: int = compute_base_octave(key, 1, bass_median)
    s_midi: int = degree_to_midi(key, 1, s_octave)
    b_midi: int = degree_to_midi(key, 1, b_octave)
    final_beat: int = get_final_strong_beat(metre)
    return Anchor(
        bar_beat=f"{total_bars}.{final_beat}",
        soprano_midi=s_midi,
        bass_midi=b_midi,
        schema="final_cadence",
        stage=1,
    )


def _generate_section_anchors(
    sections: tuple[dict, ...],
    schemas: dict[str, SchemaConfig],
    key: Key,
    soprano_median: int,
    bass_median: int,
    metre: str,
    tonal_plan: dict[str, tuple[str, ...]],
    answer_interval: int,
) -> list[Anchor]:
    """Generate anchors for all sections with transposition."""
    anchors: list[Anchor] = []
    for section in sections:
        section_anchors: list[Anchor] = _generate_single_section_anchors(
            section, schemas, key, soprano_median, bass_median,
            metre, tonal_plan, answer_interval,
        )
        anchors.extend(section_anchors)
    return anchors


def _generate_single_section_anchors(
    section: dict,
    schemas: dict[str, SchemaConfig],
    key: Key,
    soprano_median: int,
    bass_median: int,
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
    section_bars: int = end_bar - start_bar + 1
    bars_per_schema: int = max(1, section_bars // len(real_schemas))
    anchors: list[Anchor] = []
    current_bar: int = start_bar
    prev_soprano: int | None = None
    prev_bass: int | None = None
    for i, schema_name in enumerate(real_schemas):
        if schema_name not in schemas:
            continue
        schema_start: int = current_bar
        schema_end: int = end_bar if i == len(real_schemas) - 1 else min(current_bar + bars_per_schema - 1, end_bar)
        transposition: int = _get_transposition(i, is_exordium, key_areas, answer_interval)
        schema_anchors, prev_soprano, prev_bass = generate_schema_anchors(
            schema_name, schemas[schema_name], schema_start, schema_end,
            key, soprano_median, bass_median, metre, transposition,
            prev_soprano, prev_bass,
        )
        anchors.extend(schema_anchors)
        current_bar = schema_end + 1
        if current_bar > end_bar:
            break
    return anchors


def _get_covered_bars(anchors: list[Anchor]) -> set[int]:
    """Get set of bars that have at least one anchor."""
    covered: set[int] = set()
    for anchor in anchors:
        bar: int = int(anchor.bar_beat.split(".")[0])
        covered.add(bar)
    return covered


def _get_transposition(
    schema_index: int,
    is_exordium: bool,
    key_areas: tuple[str, ...],
    answer_interval: int,
) -> int:
    """Determine transposition for schema at given index."""
    if is_exordium and schema_index == 1:
        return answer_interval
    if schema_index < len(key_areas):
        return KEY_AREA_SEMITONES.get(key_areas[schema_index], 0)
    return KEY_AREA_SEMITONES.get(key_areas[-1], 0)


def _key_config_to_key(key_config: KeyConfig) -> Key:
    """Convert KeyConfig to Key object."""
    parts: list[str] = key_config.name.split()
    tonic: str = parts[0]
    mode: str = parts[1].lower() if len(parts) > 1 else "major"
    return Key(tonic=tonic, mode=mode)
