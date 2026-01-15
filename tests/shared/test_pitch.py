"""Tests for shared.pitch.

Tests pitch representation classes and utility functions.
"""
import pytest

from shared.pitch import (
    CONSONANT_DEGREE_INTERVALS,
    FloatingNote,
    MidiPitch,
    Pitch,
    Rest,
    cycle_pitch_with_variety,
    degree_interval,
    is_degree_consonant,
    is_floating,
    is_midi_pitch,
    is_rest,
    wrap_degree,
)


class TestFloatingNote:
    """Test FloatingNote class."""

    def test_creation_valid(self) -> None:
        """Valid degrees 1-7 create FloatingNote."""
        for deg in range(1, 8):
            note: FloatingNote = FloatingNote(deg)
            assert note.degree == deg

    def test_creation_invalid_zero(self) -> None:
        """Degree 0 raises assertion."""
        with pytest.raises(AssertionError):
            FloatingNote(0)

    def test_creation_invalid_eight(self) -> None:
        """Degree 8 raises assertion."""
        with pytest.raises(AssertionError):
            FloatingNote(8)

    def test_creation_invalid_negative(self) -> None:
        """Negative degree raises assertion."""
        with pytest.raises(AssertionError):
            FloatingNote(-1)

    def test_frozen(self) -> None:
        """FloatingNote is immutable."""
        note: FloatingNote = FloatingNote(1)
        with pytest.raises(Exception):
            note.degree = 2  # type: ignore

    def test_shift_up(self) -> None:
        """shift() moves degree up."""
        note: FloatingNote = FloatingNote(1)
        shifted: FloatingNote = note.shift(2)
        assert shifted.degree == 3

    def test_shift_down(self) -> None:
        """shift() moves degree down."""
        note: FloatingNote = FloatingNote(5)
        shifted: FloatingNote = note.shift(-2)
        assert shifted.degree == 3

    def test_shift_wraps(self) -> None:
        """shift() wraps around 1-7."""
        note: FloatingNote = FloatingNote(6)
        shifted: FloatingNote = note.shift(3)
        assert shifted.degree == 2


class TestRest:
    """Test Rest class."""

    def test_creation(self) -> None:
        """Rest can be created."""
        rest: Rest = Rest()
        assert isinstance(rest, Rest)

    def test_frozen(self) -> None:
        """Rest is immutable."""
        rest: Rest = Rest()
        with pytest.raises(Exception):
            rest.foo = "bar"  # type: ignore


class TestMidiPitch:
    """Test MidiPitch class."""

    def test_creation_valid(self) -> None:
        """Valid MIDI 0-127 creates MidiPitch."""
        for midi in [0, 60, 127]:
            pitch: MidiPitch = MidiPitch(midi)
            assert pitch.midi == midi

    def test_creation_invalid_negative(self) -> None:
        """Negative MIDI raises assertion."""
        with pytest.raises(AssertionError):
            MidiPitch(-1)

    def test_creation_invalid_high(self) -> None:
        """MIDI > 127 raises assertion."""
        with pytest.raises(AssertionError):
            MidiPitch(128)

    def test_frozen(self) -> None:
        """MidiPitch is immutable."""
        pitch: MidiPitch = MidiPitch(60)
        with pytest.raises(Exception):
            pitch.midi = 61  # type: ignore


class TestWrapDegree:
    """Test wrap_degree function."""

    def test_degree_1_unchanged(self) -> None:
        """Degree 1 stays 1."""
        assert wrap_degree(1) == 1

    def test_degree_7_unchanged(self) -> None:
        """Degree 7 stays 7."""
        assert wrap_degree(7) == 7

    def test_degree_8_wraps_to_1(self) -> None:
        """Degree 8 wraps to 1."""
        assert wrap_degree(8) == 1

    def test_degree_9_wraps_to_2(self) -> None:
        """Degree 9 wraps to 2."""
        assert wrap_degree(9) == 2

    def test_degree_14_wraps_to_7(self) -> None:
        """Degree 14 wraps to 7."""
        assert wrap_degree(14) == 7

    def test_degree_0_wraps_to_7(self) -> None:
        """Degree 0 wraps to 7."""
        assert wrap_degree(0) == 7

    def test_negative_degree_wraps(self) -> None:
        """Negative degrees wrap correctly."""
        assert wrap_degree(-1) == 6
        assert wrap_degree(-6) == 1


class TestTypeChecks:
    """Test type check functions."""

    def test_is_rest_true(self) -> None:
        """is_rest returns True for Rest."""
        assert is_rest(Rest()) is True

    def test_is_rest_false_floating(self) -> None:
        """is_rest returns False for FloatingNote."""
        assert is_rest(FloatingNote(1)) is False

    def test_is_rest_false_midi(self) -> None:
        """is_rest returns False for MidiPitch."""
        assert is_rest(MidiPitch(60)) is False

    def test_is_floating_true(self) -> None:
        """is_floating returns True for FloatingNote."""
        assert is_floating(FloatingNote(1)) is True

    def test_is_floating_false_rest(self) -> None:
        """is_floating returns False for Rest."""
        assert is_floating(Rest()) is False

    def test_is_midi_pitch_true(self) -> None:
        """is_midi_pitch returns True for MidiPitch."""
        assert is_midi_pitch(MidiPitch(60)) is True

    def test_is_midi_pitch_false(self) -> None:
        """is_midi_pitch returns False for FloatingNote."""
        assert is_midi_pitch(FloatingNote(1)) is False


class TestDegreeInterval:
    """Test degree_interval function."""

    def test_same_degree(self) -> None:
        """Same degree has interval 0."""
        assert degree_interval(1, 1) == 0

    def test_adjacent_degrees(self) -> None:
        """Adjacent degrees have interval 1."""
        assert degree_interval(1, 2) == 1
        assert degree_interval(2, 1) == 1

    def test_third(self) -> None:
        """Third has interval 2."""
        assert degree_interval(1, 3) == 2

    def test_fifth(self) -> None:
        """Fifth has interval 4."""
        assert degree_interval(1, 5) == 4

    def test_wraps_mod_7(self) -> None:
        """Large intervals wrap mod 7."""
        assert degree_interval(1, 8) == 0  # Same as unison


class TestIsDegreeConsonant:
    """Test is_degree_consonant function."""

    def test_unison_consonant(self) -> None:
        """Unison (interval 0) is consonant."""
        assert is_degree_consonant(1, 1) is True

    def test_third_consonant(self) -> None:
        """Third (interval 2) is consonant."""
        assert is_degree_consonant(1, 3) is True

    def test_fifth_consonant(self) -> None:
        """Fifth (interval 4) is consonant."""
        assert is_degree_consonant(1, 5) is True

    def test_sixth_consonant(self) -> None:
        """Sixth (interval 5) is consonant."""
        assert is_degree_consonant(1, 6) is True

    def test_second_dissonant(self) -> None:
        """Second (interval 1) is dissonant."""
        assert is_degree_consonant(1, 2) is False

    def test_fourth_dissonant(self) -> None:
        """Fourth (interval 3) is dissonant."""
        assert is_degree_consonant(1, 4) is False

    def test_seventh_dissonant(self) -> None:
        """Seventh (interval 6) is dissonant."""
        assert is_degree_consonant(1, 7) is False


class TestConsonantIntervals:
    """Test CONSONANT_DEGREE_INTERVALS constant."""

    def test_contains_unison(self) -> None:
        """Contains unison (0)."""
        assert 0 in CONSONANT_DEGREE_INTERVALS

    def test_contains_third(self) -> None:
        """Contains third (2)."""
        assert 2 in CONSONANT_DEGREE_INTERVALS

    def test_contains_fifth(self) -> None:
        """Contains fifth (4)."""
        assert 4 in CONSONANT_DEGREE_INTERVALS

    def test_contains_sixth(self) -> None:
        """Contains sixth (5)."""
        assert 5 in CONSONANT_DEGREE_INTERVALS

    def test_count(self) -> None:
        """Exactly 4 consonant intervals."""
        assert len(CONSONANT_DEGREE_INTERVALS) == 4


class TestCyclePitchWithVariety:
    """Test cycle_pitch_with_variety function."""

    def test_first_cycle_unchanged(self) -> None:
        """First cycle returns original pitch."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(3), FloatingNote(5))
        result: Pitch = cycle_pitch_with_variety(pitches, 0)
        assert result == FloatingNote(1)

    def test_cycles_through(self) -> None:
        """Cycles through all pitches."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(3))
        assert cycle_pitch_with_variety(pitches, 0) == FloatingNote(1)
        assert cycle_pitch_with_variety(pitches, 1) == FloatingNote(3)

    def test_second_cycle_shifts(self) -> None:
        """Second cycle shifts by 1."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(3))
        result: Pitch = cycle_pitch_with_variety(pitches, 2)
        assert result == FloatingNote(2)

    def test_rest_unchanged(self) -> None:
        """Rest is not shifted."""
        pitches: tuple[Pitch, ...] = (Rest(), FloatingNote(3))
        result: Pitch = cycle_pitch_with_variety(pitches, 2)
        assert result == Rest()
