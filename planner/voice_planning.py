"""Voice planning: build CompositionPlan from planner output.

Layer 6 equivalent: converts anchors and passage assignments into
the VoicePlan contract for the new builder.

Replaces bridge.py with richer section detection, sequencing assignment,
and affect-driven GapPlan parameters.
"""
from fractions import Fraction
from typing import Sequence
from builder.types import (
    Anchor,
    AffectConfig,
    FormConfig,
    GenreConfig,
    KeyConfig,
    PassageAssignment,
    SchemaConfig,
)
from shared.constants import (
    DENSITY_RHYTHMIC_UNIT,
    INTERVAL_DIATONIC_SIZE,
    MIN_FIGURATION_NOTES,
    SMALL_INTERVAL_NOTE_REDUCTION,
    VOICE_RANGES,
)
from shared.key import Key

from shared.plan_types import (
    AnacrusisPlan,
    CompositionPlan,
    GapPlan,
    PlanAnchor,
    SectionPlan,
    VoicePlan,
    WritingMode,
)
from shared.voice_types import Range, Role

_DENSITY_FROM_AFFECT: dict[str, str] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
}
_CHARACTER_FROM_AFFECT: dict[str, str] = {
    "low": "plain",
    "medium": "expressive",
    "high": "energetic",
}
_FUNCTION_TO_DENSITY: dict[str, str] = {
    "subject": "medium",
    "answer": "medium",
    "episode": "high",
    "coda": "low",
    "cadential": "low",
    "sequence": "high",
    "development": "high",
    "recapitulation": "medium",
}
_FUNCTION_TO_CHARACTER: dict[str, str] = {
    "subject": "plain",
    "answer": "plain",
    "episode": "energetic",
    "coda": "plain",
    "cadential": "expressive",
    "sequence": "energetic",
    "development": "energetic",
    "recapitulation": "plain",
}
TRACK_SOPRANO: int = 0
TRACK_BASS: int = 3


def build_composition_plan(
    anchors: Sequence[Anchor],
    passage_assignments: Sequence[PassageAssignment] | None,
    key_config: KeyConfig,
    affect_config: AffectConfig,
    genre_config: GenreConfig,
    schemas: dict[str, SchemaConfig] | None = None,
    seed: int = 42,
    tempo_override: int | None = None,
) -> CompositionPlan:
    """Build a CompositionPlan from planner layer outputs.

    This is the main entry point for Phase 7 voice planning.
    """
    if not anchors:
        home_key: Key = _key_config_to_key(key_config)
        return _empty_plan(home_key, genre_config, tempo_override)
    upper_range: tuple[int, int] = VOICE_RANGES[TRACK_SOPRANO]
    lower_range: tuple[int, int] = VOICE_RANGES[TRACK_BASS]
    home_key = anchors[0].local_key
    plan_anchors: tuple[PlanAnchor, ...] = _convert_anchors(anchors)
    schema_sections: list[tuple[int, int, str]] = _detect_schema_sections(plan_anchors)
    base_density: str = _DENSITY_FROM_AFFECT.get(affect_config.density, "medium")
    base_character: str = _CHARACTER_FROM_AFFECT.get(affect_config.density, "plain")
    upper_sections: tuple[SectionPlan, ...] = _build_sections(
        plan_anchors=plan_anchors,
        schema_sections=schema_sections,
        passage_assignments=passage_assignments,
        schemas=schemas,
        base_density=base_density,
        base_character=base_character,
        metre=genre_config.metre,
        is_upper=True,
        affect_config=affect_config,
    )
    lower_sections: tuple[SectionPlan, ...] = _build_sections(
        plan_anchors=plan_anchors,
        schema_sections=schema_sections,
        passage_assignments=passage_assignments,
        schemas=schemas,
        base_density=base_density,
        base_character=base_character,
        metre=genre_config.metre,
        is_upper=False,
        affect_config=affect_config,
        bass_treatment=genre_config.bass_treatment,
    )
    tessitura_upper: int = (upper_range[0] + upper_range[1]) // 2
    tessitura_lower: int = (lower_range[0] + lower_range[1]) // 2
    anacrusis: AnacrusisPlan | None = None
    if genre_config.upbeat > Fraction(0) and plan_anchors:
        anacrusis = AnacrusisPlan(
            target_degree=plan_anchors[0].upper_degree,
            duration=genre_config.upbeat,
            note_count=max(1, int(genre_config.upbeat / Fraction(1, 8))),
            ascending=True,
        )
    upper_plan: VoicePlan = VoicePlan(
        voice_id="upper",
        actuator_range=Range(low=upper_range[0], high=upper_range[1]),
        tessitura_median=tessitura_upper,
        composition_order=TRACK_SOPRANO,
        seed=seed,
        metre=genre_config.metre,
        rhythmic_unit=Fraction(1, 8),
        sections=upper_sections,
        anacrusis=anacrusis,
    )
    bass_pattern_name: str | None = (
        genre_config.bass_pattern
        if genre_config.bass_treatment == "patterned"
        else None
    )
    lower_plan: VoicePlan = VoicePlan(
        voice_id="lower",
        actuator_range=Range(low=lower_range[0], high=lower_range[1]),
        tessitura_median=tessitura_lower,
        composition_order=TRACK_BASS,
        seed=seed + 1,
        metre=genre_config.metre,
        rhythmic_unit=Fraction(1, 8),
        sections=lower_sections,
        anacrusis=None,
        bass_pattern=bass_pattern_name,
    )
    tempo: int = tempo_override if tempo_override else genre_config.tempo
    return CompositionPlan(
        home_key=home_key,
        tempo=tempo,
        upbeat=genre_config.upbeat,
        voice_plans=(upper_plan, lower_plan),
        anchors=plan_anchors,
    )


def _empty_plan(
    home_key: Key,
    genre_config: GenreConfig,
    tempo_override: int | None,
) -> CompositionPlan:
    """Create an empty plan for edge cases."""
    tempo: int = tempo_override if tempo_override else genre_config.tempo
    return CompositionPlan(
        home_key=home_key,
        tempo=tempo,
        upbeat=genre_config.upbeat,
        voice_plans=(),
        anchors=(),
    )


def _key_config_to_key(key_config: KeyConfig) -> Key:
    """Convert KeyConfig to Key object."""
    parts: list[str] = key_config.name.split()
    tonic: str = parts[0]
    mode: str = parts[1].lower() if len(parts) > 1 else "major"
    return Key(tonic=tonic, mode=mode)


def _convert_anchors(
    anchors: Sequence[Anchor],
) -> tuple[PlanAnchor, ...]:
    """Convert old Anchor sequence to PlanAnchor tuple."""
    result: list[PlanAnchor] = []
    for anchor in anchors:
        plan_anchor: PlanAnchor = PlanAnchor(
            bar_beat=anchor.bar_beat,
            upper_degree=anchor.upper_degree,
            lower_degree=anchor.lower_degree,
            local_key=anchor.local_key,
            schema=anchor.schema,
            stage=anchor.stage,
            upper_direction=anchor.upper_direction,
            lower_direction=anchor.lower_direction,
            section=anchor.section,
        )
        result.append(plan_anchor)
    return tuple(result)


def _detect_schema_sections(
    anchors: tuple[PlanAnchor, ...],
) -> list[tuple[int, int, str]]:
    """Detect contiguous sections by schema name.

    Returns list of (start_gap_idx, end_gap_idx, schema_name).
    """
    if len(anchors) < 2:
        return []
    sections: list[tuple[int, int, str]] = []
    current_schema: str = anchors[0].schema
    section_start: int = 0
    for i in range(1, len(anchors)):
        if anchors[i].schema != current_schema:
            sections.append((section_start, i, current_schema))
            current_schema = anchors[i].schema
            section_start = i
    sections.append((section_start, len(anchors) - 1, current_schema))
    return sections


def _build_sections(
    plan_anchors: tuple[PlanAnchor, ...],
    schema_sections: list[tuple[int, int, str]],
    passage_assignments: Sequence[PassageAssignment] | None,
    schemas: dict[str, SchemaConfig] | None,
    base_density: str,
    base_character: str,
    metre: str,
    is_upper: bool,
    affect_config: AffectConfig,
    bass_treatment: str = "contrapuntal",
) -> tuple[SectionPlan, ...]:
    """Build SectionPlan tuple for a voice."""
    if not schema_sections:
        if len(plan_anchors) < 2:
            return ()
        gaps: tuple[GapPlan, ...] = _build_gaps_for_range(
            plan_anchors=plan_anchors,
            start_idx=0,
            end_idx=len(plan_anchors) - 1,
            passage_assignments=passage_assignments,
            base_density=base_density,
            base_character=base_character,
            metre=metre,
            is_upper=is_upper,
            affect_config=affect_config,
            bass_treatment=bass_treatment,
        )
        section: SectionPlan = SectionPlan(
            start_gap_index=0,
            end_gap_index=len(plan_anchors) - 1,
            schema_name=None,
            sequencing="independent",
            figure_profile=None,
            role=Role.SCHEMA_UPPER if is_upper else Role.SCHEMA_LOWER,
            follows=None,
            follow_interval=None,
            follow_delay=None,
            shared_actuator_with=None,
            gaps=gaps,
        )
        return (section,)
    result: list[SectionPlan] = []
    num_sections: int = len(schema_sections)
    for idx, (start_idx, end_idx, schema_name) in enumerate(schema_sections):
        if start_idx >= end_idx:
            continue
        sequencing: str = _get_sequencing(schema_name, schemas)
        is_final: bool = idx == num_sections - 1
        gaps = _build_gaps_for_range(
            plan_anchors=plan_anchors,
            start_idx=start_idx,
            end_idx=end_idx,
            passage_assignments=passage_assignments,
            base_density=base_density,
            base_character=base_character,
            metre=metre,
            is_upper=is_upper,
            affect_config=affect_config,
            is_final_section=is_final,
            bass_treatment=bass_treatment,
        )
        section = SectionPlan(
            start_gap_index=start_idx,
            end_gap_index=end_idx,
            schema_name=schema_name,
            sequencing=sequencing,
            figure_profile=None,
            role=Role.SCHEMA_UPPER if is_upper else Role.SCHEMA_LOWER,
            follows=None,
            follow_interval=None,
            follow_delay=None,
            shared_actuator_with=None,
            gaps=gaps,
        )
        result.append(section)
    return tuple(result)


def _get_sequencing(
    schema_name: str,
    schemas: dict[str, SchemaConfig] | None,
) -> str:
    """Determine sequencing strategy from schema properties."""
    if schemas is None or schema_name not in schemas:
        return "independent"
    schema: SchemaConfig = schemas[schema_name]
    if schema.sequential:
        return "repeating"
    return "independent"


def _build_gaps_for_range(
    plan_anchors: tuple[PlanAnchor, ...],
    start_idx: int,
    end_idx: int,
    passage_assignments: Sequence[PassageAssignment] | None,
    base_density: str,
    base_character: str,
    metre: str,
    is_upper: bool,
    affect_config: AffectConfig,
    is_final_section: bool = False,
    bass_treatment: str = "contrapuntal",
) -> tuple[GapPlan, ...]:
    """Build GapPlan tuple for gaps in [start_idx, end_idx)."""
    result: list[GapPlan] = []
    for i in range(start_idx, end_idx):
        source: PlanAnchor = plan_anchors[i]
        target: PlanAnchor = plan_anchors[i + 1]
        bar_num: int = int(source.bar_beat.split(".")[0])
        gap_duration: Fraction = _compute_gap_duration(
            source.bar_beat, target.bar_beat, metre,
        )
        interval: str = _compute_interval(source, target, is_upper)
        ascending: bool = _is_ascending(source, target, is_upper)
        near_cadence: bool = _is_near_cadence(source, target)
        writing_mode: WritingMode = _get_writing_mode(
            passage_assignments, bar_num, is_upper, near_cadence, interval,
            bass_treatment=bass_treatment,
        )
        function: str = _get_function(passage_assignments, bar_num)
        is_lead: bool = _is_lead_voice(passage_assignments, bar_num, is_upper)
        density: str = _get_density(base_density, function, is_lead)
        character: str = _get_character(base_character, function)
        use_hemiola: bool = _should_use_hemiola(
            affect_config, near_cadence, metre,
        )
        note_count: int | None = (
            _compute_note_count(gap_duration, density, interval)
            if writing_mode == WritingMode.FIGURATION
            else None
        )
        gap: GapPlan = GapPlan(
            bar_num=bar_num,
            writing_mode=writing_mode,
            interval=interval,
            ascending=ascending,
            gap_duration=gap_duration,
            density=density,
            character=character,
            harmonic_tension="low",
            bar_function=_get_bar_function(source, near_cadence),
            near_cadence=near_cadence,
            use_hemiola=use_hemiola,
            overdotted=affect_config.density == "high",
            start_beat=1 if is_upper else 2,
            next_anchor_strength="strong" if near_cadence else "weak",
            required_note_count=note_count,
            compound_allowed=False,
        )
        result.append(gap)
    if is_final_section and end_idx < len(plan_anchors):
        final_anchor: PlanAnchor = plan_anchors[end_idx]
        final_bar: int = int(final_anchor.bar_beat.split(".")[0])
        final_gap: GapPlan = GapPlan(
            bar_num=final_bar,
            writing_mode=WritingMode.PILLAR,
            interval="unison",
            ascending=False,
            gap_duration=Fraction(1),
            density="low",
            character="plain",
            harmonic_tension="low",
            bar_function="final",
            near_cadence=True,
            use_hemiola=False,
            overdotted=False,
            start_beat=1,
            next_anchor_strength="strong",
            required_note_count=1,
            compound_allowed=False,
        )
        result.append(final_gap)
    return tuple(result)


def _compute_gap_duration(
    source_bar_beat: str,
    target_bar_beat: str,
    metre: str,
) -> Fraction:
    """Compute duration between two bar.beat positions."""
    source_offset: Fraction = _bar_beat_to_offset(source_bar_beat, metre)
    target_offset: Fraction = _bar_beat_to_offset(target_bar_beat, metre)
    return target_offset - source_offset


def _bar_beat_to_offset(bar_beat: str, metre: str) -> Fraction:
    """Convert 'bar.beat' string to absolute offset in whole notes."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: int = int(parts[1])
    num_str, den_str = metre.split("/")
    den: int = int(den_str)
    num: int = int(num_str)
    bar_length: Fraction = Fraction(num, den)
    beat_unit: Fraction = Fraction(1, den)
    return (bar - 1) * bar_length + (beat - 1) * beat_unit


def _compute_interval(
    source: PlanAnchor,
    target: PlanAnchor,
    is_upper: bool,
) -> str:
    """Compute diatonic interval name between source and target.
    
    Uses degrees and direction hints. Direction hint determines whether
    motion is ascending or descending. Degree difference gives interval size.
    """
    if is_upper:
        source_deg: int = source.upper_degree
        target_deg: int = target.upper_degree
        direction_hint: str | None = target.upper_direction
    else:
        source_deg = source.lower_degree
        target_deg = target.lower_degree
        direction_hint = target.lower_direction
    raw_diff: int = target_deg - source_deg
    if raw_diff == 0:
        return "unison"
    if direction_hint == "up":
        if raw_diff <= 0:
            raw_diff += 7
        direction = "up"
    elif direction_hint == "down":
        if raw_diff >= 0:
            raw_diff -= 7
        direction = "down"
    elif direction_hint == "same":
        return "unison"
    else:
        direction = "up" if raw_diff > 0 else "down"
    abs_diff: int = abs(raw_diff)
    if abs_diff == 0:
        return "unison"
    if abs_diff >= 7:
        return f"octave_{direction}"
    if abs_diff == 1:
        return f"step_{direction}"
    if abs_diff == 2:
        return f"third_{direction}"
    if abs_diff == 3:
        return f"fourth_{direction}"
    if abs_diff == 4:
        return f"fifth_{direction}"
    if abs_diff == 5:
        return f"sixth_{direction}"
    return f"sixth_{direction}"


def _is_ascending(
    source: PlanAnchor,
    target: PlanAnchor,
    is_upper: bool,
) -> bool:
    """Determine if motion is ascending using direction hint."""
    if is_upper:
        direction: str | None = target.upper_direction
        raw_diff: int = target.upper_degree - source.upper_degree
    else:
        direction = target.lower_direction
        raw_diff = target.lower_degree - source.lower_degree
    if direction == "up":
        return True
    if direction == "down":
        return False
    return raw_diff > 0


_CADENTIAL_INTERVALS: frozenset[str] = frozenset({
    "unison", "step_up", "step_down", "third_up", "third_down",
})


def _get_writing_mode(
    passage_assignments: Sequence[PassageAssignment] | None,
    bar_num: int,
    is_upper: bool,
    near_cadence: bool = False,
    interval: str = "unison",
    bass_treatment: str = "contrapuntal",
) -> WritingMode:
    """Determine writing mode from passage assignment and lead voice.

    Near cadence: both voices use CADENTIAL if interval has cadential figures.
    Lead voice gets FIGURATION; accompany voice gets the accompany_texture.
    Patterned bass: lower voice uses ARPEGGIATED instead of PILLAR.
    Default: upper leads with FIGURATION, lower accompanies with PILLAR.
    """
    if near_cadence and interval in _CADENTIAL_INTERVALS:
        return WritingMode.CADENTIAL
    bass_patterned: bool = bass_treatment == "patterned" and not is_upper
    if passage_assignments is None:
        if is_upper:
            return WritingMode.FIGURATION
        return WritingMode.ARPEGGIATED if bass_patterned else WritingMode.PILLAR
    for pa in passage_assignments:
        if pa.start_bar <= bar_num < pa.end_bar:
            lead: int | None = pa.lead_voice
            is_lead: bool = (lead == 0 and is_upper) or (lead == 1 and not is_upper)
            if lead is None:
                is_lead = is_upper
            if is_lead:
                return WritingMode.FIGURATION
            texture: str | None = pa.accompany_texture
            if texture == "pillar":
                return WritingMode.ARPEGGIATED if bass_patterned else WritingMode.PILLAR
            if texture == "staggered":
                return WritingMode.STAGGERED
            if texture == "walking":
                return WritingMode.FIGURATION
            if texture == "complementary":
                return WritingMode.FIGURATION
            return WritingMode.ARPEGGIATED if bass_patterned else WritingMode.PILLAR
    if is_upper:
        return WritingMode.FIGURATION
    return WritingMode.ARPEGGIATED if bass_patterned else WritingMode.PILLAR


def _is_near_cadence(source: PlanAnchor, target: PlanAnchor) -> bool:
    """Determine if gap is near a cadence."""
    if "cadenz" in source.schema.lower():
        return True
    if "cadenz" in target.schema.lower():
        return True
    return False


def _get_function(
    passage_assignments: Sequence[PassageAssignment] | None,
    bar_num: int,
) -> str:
    """Get passage function for a bar."""
    if passage_assignments is None:
        return "subject"
    for pa in passage_assignments:
        if pa.start_bar <= bar_num < pa.end_bar:
            return pa.function
    return "subject"


def _is_lead_voice(
    passage_assignments: Sequence[PassageAssignment] | None,
    bar_num: int,
    is_upper: bool,
) -> bool:
    """Determine if this voice is the lead for the current bar."""
    if passage_assignments is None:
        return is_upper
    for pa in passage_assignments:
        if pa.start_bar <= bar_num < pa.end_bar:
            lead: int | None = pa.lead_voice
            if lead is None:
                return is_upper
            return (lead == 0 and is_upper) or (lead == 1 and not is_upper)
    return is_upper


def _base_note_count(gap_duration: Fraction, density: str) -> int:
    """Compute base note count from gap duration and density."""
    unit: Fraction = DENSITY_RHYTHMIC_UNIT.get(density, Fraction(1, 8))
    count: Fraction = gap_duration / unit
    if count == int(count) and count >= 1:
        return int(count)
    # Preferred unit doesn't divide evenly; eighth note divides all standard gaps
    fallback: Fraction = Fraction(1, 8)
    count = gap_duration / fallback
    assert count == int(count) and count >= 1, (
        f"Gap duration {gap_duration} not divisible by fallback unit {fallback}"
    )
    return int(count)


def _compute_note_count(
    gap_duration: Fraction,
    density: str,
    interval: str,
) -> int:
    """Compute target note count for a figuration gap.

    Small intervals (unison, step, third) reduce from base count because
    less pitch space needs fewer fill notes.  Large intervals (fourth+)
    keep the full base count — their figure vocabulary only has viable
    fills at specific sizes.
    """
    base: int = _base_note_count(gap_duration, density)
    interval_size: int = INTERVAL_DIATONIC_SIZE.get(interval, 0)
    reduction: int = SMALL_INTERVAL_NOTE_REDUCTION.get(interval_size, 0)
    return max(MIN_FIGURATION_NOTES, base - reduction)


def _get_density(base_density: str, function: str, is_lead: bool) -> str:
    """Get density based on function and whether voice is leading."""
    if not is_lead:
        return "low"
    return _FUNCTION_TO_DENSITY.get(function, base_density)


def _get_character(base_character: str, function: str) -> str:
    """Get character based on function."""
    return _FUNCTION_TO_CHARACTER.get(function, base_character)


def _should_use_hemiola(
    affect_config: AffectConfig,
    near_cadence: bool,
    metre: str,
) -> bool:
    """Determine if hemiola should be used."""
    if not near_cadence:
        return False
    if metre not in ("3/4", "6/8", "3/2"):
        return False
    return affect_config.density in ("medium", "high")


def _get_bar_function(source: PlanAnchor, near_cadence: bool) -> str:
    """Determine bar function from context."""
    if near_cadence:
        return "cadential"
    if "arrival" in source.schema.lower():
        return "schema_arrival"
    return "passing"
