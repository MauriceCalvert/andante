"""Tests for planner.section_planner.

Category B tests: MacroSection -> SectionPlan with episodes.
Tests import only:
- planner.section_planner (module under test)
- planner.types (shared types)
- stdlib
"""
import pytest

from planner.section_planner import (
    get_next_seed,
    plan_all_sections,
    plan_section,
    reset_seed_counter,
)
from planner.plannertypes import (
    EpisodeSpec,
    MacroForm,
    MacroSection,
    SectionPlan,
)


def make_section(
    label: str = "A",
    character: str = "opening",
    bars: int = 16,
    texture: str = "polyphonic",
    key_area: str = "I",
    energy_arc: str = "rising",
) -> MacroSection:
    """Create MacroSection for testing."""
    return MacroSection(
        label=label,
        character=character,
        bars=bars,
        texture=texture,
        key_area=key_area,
        energy_arc=energy_arc,
    )


def make_macro_form(sections: list[MacroSection]) -> MacroForm:
    """Create MacroForm for testing."""
    total: int = sum(s.bars for s in sections)
    return MacroForm(
        sections=tuple(sections),
        climax_section="A",
        total_bars=total,
    )


class TestSeedCounter:
    """Test seed counter functions."""

    def test_reset_seed_counter(self) -> None:
        """reset_seed_counter resets to given value."""
        reset_seed_counter(0)
        seed1: int = get_next_seed()
        assert seed1 == 0

    def test_get_next_seed_increments(self) -> None:
        """get_next_seed increments counter."""
        reset_seed_counter(10)
        seed1: int = get_next_seed()
        seed2: int = get_next_seed()
        assert seed1 == 10
        assert seed2 == 11

    def test_reset_to_custom_value(self) -> None:
        """reset_seed_counter can start at custom value."""
        reset_seed_counter(100)
        seed: int = get_next_seed()
        assert seed == 100


class TestPlanSection:
    """Test plan_section function."""

    def test_returns_section_plan(self) -> None:
        """plan_section returns SectionPlan."""
        reset_seed_counter(42)
        section: MacroSection = make_section()
        result: SectionPlan = plan_section(section)
        assert isinstance(result, SectionPlan)

    def test_preserves_label(self) -> None:
        """SectionPlan preserves section label."""
        reset_seed_counter(42)
        section: MacroSection = make_section(label="B")
        result: SectionPlan = plan_section(section)
        assert result.label == "B"

    def test_preserves_character(self) -> None:
        """SectionPlan preserves section character."""
        reset_seed_counter(42)
        section: MacroSection = make_section(character="climax")
        result: SectionPlan = plan_section(section)
        assert result.character == "climax"

    def test_preserves_texture(self) -> None:
        """SectionPlan preserves section texture."""
        reset_seed_counter(42)
        section: MacroSection = make_section(texture="melody_accompaniment")
        result: SectionPlan = plan_section(section)
        assert result.texture == "melody_accompaniment"

    def test_preserves_key_area(self) -> None:
        """SectionPlan preserves section key_area."""
        reset_seed_counter(42)
        section: MacroSection = make_section(key_area="V")
        result: SectionPlan = plan_section(section)
        assert result.key_area == "V"

    def test_has_episodes(self) -> None:
        """SectionPlan has episode list."""
        reset_seed_counter(42)
        section: MacroSection = make_section(bars=16)
        result: SectionPlan = plan_section(section)
        assert len(result.episodes) > 0
        assert all(isinstance(ep, EpisodeSpec) for ep in result.episodes)

    def test_total_bars_matches(self) -> None:
        """SectionPlan total_bars equals sum of episode bars."""
        reset_seed_counter(42)
        section: MacroSection = make_section(bars=16)
        result: SectionPlan = plan_section(section)
        assert result.total_bars == sum(ep.bars for ep in result.episodes)

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed produces same result."""
        reset_seed_counter(42)
        section1: MacroSection = make_section(bars=16)
        result1: SectionPlan = plan_section(section1)
        reset_seed_counter(42)
        section2: MacroSection = make_section(bars=16)
        result2: SectionPlan = plan_section(section2)
        assert result1 == result2


class TestPlanAllSections:
    """Test plan_all_sections function."""

    def test_returns_tuple(self) -> None:
        """plan_all_sections returns tuple of SectionPlan."""
        reset_seed_counter(0)
        sections: list[MacroSection] = [
            make_section(label="A"),
            make_section(label="B"),
        ]
        macro: MacroForm = make_macro_form(sections)
        result: tuple[SectionPlan, ...] = plan_all_sections(macro)
        assert isinstance(result, tuple)
        assert all(isinstance(sp, SectionPlan) for sp in result)

    def test_plans_all_sections(self) -> None:
        """Returns plan for each section."""
        reset_seed_counter(0)
        sections: list[MacroSection] = [
            make_section(label="A"),
            make_section(label="B"),
            make_section(label="C"),
        ]
        macro: MacroForm = make_macro_form(sections)
        result: tuple[SectionPlan, ...] = plan_all_sections(macro)
        assert len(result) == 3
        labels: list[str] = [sp.label for sp in result]
        assert labels == ["A", "B", "C"]

    def test_inserts_transitions_when_needed(self) -> None:
        """Transitions inserted between sections with different keys."""
        reset_seed_counter(0)
        sections: list[MacroSection] = [
            make_section(label="A", key_area="I", character="opening"),
            make_section(label="B", key_area="V", character="development"),
        ]
        macro: MacroForm = make_macro_form(sections)
        result: tuple[SectionPlan, ...] = plan_all_sections(macro)
        # First section should have transition appended
        first_plan: SectionPlan = result[0]
        has_transition: bool = any(ep.is_transition for ep in first_plan.episodes)
        assert has_transition

    def test_no_transition_same_key_and_character(self) -> None:
        """No transition when sections have same key and character."""
        reset_seed_counter(0)
        sections: list[MacroSection] = [
            make_section(label="A", key_area="I", character="opening"),
            make_section(label="B", key_area="I", character="opening"),
        ]
        macro: MacroForm = make_macro_form(sections)
        result: tuple[SectionPlan, ...] = plan_all_sections(macro)
        first_plan: SectionPlan = result[0]
        has_transition: bool = any(ep.is_transition for ep in first_plan.episodes)
        assert not has_transition

    def test_transition_for_different_character_same_key(self) -> None:
        """Transition inserted when character differs but key is same."""
        reset_seed_counter(0)
        sections: list[MacroSection] = [
            make_section(label="A", key_area="I", character="opening"),
            make_section(label="B", key_area="I", character="climax"),
        ]
        macro: MacroForm = make_macro_form(sections)
        result: tuple[SectionPlan, ...] = plan_all_sections(macro)
        first_plan: SectionPlan = result[0]
        has_transition: bool = any(ep.is_transition for ep in first_plan.episodes)
        assert has_transition


class TestIntegration:
    """Integration tests for section_planner."""

    def test_full_macro_form_workflow(self) -> None:
        """Complete workflow with multi-section macro-form."""
        reset_seed_counter(0)
        sections: list[MacroSection] = [
            make_section(label="A", bars=16, key_area="I", character="opening", energy_arc="rising"),
            make_section(label="B", bars=24, key_area="V", character="development", energy_arc="rising"),
            make_section(label="C", bars=8, key_area="I", character="climax", energy_arc="peak"),
            make_section(label="D", bars=16, key_area="I", character="closing", energy_arc="resolving"),
        ]
        macro: MacroForm = make_macro_form(sections)
        result: tuple[SectionPlan, ...] = plan_all_sections(macro)
        # Should have 4 section plans
        assert len(result) == 4
        # Each should have episodes
        for sp in result:
            assert len(sp.episodes) > 0
        # Labels preserved
        assert [sp.label for sp in result] == ["A", "B", "C", "D"]

    def test_single_section(self) -> None:
        """Single section workflow."""
        reset_seed_counter(0)
        sections: list[MacroSection] = [
            make_section(label="A", bars=32),
        ]
        macro: MacroForm = make_macro_form(sections)
        result: tuple[SectionPlan, ...] = plan_all_sections(macro)
        assert len(result) == 1
        assert result[0].label == "A"
