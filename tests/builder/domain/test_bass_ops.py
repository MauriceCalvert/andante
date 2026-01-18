"""Tests for builder.domain.bass_ops.

Tests validate against known musical truths, not implementation details.
"""
import pytest
from fractions import Fraction

from builder.domain.bass_ops import (
    compute_degree,
    compute_harmonic_bass,
    compute_diatonic_bass,
)
from builder.types import Notes


# Standard Roman numeral to degree mapping
TONAL_ROOTS: dict[str, int] = {
    "I": 1,
    "ii": 2,
    "iii": 3,
    "IV": 4,
    "V": 5,
    "vi": 6,
    "vii": 7,
}


class TestComputeDegree:
    """Tests for compute_degree."""

    def test_tonic_is_degree_1(self) -> None:
        """I maps to degree 1."""
        assert compute_degree("I", TONAL_ROOTS) == 1

    def test_dominant_is_degree_5(self) -> None:
        """V maps to degree 5."""
        assert compute_degree("V", TONAL_ROOTS) == 5

    def test_subdominant_is_degree_4(self) -> None:
        """IV maps to degree 4."""
        assert compute_degree("IV", TONAL_ROOTS) == 4

    def test_supertonic_is_degree_2(self) -> None:
        """ii maps to degree 2."""
        assert compute_degree("ii", TONAL_ROOTS) == 2

    def test_mediant_is_degree_3(self) -> None:
        """iii maps to degree 3."""
        assert compute_degree("iii", TONAL_ROOTS) == 3

    def test_submediant_is_degree_6(self) -> None:
        """vi maps to degree 6."""
        assert compute_degree("vi", TONAL_ROOTS) == 6

    def test_leading_tone_is_degree_7(self) -> None:
        """vii maps to degree 7."""
        assert compute_degree("vii", TONAL_ROOTS) == 7


class TestComputeHarmonicBass:
    """Tests for compute_harmonic_bass."""

    def test_root_only(self) -> None:
        """Single root note on degree 1."""
        result: Notes = compute_harmonic_bass(
            root=1,
            intervals=(0,),
            durations=(Fraction(1, 4),),
        )
        assert result.pitches == (1,)
        assert result.durations == (Fraction(1, 4),)

    def test_root_and_fifth(self) -> None:
        """Root and fifth on degree 1 (I chord)."""
        result: Notes = compute_harmonic_bass(
            root=1,
            intervals=(0, 4),
            durations=(Fraction(1, 8), Fraction(1, 8)),
        )
        # Root 1, fifth = (1-1+4)%7 + 1 = 5
        assert result.pitches == (1, 5)
        assert result.durations == (Fraction(1, 8), Fraction(1, 8))

    def test_dominant_root_and_fifth(self) -> None:
        """Root and fifth on degree 5 (V chord)."""
        result: Notes = compute_harmonic_bass(
            root=5,
            intervals=(0, 4),
            durations=(Fraction(1, 4), Fraction(1, 4)),
        )
        # Root 5, fifth = (5-1+4)%7 + 1 = 8%7 + 1 = 2
        assert result.pitches == (5, 2)
        assert result.durations == (Fraction(1, 4), Fraction(1, 4))

    def test_triad_intervals(self) -> None:
        """Full triad on tonic."""
        result: Notes = compute_harmonic_bass(
            root=1,
            intervals=(0, 2, 4),
            durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
        )
        # Root 1, third = 3, fifth = 5
        assert result.pitches == (1, 3, 5)

    def test_wraparound_degrees(self) -> None:
        """Intervals that wrap around the octave."""
        result: Notes = compute_harmonic_bass(
            root=6,
            intervals=(0, 4),
            durations=(Fraction(1, 4), Fraction(1, 4)),
        )
        # Root 6, fifth = (6-1+4)%7 + 1 = 9%7 + 1 = 3
        assert result.pitches == (6, 3)


class TestComputeDiatonicBass:
    """Tests for compute_diatonic_bass."""

    def test_degree_1_octave_3(self) -> None:
        """Degree 1 in octave 3 maps to diatonic 21."""
        notes: Notes = Notes(pitches=(1,), durations=(Fraction(1, 4),))
        result: Notes = compute_diatonic_bass(notes, base_octave=3)
        # diatonic = 3*7 + (1-1)%7 = 21
        assert result.pitches == (21,)
        assert result.durations == notes.durations

    def test_degree_5_octave_3(self) -> None:
        """Degree 5 in octave 3 maps to diatonic 25."""
        notes: Notes = Notes(pitches=(5,), durations=(Fraction(1, 4),))
        result: Notes = compute_diatonic_bass(notes, base_octave=3)
        # diatonic = 3*7 + (5-1)%7 = 21 + 4 = 25
        assert result.pitches == (25,)

    def test_multiple_degrees(self) -> None:
        """Multiple degrees convert correctly."""
        notes: Notes = Notes(
            pitches=(1, 3, 5),
            durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
        )
        result: Notes = compute_diatonic_bass(notes, base_octave=3)
        # 1 -> 21, 3 -> 23, 5 -> 25
        assert result.pitches == (21, 23, 25)

    def test_octave_4_bass(self) -> None:
        """Octave 4 produces higher diatonic values."""
        notes: Notes = Notes(pitches=(1,), durations=(Fraction(1, 4),))
        result: Notes = compute_diatonic_bass(notes, base_octave=4)
        # diatonic = 4*7 + 0 = 28
        assert result.pitches == (28,)

    def test_all_degrees_in_octave(self) -> None:
        """All degrees 1-7 convert correctly in octave 3."""
        notes: Notes = Notes(
            pitches=(1, 2, 3, 4, 5, 6, 7),
            durations=tuple(Fraction(1, 8) for _ in range(7)),
        )
        result: Notes = compute_diatonic_bass(notes, base_octave=3)
        # Degrees 1-7 map to diatonic 21-27
        assert result.pitches == (21, 22, 23, 24, 25, 26, 27)

    def test_durations_preserved(self) -> None:
        """Durations are preserved during conversion."""
        durations: tuple[Fraction, ...] = (
            Fraction(1, 4),
            Fraction(1, 8),
            Fraction(3, 16),
        )
        notes: Notes = Notes(pitches=(1, 3, 5), durations=durations)
        result: Notes = compute_diatonic_bass(notes, base_octave=3)
        assert result.durations == durations
