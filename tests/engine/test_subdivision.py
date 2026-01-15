"""100% coverage tests for engine.subdivision.

Tests import only:
- engine.subdivision (module under test)
- shared (pitch types, VoiceMaterial)
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Rest
from shared.types import VoiceMaterial

from engine.subdivision import (
    VerticalSlice,
    SliceSequence,
    collect_attack_points,
    pitch_at_offset,
    build_slice_sequence,
    consecutive_slice_pairs,
)


class TestVerticalSliceConstruction:
    """Test VerticalSlice dataclass."""

    def test_construction(self) -> None:
        pitches = (FloatingNote(1), FloatingNote(5))
        vs = VerticalSlice(offset=Fraction(0), pitches=pitches)
        assert vs.offset == Fraction(0)
        assert vs.pitches == pitches

    def test_with_none_for_rest(self) -> None:
        pitches = (FloatingNote(1), None)
        vs = VerticalSlice(offset=Fraction(1), pitches=pitches)
        assert vs.pitches[1] is None

    def test_frozen(self) -> None:
        vs = VerticalSlice(offset=Fraction(0), pitches=(FloatingNote(1),))
        with pytest.raises(Exception):
            vs.offset = Fraction(1)


class TestVerticalSliceProperties:
    """Test VerticalSlice properties."""

    def test_voice_count_two(self) -> None:
        pitches = (FloatingNote(1), FloatingNote(5))
        vs = VerticalSlice(offset=Fraction(0), pitches=pitches)
        assert vs.voice_count == 2

    def test_voice_count_four(self) -> None:
        pitches = (FloatingNote(1), FloatingNote(3), FloatingNote(5), FloatingNote(1))
        vs = VerticalSlice(offset=Fraction(0), pitches=pitches)
        assert vs.voice_count == 4

    def test_pitch_for_voice_valid(self) -> None:
        pitches = (FloatingNote(1), FloatingNote(5))
        vs = VerticalSlice(offset=Fraction(0), pitches=pitches)
        assert vs.pitch_for_voice(0) == FloatingNote(1)
        assert vs.pitch_for_voice(1) == FloatingNote(5)

    def test_pitch_for_voice_none(self) -> None:
        pitches = (FloatingNote(1), None)
        vs = VerticalSlice(offset=Fraction(0), pitches=pitches)
        assert vs.pitch_for_voice(1) is None

    def test_pitch_for_voice_invalid_negative(self) -> None:
        pitches = (FloatingNote(1),)
        vs = VerticalSlice(offset=Fraction(0), pitches=pitches)
        with pytest.raises(AssertionError):
            vs.pitch_for_voice(-1)

    def test_pitch_for_voice_invalid_too_high(self) -> None:
        pitches = (FloatingNote(1),)
        vs = VerticalSlice(offset=Fraction(0), pitches=pitches)
        with pytest.raises(AssertionError):
            vs.pitch_for_voice(1)


class TestSliceSequenceConstruction:
    """Test SliceSequence dataclass."""

    def test_construction(self) -> None:
        s1 = VerticalSlice(Fraction(0), (FloatingNote(1),))
        s2 = VerticalSlice(Fraction(1), (FloatingNote(2),))
        seq = SliceSequence(slices=(s1, s2))
        assert seq.slice_count == 2

    def test_empty(self) -> None:
        seq = SliceSequence(slices=())
        assert seq.slice_count == 0


class TestSliceSequenceProperties:
    """Test SliceSequence properties."""

    def test_at_valid(self) -> None:
        s1 = VerticalSlice(Fraction(0), (FloatingNote(1),))
        s2 = VerticalSlice(Fraction(1), (FloatingNote(2),))
        seq = SliceSequence(slices=(s1, s2))
        assert seq.at(0) == s1
        assert seq.at(1) == s2


class TestCollectAttackPoints:
    """Test collect_attack_points function."""

    def test_single_voice(self) -> None:
        """Single voice with quarter notes."""
        voice = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2), FloatingNote(3)],
            durations=[Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)],
        )
        points = collect_attack_points([voice])
        assert points == [Fraction(0), Fraction(1, 4), Fraction(1, 2)]

    def test_two_voices_same_rhythm(self) -> None:
        """Two voices with identical rhythms."""
        soprano = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        bass = VoiceMaterial(
            voice_index=1,
            pitches=[FloatingNote(5), FloatingNote(1)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        points = collect_attack_points([soprano, bass])
        assert points == [Fraction(0), Fraction(1, 2)]

    def test_two_voices_different_rhythms(self) -> None:
        """Two voices with different rhythms create more attack points."""
        soprano = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        bass = VoiceMaterial(
            voice_index=1,
            pitches=[FloatingNote(5), FloatingNote(4), FloatingNote(3), FloatingNote(1)],
            durations=[Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)],
        )
        points = collect_attack_points([soprano, bass])
        # Soprano: 0, 1/2
        # Bass: 0, 1/4, 1/2, 3/4
        # Union: 0, 1/4, 1/2, 3/4
        assert points == [Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)]

    def test_sorted_output(self) -> None:
        """Attack points are returned sorted."""
        voice = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(3, 4), Fraction(1, 4)],
        )
        points = collect_attack_points([voice])
        assert points == sorted(points)


class TestPitchAtOffset:
    """Test pitch_at_offset function."""

    def test_at_attack_point(self) -> None:
        """Pitch at exact attack point."""
        voice = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        assert pitch_at_offset(voice, Fraction(0)) == FloatingNote(1)
        assert pitch_at_offset(voice, Fraction(1, 2)) == FloatingNote(2)

    def test_during_sustained_note(self) -> None:
        """Pitch during a sustained note returns that note."""
        voice = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(1), Fraction(1)],
        )
        # At offset 1/2, first note (dur=1) is still sounding
        assert pitch_at_offset(voice, Fraction(1, 2)) == FloatingNote(1)

    def test_rest_returns_none(self) -> None:
        """Rest at offset returns None."""
        voice = VoiceMaterial(
            voice_index=0,
            pitches=[Rest(), FloatingNote(2)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        assert pitch_at_offset(voice, Fraction(0)) is None
        assert pitch_at_offset(voice, Fraction(1, 2)) == FloatingNote(2)

    def test_rest_during_sustain(self) -> None:
        """Rest continues to be None while sustained."""
        voice = VoiceMaterial(
            voice_index=0,
            pitches=[Rest()],
            durations=[Fraction(1)],
        )
        assert pitch_at_offset(voice, Fraction(1, 2)) is None

    def test_note_after_rest(self) -> None:
        """Note following rest is correctly returned."""
        voice = VoiceMaterial(
            voice_index=0,
            pitches=[Rest(), FloatingNote(3)],
            durations=[Fraction(1, 4), Fraction(3, 4)],
        )
        assert pitch_at_offset(voice, Fraction(0)) is None
        assert pitch_at_offset(voice, Fraction(1, 4)) == FloatingNote(3)
        assert pitch_at_offset(voice, Fraction(1, 2)) == FloatingNote(3)


class TestBuildSliceSequence:
    """Test build_slice_sequence function."""

    def test_two_voices_aligned(self) -> None:
        """Two voices with same rhythm produce aligned slices."""
        soprano = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        bass = VoiceMaterial(
            voice_index=1,
            pitches=[FloatingNote(5), FloatingNote(1)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        seq = build_slice_sequence([soprano, bass])
        assert seq.slice_count == 2
        # First slice at offset 0
        assert seq.at(0).offset == Fraction(0)
        assert seq.at(0).pitches == (FloatingNote(1), FloatingNote(5))
        # Second slice at offset 1/2
        assert seq.at(1).offset == Fraction(1, 2)
        assert seq.at(1).pitches == (FloatingNote(2), FloatingNote(1))

    def test_staggered_attacks(self) -> None:
        """Voices with different rhythms produce more slices."""
        soprano = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1)],
            durations=[Fraction(1)],
        )
        bass = VoiceMaterial(
            voice_index=1,
            pitches=[FloatingNote(5), FloatingNote(4)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        seq = build_slice_sequence([soprano, bass])
        # Attack points: 0, 1/2
        assert seq.slice_count == 2
        # At 0: soprano=1, bass=5
        assert seq.at(0).pitches == (FloatingNote(1), FloatingNote(5))
        # At 1/2: soprano still 1 (sustained), bass=4
        assert seq.at(1).pitches == (FloatingNote(1), FloatingNote(4))

    def test_with_rests(self) -> None:
        """Rests appear as None in slices."""
        soprano = VoiceMaterial(
            voice_index=0,
            pitches=[Rest(), FloatingNote(2)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        bass = VoiceMaterial(
            voice_index=1,
            pitches=[FloatingNote(5), FloatingNote(1)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        seq = build_slice_sequence([soprano, bass])
        assert seq.at(0).pitches == (None, FloatingNote(5))
        assert seq.at(1).pitches == (FloatingNote(2), FloatingNote(1))


class TestConsecutiveSlicePairs:
    """Test consecutive_slice_pairs function."""

    def test_two_slices_one_pair(self) -> None:
        """Two slices produce one pair."""
        s1 = VerticalSlice(Fraction(0), (FloatingNote(1),))
        s2 = VerticalSlice(Fraction(1), (FloatingNote(2),))
        seq = SliceSequence(slices=(s1, s2))
        pairs = consecutive_slice_pairs(seq)
        assert len(pairs) == 1
        assert pairs[0] == (s1, s2)

    def test_three_slices_two_pairs(self) -> None:
        """Three slices produce two pairs."""
        s1 = VerticalSlice(Fraction(0), (FloatingNote(1),))
        s2 = VerticalSlice(Fraction(1, 2), (FloatingNote(2),))
        s3 = VerticalSlice(Fraction(1), (FloatingNote(3),))
        seq = SliceSequence(slices=(s1, s2, s3))
        pairs = consecutive_slice_pairs(seq)
        assert len(pairs) == 2
        assert pairs[0] == (s1, s2)
        assert pairs[1] == (s2, s3)

    def test_single_slice_no_pairs(self) -> None:
        """Single slice produces no pairs."""
        s1 = VerticalSlice(Fraction(0), (FloatingNote(1),))
        seq = SliceSequence(slices=(s1,))
        pairs = consecutive_slice_pairs(seq)
        assert len(pairs) == 0

    def test_empty_sequence_no_pairs(self) -> None:
        """Empty sequence produces no pairs."""
        seq = SliceSequence(slices=())
        pairs = consecutive_slice_pairs(seq)
        assert len(pairs) == 0
