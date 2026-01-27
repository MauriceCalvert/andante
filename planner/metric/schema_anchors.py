"""Schema anchor generation."""
from builder.types import Anchor, SchemaConfig
from planner.metric.constants import CLAUSULA_ARRIVAL_BASS, CLAUSULA_ARRIVAL_SOPRANO
from shared.key import Key


def generate_schema_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    end_bar: int,
    home_key: Key,
    metre: str,
) -> list[Anchor]:
    """Generate anchors for a schema: one anchor per bar, one stage per bar."""
    if schema_def.sequential:
        return _generate_sequential_anchors(
            schema_name,
            schema_def,
            start_bar,
            home_key,
        )
    return _generate_regular_anchors(
        schema_name,
        schema_def,
        start_bar,
        home_key,
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


def _get_segment_count(schema_def: SchemaConfig) -> int:
    """Get number of segments for a sequential schema."""
    segments: tuple[int, ...] = schema_def.segments or (2,)
    if isinstance(segments, (list, tuple)):
        return max(segments)
    return segments


def _generate_sequential_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    home_key: Key,
) -> list[Anchor]:
    """Generate anchors for sequential schema (Monte, Fonte).
    
    Each segment uses fixed clausula arrival degrees (3,1) in its local key.
    The soprano rises E->F#->G because the key rises (IV->V->vi in G major),
    NOT because the degree changes.
    
    Example for monte in G major with typical_keys="IV -> V (-> vi)":
        Segment 1: key=C (IV), degree 3 -> E
        Segment 2: key=D (V), degree 3 -> F#
        Segment 3: key=Em (vi), degree 3 -> G
    """
    anchors: list[Anchor] = []
    segment_count: int = _get_segment_count(schema_def)
    typical_keys: tuple[str, ...] | None = schema_def.typical_keys
    for seg_idx in range(segment_count):
        bar: int = start_bar + seg_idx
        local_key: Key = _get_segment_key(
            home_key,
            seg_idx,
            typical_keys,
        )
        anchors.append(Anchor(
            bar_beat=f"{bar}.1",
            soprano_degree=CLAUSULA_ARRIVAL_SOPRANO,
            bass_degree=CLAUSULA_ARRIVAL_BASS,
            local_key=local_key,
            schema=schema_name,
            stage=seg_idx + 1,
        ))
    return anchors


def _get_segment_key(
    home_key: Key,
    segment_index: int,
    typical_keys: tuple[str, ...] | None,
) -> Key:
    """Get local key for a sequential schema segment.
    
    Uses typical_keys to determine key area for each segment.
    Falls back to home key if typical_keys not defined.
    """
    if typical_keys is None or len(typical_keys) == 0:
        return home_key
    key_idx: int = min(segment_index, len(typical_keys) - 1)
    key_area: str = typical_keys[key_idx]
    if key_area == "I" or key_area == "i":
        return home_key
    return home_key.modulate_to(key_area)
