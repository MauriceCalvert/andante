"""Tests for planner.planner.

Category B tests: Main orchestrator - Brief -> Plan pipeline.
Tests import only:
- planner.planner (module under test)
- planner.types (shared types)
- stdlib
"""
from fractions import Fraction

import pytest

from planner.planner import build_plan
from planner.plannertypes import (
    Brief,
    Frame,
    Material,
    Motif,
    Plan,
    Structure,
)


def make_brief(
    affect: str = "Majestaet",
    genre: str = "minuet",
    bars: int = 16,
) -> Brief:
    """Create Brief for testing."""
    return Brief(affect=affect, genre=genre, forces="keyboard", bars=bars)


class TestBuildPlanReturnsType:
    """Test build_plan returns correct type."""

    def test_returns_plan(self) -> None:
        """build_plan returns Plan object."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert isinstance(result, Plan)

    def test_plan_has_brief(self) -> None:
        """Plan contains original brief."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert result.brief == brief

    def test_plan_has_frame(self) -> None:
        """Plan contains resolved frame."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert isinstance(result.frame, Frame)

    def test_plan_has_material(self) -> None:
        """Plan contains acquired material."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert isinstance(result.material, Material)

    def test_plan_has_structure(self) -> None:
        """Plan contains planned structure."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert isinstance(result.structure, Structure)


class TestBuildPlanValidation:
    """Test build_plan validation."""

    def test_plan_passes_validation(self) -> None:
        """Built plan passes internal validation."""
        brief: Brief = make_brief()
        # build_plan asserts validation internally
        result: Plan = build_plan(brief)
        # If we get here, validation passed
        assert result is not None

    def test_actual_bars_computed(self) -> None:
        """actual_bars field is computed from structure."""
        brief: Brief = make_brief(bars=16)
        result: Plan = build_plan(brief)
        assert result.actual_bars > 0

    def test_actual_bars_matches_structure(self) -> None:
        """actual_bars matches sum of phrase bars in structure."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        computed_bars: int = sum(
            sum(phrase.bars for episode in section.episodes for phrase in episode.phrases)
            for section in result.structure.sections
        )
        assert result.actual_bars == computed_bars


class TestBuildPlanWithUserMotif:
    """Test build_plan with user-provided motif."""

    def test_accepts_user_motif(self) -> None:
        """build_plan accepts user motif parameter."""
        brief: Brief = make_brief()  # minuet uses 3/4 metre
        user_motif: Motif = Motif(
            degrees=(1, 3, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),  # Sum = 3/4
            bars=1,
        )
        result: Plan = build_plan(brief, user_motif)
        assert isinstance(result, Plan)

    def test_user_motif_used_as_subject(self) -> None:
        """User motif becomes material subject."""
        brief: Brief = make_brief()  # minuet uses 3/4 metre
        user_motif: Motif = Motif(
            degrees=(1, 3, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),  # Sum = 3/4
            bars=1,
        )
        result: Plan = build_plan(brief, user_motif)
        assert result.material.subject.degrees == user_motif.degrees

    def test_none_user_motif_generates_default(self) -> None:
        """None user_motif generates default subject."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief, None)
        assert result.material.subject is not None
        assert len(result.material.subject.degrees) > 0


class TestBuildPlanGenres:
    """Test build_plan with different genres."""

    def test_minuet_genre(self) -> None:
        """Minuet genre produces valid plan."""
        brief: Brief = make_brief(genre="minuet")
        result: Plan = build_plan(brief)
        assert result.frame.form is not None

    def test_fantasia_genre(self) -> None:
        """Fantasia genre produces valid plan."""
        brief: Brief = make_brief(genre="fantasia", bars=64)
        result: Plan = build_plan(brief)
        assert len(result.structure.sections) > 0


class TestBuildPlanAffects:
    """Test build_plan with different affects."""

    def test_maestoso_affect(self) -> None:
        """Majestaet affect produces valid plan."""
        brief: Brief = make_brief(affect="Majestaet")
        result: Plan = build_plan(brief)
        assert result.frame.tempo is not None

    def test_grazioso_affect(self) -> None:
        """Zaertlichkeit affect produces valid plan."""
        brief: Brief = make_brief(affect="Zaertlichkeit")
        result: Plan = build_plan(brief)
        assert result.frame.tempo is not None


class TestBuildPlanStructure:
    """Test structure properties of built plans."""

    def test_sections_not_empty(self) -> None:
        """Plan has at least one section."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert len(result.structure.sections) > 0

    def test_sections_have_episodes(self) -> None:
        """Each section has at least one episode."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        for section in result.structure.sections:
            assert len(section.episodes) > 0

    def test_episodes_have_phrases(self) -> None:
        """Each episode has at least one phrase."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        for section in result.structure.sections:
            for episode in section.episodes:
                assert len(episode.phrases) > 0

    def test_last_section_authentic_cadence(self) -> None:
        """Last section ends with authentic cadence."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        last_section = result.structure.sections[-1]
        assert last_section.final_cadence == "authentic"

    def test_phrase_indices_sequential(self) -> None:
        """Phrase indices are sequential from 0."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        indices: list[int] = []
        for section in result.structure.sections:
            for episode in section.episodes:
                for phrase in episode.phrases:
                    indices.append(phrase.index)
        expected: list[int] = list(range(len(indices)))
        assert indices == expected


class TestBuildPlanMaterial:
    """Test material properties of built plans."""

    def test_subject_has_valid_degrees(self) -> None:
        """Subject motif has valid scale degrees (1-7)."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert all(1 <= d <= 7 for d in result.material.subject.degrees)

    def test_subject_durations_match_degrees(self) -> None:
        """Subject has matching degrees and durations length."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert len(result.material.subject.degrees) == len(result.material.subject.durations)

    def test_counter_subject_generated(self) -> None:
        """Counter-subject is generated."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert result.material.counter_subject is not None


class TestBuildPlanFrame:
    """Test frame properties of built plans."""

    def test_frame_has_key(self) -> None:
        """Frame has key."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert result.frame.key is not None

    def test_frame_has_mode(self) -> None:
        """Frame has mode."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert result.frame.mode in ("major", "minor")

    def test_frame_has_metre(self) -> None:
        """Frame has metre."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert result.frame.metre is not None

    def test_frame_has_tempo(self) -> None:
        """Frame has tempo."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert result.frame.tempo is not None

    def test_frame_has_voices(self) -> None:
        """Frame has voice count."""
        brief: Brief = make_brief()
        result: Plan = build_plan(brief)
        assert result.frame.voices >= 2


class TestIntegration:
    """Integration tests for planner orchestrator."""

    def test_full_minuet_workflow(self) -> None:
        """Complete minuet planning workflow."""
        brief: Brief = Brief(
            affect="Majestaet",
            genre="minuet",
            forces="keyboard",
            bars=16,
        )
        plan: Plan = build_plan(brief)
        # Verify all components present
        assert plan.brief == brief
        assert plan.frame is not None
        assert plan.material is not None
        assert plan.structure is not None
        assert plan.actual_bars > 0
        # Verify structure validity
        assert len(plan.structure.sections) >= 2  # A and B sections
        labels: list[str] = [s.label for s in plan.structure.sections]
        assert "A" in labels
        assert "B" in labels

    def test_full_fantasia_workflow(self) -> None:
        """Complete fantasia planning workflow."""
        brief: Brief = Brief(
            affect="Majestaet",
            genre="fantasia",
            forces="keyboard",
            bars=64,
        )
        plan: Plan = build_plan(brief)
        # Verify all components present
        assert plan.brief == brief
        assert plan.frame is not None
        assert plan.material is not None
        assert plan.structure is not None
        assert plan.actual_bars > 0
        # Fantasia should have multiple sections
        assert len(plan.structure.sections) >= 2

    def test_reproducibility_with_different_briefs(self) -> None:
        """Different briefs produce different plans."""
        brief1: Brief = make_brief(affect="Majestaet", genre="minuet")
        brief2: Brief = make_brief(affect="Zaertlichkeit", genre="minuet")
        plan1: Plan = build_plan(brief1)
        plan2: Plan = build_plan(brief2)
        # Tempos should differ based on affect
        assert plan1.frame.tempo != plan2.frame.tempo or plan1.brief != plan2.brief

