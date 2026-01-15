"""Tests for shared.schema_validator.

Validates that all data/*.yaml files have consistent cross-references.
"""
import pytest

from shared.schema_validator import validate_schema


class TestSchemaValidation:
    """Test schema validation."""

    def test_all_references_valid(self) -> None:
        """All cross-file references resolve to defined types."""
        valid, errors = validate_schema()
        if not valid:
            pytest.fail(f"Schema validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    def test_returns_tuple(self) -> None:
        """validate_schema returns (bool, list) tuple."""
        result = validate_schema()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)
