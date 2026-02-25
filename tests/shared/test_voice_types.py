"""Tests for shared/voice_types.py — Range dataclass."""
from shared.voice_types import Range


class TestRange:
    def test_construction(self) -> None:
        r: Range = Range(low=36, high=62)
        assert r.low == 36
        assert r.high == 62

    def test_frozen(self) -> None:
        r: Range = Range(low=55, high=84)
        import pytest
        with pytest.raises(AttributeError):
            r.low = 60  # type: ignore[misc]

    def test_equality(self) -> None:
        a: Range = Range(low=55, high=84)
        b: Range = Range(low=55, high=84)
        assert a == b

    def test_inequality(self) -> None:
        a: Range = Range(low=55, high=84)
        b: Range = Range(low=36, high=62)
        assert a != b
