"""Schema anchor generation."""
from builder.types import Anchor, SchemaConfig
from planner.metric.constants import (
    CLAUSULA_APPROACH_BASS,
    CLAUSULA_APPROACH_SOPRANO,
    CLAUSULA_ARRIVAL_BASS,
    CLAUSULA_ARRIVAL_SOPRANO,
)
from planner.metric.distribution import distribute_arrivals, get_final_strong_beat
from planner.metric.pitch import wrap_degree
from shared.key import Key


def generate_schema_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    end_bar: int,
    local_key: Key,
    metre: str,
) -> list[Anchor]:
    """Generate anchors for a single schema in local key."""
    if schema_def.sequential:
        return _generate_sequential_anchors(
            schema_name, schema_def, start_bar, end_bar, local_key, metre,
        )
    anchors: list[Anchor] = []
    soprano_degrees: tuple[int, ...] = schema_def.soprano_degrees
    bass_degrees: tuple[int, ...] = schema_def.bass_degrees
    if not soprano_degrees or not bass_degrees:
        return anchors
    stages: int = len(soprano_degrees)
    is_cadential: bool = schema_def.cadential_state == "closed"
    bar_beats: list[str] = _distribute_schema_arrivals(
        stages, start_bar, end_bar, metre, is_cadential,
    )
    for stage, bar_beat in enumerate(bar_beats):
        if stage >= len(soprano_degrees) or stage >= len(bass_degrees):
            break
        anchors.append(Anchor(
            bar_beat=bar_beat,
            soprano_degree=soprano_degrees[stage],
            bass_degree=bass_degrees[stage],
            local_key=local_key,
            schema=schema_name,
            stage=stage + 1,
        ))
    return anchors


def _distribute_schema_arrivals(
    stages: int,
    start_bar: int,
    end_bar: int,
    metre: str,
    anchor_final: bool,
) -> list[str]:
    """Distribute arrival beats, optionally anchoring final stage to end_bar."""
    if not anchor_final or stages < 2:
        return distribute_arrivals(stages, start_bar, end_bar, metre)
    preceding: list[str] = distribute_arrivals(stages - 1, start_bar, end_bar - 1, metre)
    return preceding + [f"{end_bar}.1"]


def _generate_sequential_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    end_bar: int,
    local_key: Key,
    metre: str,
) -> list[Anchor]:
    """Generate anchors for sequential schema (Monte, Fonte) in local key."""
    anchors: list[Anchor] = []
    available_bars: int = end_bar - start_bar + 1
    segment_count: int = _determine_segment_count(schema_def, available_bars)
    direction: str = schema_def.direction or "ascending"
    degree_step: int = 1 if direction == "ascending" else -1
    bars_per_segment: int = max(1, available_bars // segment_count)
    arrival_beat: int = get_final_strong_beat(metre)
    for seg_idx in range(segment_count):
        segment_bar: int = start_bar + (seg_idx * bars_per_segment)
        if segment_bar > end_bar:
            segment_bar = end_bar
        degree_offset: int = seg_idx * degree_step
        approach_anchor: Anchor = _make_clausula_approach(
            segment_bar, degree_offset, local_key, schema_name, seg_idx,
        )
        anchors.append(approach_anchor)
        arrival_anchor: Anchor = _make_clausula_arrival(
            segment_bar, arrival_beat, degree_offset, local_key, schema_name, seg_idx,
        )
        anchors.append(arrival_anchor)
    return anchors


def _determine_segment_count(
    schema_def: SchemaConfig,
    available_bars: int,
) -> int:
    """Determine segment count for sequential schema."""
    segments: tuple[int, ...] = schema_def.segments
    if not segments:
        segments = (2,)
    min_segments: int = min(segments)
    max_segments: int = max(segments)
    if available_bars >= max_segments:
        return max_segments
    if available_bars >= min_segments:
        return available_bars
    return min_segments


def _make_clausula_approach(
    segment_bar: int,
    degree_offset: int,
    local_key: Key,
    schema_name: str,
    seg_idx: int,
) -> Anchor:
    """Create approach anchor for clausula cantizans."""
    s_deg: int = wrap_degree(CLAUSULA_APPROACH_SOPRANO + degree_offset)
    b_deg: int = wrap_degree(CLAUSULA_APPROACH_BASS + degree_offset)
    return Anchor(
        bar_beat=f"{segment_bar}.1",
        soprano_degree=s_deg,
        bass_degree=b_deg,
        local_key=local_key,
        schema=schema_name,
        stage=(seg_idx * 2) + 1,
    )


def _make_clausula_arrival(
    segment_bar: int,
    arrival_beat: int,
    degree_offset: int,
    local_key: Key,
    schema_name: str,
    seg_idx: int,
) -> Anchor:
    """Create arrival anchor for clausula cantizans."""
    s_deg: int = wrap_degree(CLAUSULA_ARRIVAL_SOPRANO + degree_offset)
    b_deg: int = wrap_degree(CLAUSULA_ARRIVAL_BASS + degree_offset)
    return Anchor(
        bar_beat=f"{segment_bar}.{arrival_beat}",
        soprano_degree=s_deg,
        bass_degree=b_deg,
        local_key=local_key,
        schema=schema_name,
        stage=(seg_idx * 2) + 2,
    )
