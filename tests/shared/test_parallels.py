"""Tests for shared.parallels.

Tests parallel fifth and octave detection.
"""
import pytest

from shared.parallels import is_parallel_fifth, is_parallel_motion, is_parallel_octave


class TestIsParallelMotion:
    """Test is_parallel_motion function."""

    def test_parallel_fifths_ascending(self) -> None:
        """Detects ascending parallel fifths."""
        assert is_parallel_motion(67, 60, 69, 62, 7) is True

    def test_parallel_fifths_descending(self) -> None:
        """Detects descending parallel fifths."""
        assert is_parallel_motion(69, 62, 67, 60, 7) is True

    def test_parallel_octaves_ascending(self) -> None:
        """Detects ascending parallel octaves."""
        assert is_parallel_motion(72, 60, 74, 62, 0) is True

    def test_parallel_octaves_descending(self) -> None:
        """Detects descending parallel octaves."""
        assert is_parallel_motion(74, 62, 72, 60, 0) is True

    def test_contrary_motion_not_parallel(self) -> None:
        """Contrary motion is not parallel."""
        assert is_parallel_motion(67, 60, 69, 58, 7) is False

    def test_oblique_upper_stationary(self) -> None:
        """Upper voice stationary is not parallel."""
        assert is_parallel_motion(67, 60, 67, 60, 7) is False

    def test_oblique_lower_stationary(self) -> None:
        """Lower voice stationary is not parallel."""
        assert is_parallel_motion(67, 60, 69, 60, 7) is False

    def test_different_intervals_not_parallel(self) -> None:
        """Different intervals is not parallel."""
        assert is_parallel_motion(67, 60, 70, 62, 7) is False

    def test_first_interval_wrong(self) -> None:
        """Wrong interval at first position is not parallel."""
        assert is_parallel_motion(68, 60, 69, 62, 7) is False


class TestIsParallelFifth:
    """Test is_parallel_fifth function."""

    def test_parallel_fifths_c_g_to_d_a(self) -> None:
        """C-G to D-A is parallel fifths."""
        assert is_parallel_fifth(67, 60, 69, 62) is True

    def test_parallel_fifths_across_octave(self) -> None:
        """Parallel fifths work across octave boundaries."""
        assert is_parallel_fifth(79, 72, 81, 74) is True

    def test_not_parallel_fifths_contrary(self) -> None:
        """Contrary motion fifths is not parallel."""
        assert is_parallel_fifth(67, 60, 65, 62) is False

    def test_not_parallel_fifths_oblique(self) -> None:
        """Oblique motion is not parallel fifths."""
        assert is_parallel_fifth(67, 60, 67, 62) is False

    def test_not_fifths_at_all(self) -> None:
        """Non-fifth intervals don't count."""
        assert is_parallel_fifth(64, 60, 66, 62) is False


class TestIsParallelOctave:
    """Test is_parallel_octave function."""

    def test_parallel_octaves_ascending(self) -> None:
        """Ascending parallel octaves detected."""
        assert is_parallel_octave(72, 60, 74, 62) is True

    def test_parallel_unisons_ascending(self) -> None:
        """Parallel unisons detected."""
        assert is_parallel_octave(60, 60, 62, 62) is True

    def test_parallel_octaves_descending(self) -> None:
        """Descending parallel octaves detected."""
        assert is_parallel_octave(74, 62, 72, 60) is True

    def test_not_parallel_octaves_contrary(self) -> None:
        """Contrary motion octaves is not parallel."""
        assert is_parallel_octave(72, 60, 74, 58) is False

    def test_not_parallel_octaves_oblique(self) -> None:
        """Oblique motion is not parallel octaves."""
        assert is_parallel_octave(72, 60, 72, 62) is False

    def test_not_octaves_at_all(self) -> None:
        """Non-octave intervals don't count."""
        assert is_parallel_octave(67, 60, 69, 62) is False
