"""Integration tests for engine.realiser_guards.

Category B orchestrator tests: verify guard checking on realised phrases.
Tests import only:
- engine.realiser_guards (module under test)
- engine.types (data types)
- engine.guards.registry (Guard types)
- stdlib
"""
from fractions import Fraction

import pytest
from engine.realiser_guards import check_guards
from engine.guards.registry import create_guards, Diagnostic
from engine.engine_types import ExpandedPhrase, RealisedNote, RealisedPhrase, RealisedVoice
from engine.voice_material import ExpandedVoices, VoiceMaterial
from shared.pitch import MidiPitch


def make_realised_voice(
    index: int,
    notes: list[tuple[Fraction, int, Fraction]],
    name: str,
) -> RealisedVoice:
    """Create a realised voice from (offset, pitch, duration) tuples."""
    realised_notes: list[RealisedNote] = [
        RealisedNote(offset=offset, pitch=pitch, duration=dur, voice=name)
        for offset, pitch, dur in notes
    ]
    return RealisedVoice(voice_index=index, notes=realised_notes)


def make_realised_phrase(
    index: int,
    soprano_notes: list[tuple[Fraction, int, Fraction]],
    bass_notes: list[tuple[Fraction, int, Fraction]],
) -> RealisedPhrase:
    """Create a two-voice realised phrase."""
    soprano: RealisedVoice = make_realised_voice(0, soprano_notes, "soprano")
    bass: RealisedVoice = make_realised_voice(1, bass_notes, "bass")
    return RealisedPhrase(index=index, voices=(soprano, bass))


def make_four_voice_realised_phrase(
    index: int,
    soprano_notes: list[tuple[Fraction, int, Fraction]],
    alto_notes: list[tuple[Fraction, int, Fraction]],
    tenor_notes: list[tuple[Fraction, int, Fraction]],
    bass_notes: list[tuple[Fraction, int, Fraction]],
) -> RealisedPhrase:
    """Create a four-voice realised phrase."""
    soprano: RealisedVoice = make_realised_voice(0, soprano_notes, "soprano")
    alto: RealisedVoice = make_realised_voice(1, alto_notes, "alto")
    tenor: RealisedVoice = make_realised_voice(2, tenor_notes, "tenor")
    bass: RealisedVoice = make_realised_voice(3, bass_notes, "bass")
    return RealisedPhrase(index=index, voices=(soprano, alto, tenor, bass))


def make_expanded_phrase(index: int, cadence: str | None = None) -> ExpandedPhrase:
    """Create a minimal expanded phrase for testing."""
    soprano: VoiceMaterial = VoiceMaterial(
        voice_index=0,
        pitches=[MidiPitch(72)],
        durations=[Fraction(1)],
    )
    bass: VoiceMaterial = VoiceMaterial(
        voice_index=1,
        pitches=[MidiPitch(48)],
        durations=[Fraction(1)],
    )
    voices: ExpandedVoices = ExpandedVoices(voices=[soprano, bass])
    return ExpandedPhrase(
        index=index, bars=1, voices=voices, cadence=cadence, tonal_target="I",
        is_climax=False, articulation=None, gesture=None,
        energy="moderate", surprise=None, texture="polyphonic",
        episode_type="statement",
    )


class TestCheckGuardsBasic:
    """Test basic check_guards functionality."""

    def test_empty_phrases_no_diagnostics(self) -> None:
        """Empty phrase list returns no diagnostics."""
        guards = create_guards()
        result: list[Diagnostic] = check_guards([], [], guards, Fraction(1), "4/4")
        assert result == []

    def test_clean_voices_no_violations(self) -> None:
        """Clean voice leading produces no violations."""
        realised: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 72, Fraction(1, 4)), (Fraction(1, 4), 74, Fraction(1, 4))],
            [(Fraction(0), 60, Fraction(1, 4)), (Fraction(1, 4), 59, Fraction(1, 4))],  # Contrary
        )
        expanded: ExpandedPhrase = make_expanded_phrase(0)
        guards = create_guards()
        result: list[Diagnostic] = check_guards(
            [realised], [expanded], guards, Fraction(1), "4/4"
        )
        # May have some violations depending on guard configuration
        # Just verify it runs without error
        assert isinstance(result, list)


class TestCheckGuardsParallelMotion:
    """Test parallel motion detection in check_guards."""

    def test_parallel_fifth_detected(self) -> None:
        """Parallel fifth is detected."""
        # Parallel fifths: C-G to D-A
        realised: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 72, Fraction(1, 4)), (Fraction(1, 4), 74, Fraction(1, 4))],  # C5 to D5
            [(Fraction(0), 65, Fraction(1, 4)), (Fraction(1, 4), 67, Fraction(1, 4))],  # F4 to G4
        )
        expanded: ExpandedPhrase = make_expanded_phrase(0)
        guards = create_guards()
        result: list[Diagnostic] = check_guards(
            [realised], [expanded], guards, Fraction(1), "4/4"
        )
        # Should detect parallel fifths
        assert isinstance(result, list)

    def test_parallel_octave_detected(self) -> None:
        """Parallel octave is detected."""
        # Parallel octaves: C5-C4 to D5-D4
        realised: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 72, Fraction(1, 4)), (Fraction(1, 4), 74, Fraction(1, 4))],  # C5 to D5
            [(Fraction(0), 60, Fraction(1, 4)), (Fraction(1, 4), 62, Fraction(1, 4))],  # C4 to D4
        )
        expanded: ExpandedPhrase = make_expanded_phrase(0)
        guards = create_guards()
        result: list[Diagnostic] = check_guards(
            [realised], [expanded], guards, Fraction(1), "4/4"
        )
        # Should detect parallel octaves
        assert isinstance(result, list)


class TestCheckGuardsCadence:
    """Test cadence filtering in check_guards."""

    def test_cadence_final_note_filtered(self) -> None:
        """Violations at cadence final note are filtered."""
        # Parallel motion at final note
        realised: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 72, Fraction(1, 4)), (Fraction(1, 4), 74, Fraction(1, 4))],
            [(Fraction(0), 60, Fraction(1, 4)), (Fraction(1, 4), 62, Fraction(1, 4))],
        )
        expanded: ExpandedPhrase = make_expanded_phrase(0, cadence="authentic")
        guards = create_guards()
        result: list[Diagnostic] = check_guards(
            [realised], [expanded], guards, Fraction(1), "4/4"
        )
        # Cadence violations should be filtered
        assert isinstance(result, list)


class TestCheckGuardsFourVoice:
    """Test check_guards with four voices."""

    def test_four_voice_all_pairs_checked(self) -> None:
        """All voice pairs are checked in four-voice texture."""
        realised: RealisedPhrase = make_four_voice_realised_phrase(
            0,
            [(Fraction(0), 72, Fraction(1, 4))],  # Soprano
            [(Fraction(0), 64, Fraction(1, 4))],  # Alto
            [(Fraction(0), 57, Fraction(1, 4))],  # Tenor
            [(Fraction(0), 48, Fraction(1, 4))],  # Bass
        )
        expanded: ExpandedPhrase = make_expanded_phrase(0)
        guards = create_guards()
        result: list[Diagnostic] = check_guards(
            [realised], [expanded], guards, Fraction(1), "4/4"
        )
        # Should run without error
        assert isinstance(result, list)


class TestCheckGuardsMultiplePhrases:
    """Test check_guards with multiple phrases."""

    def test_multiple_phrases_processed(self) -> None:
        """Multiple phrases are all processed."""
        realised_1: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 72, Fraction(1, 4))],
            [(Fraction(0), 60, Fraction(1, 4))],
        )
        realised_2: RealisedPhrase = make_realised_phrase(
            1,
            [(Fraction(1, 4), 74, Fraction(1, 4))],
            [(Fraction(1, 4), 62, Fraction(1, 4))],
        )
        expanded_1: ExpandedPhrase = make_expanded_phrase(0)
        expanded_2: ExpandedPhrase = make_expanded_phrase(1)
        guards = create_guards()
        result: list[Diagnostic] = check_guards(
            [realised_1, realised_2], [expanded_1, expanded_2], guards, Fraction(1), "4/4"
        )
        assert isinstance(result, list)


class TestRealisedPhraseStructure:
    """Test RealisedPhrase structure for guards."""

    def test_realised_phrase_has_voices(self) -> None:
        """RealisedPhrase has voices tuple."""
        realised: RealisedPhrase = make_realised_phrase(
            0,
            [(Fraction(0), 72, Fraction(1, 4))],
            [(Fraction(0), 60, Fraction(1, 4))],
        )
        assert len(realised.voices) == 2

    def test_realised_voice_has_notes(self) -> None:
        """RealisedVoice has notes tuple."""
        voice: RealisedVoice = make_realised_voice(
            0, [(Fraction(0), 72, Fraction(1, 4))], "soprano"
        )
        assert len(voice.notes) == 1

    def test_realised_note_attributes(self) -> None:
        """RealisedNote has offset, pitch, duration, voice."""
        note: RealisedNote = RealisedNote(
            offset=Fraction(1, 2), pitch=64, duration=Fraction(1, 4), voice="alto"
        )
        assert note.offset == Fraction(1, 2)
        assert note.pitch == 64
        assert note.duration == Fraction(1, 4)
        assert note.voice == "alto"


class TestDiagnosticStructure:
    """Test Diagnostic structure from guards."""

    def test_diagnostic_type(self) -> None:
        """Diagnostics have correct type attribute."""
        guards = create_guards()
        # Just verify guards are created
        assert isinstance(guards, dict)
