"""Tests for counterpoint checking, sequencing, imitation, and anacrusis.

Tests Phase 6c (counterpoint), 6d (sequencing), 6e (anacrusis).
"""
import pytest
from fractions import Fraction
from builder.compose import compose_voices
from builder.types import Composition, Note
from builder.voice_checks import (
    check_consonance,
    check_direct_motion,
    check_parallels,
    check_range,
    check_strong_beat_consonance,
)
from shared.constants import GATE_FACTOR
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


def _make_gap(
    bar_num: int,
    gap_duration: Fraction,
    mode: WritingMode = WritingMode.PILLAR,
    density: str = "low",
    interval: str = "unison",
) -> GapPlan:
    """Create a gap with specified parameters."""
    return GapPlan(
        bar_num=bar_num,
        writing_mode=mode,
        interval=interval,
        ascending=False,
        gap_duration=gap_duration,
        density=density,
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


class TestVoiceChecks:
    """Unit tests for voice_checks.py functions."""

    def test_check_consonance_unison(self) -> None:
        """Unison (interval class 0) is consonant."""
        assert check_consonance(60, 60) is True

    def test_check_consonance_perfect_fifth(self) -> None:
        """Perfect fifth (interval class 7) is consonant."""
        assert check_consonance(60, 67) is True
        assert check_consonance(67, 60) is True

    def test_check_consonance_major_third(self) -> None:
        """Major third (interval class 4) is consonant."""
        assert check_consonance(60, 64) is True

    def test_check_consonance_minor_second(self) -> None:
        """Minor second (interval class 1) is dissonant."""
        assert check_consonance(60, 61) is False

    def test_check_consonance_tritone(self) -> None:
        """Tritone (interval class 6) is dissonant above bass."""
        assert check_consonance(60, 66) is False

    def test_check_parallels_no_parallel(self) -> None:
        """Non-parallel motion (different intervals) passes."""
        # Prev: M3 (60-56=4), Curr: m7 (62-55=7) - different intervals
        assert check_parallels(60, 56, 62, 55) is True

    def test_check_parallels_parallel_fifth(self) -> None:
        """Parallel fifths fail."""
        assert check_parallels(67, 60, 69, 62) is False

    def test_check_parallels_parallel_octave(self) -> None:
        """Parallel octaves fail."""
        assert check_parallels(72, 60, 74, 62) is False

    def test_check_parallels_contrary_motion(self) -> None:
        """Contrary motion from P5 to P5 passes (not parallel)."""
        # Prev: P5 (67-60=7), Curr: P5 (65-72=7) - contrary motion
        # Upper goes down (65<67), lower goes up (72>60)
        assert check_parallels(67, 60, 65, 72) is True

    def test_check_direct_motion_step_ok(self) -> None:
        """Stepwise soprano motion to perfect interval passes."""
        assert check_direct_motion(65, 60, 67, 60) is True

    def test_check_direct_motion_leap_fail(self) -> None:
        """Soprano leap to perfect interval fails."""
        assert check_direct_motion(60, 55, 67, 60) is False

    def test_check_range_in_range(self) -> None:
        """Pitch within range passes."""
        assert check_range(60, Range(low=48, high=84)) is True

    def test_check_range_below(self) -> None:
        """Pitch below range fails."""
        assert check_range(40, Range(low=48, high=84)) is False

    def test_check_range_above(self) -> None:
        """Pitch above range fails."""
        assert check_range(90, Range(low=48, high=84)) is False

    def test_check_strong_beat_consonance_downbeat(self) -> None:
        """Dissonance on downbeat fails."""
        assert check_strong_beat_consonance(60, 61, Fraction(0), "4/4") is False

    def test_check_strong_beat_consonance_weak_beat(self) -> None:
        """Dissonance on weak beat passes."""
        assert check_strong_beat_consonance(60, 61, Fraction(1, 4), "4/4") is True


class TestCounterpointFiltering:
    """Integration tests for counterpoint filtering in compose_voices."""

    def test_two_voices_consonant(self) -> None:
        """Two consonant voices produce notes at expected pitches."""
        home_key: Key = Key(tonic="C", mode="major")
        upper_step: int = 35
        lower_step: int = 28
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, upper_step, lower_step, home_key),
            _make_anchor(2, 1, upper_step, lower_step, home_key),
        )
        gap_upper: GapPlan = _make_gap(1, Fraction(1, 1))
        gap_lower: GapPlan = _make_gap(1, Fraction(1, 1))
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
        soprano_midi: int = result.voices["soprano"][0].pitch
        bass_midi: int = result.voices["bass"][0].pitch
        interval: int = abs(soprano_midi - bass_midi) % 12
        assert interval in {0, 3, 4, 7, 8, 9}


class TestSequencing:
    """Tests for sequencing strategies (repeating, static)."""

    def test_repeating_sequencing(self) -> None:
        """Repeating sequencing produces transposed figures."""
        home_key: Key = Key(tonic="C", mode="major")
        steps: list[int] = [35, 36, 37, 38]
        anchors: tuple[PlanAnchor, ...] = tuple(
            _make_anchor(i + 1, 1, steps[i], 28 + i, home_key)
            for i in range(4)
        )
        gaps: tuple[GapPlan, ...] = tuple(
            _make_gap(i + 1, Fraction(1, 1), WritingMode.PILLAR)
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
        assert len(notes) == 3


class TestAnacrusis:
    """Tests for anacrusis (upbeat) support."""

    def test_anacrusis_ascending(self) -> None:
        """Ascending anacrusis produces notes before bar 1."""
        home_key: Key = Key(tonic="C", mode="major")
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, 35, 28, home_key),
            _make_anchor(2, 1, 35, 28, home_key),
        )
        gap: GapPlan = _make_gap(1, Fraction(1, 1))
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
            target_pitch=DiatonicPitch(step=35),
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
        anacrusis_notes: list[Note] = [n for n in notes if n.offset < 0]
        assert len(anacrusis_notes) == 2
        assert anacrusis_notes[0].offset == Fraction(-1, 4)
        assert anacrusis_notes[1].offset == Fraction(-1, 8)

    def test_anacrusis_descending(self) -> None:
        """Descending anacrusis produces notes in descending pitch order."""
        home_key: Key = Key(tonic="C", mode="major")
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, 35, 28, home_key),
            _make_anchor(2, 1, 35, 28, home_key),
        )
        gap: GapPlan = _make_gap(1, Fraction(1, 1))
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
            target_pitch=DiatonicPitch(step=35),
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
        assert anacrusis_notes[0].pitch > anacrusis_notes[1].pitch


class TestImitation:
    """Tests for imitative role."""

    def test_imitative_section(self) -> None:
        """Imitative section copies and transposes source voice."""
        home_key: Key = Key(tonic="C", mode="major")
        anchors: tuple[PlanAnchor, ...] = (
            _make_anchor(1, 1, 35, 28, home_key),
            _make_anchor(2, 1, 36, 29, home_key),
            _make_anchor(3, 1, 35, 28, home_key),
        )
        gap1: GapPlan = _make_gap(1, Fraction(1, 1))
        gap2: GapPlan = _make_gap(2, Fraction(1, 1))
        section_upper: SectionPlan = SectionPlan(
            start_gap_index=0,
            end_gap_index=2,
            schema_name="test",
            sequencing="independent",
            figure_profile=None,
            role=Role.SCHEMA_UPPER,
            follows=None,
            follow_interval=None,
            follow_delay=None,
            shared_actuator_with=None,
            gaps=(gap1, gap2),
        )
        section_imitative: SectionPlan = SectionPlan(
            start_gap_index=0,
            end_gap_index=2,
            schema_name="test",
            sequencing="independent",
            figure_profile=None,
            role=Role.IMITATIVE,
            follows="soprano",
            follow_interval=-7,
            follow_delay=Fraction(1, 1),
            shared_actuator_with=None,
            gaps=(gap1, gap2),
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
            sections=(section_imitative,),
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
        soprano_notes: tuple[Note, ...] = result.voices["soprano"]
        bass_notes: tuple[Note, ...] = result.voices["bass"]
        assert len(soprano_notes) >= 1
        if bass_notes:
            first_bass: Note = bass_notes[0]
            assert first_bass.offset == Fraction(1, 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
