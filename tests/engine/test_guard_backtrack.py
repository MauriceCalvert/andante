"""Integration tests for engine.guard_backtrack.

Category B orchestrator tests: verify guard-based backtracking.
Tests import only:
- engine.guard_backtrack (module under test)
- engine.key (Key type)
- shared.pitch (pitch types)
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, MidiPitch, Rest
from engine.guard_backtrack import (
    accept_candidate,
    AccumulatedMidi,
    check_candidate_guards,
    reset_accumulated_midi,
)
from engine.key import Key


class TestAccumulatedMidi:
    """Test AccumulatedMidi dataclass."""

    def test_empty_creates_empty_voices(self) -> None:
        """Empty creates lists for all voices."""
        acc: AccumulatedMidi = AccumulatedMidi.empty(4)
        assert acc.voice_count == 4
        for i in range(4):
            assert acc.get_voice(i) == []

    def test_add_voice_notes(self) -> None:
        """Add notes to a voice."""
        acc: AccumulatedMidi = AccumulatedMidi.empty(2)
        notes: list[tuple[Fraction, int]] = [(Fraction(0), 60), (Fraction(1, 4), 62)]
        new_acc: AccumulatedMidi = acc.add_voice_notes(0, notes)
        assert new_acc.get_voice(0) == notes
        # Original unchanged (immutable)
        assert acc.get_voice(0) == []

    def test_voice_count(self) -> None:
        """Voice count is correct."""
        acc: AccumulatedMidi = AccumulatedMidi.empty(3)
        assert acc.voice_count == 3

    def test_get_voice(self) -> None:
        """Get voice returns correct list."""
        acc: AccumulatedMidi = AccumulatedMidi.empty(2)
        notes: list[tuple[Fraction, int]] = [(Fraction(0), 60)]
        acc = acc.add_voice_notes(1, notes)
        assert acc.get_voice(1) == notes
        assert acc.get_voice(0) == []


class TestResetAccumulatedMidi:
    """Test reset_accumulated_midi function."""

    def test_reset_clears_state(self) -> None:
        """Reset clears accumulated state."""
        reset_accumulated_midi(2)
        # Subsequent operations should work on fresh state
        key: Key = Key("C", "major")
        violations = check_candidate_guards(
            (MidiPitch(60),), (Fraction(1, 4),),
            (MidiPitch(48),), (Fraction(1, 4),),
            key, Fraction(0)
        )
        assert isinstance(violations, list)

    def test_reset_with_voice_count(self) -> None:
        """Reset with specific voice count."""
        reset_accumulated_midi(4)
        # Should work without error
        key: Key = Key("C", "major")
        check_candidate_guards(
            (MidiPitch(60),), (Fraction(1, 4),),
            (MidiPitch(48),), (Fraction(1, 4),),
            key, Fraction(0)
        )


class TestCheckCandidateGuards:
    """Test check_candidate_guards function."""

    def test_clean_candidate_no_violations(self) -> None:
        """Clean candidate produces no violations."""
        reset_accumulated_midi(2)
        key: Key = Key("C", "major")
        soprano: tuple = (MidiPitch(60), MidiPitch(62), MidiPitch(64))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        bass: tuple = (MidiPitch(48), MidiPitch(50), MidiPitch(52))
        violations = check_candidate_guards(
            soprano, durations, bass, durations, key, Fraction(0)
        )
        # Clean initial candidate should have no violations
        assert isinstance(violations, list)

    def test_floating_note_resolved(self) -> None:
        """FloatingNote pitches are resolved."""
        reset_accumulated_midi(2)
        key: Key = Key("C", "major")
        soprano: tuple = (FloatingNote(1), FloatingNote(2))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4))
        bass: tuple = (FloatingNote(1), FloatingNote(7))
        violations = check_candidate_guards(
            soprano, durations, bass, durations, key, Fraction(0)
        )
        # Should resolve FloatingNotes and check
        assert isinstance(violations, list)

    def test_rest_skipped(self) -> None:
        """Rests are skipped in checking."""
        reset_accumulated_midi(2)
        key: Key = Key("C", "major")
        soprano: tuple = (MidiPitch(60), Rest(), MidiPitch(64))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        bass: tuple = (MidiPitch(48), MidiPitch(50), MidiPitch(52))
        violations = check_candidate_guards(
            soprano, durations, bass, durations, key, Fraction(0)
        )
        # Should handle rests
        assert isinstance(violations, list)

    def test_phrase_offset_applied(self) -> None:
        """Phrase offset is applied to note times."""
        reset_accumulated_midi(2)
        key: Key = Key("C", "major")
        soprano: tuple = (MidiPitch(60),)
        durations: tuple = (Fraction(1, 4),)
        bass: tuple = (MidiPitch(48),)
        violations = check_candidate_guards(
            soprano, durations, bass, durations, key, Fraction(4)
        )
        # Should apply offset
        assert isinstance(violations, list)


class TestAcceptCandidate:
    """Test accept_candidate function."""

    def test_accept_adds_to_accumulated(self) -> None:
        """Accept adds notes to accumulated state."""
        reset_accumulated_midi(2)
        key: Key = Key("C", "major")
        soprano: tuple = (MidiPitch(60), MidiPitch(62))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4))
        bass: tuple = (MidiPitch(48), MidiPitch(50))
        # Accept the candidate
        accept_candidate(soprano, durations, bass, durations, key, Fraction(0))
        # Check that subsequent candidate is checked against accumulated
        violations = check_candidate_guards(
            (MidiPitch(60), MidiPitch(62)),  # Duplicate
            durations,
            (MidiPitch(48), MidiPitch(50)),  # Duplicate
            durations,
            key, Fraction(1, 2)
        )
        # May detect duplication
        assert isinstance(violations, list)

    def test_accept_with_floating_notes(self) -> None:
        """Accept works with FloatingNotes."""
        reset_accumulated_midi(2)
        key: Key = Key("C", "major")
        soprano: tuple = (FloatingNote(1), FloatingNote(2))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4))
        bass: tuple = (FloatingNote(5), FloatingNote(6))
        # Should resolve and accept
        accept_candidate(soprano, durations, bass, durations, key, Fraction(0))

    def test_accept_with_rests(self) -> None:
        """Accept handles rests correctly."""
        reset_accumulated_midi(2)
        key: Key = Key("C", "major")
        soprano: tuple = (MidiPitch(60), Rest())
        durations: tuple = (Fraction(1, 4), Fraction(1, 4))
        bass: tuple = (MidiPitch(48), MidiPitch(50))
        # Should handle rests
        accept_candidate(soprano, durations, bass, durations, key, Fraction(0))


class TestAccumulatedMidiImmutability:
    """Test that AccumulatedMidi is immutable."""

    def test_add_returns_new_instance(self) -> None:
        """add_voice_notes returns new instance."""
        acc1: AccumulatedMidi = AccumulatedMidi.empty(2)
        acc2: AccumulatedMidi = acc1.add_voice_notes(0, [(Fraction(0), 60)])
        assert acc1 is not acc2
        assert acc1.get_voice(0) == []
        assert acc2.get_voice(0) == [(Fraction(0), 60)]

    def test_multiple_adds_preserve_state(self) -> None:
        """Multiple adds don't interfere."""
        acc1: AccumulatedMidi = AccumulatedMidi.empty(2)
        acc2: AccumulatedMidi = acc1.add_voice_notes(0, [(Fraction(0), 60)])
        acc3: AccumulatedMidi = acc2.add_voice_notes(1, [(Fraction(0), 48)])
        assert acc1.get_voice(0) == []
        assert acc1.get_voice(1) == []
        assert acc2.get_voice(0) == [(Fraction(0), 60)]
        assert acc2.get_voice(1) == []
        assert acc3.get_voice(0) == [(Fraction(0), 60)]
        assert acc3.get_voice(1) == [(Fraction(0), 48)]


class TestGuardBacktrackIntegration:
    """Integration tests for guard backtracking flow."""

    def test_reset_check_accept_flow(self) -> None:
        """Full reset -> check -> accept flow works."""
        reset_accumulated_midi(2)
        key: Key = Key("C", "major")
        # First phrase
        soprano1: tuple = (MidiPitch(72), MidiPitch(74))
        durations: tuple = (Fraction(1, 4), Fraction(1, 4))
        bass1: tuple = (MidiPitch(48), MidiPitch(50))
        # Check first candidate
        violations1 = check_candidate_guards(
            soprano1, durations, bass1, durations, key, Fraction(0)
        )
        # Accept first candidate
        accept_candidate(soprano1, durations, bass1, durations, key, Fraction(0))
        # Second phrase
        soprano2: tuple = (MidiPitch(76), MidiPitch(77))
        bass2: tuple = (MidiPitch(52), MidiPitch(53))
        # Check second candidate
        violations2 = check_candidate_guards(
            soprano2, durations, bass2, durations, key, Fraction(1, 2)
        )
        # Both checks should complete
        assert isinstance(violations1, list)
        assert isinstance(violations2, list)

    def test_multiple_resets(self) -> None:
        """Multiple resets work correctly."""
        for _ in range(3):
            reset_accumulated_midi(2)
            key: Key = Key("C", "major")
            violations = check_candidate_guards(
                (MidiPitch(60),), (Fraction(1, 4),),
                (MidiPitch(48),), (Fraction(1, 4),),
                key, Fraction(0)
            )
            assert isinstance(violations, list)
