"""Integration tests for engine.realiser.

Category B orchestrator tests: verify phrase realisation orchestration.
Tests import only:
- engine.realiser (module under test)
- engine.types (data types)
- engine.key (Key type)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote
from shared.types import ExpandedVoices, VoiceMaterial
from engine.key import Key
from engine.realiser import (
    beat,
    shortest,
    apply_phrase_gap,
    validate_notes,
    realise_phrase,
    realise_phrases,
)
from engine.engine_types import (
    ExpandedPhrase,
    RealisedNote,
    RealisedPhrase,
    RealisedVoice,
)


def make_expanded_phrase(
    index: int = 0,
    bars: int = 1,
    tonal_target: str = "I",
    cadence: str | None = None,
    soprano_pitches: tuple = None,
    soprano_durations: tuple = None,
    bass_pitches: tuple = None,
    bass_durations: tuple = None,
) -> ExpandedPhrase:
    """Create a test ExpandedPhrase."""
    if soprano_pitches is None:
        soprano_pitches = (FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(1))
    if soprano_durations is None:
        soprano_durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
    if bass_pitches is None:
        bass_pitches = (FloatingNote(1), FloatingNote(5), FloatingNote(1), FloatingNote(1))
    if bass_durations is None:
        bass_durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
    soprano = VoiceMaterial(0, list(soprano_pitches), list(soprano_durations))
    bass = VoiceMaterial(1, list(bass_pitches), list(bass_durations))
    voices = ExpandedVoices(voices=[soprano, bass])
    return ExpandedPhrase(
        index=index,
        bars=bars,
        voices=voices,
        cadence=cadence,
        tonal_target=tonal_target,
    )


class TestBeat:
    """Test beat function."""

    def test_beat_common_time(self) -> None:
        """4/4 metre has quarter note beat."""
        assert beat("4/4") == Fraction(1, 4)

    def test_beat_triple_time(self) -> None:
        """3/4 metre has quarter note beat."""
        assert beat("3/4") == Fraction(1, 4)

    def test_beat_cut_time(self) -> None:
        """2/2 metre has half note beat."""
        assert beat("2/2") == Fraction(1, 2)

    def test_beat_six_eight(self) -> None:
        """6/8 metre has eighth note beat."""
        assert beat("6/8") == Fraction(1, 8)


class TestShortest:
    """Test shortest function."""

    def test_shortest_common_time(self) -> None:
        """4/4 metre has 32nd note as shortest."""
        assert shortest("4/4") == Fraction(1, 32)

    def test_shortest_cut_time(self) -> None:
        """2/2 metre has 16th note as shortest."""
        assert shortest("2/2") == Fraction(1, 16)


class TestApplyPhraseGap:
    """Test apply_phrase_gap function."""

    def test_apply_phrase_gap_shortens_final_note(self) -> None:
        """Final note is shortened by gap amount."""
        notes: tuple[RealisedNote, ...] = (
            RealisedNote(offset=Fraction(0), pitch=60, duration=Fraction(1, 4), voice="soprano"),
            RealisedNote(offset=Fraction(1, 4), pitch=62, duration=Fraction(1, 4), voice="soprano"),
        )
        result = apply_phrase_gap(notes, "4/4")
        assert len(result) == 2
        assert result[1].duration < Fraction(1, 4)

    def test_apply_phrase_gap_preserves_other_notes(self) -> None:
        """Non-final notes are unchanged."""
        notes: tuple[RealisedNote, ...] = (
            RealisedNote(offset=Fraction(0), pitch=60, duration=Fraction(1, 4), voice="soprano"),
            RealisedNote(offset=Fraction(1, 4), pitch=62, duration=Fraction(1, 4), voice="soprano"),
            RealisedNote(offset=Fraction(1, 2), pitch=64, duration=Fraction(1, 4), voice="soprano"),
        )
        result = apply_phrase_gap(notes, "4/4")
        assert result[0].duration == Fraction(1, 4)
        assert result[1].duration == Fraction(1, 4)

    def test_apply_phrase_gap_tiny_note_unchanged(self) -> None:
        """Note shorter than gap is not shortened further."""
        gap = shortest("4/4")  # 1/32
        notes: tuple[RealisedNote, ...] = (
            RealisedNote(offset=Fraction(0), pitch=60, duration=gap, voice="soprano"),
        )
        result = apply_phrase_gap(notes, "4/4")
        assert result[0].duration == gap


class TestValidateNotes:
    """Test validate_notes function."""

    def test_validate_notes_valid_sequence(self) -> None:
        """Valid note sequence passes validation."""
        notes: tuple[RealisedNote, ...] = (
            RealisedNote(offset=Fraction(0), pitch=60, duration=Fraction(1, 4), voice="soprano"),
            RealisedNote(offset=Fraction(1, 4), pitch=62, duration=Fraction(1, 4), voice="soprano"),
        )
        validate_notes(notes, "soprano", "4/4")  # Should not raise

    def test_validate_notes_gap_within_tolerance(self) -> None:
        """Small gap within tolerance passes validation."""
        gap = shortest("4/4")
        notes: tuple[RealisedNote, ...] = (
            RealisedNote(offset=Fraction(0), pitch=60, duration=Fraction(1, 4), voice="soprano"),
            RealisedNote(offset=Fraction(1, 4) + gap, pitch=62, duration=Fraction(1, 4), voice="soprano"),
        )
        validate_notes(notes, "soprano", "4/4")  # Should not raise

    def test_validate_notes_duration_too_short_raises(self) -> None:
        """Duration shorter than minimum raises assertion."""
        min_dur = shortest("4/4")
        tiny = min_dur / 2
        notes: tuple[RealisedNote, ...] = (
            RealisedNote(offset=Fraction(0), pitch=60, duration=tiny, voice="soprano"),
        )
        with pytest.raises(AssertionError):
            validate_notes(notes, "soprano", "4/4")


class TestRealisePhraseBasic:
    """Test basic realise_phrase functionality."""

    def test_realise_phrase_returns_realised_phrase(self) -> None:
        """realise_phrase returns RealisedPhrase instance."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        assert isinstance(result, RealisedPhrase)

    def test_realise_phrase_preserves_index(self) -> None:
        """Phrase index is preserved."""
        exp = make_expanded_phrase(index=5)
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        assert result.index == 5

    def test_realise_phrase_produces_two_voices(self) -> None:
        """Two-voice phrase produces two realised voices."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        assert len(result.voices) == 2

    def test_realise_phrase_soprano_voice_index_zero(self) -> None:
        """Soprano voice has index 0."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        assert result.voices[0].voice_index == 0

    def test_realise_phrase_bass_voice_index_one(self) -> None:
        """Bass voice has index 1 for two-voice piece."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        assert result.voices[1].voice_index == 1


class TestRealisePhraseNotes:
    """Test realise_phrase note generation."""

    def test_realise_phrase_produces_midi_pitches(self) -> None:
        """All notes have MIDI pitch values."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        for voice in result.voices:
            for note in voice.notes:
                assert isinstance(note.pitch, int)
                assert 0 <= note.pitch <= 127

    def test_realise_phrase_notes_have_durations(self) -> None:
        """All notes have positive durations."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        for voice in result.voices:
            for note in voice.notes:
                assert note.duration > 0

    def test_realise_phrase_notes_have_offsets(self) -> None:
        """All notes have valid offsets."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        for voice in result.voices:
            for note in voice.notes:
                assert isinstance(note.offset, Fraction)
                assert note.offset >= 0


class TestRealisePhraseOffset:
    """Test phrase offset handling."""

    def test_realise_phrase_respects_offset(self) -> None:
        """Notes start at specified offset."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        offset = Fraction(4)  # 4 bars in
        result = realise_phrase(exp, key, offset, Fraction(1), "4/4")
        for voice in result.voices:
            if voice.notes:
                assert voice.notes[0].offset >= offset

    def test_realise_phrase_zero_offset(self) -> None:
        """Notes start at beginning when offset is zero."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        for voice in result.voices:
            if voice.notes:
                assert voice.notes[0].offset == Fraction(0)


class TestRealisePhraseTonalTarget:
    """Test realisation with different tonal targets."""

    def test_realise_phrase_tonic_target(self) -> None:
        """Tonic target produces valid notes."""
        exp = make_expanded_phrase(tonal_target="I")
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        assert len(result.voices[0].notes) > 0

    def test_realise_phrase_dominant_target(self) -> None:
        """Dominant target produces valid notes."""
        exp = make_expanded_phrase(tonal_target="V")
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        assert len(result.voices[0].notes) > 0

    def test_realise_phrase_minor_tonic(self) -> None:
        """Minor tonic target produces valid notes."""
        exp = make_expanded_phrase(tonal_target="i")
        key = Key(tonic="A", mode="minor")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        assert len(result.voices[0].notes) > 0


class TestRealisePhraseClimax:
    """Test climax phrase handling."""

    def test_realise_phrase_climax_boost(self) -> None:
        """Climax phrase has register boost."""
        exp_normal = make_expanded_phrase()
        exp_climax = ExpandedPhrase(
            index=0,
            bars=1,
            voices=exp_normal.voices,
            cadence=None,
            tonal_target="I",
            is_climax=True,
        )
        key = Key(tonic="C", mode="major")
        result_normal = realise_phrase(exp_normal, key, Fraction(0), Fraction(1), "4/4")
        result_climax = realise_phrase(exp_climax, key, Fraction(0), Fraction(1), "4/4")
        # Climax should have higher median register
        normal_avg = sum(n.pitch for n in result_normal.voices[0].notes) / len(result_normal.voices[0].notes)
        climax_avg = sum(n.pitch for n in result_climax.voices[0].notes) / len(result_climax.voices[0].notes)
        assert climax_avg > normal_avg


class TestRealisePhrases:
    """Test realise_phrases function."""

    def test_realise_phrases_single_phrase(self) -> None:
        """Single phrase is realised correctly."""
        exp = make_expanded_phrase(cadence="authentic")
        key = Key(tonic="C", mode="major")
        result = realise_phrases([exp], key, Fraction(1), "4/4")
        assert len(result) == 1
        assert isinstance(result[0], RealisedPhrase)

    def test_realise_phrases_multiple_phrases(self) -> None:
        """Multiple phrases are realised in order."""
        phrases: list[ExpandedPhrase] = []
        for i in range(3):
            cadence = "authentic" if i == 2 else None
            exp = make_expanded_phrase(index=i, cadence=cadence)
            phrases.append(exp)
        key = Key(tonic="C", mode="major")
        result = realise_phrases(phrases, key, Fraction(1), "4/4")
        assert len(result) == 3
        for i, rp in enumerate(result):
            assert rp.index == i

    def test_realise_phrases_offsets_accumulate(self) -> None:
        """Phrase offsets accumulate correctly."""
        exp1 = make_expanded_phrase(index=0)  # 1 bar
        exp2 = make_expanded_phrase(index=1, cadence="authentic")  # 1 bar
        key = Key(tonic="C", mode="major")
        result = realise_phrases([exp1, exp2], key, Fraction(1), "4/4")
        # Second phrase should start after first
        first_end = max(n.offset + n.duration for n in result[0].voices[0].notes)
        second_start = min(n.offset for n in result[1].voices[0].notes)
        assert second_start >= first_end - shortest("4/4")  # Allow for articulation gap


class TestRealisedPhraseProperties:
    """Test RealisedPhrase property accessors."""

    def test_soprano_property(self) -> None:
        """soprano property returns soprano notes."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        soprano_notes = result.soprano
        assert isinstance(soprano_notes, tuple)
        assert all(isinstance(n, RealisedNote) for n in soprano_notes)

    def test_bass_property(self) -> None:
        """bass property returns bass notes."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        bass_notes = result.bass
        assert isinstance(bass_notes, tuple)
        assert all(isinstance(n, RealisedNote) for n in bass_notes)


class TestRealisedVoiceProperties:
    """Test RealisedVoice property accessors."""

    def test_note_count_property(self) -> None:
        """note_count property returns correct count."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        for voice in result.voices:
            assert voice.note_count == len(voice.notes)


class TestRealisationMusicTheory:
    """Test music theory correctness in realisation."""

    def test_soprano_above_bass(self) -> None:
        """Soprano notes are generally above bass notes."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        soprano_notes = result.voices[0].notes
        bass_notes = result.voices[-1].notes
        soprano_avg = sum(n.pitch for n in soprano_notes) / len(soprano_notes)
        bass_avg = sum(n.pitch for n in bass_notes) / len(bass_notes)
        assert soprano_avg > bass_avg, "Soprano should be higher than bass"

    def test_pitches_in_range(self) -> None:
        """Pitches are within reasonable MIDI range."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        result = realise_phrase(exp, key, Fraction(0), Fraction(1), "4/4")
        for voice in result.voices:
            for note in voice.notes:
                # Reasonable range for keyboard music
                assert 36 <= note.pitch <= 96

    def test_durations_sum_to_phrase_length(self) -> None:
        """Voice durations sum to phrase length (within gap tolerance)."""
        exp = make_expanded_phrase()
        key = Key(tonic="C", mode="major")
        bar_dur = Fraction(1)
        result = realise_phrase(exp, key, Fraction(0), bar_dur, "4/4")
        expected = sum(exp.soprano_durations)
        gap = shortest("4/4")
        for voice in result.voices:
            total = sum(n.duration for n in voice.notes)
            assert total >= expected - gap
            assert total <= expected
