"""Tests for planner.macro_form.

Category B tests: MacroForm planning for extended pieces.
Tests import only:
- planner.macro_form (module under test)
- planner.types (shared types)
- stdlib
"""
from fractions import Fraction

import pytest

from planner.macro_form import (
    build_macro_form,
    estimate_transition_bars,
    load_yaml,
    scale_section_bars,
    select_macro_arc,
    uses_macro_form,
)
from planner.plannertypes import Brief, Frame, MacroForm, MacroSection


def make_brief(
    affect: str = "Majestaet",
    genre: str = "fantasia",
    bars: int = 64,
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


class TestLoadYaml:
    """Test load_yaml function."""

    def test_loads_arc_selection(self) -> None:
        """Arc selection data loads successfully."""
        data: dict = load_yaml("arc_selection.yaml")
        assert "fantasia" in data
        assert "invention" in data

    def test_loads_fantasia_arcs(self) -> None:
        """Fantasia arcs data loads successfully."""
        data: dict = load_yaml("fantasia_arcs.yaml")
        assert "arch_form" in data
        assert "stormy_lyrical_triumphant" in data


class TestSelectMacroArc:
    """Test select_macro_arc function."""

    def test_fantasia_maestoso_uses_arch_form(self) -> None:
        """Fantasia with Majestaet affect uses arch_form."""
        brief: Brief = make_brief(affect="Majestaet", genre="fantasia")
        frame: Frame = make_frame()
        result: str = select_macro_arc(brief, frame)
        assert result == "arch_form"

    def test_fantasia_dolore_uses_stormy(self) -> None:
        """Fantasia with Klage affect uses stormy_lyrical_triumphant."""
        brief: Brief = make_brief(affect="Klage", genre="fantasia")
        frame: Frame = make_frame(mode="minor")
        result: str = select_macro_arc(brief, frame)
        assert result == "stormy_lyrical_triumphant"

    def test_fantasia_furioso_uses_tempestuous(self) -> None:
        """Fantasia with Zorn affect uses tempestuous."""
        brief: Brief = make_brief(affect="Zorn", genre="fantasia")
        frame: Frame = make_frame(mode="minor")
        result: str = select_macro_arc(brief, frame)
        assert result == "tempestuous"

    def test_fantasia_grazioso_uses_virtuosic(self) -> None:
        """Fantasia with Zaertlichkeit affect uses virtuosic_display."""
        brief: Brief = make_brief(affect="Zaertlichkeit", genre="fantasia")
        frame: Frame = make_frame()
        result: str = select_macro_arc(brief, frame)
        assert result == "virtuosic_display"

    def test_unknown_genre_raises(self) -> None:
        """Unknown genre raises assertion error."""
        brief: Brief = Brief(affect="Majestaet", genre="unknown", forces="keyboard", bars=64)
        frame: Frame = make_frame()
        with pytest.raises(AssertionError, match="No arc selection"):
            select_macro_arc(brief, frame)

    def test_unknown_affect_raises(self) -> None:
        """Unknown affect for genre raises assertion error."""
        brief: Brief = Brief(affect="unknown", genre="fantasia", forces="keyboard", bars=64)
        frame: Frame = make_frame()
        with pytest.raises(AssertionError, match="No arc for affect"):
            select_macro_arc(brief, frame)


class TestEstimateTransitionBars:
    """Test estimate_transition_bars function."""

    def test_same_key_and_character_no_transition(self) -> None:
        """Same key and character needs no transition bars."""
        sections: list[dict] = [
            {"key_area": "I", "character": "opening"},
            {"key_area": "I", "character": "opening"},
        ]
        result: int = estimate_transition_bars(sections)
        assert result == 0

    def test_different_key_needs_transition(self) -> None:
        """Different key areas need transition bars."""
        sections: list[dict] = [
            {"key_area": "I", "character": "opening"},
            {"key_area": "V", "character": "opening"},
        ]
        result: int = estimate_transition_bars(sections)
        assert result == 2

    def test_different_character_needs_transition(self) -> None:
        """Different characters need transition bars."""
        sections: list[dict] = [
            {"key_area": "I", "character": "opening"},
            {"key_area": "I", "character": "climax"},
        ]
        result: int = estimate_transition_bars(sections)
        assert result == 2

    def test_multiple_transitions(self) -> None:
        """Multiple transitions sum up."""
        sections: list[dict] = [
            {"key_area": "I", "character": "opening"},
            {"key_area": "V", "character": "development"},
            {"key_area": "I", "character": "closing"},
        ]
        # Two transitions: I->V and V->I
        result: int = estimate_transition_bars(sections)
        assert result == 4


class TestScaleSectionBars:
    """Test scale_section_bars function."""

    def test_scales_proportionally(self) -> None:
        """Sections are scaled proportionally to target."""
        sections: list[dict] = [
            {"bars": 40, "key_area": "I", "character": "A"},
            {"bars": 40, "key_area": "I", "character": "A"},
        ]
        template_total: int = 80
        target_bars: int = 80
        result: list[int] = scale_section_bars(sections, template_total, target_bars)
        # Equal proportions, no transitions
        assert sum(result) == target_bars

    def test_minimum_bars_is_four(self) -> None:
        """No section gets fewer than 4 bars."""
        sections: list[dict] = [
            {"bars": 100, "key_area": "I", "character": "A"},
            {"bars": 10, "key_area": "I", "character": "A"},
        ]
        template_total: int = 110
        target_bars: int = 20
        result: list[int] = scale_section_bars(sections, template_total, target_bars)
        assert all(b >= 4 for b in result)

    def test_rounds_to_multiples_of_four(self) -> None:
        """Section bars are rounded to multiples of 4."""
        sections: list[dict] = [
            {"bars": 30, "key_area": "I", "character": "A"},
            {"bars": 30, "key_area": "I", "character": "A"},
        ]
        template_total: int = 60
        target_bars: int = 48
        result: list[int] = scale_section_bars(sections, template_total, target_bars)
        assert all(b % 4 == 0 for b in result)


class TestBuildMacroForm:
    """Test build_macro_form function."""

    def test_returns_macro_form(self) -> None:
        """build_macro_form returns MacroForm object."""
        brief: Brief = make_brief(affect="Majestaet", genre="fantasia", bars=64)
        frame: Frame = make_frame()
        result: MacroForm = build_macro_form(brief, frame)
        assert isinstance(result, MacroForm)

    def test_has_sections(self) -> None:
        """MacroForm has sections tuple."""
        brief: Brief = make_brief(affect="Majestaet", genre="fantasia", bars=64)
        frame: Frame = make_frame()
        result: MacroForm = build_macro_form(brief, frame)
        assert len(result.sections) > 0
        assert all(isinstance(s, MacroSection) for s in result.sections)

    def test_has_climax_section(self) -> None:
        """MacroForm identifies climax section."""
        brief: Brief = make_brief(affect="Majestaet", genre="fantasia", bars=64)
        frame: Frame = make_frame()
        result: MacroForm = build_macro_form(brief, frame)
        assert result.climax_section is not None
        # Climax section label should exist in sections
        labels: list[str] = [s.label for s in result.sections]
        assert result.climax_section in labels

    def test_total_bars_matches_target(self) -> None:
        """Total bars approximately matches brief.bars."""
        brief: Brief = make_brief(affect="Majestaet", genre="fantasia", bars=64)
        frame: Frame = make_frame()
        result: MacroForm = build_macro_form(brief, frame)
        assert result.total_bars == brief.bars

    def test_section_fields_populated(self) -> None:
        """Each MacroSection has all fields populated."""
        brief: Brief = make_brief(affect="Majestaet", genre="fantasia", bars=64)
        frame: Frame = make_frame()
        result: MacroForm = build_macro_form(brief, frame)
        for section in result.sections:
            assert section.label is not None
            assert section.character is not None
            assert section.bars > 0
            assert section.texture is not None
            assert section.key_area is not None
            assert section.energy_arc is not None

    def test_arch_form_structure(self) -> None:
        """Arch form has expected section structure."""
        brief: Brief = make_brief(affect="Majestaet", genre="fantasia", bars=120)
        frame: Frame = make_frame()
        result: MacroForm = build_macro_form(brief, frame)
        # Arch form: A, B, C, B2, A2
        labels: list[str] = [s.label for s in result.sections]
        assert "A" in labels
        assert "C" in labels  # Climax in arch form
        assert result.climax_section == "C"


class TestUsesMacroForm:
    """Test uses_macro_form function."""

    def test_fantasia_uses_macro_form(self) -> None:
        """Fantasia genre uses macro-form planning."""
        brief: Brief = make_brief(genre="fantasia")
        result: bool = uses_macro_form(brief)
        assert result is True

    def test_invention_no_macro_form(self) -> None:
        """Invention genre does not use macro-form."""
        brief: Brief = make_brief(genre="invention")
        result: bool = uses_macro_form(brief)
        assert result is False


class TestIntegration:
    """Integration tests for macro_form module."""

    def test_stormy_lyrical_triumphant(self) -> None:
        """Stormy-lyrical-triumphant arc structure."""
        brief: Brief = make_brief(affect="Klage", genre="fantasia", bars=120)
        frame: Frame = make_frame(mode="minor")
        result: MacroForm = build_macro_form(brief, frame)
        # Should have stormy -> lyrical -> virtuosic -> triumphant
        labels: list[str] = [s.label for s in result.sections]
        assert "A" in labels
        assert "D" in labels  # Triumphant section
        assert result.climax_section == "D"

    def test_tempestuous_arc(self) -> None:
        """Tempestuous arc structure."""
        brief: Brief = make_brief(affect="Zorn", genre="fantasia", bars=140)
        frame: Frame = make_frame(mode="minor")
        result: MacroForm = build_macro_form(brief, frame)
        # Tempestuous has 5 sections ending in triumphant
        assert len(result.sections) == 5
        assert result.climax_section == "E"
