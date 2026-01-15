"""100% coverage tests for shared.types (VoiceMaterial, ExpandedVoices).

Tests import only:
- shared (shared types)
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Rest, MidiPitch
from shared.types import (
    VoiceMaterial,
    ExpandedVoices,
)


class TestVoiceMaterialConstruction:
    """Test VoiceMaterial dataclass construction."""

    def test_valid_construction(self) -> None:
        vm = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(1, 4), Fraction(1, 4)],
        )
        assert vm.voice_index == 0
        assert len(vm.pitches) == 2
        assert len(vm.durations) == 2

    def test_empty_lists(self) -> None:
        vm = VoiceMaterial(voice_index=0, pitches=[], durations=[])
        assert vm.note_count == 0

    def test_mismatched_lengths_raises(self) -> None:
        with pytest.raises(AssertionError, match="Pitch/duration mismatch"):
            VoiceMaterial(
                voice_index=0,
                pitches=[FloatingNote(1), FloatingNote(2)],
                durations=[Fraction(1, 4)],
            )

    def test_with_rest(self) -> None:
        vm = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), Rest()],
            durations=[Fraction(1, 4), Fraction(1, 4)],
        )
        assert len(vm.pitches) == 2

    def test_with_midi_pitch(self) -> None:
        vm = VoiceMaterial(
            voice_index=1,
            pitches=[MidiPitch(60), MidiPitch(62)],
            durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        assert vm.pitches[0].midi == 60

    def test_frozen(self) -> None:
        vm = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1)],
            durations=[Fraction(1, 4)],
        )
        with pytest.raises(Exception):
            vm.voice_index = 1


class TestVoiceMaterialProperties:
    """Test VoiceMaterial property methods."""

    def test_budget_single_note(self) -> None:
        vm = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1)],
            durations=[Fraction(1, 4)],
        )
        assert vm.budget == Fraction(1, 4)

    def test_budget_multiple_notes(self) -> None:
        vm = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2), FloatingNote(3)],
            durations=[Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)],
        )
        assert vm.budget == Fraction(1)

    def test_budget_empty(self) -> None:
        vm = VoiceMaterial(voice_index=0, pitches=[], durations=[])
        assert vm.budget == Fraction(0)

    def test_note_count(self) -> None:
        vm = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2), FloatingNote(3)],
            durations=[Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)],
        )
        assert vm.note_count == 3


class TestExpandedVoicesConstruction:
    """Test ExpandedVoices dataclass construction."""

    def test_valid_two_voices(self) -> None:
        ev = ExpandedVoices(voices=[
            VoiceMaterial(0, [FloatingNote(1)], [Fraction(1)]),
            VoiceMaterial(1, [FloatingNote(5)], [Fraction(1)]),
        ])
        assert ev.count == 2

    def test_valid_four_voices(self) -> None:
        ev = ExpandedVoices(voices=[
            VoiceMaterial(0, [FloatingNote(1)], [Fraction(1)]),
            VoiceMaterial(1, [FloatingNote(3)], [Fraction(1)]),
            VoiceMaterial(2, [FloatingNote(5)], [Fraction(1)]),
            VoiceMaterial(3, [FloatingNote(1)], [Fraction(1)]),
        ])
        assert ev.count == 4

    def test_less_than_two_voices_raises(self) -> None:
        with pytest.raises(AssertionError, match="at least 2 voices"):
            ExpandedVoices(voices=[
                VoiceMaterial(0, [FloatingNote(1)], [Fraction(1)]),
            ])

    def test_voice_index_mismatch_raises(self) -> None:
        with pytest.raises(AssertionError, match="Voice index mismatch"):
            ExpandedVoices(voices=[
                VoiceMaterial(0, [FloatingNote(1)], [Fraction(1)]),
                VoiceMaterial(2, [FloatingNote(5)], [Fraction(1)]),  # Should be 1
            ])

    def test_frozen(self) -> None:
        ev = ExpandedVoices(voices=[
            VoiceMaterial(0, [FloatingNote(1)], [Fraction(1)]),
            VoiceMaterial(1, [FloatingNote(5)], [Fraction(1)]),
        ])
        with pytest.raises(Exception):
            ev.voices = []


class TestExpandedVoicesProperties:
    """Test ExpandedVoices property methods."""

    def test_soprano_is_first_voice(self) -> None:
        soprano = VoiceMaterial(0, [FloatingNote(5)], [Fraction(1)])
        bass = VoiceMaterial(1, [FloatingNote(1)], [Fraction(1)])
        ev = ExpandedVoices(voices=[soprano, bass])
        assert ev.soprano == soprano

    def test_bass_is_last_voice(self) -> None:
        soprano = VoiceMaterial(0, [FloatingNote(5)], [Fraction(1)])
        alto = VoiceMaterial(1, [FloatingNote(3)], [Fraction(1)])
        bass = VoiceMaterial(2, [FloatingNote(1)], [Fraction(1)])
        ev = ExpandedVoices(voices=[soprano, alto, bass])
        assert ev.bass == bass

    def test_count(self) -> None:
        ev = ExpandedVoices(voices=[
            VoiceMaterial(0, [FloatingNote(1)], [Fraction(1)]),
            VoiceMaterial(1, [FloatingNote(5)], [Fraction(1)]),
        ])
        assert ev.count == 2

    def test_inner_voices_two_voice(self) -> None:
        ev = ExpandedVoices(voices=[
            VoiceMaterial(0, [FloatingNote(1)], [Fraction(1)]),
            VoiceMaterial(1, [FloatingNote(5)], [Fraction(1)]),
        ])
        assert ev.inner_voices() == []

    def test_inner_voices_three_voice(self) -> None:
        alto = VoiceMaterial(1, [FloatingNote(3)], [Fraction(1)])
        ev = ExpandedVoices(voices=[
            VoiceMaterial(0, [FloatingNote(5)], [Fraction(1)]),
            alto,
            VoiceMaterial(2, [FloatingNote(1)], [Fraction(1)]),
        ])
        assert ev.inner_voices() == [alto]

    def test_inner_voices_four_voice(self) -> None:
        alto = VoiceMaterial(1, [FloatingNote(3)], [Fraction(1)])
        tenor = VoiceMaterial(2, [FloatingNote(5)], [Fraction(1)])
        ev = ExpandedVoices(voices=[
            VoiceMaterial(0, [FloatingNote(5)], [Fraction(1)]),
            alto,
            tenor,
            VoiceMaterial(3, [FloatingNote(1)], [Fraction(1)]),
        ])
        assert ev.inner_voices() == [alto, tenor]


class TestExpandedVoicesFromTwoVoices:
    """Test ExpandedVoices.from_two_voices static method."""

    def test_creates_two_voice_structure(self) -> None:
        ev = ExpandedVoices.from_two_voices(
            soprano_pitches=[FloatingNote(5), FloatingNote(4)],
            soprano_durations=[Fraction(1, 2), Fraction(1, 2)],
            bass_pitches=[FloatingNote(1), FloatingNote(2)],
            bass_durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        assert ev.count == 2

    def test_soprano_has_correct_index(self) -> None:
        ev = ExpandedVoices.from_two_voices(
            soprano_pitches=[FloatingNote(5)],
            soprano_durations=[Fraction(1)],
            bass_pitches=[FloatingNote(1)],
            bass_durations=[Fraction(1)],
        )
        assert ev.soprano.voice_index == 0

    def test_bass_has_correct_index(self) -> None:
        ev = ExpandedVoices.from_two_voices(
            soprano_pitches=[FloatingNote(5)],
            soprano_durations=[Fraction(1)],
            bass_pitches=[FloatingNote(1)],
            bass_durations=[Fraction(1)],
        )
        assert ev.bass.voice_index == 1

    def test_pitches_preserved(self) -> None:
        soprano_p = [FloatingNote(5), FloatingNote(4), FloatingNote(3)]
        bass_p = [FloatingNote(1), FloatingNote(2), FloatingNote(3)]
        ev = ExpandedVoices.from_two_voices(
            soprano_pitches=soprano_p,
            soprano_durations=[Fraction(1, 4)] * 3,
            bass_pitches=bass_p,
            bass_durations=[Fraction(1, 4)] * 3,
        )
        assert ev.soprano.pitches == soprano_p
        assert ev.bass.pitches == bass_p

    def test_durations_preserved(self) -> None:
        soprano_d = [Fraction(1, 4), Fraction(1, 8), Fraction(1, 8)]
        bass_d = [Fraction(1, 2)]
        ev = ExpandedVoices.from_two_voices(
            soprano_pitches=[FloatingNote(1)] * 3,
            soprano_durations=soprano_d,
            bass_pitches=[FloatingNote(1)],
            bass_durations=bass_d,
        )
        assert ev.soprano.durations == soprano_d
        assert ev.bass.durations == bass_d
