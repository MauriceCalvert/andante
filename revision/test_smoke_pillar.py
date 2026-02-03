"""Smoke test: hand-built CompositionPlan with all-PILLAR gaps.

Verifies that compose_voices() produces correct output for the
simplest possible plan.  See phase6_design.md §6a.
"""
import pytest
from fractions import Fraction
from builder.compose import compose_voices
from builder.types import Composition, Note
from shared.constants import GATE_FACTOR
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


def _make_pillar_gap(bar_num: int, gap_duration: Fraction) -> GapPlan:
    """Create a PILLAR gap with minimal required fields."""
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
    """Create an anchor at bar.beat with given step values."""
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


class TestSmokePillar:
    """Smoke tests for all-PILLAR composition."""

    def test_single_voice_two_anchors(self) -> None:
        """One voice, two anchors, one PILLAR gap produces one held note."""
        home_key: Key = Key(tonic="C", mode="major")
        upper_step: int = 35
        lower_step: int = 28
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, upper_step, lower_step, home_key),
            _make_anchor(2, 1, upper_step, lower_step, home_key),
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
        assert "soprano" in result.voices
        notes: tuple[Note, ...] = result.voices["soprano"]
        assert len(notes) == 1
        note: Note = notes[0]
        expected_midi: int = home_key.diatonic_to_midi(DiatonicPitch(step=upper_step))
        assert note.pitch == expected_midi
        assert note.offset == Fraction(0)
        expected_dur: Fraction = Fraction(1, 1) * GATE_FACTOR
        assert note.duration == expected_dur
        assert note.voice == 0

    def test_two_voices_pillar(self) -> None:
        """Two voices, both PILLAR, produce two held notes at different pitches."""
        home_key: Key = Key(tonic="G", mode="major")
        upper_step: int = 35
        lower_step: int = 28
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, upper_step, lower_step, home_key),
            _make_anchor(2, 1, upper_step, lower_step, home_key),
        )
        gap_upper: GapPlan = _make_pillar_gap(bar_num=1, gap_duration=Fraction(1, 1))
        gap_lower: GapPlan = _make_pillar_gap(bar_num=1, gap_duration=Fraction(1, 1))
        section_upper: SectionPlan = SectionPlan(
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
            gaps=(gap_upper,),
        )
        section_lower: SectionPlan = SectionPlan(
            start_gap_index=0,
            end_gap_index=1,
            schema_name="test",
            sequencing="independent",
            figure_profile=None,
            role=Role.SCHEMA_LOWER,
            follows=None,
            follow_interval=None,
            follow_delay=None,
            shared_actuator_with=None,
            gaps=(gap_lower,),
        )
        soprano_plan: VoicePlan = VoicePlan(
            voice_id="soprano",
            actuator_range=Range(low=48, high=84),
            tessitura_median=DiatonicPitch(step=35),
            composition_order=0,
            seed=42,
            metre="4/4",
            rhythmic_unit=Fraction(1, 8),
            sections=(section_upper,),
            anacrusis=None,
        )
        bass_plan: VoicePlan = VoicePlan(
            voice_id="bass",
            actuator_range=Range(low=36, high=67),
            tessitura_median=DiatonicPitch(step=28),
            composition_order=1,
            seed=43,
            metre="4/4",
            rhythmic_unit=Fraction(1, 8),
            sections=(section_lower,),
            anacrusis=None,
        )
        plan: CompositionPlan = CompositionPlan(
            home_key=home_key,
            tempo=80,
            upbeat=Fraction(0),
            voice_plans=(soprano_plan, bass_plan),
            anchors=anchors,
        )
        result: Composition = compose_voices(plan)
        assert len(result.voices) == 2
        assert "soprano" in result.voices
        assert "bass" in result.voices
        soprano_notes: tuple[Note, ...] = result.voices["soprano"]
        bass_notes: tuple[Note, ...] = result.voices["bass"]
        assert len(soprano_notes) == 1
        assert len(bass_notes) == 1
        expected_soprano_midi: int = home_key.diatonic_to_midi(
            DiatonicPitch(step=upper_step),
        )
        expected_bass_midi: int = home_key.diatonic_to_midi(
            DiatonicPitch(step=lower_step),
        )
        assert soprano_notes[0].pitch == expected_soprano_midi
        assert bass_notes[0].pitch == expected_bass_midi
        assert soprano_notes[0].voice == 0
        assert bass_notes[0].voice == 1

    def test_multiple_gaps_pillar(self) -> None:
        """Four anchors, three PILLAR gaps produce three held notes."""
        home_key: Key = Key(tonic="C", mode="major")
        steps: list[int] = [35, 36, 37, 35]
        anchors: tuple[PlanAnchor, ...] = tuple(
            _make_anchor(i + 1, 1, steps[i], 28, home_key)
            for i in range(4)
        )
        gaps: tuple[GapPlan, ...] = tuple(
            _make_pillar_gap(bar_num=i + 1, gap_duration=Fraction(1, 1))
            for i in range(3)
        )
        section: SectionPlan = SectionPlan(
            start_gap_index=0,
            end_gap_index=3,
            schema_name="test",
            sequencing="independent",
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
        assert len(notes) == 3
        for i, note in enumerate(notes):
            expected_midi: int = home_key.diatonic_to_midi(
                DiatonicPitch(step=steps[i]),
            )
            assert note.pitch == expected_midi
            expected_offset: Fraction = Fraction(i, 1)
            assert note.offset == expected_offset
            expected_dur: Fraction = Fraction(1, 1) * GATE_FACTOR
            assert note.duration == expected_dur

    def test_minor_key(self) -> None:
        """PILLAR in minor key produces correct MIDI values."""
        home_key: Key = Key(tonic="A", mode="minor")
        upper_step: int = 35
        lower_step: int = 28
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, upper_step, lower_step, home_key),
            _make_anchor(2, 1, upper_step, lower_step, home_key),
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
        assert len(notes) == 1
        expected_midi: int = home_key.diatonic_to_midi(DiatonicPitch(step=upper_step))
        assert notes[0].pitch == expected_midi
        midi_c_major: int = Key(tonic="C", mode="major").diatonic_to_midi(
            DiatonicPitch(step=upper_step),
        )
        assert notes[0].pitch != midi_c_major

    def test_range_violation_fails(self) -> None:
        """Anchor pitch outside actuator range fails at assertion."""
        home_key: Key = Key(tonic="C", mode="major")
        upper_step: int = 50
        lower_step: int = 28
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, upper_step, lower_step, home_key),
            _make_anchor(2, 1, upper_step, lower_step, home_key),
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
        voice_plan: VoicePlan = VoicePlan(
            voice_id="soprano",
            actuator_range=Range(low=48, high=72),
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
        with pytest.raises(AssertionError):
            compose_voices(plan)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
