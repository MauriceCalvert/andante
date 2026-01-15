"""100% coverage tests for engine.sequence.

Tests import only:
- engine.sequence (module under test)
- shared (pitch, timed_material)
- stdlib

Sequences are patterns repeated at shifted pitch levels with variation.
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Rest

from engine.sequence import (
    EXTENDED_VARIATIONS,
    VARIATIONS,
    Variation,
    build_sequence,
    build_sequence_break,
)


class TestVariationDataclass:
    """Test Variation dataclass."""

    def test_variation_defaults(self) -> None:
        """Default variation has no invert or reverse."""
        v: Variation = Variation("test")
        assert v.name == "test"
        assert v.invert is False
        assert v.reverse is False

    def test_variation_with_invert(self) -> None:
        """Variation can have invert flag."""
        v: Variation = Variation("inv", invert=True)
        assert v.invert is True
        assert v.reverse is False

    def test_variation_with_reverse(self) -> None:
        """Variation can have reverse flag."""
        v: Variation = Variation("rev", reverse=True)
        assert v.invert is False
        assert v.reverse is True

    def test_variation_with_both(self) -> None:
        """Variation can have both flags."""
        v: Variation = Variation("both", invert=True, reverse=True)
        assert v.invert is True
        assert v.reverse is True

    def test_variation_is_frozen(self) -> None:
        """Variation is immutable."""
        v: Variation = Variation("test")
        with pytest.raises(AttributeError):
            v.name = "other"  # type: ignore


class TestVariationsConstant:
    """Test VARIATIONS tuple."""

    def test_four_variations(self) -> None:
        """VARIATIONS has 4 entries."""
        assert len(VARIATIONS) == 4

    def test_none_variation_first(self) -> None:
        """First variation is 'none' with no transforms."""
        v: Variation = VARIATIONS[0]
        assert v.name == "none"
        assert v.invert is False
        assert v.reverse is False

    def test_invert_variation(self) -> None:
        """Second variation is 'invert'."""
        v: Variation = VARIATIONS[1]
        assert v.name == "invert"
        assert v.invert is True
        assert v.reverse is False

    def test_retrograde_variation(self) -> None:
        """Third variation is 'retrograde'."""
        v: Variation = VARIATIONS[2]
        assert v.name == "retrograde"
        assert v.invert is False
        assert v.reverse is True

    def test_inv_retro_variation(self) -> None:
        """Fourth variation is combined invert+retrograde."""
        v: Variation = VARIATIONS[3]
        assert v.name == "inv_retro"
        assert v.invert is True
        assert v.reverse is True


class TestExtendedVariationsConstant:
    """Test EXTENDED_VARIATIONS tuple."""

    def test_extends_variations(self) -> None:
        """EXTENDED_VARIATIONS includes all VARIATIONS."""
        for i, v in enumerate(VARIATIONS):
            assert EXTENDED_VARIATIONS[i] == v

    def test_has_additional_variations(self) -> None:
        """EXTENDED_VARIATIONS has more than VARIATIONS."""
        assert len(EXTENDED_VARIATIONS) > len(VARIATIONS)

    def test_includes_shift_variations(self) -> None:
        """Extended variations include shift variants."""
        names: list[str] = [v.name for v in EXTENDED_VARIATIONS]
        assert "none_shift1" in names
        assert "invert_shift" in names
        assert "retro_shift" in names


class TestBuildSequence:
    """Test build_sequence function."""

    def test_returns_tuple_pair(self) -> None:
        """Returns tuple of (pitches, durations)."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = build_sequence(pitches, durations, Fraction(1))
        assert isinstance(result_p, tuple)
        assert isinstance(result_d, tuple)

    def test_budget_exactly_filled(self) -> None:
        """Total duration equals budget."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(3))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        budget: Fraction = Fraction(2)
        result_p, result_d = build_sequence(pitches, durations, budget)
        assert sum(result_d) == budget

    def test_repeats_subject(self) -> None:
        """Sequence repeats subject material."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        result_p, result_d = build_sequence(pitches, durations, Fraction(2))
        # With budget=2 and subject_dur=1/2, we get 4+ notes
        assert len(result_p) >= 4

    def test_step_shifts_degrees(self) -> None:
        """Each repetition shifts by step."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result_p, result_d = build_sequence(
            pitches, durations, Fraction(1), step=-1, vary=False
        )
        # First note at degree 1, second at degree 1-1=0 wrapped to 7
        degrees: list[int] = [p.degree for p in result_p]
        # With vary=False, no variation applied
        assert degrees[0] != degrees[1] or len(degrees) == 1

    def test_vary_false_no_variation(self) -> None:
        """vary=False uses only 'none' variation."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 8), Fraction(1, 8))
        result_p, result_d = build_sequence(
            pitches, durations, Fraction(1), vary=False, step=0
        )
        # With step=0 and no variation, all repetitions have same pattern
        # Degrees should repeat
        degrees: list[int] = [p.degree for p in result_p]
        # Check pairs match
        if len(degrees) >= 4:
            assert degrees[0] == degrees[2]
            assert degrees[1] == degrees[3]

    def test_vary_true_applies_variations(self) -> None:
        """vary=True applies different variations to repetitions."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 8), Fraction(1, 8))
        # Use step=0 to isolate variation effect
        result_p, result_d = build_sequence(
            pitches, durations, Fraction(1), vary=True, step=0, phrase_seed=0
        )
        # With 4 variations cycling, there should be some variety
        degrees: list[int] = [p.degree for p in result_p]
        # At least 2 unique degree patterns
        assert len(set(degrees)) >= 2

    def test_phrase_seed_affects_variation(self) -> None:
        """Different phrase_seed produces different variation order."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(3))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        r1_p, _ = build_sequence(pitches, durations, Fraction(2), phrase_seed=0)
        r2_p, _ = build_sequence(pitches, durations, Fraction(2), phrase_seed=1)
        # Different seeds should produce different results
        d1: list[int] = [p.degree for p in r1_p]
        d2: list[int] = [p.degree for p in r2_p]
        assert d1 != d2

    def test_phrase_seed_affects_start_offset(self) -> None:
        """phrase_seed offsets the starting position."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        # Same parameters except phrase_seed
        r1_p, _ = build_sequence(
            pitches, durations, Fraction(1), phrase_seed=0, vary=False
        )
        r2_p, _ = build_sequence(
            pitches, durations, Fraction(1), phrase_seed=1, vary=False
        )
        # First notes should differ due to start_offset
        assert r1_p[0].degree != r2_p[0].degree

    def test_avoid_leading_tone_converts_7_to_6(self) -> None:
        """avoid_leading_tone replaces degree 7 with 6."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(6),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        # Shift +1 would make 6 -> 7
        result_p, _ = build_sequence(
            pitches, durations, Fraction(1), start=1, step=0,
            avoid_leading_tone=True, vary=False
        )
        # All notes should be 6 (7 converted to 6)
        for p in result_p:
            assert p.degree != 7

    def test_avoid_leading_tone_false_allows_7(self) -> None:
        """Without avoid_leading_tone, degree 7 is allowed."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(6),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        # Shift +1 makes 6 -> 7
        result_p, _ = build_sequence(
            pitches, durations, Fraction(1, 4), start=1, step=0,
            avoid_leading_tone=False, vary=False
        )
        # Should have degree 7
        assert any(p.degree == 7 for p in result_p)

    def test_rests_preserved(self) -> None:
        """Rests in subject are preserved in sequence."""
        pitches: tuple[FloatingNote | Rest, ...] = (FloatingNote(1), Rest())
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        result_p, _ = build_sequence(pitches, durations, Fraction(1), vary=False)
        # Should have rests
        rest_count: int = sum(1 for p in result_p if isinstance(p, Rest))
        assert rest_count > 0

    def test_minimum_reps_calculated(self) -> None:
        """Enough repetitions generated to fill budget."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)  # 1/4 each
        budget: Fraction = Fraction(4)  # Need 16 notes
        result_p, result_d = build_sequence(pitches, durations, budget, reps=2)
        # Should have exactly budget worth
        assert sum(result_d) == budget

    def test_reps_parameter_respected_when_larger(self) -> None:
        """If reps > calculated min, uses reps."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        # reps=10 requested, but budget only needs 4
        result_p, _ = build_sequence(
            pitches, durations, Fraction(1), reps=10, vary=False, step=0
        )
        # Fills budget exactly regardless of reps
        assert len(result_p) == 4

    def test_zero_duration_subject_asserts(self) -> None:
        """Subject with zero duration raises AssertionError."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(0),)
        with pytest.raises(AssertionError, match="positive"):
            build_sequence(pitches, durations, Fraction(1))

    def test_start_parameter_shifts_first_note(self) -> None:
        """start parameter shifts all notes."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result_p, _ = build_sequence(
            pitches, durations, Fraction(1, 4), start=2, vary=False
        )
        # Degree 1 + shift 2 = 3
        assert result_p[0].degree == 3

    def test_negative_step(self) -> None:
        """Negative step descends."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(5),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result_p, _ = build_sequence(
            pitches, durations, Fraction(1, 2), step=-2, vary=False, phrase_seed=0
        )
        # First at 5, second at 5-2=3
        degrees: list[int] = [p.degree for p in result_p]
        assert degrees[0] == 5
        assert degrees[1] == 3

    def test_inversion_mirrors_degrees(self) -> None:
        """Inversion uses 8-degree formula via variation cycling."""
        # Test that different phrase_seeds produce variety via variation
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        all_degrees: set[int] = set()
        # Try multiple seeds to find one that applies inversion
        for seed in range(8):
            result_p, _ = build_sequence(
                pitches, durations, Fraction(1), step=0, phrase_seed=seed, vary=True
            )
            degrees: list[int] = [p.degree for p in result_p]
            all_degrees.update(degrees)
        # With variation cycling, we should see inverted degrees somewhere
        # Degree 1 inverts to 7, degree 2 inverts to 6
        assert 6 in all_degrees or 7 in all_degrees


class TestBuildSequenceBreak:
    """Test build_sequence_break function."""

    def test_returns_tuple_pair(self) -> None:
        """Returns tuple of (pitches, durations)."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result_p, result_d = build_sequence_break(pitches, durations, Fraction(1))
        assert isinstance(result_p, tuple)
        assert isinstance(result_d, tuple)

    def test_budget_exactly_filled(self) -> None:
        """Total duration equals budget."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        budget: Fraction = Fraction(2)
        result_p, result_d = build_sequence_break(pitches, durations, budget)
        assert sum(result_d) == budget

    def test_break_after_changes_pattern(self) -> None:
        """After break_after reps, shift changes."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(5),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result_p, _ = build_sequence_break(
            pitches, durations, Fraction(3, 4),
            break_after=1, step=-1, break_shift=3
        )
        degrees: list[int] = [p.degree for p in result_p]
        # Rep 0: shift=0, degree=5
        # Rep 1: shift=0+3=3 (after break), degree=5+3=8->1
        # Rep 2: also shift=3
        assert degrees[0] == 5
        assert degrees[1] == 1  # 5 + 3 = 8 wrapped to 1

    def test_regular_step_before_break(self) -> None:
        """Before break, regular step is used."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(5),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result_p, _ = build_sequence_break(
            pitches, durations, Fraction(1, 2),
            break_after=2, step=-1
        )
        degrees: list[int] = [p.degree for p in result_p]
        # Rep 0: shift=0*-1=0, degree=5
        # Rep 1: shift=1*-1=-1, degree=4
        assert degrees[0] == 5
        assert degrees[1] == 4

    def test_break_shift_applied(self) -> None:
        """break_shift determines post-break shift."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result_p, _ = build_sequence_break(
            pitches, durations, Fraction(1, 2),
            break_after=1, step=-1, break_shift=4
        )
        degrees: list[int] = [p.degree for p in result_p]
        # Rep 0: shift=0, degree=1
        # Rep 1: shift=(1-1)*-1+4=4, degree=1+4=5
        assert degrees[0] == 1
        assert degrees[1] == 5

    def test_zero_duration_asserts(self) -> None:
        """Zero duration in subject raises AssertionError."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(0),)
        with pytest.raises(AssertionError, match="positive"):
            build_sequence_break(pitches, durations, Fraction(1))

    def test_rests_preserved(self) -> None:
        """Rests are preserved in output."""
        pitches: tuple[FloatingNote | Rest, ...] = (FloatingNote(1), Rest())
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        result_p, _ = build_sequence_break(pitches, durations, Fraction(1))
        rest_count: int = sum(1 for p in result_p if isinstance(p, Rest))
        assert rest_count > 0

    def test_partial_last_duration(self) -> None:
        """Last duration can be partial if budget doesn't align."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        budget: Fraction = Fraction(3, 8)  # 1.5 notes worth
        result_p, result_d = build_sequence_break(pitches, durations, budget)
        assert sum(result_d) == budget
        # Last duration should be 1/8 (partial)
        assert result_d[-1] == Fraction(1, 8)

    def test_budget_exhausted_mid_subject(self) -> None:
        """Budget can be exactly exhausted mid-subject."""
        # Subject with 2 notes, budget for 3 notes exactly
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        budget: Fraction = Fraction(3, 4)  # 3 notes, stops mid-2nd rep
        result_p, result_d = build_sequence_break(pitches, durations, budget)
        assert sum(result_d) == budget
        assert len(result_p) == 3  # First rep complete (2) + one from second rep

    def test_default_break_after_is_1(self) -> None:
        """Default break_after is 1."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(5),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result_p, _ = build_sequence_break(
            pitches, durations, Fraction(1, 2), step=-1, break_shift=3
        )
        degrees: list[int] = [p.degree for p in result_p]
        # Default break_after=1: Rep 0 at step 0, Rep 1 at break_shift
        assert degrees[0] == 5
        assert degrees[1] == 1  # 5 + 3 = 8 -> 1

    def test_break_after_2_gives_regular_then_break(self) -> None:
        """break_after=2 gives 2 regular then break."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(5),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result_p, _ = build_sequence_break(
            pitches, durations, Fraction(3, 4),
            break_after=2, step=-1, break_shift=5
        )
        degrees: list[int] = [p.degree for p in result_p]
        # Rep 0: shift=0, degree=5
        # Rep 1: shift=-1, degree=4
        # Rep 2: shift=(2-1)*-1+5=4, degree=5+4=9->2
        assert degrees[0] == 5
        assert degrees[1] == 4
        assert degrees[2] == 2


class TestPrivateFunctions:
    """Test private functions via public API behavior."""

    def test_pitch_signature_uniqueness(self) -> None:
        """Different pitch patterns produce different results."""
        p1: tuple[FloatingNote, ...] = tuple(FloatingNote(i % 7 + 1) for i in range(20))
        p2: tuple[FloatingNote, ...] = tuple(FloatingNote((i + 3) % 7 + 1) for i in range(20))
        d: tuple[Fraction, ...] = tuple(Fraction(1, 16) for _ in range(20))
        # Different starting patterns should produce different sequences
        r1_p, _ = build_sequence(p1, d, Fraction(2), vary=False, step=0)
        r2_p, _ = build_sequence(p2, d, Fraction(2), vary=False, step=0)
        d1: list[int] = [p.degree for p in r1_p]
        d2: list[int] = [p.degree for p in r2_p]
        assert d1 != d2

    def test_excessive_repetition_avoided_through_variation(self) -> None:
        """Variation helps avoid excessive consecutive same degrees."""
        # Subject with same degree repeated
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(1))
        durations: tuple[Fraction, ...] = (Fraction(1, 8), Fraction(1, 8))
        # With variation, the inversion will change degrees
        result_p, _ = build_sequence(
            pitches, durations, Fraction(1), vary=True, phrase_seed=1
        )
        degrees: list[int] = [p.degree for p in result_p]
        # Should have some variety due to inversion
        assert len(set(degrees)) > 1

    def test_wrap_degree_handles_overflow(self) -> None:
        """Degrees wrap correctly when shifted beyond 7."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(7),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        # Shift +3 from degree 7: 7+3=10 -> wrapped to 3
        result_p, _ = build_sequence(
            pitches, durations, Fraction(1, 4), start=3, vary=False
        )
        assert result_p[0].degree == 3  # 7+3=10 -> 3

    def test_wrap_degree_handles_negative(self) -> None:
        """Degrees wrap correctly when shifted below 1."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        # Shift -3 from degree 1: 1-3=-2 -> wrapped to 5
        result_p, _ = build_sequence(
            pitches, durations, Fraction(1, 4), start=-3, vary=False
        )
        assert result_p[0].degree == 5  # 1-3=-2 -> 5


class TestIntegration:
    """Integration tests for sequence module."""

    def test_sequence_then_break_produces_valid_output(self) -> None:
        """Both sequence functions produce compatible output."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(3), FloatingNote(5))
        durations: tuple[Fraction, ...] = (Fraction(1, 8), Fraction(1, 8), Fraction(1, 4))
        budget: Fraction = Fraction(2)
        # Regular sequence
        seq_p, seq_d = build_sequence(pitches, durations, budget)
        assert sum(seq_d) == budget
        # Sequence with break
        brk_p, brk_d = build_sequence_break(pitches, durations, budget)
        assert sum(brk_d) == budget

    def test_long_sequence_fills_budget(self) -> None:
        """Long budget is filled correctly."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        budget: Fraction = Fraction(16)
        result_p, result_d = build_sequence(pitches, durations, budget)
        assert sum(result_d) == budget
        assert len(result_p) == 64  # 16 / (1/4) = 64

    def test_short_sequence_respects_budget(self) -> None:
        """Short budget stops at budget."""
        pitches: tuple[FloatingNote, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 2), Fraction(1, 2))
        budget: Fraction = Fraction(3, 4)  # Less than one full cycle
        result_p, result_d = build_sequence(pitches, durations, budget)
        assert sum(result_d) == budget
        # Should have partial material
        assert len(result_p) == 2  # First note full, second partial

    def test_all_pitches_are_valid(self) -> None:
        """All output pitches are valid FloatingNote or Rest."""
        pitches: tuple[FloatingNote | Rest, ...] = (
            FloatingNote(1), FloatingNote(2), Rest(), FloatingNote(4)
        )
        durations: tuple[Fraction, ...] = (
            Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)
        )
        result_p, _ = build_sequence(pitches, durations, Fraction(2))
        for p in result_p:
            assert isinstance(p, (FloatingNote, Rest))
            if isinstance(p, FloatingNote):
                assert 1 <= p.degree <= 7
