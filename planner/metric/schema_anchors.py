"""Schema anchor generation."""
from builder.types import Anchor, SchemaConfig
from planner.metric.constants import CLAUSULA_ARRIVAL_BASS, CLAUSULA_ARRIVAL_SOPRANO
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
    """Generate anchors for a schema: one anchor per bar, one stage per bar."""
    if schema_def.sequential:
        return _generate_sequential_anchors(
            schema_name, schema_def, start_bar, local_key,
        )
    return _generate_regular_anchors(
        schema_name, schema_def, start_bar, local_key,
    )


def _generate_regular_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    local_key: Key,
) -> list[Anchor]:
    """Generate anchors for regular (non-sequential) schema."""
    anchors: list[Anchor] = []
    soprano_degrees: tuple[int, ...] = schema_def.soprano_degrees
    bass_degrees: tuple[int, ...] = schema_def.bass_degrees
    if not soprano_degrees or not bass_degrees:
        return anchors
    stages: int = len(soprano_degrees)
    for stage in range(stages):
        bar: int = start_bar + stage
        anchors.append(Anchor(
            bar_beat=f"{bar}.1",
            soprano_degree=soprano_degrees[stage],
            bass_degree=bass_degrees[stage],
            local_key=local_key,
            schema=schema_name,
            stage=stage + 1,
        ))
    return anchors


def _generate_sequential_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    local_key: Key,
) -> list[Anchor]:
    """Generate anchors for sequential schema (Monte, Fonte).
    
    One arrival per segment at (3,1). One segment = one bar.
    """
    anchors: list[Anchor] = []
    segments: tuple[int, ...] = schema_def.segments or (2,)
    segment_count: int = max(segments) if isinstance(segments, (list, tuple)) else segments
    direction: str = schema_def.direction or "ascending"
    degree_step: int = 1 if direction == "ascending" else -1
    for seg_idx in range(segment_count):
        bar: int = start_bar + seg_idx
        degree_offset: int = seg_idx * degree_step
        s_deg: int = wrap_degree(CLAUSULA_ARRIVAL_SOPRANO + degree_offset)
        b_deg: int = wrap_degree(CLAUSULA_ARRIVAL_BASS + degree_offset)
        anchors.append(Anchor(
            bar_beat=f"{bar}.1",
            soprano_degree=s_deg,
            bass_degree=b_deg,
            local_key=local_key,
            schema=schema_name,
            stage=seg_idx + 1,
        ))
    return anchors
