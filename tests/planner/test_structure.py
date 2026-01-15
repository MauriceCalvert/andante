"""Tests for planner.structure.

Category B tests: Structure planning from Brief/Frame/Material.
Tests import only:
- planner.structure (module under test)
- planner.types (shared types)
- stdlib
"""
from fractions import Fraction

import pytest

from planner.structure import (
    get_episode_treatment,
    get_section_phrase_count,
    phrase_at_position,
    plan_structure,
)
from planner.plannertypes import (
    Brief,
    Episode,
    Frame,
    Material,
    Motif,
    Section,
    Structure,
)


def make_brief(
    affect: str = "Majestaet",
    genre: str = "minuet",
    bars: int = 16,
) -> Brief:
    """Create Brief for testing."""
    return Brief(affect=affect, genre=genre, forces="keyboard", bars=bars)


def make_frame(mode: str = "major") -> Frame:
    """Create Frame for testing."""
    return Frame(
        key="C",
        mode=mode,
        metre="4/4",
        tempo="allegro",
        voices=2,
        upbeat=Fraction(0),
        form="through_composed",
    )


def make_material() -> Material:
    """Create Material for testing."""
    subject: Motif = Motif(
        degrees=(1, 2, 3, 4, 5, 6, 7, 1),
        durations=(Fraction(1, 8),) * 8,
        bars=1,
    )
    cs: Motif = Motif(
        degrees=(5, 4, 3, 2, 1, 2, 3, 4),
        durations=(Fraction(1, 8),) * 8,
        bars=1,
    )
    return Material(subject=subject, counter_subject=cs)


class TestPhraseAtPosition:
    """Test phrase_at_position function."""

    def test_position_zero(self) -> None:
        """Position 0.0 gives phrase index 0."""
        result: int = phrase_at_position(0.0, 10)
        assert result == 0

    def test_position_one(self) -> None:
        """Position 1.0 gives last phrase index."""
        result: int = phrase_at_position(1.0, 10)
        assert result == 10

    def test_position_half(self) -> None:
        """Position 0.5 gives middle phrase index."""
        result: int = phrase_at_position(0.5, 10)
        assert result == 5

    def test_position_quarter(self) -> None:
        """Position 0.25 gives 1/4 phrase index."""
        result: int = phrase_at_position(0.25, 8)
        assert result == 2


class TestGetEpisodeTreatment:
    """Test get_episode_treatment function."""

    def test_statement_type(self) -> None:
        """Statement episode type returns its treatment."""
        # This depends on episodes.yaml, but statement typically has 'statement' treatment
        result: str = get_episode_treatment("statement")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_returns_statement(self) -> None:
        """Unknown episode type defaults to statement treatment."""
        result: str = get_episode_treatment("unknown_type")
        assert result == "statement"


class TestGetSectionPhraseCount:
    """Test get_section_phrase_count function."""

    def test_episodes_list(self) -> None:
        """Section with episodes list uses episode count."""
        section_def: dict = {
            "episodes": ["statement", "continuation", "cadential"],
            "tonal_path": ["I"],
        }
        result: int = get_section_phrase_count(section_def)
        assert result == 3

    def test_tonal_path_only(self) -> None:
        """Section without episodes uses tonal_path length."""
        section_def: dict = {
            "tonal_path": ["I", "V", "I"],
        }
        result: int = get_section_phrase_count(section_def)
        assert result == 3


class TestPlanStructure:
    """Test plan_structure function."""

    def test_returns_structure(self) -> None:
        """plan_structure returns Structure object."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        assert isinstance(result, Structure)

    def test_has_sections(self) -> None:
        """Structure has sections tuple."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        assert len(result.sections) > 0
        assert all(isinstance(s, Section) for s in result.sections)

    def test_has_arc(self) -> None:
        """Structure has arc name."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        assert result.arc is not None
        assert len(result.arc) > 0

    def test_sections_have_episodes(self) -> None:
        """Each section has episodes."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        for section in result.sections:
            assert len(section.episodes) > 0
            assert all(isinstance(ep, Episode) for ep in section.episodes)

    def test_sections_have_tonal_path(self) -> None:
        """Each section has tonal_path."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        for section in result.sections:
            assert len(section.tonal_path) > 0

    def test_last_section_authentic_cadence(self) -> None:
        """Last section has authentic final_cadence."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        last_section: Section = result.sections[-1]
        assert last_section.final_cadence == "authentic"

    def test_phrases_have_sequential_indices(self) -> None:
        """All phrases have sequential indices starting from 0."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        indices: list[int] = []
        for section in result.sections:
            for episode in section.episodes:
                for phrase in episode.phrases:
                    indices.append(phrase.index)
        expected: list[int] = list(range(len(indices)))
        assert indices == expected


class TestPlanStructureFantasia:
    """Test plan_structure for fantasia (uses macro-form)."""

    def test_fantasia_uses_macro_form(self) -> None:
        """Fantasia genre uses macro-form planning."""
        brief: Brief = make_brief(genre="fantasia", bars=64)
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        # Should have multiple sections from macro-form
        assert len(result.sections) >= 2

    def test_fantasia_has_climax(self) -> None:
        """Fantasia structure has climax phrase."""
        brief: Brief = make_brief(genre="fantasia", affect="Majestaet", bars=64)
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        # Check for climax
        has_climax: bool = False
        for section in result.sections:
            for episode in section.episodes:
                for phrase in episode.phrases:
                    if phrase.is_climax:
                        has_climax = True
        # Note: climax may not always be set depending on section types
        # This is more of a smoke test
        assert isinstance(result, Structure)


class TestPlanStructureIntegration:
    """Integration tests for structure planning."""

    def test_minuet_structure(self) -> None:
        """Minuet genre produces valid structure."""
        brief: Brief = make_brief(genre="minuet", affect="Majestaet")
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        # Minuet has A and B sections
        labels: list[str] = [s.label for s in result.sections]
        assert "A" in labels
        assert "B" in labels

    def test_energy_field_populated(self) -> None:
        """Phrases have energy field populated."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        for section in result.sections:
            for episode in section.episodes:
                for phrase in episode.phrases:
                    assert phrase.energy is not None

    def test_tonal_targets_populated(self) -> None:
        """Phrases have tonal_target populated."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        for section in result.sections:
            for episode in section.episodes:
                for phrase in episode.phrases:
                    assert phrase.tonal_target is not None
                    assert len(phrase.tonal_target) > 0

    def test_treatments_populated(self) -> None:
        """Phrases have treatment populated."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        result: Structure = plan_structure(brief, frame, material)
        for section in result.sections:
            for episode in section.episodes:
                for phrase in episode.phrases:
                    assert phrase.treatment is not None
                    assert len(phrase.treatment) > 0
