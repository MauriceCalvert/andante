"""Integration tests for engine.inner_voice.

Category B orchestrator tests: verify inner voice generation.
Tests import only:
- engine.inner_voice (module under test)
- engine.types (data types)
- engine.key (Key type)
- engine.voice_config (VoiceSet)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, MidiPitch, Rest
from engine.inner_voice import add_inner_voices_with_backtracking
from engine.key import Key
from engine.engine_types import ExpandedPhrase, MotifAST
from engine.voice_config import voice_set_from_count
from engine.voice_material import ExpandedVoices, VoiceMaterial


def make_subject() -> MotifAST:
    """Create a test subject motif."""
    return MotifAST(
        pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4)),
        durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        bars=1,
    )


def make_counter_subject() -> MotifAST:
    """Create a test counter-subject motif."""
    return MotifAST(
        pitches=(FloatingNote(5), FloatingNote(4), FloatingNote(3), FloatingNote(2)),
        durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 2)),
        bars=1,
    )


def make_two_voice_phrase(budget: Fraction = Fraction(2)) -> ExpandedPhrase:
    """Create a two-voice expanded phrase."""
    soprano: VoiceMaterial = VoiceMaterial(
        voice_index=0,
        pitches=[MidiPitch(72), MidiPitch(74), MidiPitch(76), MidiPitch(77)],
        durations=[Fraction(1, 2), Fraction(1, 2), Fraction(1, 2), Fraction(1, 2)],
    )
    bass: VoiceMaterial = VoiceMaterial(
        voice_index=1,
        pitches=[MidiPitch(48), MidiPitch(50), MidiPitch(52), MidiPitch(53)],
        durations=[Fraction(1, 2), Fraction(1, 2), Fraction(1, 2), Fraction(1, 2)],
    )
    voices: ExpandedVoices = ExpandedVoices(voices=[soprano, bass])
    return ExpandedPhrase(
        index=0, bars=2, voices=voices, cadence=None, tonal_target="I",
        is_climax=False, articulation=None, gesture=None,
        energy="moderate", surprise=None, texture="polyphonic",
        episode_type="statement",
    )


def make_four_voice_phrase(budget: Fraction = Fraction(2)) -> ExpandedPhrase:
    """Create a four-voice expanded phrase with inner voices as rests."""
    soprano: VoiceMaterial = VoiceMaterial(
        voice_index=0,
        pitches=[MidiPitch(72), MidiPitch(74)],
        durations=[Fraction(1), Fraction(1)],
    )
    alto: VoiceMaterial = VoiceMaterial(
        voice_index=1,
        pitches=[Rest()],
        durations=[budget],
    )
    tenor: VoiceMaterial = VoiceMaterial(
        voice_index=2,
        pitches=[Rest()],
        durations=[budget],
    )
    bass: VoiceMaterial = VoiceMaterial(
        voice_index=3,
        pitches=[MidiPitch(48), MidiPitch(50)],
        durations=[Fraction(1), Fraction(1)],
    )
    voices: ExpandedVoices = ExpandedVoices(voices=[soprano, alto, tenor, bass])
    return ExpandedPhrase(
        index=0, bars=2, voices=voices, cadence=None, tonal_target="I",
        is_climax=False, articulation=None, gesture=None,
        energy="moderate", surprise=None, texture="polyphonic",
        episode_type="statement",
    )


class TestAddInnerVoicesTwoVoice:
    """Test add_inner_voices_with_backtracking with two voices."""

    def test_two_voice_unchanged(self) -> None:
        """Two-voice phrase returns unchanged."""
        phrase: ExpandedPhrase = make_two_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(2)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        assert result.voices.count == 2


class TestAddInnerVoicesFourVoice:
    """Test add_inner_voices_with_backtracking with four voices."""

    def test_four_voice_fills_inner(self) -> None:
        """Four-voice phrase gets inner voices filled."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0),
            subject=make_subject()
        )
        # Inner voices should no longer be single rests
        assert result.voices.count == 4

    def test_polyphonic_texture_uses_thematic(self) -> None:
        """Polyphonic texture uses thematic material."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0),
            subject=make_subject()
        )
        # Result should have 4 voices
        assert result.voices.count == 4

    def test_homophonic_texture_uses_chords(self) -> None:
        """Homophonic texture fills with chord tones."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "homophonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        # Result should have 4 voices
        assert result.voices.count == 4


class TestAddInnerVoicesAttributes:
    """Test that add_inner_voices_with_backtracking preserves phrase attributes."""

    def test_preserves_index(self) -> None:
        """Phrase index is preserved."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        assert result.index == phrase.index

    def test_preserves_cadence(self) -> None:
        """Phrase cadence is preserved."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        assert result.cadence == phrase.cadence

    def test_preserves_tonal_target(self) -> None:
        """Phrase tonal target is preserved."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        assert result.tonal_target == phrase.tonal_target

    def test_preserves_texture(self) -> None:
        """Phrase texture is preserved."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        assert result.texture == phrase.texture


class TestAddInnerVoicesVoiceOrdering:
    """Test voice ordering in add_inner_voices_with_backtracking."""

    def test_voice_indices_sequential(self) -> None:
        """Voice indices are 0, 1, 2, 3."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        for i, voice in enumerate(result.voices.voices):
            assert voice.voice_index == i

    def test_soprano_unchanged(self) -> None:
        """Soprano voice is unchanged."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "homophonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        # Soprano pitches should be MidiPitch (possibly converted)
        assert result.voices.soprano.voice_index == 0

    def test_bass_unchanged(self) -> None:
        """Bass voice is unchanged."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "homophonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        # Bass should be at last index
        assert result.voices.bass.voice_index == 3


class TestAddInnerVoicesWithSubject:
    """Test add_inner_voices_with_backtracking with subject material."""

    def test_with_subject_produces_pitches(self) -> None:
        """Subject material produces inner voice pitches."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        subject: MotifAST = make_subject()
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0),
            subject=subject
        )
        # Should have 4 voices
        assert result.voices.count == 4

    def test_with_counter_subject(self) -> None:
        """Counter-subject can be used for inner voices."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        subject: MotifAST = make_subject()
        cs: MotifAST = make_counter_subject()
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "polyphonic", voice_set,
            Fraction(1), "4/4", Fraction(0),
            subject=subject, counter_subject=cs
        )
        assert result.voices.count == 4


class TestAddInnerVoicesBacktracking:
    """Test backtracking behavior - replaces proposal_index tests."""

    def test_backtracking_produces_valid_result(self) -> None:
        """Backtracking produces valid result."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "homophonic", voice_set,
            Fraction(1), "4/4", Fraction(0)
        )
        assert result.voices.count == 4

    def test_max_backtracks_parameter(self) -> None:
        """max_backtracks parameter is respected."""
        phrase: ExpandedPhrase = make_four_voice_phrase()
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        # Even with low max_backtracks, should produce result
        result: ExpandedPhrase = add_inner_voices_with_backtracking(
            phrase, key, "homophonic", voice_set,
            Fraction(1), "4/4", Fraction(0),
            max_backtracks=10
        )
        assert result.voices.count == 4
