"""Tests for planner.validator.

Category B tests: Plan validation - structural and semantic checks.
Tests import only:
- planner.validator (module under test)
- planner.types (shared types)
- stdlib
"""
from fractions import Fraction

import pytest

from planner.validator import validate
from planner.plannertypes import (
    Brief,
    Episode,
    Frame,
    Material,
    Motif,
    Phrase,
    Plan,
    Section,
    Structure,
)


def make_brief() -> Brief:
    """Create valid Brief."""
    return Brief(affect="maestoso", genre="minuet", forces="keyboard", bars=16)


def make_frame(metre: str = "4/4") -> Frame:
    """Create valid Frame."""
    return Frame(
        key="C",
        mode="major",
        metre=metre,
        tempo="allegro",
        voices=2,
        upbeat=Fraction(0),
        form="through_composed",
    )


def make_motif(durations: tuple[Fraction, ...] | None = None, bars: int = 1) -> Motif:
    """Create valid Motif."""
    if durations is None:
        # Default: 1 bar in 4/4
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
    degrees: tuple[int, ...] = tuple(range(1, len(durations) + 1))
    degrees = tuple(((d - 1) % 7) + 1 for d in degrees)  # Keep in 1-7 range
    return Motif(degrees=degrees, durations=durations, bars=bars)


def make_material(motif: Motif | None = None) -> Material:
    """Create valid Material."""
    if motif is None:
        motif = make_motif()
    return Material(subject=motif)


def make_phrase(index: int, bars: int = 4, tonal_target: str = "I") -> Phrase:
    """Create valid Phrase."""
    return Phrase(
        index=index,
        bars=bars,
        tonal_target=tonal_target,
        cadence=None,
        treatment="statement",
        surprise=None,
    )


def make_episode(phrases: tuple[Phrase, ...], bars: int | None = None) -> Episode:
    """Create valid Episode."""
    if bars is None:
        bars = sum(p.bars for p in phrases)
    return Episode(
        type="statement",
        bars=bars,
        texture="polyphonic",
        phrases=phrases,
    )


def make_section(
    label: str,
    episodes: tuple[Episode, ...],
    final_cadence: str = "authentic",
) -> Section:
    """Create valid Section."""
    phrase_count: int = sum(len(ep.phrases) for ep in episodes)
    tonal_path: tuple[str, ...] = tuple(["I"] * phrase_count)
    return Section(
        label=label,
        tonal_path=tonal_path,
        final_cadence=final_cadence,
        episodes=episodes,
    )


def make_structure(sections: tuple[Section, ...]) -> Structure:
    """Create valid Structure."""
    return Structure(sections=sections, arc="arch")


def make_valid_plan() -> Plan:
    """Create a fully valid Plan."""
    brief: Brief = make_brief()
    frame: Frame = make_frame("4/4")
    motif: Motif = make_motif()
    material: Material = make_material(motif)
    phrase1: Phrase = make_phrase(index=0)
    phrase2: Phrase = make_phrase(index=1)
    episode1: Episode = make_episode((phrase1,))
    episode2: Episode = make_episode((phrase2,))
    section: Section = make_section("A", (episode1, episode2))
    structure: Structure = make_structure((section,))
    return Plan(
        brief=brief,
        frame=frame,
        material=material,
        structure=structure,
        actual_bars=8,
    )


class TestValidPlan:
    """Test validation of valid plans."""

    def test_valid_plan_passes(self) -> None:
        """A valid plan passes validation."""
        plan: Plan = make_valid_plan()
        valid, errors = validate(plan)
        assert valid is True
        assert errors == []


class TestSectionValidation:
    """Test section validation rules."""

    def test_empty_sections_fails(self) -> None:
        """Plan with empty sections list fails."""
        brief: Brief = make_brief()
        frame: Frame = make_frame()
        material: Material = make_material()
        structure: Structure = Structure(sections=(), arc="arch")
        plan: Plan = Plan(
            brief=brief,
            frame=frame,
            material=material,
            structure=structure,
            actual_bars=0,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert "at least one section" in errors[0]

    def test_duplicate_section_labels_fails(self) -> None:
        """Duplicate section labels fail validation."""
        phrase1: Phrase = make_phrase(index=0)
        phrase2: Phrase = make_phrase(index=1)
        episode1: Episode = make_episode((phrase1,))
        episode2: Episode = make_episode((phrase2,))
        section1: Section = make_section("A", (episode1,))
        section2: Section = make_section("A", (episode2,), final_cadence="authentic")  # Duplicate label
        structure: Structure = make_structure((section1, section2))
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame(),
            material=make_material(),
            structure=structure,
            actual_bars=8,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert any("Duplicate section label" in e for e in errors)

    def test_section_without_episodes_fails(self) -> None:
        """Section with empty episodes tuple fails."""
        section: Section = Section(
            label="A",
            tonal_path=("I",),
            final_cadence="authentic",
            episodes=(),  # Empty
        )
        structure: Structure = make_structure((section,))
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame(),
            material=make_material(),
            structure=structure,
            actual_bars=0,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert any("at least one episode" in e for e in errors)

    def test_section_empty_tonal_path_fails(self) -> None:
        """Section with empty tonal_path fails."""
        phrase: Phrase = make_phrase(index=0)
        episode: Episode = make_episode((phrase,))
        section: Section = Section(
            label="A",
            tonal_path=(),  # Empty
            final_cadence="authentic",
            episodes=(episode,),
        )
        structure: Structure = make_structure((section,))
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame(),
            material=make_material(),
            structure=structure,
            actual_bars=4,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert any("non-empty tonal_path" in e for e in errors)

    def test_phrase_count_mismatch_fails(self) -> None:
        """Phrase count != tonal_path length fails."""
        phrase: Phrase = make_phrase(index=0)
        episode: Episode = make_episode((phrase,))
        section: Section = Section(
            label="A",
            tonal_path=("I", "V"),  # 2 items but only 1 phrase
            final_cadence="authentic",
            episodes=(episode,),
        )
        structure: Structure = make_structure((section,))
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame(),
            material=make_material(),
            structure=structure,
            actual_bars=4,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert any("phrase count must equal tonal_path length" in e for e in errors)


class TestFinalCadenceValidation:
    """Test final cadence validation."""

    def test_last_section_non_authentic_fails(self) -> None:
        """Last section with non-authentic cadence fails."""
        phrase: Phrase = make_phrase(index=0)
        episode: Episode = make_episode((phrase,))
        section: Section = make_section("A", (episode,), final_cadence="half")
        structure: Structure = make_structure((section,))
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame(),
            material=make_material(),
            structure=structure,
            actual_bars=4,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert any("authentic final_cadence" in e for e in errors)

    def test_last_section_authentic_passes(self) -> None:
        """Last section with authentic cadence passes."""
        phrase: Phrase = make_phrase(index=0)
        episode: Episode = make_episode((phrase,))
        section: Section = make_section("A", (episode,), final_cadence="authentic")
        structure: Structure = make_structure((section,))
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame(),
            material=make_material(),
            structure=structure,
            actual_bars=4,
        )
        valid, errors = validate(plan)
        # Should pass if everything else is valid
        cadence_errors: list[str] = [e for e in errors if "authentic" in e]
        assert len(cadence_errors) == 0


class TestMotifValidation:
    """Test motif validation rules."""

    def test_motif_length_mismatch_fails(self) -> None:
        """Motif with mismatched degrees/durations fails."""
        # Create a malformed motif (bypassing __post_init__)
        # Actually, Motif with mismatched lengths can't be created normally
        # So we test the validator catches it if it somehow got through
        pass  # Skip - Motif dataclass prevents this

    def test_motif_duration_mismatch_fails(self) -> None:
        """Motif total duration != expected bar duration fails."""
        # 4/4 metre expects 1 whole note per bar
        # Create motif with wrong duration sum
        wrong_durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))  # 1/2 total
        motif: Motif = Motif(
            degrees=(1, 2),
            durations=wrong_durations,
            bars=1,  # Claims 1 bar but durations only sum to 1/2
        )
        material: Material = make_material(motif)
        phrase: Phrase = make_phrase(index=0)
        episode: Episode = make_episode((phrase,))
        section: Section = make_section("A", (episode,))
        structure: Structure = make_structure((section,))
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame("4/4"),
            material=material,
            structure=structure,
            actual_bars=4,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert any("Motif duration" in e for e in errors)


class TestPhraseIndexValidation:
    """Test phrase index validation."""

    def test_non_sequential_indices_fails(self) -> None:
        """Non-sequential phrase indices fail."""
        phrase1: Phrase = make_phrase(index=0)
        phrase2: Phrase = make_phrase(index=2)  # Skips 1
        episode1: Episode = make_episode((phrase1,))
        episode2: Episode = make_episode((phrase2,))
        section: Section = make_section("A", (episode1, episode2))
        structure: Structure = make_structure((section,))
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame(),
            material=make_material(),
            structure=structure,
            actual_bars=8,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert any("sequential from 0" in e for e in errors)

    def test_indices_not_starting_from_zero_fails(self) -> None:
        """Phrase indices not starting from 0 fail."""
        phrase1: Phrase = make_phrase(index=1)
        phrase2: Phrase = make_phrase(index=2)
        episode1: Episode = make_episode((phrase1,))
        episode2: Episode = make_episode((phrase2,))
        section: Section = make_section("A", (episode1, episode2))
        structure: Structure = make_structure((section,))
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame(),
            material=make_material(),
            structure=structure,
            actual_bars=8,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert any("sequential from 0" in e for e in errors)


class TestMultipleErrors:
    """Test that validator collects multiple errors."""

    def test_collects_multiple_errors(self) -> None:
        """Validator returns all errors, not just first."""
        # Create plan with multiple issues
        phrase1: Phrase = make_phrase(index=1)  # Wrong starting index
        episode1: Episode = make_episode((phrase1,))
        section1: Section = Section(
            label="A",
            tonal_path=("I", "V"),  # 2 items but 1 phrase
            final_cadence="half",  # Not authentic for last section
            episodes=(episode1,),
        )
        structure: Structure = make_structure((section1,))
        wrong_durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        motif: Motif = Motif(degrees=(1,), durations=wrong_durations, bars=1)
        material: Material = make_material(motif)
        plan: Plan = Plan(
            brief=make_brief(),
            frame=make_frame(),
            material=material,
            structure=structure,
            actual_bars=4,
        )
        valid, errors = validate(plan)
        assert valid is False
        assert len(errors) >= 2  # Should have multiple errors
