"""Tests for shared/constants.py — exact_fraction utility."""
import pytest
from fractions import Fraction

from shared.constants import exact_fraction


class TestExactFraction:
    def test_exact_quarter(self) -> None:
        assert exact_fraction(0.25) == Fraction(1, 4)

    def test_exact_half(self) -> None:
        assert exact_fraction(0.5) == Fraction(1, 2)

    def test_exact_whole(self) -> None:
        assert exact_fraction(1.0) == Fraction(1)

    def test_exact_eighth(self) -> None:
        assert exact_fraction(0.125) == Fraction(1, 8)

    def test_exact_zero(self) -> None:
        assert exact_fraction(0.0) == Fraction(0)

    def test_non_exact_float_raises(self) -> None:
        with pytest.raises(AssertionError, match="denominator"):
            exact_fraction(1.0 / 3.0)

    def test_label_in_error_message(self) -> None:
        with pytest.raises(AssertionError, match="my_dur"):
            exact_fraction(1.0 / 3.0, label="my_dur")

    def test_dotted_quarter(self) -> None:
        assert exact_fraction(0.375) == Fraction(3, 8)

    def test_sixteenth(self) -> None:
        assert exact_fraction(0.0625) == Fraction(1, 16)
