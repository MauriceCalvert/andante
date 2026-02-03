"""Bridge: convert old planner output to new CompositionPlan.

This module enables the transition from the old realise_with_figuration
pipeline to the new compose_voices pipeline without modifying the planner.

Once Phase 7 is complete (planner produces VoicePlans directly), this
module can be deleted.
"""
from fractions import Fraction
from typing import Sequence
from builder.compose import compose_voices
from builder.types import (
    Anchor,
    AffectConfig,
    Composition,
    FormConfig,
    GenreConfig,
    KeyConfig,
    PassageAssignment,
)
from shared.constants import VOICE_RANGES
from shared.pitch import place_anchors_in_tessitura
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import (
    CompositionPlan,
    GapPlan,
    PlanAnchor,
    SectionPlan,
    VoicePlan,
    WritingMode,
)
from shared.voice_types import Range, Role

_DENSITY_MAP: dict[str, str] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
}
_CHARACTER_MAP: dict[str, str] = {
    "low": "plain",
    "medium": "expressive",
    "high": "energetic",
}


def realise_via_new_builder(
    anchors: Sequence[Anchor],
    passage_assignments: Sequence[PassageAssignment] | None,
    key_config: KeyConfig,
    affect_config: AffectConfig,
    genre_config: GenreConfig,
    form_config: FormConfig,
    total_bars: int,
    seed: int = 42,
    tempo_override: int | None = None,
) -> Composition:
    """Convert anchors to notes using the new compose_voices pipeline.

    This function has the same signature as realise_with_figuration
    to enable drop-in replacement.
    """
    if not anchors:
        return Composition(
            voices={"upper": (), "lower": ()},
            metre=genre_config.metre,
            tempo=72,
            upbeat=genre_config.upbeat,
        )
    upper_range: tuple[int, int] = VOICE_RANGES[0]
    lower_range: tuple[int, int] = VOICE_RANGES[3]
    placed_anchors: list[Anchor] = place_anchors_in_tessitura(
        list(anchors), upper_range, lower_range,
    )
    home_key: Key = placed_anchors[0].local_key
    plan_anchors: tuple[PlanAnchor, ...] = _convert_anchors(
        placed_anchors, home_key,
    )
    density: str = _DENSITY_MAP.get(affect_config.density, "medium")
    character: str = _CHARACTER_MAP.get(affect_config.density, "plain")
    upper_gaps: tuple[GapPlan, ...] = _build_gaps(
        plan_anchors, density, character, genre_config.metre,
        passage_assignments, is_upper=True,
    )
    lower_gaps: tuple[GapPlan, ...] = _build_gaps(
        plan_anchors, density, character, genre_config.metre,
        passage_assignments, is_upper=False,
    )
    upper_section: SectionPlan = SectionPlan(
        start_gap_index=0,
        end_gap_index=len(upper_gaps),
        schema_name=None,
        sequencing="independent",
        figure_profile=None,
        role=Role.SCHEMA_UPPER,
        follows=None,
        follow_interval=None,
        follow_delay=None,
        shared_actuator_with=None,
        gaps=upper_gaps,
    )
    lower_section: SectionPlan = SectionPlan(
        start_gap_index=0,
        end_gap_index=len(lower_gaps),
        schema_name=None,
        sequencing="independent",
        figure_profile=None,
        role=Role.SCHEMA_LOWER,
        follows=None,
        follow_interval=None,
        follow_delay=None,
        shared_actuator_with=None,
        gaps=lower_gaps,
    )
    tessitura_upper: int = (upper_range[0] + upper_range[1]) // 2
    tessitura_lower: int = (lower_range[0] + lower_range[1]) // 2
    upper_plan: VoicePlan = VoicePlan(
        voice_id="upper",
        actuator_range=Range(low=upper_range[0], high=upper_range[1]),
        tessitura_median=home_key.midi_to_diatonic(tessitura_upper),
        composition_order=0,
        seed=seed,
        metre=genre_config.metre,
        rhythmic_unit=Fraction(1, 8),
        sections=(upper_section,),
        anacrusis=None,
    )
    lower_plan: VoicePlan = VoicePlan(
        voice_id="lower",
        actuator_range=Range(low=lower_range[0], high=lower_range[1]),
        tessitura_median=home_key.midi_to_diatonic(tessitura_lower),
        composition_order=1,
        seed=seed + 1,
        metre=genre_config.metre,
        rhythmic_unit=Fraction(1, 8),
        sections=(lower_section,),
        anacrusis=None,
    )
    tempo: int = tempo_override if tempo_override else genre_config.tempo
    plan: CompositionPlan = CompositionPlan(
        home_key=home_key,
        tempo=tempo,
        upbeat=genre_config.upbeat,
        voice_plans=(upper_plan, lower_plan),
        anchors=plan_anchors,
    )
    return compose_voices(plan)


def _convert_anchors(
    anchors: Sequence[Anchor],
    home_key: Key,
) -> tuple[PlanAnchor, ...]:
    """Convert old Anchor sequence to PlanAnchor tuple."""
    result: list[PlanAnchor] = []
    for anchor in anchors:
        upper_midi: int = anchor.upper_midi if anchor.upper_midi else 60
        lower_midi: int = anchor.lower_midi if anchor.lower_midi else 48
        upper_pitch: DiatonicPitch = home_key.midi_to_diatonic(upper_midi)
        lower_pitch: DiatonicPitch = home_key.midi_to_diatonic(lower_midi)
        plan_anchor: PlanAnchor = PlanAnchor(
            bar_beat=anchor.bar_beat,
            upper_degree=anchor.upper_degree,
            lower_degree=anchor.lower_degree,
            upper_pitch=upper_pitch,
            lower_pitch=lower_pitch,
            local_key=anchor.local_key,
            schema=anchor.schema,
            stage=anchor.stage,
            upper_direction=anchor.upper_direction,
            lower_direction=anchor.lower_direction,
            section=anchor.section,
        )
        result.append(plan_anchor)
    return tuple(result)


def _build_gaps(
    anchors: tuple[PlanAnchor, ...],
    density: str,
    character: str,
    metre: str,
    passage_assignments: Sequence[PassageAssignment] | None,
    is_upper: bool,
) -> tuple[GapPlan, ...]:
    """Build GapPlan tuple for all gaps between anchors."""
    if len(anchors) < 2:
        return ()
    result: list[GapPlan] = []
    for i in range(len(anchors) - 1):
        source: PlanAnchor = anchors[i]
        target: PlanAnchor = anchors[i + 1]
        gap_duration: Fraction = _compute_gap_duration(
            source.bar_beat, target.bar_beat, metre,
        )
        bar_num: int = int(source.bar_beat.split(".")[0])
        interval: str = _compute_interval(source, target, is_upper)
        ascending: bool = _is_ascending(source, target, is_upper)
        writing_mode: WritingMode = _get_writing_mode(
            passage_assignments, bar_num, is_upper,
        )
        near_cadence: bool = _is_near_cadence(
            source, target, passage_assignments, bar_num,
        )
        gap: GapPlan = GapPlan(
            bar_num=bar_num,
            writing_mode=writing_mode,
            interval=interval,
            ascending=ascending,
            gap_duration=gap_duration,
            density=density if is_upper else "low",
            character=character,
            harmonic_tension="low",
            bar_function="passing",
            near_cadence=near_cadence,
            use_hemiola=False,
            overdotted=False,
            start_beat=1 if is_upper else 2,
            next_anchor_strength="strong",
            required_note_count=None,
            compound_allowed=False,
        )
        result.append(gap)
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
    """Compute diatonic interval name between source and target."""
    if is_upper:
        source_step: int = source.upper_pitch.step
        target_step: int = target.upper_pitch.step
    else:
        source_step = source.lower_pitch.step
        target_step = target.lower_pitch.step
    diff: int = target_step - source_step
    abs_diff: int = abs(diff)
    if abs_diff == 0:
        return "unison"
    direction: str = "up" if diff > 0 else "down"
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
    if abs_diff == 6:
        return f"seventh_{direction}"
    if abs_diff == 7:
        return f"octave_{direction}"
    return f"step_{direction}"


def _is_ascending(
    source: PlanAnchor,
    target: PlanAnchor,
    is_upper: bool,
) -> bool:
    """Determine if motion is ascending."""
    if is_upper:
        return target.upper_pitch.step > source.upper_pitch.step
    return target.lower_pitch.step > source.lower_pitch.step


def _get_writing_mode(
    passage_assignments: Sequence[PassageAssignment] | None,
    bar_num: int,
    is_upper: bool,
) -> WritingMode:
    """Determine writing mode from passage assignment."""
    if is_upper:
        return WritingMode.FIGURATION
    if passage_assignments is None:
        return WritingMode.PILLAR
    for pa in passage_assignments:
        if pa.start_bar <= bar_num < pa.end_bar:
            if pa.accompany_texture == "pillar":
                return WritingMode.PILLAR
            if pa.accompany_texture == "staggered":
                return WritingMode.STAGGERED
            if pa.accompany_texture == "walking":
                return WritingMode.FIGURATION
    return WritingMode.PILLAR


def _is_near_cadence(
    source: PlanAnchor,
    target: PlanAnchor,
    passage_assignments: Sequence[PassageAssignment] | None,
    bar_num: int,
) -> bool:
    """Determine if gap is near a cadence."""
    if "cadenz" in source.schema.lower():
        return True
    if "cadenz" in target.schema.lower():
        return True
    return False
