"""Tests for builder.domain.transform_ops.

Tests validate against known musical truths, not implementation details.
"""
import pytest
from fractions import Fraction

from builder.domain.transform_ops import Transform, validate_transform_spec
from builder.types import Notes


class TestTransformInit:
    """Tests for Transform initialization."""

    def test_empty_spec(self) -> None:
        """Empty spec creates identity transform."""
        t: Transform = Transform("identity", {})
        assert t.name == "identity"
        assert t.pitch_op is None
        assert t.duration_op is None
        assert t.slice_n is None

    def test_pitch_op_parsed(self) -> None:
        """Pitch operation is stored."""
        t: Transform = Transform("invert", {"pitch": "negate"})
        assert t.pitch_op == "negate"

    def test_duration_op_parsed(self) -> None:
        """Duration operation is stored."""
        t: Transform = Transform("aug", {"duration": "augment"})
        assert t.duration_op == "augment"

    def test_slice_parsed(self) -> None:
        """Slice parameter is stored."""
        t: Transform = Transform("head", {"slice": 4})
        assert t.slice_n == 4

    def test_transpose_arg_parsed(self) -> None:
        """Transpose argument is extracted."""
        t: Transform = Transform("t3", {"pitch": "transpose(3)"})
        assert t.pitch_op == "transpose(3)"
        assert t.transpose_n == 3

    def test_transpose_negative_arg(self) -> None:
        """Negative transpose argument is parsed."""
        t: Transform = Transform("t-2", {"pitch": "transpose(-2)"})
        assert t.transpose_n == -2


class TestTransformApplyPitch:
    """Tests for Transform pitch operations."""

    def test_negate_around_pivot(self) -> None:
        """Negate inverts pitches around pivot."""
        t: Transform = Transform("inv", {"pitch": "negate"})
        notes: Notes = Notes(
            pitches=(28, 30, 32),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        )
        result: Notes = t.apply(notes, pivot=30)
        # 2*30 - 28 = 32, 2*30 - 30 = 30, 2*30 - 32 = 28
        assert result.pitches == (32, 30, 28)

    def test_reverse_pitches(self) -> None:
        """Reverse reverses pitch order."""
        t: Transform = Transform("retro", {"pitch": "reverse"})
        notes: Notes = Notes(
            pitches=(1, 2, 3, 4),
            durations=(Fraction(1, 4),) * 4,
        )
        result: Notes = t.apply(notes)
        assert result.pitches == (4, 3, 2, 1)

    def test_transpose_from_spec(self) -> None:
        """Transpose uses value from spec."""
        t: Transform = Transform("t5", {"pitch": "transpose(5)"})
        notes: Notes = Notes(pitches=(28,), durations=(Fraction(1, 4),))
        result: Notes = t.apply(notes)
        assert result.pitches == (33,)

    def test_transpose_from_kwarg(self) -> None:
        """Transpose kwarg overrides spec."""
        t: Transform = Transform("t5", {"pitch": "transpose(5)"})
        notes: Notes = Notes(pitches=(28,), durations=(Fraction(1, 4),))
        result: Notes = t.apply(notes, n=2)
        assert result.pitches == (30,)

    def test_no_pitch_op_unchanged(self) -> None:
        """No pitch op leaves pitches unchanged."""
        t: Transform = Transform("dur_only", {"duration": "augment"})
        notes: Notes = Notes(pitches=(1, 2, 3), durations=(Fraction(1, 8),) * 3)
        result: Notes = t.apply(notes)
        assert result.pitches == (1, 2, 3)


class TestTransformApplyDuration:
    """Tests for Transform duration operations."""

    def test_reverse_durations(self) -> None:
        """Reverse reverses duration order."""
        t: Transform = Transform("retro", {"duration": "reverse"})
        notes: Notes = Notes(
            pitches=(1, 2, 3),
            durations=(Fraction(1, 8), Fraction(1, 4), Fraction(1, 2)),
        )
        result: Notes = t.apply(notes)
        assert result.durations == (Fraction(1, 2), Fraction(1, 4), Fraction(1, 8))

    def test_augment_durations(self) -> None:
        """Augment doubles durations."""
        t: Transform = Transform("aug", {"duration": "augment"})
        notes: Notes = Notes(
            pitches=(1, 2),
            durations=(Fraction(1, 8), Fraction(1, 4)),
        )
        result: Notes = t.apply(notes)
        assert result.durations == (Fraction(1, 4), Fraction(1, 2))

    def test_diminish_durations(self) -> None:
        """Diminish halves durations."""
        t: Transform = Transform("dim", {"duration": "diminish"})
        notes: Notes = Notes(
            pitches=(1, 2),
            durations=(Fraction(1, 4), Fraction(1, 2)),
        )
        result: Notes = t.apply(notes)
        assert result.durations == (Fraction(1, 8), Fraction(1, 4))

    def test_no_duration_op_unchanged(self) -> None:
        """No duration op leaves durations unchanged."""
        t: Transform = Transform("pitch_only", {"pitch": "reverse"})
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 8))
        notes: Notes = Notes(pitches=(1, 2), durations=durations)
        result: Notes = t.apply(notes)
        assert result.durations == durations


class TestTransformApplySlice:
    """Tests for Transform slice operations."""

    def test_positive_slice_takes_head(self) -> None:
        """Positive slice takes first N notes."""
        t: Transform = Transform("head3", {"slice": 3})
        notes: Notes = Notes(
            pitches=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 8),) * 5,
        )
        result: Notes = t.apply(notes)
        assert result.pitches == (1, 2, 3)
        assert len(result.durations) == 3

    def test_negative_slice_takes_tail(self) -> None:
        """Negative slice takes last N notes."""
        t: Transform = Transform("tail2", {"slice": -2})
        notes: Notes = Notes(
            pitches=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 8),) * 5,
        )
        result: Notes = t.apply(notes)
        assert result.pitches == (4, 5)
        assert len(result.durations) == 2

    def test_slice_before_pitch_op(self) -> None:
        """Slice is applied before pitch operation."""
        t: Transform = Transform("head_inv", {"slice": 3, "pitch": "reverse"})
        notes: Notes = Notes(
            pitches=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 8),) * 5,
        )
        result: Notes = t.apply(notes)
        # First slice to (1, 2, 3), then reverse to (3, 2, 1)
        assert result.pitches == (3, 2, 1)


class TestTransformCombined:
    """Tests for combined Transform operations."""

    def test_pitch_and_duration_both_applied(self) -> None:
        """Both pitch and duration ops apply."""
        t: Transform = Transform("both", {"pitch": "reverse", "duration": "reverse"})
        notes: Notes = Notes(
            pitches=(1, 2, 3),
            durations=(Fraction(1, 8), Fraction(1, 4), Fraction(1, 2)),
        )
        result: Notes = t.apply(notes)
        assert result.pitches == (3, 2, 1)
        assert result.durations == (Fraction(1, 2), Fraction(1, 4), Fraction(1, 8))

    def test_full_retrograde_inversion(self) -> None:
        """Full retrograde inversion: reverse + negate."""
        t: Transform = Transform("ri", {"pitch": "reverse"})
        t_inv: Transform = Transform("inv", {"pitch": "negate"})
        notes: Notes = Notes(pitches=(28, 30, 32), durations=(Fraction(1, 4),) * 3)

        # First reverse
        r1: Notes = t.apply(notes)
        assert r1.pitches == (32, 30, 28)

        # Then invert around middle (30)
        r2: Notes = t_inv.apply(r1, pivot=30)
        assert r2.pitches == (28, 30, 32)


class TestValidateTransformSpec:
    """Tests for validate_transform_spec."""

    def test_valid_pitch_ops(self) -> None:
        """Valid pitch ops pass validation."""
        validate_transform_spec("t1", {"pitch": "negate"})
        validate_transform_spec("t2", {"pitch": "reverse"})
        validate_transform_spec("t3", {"pitch": "transpose(5)"})

    def test_valid_duration_ops(self) -> None:
        """Valid duration ops pass validation."""
        validate_transform_spec("t1", {"duration": "reverse"})
        validate_transform_spec("t2", {"duration": "augment"})
        validate_transform_spec("t3", {"duration": "diminish"})

    def test_empty_spec_valid(self) -> None:
        """Empty spec is valid."""
        validate_transform_spec("identity", {})

    def test_invalid_pitch_op_raises(self) -> None:
        """Invalid pitch op raises ValueError."""
        with pytest.raises(ValueError, match="unknown pitch op"):
            validate_transform_spec("bad", {"pitch": "invalid_op"})

    def test_invalid_duration_op_raises(self) -> None:
        """Invalid duration op raises ValueError."""
        with pytest.raises(ValueError, match="unknown duration op"):
            validate_transform_spec("bad", {"duration": "invalid_op"})

    def test_combined_valid(self) -> None:
        """Combined valid ops pass."""
        validate_transform_spec("both", {"pitch": "negate", "duration": "augment"})
