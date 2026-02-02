"""Smoke test for Phase 6a: all-PILLAR CompositionPlan through compose_voices.

Hand-builds a minimal CompositionPlan with two voices, all PILLAR gaps,
calls compose_voices(), and verifies the output Composition is correct.
"""
import pytest
from fractions import Fraction
from builder.compose import compose_voices
from builder.types import Composition, Note
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import (
    CompositionPlan,
    GapPlan,
    PlanAnchor,
    SectionPlan,
    VoicePlan,
    WritingMode,
    validate_plan,
)
from shared.voice_types import Range, Role

C_MAJOR: Key = Key(tonic="C", mode="major")
SOPRANO_RANGE: Range = Range(low=55, high=81)
BASS_RANGE: Range = Range(low=40, high=64)


def _make_pillar_gap(bar_num: int) -> GapPlan:
    """Create a PILLAR gap for one bar in 4/4."""
    return GapPlan(
        bar_num=bar_num,
        writing_mode=WritingMode.PILLAR,
        interval="unison",
        ascending=True,
        gap_duration=Fraction(1),
        density="low",
        character="plain",
        harmonic_tension="low",
        bar_function="passing",
        near_cadence=False,
        use_hemiola=False,
        overdotted=False,
        start_beat=1,
        next_anchor_strength="strong",
        required_note_count=None,
        compound_allowed=False,
    )


def _make_plan() -> CompositionPlan:
    """Build a 4-bar plan: 2 voices, all PILLAR, C major 4/4."""
    anchors: tuple[PlanAnchor, ...] = (
        PlanAnchor(
            bar_beat="1.1",
            upper_degree=1, lower_degree=1,
            upper_pitch=DiatonicPitch(step=35),
            lower_pitch=DiatonicPitch(step=28),
            local_key=C_MAJOR, schema="romanesca", stage=1,
        ),
        PlanAnchor(
            bar_beat="2.1",
            upper_degree=7, lower_degree=2,
            upper_pitch=DiatonicPitch(step=34),
            lower_pitch=DiatonicPitch(step=29),
            local_key=C_MAJOR, schema="romanesca", stage=2,
        ),
        PlanAnchor(
            bar_beat="3.1",
            upper_degree=6, lower_degree=3,
            upper_pitch=DiatonicPitch(step=33),
            lower_pitch=DiatonicPitch(step=30),
            local_key=C_MAJOR, schema="romanesca", stage=3,
        ),
        PlanAnchor(
            bar_beat="4.1",
            upper_degree=5, lower_degree=4,
            upper_pitch=DiatonicPitch(step=32),
            lower_pitch=DiatonicPitch(step=31),
            local_key=C_MAJOR, schema="romanesca", stage=4,
        ),
        PlanAnchor(
            bar_beat="5.1",
            upper_degree=1, lower_degree=1,
            upper_pitch=DiatonicPitch(step=35),
            lower_pitch=DiatonicPitch(step=28),
            local_key=C_MAJOR, schema="romanesca", stage=5,
        ),
    )
    gaps: tuple[GapPlan, ...] = tuple(_make_pillar_gap(i + 1) for i in range(4))
    soprano_section: SectionPlan = SectionPlan(
        start_gap_index=0, end_gap_index=4,
        schema_name="romanesca", sequencing="independent",
        figure_profile=None,
        role=Role.SCHEMA_UPPER,
        follows=None, follow_interval=None, follow_delay=None,
        shared_actuator_with=None,
        gaps=gaps,
    )
    bass_section: SectionPlan = SectionPlan(
        start_gap_index=0, end_gap_index=4,
        schema_name="romanesca", sequencing="independent",
        figure_profile=None,
        role=Role.SCHEMA_LOWER,
        follows=None, follow_interval=None, follow_delay=None,
        shared_actuator_with=None,
        gaps=gaps,
    )
    soprano_plan: VoicePlan = VoicePlan(
        voice_id="upper",
        actuator_range=SOPRANO_RANGE,
        tessitura_median=DiatonicPitch(step=37),
        composition_order=0,
        seed=42,
        metre="4/4",
        rhythmic_unit=Fraction(1, 16),
        sections=(soprano_section,),
        anacrusis=None,
    )
    bass_plan: VoicePlan = VoicePlan(
        voice_id="lower",
        actuator_range=BASS_RANGE,
        tessitura_median=DiatonicPitch(step=30),
        composition_order=1,
        seed=43,
        metre="4/4",
        rhythmic_unit=Fraction(1, 16),
        sections=(bass_section,),
        anacrusis=None,
    )
    return CompositionPlan(
        home_key=C_MAJOR,
        tempo=100,
        upbeat=Fraction(0),
        voice_plans=(soprano_plan, bass_plan),
        anchors=anchors,
    )


def test_validate_plan() -> None:
    """validate_plan accepts the hand-built plan without assertion."""
    plan: CompositionPlan = _make_plan()
    validate_plan(plan)


def test_compose_voices_produces_composition() -> None:
    """compose_voices returns a Composition with correct structure."""
    plan: CompositionPlan = _make_plan()
    comp: Composition = compose_voices(plan)
    assert isinstance(comp, Composition)
    assert "upper" in comp.voices
    assert "lower" in comp.voices
    assert comp.metre == "4/4"
    assert comp.tempo == 100


def test_compose_voices_note_count() -> None:
    """Each voice produces exactly 4 notes (one PILLAR per gap)."""
    plan: CompositionPlan = _make_plan()
    comp: Composition = compose_voices(plan)
    assert len(comp.voices["upper"]) == 4
    assert len(comp.voices["lower"]) == 4


def test_compose_voices_soprano_midi() -> None:
    """Soprano PILLAR notes have correct MIDI pitches."""
    plan: CompositionPlan = _make_plan()
    comp: Composition = compose_voices(plan)
    soprano: tuple[Note, ...] = comp.voices["upper"]
    expected_steps: list[int] = [35, 34, 33, 32]
    for i, note in enumerate(soprano):
        expected_midi: int = C_MAJOR.diatonic_to_midi(DiatonicPitch(step=expected_steps[i]))
        assert note.pitch == expected_midi, (
            f"Soprano note {i}: pitch {note.pitch} != expected {expected_midi}"
        )


def test_compose_voices_bass_midi() -> None:
    """Bass PILLAR notes have correct MIDI pitches."""
    plan: CompositionPlan = _make_plan()
    comp: Composition = compose_voices(plan)
    bass: tuple[Note, ...] = comp.voices["lower"]
    expected_steps: list[int] = [28, 29, 30, 31]
    for i, note in enumerate(bass):
        expected_midi: int = C_MAJOR.diatonic_to_midi(DiatonicPitch(step=expected_steps[i]))
        assert note.pitch == expected_midi, (
            f"Bass note {i}: pitch {note.pitch} != expected {expected_midi}"
        )


def test_compose_voices_offsets() -> None:
    """Notes have correct offsets (one per bar in 4/4)."""
    plan: CompositionPlan = _make_plan()
    comp: Composition = compose_voices(plan)
    expected_offsets: list[Fraction] = [
        Fraction(0), Fraction(1), Fraction(2), Fraction(3),
    ]
    for voice_id in ("upper", "lower"):
        notes: tuple[Note, ...] = comp.voices[voice_id]
        for i, note in enumerate(notes):
            assert note.offset == expected_offsets[i], (
                f"{voice_id} note {i}: offset {note.offset} != "
                f"expected {expected_offsets[i]}"
            )


def test_compose_voices_durations() -> None:
    """PILLAR note durations are gap_duration * GATE_FACTOR."""
    from shared.constants import GATE_FACTOR
    plan: CompositionPlan = _make_plan()
    comp: Composition = compose_voices(plan)
    expected_dur: Fraction = Fraction(1) * GATE_FACTOR
    for voice_id in ("upper", "lower"):
        for note in comp.voices[voice_id]:
            assert note.duration == expected_dur, (
                f"{voice_id}: duration {note.duration} != expected {expected_dur}"
            )


def test_compose_voices_voice_indices() -> None:
    """Voice index matches composition_order."""
    plan: CompositionPlan = _make_plan()
    comp: Composition = compose_voices(plan)
    for note in comp.voices["upper"]:
        assert note.voice == 0
    for note in comp.voices["lower"]:
        assert note.voice == 1
