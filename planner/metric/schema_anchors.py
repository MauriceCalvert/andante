"""Schema anchor generation."""
from builder.types import Anchor, SchemaConfig
from planner.metric.constants import (
    CLAUSULA_APPROACH_BASS,
    CLAUSULA_APPROACH_SOPRANO,
    CLAUSULA_ARRIVAL_BASS,
    CLAUSULA_ARRIVAL_SOPRANO,
)
from planner.metric.distribution import distribute_arrivals, get_final_strong_beat
from planner.metric.pitch import gravitational_pitch, wrap_degree
from shared.key import Key


def generate_schema_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    end_bar: int,
    key: Key,
    soprano_median: int,
    bass_median: int,
    metre: str,
    transposition: int,
    prev_soprano: int | None,
    prev_bass: int | None,
) -> tuple[list[Anchor], int, int]:
    """Generate anchors for a single schema with transposition."""
    if schema_def.sequential:
        return generate_sequential_anchors(
            schema_name, schema_def, start_bar, end_bar,
            key, soprano_median, bass_median, metre, transposition,
            prev_soprano, prev_bass,
        )
    anchors: list[Anchor] = []
    soprano_degrees: tuple[int, ...] = schema_def.soprano_degrees
    bass_degrees: tuple[int, ...] = schema_def.bass_degrees
    if not soprano_degrees or not bass_degrees:
        return anchors, prev_soprano or 72, prev_bass or 48
    stages: int = len(soprano_degrees)
    bar_beats: list[str] = distribute_arrivals(stages, start_bar, end_bar, metre)
    if prev_soprano is None:
        prev_soprano = gravitational_pitch(key, soprano_degrees[0], soprano_median, soprano_median)
    if prev_bass is None:
        prev_bass = gravitational_pitch(key, bass_degrees[0], bass_median, bass_median)
    for stage, bar_beat in enumerate(bar_beats):
        if stage >= len(soprano_degrees) or stage >= len(bass_degrees):
            break
        s_degree: int = soprano_degrees[stage]
        b_degree: int = bass_degrees[stage]
        s_midi: int = gravitational_pitch(key, s_degree, prev_soprano, soprano_median) + transposition
        b_midi: int = gravitational_pitch(key, b_degree, prev_bass, bass_median) + transposition
        prev_soprano = s_midi - transposition
        prev_bass = b_midi - transposition
        anchors.append(Anchor(
            bar_beat=bar_beat,
            soprano_midi=s_midi,
            bass_midi=b_midi,
            schema=schema_name,
            stage=stage + 1,
        ))
    return anchors, prev_soprano, prev_bass


def generate_sequential_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    end_bar: int,
    key: Key,
    soprano_median: int,
    bass_median: int,
    metre: str,
    base_transposition: int,
    prev_soprano: int | None,
    prev_bass: int | None,
) -> tuple[list[Anchor], int, int]:
    """Generate anchors for sequential schema (Monte, Fonte)."""
    anchors: list[Anchor] = []
    available_bars: int = end_bar - start_bar + 1
    segment_count: int = _determine_segment_count(schema_def, available_bars)
    direction: str = schema_def.direction or "ascending"
    degree_step: int = 1 if direction == "ascending" else -1
    bars_per_segment: int = max(1, available_bars // segment_count)
    arrival_beat: int = get_final_strong_beat(metre)
    if prev_soprano is None:
        prev_soprano = gravitational_pitch(key, CLAUSULA_APPROACH_SOPRANO, soprano_median, soprano_median)
    if prev_bass is None:
        prev_bass = gravitational_pitch(key, CLAUSULA_APPROACH_BASS, bass_median, bass_median)
    for seg_idx in range(segment_count):
        segment_bar: int = start_bar + (seg_idx * bars_per_segment)
        if segment_bar > end_bar:
            segment_bar = end_bar
        degree_offset: int = seg_idx * degree_step
        approach_anchors, prev_soprano, prev_bass = _generate_clausula_approach(
            segment_bar, degree_offset, key, soprano_median, bass_median,
            base_transposition, prev_soprano, prev_bass, schema_name, seg_idx,
        )
        anchors.extend(approach_anchors)
        arrival_anchors, prev_soprano, prev_bass = _generate_clausula_arrival(
            segment_bar, arrival_beat, degree_offset, key, soprano_median, bass_median,
            base_transposition, prev_soprano, prev_bass, schema_name, seg_idx,
        )
        anchors.extend(arrival_anchors)
    return anchors, prev_soprano, prev_bass


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


def _generate_clausula_approach(
    segment_bar: int,
    degree_offset: int,
    key: Key,
    soprano_median: int,
    bass_median: int,
    transposition: int,
    prev_soprano: int,
    prev_bass: int,
    schema_name: str,
    seg_idx: int,
) -> tuple[list[Anchor], int, int]:
    """Generate approach anchor for clausula cantizans."""
    s_deg: int = wrap_degree(CLAUSULA_APPROACH_SOPRANO + degree_offset)
    b_deg: int = wrap_degree(CLAUSULA_APPROACH_BASS + degree_offset)
    s_midi: int = gravitational_pitch(key, s_deg, prev_soprano, soprano_median) + transposition
    b_midi: int = gravitational_pitch(key, b_deg, prev_bass, bass_median) + transposition
    anchor: Anchor = Anchor(
        bar_beat=f"{segment_bar}.1",
        soprano_midi=s_midi,
        bass_midi=b_midi,
        schema=schema_name,
        stage=(seg_idx * 2) + 1,
    )
    return [anchor], s_midi - transposition, b_midi - transposition


def _generate_clausula_arrival(
    segment_bar: int,
    arrival_beat: int,
    degree_offset: int,
    key: Key,
    soprano_median: int,
    bass_median: int,
    transposition: int,
    prev_soprano: int,
    prev_bass: int,
    schema_name: str,
    seg_idx: int,
) -> tuple[list[Anchor], int, int]:
    """Generate arrival anchor for clausula cantizans."""
    s_deg: int = wrap_degree(CLAUSULA_ARRIVAL_SOPRANO + degree_offset)
    b_deg: int = wrap_degree(CLAUSULA_ARRIVAL_BASS + degree_offset)
    s_midi: int = gravitational_pitch(key, s_deg, prev_soprano, soprano_median) + transposition
    b_midi: int = gravitational_pitch(key, b_deg, prev_bass, bass_median) + transposition
    anchor: Anchor = Anchor(
        bar_beat=f"{segment_bar}.{arrival_beat}",
        soprano_midi=s_midi,
        bass_midi=b_midi,
        schema=schema_name,
        stage=(seg_idx * 2) + 2,
    )
    return [anchor], s_midi - transposition, b_midi - transposition
