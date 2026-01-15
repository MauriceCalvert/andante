"""Tests for engine.figuration.

Category A tests: verify figuration YAML loading and parse_durations utility.

Note: The figuration module has functions (apply_figuration, can_figurate, etc.)
that expect YAML patterns with 'steps' and 'durations' keys, but the actual
figurations.yaml uses a different schema (type, direction, degrees_per_beat).
This is a code-data mismatch. These tests verify only the working parts:
- parse_durations utility function
- FIGURATIONS YAML structure as loaded
"""
from fractions import Fraction

import pytest
from engine.figuration import (
    FIGURATIONS,
    parse_durations,
)


class TestParseDurations:
    """Test parse_durations function."""

    def test_parses_strings(self) -> None:
        """Parses string fractions."""
        result: tuple[Fraction, ...] = parse_durations(["1/4", "1/4", "1/2"])
        assert result == (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))

    def test_parses_numbers(self) -> None:
        """Parses numeric fractions."""
        result: tuple[Fraction, ...] = parse_durations([1, 2])
        assert result == (Fraction(1), Fraction(2))

    def test_empty_list(self) -> None:
        """Empty list returns empty tuple."""
        result: tuple[Fraction, ...] = parse_durations([])
        assert result == ()

    def test_mixed_types(self) -> None:
        """Mixed string and numeric input."""
        result: tuple[Fraction, ...] = parse_durations(["1/4", 1, "1/8"])
        assert result == (Fraction(1, 4), Fraction(1), Fraction(1, 8))


class TestFigurationsLoaded:
    """Test FIGURATIONS constant loaded from YAML."""

    def test_figurations_not_empty(self) -> None:
        """FIGURATIONS has patterns."""
        assert len(FIGURATIONS) > 0

    def test_has_scalar_patterns(self) -> None:
        """Has scalar figuration patterns."""
        assert "scalar_ascending" in FIGURATIONS
        assert "scalar_descending" in FIGURATIONS

    def test_has_arpeggio_patterns(self) -> None:
        """Has arpeggio figuration patterns."""
        assert "arpeggio_ascending" in FIGURATIONS
        assert "arpeggio_descending" in FIGURATIONS

    def test_has_tremolo_patterns(self) -> None:
        """Has tremolo figuration patterns."""
        assert "tremolo_fifth" in FIGURATIONS
        assert "tremolo_third" in FIGURATIONS

    def test_pattern_has_type(self) -> None:
        """Each pattern has type field."""
        for name, pattern in FIGURATIONS.items():
            assert "type" in pattern, f"{name} missing type"

    def test_pattern_has_degrees_per_beat(self) -> None:
        """Each pattern has degrees_per_beat field."""
        for name, pattern in FIGURATIONS.items():
            assert "degrees_per_beat" in pattern, f"{name} missing degrees_per_beat"

    def test_pattern_has_triggers(self) -> None:
        """Each pattern has triggers list."""
        for name, pattern in FIGURATIONS.items():
            assert "triggers" in pattern, f"{name} missing triggers"
            assert isinstance(pattern["triggers"], list)


class TestFigurationTypes:
    """Test figuration type values."""

    def test_valid_types(self) -> None:
        """All patterns have valid type."""
        valid_types: set[str] = {"scalar", "arpeggiated", "tremolo", "broken"}
        for name, pattern in FIGURATIONS.items():
            assert pattern["type"] in valid_types, f"{name} has invalid type: {pattern['type']}"

    def test_valid_directions(self) -> None:
        """Directional patterns have valid direction."""
        valid_directions: set[str] = {"up", "down", "round"}
        for name, pattern in FIGURATIONS.items():
            if "direction" in pattern:
                assert pattern["direction"] in valid_directions, f"{name} has invalid direction"

    def test_degrees_per_beat_positive(self) -> None:
        """degrees_per_beat is positive."""
        for name, pattern in FIGURATIONS.items():
            assert pattern["degrees_per_beat"] > 0, f"{name} has invalid degrees_per_beat"


class TestFigurationTriggers:
    """Test figuration trigger values."""

    def test_triggers_non_empty(self) -> None:
        """Each pattern has at least one trigger."""
        for name, pattern in FIGURATIONS.items():
            assert len(pattern["triggers"]) > 0, f"{name} has no triggers"

    def test_triggers_are_strings(self) -> None:
        """All triggers are strings."""
        for name, pattern in FIGURATIONS.items():
            for trigger in pattern["triggers"]:
                assert isinstance(trigger, str), f"{name} has non-string trigger"


class TestScalarFigurations:
    """Test scalar figuration patterns."""

    def test_scalar_has_direction(self) -> None:
        """Scalar patterns have direction field."""
        for name, pattern in FIGURATIONS.items():
            if pattern.get("type") == "scalar":
                assert "direction" in pattern, f"{name} missing direction"

    def test_scalar_has_span(self) -> None:
        """Scalar patterns have span field."""
        for name, pattern in FIGURATIONS.items():
            if pattern.get("type") == "scalar":
                assert "span" in pattern, f"{name} missing span"


class TestArpeggiatedFigurations:
    """Test arpeggiated figuration patterns."""

    def test_arpeggiated_has_direction(self) -> None:
        """Arpeggiated patterns have direction field."""
        for name, pattern in FIGURATIONS.items():
            if pattern.get("type") == "arpeggiated":
                assert "direction" in pattern, f"{name} missing direction"

    def test_arpeggiated_has_span(self) -> None:
        """Arpeggiated patterns have span field."""
        for name, pattern in FIGURATIONS.items():
            if pattern.get("type") == "arpeggiated":
                assert "span" in pattern, f"{name} missing span"


class TestTremoloFigurations:
    """Test tremolo figuration patterns."""

    def test_tremolo_has_interval(self) -> None:
        """Tremolo patterns have interval field."""
        for name, pattern in FIGURATIONS.items():
            if pattern.get("type") == "tremolo":
                assert "interval" in pattern, f"{name} missing interval"


class TestBrokenFigurations:
    """Test broken figuration patterns."""

    def test_broken_has_pattern(self) -> None:
        """Broken patterns have pattern list."""
        for name, pattern in FIGURATIONS.items():
            if pattern.get("type") == "broken":
                assert "pattern" in pattern, f"{name} missing pattern"
                assert isinstance(pattern["pattern"], list)
