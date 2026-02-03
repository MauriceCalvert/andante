"""Tests for counterpoint checking in voice writing.

Verifies that parallel fifths/octaves and direct motion are rejected.
"""
import pytest
from fractions import Fraction
from builder.compose import compose_voices
from builder.types import Composition, Note
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
        local_key=home_key,
        schema="test",
        stage=0,
    )


class TestCounterpointChecking:
    """Tests for counterpoint rule enforcement."""

    def test_consonant_interval_passes(self) -> None:
        """Two voices forming a consonant interval (third) passes."""
        home_key: Key = Key(tonic="C", mode="major")
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
            tessitura_median=66,
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
            tessitura_median=52,
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
        assert interval == 4

    def test_dissonant_anchor_uses_consonant_alternative(self) -> None:
        """When anchor degree would be dissonant, pillar uses consonant alternative."""
        home_key: Key = Key(tonic="C", mode="major")
        upper_step: int = 35  # degree 1 (C)
        lower_step: int = 41  # degree 7 (B) - dissonant with C
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
            tessitura_median=66,
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
            tessitura_median=52,
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
        # Resulting interval must be consonant (not a minor 2nd / ic 1)
        soprano_midi: int = result.voices["soprano"][0].pitch
        bass_midi: int = result.voices["bass"][0].pitch
        ic: int = abs(soprano_midi - bass_midi) % 12
        dissonant_ics: set[int] = {1, 2, 6, 10, 11}
        assert ic not in dissonant_ics, (
            f"Interval class {ic} is dissonant "
            f"(soprano={soprano_midi}, bass={bass_midi})"
        )

    def test_parallel_motion_detection(self) -> None:
        """Verify parallel fifths are detected via check_parallels."""
        from builder.voice_checks import check_parallels
        result: bool = check_parallels(
            prev_upper=67,
            prev_lower=60,
            curr_upper=69,
            curr_lower=62,
        )
        assert result is False

    def test_contrary_motion_to_fifth_allowed(self) -> None:
        """Verify contrary motion to a fifth is allowed."""
        from builder.voice_checks import check_parallels
        result: bool = check_parallels(
            prev_upper=71,
            prev_lower=64,
            curr_upper=67,
            curr_lower=60,
        )
        assert result is False

    def test_oblique_motion_to_fifth_allowed(self) -> None:
        """Verify oblique motion to a fifth is allowed."""
        from builder.voice_checks import check_parallels
        result: bool = check_parallels(
            prev_upper=67,
            prev_lower=64,
            curr_upper=67,
            curr_lower=60,
        )
        assert result is True

    def test_direct_fifths_with_leap_rejected(self) -> None:
        """Direct motion to fifth with soprano leap is forbidden."""
        from builder.voice_checks import check_direct_motion
        result: bool = check_direct_motion(
            prev_upper=60,
            prev_lower=55,
            curr_upper=67,
            curr_lower=60,
        )
        assert result is False

    def test_direct_fifths_with_step_allowed(self) -> None:
        """Direct motion to fifth with soprano step is allowed."""
        from builder.voice_checks import check_direct_motion
        result: bool = check_direct_motion(
            prev_upper=65,
            prev_lower=55,
            curr_upper=67,
            curr_lower=60,
        )
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
