"""Tests for planner.frame.

Category B tests: Brief -> Frame resolution.
Tests import only:
- planner.frame (module under test)
- planner.types (shared types)
- stdlib

Uses German Affektenlehre terms (see affects.yaml).
"""
from fractions import Fraction

import pytest

from planner.frame import (
    load_yaml,
    parse_upbeat,
    resolve_frame,
)
from planner.plannertypes import Brief, Frame


def make_brief(
    affect: str = "Majestaet",
    genre: str = "invention",
    forces: str = "keyboard",
    bars: int = 16,
) -> Brief:
    """Create Brief with specified parameters."""
    return Brief(affect=affect, genre=genre, forces=forces, bars=bars)


class TestLoadYaml:
    """Test load_yaml function."""

    def test_loads_affects(self) -> None:
        """Affects data loads successfully (German Affektenlehre)."""
        data: dict = load_yaml("affects.yaml")
        assert "Majestaet" in data
        assert "Klage" in data

    def test_loads_keys(self) -> None:
        """Keys data loads successfully."""
        data: dict = load_yaml("keys.yaml")
        assert "dark" in data
        assert "bright" in data

    def test_loads_genre(self) -> None:
        """Genre data loads successfully."""
        data: dict = load_yaml("genres/invention.yaml")
        assert "voices" in data
        assert "metre" in data


class TestParseUpbeat:
    """Test parse_upbeat function."""

    def test_int_zero(self) -> None:
        """Integer 0 parses to Fraction(0)."""
        result: Fraction = parse_upbeat(0)
        assert result == Fraction(0)

    def test_string_fraction(self) -> None:
        """String fraction parses correctly."""
        result: Fraction = parse_upbeat("1/4")
        assert result == Fraction(1, 4)

    def test_string_half(self) -> None:
        """String '1/2' parses to Fraction(1, 2)."""
        result: Fraction = parse_upbeat("1/2")
        assert result == Fraction(1, 2)

    def test_int_positive(self) -> None:
        """Positive integer parses to Fraction."""
        result: Fraction = parse_upbeat(1)
        assert result == Fraction(1)


class TestResolveFrame:
    """Test resolve_frame function."""

    def test_returns_frame(self) -> None:
        """resolve_frame returns Frame object."""
        brief: Brief = make_brief()
        result: Frame = resolve_frame(brief)
        assert isinstance(result, Frame)

    def test_majestaet_major_mode(self) -> None:
        """Majestaet affect produces major mode."""
        brief: Brief = make_brief(affect="Majestaet")
        result: Frame = resolve_frame(brief)
        assert result.mode == "major"

    def test_klage_minor_mode(self) -> None:
        """Klage affect produces minor mode."""
        brief: Brief = make_brief(affect="Klage")
        result: Frame = resolve_frame(brief)
        assert result.mode == "minor"

    def test_zorn_minor_mode(self) -> None:
        """Zorn affect produces minor mode."""
        brief: Brief = make_brief(affect="Zorn")
        result: Frame = resolve_frame(brief)
        assert result.mode == "minor"

    def test_zaertlichkeit_major_mode(self) -> None:
        """Zaertlichkeit affect produces major mode."""
        brief: Brief = make_brief(affect="Zaertlichkeit")
        result: Frame = resolve_frame(brief)
        assert result.mode == "major"

    def test_tempo_from_affect(self) -> None:
        """Tempo comes from affect definition."""
        brief: Brief = make_brief(affect="Klage")
        result: Frame = resolve_frame(brief)
        assert result.tempo in ["adagio", "lento", "grave", "largo"]

    def test_tempo_allegro_for_majestaet(self) -> None:
        """Majestaet has stately tempo."""
        brief: Brief = make_brief(affect="Majestaet")
        result: Frame = resolve_frame(brief)
        assert result.tempo in ["allegro", "moderato", "andante"]

    def test_tempo_presto_for_zorn(self) -> None:
        """Zorn has fast tempo."""
        brief: Brief = make_brief(affect="Zorn")
        result: Frame = resolve_frame(brief)
        assert result.tempo in ["presto", "vivace", "allegro"]

    def test_key_from_character(self) -> None:
        """Key is selected based on key_character in affect."""
        brief: Brief = make_brief(affect="Majestaet")
        result: Frame = resolve_frame(brief)
        assert result.key is not None

    def test_bright_key(self) -> None:
        """Bright key character produces valid key."""
        brief: Brief = make_brief(affect="Zaertlichkeit")
        result: Frame = resolve_frame(brief)
        assert result.key is not None

    def test_metre_from_genre(self) -> None:
        """Metre comes from genre definition."""
        brief: Brief = make_brief(genre="invention")
        result: Frame = resolve_frame(brief)
        assert result.metre == "4/4"

    def test_voices_from_genre(self) -> None:
        """Voice count comes from genre definition."""
        brief: Brief = make_brief(genre="invention")
        result: Frame = resolve_frame(brief)
        assert result.voices == 2

    def test_upbeat_from_genre(self) -> None:
        """Upbeat comes from genre definition."""
        brief: Brief = make_brief(genre="invention")
        result: Frame = resolve_frame(brief)
        assert result.upbeat == Fraction(0)

    def test_form_from_genre(self) -> None:
        """Form comes from genre definition."""
        brief: Brief = make_brief(genre="invention")
        result: Frame = resolve_frame(brief)
        assert result.form == "through_composed"

    def test_unknown_affect_raises(self) -> None:
        """Unknown affect raises assertion error."""
        brief: Brief = Brief(affect="unknown", genre="invention", forces="keyboard", bars=16)
        with pytest.raises(AssertionError, match="Unknown affect"):
            resolve_frame(brief)


class TestIntegration:
    """Integration tests for frame resolution."""

    def test_complete_workflow_majestaet(self) -> None:
        """Complete resolution for Majestaet affect."""
        brief: Brief = make_brief(affect="Majestaet", genre="invention")
        frame: Frame = resolve_frame(brief)
        # Verify all fields are populated
        assert frame.key is not None
        assert frame.mode == "major"
        assert frame.metre == "4/4"
        assert frame.tempo in ["allegro", "moderato", "andante"]
        assert frame.voices == 2
        assert frame.upbeat == Fraction(0)
        assert frame.form == "through_composed"

    def test_complete_workflow_klage(self) -> None:
        """Complete resolution for Klage affect."""
        brief: Brief = make_brief(affect="Klage", genre="invention")
        frame: Frame = resolve_frame(brief)
        assert frame.mode == "minor"
        assert frame.tempo in ["adagio", "lento", "grave", "largo"]
        assert frame.key is not None
