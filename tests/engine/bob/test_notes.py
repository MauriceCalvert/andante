"""Tests for Bob NOTES (perceptual observations)."""
import pytest
from fractions import Fraction

from engine.bob.notes import (
    check_resolves_nicely,
    check_feels_conclusive,
    check_feels_half_stop,
    check_same_pattern,
    check_reaches_peak,
    collect_notes,
)
from engine.engine_types import RealisedNote, RealisedPhrase, RealisedVoice


def make_phrase(
    soprano_pitches: list[int],
    bass_pitches: list[int],
    index: int = 0,
) -> RealisedPhrase:
    """Create a phrase for testing."""
    soprano_notes = [
        RealisedNote(offset=Fraction(i), pitch=p, duration=Fraction(1), voice="soprano")
        for i, p in enumerate(soprano_pitches)
    ]
    bass_notes = [
        RealisedNote(offset=Fraction(i), pitch=p, duration=Fraction(1), voice="bass")
        for i, p in enumerate(bass_pitches)
    ]
    return RealisedPhrase(
        index=index,
        voices=[
            RealisedVoice(voice_index=0, notes=soprano_notes),
            RealisedVoice(voice_index=1, notes=bass_notes),
        ],
    )


class TestResolvesNicely:
    """Tests for nice resolution detection."""

    def test_suspension_resolution_detected(self):
        """Dissonance resolving down to consonance should be noted."""
        # Beat 0: m2 (dissonance), Beat 1: consonance after step down
        # Soprano 61 over bass 60 = m2 (dissonant)
        # Soprano 60 over bass 60 = unison (consonant)
        phrase = make_phrase([61, 60], [60, 60])
        issues = check_resolves_nicely([phrase], Fraction(4))
        assert len(issues) >= 1
        assert "resolves" in issues[0].message.lower()

    def test_no_dissonance_no_note(self):
        """All consonant passage should not generate resolution note."""
        # All thirds - consonant throughout
        phrase = make_phrase([64, 65, 67], [60, 61, 63])
        issues = check_resolves_nicely([phrase], Fraction(4))
        assert len(issues) == 0


class TestFeelsConclusive:
    """Tests for conclusive ending detection."""

    def test_authentic_cadence_detected(self):
        """V-I in bass with soprano on tonic should feel conclusive."""
        # In C major: G in bass -> C in bass, soprano ends on C
        # G = 55, C = 48 (bass), C = 60 (soprano)
        phrase = make_phrase([64, 60], [55, 48])  # Bass G->C, soprano E->C
        issues = check_feels_conclusive([phrase], Fraction(4), tonic_pc=0)
        assert len(issues) >= 1
        assert "conclusive" in issues[0].message.lower()

    def test_half_cadence_not_conclusive(self):
        """Ending on V should not feel conclusive."""
        # Ends on G (dominant of C)
        phrase = make_phrase([67, 67], [48, 55])  # Bass C->G
        issues = check_feels_conclusive([phrase], Fraction(4), tonic_pc=0)
        assert len(issues) == 0


class TestFeelsHalfStop:
    """Tests for half cadence detection."""

    def test_half_cadence_detected(self):
        """Phrase ending on dominant should feel like half-stop."""
        # First phrase ends on G (dominant of C), not last phrase
        phrase1 = make_phrase([64, 67], [48, 55], index=0)  # Ends on G
        phrase2 = make_phrase([65, 60], [53, 48], index=1)  # Different phrase after
        issues = check_feels_half_stop([phrase1, phrase2], Fraction(4), tonic_pc=0)
        assert len(issues) >= 1
        assert "half-stop" in issues[0].message.lower()

    def test_final_phrase_no_half_stop(self):
        """Last phrase ending on V should not be flagged as half-stop."""
        # Only one phrase - it's the last one
        phrase = make_phrase([64, 67], [48, 55])  # Ends on G
        issues = check_feels_half_stop([phrase], Fraction(4), tonic_pc=0)
        # Single phrase is last phrase, shouldn't flag
        assert len(issues) == 0


class TestSamePattern:
    """Tests for sequence detection."""

    def test_sequence_detected(self):
        """Transposed repeated pattern should be noted."""
        # Phrase 1: C-D-E (ascending step pattern)
        # Phrase 2: D-E-F# (same intervals, transposed up)
        phrase1 = make_phrase([60, 62, 64], [48, 50, 52], index=0)
        phrase2 = make_phrase([62, 64, 66], [50, 52, 54], index=1)
        issues = check_same_pattern([phrase1, phrase2], Fraction(4))
        assert len(issues) >= 1
        assert "pattern" in issues[0].message.lower()
        assert "higher" in issues[0].message.lower()

    def test_different_pattern_no_note(self):
        """Different patterns should not be noted as sequence."""
        phrase1 = make_phrase([60, 62, 64], [48, 50, 52], index=0)
        phrase2 = make_phrase([67, 64, 60], [55, 52, 48], index=1)  # Different intervals
        issues = check_same_pattern([phrase1, phrase2], Fraction(4))
        assert len(issues) == 0


class TestReachesPeak:
    """Tests for climax detection."""

    def test_peak_detected(self):
        """Highest soprano note should be noted as peak."""
        phrase1 = make_phrase([60, 65, 72], [48, 53, 60], index=0)  # Peak at 72
        phrase2 = make_phrase([70, 65, 60], [58, 53, 48], index=1)
        issues = check_reaches_peak([phrase1, phrase2], Fraction(4))
        assert len(issues) == 1
        assert "high point" in issues[0].message.lower()
        # Peak should be at bar 1, beat 3 (offset 2)
        assert issues[0].bar == 1
        assert issues[0].beat == 3.0


class TestCollectNotes:
    """Tests for collect_notes aggregation."""

    def test_collect_all_notes(self):
        """All NOTES checks should run and return correct category."""
        phrase = make_phrase([64, 60], [55, 48])  # Authentic cadence
        issues = collect_notes([phrase], Fraction(4), tonic_pc=0)
        assert all(i.category == "NOTES" for i in issues)
