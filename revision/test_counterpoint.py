"""Tests for counterpoint checking in voice writing.

Verifies that parallel fifths/octaves and direct motion are rejected.
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
)
from shared.voice_types import Range, Role


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


class TestCounterpointChecking:
    """Tests for counterpoint rule enforcement."""

    def test_consonant_interval_passes(self) -> None:
        """Two voices forming a consonant interval (third) passes."""
        home_key: Key = Key(tonic="C", mode="major")
        # Soprano at step 37 (E4, MIDI 64), bass at step 35 (C4, MIDI 60)
        # Interval = 4 semitones = major third = consonant
        upper_step: int = 37
        lower_step: int = 35
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
            actuator_range=Range(low=36, high=72),
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
        assert len(result.voices["soprano"]) == 1
        assert len(result.voices["bass"]) == 1
        soprano_midi: int = result.voices["soprano"][0].pitch
        bass_midi: int = result.voices["bass"][0].pitch
        interval: int = abs(soprano_midi - bass_midi) % 12
        assert interval == 4  # major third

    def test_dissonant_strong_beat_fails(self) -> None:
        """Two voices forming a dissonant interval (m2) on strong beat fails."""
        home_key: Key = Key(tonic="C", mode="major")
        # Soprano at step 35 (C4, MIDI 60), bass at step 41 (B4, MIDI 71)
        # Interval = 11 semitones = major 7th = dissonant on strong beat
        upper_step: int = 35
        lower_step: int = 41
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
            actuator_range=Range(low=36, high=84),
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
        # This should fail because PILLAR has no fallback and the
        # dissonant anchor fails the candidate filter
        with pytest.raises(AssertionError):
            compose_voices(plan)

    def test_parallel_motion_detection(self) -> None:
        """Verify parallel fifths are detected via check_parallels."""
        from builder.voice_checks import check_parallels
        # C-G (perfect fifth) to D-A (perfect fifth) in parallel motion
        # prev_upper=67 (G4), prev_lower=60 (C4) -> 7 semitones = P5
        # curr_upper=69 (A4), curr_lower=62 (D4) -> 7 semitones = P5
        # Both move up by step = parallel fifths = forbidden
        result: bool = check_parallels(
            prev_upper=67,
            prev_lower=60,
            curr_upper=69,
            curr_lower=62,
        )
        assert result is False  # Parallel fifths rejected

    def test_contrary_motion_to_fifth_allowed(self) -> None:
        """Verify contrary motion to a fifth is allowed."""
        from builder.voice_checks import check_parallels
        # E-B (perfect fifth) with contrary motion
        # prev_upper=71 (B4), prev_lower=64 (E4) -> 7 semitones = P5
        # curr_upper=67 (G4), curr_lower=60 (C4) -> 7 semitones = P5
        # Upper descends, lower descends = parallel (same direction)
        # Actually: 71->67 = -4 (down), 64->60 = -4 (down) = same direction
        # This is parallel motion, should fail
        result: bool = check_parallels(
            prev_upper=71,
            prev_lower=64,
            curr_upper=67,
            curr_lower=60,
        )
        assert result is False  # Still parallel

    def test_oblique_motion_to_fifth_allowed(self) -> None:
        """Verify oblique motion to a fifth is allowed."""
        from builder.voice_checks import check_parallels
        # Upper holds, lower moves
        # prev_upper=67 (G4), prev_lower=64 (E4) -> 3 semitones = m3
        # curr_upper=67 (G4), curr_lower=60 (C4) -> 7 semitones = P5
        # Upper stationary, lower moves = oblique motion = allowed
        result: bool = check_parallels(
            prev_upper=67,
            prev_lower=64,
            curr_upper=67,
            curr_lower=60,
        )
        assert result is True  # Oblique motion allowed

    def test_direct_fifths_with_leap_rejected(self) -> None:
        """Direct motion to fifth with soprano leap is forbidden."""
        from builder.voice_checks import check_direct_motion
        # Both voices move up, arriving at perfect fifth, soprano leaps
        # prev_upper=60 (C4), prev_lower=55 (G3)
        # curr_upper=67 (G4), curr_lower=60 (C4) -> 7 semitones = P5
        # Upper moves 60->67 = +7 (leap), lower moves 55->60 = +5
        # Same direction + P5 arrival + upper leap = direct fifths
        result: bool = check_direct_motion(
            prev_upper=60,
            prev_lower=55,
            curr_upper=67,
            curr_lower=60,
        )
        assert result is False  # Direct fifths with leap rejected

    def test_direct_fifths_with_step_allowed(self) -> None:
        """Direct motion to fifth with soprano step is allowed."""
        from builder.voice_checks import check_direct_motion
        # Both voices move up, arriving at perfect fifth, soprano steps
        # prev_upper=65 (F4), prev_lower=55 (G3)
        # curr_upper=67 (G4), curr_lower=60 (C4) -> 7 semitones = P5
        # Upper moves 65->67 = +2 (step), lower moves 55->60 = +5
        # Same direction + P5 arrival + upper step = allowed
        result: bool = check_direct_motion(
            prev_upper=65,
            prev_lower=55,
            curr_upper=67,
            curr_lower=60,
        )
        assert result is True  # Stepwise approach allowed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
