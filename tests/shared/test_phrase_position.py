"""Tests for phrase position classification."""
import pytest

from shared.phrase_position import phrase_zone


class TestPhraseZone:
    def test_single_bar(self) -> None:
        """Single bar phrase → cadential."""
        assert phrase_zone(phrase_bar=1, total_bars=1) == "cadential"

    def test_two_bars(self) -> None:
        """Two bar phrase: bar 1 opening, bar 2 cadential."""
        assert phrase_zone(phrase_bar=1, total_bars=2) == "opening"
        assert phrase_zone(phrase_bar=2, total_bars=2) == "cadential"

    def test_four_bars(self) -> None:
        """Four bar phrase: bar 1 opening, bars 2-3 middle, bar 4 cadential."""
        assert phrase_zone(phrase_bar=1, total_bars=4) == "opening"
        assert phrase_zone(phrase_bar=2, total_bars=4) == "middle"
        assert phrase_zone(phrase_bar=3, total_bars=4) == "middle"
        assert phrase_zone(phrase_bar=4, total_bars=4) == "cadential"

    def test_eight_bars(self) -> None:
        """Eight bar phrase: bars 1-2 opening, 3-6 middle, 7-8 cadential."""
        # Opening: floor(8 * 0.25) = 2 → bars 1-2
        assert phrase_zone(phrase_bar=1, total_bars=8) == "opening"
        assert phrase_zone(phrase_bar=2, total_bars=8) == "opening"

        # Middle: bars 3-6
        assert phrase_zone(phrase_bar=3, total_bars=8) == "middle"
        assert phrase_zone(phrase_bar=4, total_bars=8) == "middle"
        assert phrase_zone(phrase_bar=5, total_bars=8) == "middle"
        assert phrase_zone(phrase_bar=6, total_bars=8) == "middle"

        # Cadential: int(8 * 0.75) + 1 = 7 → bars 7-8
        assert phrase_zone(phrase_bar=7, total_bars=8) == "cadential"
        assert phrase_zone(phrase_bar=8, total_bars=8) == "cadential"

    def test_three_bars(self) -> None:
        """Three bar phrase: bar 1 opening, bar 2 middle, bar 3 cadential."""
        # Opening: floor(3 * 0.25) = 0 → max(1, 0) = 1 → bar 1
        assert phrase_zone(phrase_bar=1, total_bars=3) == "opening"

        # Cadential: int(3 * 0.75) + 1 = 3 → bar 3
        assert phrase_zone(phrase_bar=3, total_bars=3) == "cadential"

        # Middle: bar 2
        assert phrase_zone(phrase_bar=2, total_bars=3) == "middle"

    def test_six_bars(self) -> None:
        """Six bar phrase."""
        # Opening: floor(6 * 0.25) = 1 → bar 1
        assert phrase_zone(phrase_bar=1, total_bars=6) == "opening"

        # Cadential: int(6 * 0.75) + 1 = 5 → bars 5-6
        assert phrase_zone(phrase_bar=5, total_bars=6) == "cadential"
        assert phrase_zone(phrase_bar=6, total_bars=6) == "cadential"

        # Middle: bars 2-4
        assert phrase_zone(phrase_bar=2, total_bars=6) == "middle"
        assert phrase_zone(phrase_bar=3, total_bars=6) == "middle"
        assert phrase_zone(phrase_bar=4, total_bars=6) == "middle"

    def test_invalid_inputs_raise(self) -> None:
        """Invalid inputs raise assertion."""
        with pytest.raises(AssertionError):
            phrase_zone(phrase_bar=0, total_bars=4)

        with pytest.raises(AssertionError):
            phrase_zone(phrase_bar=1, total_bars=0)
