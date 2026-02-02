"""Tests for CompositionPlan structural validation.

Tests validate_plan() against edge-case plans to catch planner bugs
that faults.py cannot see.
"""
import pytest
from fractions import Fraction
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import (
    AnacrusisPlan,
    CompositionPlan,
    GapPlan,
    PlanAnchor,
    SectionPlan,
    VoicePlan,
    WritingMode,
    validate_plan,
)
from shared.voice_types import Range, Role


# ── Helpers ──────────────────────────────────────────────────────────────────

HOME_KEY: Key = Key(tonic="C", mode="major")
UNIT: Fraction = Fraction(1, 16)


def _anchor(bar_beat: str, stage: int = 0) -> PlanAnchor:
    """Minimal anchor for testing."""
    return PlanAnchor(
        bar_beat=bar_beat,
        upper_degree=1,
        lower_degree=1,
        upper_pitch=DiatonicPitch(step=35),
        lower_pitch=DiatonicPitch(step=28),
        local_key=HOME_KEY,
        schema="do_re_mi",
        stage=stage,
    )


def _gap(bar_num: int = 1) -> GapPlan:
    """Minimal gap for testing."""
    return GapPlan(
        bar_num=bar_num,
        writing_mode=WritingMode.FIGURATION,
        interval="step_up",
        ascending=True,
        gap_duration=Fraction(1, 4),
        density="medium",
        character="plain",
        harmonic_tension="low",
        bar_function="passing",
        near_cadence=False,
        use_hemiola=False,
        overdotted=False,
        start_beat=1,
        next_anchor_strength="strong",
        required_note_count=4,
        compound_allowed=False,
    )


def _section(
    start: int,
    end: int,
    role: Role = Role.SCHEMA_UPPER,
    follows: str | None = None,
    follow_interval: int | None = None,
    follow_delay: Fraction | None = None,
    shared_actuator_with: str | None = None,
) -> SectionPlan:
    """Section with auto-generated gaps."""
    gap_count: int = end - start
    return SectionPlan(
        start_gap_index=start,
        end_gap_index=end,
        schema_name="do_re_mi",
        sequencing="independent",
        figure_profile=None,
        role=role,
        follows=follows,
        follow_interval=follow_interval,
        follow_delay=follow_delay,
        shared_actuator_with=shared_actuator_with,
        gaps=tuple(_gap(bar_num=start + i + 1) for i in range(gap_count)),
    )


def _voice(
    voice_id: str,
    order: int,
    sections: tuple[SectionPlan, ...],
) -> VoicePlan:
    """Minimal voice plan."""
    return VoicePlan(
        voice_id=voice_id,
        actuator_range=Range(low=48, high=84),
        tessitura_median=DiatonicPitch(step=35),
        composition_order=order,
        seed=42,
        metre="4/4",
        rhythmic_unit=UNIT,
        sections=sections,
        anacrusis=None,
    )


def _plan(
    voice_plans: tuple[VoicePlan, ...],
    anchors: tuple[PlanAnchor, ...],
) -> CompositionPlan:
    """Minimal CompositionPlan wrapper for testing."""
    return CompositionPlan(
        home_key=HOME_KEY,
        tempo=80,
        upbeat=Fraction(0),
        voice_plans=voice_plans,
        anchors=anchors,
    )


def _valid_two_voice_plan() -> CompositionPlan:
    """Minimal valid 2-voice plan with 3 anchors (2 gaps)."""
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1", stage=0),
        _anchor("1.3", stage=1),
        _anchor("2.1", stage=2),
    )
    upper: VoicePlan = _voice("upper", 0, (_section(0, 2),))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 2, role=Role.SCHEMA_LOWER),
    ))
    return _plan((upper, lower), anchors)


# ── Valid plans pass ─────────────────────────────────────────────────────────

def test_valid_two_voice_plan() -> None:
    plan: CompositionPlan = _valid_two_voice_plan()
    validate_plan(plan)


def test_valid_plan_with_imitative_voice() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    upper: VoicePlan = _voice("upper", 0, (_section(0, 2),))
    lower: VoicePlan = _voice("lower", 1, (
        _section(
            0, 2,
            role=Role.IMITATIVE,
            follows="upper",
            follow_interval=-7,
            follow_delay=Fraction(1, 1),
        ),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    validate_plan(plan)


def test_valid_plan_with_multiple_sections() -> None:
    anchors: tuple[PlanAnchor, ...] = tuple(
        _anchor(f"{i}.1", stage=i) for i in range(1, 6)
    )
    upper: VoicePlan = _voice("upper", 0, (
        _section(0, 2),
        _section(2, 4),
    ))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 4, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    validate_plan(plan)


def test_valid_shared_actuator_reciprocal() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    upper: VoicePlan = _voice("upper", 0, (
        _section(0, 2, shared_actuator_with="lower"),
    ))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 2, role=Role.SCHEMA_LOWER, shared_actuator_with="upper"),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    validate_plan(plan)


# ── Duplicate voice id ───────────────────────────────────────────────────────

def test_duplicate_voice_id() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    v1: VoicePlan = _voice("upper", 0, (_section(0, 2),))
    v2: VoicePlan = _voice("upper", 1, (
        _section(0, 2, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((v1, v2), anchors)
    with pytest.raises(AssertionError, match="Duplicate voice_id"):
        validate_plan(plan)


# ── Composition order ────────────────────────────────────────────────────────

def test_composition_order_gap() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    upper: VoicePlan = _voice("upper", 0, (_section(0, 2),))
    lower: VoicePlan = _voice("lower", 2, (
        _section(0, 2, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="composition_order"):
        validate_plan(plan)


def test_composition_order_duplicate() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    upper: VoicePlan = _voice("upper", 0, (_section(0, 2),))
    lower: VoicePlan = _voice("lower", 0, (
        _section(0, 2, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="composition_order"):
        validate_plan(plan)


# ── Follows references ───────────────────────────────────────────────────────

def test_follows_unknown_voice() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    upper: VoicePlan = _voice("upper", 0, (_section(0, 2),))
    lower: VoicePlan = _voice("lower", 1, (
        _section(
            0, 2,
            role=Role.IMITATIVE,
            follows="ghost",
            follow_interval=-7,
            follow_delay=Fraction(1, 1),
        ),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="unknown voice 'ghost'"):
        validate_plan(plan)


def test_follows_self() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    lower: VoicePlan = _voice("lower", 0, (_section(0, 2),))
    upper: VoicePlan = _voice("upper", 1, (
        _section(
            0, 2,
            role=Role.IMITATIVE,
            follows="upper",
            follow_interval=-7,
            follow_delay=Fraction(1, 1),
        ),
    ))
    plan: CompositionPlan = _plan((lower, upper), anchors)
    with pytest.raises(AssertionError, match="cannot follow itself"):
        validate_plan(plan)


def test_follows_higher_order() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    upper: VoicePlan = _voice("upper", 0, (
        _section(
            0, 2,
            role=Role.IMITATIVE,
            follows="lower",
            follow_interval=7,
            follow_delay=Fraction(1, 1),
        ),
    ))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 2, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="lower composition_order"):
        validate_plan(plan)


# ── Role-specific fields ────────────────────────────────────────────────────

def test_imitative_missing_follows() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    upper: VoicePlan = _voice("upper", 0, (_section(0, 2),))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 2, role=Role.IMITATIVE),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="IMITATIVE requires follows"):
        validate_plan(plan)


def test_schema_upper_with_follows() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    lower: VoicePlan = _voice("lower", 0, (
        _section(0, 2, role=Role.SCHEMA_LOWER),
    ))
    upper: VoicePlan = _voice("upper", 1, (
        _section(0, 2, role=Role.SCHEMA_UPPER, follows="lower"),
    ))
    plan: CompositionPlan = _plan((lower, upper), anchors)
    with pytest.raises(AssertionError, match="SCHEMA_UPPER must not have follows"):
        validate_plan(plan)


# ── Gap contiguity ───────────────────────────────────────────────────────────

def test_section_not_starting_at_zero() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    upper: VoicePlan = _voice("upper", 0, (_section(1, 2),))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 2, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="must start at gap 0"):
        validate_plan(plan)


def test_section_not_ending_at_total() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
        _anchor("2.3"),
    )
    upper: VoicePlan = _voice("upper", 0, (_section(0, 2),))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 3, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="must end at gap"):
        validate_plan(plan)


def test_section_gap_between_sections() -> None:
    anchors: tuple[PlanAnchor, ...] = tuple(
        _anchor(f"{i}.1") for i in range(1, 6)
    )
    upper: VoicePlan = _voice("upper", 0, (
        _section(0, 1),
        _section(2, 4),
    ))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 4, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="gap between sections"):
        validate_plan(plan)


# ── Gap count mismatch ───────────────────────────────────────────────────────

def test_gap_count_mismatch() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    bad_section: SectionPlan = SectionPlan(
        start_gap_index=0,
        end_gap_index=2,
        schema_name="do_re_mi",
        sequencing="independent",
        figure_profile=None,
        role=Role.SCHEMA_UPPER,
        follows=None,
        follow_interval=None,
        follow_delay=None,
        shared_actuator_with=None,
        gaps=(_gap(),),  # 1 gap but span is 2
    )
    upper: VoicePlan = _voice("upper", 0, (bad_section,))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 2, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="has 1 gaps but span is 2"):
        validate_plan(plan)


# ── Shared actuator ──────────────────────────────────────────────────────────

def test_shared_actuator_no_reciprocal() -> None:
    anchors: tuple[PlanAnchor, ...] = (
        _anchor("1.1"), _anchor("1.3"), _anchor("2.1"),
    )
    upper: VoicePlan = _voice("upper", 0, (
        _section(0, 2, shared_actuator_with="lower"),
    ))
    lower: VoicePlan = _voice("lower", 1, (
        _section(0, 2, role=Role.SCHEMA_LOWER),
    ))
    plan: CompositionPlan = _plan((upper, lower), anchors)
    with pytest.raises(AssertionError, match="no reciprocal"):
        validate_plan(plan)
