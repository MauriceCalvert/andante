"""Tests for builder.domain.material_ops.

Tests validate against known musical truths, not implementation details.
"""
import pytest
from fractions import Fraction

from builder.domain.material_ops import (
    apply_pitch_shift,
    fit_to_duration,
    convert_midi_to_diatonic,
    convert_degrees_to_diatonic,
)
from builder.types import Notes


class TestApplyPitchShift:
    """Tests for apply_pitch_shift."""

    def test_shift_up_by_one(self) -> None:
        """Shift all pitches up by 1."""
        notes: Notes = Notes(
            pitches=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        )
        result: Notes = apply_pitch_shift(notes, shift=1)
        assert result.pitches == (2, 3, 4)
        assert result.durations == notes.durations

    def test_shift_down(self) -> None:
        """Shift all pitches down by 2."""
        notes: Notes = Notes(
            pitches=(5, 6, 7),
            durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
        )
        result: Notes = apply_pitch_shift(notes, shift=-2)
        assert result.pitches == (3, 4, 5)

    def test_zero_shift(self) -> None:
        """Zero shift returns same pitches."""
        notes: Notes = Notes(
            pitches=(28, 30, 32),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        )
        result: Notes = apply_pitch_shift(notes, shift=0)
        assert result.pitches == notes.pitches

    def test_durations_unchanged(self) -> None:
        """Shift preserves durations exactly."""
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 8), Fraction(3, 16))
        notes: Notes = Notes(pitches=(1, 2, 3), durations=durations)
        result: Notes = apply_pitch_shift(notes, shift=7)
        assert result.durations == durations

    def test_large_shift(self) -> None:
        """Large shifts work correctly (octave = 7 diatonic steps)."""
        notes: Notes = Notes(pitches=(28,), durations=(Fraction(1, 4),))
        result: Notes = apply_pitch_shift(notes, shift=7)
        assert result.pitches == (35,)  # One octave up


class TestFitToDuration:
    """Tests for fit_to_duration."""

    def test_exact_fit_no_change(self) -> None:
        """Notes already fit target duration."""
        notes: Notes = Notes(
            pitches=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        )
        result: Notes = fit_to_duration(notes, target=Fraction(1))
        assert result.pitches == notes.pitches
        assert result.durations == notes.durations

    def test_cycle_to_fill(self) -> None:
        """Cycle notes to fill longer target."""
        notes: Notes = Notes(
            pitches=(1, 2),
            durations=(Fraction(1, 4), Fraction(1, 4)),
        )
        result: Notes = fit_to_duration(notes, target=Fraction(1))
        # Need 4 notes to fill 1 whole note
        assert result.pitches == (1, 2, 1, 2)
        assert result.durations == (Fraction(1, 4),) * 4

    def test_truncate_to_fit(self) -> None:
        """Truncate last note to fit target."""
        notes: Notes = Notes(
            pitches=(1, 2),
            durations=(Fraction(1, 4), Fraction(1, 2)),
        )
        result: Notes = fit_to_duration(notes, target=Fraction(1, 2))
        # First note fits, second truncated to 1/4
        assert result.pitches == (1, 2)
        assert result.durations == (Fraction(1, 4), Fraction(1, 4))

    def test_short_target(self) -> None:
        """Target shorter than first note."""
        notes: Notes = Notes(
            pitches=(1, 2),
            durations=(Fraction(1, 2), Fraction(1, 2)),
        )
        result: Notes = fit_to_duration(notes, target=Fraction(1, 4))
        assert result.pitches == (1,)
        assert result.durations == (Fraction(1, 4),)

    def test_total_duration_equals_target(self) -> None:
        """Result total duration equals target exactly."""
        notes: Notes = Notes(
            pitches=(1, 2, 3),
            durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
        )
        target: Fraction = Fraction(1, 2)
        result: Notes = fit_to_duration(notes, target=target)
        total: Fraction = sum(result.durations, Fraction(0))
        assert total == target


class TestConvertMidiToDiatonic:
    """Tests for convert_midi_to_diatonic."""

    def test_c_to_c_major_identity(self) -> None:
        """C major to C major is identity (just octave conversion)."""
        # C4 = MIDI 60
        notes: Notes = Notes(pitches=(60,), durations=(Fraction(1, 4),))
        result: Notes = convert_midi_to_diatonic(
            notes,
            source_key="C",
            target_key="C",
            target_mode="major",
            min_diatonic=0,
        )
        # MIDI 60 / 12 - 1 = octave 4, pc 0 = degree 0
        # diatonic = 4 * 7 + 0 = 28
        assert result.pitches == (28,)

    def test_g_to_c_major_transpose(self) -> None:
        """G major to C major transposes down 7 semitones."""
        # G4 in G major = MIDI 67
        notes: Notes = Notes(pitches=(67,), durations=(Fraction(1, 4),))
        result: Notes = convert_midi_to_diatonic(
            notes,
            source_key="G",
            target_key="C",
            target_mode="major",
            min_diatonic=0,
        )
        # 67 - 7 = 60 (C4), diatonic 28
        assert result.pitches == (28,)

    def test_min_diatonic_enforced(self) -> None:
        """Notes shifted up if below min_diatonic."""
        # C3 = MIDI 48
        notes: Notes = Notes(pitches=(48,), durations=(Fraction(1, 4),))
        result: Notes = convert_midi_to_diatonic(
            notes,
            source_key="C",
            target_key="C",
            target_mode="major",
            min_diatonic=28,  # C4
        )
        # C3 = diatonic 21, but min is 28, so shift up by 7
        assert result.pitches[0] >= 28

    def test_durations_preserved(self) -> None:
        """Durations unchanged during conversion."""
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 8))
        notes: Notes = Notes(pitches=(60, 62), durations=durations)
        result: Notes = convert_midi_to_diatonic(
            notes,
            source_key="C",
            target_key="C",
            target_mode="major",
            min_diatonic=0,
        )
        assert result.durations == durations

    def test_scale_degrees_in_major(self) -> None:
        """C major scale maps to consecutive diatonic pitches."""
        # C D E F G A B = MIDI 60 62 64 65 67 69 71
        notes: Notes = Notes(
            pitches=(60, 62, 64, 65, 67, 69, 71),
            durations=tuple(Fraction(1, 8) for _ in range(7)),
        )
        result: Notes = convert_midi_to_diatonic(
            notes,
            source_key="C",
            target_key="C",
            target_mode="major",
            min_diatonic=0,
        )
        # Should be consecutive: 28, 29, 30, 31, 32, 33, 34
        assert result.pitches == (28, 29, 30, 31, 32, 33, 34)


class TestConvertDegreesToDiatonic:
    """Tests for convert_degrees_to_diatonic."""

    def test_degree_1_octave_4(self) -> None:
        """Degree 1 in octave 4 is diatonic 28."""
        notes: Notes = Notes(pitches=(1,), durations=(Fraction(1, 4),))
        result: Notes = convert_degrees_to_diatonic(notes, base_octave=4)
        assert result.pitches == (28,)

    def test_all_degrees(self) -> None:
        """Degrees 1-7 map correctly."""
        notes: Notes = Notes(
            pitches=(1, 2, 3, 4, 5, 6, 7),
            durations=tuple(Fraction(1, 8) for _ in range(7)),
        )
        result: Notes = convert_degrees_to_diatonic(notes, base_octave=4)
        # 28, 29, 30, 31, 32, 33, 34
        assert result.pitches == (28, 29, 30, 31, 32, 33, 34)

    def test_octave_3(self) -> None:
        """Octave 3 produces lower pitches."""
        notes: Notes = Notes(pitches=(1,), durations=(Fraction(1, 4),))
        result: Notes = convert_degrees_to_diatonic(notes, base_octave=3)
        # 3 * 7 + 0 = 21
        assert result.pitches == (21,)

    def test_durations_preserved(self) -> None:
        """Durations unchanged during conversion."""
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(3, 8))
        notes: Notes = Notes(pitches=(1, 5), durations=durations)
        result: Notes = convert_degrees_to_diatonic(notes, base_octave=4)
        assert result.durations == durations
