"""Integration tests for engine.motif_expander.

Category B orchestrator tests: verify motif cycling/trimming to budget.
Tests import only:
- engine.motif_expander (module under test)
- shared.types (Motif type)
- stdlib
"""
from fractions import Fraction

import pytest
from shared.types import Motif
from engine.motif_expander import (
    cycle_motif,
    extend_motif,
    extend_pair,
    trim_motif,
)


def make_motif(
    degrees: tuple[int, ...] = (1, 2, 3, 4),
    durations: tuple[Fraction, ...] | None = None,
) -> Motif:
    """Create a test motif."""
    if durations is None:
        durations = tuple(Fraction(1, 4) for _ in degrees)
    return Motif(degrees=degrees, durations=durations, bars=1)


class TestCycleMotif:
    """Test cycle_motif function."""

    def test_cycle_fills_budget(self) -> None:
        """Cycle fills budget exactly."""
        motif: Motif = make_motif()
        result: Motif = cycle_motif(motif, Fraction(2))
        assert sum(result.durations) == Fraction(2)

    def test_cycle_repeats_degrees(self) -> None:
        """Cycle repeats degrees to fill budget."""
        motif: Motif = make_motif((1, 2))
        result: Motif = cycle_motif(motif, Fraction(1))
        # Should repeat 1, 2, 1, 2
        assert len(result.degrees) == 4
        assert result.degrees == (1, 2, 1, 2)

    def test_cycle_partial_last_note(self) -> None:
        """Cycle truncates last note if needed."""
        motif: Motif = make_motif((1, 2), (Fraction(1, 4), Fraction(1, 4)))
        result: Motif = cycle_motif(motif, Fraction(3, 8))
        # 1/4 + 1/8 (truncated 1/4) = 3/8
        assert sum(result.durations) == Fraction(3, 8)

    def test_cycle_exact_multiple(self) -> None:
        """Cycle with exact multiple budget."""
        motif: Motif = make_motif((1, 2), (Fraction(1, 4), Fraction(1, 4)))
        result: Motif = cycle_motif(motif, Fraction(1))
        assert sum(result.durations) == Fraction(1)
        assert len(result.degrees) == 4

    def test_cycle_preserves_bars(self) -> None:
        """Cycle preserves bars attribute."""
        motif: Motif = make_motif()
        motif = Motif(degrees=motif.degrees, durations=motif.durations, bars=2)
        result: Motif = cycle_motif(motif, Fraction(4))
        assert result.bars == 2


class TestTrimMotif:
    """Test trim_motif function."""

    def test_trim_within_budget(self) -> None:
        """Trim to budget shorter than motif."""
        motif: Motif = make_motif((1, 2, 3, 4))
        result: Motif = trim_motif(motif, Fraction(1, 2))
        assert sum(result.durations) == Fraction(1, 2)
        assert len(result.degrees) == 2

    def test_trim_partial_note(self) -> None:
        """Trim truncates last note if needed."""
        motif: Motif = make_motif((1, 2), (Fraction(1, 4), Fraction(1, 2)))
        result: Motif = trim_motif(motif, Fraction(1, 2))
        # 1/4 + 1/4 (truncated from 1/2) = 1/2
        assert sum(result.durations) == Fraction(1, 2)
        assert len(result.degrees) == 2

    def test_trim_exact_length(self) -> None:
        """Trim with exact budget returns all notes."""
        motif: Motif = make_motif((1, 2), (Fraction(1, 4), Fraction(1, 4)))
        result: Motif = trim_motif(motif, Fraction(1, 2))
        assert result.degrees == (1, 2)
        assert result.durations == (Fraction(1, 4), Fraction(1, 4))

    def test_trim_zero_budget(self) -> None:
        """Trim with zero budget returns empty."""
        motif: Motif = make_motif()
        result: Motif = trim_motif(motif, Fraction(0))
        assert len(result.degrees) == 0
        assert sum(result.durations) == Fraction(0)

    def test_trim_preserves_bars(self) -> None:
        """Trim preserves bars attribute."""
        motif: Motif = Motif(degrees=(1, 2, 3, 4), durations=(Fraction(1, 4),) * 4, bars=2)
        result: Motif = trim_motif(motif, Fraction(1, 2))
        assert result.bars == 2


class TestExtendMotif:
    """Test extend_motif function."""

    def test_extend_shorter_motif_cycles(self) -> None:
        """Short motif is cycled."""
        motif: Motif = make_motif((1, 2), (Fraction(1, 4), Fraction(1, 4)))
        result: Motif = extend_motif(motif, Fraction(2))
        assert sum(result.durations) == Fraction(2)
        assert len(result.degrees) > 2

    def test_extend_longer_motif_trims(self) -> None:
        """Long motif is trimmed."""
        motif: Motif = make_motif((1, 2, 3, 4), (Fraction(1, 2),) * 4)
        result: Motif = extend_motif(motif, Fraction(1))
        assert sum(result.durations) == Fraction(1)
        assert len(result.degrees) == 2

    def test_extend_exact_length(self) -> None:
        """Exact length motif unchanged."""
        motif: Motif = make_motif((1, 2), (Fraction(1, 4), Fraction(1, 4)))
        result: Motif = extend_motif(motif, Fraction(1, 2))
        assert result.degrees == motif.degrees
        assert result.durations == motif.durations

    def test_extend_fills_budget(self) -> None:
        """Extend always fills budget exactly."""
        motif: Motif = make_motif()
        for budget in [Fraction(1, 2), Fraction(1), Fraction(3, 2), Fraction(4)]:
            result: Motif = extend_motif(motif, budget)
            assert sum(result.durations) == budget


class TestExtendPair:
    """Test extend_pair function."""

    def test_extend_both_motifs(self) -> None:
        """Extends both subject and counter-subject."""
        subject: Motif = make_motif((1, 2, 3, 4))
        cs: Motif = make_motif((5, 4, 3, 2))
        subj_result, cs_result = extend_pair(subject, cs, Fraction(2))
        assert sum(subj_result.durations) == Fraction(2)
        assert sum(cs_result.durations) == Fraction(2)

    def test_extend_pair_different_source_lengths(self) -> None:
        """Handles different source lengths."""
        subject: Motif = make_motif((1, 2), (Fraction(1, 4), Fraction(1, 4)))
        cs: Motif = make_motif((5, 4, 3), (Fraction(1, 8), Fraction(1, 8), Fraction(1, 4)))
        subj_result, cs_result = extend_pair(subject, cs, Fraction(1))
        assert sum(subj_result.durations) == Fraction(1)
        assert sum(cs_result.durations) == Fraction(1)

    def test_extend_pair_preserves_content(self) -> None:
        """Original degrees are preserved (repeated/trimmed)."""
        subject: Motif = make_motif((1, 2))
        cs: Motif = make_motif((5, 6))
        subj_result, cs_result = extend_pair(subject, cs, Fraction(1))
        # Should cycle degrees
        for d in subj_result.degrees:
            assert d in (1, 2)
        for d in cs_result.degrees:
            assert d in (5, 6)


class TestMotifEdgeCases:
    """Test edge cases for motif operations."""

    def test_single_note_motif_cycle(self) -> None:
        """Single note motif cycles correctly."""
        motif: Motif = make_motif((1,), (Fraction(1, 4),))
        result: Motif = cycle_motif(motif, Fraction(1))
        assert sum(result.durations) == Fraction(1)
        assert all(d == 1 for d in result.degrees)

    def test_very_short_budget(self) -> None:
        """Very short budget handled."""
        motif: Motif = make_motif((1, 2, 3, 4))
        result: Motif = extend_motif(motif, Fraction(1, 16))
        assert sum(result.durations) == Fraction(1, 16)

    def test_large_budget(self) -> None:
        """Large budget handled."""
        motif: Motif = make_motif((1, 2), (Fraction(1, 4), Fraction(1, 4)))
        result: Motif = extend_motif(motif, Fraction(16))
        assert sum(result.durations) == Fraction(16)

    def test_dotted_rhythm_motif(self) -> None:
        """Dotted rhythm motif handled."""
        motif: Motif = make_motif((1, 2), (Fraction(3, 8), Fraction(1, 8)))
        result: Motif = extend_motif(motif, Fraction(2))
        assert sum(result.durations) == Fraction(2)


class TestMotifDurations:
    """Test duration handling in motif operations."""

    def test_mixed_durations_cycle(self) -> None:
        """Mixed durations cycle correctly."""
        motif: Motif = make_motif((1, 2, 3), (Fraction(1, 4), Fraction(1, 8), Fraction(1, 8)))
        result: Motif = cycle_motif(motif, Fraction(1))
        assert sum(result.durations) == Fraction(1)

    def test_duration_count_matches_degrees(self) -> None:
        """Duration count always matches degree count."""
        motif: Motif = make_motif()
        for budget in [Fraction(1, 2), Fraction(1), Fraction(2)]:
            result: Motif = extend_motif(motif, budget)
            assert len(result.degrees) == len(result.durations)
