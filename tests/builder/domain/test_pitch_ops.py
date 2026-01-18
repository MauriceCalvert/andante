"""Tests for builder.domain.pitch_ops.

Tests validate against known musical truths, not implementation details.
"""
import pytest

from builder.domain.pitch_ops import compute_midi_from_diatonic, compute_note_name


class TestComputeMidiFromDiatonic:
    """Tests for compute_midi_from_diatonic."""

    def test_c4_is_midi_60(self) -> None:
        """C4 (diatonic 28) maps to MIDI 60."""
        # diatonic = octave * 7 + degree_index
        # C4 = 4 * 7 + 0 = 28
        assert compute_midi_from_diatonic(28) == 60

    def test_d4_is_midi_62(self) -> None:
        """D4 (diatonic 29) maps to MIDI 62."""
        assert compute_midi_from_diatonic(29) == 62

    def test_e4_is_midi_64(self) -> None:
        """E4 (diatonic 30) maps to MIDI 64."""
        assert compute_midi_from_diatonic(30) == 64

    def test_f4_is_midi_65(self) -> None:
        """F4 (diatonic 31) maps to MIDI 65."""
        assert compute_midi_from_diatonic(31) == 65

    def test_g4_is_midi_67(self) -> None:
        """G4 (diatonic 32) maps to MIDI 67."""
        assert compute_midi_from_diatonic(32) == 67

    def test_a4_is_midi_69(self) -> None:
        """A4 (diatonic 33) maps to MIDI 69."""
        assert compute_midi_from_diatonic(33) == 69

    def test_b4_is_midi_71(self) -> None:
        """B4 (diatonic 34) maps to MIDI 71."""
        assert compute_midi_from_diatonic(34) == 71

    def test_c5_is_midi_72(self) -> None:
        """C5 (diatonic 35) maps to MIDI 72."""
        assert compute_midi_from_diatonic(35) == 72

    def test_c3_is_midi_48(self) -> None:
        """C3 (diatonic 21) maps to MIDI 48."""
        assert compute_midi_from_diatonic(21) == 48

    def test_key_offset_transposes(self) -> None:
        """Key offset transposes result by semitones."""
        # C4 in C major = 60
        # C4 in G major (key_offset=7) = 67
        assert compute_midi_from_diatonic(28, key_offset=7) == 67

    def test_negative_key_offset(self) -> None:
        """Negative key offset transposes down."""
        # C4 in C major = 60
        # C4 in F major (key_offset=-7 or +5) = 65
        assert compute_midi_from_diatonic(28, key_offset=5) == 65

    def test_octave_boundaries(self) -> None:
        """Verify octave boundaries are correct."""
        # C2 = diatonic 14
        assert compute_midi_from_diatonic(14) == 36
        # C6 = diatonic 42
        assert compute_midi_from_diatonic(42) == 84


class TestComputeNoteName:
    """Tests for compute_note_name."""

    def test_midi_60_is_c4(self) -> None:
        """MIDI 60 is C4."""
        assert compute_note_name(60) == "C4"

    def test_midi_69_is_a4(self) -> None:
        """MIDI 69 is A4 (concert pitch)."""
        assert compute_note_name(69) == "A4"

    def test_midi_61_is_csharp4(self) -> None:
        """MIDI 61 is C#4."""
        assert compute_note_name(61) == "C#4"

    def test_midi_72_is_c5(self) -> None:
        """MIDI 72 is C5."""
        assert compute_note_name(72) == "C5"

    def test_midi_48_is_c3(self) -> None:
        """MIDI 48 is C3."""
        assert compute_note_name(48) == "C3"

    def test_midi_36_is_c2(self) -> None:
        """MIDI 36 is C2."""
        assert compute_note_name(36) == "C2"

    def test_all_naturals_in_octave_4(self) -> None:
        """All natural notes in octave 4."""
        expected: dict[int, str] = {
            60: "C4",
            62: "D4",
            64: "E4",
            65: "F4",
            67: "G4",
            69: "A4",
            71: "B4",
        }
        for midi, name in expected.items():
            assert compute_note_name(midi) == name

    def test_all_sharps_in_octave_4(self) -> None:
        """All sharp notes in octave 4."""
        expected: dict[int, str] = {
            61: "C#4",
            63: "D#4",
            66: "F#4",
            68: "G#4",
            70: "A#4",
        }
        for midi, name in expected.items():
            assert compute_note_name(midi) == name

    def test_low_midi_values(self) -> None:
        """Very low MIDI values produce negative octaves."""
        # MIDI 0 = C-1
        assert compute_note_name(0) == "C-1"
        # MIDI 12 = C0
        assert compute_note_name(12) == "C0"

    def test_high_midi_values(self) -> None:
        """High MIDI values work correctly."""
        # MIDI 127 = G9
        assert compute_note_name(127) == "G9"
