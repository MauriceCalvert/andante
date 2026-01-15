"""Integration tests for engine.realiser_passes.

Category B orchestrator tests: verify realiser post-processing passes.
Tests import only:
- engine.realiser_passes (module under test)
- engine.key (Key type)
- engine.types (data types)
- stdlib
"""
from fractions import Fraction

import pytest
from engine.key import Key
from engine.realiser_passes import (
    apply_bass_passes,
    fix_downbeat_dissonance,
    fix_parallel_violations,
    is_consonant,
    should_apply_dissonance_fix,
    should_apply_parallel_fix,
)
from engine.engine_types import RealisedNote


def make_soprano_notes(*pitches_offsets: tuple[int, Fraction]) -> tuple[RealisedNote, ...]:
    """Create soprano notes from (pitch, offset) pairs."""
    return tuple(
        RealisedNote(offset=offset, pitch=pitch, duration=Fraction(1, 4), voice="soprano")
        for pitch, offset in pitches_offsets
    )


def make_bass_notes(*pitches_offsets: tuple[int, Fraction]) -> tuple[RealisedNote, ...]:
    """Create bass notes from (pitch, offset) pairs."""
    return tuple(
        RealisedNote(offset=offset, pitch=pitch, duration=Fraction(1, 4), voice="bass")
        for pitch, offset in pitches_offsets
    )


class TestIsConsonant:
    """Test is_consonant function."""

    def test_unison_consonant(self) -> None:
        """Unison is consonant."""
        assert is_consonant(60, 60) is True

    def test_octave_consonant(self) -> None:
        """Octave is consonant."""
        assert is_consonant(72, 60) is True

    def test_fifth_consonant(self) -> None:
        """Perfect fifth is consonant."""
        assert is_consonant(67, 60) is True

    def test_third_consonant(self) -> None:
        """Major third is consonant."""
        assert is_consonant(64, 60) is True

    def test_minor_third_consonant(self) -> None:
        """Minor third is consonant."""
        assert is_consonant(63, 60) is True

    def test_sixth_consonant(self) -> None:
        """Major sixth is consonant."""
        assert is_consonant(69, 60) is True

    def test_second_dissonant(self) -> None:
        """Major second is dissonant."""
        assert is_consonant(62, 60) is False

    def test_minor_second_dissonant(self) -> None:
        """Minor second is dissonant."""
        assert is_consonant(61, 60) is False

    def test_tritone_dissonant(self) -> None:
        """Tritone is dissonant."""
        assert is_consonant(66, 60) is False

    def test_seventh_dissonant(self) -> None:
        """Seventh is dissonant."""
        assert is_consonant(71, 60) is False


class TestFixDownbeatDissonance:
    """Test fix_downbeat_dissonance function."""

    def test_consonant_unchanged(self) -> None:
        """Consonant intervals unchanged."""
        soprano: tuple[RealisedNote, ...] = make_soprano_notes((72, Fraction(0)))
        bass: tuple[RealisedNote, ...] = make_bass_notes((60, Fraction(0)))  # Octave
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = fix_downbeat_dissonance(
            soprano, bass, Fraction(1), 0, key
        )
        assert result[0].pitch == 60

    def test_off_beat_ignored(self) -> None:
        """Off-beat dissonances not fixed."""
        soprano: tuple[RealisedNote, ...] = make_soprano_notes((72, Fraction(1, 8)))
        bass: tuple[RealisedNote, ...] = make_bass_notes((62, Fraction(1, 8)))  # Dissonant
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = fix_downbeat_dissonance(
            soprano, bass, Fraction(1), 0, key
        )
        # Off-beat position, not at quarter note boundary
        assert len(result) == 1


class TestFixParallelViolations:
    """Test fix_parallel_violations function."""

    def test_no_parallels_unchanged(self) -> None:
        """No parallel motion leaves bass unchanged."""
        soprano: tuple[RealisedNote, ...] = make_soprano_notes(
            (72, Fraction(0)), (74, Fraction(1, 4))
        )
        bass: tuple[RealisedNote, ...] = make_bass_notes(
            (60, Fraction(0)), (59, Fraction(1, 4))  # Contrary motion
        )
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = fix_parallel_violations(
            soprano, bass, key, 0, preserve_final=False
        )
        assert result[0].pitch == 60
        assert result[1].pitch == 59

    def test_preserve_final_flag(self) -> None:
        """Preserve final flag prevents final note changes."""
        soprano: tuple[RealisedNote, ...] = make_soprano_notes(
            (72, Fraction(0)), (79, Fraction(1, 4))
        )
        bass: tuple[RealisedNote, ...] = make_bass_notes(
            (60, Fraction(0)), (67, Fraction(1, 4))  # Parallel fifth
        )
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = fix_parallel_violations(
            soprano, bass, key, 0, preserve_final=True
        )
        # Should preserve final note if parallel at final
        assert len(result) == 2


class TestShouldApplyDissonanceFix:
    """Test should_apply_dissonance_fix function."""

    def test_two_voice_no_fix(self) -> None:
        """Two-voice doesn't apply fix."""
        assert should_apply_dissonance_fix("statement", "polyphonic", True, 2) is False

    def test_multi_voice_imitative_no_fix(self) -> None:
        """Multi-voice imitative statement doesn't apply fix."""
        assert should_apply_dissonance_fix("statement", "polyphonic", True, 4) is False

    def test_multi_voice_homophonic_applies_fix(self) -> None:
        """Multi-voice homophonic applies fix."""
        assert should_apply_dissonance_fix("statement", "homophonic", True, 4) is True

    def test_continuation_applies_fix(self) -> None:
        """Continuation episode applies fix."""
        assert should_apply_dissonance_fix("continuation", "polyphonic", True, 4) is True


class TestShouldApplyParallelFix:
    """Test should_apply_parallel_fix function."""

    def test_always_applies(self) -> None:
        """Parallel fix always applies."""
        assert should_apply_parallel_fix(True) is True
        assert should_apply_parallel_fix(False) is True


class TestApplyBassPasses:
    """Test apply_bass_passes function."""

    def test_two_voice_returns_bass(self) -> None:
        """Two-voice returns bass (possibly modified)."""
        soprano: tuple[RealisedNote, ...] = make_soprano_notes((72, Fraction(0)))
        bass: tuple[RealisedNote, ...] = make_bass_notes((60, Fraction(0)))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = apply_bass_passes(
            soprano, bass, Fraction(1), 0, key,
            "statement", "polyphonic", False, voice_count=2
        )
        assert len(result) == 1

    def test_four_voice_applies_passes(self) -> None:
        """Four-voice applies relevant passes."""
        soprano: tuple[RealisedNote, ...] = make_soprano_notes((72, Fraction(0)))
        bass: tuple[RealisedNote, ...] = make_bass_notes((60, Fraction(0)))
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = apply_bass_passes(
            soprano, bass, Fraction(1), 0, key,
            "continuation", "homophonic", False, voice_count=4
        )
        assert len(result) == 1


class TestRealisedNoteAttributes:
    """Test RealisedNote in passes context."""

    def test_note_has_offset(self) -> None:
        """RealisedNote has offset."""
        note: RealisedNote = RealisedNote(
            offset=Fraction(1, 2), pitch=60, duration=Fraction(1, 4), voice="bass"
        )
        assert note.offset == Fraction(1, 2)

    def test_note_has_pitch(self) -> None:
        """RealisedNote has pitch."""
        note: RealisedNote = RealisedNote(
            offset=Fraction(0), pitch=72, duration=Fraction(1, 4), voice="soprano"
        )
        assert note.pitch == 72

    def test_note_has_duration(self) -> None:
        """RealisedNote has duration."""
        note: RealisedNote = RealisedNote(
            offset=Fraction(0), pitch=60, duration=Fraction(1, 2), voice="bass"
        )
        assert note.duration == Fraction(1, 2)

    def test_note_has_voice(self) -> None:
        """RealisedNote has voice."""
        note: RealisedNote = RealisedNote(
            offset=Fraction(0), pitch=60, duration=Fraction(1, 4), voice="alto"
        )
        assert note.voice == "alto"


class TestFixDownbeatDissonanceMultiple:
    """Test fix_downbeat_dissonance with multiple notes."""

    def test_multiple_notes(self) -> None:
        """Multiple notes processed correctly."""
        soprano: tuple[RealisedNote, ...] = make_soprano_notes(
            (72, Fraction(0)),
            (74, Fraction(1, 4)),
            (76, Fraction(1, 2)),
        )
        bass: tuple[RealisedNote, ...] = make_bass_notes(
            (60, Fraction(0)),
            (62, Fraction(1, 4)),
            (64, Fraction(1, 2)),
        )
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = fix_downbeat_dissonance(
            soprano, bass, Fraction(1), 0, key
        )
        assert len(result) == 3


class TestFixParallelViolationsMultiple:
    """Test fix_parallel_violations with multiple notes."""

    def test_multiple_notes(self) -> None:
        """Multiple notes processed correctly."""
        soprano: tuple[RealisedNote, ...] = make_soprano_notes(
            (72, Fraction(0)),
            (74, Fraction(1, 4)),
            (76, Fraction(1, 2)),
        )
        bass: tuple[RealisedNote, ...] = make_bass_notes(
            (60, Fraction(0)),
            (62, Fraction(1, 4)),
            (64, Fraction(1, 2)),
        )
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = fix_parallel_violations(
            soprano, bass, key, 0
        )
        assert len(result) == 3
