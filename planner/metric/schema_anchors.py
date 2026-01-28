"""Schema anchor generation."""
from fractions import Fraction

from builder.types import Anchor, SchemaConfig
from planner.metric.constants import CLAUSULA_ARRIVAL_BASS, CLAUSULA_ARRIVAL_SOPRANO
from shared.key import Key


def _compute_upbeat_bar_beat(start_bar: int, upbeat: Fraction, metre: str) -> tuple[int, int]:
    """Compute bar and beat for first anchor with upbeat.
    
    For gavotte with upbeat=1/2 in 4/4:
        - start_bar=1, upbeat=1/2 -> bar 0, beat 3
    """
    if upbeat == 0:
        return start_bar, 1
    num, den = (int(x) for x in metre.split("/"))
    beats_per_bar: int = num
    upbeat_beats: int = int(upbeat * beats_per_bar * den / 4)
    first_beat: int = beats_per_bar - upbeat_beats + 1
    return start_bar - 1, first_beat


def generate_schema_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    end_bar: int,
    home_key: Key,
    metre: str,
    upbeat: Fraction = Fraction(0),
    section: str = "",
) -> list[Anchor]:
    """Generate anchors for a schema: one anchor per bar, one stage per bar."""
    if schema_def.sequential:
        return _generate_sequential_anchors(
            schema_name,
            schema_def,
            start_bar,
            home_key,
            upbeat,
            metre,
            section,
        )
    return _generate_regular_anchors(
        schema_name,
        schema_def,
        start_bar,
        home_key,
        upbeat,
        metre,
        section,
    )


def _generate_regular_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    local_key: Key,
    upbeat: Fraction = Fraction(0),
    metre: str = "4/4",
    section: str = "",
) -> list[Anchor]:
    """Generate anchors for regular (non-sequential) schema.
    
    With upbeat: first anchor at (bar 0, beat 3), then bar 1, bar 2, etc.
    Without upbeat: anchors at bar 1, bar 2, bar 3, etc.
    
    Directions come from schema definition, same length as degrees.
    First degree has direction=None; subsequent degrees have explicit direction.
    """
    anchors: list[Anchor] = []
    soprano_degrees: tuple[int, ...] = schema_def.soprano_degrees
    bass_degrees: tuple[int, ...] = schema_def.bass_degrees
    soprano_directions: tuple[str | None, ...] = schema_def.soprano_directions
    bass_directions: tuple[str | None, ...] = schema_def.bass_directions
    if not soprano_degrees or not bass_degrees:
        return anchors
    stages: int = len(soprano_degrees)
    for stage in range(stages):
        if stage == 0 and upbeat > 0:
            bar, beat = _compute_upbeat_bar_beat(start_bar, upbeat, metre)
        else:
            bar = start_bar + stage - (1 if upbeat > 0 else 0)
            beat = 1
        # Get direction for this stage (None for first, explicit for rest)
        upper_dir: str | None = soprano_directions[stage] if stage < len(soprano_directions) else None
        lower_dir: str | None = bass_directions[stage] if stage < len(bass_directions) else None
        anchors.append(Anchor(
            bar_beat=f"{bar}.{beat}",
            upper_degree=soprano_degrees[stage],
            lower_degree=bass_degrees[stage],
            local_key=local_key,
            schema=schema_name,
            stage=stage + 1,
            upper_direction=upper_dir,
            lower_direction=lower_dir,
            section=section,
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
    upbeat: Fraction = Fraction(0),
    metre: str = "4/4",
    section: str = "",
) -> list[Anchor]:
    """Generate anchors for sequential schema (Monte, Fonte).
    
    Each segment uses fixed clausula arrival degrees (3,1) in its local key.
    The soprano rises E->F#->G because the key rises (IV->V->vi in G major),
    NOT because the degree changes.
    
    Example for monte in G major with typical_keys="IV -> V (-> vi)":
        Segment 1: key=C (IV), degree 3 -> E
        Segment 2: key=D (V), degree 3 -> F#
        Segment 3: key=Em (vi), degree 3 -> G
    
    With upbeat: first anchor at (bar 0, beat 3), then bar 1, bar 2, etc.
    
    For sequential schemas, segment_direction indicates motion between segments.
    First segment has None direction; subsequent segments use segment_direction.
    """
    anchors: list[Anchor] = []
    segment_count: int = _get_segment_count(schema_def)
    typical_keys: tuple[str, ...] | None = schema_def.typical_keys
    segment_direction: str | None = schema_def.segment_direction
    for seg_idx in range(segment_count):
        if seg_idx == 0 and upbeat > 0:
            bar, beat = _compute_upbeat_bar_beat(start_bar, upbeat, metre)
        else:
            bar = start_bar + seg_idx - (1 if upbeat > 0 else 0)
            beat = 1
        local_key: Key = _get_segment_key(
            home_key,
            seg_idx,
            typical_keys,
        )
        # First segment has no direction; subsequent segments use segment_direction
        upper_dir: str | None = segment_direction if seg_idx > 0 else None
        lower_dir: str | None = segment_direction if seg_idx > 0 else None
        anchors.append(Anchor(
            bar_beat=f"{bar}.{beat}",
            upper_degree=CLAUSULA_ARRIVAL_SOPRANO,
            lower_degree=CLAUSULA_ARRIVAL_BASS,
            local_key=local_key,
            schema=schema_name,
            stage=seg_idx + 1,
            upper_direction=upper_dir,
            lower_direction=lower_dir,
            section=section,
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
