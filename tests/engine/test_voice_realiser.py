"""Integration tests for engine.voice_realiser.

Category B orchestrator tests: verify voice realisation to MIDI.
Tests import only:
- engine.voice_realiser (module under test)
- engine.key (Key type)
- engine.types (data types)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, MidiPitch, Rest
from engine.key import Key
from engine.voice_realiser import realise_bass_contrapuntal, realise_voice
from engine.engine_types import RealisedNote


class TestRealiseVoice:
    """Test realise_voice function."""

    def test_realise_midi_pitch_passthrough(self) -> None:
        """MidiPitch passes through unchanged."""
        pitches: tuple = (MidiPitch(60), MidiPitch(62), MidiPitch(64))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 64, "soprano", Fraction(0)
        )
        assert len(result) == 3
        assert result[0].pitch == 60
        assert result[1].pitch == 62
        assert result[2].pitch == 64

    def test_realise_floating_note(self) -> None:
        """FloatingNote resolves to MIDI."""
        pitches: tuple = (FloatingNote(1), FloatingNote(3), FloatingNote(5))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 60, "soprano", Fraction(0)
        )
        assert len(result) == 3
        # Degree 1 in C major is C (pitch class 0)
        assert result[0].pitch % 12 == 0
        # Degree 3 in C major is E (pitch class 4)
        assert result[1].pitch % 12 == 4
        # Degree 5 in C major is G (pitch class 7)
        assert result[2].pitch % 12 == 7

    def test_realise_skips_rests(self) -> None:
        """Rests are skipped (no note produced)."""
        pitches: tuple = (MidiPitch(60), Rest(), MidiPitch(64))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 64, "soprano", Fraction(0)
        )
        assert len(result) == 2  # Rest skipped
        assert result[0].pitch == 60
        assert result[1].pitch == 64

    def test_realise_offsets_accumulate(self) -> None:
        """Offsets accumulate correctly."""
        pitches: tuple = (MidiPitch(60), MidiPitch(62), MidiPitch(64))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 64, "soprano", Fraction(0)
        )
        assert result[0].offset == Fraction(0)
        assert result[1].offset == Fraction(1, 4)
        assert result[2].offset == Fraction(1, 2)

    def test_realise_offset_after_rest(self) -> None:
        """Offset advances through rests."""
        pitches: tuple = (MidiPitch(60), Rest(), MidiPitch(64))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 64, "soprano", Fraction(0)
        )
        assert result[0].offset == Fraction(0)
        assert result[1].offset == Fraction(1, 2)  # After rest

    def test_realise_start_offset(self) -> None:
        """Start offset is applied."""
        pitches: tuple = (MidiPitch(60),)
        durations: tuple = (Fraction(1, 4),)
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 64, "soprano", Fraction(2)
        )
        assert result[0].offset == Fraction(2)

    def test_realise_durations_preserved(self) -> None:
        """Durations are preserved."""
        pitches: tuple = (MidiPitch(60), MidiPitch(62))
        durations: tuple = (Fraction(1, 4), Fraction(1, 2))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 64, "soprano", Fraction(0)
        )
        assert result[0].duration == Fraction(1, 4)
        assert result[1].duration == Fraction(1, 2)

    def test_realise_voice_name_set(self) -> None:
        """Voice name is set on notes."""
        pitches: tuple = (MidiPitch(60),)
        durations: tuple = (Fraction(1, 4),)
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 64, "soprano", Fraction(0)
        )
        assert result[0].voice == "soprano"

    def test_realise_minor_mode(self) -> None:
        """Minor mode resolves correctly."""
        pitches: tuple = (FloatingNote(1), FloatingNote(3), FloatingNote(5))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        key: Key = Key("A", "minor")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 60, "soprano", Fraction(0)
        )
        # Degree 1 in A minor is A (pitch class 9)
        assert result[0].pitch % 12 == 9
        # Degree 3 in A minor is C (pitch class 0)
        assert result[1].pitch % 12 == 0
        # Degree 5 in A minor is E (pitch class 4)
        assert result[2].pitch % 12 == 4


class TestRealiseVoiceStepwise:
    """Test voice leading in realise_voice."""

    def test_stepwise_motion_preferred(self) -> None:
        """Stepwise motion is preferred over leaps."""
        pitches: tuple = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_voice(
            pitches, durations, key, 60, "soprano", Fraction(0)
        )
        # Steps should be small
        interval_1: int = abs(result[1].pitch - result[0].pitch)
        interval_2: int = abs(result[2].pitch - result[1].pitch)
        assert interval_1 <= 4  # Major third or less
        assert interval_2 <= 4


class TestRealiseBasContrapuntal:
    """Test realise_bass_contrapuntal function."""

    def test_bass_resolves_to_midi(self) -> None:
        """Bass pitches resolve to MIDI."""
        bass_pitches: tuple = (FloatingNote(1), FloatingNote(5))
        bass_durations: tuple = (Fraction(1, 2), Fraction(1, 2))
        key: Key = Key("C", "major")
        soprano_notes: tuple[RealisedNote, ...] = (
            RealisedNote(Fraction(0), 72, Fraction(1, 2), "soprano"),
            RealisedNote(Fraction(1, 2), 74, Fraction(1, 2), "soprano"),
        )
        result: tuple[RealisedNote, ...] = realise_bass_contrapuntal(
            bass_pitches, bass_durations, key, 48, Fraction(0), soprano_notes
        )
        assert len(result) == 2
        # Degree 1 is C
        assert result[0].pitch % 12 == 0
        # Degree 5 is G
        assert result[1].pitch % 12 == 7

    def test_bass_midi_passthrough(self) -> None:
        """MidiPitch passes through unchanged."""
        bass_pitches: tuple = (MidiPitch(48), MidiPitch(55))
        bass_durations: tuple = (Fraction(1, 2), Fraction(1, 2))
        key: Key = Key("C", "major")
        soprano_notes: tuple[RealisedNote, ...] = (
            RealisedNote(Fraction(0), 72, Fraction(1, 2), "soprano"),
        )
        result: tuple[RealisedNote, ...] = realise_bass_contrapuntal(
            bass_pitches, bass_durations, key, 48, Fraction(0), soprano_notes
        )
        assert result[0].pitch == 48
        assert result[1].pitch == 55

    def test_bass_skips_rests(self) -> None:
        """Rests are skipped."""
        bass_pitches: tuple = (MidiPitch(48), Rest(), MidiPitch(55))
        bass_durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        key: Key = Key("C", "major")
        soprano_notes: tuple[RealisedNote, ...] = ()
        result: tuple[RealisedNote, ...] = realise_bass_contrapuntal(
            bass_pitches, bass_durations, key, 48, Fraction(0), soprano_notes
        )
        assert len(result) == 2

    def test_bass_voice_name(self) -> None:
        """Bass notes have 'bass' voice name."""
        bass_pitches: tuple = (MidiPitch(48),)
        bass_durations: tuple = (Fraction(1, 2),)
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_bass_contrapuntal(
            bass_pitches, bass_durations, key, 48, Fraction(0), ()
        )
        assert result[0].voice == "bass"

    def test_bass_offsets_accumulate(self) -> None:
        """Bass offsets accumulate correctly."""
        bass_pitches: tuple = (MidiPitch(48), MidiPitch(55), MidiPitch(52))
        bass_durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = realise_bass_contrapuntal(
            bass_pitches, bass_durations, key, 48, Fraction(0), ()
        )
        assert result[0].offset == Fraction(0)
        assert result[1].offset == Fraction(1, 4)
        assert result[2].offset == Fraction(1, 2)


class TestRealisedNoteAttributes:
    """Test RealisedNote attributes."""

    def test_realised_note_has_offset(self) -> None:
        """RealisedNote has offset."""
        note: RealisedNote = RealisedNote(Fraction(1, 4), 60, Fraction(1, 4), "soprano")
        assert note.offset == Fraction(1, 4)

    def test_realised_note_has_pitch(self) -> None:
        """RealisedNote has pitch."""
        note: RealisedNote = RealisedNote(Fraction(0), 72, Fraction(1, 4), "soprano")
        assert note.pitch == 72

    def test_realised_note_has_duration(self) -> None:
        """RealisedNote has duration."""
        note: RealisedNote = RealisedNote(Fraction(0), 60, Fraction(1, 2), "soprano")
        assert note.duration == Fraction(1, 2)

    def test_realised_note_has_voice(self) -> None:
        """RealisedNote has voice."""
        note: RealisedNote = RealisedNote(Fraction(0), 60, Fraction(1, 4), "bass")
        assert note.voice == "bass"
