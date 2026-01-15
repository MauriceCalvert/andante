"""Tests for shared.constraint_validator.

Validates semantic constraints on Brief and Frame combinations.
"""
import pytest

from shared.constraint_validator import (
    validate_brief,
    validate_frame,
    validate_plan_structure,
)


class TestValidateBrief:
    """Test Brief validation."""

    def test_valid_minuet_brief(self) -> None:
        """Valid minuet brief passes."""
        valid, errors = validate_brief("minuet", "Majestaet", 16)
        assert valid is True
        assert errors == []

    def test_valid_invention_brief(self) -> None:
        """Valid invention brief passes."""
        valid, errors = validate_brief("invention", "Majestaet", 16)
        assert valid is True
        assert errors == []

    def test_valid_fantasia_brief(self) -> None:
        """Valid fantasia brief passes."""
        valid, errors = validate_brief("fantasia", "Majestaet", 64)
        assert valid is True
        assert errors == []

    def test_insufficient_bars_fails(self) -> None:
        """Too few bars fails validation."""
        valid, errors = validate_brief("minuet", "Majestaet", 4)
        assert valid is False
        assert any("at least 8 bars" in e for e in errors)


class TestValidateFrameGenre:
    """Test Frame validation for genre constraints."""

    def test_minuet_valid_metre(self) -> None:
        """Minuet in 3/4 passes."""
        valid, errors = validate_frame(
            genre="minuet",
            affect="Majestaet",
            key="C",
            mode="major",
            metre="3/4",
            tempo="allegro",
            voices=2,
            form="binary",
        )
        assert valid is True

    def test_minuet_invalid_metre(self) -> None:
        """Minuet in 4/4 fails."""
        valid, errors = validate_frame(
            genre="minuet",
            affect="Majestaet",
            key="C",
            mode="major",
            metre="4/4",
            tempo="allegro",
            voices=2,
            form="binary",
        )
        assert valid is False
        assert any("3/4" in e for e in errors)

    def test_minuet_invalid_voices(self) -> None:
        """Minuet with wrong voice count fails."""
        valid, errors = validate_frame(
            genre="minuet",
            affect="Majestaet",
            key="C",
            mode="major",
            metre="3/4",
            tempo="allegro",
            voices=4,
            form="binary",
        )
        assert valid is False
        assert any("2 voices" in e for e in errors)

    def test_chorale_requires_four_voices(self) -> None:
        """Chorale requires 4 voices."""
        valid, errors = validate_frame(
            genre="chorale",
            affect="Majestaet",
            key="C",
            mode="major",
            metre="4/4",
            tempo="andante",
            voices=2,
            form="through_composed",
        )
        assert valid is False
        assert any("4 voices" in e for e in errors)


class TestValidateFrameAffect:
    """Test Frame validation for affect constraints."""

    def test_furioso_requires_minor(self) -> None:
        """Zorn affect requires minor mode."""
        valid, errors = validate_frame(
            genre="invention",
            affect="Zorn",
            key="C",
            mode="major",
            metre="4/4",
            tempo="presto",
            voices=2,
            form="through_composed",
        )
        assert valid is False
        assert any("minor" in e.lower() for e in errors)

    def test_furioso_requires_fast_tempo(self) -> None:
        """Zorn affect requires fast tempo."""
        valid, errors = validate_frame(
            genre="invention",
            affect="Zorn",
            key="C",
            mode="minor",
            metre="4/4",
            tempo="adagio",
            voices=2,
            form="through_composed",
        )
        assert valid is False
        assert any("tempo" in e.lower() for e in errors)

    def test_dolore_requires_minor(self) -> None:
        """Klage affect requires minor mode."""
        valid, errors = validate_frame(
            genre="invention",
            affect="Klage",
            key="C",
            mode="major",
            metre="4/4",
            tempo="adagio",
            voices=2,
            form="through_composed",
        )
        assert valid is False
        assert any("minor" in e.lower() for e in errors)

    def test_dolore_requires_slow_tempo(self) -> None:
        """Klage affect requires slow tempo."""
        valid, errors = validate_frame(
            genre="invention",
            affect="Klage",
            key="C",
            mode="minor",
            metre="4/4",
            tempo="presto",
            voices=2,
            form="through_composed",
        )
        assert valid is False
        assert any("tempo" in e.lower() for e in errors)


class TestValidatePlanStructure:
    """Test structure validation."""

    def test_last_section_authentic_cadence(self) -> None:
        """Last section must have authentic cadence."""
        sections = [
            {"label": "A", "final_cadence": "half"},
            {"label": "B", "final_cadence": "half"},
        ]
        valid, errors = validate_plan_structure(sections, "binary", 4, 16)
        assert valid is False
        assert any("authentic" in e.lower() for e in errors)

    def test_valid_structure_passes(self) -> None:
        """Valid structure passes."""
        sections = [
            {"label": "A", "final_cadence": "half"},
            {"label": "B", "final_cadence": "authentic"},
        ]
        valid, errors = validate_plan_structure(sections, "binary", 4, 16)
        assert valid is True


class TestMultipleErrors:
    """Test that validator collects multiple errors."""

    def test_collects_multiple_errors(self) -> None:
        """Validator returns all errors, not just first."""
        valid, errors = validate_frame(
            genre="minuet",
            affect="Zorn",
            key="C",
            mode="major",
            metre="4/4",
            tempo="adagio",
            voices=4,
            form="binary",
        )
        assert valid is False
        assert len(errors) >= 2


class TestReturnTypes:
    """Test return type consistency."""

    def test_validate_brief_returns_tuple(self) -> None:
        """validate_brief returns (bool, list) tuple."""
        result = validate_brief("minuet", "Majestaet", 16)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)

    def test_validate_frame_returns_tuple(self) -> None:
        """validate_frame returns (bool, list) tuple."""
        result = validate_frame(
            genre="minuet",
            affect="Majestaet",
            key="C",
            mode="major",
            metre="3/4",
            tempo="allegro",
            voices=2,
            form="binary",
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)
