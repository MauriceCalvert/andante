"""Layer 4: Metric.

Category A: Pure functions, no I/O, no validation.
Input: Schema chain + genre sections + tonal plan
Output: Bar assignments + phrase-grouped anchors with transposition

Uses genre.sections for bar allocation (single source of truth per L017).
Applies tonal_plan for key area transposition.
Handles Subject/Answer relationship in exordium.
"""
from builder.types import Anchor, FormConfig, GenreConfig, KeyConfig, SchemaChain, SchemaConfig
from shared.key import Key


# Key area transpositions in semitones from tonic
KEY_AREA_SEMITONES: dict[str, int] = {
    "I": 0,
    "II": 2,
    "ii": 2,
    "III": 4,
    "iii": 4,
    "IV": 5,
    "iv": 5,
    "V": 7,
    "v": 7,
    "VI": 9,
    "vi": 9,
    "VII": 11,
    "vii": 11,
}


def layer_4_metric(
    schema_chain: SchemaChain,
    genre_config: GenreConfig,
    form_config: FormConfig,
    key_config: KeyConfig | None = None,
    schemas: dict[str, SchemaConfig] | None = None,
    tonal_plan: dict[str, tuple[str, ...]] | None = None,
    answer_interval: int = 7,
) -> tuple[dict[str, tuple[int, int]], list[Anchor], int]:
    """Execute Layer 4."""
    bar_assignments: dict[str, tuple[int, int]] = {}
    for section in genre_config.sections:
        section_name: str = section["name"]
        bars: list[int] = section["bars"]
        bar_assignments[section_name] = (bars[0], bars[1])
    total_bars: int = form_config.minimum_bars
    arrivals: list[Anchor] = []
    if key_config is None or schemas is None:
        return bar_assignments, arrivals, total_bars
    key: Key = _key_config_to_key(key_config)
    soprano_median: int = genre_config.tessitura.get("soprano", 70)
    bass_median: int = genre_config.tessitura.get("bass", 48)
    if tonal_plan is None:
        tonal_plan = {}
    section_anchors: list[Anchor] = _generate_section_anchors(
        genre_config.sections,
        schemas,
        key,
        soprano_median,
        bass_median,
        genre_config.metre,
        tonal_plan,
        answer_interval,
    )
    arrivals.extend(section_anchors)
    final_anchor: Anchor = _generate_final_cadence_anchor(
        total_bars,
        key,
        soprano_median,
        bass_median,
    )
    arrivals.append(final_anchor)
    covered_bars: set[int] = _get_covered_bars(arrivals)
    bridge_anchors: list[Anchor] = _generate_bridge_anchors(
        total_bars,
        covered_bars,
        arrivals,
        key,
        soprano_median,
        bass_median,
    )
    arrivals.extend(bridge_anchors)
    arrivals.sort(key=lambda a: (_bar_beat_to_float(a.bar_beat), a.soprano_midi))
    return bar_assignments, arrivals, total_bars


def _key_config_to_key(key_config: KeyConfig) -> Key:
    """Convert KeyConfig to Key object."""
    parts: list[str] = key_config.name.split()
    tonic: str = parts[0]
    mode: str = parts[1].lower() if len(parts) > 1 else "major"
    return Key(tonic=tonic, mode=mode)


def _degree_to_midi_with_octave(
    key: Key,
    degree: int,
    median: int,
    prev_pitch: int | None = None,
) -> int:
    """Convert scale degree to MIDI pitch near the median.

    When distances to median are equal, prefers pitch closer to prev_pitch
    (if provided) to maintain stepwise motion.
    """
    base_midi: int = key.degree_to_midi(degree, octave=4)
    pc: int = base_midi % 12
    candidates: list[tuple[int, int, int]] = []  # (midi, dist_to_median, dist_to_prev)
    for octave in range(2, 7):
        candidate: int = pc + (octave + 1) * 12
        dist_median: int = abs(candidate - median)
        dist_prev: int = abs(candidate - prev_pitch) if prev_pitch is not None else 0
        candidates.append((candidate, dist_median, dist_prev))
    if prev_pitch is not None:
        candidates.sort(key=lambda c: (c[1], c[2]))
    else:
        candidates.sort(key=lambda c: c[1])
    return candidates[0][0]


def _bar_beat_to_float(bar_beat: str) -> float:
    """Convert bar.beat string to float for sorting."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    return bar + (beat - 1) / 4.0


def _generate_final_cadence_anchor(
    total_bars: int,
    key: Key,
    soprano_median: int,
    bass_median: int,
) -> Anchor:
    """Generate final tonic cadence anchor on last bar beat 3."""
    s_midi: int = _degree_to_midi_with_octave(key, 1, soprano_median)
    b_midi: int = _degree_to_midi_with_octave(key, 1, bass_median)
    return Anchor(
        bar_beat=f"{total_bars}.3",
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
        section_name: str = section["name"]
        bars: list[int] = section["bars"]
        start_bar: int = bars[0]
        end_bar: int = bars[1]
        schema_sequence: list[str] = section.get("schema_sequence", [])
        real_schemas: list[str] = [s for s in schema_sequence if s != "episode"]
        if not real_schemas:
            continue
        key_areas: tuple[str, ...] = tonal_plan.get(section_name, ("I",))
        is_exordium: bool = section_name == "exordium"
        section_bars: int = end_bar - start_bar + 1
        bars_per_schema: int = max(1, section_bars // len(real_schemas))
        current_bar: int = start_bar
        for i, schema_name in enumerate(real_schemas):
            if schema_name not in schemas:
                continue
            schema_start: int = current_bar
            if i == len(real_schemas) - 1:
                schema_end = end_bar
            else:
                schema_end = min(current_bar + bars_per_schema - 1, end_bar)
            if is_exordium and i == 1:
                transposition: int = answer_interval
            elif i < len(key_areas):
                transposition = KEY_AREA_SEMITONES.get(key_areas[i], 0)
            else:
                transposition = KEY_AREA_SEMITONES.get(key_areas[-1], 0)
            schema_anchors: list[Anchor] = _generate_schema_anchors(
                schema_name,
                schemas[schema_name],
                schema_start,
                schema_end,
                key,
                soprano_median,
                bass_median,
                metre,
                transposition,
            )
            anchors.extend(schema_anchors)
            current_bar = schema_end + 1
            if current_bar > end_bar:
                break
    return anchors


def _generate_schema_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    end_bar: int,
    key: Key,
    soprano_median: int,
    bass_median: int,
    metre: str,
    transposition: int,
) -> list[Anchor]:
    """Generate anchors for a single schema with transposition."""
    if schema_def.sequential:
        return _generate_sequential_anchors(
            schema_name, schema_def, start_bar, end_bar,
            key, soprano_median, bass_median, metre, transposition,
        )
    anchors: list[Anchor] = []
    soprano_degrees: tuple[int, ...] = schema_def.soprano_degrees
    bass_degrees: tuple[int, ...] = schema_def.bass_degrees
    if not soprano_degrees or not bass_degrees:
        return anchors
    stages: int = len(soprano_degrees)
    bar_beats: list[str] = _distribute_arrivals(stages, start_bar, end_bar, metre)
    prev_soprano: int | None = None
    prev_bass: int | None = None
    for stage, bar_beat in enumerate(bar_beats):
        if stage >= len(soprano_degrees) or stage >= len(bass_degrees):
            break
        s_degree: int = soprano_degrees[stage]
        b_degree: int = bass_degrees[stage]
        s_raw: int = _degree_to_midi_with_octave(key, s_degree, soprano_median, prev_soprano)
        b_raw: int = _degree_to_midi_with_octave(key, b_degree, bass_median, prev_bass)
        prev_soprano = s_raw
        prev_bass = b_raw
        anchors.append(Anchor(
            bar_beat=bar_beat,
            soprano_midi=s_raw + transposition,
            bass_midi=b_raw + transposition,
            schema=schema_name,
            stage=stage + 1,
        ))
    return anchors


def _generate_sequential_anchors(
    schema_name: str,
    schema_def: SchemaConfig,
    start_bar: int,
    end_bar: int,
    key: Key,
    soprano_median: int,
    bass_median: int,
    metre: str,
    base_transposition: int,
) -> list[Anchor]:
    """Generate anchors for sequential schema (Monte, Fonte).

    Sequential schemas repeat a clausula cantizans pattern at ascending or
    descending pitch levels. Each segment produces TWO anchors:
      - Beat 1: approach (4,7) - passing motion
      - Beat 3: arrival (3,1) - consonant resolution

    Monte: ascending by step (IV -> V -> vi)
    Fonte: descending by step (ii -> I)
    """
    anchors: list[Anchor] = []
    available_bars: int = end_bar - start_bar + 1
    segment_count: int = _determine_segment_count(schema_def, available_bars)
    direction: str = schema_def.direction or "ascending"
    step_semitones: int = 2 if direction == "ascending" else -2
    approach_soprano: int = 4
    approach_bass: int = 7
    arrival_soprano: int = 3
    arrival_bass: int = 1
    bars_per_segment: int = max(1, available_bars // segment_count)
    prev_soprano: int | None = None
    prev_bass: int | None = None
    for seg_idx in range(segment_count):
        segment_bar: int = start_bar + (seg_idx * bars_per_segment)
        if segment_bar > end_bar:
            segment_bar = end_bar
        segment_transposition: int = base_transposition + (seg_idx * step_semitones)
        s_approach_raw: int = _degree_to_midi_with_octave(key, approach_soprano, soprano_median, prev_soprano)
        b_approach_raw: int = _degree_to_midi_with_octave(key, approach_bass, bass_median, prev_bass)
        prev_soprano = s_approach_raw
        prev_bass = b_approach_raw
        anchors.append(Anchor(
            bar_beat=f"{segment_bar}.1",
            soprano_midi=s_approach_raw + segment_transposition,
            bass_midi=b_approach_raw + segment_transposition,
            schema=schema_name,
            stage=(seg_idx * 2) + 1,
        ))
        s_arrival_raw: int = _degree_to_midi_with_octave(key, arrival_soprano, soprano_median, prev_soprano)
        b_arrival_raw: int = _degree_to_midi_with_octave(key, arrival_bass, bass_median, prev_bass)
        prev_soprano = s_arrival_raw
        prev_bass = b_arrival_raw
        anchors.append(Anchor(
            bar_beat=f"{segment_bar}.3",
            soprano_midi=s_arrival_raw + segment_transposition,
            bass_midi=b_arrival_raw + segment_transposition,
            schema=schema_name,
            stage=(seg_idx * 2) + 2,
        ))
    return anchors


def _determine_segment_count(schema_def: SchemaConfig, available_bars: int) -> int:
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


def distribute_arrivals(
    schema_name: str,
    stages: int,
    start_bar: int,
    end_bar: int,
    metre: str,
) -> list[str]:
    """Public wrapper for _distribute_arrivals (for test compatibility).

    Args:
        schema_name: Schema name (unused, kept for backward compat)
        stages: Number of arrival stages
        start_bar: First bar (1-indexed)
        end_bar: Last bar (1-indexed)
        metre: Time signature string

    Returns:
        List of bar.beat strings
    """
    return _distribute_arrivals(stages, start_bar, end_bar, metre)


def _distribute_arrivals(
    stages: int,
    start_bar: int,
    end_bar: int,
    metre: str,
) -> list[str]:
    """Distribute arrival beats across bars (internal)."""
    arrivals: list[str] = []
    if metre == "4/4":
        strong_beats: list[int] = [1, 3]
    else:
        strong_beats = [1]
    total_strong_beats: int = (end_bar - start_bar + 1) * len(strong_beats)
    if stages <= total_strong_beats:
        beat_idx: int = 0
        for stage in range(stages):
            bar: int = start_bar + beat_idx // len(strong_beats)
            beat: int = strong_beats[beat_idx % len(strong_beats)]
            arrivals.append(f"{bar}.{beat}")
            beat_idx += 1
    else:
        for stage in range(stages):
            bar: int = start_bar + stage // 4
            beat: int = (stage % 4) + 1
            arrivals.append(f"{bar}.{beat}")
    return arrivals


def _get_covered_bars(anchors: list[Anchor]) -> set[int]:
    """Get set of bars that have at least one anchor."""
    covered: set[int] = set()
    for anchor in anchors:
        bar: int = int(anchor.bar_beat.split(".")[0])
        covered.add(bar)
    return covered


def _generate_bridge_anchors(
    total_bars: int,
    covered_bars: set[int],
    existing_anchors: list[Anchor],
    key: Key,
    soprano_median: int,
    bass_median: int,
) -> list[Anchor]:
    """Generate bridge anchors for uncovered bars."""
    anchors: list[Anchor] = []
    uncovered: list[int] = [b for b in range(1, total_bars + 1) if b not in covered_bars]
    if not uncovered:
        return anchors
    anchor_by_bar: dict[int, Anchor] = {}
    for anchor in existing_anchors:
        bar: int = int(anchor.bar_beat.split(".")[0])
        if bar not in anchor_by_bar:
            anchor_by_bar[bar] = anchor
    tonic_soprano: int = _degree_to_midi_with_octave(key, 1, soprano_median)
    tonic_bass: int = _degree_to_midi_with_octave(key, 1, bass_median)
    dominant_soprano: int = _degree_to_midi_with_octave(key, 2, soprano_median)
    dominant_bass: int = _degree_to_midi_with_octave(key, 5, bass_median)
    for bar in uncovered:
        prev_bar: int | None = None
        next_bar: int | None = None
        for b in range(bar - 1, 0, -1):
            if b in anchor_by_bar:
                prev_bar = b
                break
        for b in range(bar + 1, total_bars + 1):
            if b in anchor_by_bar:
                next_bar = b
                break
        if prev_bar is not None and next_bar is not None:
            prev_anchor: Anchor = anchor_by_bar[prev_bar]
            next_anchor: Anchor = anchor_by_bar[next_bar]
            t: float = (bar - prev_bar) / (next_bar - prev_bar)
            s_midi: int = int(prev_anchor.soprano_midi + t * (next_anchor.soprano_midi - prev_anchor.soprano_midi))
            b_midi: int = int(prev_anchor.bass_midi + t * (next_anchor.bass_midi - prev_anchor.bass_midi))
            s_midi = _snap_to_key(s_midi, key)
            b_midi = _snap_to_key(b_midi, key)
        elif prev_bar is not None:
            prev_anchor = anchor_by_bar[prev_bar]
            bars_to_end: int = total_bars - bar
            if bars_to_end <= 2:
                s_midi = dominant_soprano
                b_midi = dominant_bass
            else:
                s_midi = prev_anchor.soprano_midi
                b_midi = prev_anchor.bass_midi
        elif next_bar is not None:
            next_anchor = anchor_by_bar[next_bar]
            s_midi = next_anchor.soprano_midi
            b_midi = next_anchor.bass_midi
        else:
            s_midi = tonic_soprano
            b_midi = tonic_bass
        anchors.append(Anchor(
            bar_beat=f"{bar}.1",
            soprano_midi=s_midi,
            bass_midi=b_midi,
            schema="bridge",
            stage=1,
        ))
        if bar < total_bars:
            anchors.append(Anchor(
                bar_beat=f"{bar}.3",
                soprano_midi=s_midi,
                bass_midi=b_midi,
                schema="bridge",
                stage=2,
            ))
    return anchors


def _snap_to_key(midi: int, key: Key) -> int:
    """Snap MIDI pitch to nearest pitch in key."""
    pc: int = midi % 12
    key_pcs: set[int] = set()
    for degree in range(1, 8):
        degree_midi: int = key.degree_to_midi(degree, octave=0)
        key_pcs.add(degree_midi % 12)
    if pc in key_pcs:
        return midi
    for offset in [1, -1, 2, -2]:
        if (pc + offset) % 12 in key_pcs:
            return midi + offset
    return midi
