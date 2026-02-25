"""Tests for shared/yaml_parsing.py — YAML field parsers."""
import pytest

from shared.yaml_parsing import (
    parse_signed_degree,
    parse_signed_degrees,
    parse_typical_keys,
)


# =========================================================================
# parse_signed_degree
# =========================================================================


class TestParseSignedDegree:
    def test_first_degree_unsigned_int(self) -> None:
        degree, direction = parse_signed_degree(3, is_first=True)
        assert degree == 3
        assert direction is None

    def test_first_degree_unsigned_str(self) -> None:
        degree, direction = parse_signed_degree("5", is_first=True)
        assert degree == 5
        assert direction is None

    def test_subsequent_positive(self) -> None:
        degree, direction = parse_signed_degree("+2", is_first=False)
        assert degree == 2
        assert direction == "up"

    def test_subsequent_negative(self) -> None:
        degree, direction = parse_signed_degree("-7", is_first=False)
        assert degree == 7
        assert direction == "down"

    def test_subsequent_unsigned_means_same(self) -> None:
        degree, direction = parse_signed_degree("4", is_first=False)
        assert degree == 4
        assert direction == "same"

    def test_subsequent_int_means_same(self) -> None:
        degree, direction = parse_signed_degree(6, is_first=False)
        assert degree == 6
        assert direction == "same"

    def test_float_input(self) -> None:
        degree, direction = parse_signed_degree(3.0, is_first=True)
        assert degree == 3
        assert direction is None

    def test_negative_float_input(self) -> None:
        degree, direction = parse_signed_degree(-5.0, is_first=True)
        assert degree == 5
        assert direction is None

    def test_empty_string(self) -> None:
        degree, direction = parse_signed_degree("", is_first=True)
        assert degree == 1
        assert direction is None

    def test_first_positive_prefix_ignored(self) -> None:
        degree, direction = parse_signed_degree("+3", is_first=True)
        assert degree == 3
        assert direction is None

    def test_first_negative_prefix_ignored(self) -> None:
        degree, direction = parse_signed_degree("-3", is_first=True)
        assert degree == 3
        assert direction is None


# =========================================================================
# parse_signed_degrees
# =========================================================================


class TestParseSignedDegrees:
    def test_simple_sequence(self) -> None:
        degrees, directions = parse_signed_degrees([1, "+3", "-5", "2"])
        assert degrees == (1, 3, 5, 2)
        assert directions == (None, "up", "down", "same")

    def test_single_degree(self) -> None:
        degrees, directions = parse_signed_degrees([5])
        assert degrees == (5,)
        assert directions == (None,)

    def test_empty_list(self) -> None:
        degrees, directions = parse_signed_degrees([])
        assert degrees == ()
        assert directions == ()

    def test_all_unsigned(self) -> None:
        degrees, directions = parse_signed_degrees([1, 2, 3])
        assert degrees == (1, 2, 3)
        assert directions == (None, "same", "same")


# =========================================================================
# parse_typical_keys
# =========================================================================


class TestParseTypicalKeys:
    def test_none_input(self) -> None:
        assert parse_typical_keys(None) is None

    def test_two_keys(self) -> None:
        result = parse_typical_keys("ii -> I")
        assert result is not None
        assert "ii" in result
        assert "I" in result

    def test_three_keys_with_parens(self) -> None:
        result = parse_typical_keys("IV -> V (-> vi)")
        assert result is not None
        assert "IV" in result
        assert "V" in result
        assert "vi" in result

    def test_no_match(self) -> None:
        result = parse_typical_keys("no keys here 123")
        assert result is None
