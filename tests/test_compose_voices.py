"""Unit tests for builder/compose.py — gap scheduler and compose_voices path."""
import pytest
from fractions import Fraction

from builder.compose import (
    GapTask,
    _build_gap_schedule,
    _section_is_lead,
    compose_voices,
)
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


# =========================================================================
# Helpers — minimal plan objects
# =========================================================================


def _make_gap(
    bar_num: int = 1,
    mode: WritingMode = WritingMode.PILLAR,
    density: str = "low",
) -> GapPlan:
    """Minimal GapPlan for scheduling tests."""
    return GapPlan(
        bar_num=bar_num,
        writing_mode=mode,
        interval="unison",
        ascending=True,
        gap_duration=Fraction(1, 2),
        density=density,
        character="plain",
        harmonic_tension="low",
        bar_function="continuation",
        near_cadence=False,
        use_hemiola=False,
        start_beat=1,
        next_anchor_strength="weak",
        required_note_count=None,
        compound_allowed=False,
    )


def _make_section(
    start: int,
    end: int,
    role: Role = Role.SCHEMA_UPPER,
    density: str = "high",
) -> SectionPlan:
    """Minimal SectionPlan with gaps."""
    gap_count: int = end - start
    gaps: tuple[GapPlan, ...] = tuple(
        _make_gap(bar_num=start + i + 1, density=density) for i in range(gap_count)
    )
    return SectionPlan(
        start_gap_index=start,
        end_gap_index=end,
        schema_name="do_re_mi",
        sequencing="none",
        figure_profile=None,
        role=role,
        follows=None,
        follow_interval=None,
        follow_delay=None,
        shared_actuator_with=None,
        gaps=gaps,
    )


def _make_anchor(stage: int) -> PlanAnchor:
    """Minimal PlanAnchor."""
    return PlanAnchor(
        bar_beat=f"{stage}.1",
        upper_degree=1,
        lower_degree=1,
        local_key=Key(tonic="C", mode="major"),
        schema="do_re_mi",
        stage=stage,
    )


def _make_voice_plan(
    voice_id: str,
    order: int,
    sections: tuple[SectionPlan, ...],
    track: int = 0,
) -> VoicePlan:
    """Minimal VoicePlan."""
    return VoicePlan(
        voice_id=voice_id,
        actuator_range=Range(low=55, high=84),
        tessitura_median=70,
        composition_order=order,
        midi_track=track,
        seed=42,
        metre="3/4",
        rhythmic_unit=Fraction(1, 4),
        sections=sections,
        anacrusis=None,
    )


# =========================================================================
# _section_is_lead
# =========================================================================


def test_section_is_lead_high_density() -> None:
    """Section with majority high-density gaps is lead."""
    section: SectionPlan = _make_section(start=0, end=3, density="high")
    assert _section_is_lead(section=section) is True


def test_section_is_lead_low_density() -> None:
    """Section with all low-density gaps is not lead."""
    section: SectionPlan = _make_section(start=0, end=3, density="low")
    assert _section_is_lead(section=section) is False


def test_section_is_lead_imitative_never_lead() -> None:
    """IMITATIVE sections are never lead regardless of density."""
    section: SectionPlan = SectionPlan(
        start_gap_index=0,
        end_gap_index=2,
        schema_name="do_re_mi",
        sequencing="none",
        figure_profile=None,
        role=Role.IMITATIVE,
        follows="soprano",
        follow_interval=7,
        follow_delay=Fraction(1, 2),
        shared_actuator_with=None,
        gaps=(_make_gap(density="high"), _make_gap(density="high")),
    )
    assert _section_is_lead(section=section) is False


def test_section_is_lead_empty_gaps() -> None:
    """Section with no gaps counts as lead."""
    section: SectionPlan = SectionPlan(
        start_gap_index=0,
        end_gap_index=0,
        schema_name=None,
        sequencing="none",
        figure_profile=None,
        role=Role.SCHEMA_UPPER,
        follows=None,
        follow_interval=None,
        follow_delay=None,
        shared_actuator_with=None,
        gaps=(),
    )
    assert _section_is_lead(section=section) is True


# =========================================================================
# _build_gap_schedule — ordering invariants
# =========================================================================


def test_gap_schedule_lead_before_follower() -> None:
    """At each anchor, lead voice gaps are scheduled before follower gaps."""
    anchors: tuple[PlanAnchor, ...] = tuple(_make_anchor(stage=i) for i in range(4))
    soprano_section: SectionPlan = _make_section(
        start=0, end=3, role=Role.SCHEMA_UPPER, density="high",
    )
    bass_section: SectionPlan = _make_section(
        start=0, end=3, role=Role.SCHEMA_LOWER, density="low",
    )
    plan: CompositionPlan = CompositionPlan(
        home_key=Key(tonic="C", mode="major"),
        tempo=80,
        upbeat=Fraction(0),
        voice_plans=(
            _make_voice_plan(
                voice_id="soprano",
                order=0,
                sections=(soprano_section,),
                track=0,
            ),
            _make_voice_plan(
                voice_id="bass",
                order=1,
                sections=(bass_section,),
                track=3,
            ),
        ),
        anchors=anchors,
    )
    schedule: list[GapTask] = _build_gap_schedule(plan=plan)
    assert len(schedule) == 6  # 3 gaps x 2 voices
    # At each anchor_idx, lead (soprano) should come first
    for i in range(0, 6, 2):
        assert schedule[i].is_lead is True, f"Task {i} should be lead"
        assert schedule[i + 1].is_lead is False, f"Task {i+1} should be follower"
        assert schedule[i].anchor_idx == schedule[i + 1].anchor_idx


def test_gap_schedule_sorted_by_anchor_idx() -> None:
    """Tasks are sorted by ascending anchor index."""
    anchors: tuple[PlanAnchor, ...] = tuple(_make_anchor(stage=i) for i in range(4))
    section: SectionPlan = _make_section(start=0, end=3, density="high")
    plan: CompositionPlan = CompositionPlan(
        home_key=Key(tonic="C", mode="major"),
        tempo=80,
        upbeat=Fraction(0),
        voice_plans=(
            _make_voice_plan(voice_id="soprano", order=0, sections=(section,)),
        ),
        anchors=anchors,
    )
    schedule: list[GapTask] = _build_gap_schedule(plan=plan)
    anchor_indices: list[int] = [t.anchor_idx for t in schedule]
    assert anchor_indices == sorted(anchor_indices)


# =========================================================================
# compose_voices — integration via pipeline
# =========================================================================


def test_compose_voices_produces_notes() -> None:
    """Full pipeline through compose_voices produces non-empty voices."""
    from planner.planner import generate
    composition = generate(genre="minuet", affect="Zierlich", key="c_major")
    assert len(composition.voices) > 0
    for voice_id, notes in composition.voices.items():
        assert len(notes) > 0, f"Voice '{voice_id}' has no notes"


def test_compose_voices_notes_sorted_by_offset() -> None:
    """compose_voices returns notes sorted by offset within each voice."""
    from planner.planner import generate
    composition = generate(genre="minuet", affect="Zierlich", key="c_major")
    for voice_id, notes in composition.voices.items():
        offsets: list[Fraction] = [n.offset for n in notes]
        assert offsets == sorted(offsets), (
            f"Voice '{voice_id}' notes not sorted by offset"
        )


def test_compose_voices_preserves_metre() -> None:
    """Composition carries through metre from genre."""
    from planner.planner import generate
    composition = generate(genre="minuet", affect="Zierlich", key="c_major")
    assert composition.metre == "3/4"
