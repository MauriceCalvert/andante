"""Tests for sequencing strategies and anacrusis.

Verifies repeating/static sequencing and anacrusis generation.
"""
import pytest
from fractions import Fraction
from builder.compose import compose_voices
from builder.types import Composition, Note
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
)
from shared.voice_types import Range, Role


def _make_figuration_gap(
    bar_num: int,
    gap_duration: Fraction,
    interval: str = "step_up",
    ascending: bool = True,
) -> GapPlan:
    """Create a FIGURATION gap."""
    return GapPlan(
        bar_num=bar_num,
        writing_mode=WritingMode.FIGURATION,
        interval=interval,
        ascending=ascending,
        gap_duration=gap_duration,
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


def _make_pillar_gap(bar_num: int, gap_duration: Fraction) -> GapPlan:
    """Create a PILLAR gap."""
    return GapPlan(
        bar_num=bar_num,
        writing_mode=WritingMode.PILLAR,
        interval="unison",
        ascending=False,
        gap_duration=gap_duration,
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


def _make_anchor(
    bar: int,
    beat: int,
    upper_step: int,
    lower_step: int,
    home_key: Key,
) -> PlanAnchor:
    """Create an anchor."""
    return PlanAnchor(
        bar_beat=f"{bar}.{beat}",
        upper_degree=(upper_step % 7) + 1,
        lower_degree=(lower_step % 7) + 1,
        upper_pitch=DiatonicPitch(step=upper_step),
        lower_pitch=DiatonicPitch(step=lower_step),
        local_key=home_key,
        schema="test",
        stage=0,
    )


class TestSequencing:
    """Tests for sequencing strategies."""

    def test_repeating_sequencing(self) -> None:
        """Repeating sequencing transposes first gap's figure to subsequent gaps."""
        home_key: Key = Key(tonic="C", mode="major")
        # 4 anchors, 3 gaps, each a step up
        upper_steps: list[int] = [35, 36, 37, 38]
        lower_steps: list[int] = [28, 29, 30, 31]
        anchors: tuple[PlanAnchor, ...] = tuple(
            _make_anchor(i + 1, 1, upper_steps[i], lower_steps[i], home_key)
            for i in range(4)
        )
        gaps: tuple[GapPlan, ...] = tuple(
            _make_figuration_gap(
                bar_num=i + 1,
                gap_duration=Fraction(1, 1),
                interval="step_up",
                ascending=True,
            )
            for i in range(3)
        )
        section: SectionPlan = SectionPlan(
            start_gap_index=0,
            end_gap_index=3,
            schema_name="test",
            sequencing="repeating",
            figure_profile=None,
            role=Role.SCHEMA_UPPER,
            follows=None,
            follow_interval=None,
            follow_delay=None,
            shared_actuator_with=None,
            gaps=gaps,
        )
        voice_plan: VoicePlan = VoicePlan(
            voice_id="soprano",
            actuator_range=Range(low=48, high=84),
            tessitura_median=DiatonicPitch(step=35),
            composition_order=0,
            seed=42,
            metre="4/4",
            rhythmic_unit=Fraction(1, 8),
            sections=(section,),
            anacrusis=None,
        )
        plan: CompositionPlan = CompositionPlan(
            home_key=home_key,
            tempo=80,
            upbeat=Fraction(0),
            voice_plans=(voice_plan,),
            anchors=anchors,
        )
        result: Composition = compose_voices(plan)
        notes: tuple[Note, ...] = result.voices["soprano"]
        # With repeating sequencing, should have notes in each gap
        assert len(notes) >= 3  # At least one note per gap
        # Check notes span all 3 bars
        offsets: set[int] = {int(n.offset) for n in notes}
        assert 0 in offsets  # Bar 1
        assert 1 in offsets  # Bar 2
        assert 2 in offsets  # Bar 3

    def test_static_sequencing(self) -> None:
        """Static sequencing reuses first gap's figure unchanged."""
        home_key: Key = Key(tonic="C", mode="major")
        # 3 anchors, 2 gaps, all at same pitch (static)
        upper_step: int = 35
        lower_step: int = 28
        anchors: tuple[PlanAnchor, ...] = tuple(
            _make_anchor(i + 1, 1, upper_step, lower_step, home_key)
            for i in range(3)
        )
        gaps: tuple[GapPlan, ...] = tuple(
            _make_figuration_gap(
                bar_num=i + 1,
                gap_duration=Fraction(1, 1),
                interval="unison",
                ascending=True,
            )
            for i in range(2)
        )
        section: SectionPlan = SectionPlan(
            start_gap_index=0,
            end_gap_index=2,
            schema_name="test",
            sequencing="static",
            figure_profile=None,
            role=Role.SCHEMA_UPPER,
            follows=None,
            follow_interval=None,
            follow_delay=None,
            shared_actuator_with=None,
            gaps=gaps,
        )
        voice_plan: VoicePlan = VoicePlan(
            voice_id="soprano",
            actuator_range=Range(low=48, high=84),
            tessitura_median=DiatonicPitch(step=35),
            composition_order=0,
            seed=42,
            metre="4/4",
            rhythmic_unit=Fraction(1, 8),
            sections=(section,),
            anacrusis=None,
        )
        plan: CompositionPlan = CompositionPlan(
            home_key=home_key,
            tempo=80,
            upbeat=Fraction(0),
            voice_plans=(voice_plan,),
            anchors=anchors,
        )
        result: Composition = compose_voices(plan)
        notes: tuple[Note, ...] = result.voices["soprano"]
        assert len(notes) >= 2


class TestAnacrusis:
    """Tests for anacrusis (upbeat) generation."""

    def test_ascending_anacrusis(self) -> None:
        """Ascending anacrusis produces notes leading up to first anchor."""
        home_key: Key = Key(tonic="C", mode="major")
        target_step: int = 35
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, target_step, 28, home_key),
            _make_anchor(2, 1, target_step, 28, home_key),
        )
        gap: GapPlan = _make_pillar_gap(bar_num=1, gap_duration=Fraction(1, 1))
        section: SectionPlan = SectionPlan(
            start_gap_index=0,
            end_gap_index=1,
            schema_name="test",
            sequencing="independent",
            figure_profile=None,
            role=Role.SCHEMA_UPPER,
            follows=None,
            follow_interval=None,
            follow_delay=None,
            shared_actuator_with=None,
            gaps=(gap,),
        )
        anacrusis: AnacrusisPlan = AnacrusisPlan(
            target_pitch=DiatonicPitch(step=target_step),
            duration=Fraction(1, 4),
            note_count=2,
            ascending=True,
        )
        voice_plan: VoicePlan = VoicePlan(
            voice_id="soprano",
            actuator_range=Range(low=48, high=84),
            tessitura_median=DiatonicPitch(step=35),
            composition_order=0,
            seed=42,
            metre="4/4",
            rhythmic_unit=Fraction(1, 8),
            sections=(section,),
            anacrusis=anacrusis,
        )
        plan: CompositionPlan = CompositionPlan(
            home_key=home_key,
            tempo=80,
            upbeat=Fraction(1, 4),
            voice_plans=(voice_plan,),
            anchors=anchors,
        )
        result: Composition = compose_voices(plan)
        notes: tuple[Note, ...] = result.voices["soprano"]
        # Should have anacrusis notes (negative offsets) + main notes
        anacrusis_notes: list[Note] = [n for n in notes if n.offset < 0]
        assert len(anacrusis_notes) == 2
        # First anacrusis note is below target
        first_midi: int = anacrusis_notes[0].pitch
        target_midi: int = home_key.diatonic_to_midi(DiatonicPitch(step=target_step))
        assert first_midi < target_midi

    def test_descending_anacrusis(self) -> None:
        """Descending anacrusis produces notes leading down to first anchor."""
        home_key: Key = Key(tonic="C", mode="major")
        target_step: int = 35
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, target_step, 28, home_key),
            _make_anchor(2, 1, target_step, 28, home_key),
        )
        gap: GapPlan = _make_pillar_gap(bar_num=1, gap_duration=Fraction(1, 1))
        section: SectionPlan = SectionPlan(
            start_gap_index=0,
            end_gap_index=1,
            schema_name="test",
            sequencing="independent",
            figure_profile=None,
            role=Role.SCHEMA_UPPER,
            follows=None,
            follow_interval=None,
            follow_delay=None,
            shared_actuator_with=None,
            gaps=(gap,),
        )
        anacrusis: AnacrusisPlan = AnacrusisPlan(
            target_pitch=DiatonicPitch(step=target_step),
            duration=Fraction(1, 4),
            note_count=2,
            ascending=False,
        )
        voice_plan: VoicePlan = VoicePlan(
            voice_id="soprano",
            actuator_range=Range(low=48, high=84),
            tessitura_median=DiatonicPitch(step=35),
            composition_order=0,
            seed=42,
            metre="4/4",
            rhythmic_unit=Fraction(1, 8),
            sections=(section,),
            anacrusis=anacrusis,
        )
        plan: CompositionPlan = CompositionPlan(
            home_key=home_key,
            tempo=80,
            upbeat=Fraction(1, 4),
            voice_plans=(voice_plan,),
            anchors=anchors,
        )
        result: Composition = compose_voices(plan)
        notes: tuple[Note, ...] = result.voices["soprano"]
        anacrusis_notes: list[Note] = [n for n in notes if n.offset < 0]
        assert len(anacrusis_notes) == 2
        # First anacrusis note is above target (descending approach)
        first_midi: int = anacrusis_notes[0].pitch
        target_midi: int = home_key.diatonic_to_midi(DiatonicPitch(step=target_step))
        assert first_midi > target_midi


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
