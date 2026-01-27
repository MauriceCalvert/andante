"""Comprehensive tests for builder/faults.py with 100% coverage target."""
import pytest
from fractions import Fraction

from builder.faults import (
    Fault,
    find_faults,
    print_faults,
    _bar_duration,
    _beat_duration,
    _extract_bar_pitches,
    _extract_bar_rhythm,
    _get_bar_count,
    _interval_semitones,
    _is_strong_beat,
    _midi_to_name,
    _motion_type,
    _offset_to_bar_beat,
    _simple_interval,
    _check_consecutive_leaps,
    _check_cross_relation,
    _check_direct_motion,
    _check_dissonance,
    _check_excessive_leaps,
    _check_melodic_repetition,
    _check_missing_contrary,
    _check_monotonous_contour,
    _check_parallel_imperfect,
    _check_parallel_perfect,
    _check_parallel_rhythm,
    _check_sequence_overuse,
    _check_spacing,
    _check_tessitura,
    _check_ugly_leaps,
    _check_unreversed_leap,
    _check_voice_crossing,
    _check_voice_overlap,
    _check_weak_cadence,
)
from builder.types import Note


# =============================================================================
# Helper function tests
# =============================================================================

class TestHelperFunctions:
    """Tests for utility functions."""

    def test_bar_duration_4_4(self) -> None:
        assert _bar_duration("4/4") == Fraction(1)

    def test_bar_duration_3_4(self) -> None:
        assert _bar_duration("3/4") == Fraction(3, 4)

    def test_bar_duration_6_8(self) -> None:
        assert _bar_duration("6/8") == Fraction(6, 8)

    def test_beat_duration_4_4(self) -> None:
        assert _beat_duration("4/4") == Fraction(1, 4)

    def test_beat_duration_3_4(self) -> None:
        assert _beat_duration("3/4") == Fraction(1, 4)

    def test_beat_duration_6_8(self) -> None:
        assert _beat_duration("6/8") == Fraction(1, 8)

    def test_interval_semitones(self) -> None:
        assert _interval_semitones(60, 67) == 7
        assert _interval_semitones(67, 60) == -7

    def test_simple_interval(self) -> None:
        assert _simple_interval(60, 67) == 7
        assert _simple_interval(60, 72) == 0
        assert _simple_interval(60, 84) == 0

    def test_midi_to_name(self) -> None:
        assert _midi_to_name(60) == "C4"
        assert _midi_to_name(69) == "A4"
        assert _midi_to_name(48) == "C3"
        assert _midi_to_name(61) == "C#4"

    def test_offset_to_bar_beat_4_4(self) -> None:
        assert _offset_to_bar_beat(Fraction(0), "4/4") == "1.1"
        assert _offset_to_bar_beat(Fraction(1, 4), "4/4") == "1.2"
        assert _offset_to_bar_beat(Fraction(1, 2), "4/4") == "1.3"
        assert _offset_to_bar_beat(Fraction(3, 4), "4/4") == "1.4"
        assert _offset_to_bar_beat(Fraction(1), "4/4") == "2.1"

    def test_offset_to_bar_beat_3_4(self) -> None:
        assert _offset_to_bar_beat(Fraction(0), "3/4") == "1.1"
        assert _offset_to_bar_beat(Fraction(3, 4), "3/4") == "2.1"

    def test_is_strong_beat_4_4(self) -> None:
        assert _is_strong_beat(Fraction(0), "4/4") is True
        assert _is_strong_beat(Fraction(1, 4), "4/4") is False
        assert _is_strong_beat(Fraction(1, 2), "4/4") is True
        assert _is_strong_beat(Fraction(3, 4), "4/4") is False

    def test_is_strong_beat_3_4(self) -> None:
        assert _is_strong_beat(Fraction(0), "3/4") is True
        assert _is_strong_beat(Fraction(1, 4), "3/4") is False
        assert _is_strong_beat(Fraction(1, 2), "3/4") is False

    def test_motion_type_similar(self) -> None:
        assert _motion_type(60, 62, 48, 50) == "similar"

    def test_motion_type_contrary(self) -> None:
        assert _motion_type(60, 62, 48, 46) == "contrary"

    def test_motion_type_oblique(self) -> None:
        assert _motion_type(60, 60, 48, 50) == "oblique"
        assert _motion_type(60, 62, 48, 48) == "oblique"

    def test_motion_type_static(self) -> None:
        assert _motion_type(60, 60, 48, 48) == "static"

    def test_get_bar_count(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1), 62, Fraction(1, 4), 0),
        ]
        assert _get_bar_count(notes, "4/4") == 2

    def test_get_bar_count_empty(self) -> None:
        assert _get_bar_count([], "4/4") == 0

    def test_extract_bar_pitches(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
            Note(Fraction(1), 64, Fraction(1, 4), 0),
        ]
        assert _extract_bar_pitches(notes, 1, "4/4") == [60, 62]
        assert _extract_bar_pitches(notes, 2, "4/4") == [64]

    def test_extract_bar_rhythm(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 2), 0),
        ]
        assert _extract_bar_rhythm(notes, 1, "4/4") == (Fraction(1, 4), Fraction(1, 2))


# =============================================================================
# Error category tests
# =============================================================================

class TestParallelPerfect:
    """Tests for parallel fifths, octaves, unisons."""

    def test_parallel_octaves_detected(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 50, Fraction(1, 4), 1),
        ]
        faults = _check_parallel_perfect([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "parallel_octave"
        assert faults[0].severity == "error"

    def test_parallel_fifths_detected(self) -> None:
        soprano = [
            Note(Fraction(0), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 69, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 60, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 1),
        ]
        faults = _check_parallel_perfect([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "parallel_fifth"

    def test_parallel_unisons_detected(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 60, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 1),
        ]
        faults = _check_parallel_perfect([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "parallel_unison"

    def test_contrary_motion_no_parallels(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 46, Fraction(1, 4), 1),
        ]
        faults = _check_parallel_perfect([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_single_voice_no_parallels(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        faults = _check_parallel_perfect([soprano], "4/4")
        assert len(faults) == 0

    def test_static_voices_no_parallels(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 60, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 48, Fraction(1, 4), 1),
        ]
        faults = _check_parallel_perfect([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_parallel_octaves_at_final_cadence_exempt(self) -> None:
        """Parallel octaves approaching final note should be permitted."""
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 50, Fraction(1, 4), 1),
        ]
        faults = _check_parallel_perfect([soprano, bass], "4/4")
        assert len(faults) == 0


class TestDirectMotion:
    """Tests for direct fifths/octaves."""

    def test_direct_fifth_with_soprano_leap(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 60, Fraction(1, 4), 1),
        ]
        faults = _check_direct_motion([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "direct_fifth"

    def test_direct_octave_with_soprano_leap(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 72, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 60, Fraction(1, 4), 1),
        ]
        faults = _check_direct_motion([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "direct_octave"

    def test_soprano_step_allowed(self) -> None:
        soprano = [
            Note(Fraction(0), 65, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 53, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 60, Fraction(1, 4), 1),
        ]
        faults = _check_direct_motion([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_contrary_motion_allowed(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 55, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 48, Fraction(1, 4), 1),
        ]
        faults = _check_direct_motion([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_single_voice_no_direct_motion(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        faults = _check_direct_motion([soprano], "4/4")
        assert len(faults) == 0


class TestDissonance:
    """Tests for dissonance preparation and resolution."""

    def test_unprepared_dissonance(self) -> None:
        soprano = [
            Note(Fraction(0), 61, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
        ]
        faults = _check_dissonance([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "unprepared_dissonance"

    def test_prepared_but_unresolved(self) -> None:
        soprano = [
            Note(Fraction(0), 61, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 61, Fraction(1, 4), 0),
            Note(Fraction(3, 4), 65, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 55, Fraction(1, 4), 1),
            Note(Fraction(1, 2), 48, Fraction(1, 4), 1),
            Note(Fraction(3, 4), 48, Fraction(1, 4), 1),
        ]
        faults = _check_dissonance([soprano, bass], "4/4")
        unresolved = [f for f in faults if f.category == "unresolved_dissonance"]
        assert len(unresolved) >= 1

    def test_consonance_no_fault(self) -> None:
        soprano = [
            Note(Fraction(0), 64, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
        ]
        faults = _check_dissonance([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_weak_beat_dissonance_allowed(self) -> None:
        soprano = [
            Note(Fraction(1, 4), 61, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(1, 4), 48, Fraction(1, 4), 1),
        ]
        faults = _check_dissonance([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_single_voice_no_dissonance_check(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        faults = _check_dissonance([soprano], "4/4")
        assert len(faults) == 0


# =============================================================================
# Warning category tests
# =============================================================================

class TestUglyLeaps:
    """Tests for augmented/diminished intervals."""

    def test_tritone_leap(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 66, Fraction(1, 4), 0),
        ]
        faults = _check_ugly_leaps(notes, 0, "4/4")
        assert len(faults) == 1
        assert "tritone" in faults[0].message

    def test_major_seventh_leap(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 71, Fraction(1, 4), 0),
        ]
        faults = _check_ugly_leaps(notes, 0, "4/4")
        assert len(faults) == 1
        assert "seventh" in faults[0].message.lower()

    def test_minor_seventh_leap(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 70, Fraction(1, 4), 0),
        ]
        faults = _check_ugly_leaps(notes, 0, "4/4")
        assert len(faults) == 1

    def test_augmented_octave_leap(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 73, Fraction(1, 4), 0),
        ]
        faults = _check_ugly_leaps(notes, 0, "4/4")
        assert len(faults) == 1
        assert "augmented octave" in faults[0].message

    def test_minor_ninth_leap(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 73, Fraction(1, 4), 0),
        ]
        faults = _check_ugly_leaps(notes, 0, "4/4")
        assert len(faults) == 1

    def test_step_no_fault(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
        ]
        faults = _check_ugly_leaps(notes, 0, "4/4")
        assert len(faults) == 0

    def test_perfect_fifth_no_fault(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
        ]
        faults = _check_ugly_leaps(notes, 0, "4/4")
        assert len(faults) == 0


class TestConsecutiveLeaps:
    """Tests for two leaps in same direction."""

    def test_two_leaps_up(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 74, Fraction(1, 4), 0),
        ]
        faults = _check_consecutive_leaps(notes, 0, "4/4")
        assert len(faults) == 1
        assert faults[0].category == "consecutive_leaps"

    def test_leap_then_step(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 65, Fraction(1, 4), 0),
        ]
        faults = _check_consecutive_leaps(notes, 0, "4/4")
        assert len(faults) == 0

    def test_leaps_opposite_directions(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 60, Fraction(1, 4), 0),
        ]
        faults = _check_consecutive_leaps(notes, 0, "4/4")
        assert len(faults) == 0


class TestUnreversedLeap:
    """Tests for leap recovery. Only applies to soprano (voice 0)."""

    def test_leap_not_recovered(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 69, Fraction(1, 4), 0),
        ]
        faults = _check_unreversed_leap(notes, 0, "4/4")
        assert len(faults) == 1
        assert faults[0].category == "unreversed_leap"

    def test_leap_recovered_by_step(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 65, Fraction(1, 4), 0),
        ]
        faults = _check_unreversed_leap(notes, 0, "4/4")
        assert len(faults) == 0

    def test_skip_not_leap(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 64, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 67, Fraction(1, 4), 0),
        ]
        faults = _check_unreversed_leap(notes, 0, "4/4")
        assert len(faults) == 0

    def test_bass_leaps_not_checked_in_find_faults(self) -> None:
        """Bass voice should not have unreversed_leap check in find_faults."""
        soprano = [
            Note(Fraction(0), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 69, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 71, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 40, Fraction(1, 4), 1),
            Note(Fraction(1, 2), 45, Fraction(1, 4), 1),
        ]
        faults = find_faults([soprano, bass], "4/4")
        unreversed = [f for f in faults if f.category == "unreversed_leap"]
        bass_unreversed = [f for f in unreversed if 1 in f.voices]
        assert len(bass_unreversed) == 0


class TestTessitura:
    """Tests for tessitura excursions using fixed voice ranges."""

    def test_soprano_below_range(self) -> None:
        """Soprano below C4 (60) should trigger fault."""
        notes = [Note(Fraction(0), 55, Fraction(1, 4), 0)]
        faults = _check_tessitura(notes, 0, "4/4", voice_count=2)
        assert len(faults) == 1
        assert faults[0].category == "tessitura_excursion"
        assert "below" in faults[0].message

    def test_soprano_above_range(self) -> None:
        """Soprano above A5 (81) should trigger fault."""
        notes = [Note(Fraction(0), 85, Fraction(1, 4), 0)]
        faults = _check_tessitura(notes, 0, "4/4", voice_count=2)
        assert len(faults) == 1
        assert faults[0].category == "tessitura_excursion"
        assert "above" in faults[0].message

    def test_soprano_within_range(self) -> None:
        """Soprano within C4-A5 should be fine."""
        notes = [Note(Fraction(0), 70, Fraction(1, 4), 0)]
        faults = _check_tessitura(notes, 0, "4/4", voice_count=2)
        assert len(faults) == 0

    def test_bass_below_range(self) -> None:
        """Bass below E2 (40) should trigger fault."""
        notes = [Note(Fraction(0), 35, Fraction(1, 4), 1)]
        faults = _check_tessitura(notes, 1, "4/4", voice_count=2)
        assert len(faults) == 1
        assert "below" in faults[0].message

    def test_bass_within_range(self) -> None:
        """Bass within E2-D4 should be fine."""
        notes = [Note(Fraction(0), 50, Fraction(1, 4), 1)]
        faults = _check_tessitura(notes, 1, "4/4", voice_count=2)
        assert len(faults) == 0


class TestVoiceCrossing:
    """Tests for persistent voice crossing."""

    def test_persistent_crossing(self) -> None:
        soprano = [
            Note(Fraction(i, 4), 50, Fraction(1, 4), 0) for i in range(5)
        ]
        bass = [
            Note(Fraction(i, 4), 60, Fraction(1, 4), 1) for i in range(5)
        ]
        faults = _check_voice_crossing([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "voice_crossing"

    def test_brief_crossing_allowed(self) -> None:
        soprano = [
            Note(Fraction(0), 50, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 50, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 65, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 60, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 60, Fraction(1, 4), 1),
            Note(Fraction(1, 2), 48, Fraction(1, 4), 1),
        ]
        faults = _check_voice_crossing([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_single_voice_no_crossing(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        faults = _check_voice_crossing([soprano], "4/4")
        assert len(faults) == 0

    def test_single_voice_no_overlap(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        faults = _check_voice_overlap([soprano], "4/4")
        assert len(faults) == 0


class TestVoiceOverlap:
    """Tests for voice overlap."""

    def test_overlap_detected(self) -> None:
        soprano = [
            Note(Fraction(0), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 60, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 60, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 55, Fraction(1, 4), 1),
        ]
        faults = _check_voice_overlap([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "voice_overlap"

    def test_no_overlap(self) -> None:
        soprano = [
            Note(Fraction(0), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 65, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 50, Fraction(1, 4), 1),
        ]
        faults = _check_voice_overlap([soprano, bass], "4/4")
        assert len(faults) == 0


class TestCrossRelation:
    """Tests for chromatic contradictions."""

    def test_cross_relation_detected(self) -> None:
        soprano = [
            Note(Fraction(0), 66, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(1, 4), 65, Fraction(1, 4), 1),
        ]
        faults = _check_cross_relation([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "cross_relation"

    def test_no_cross_relation(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(1, 4), 48, Fraction(1, 4), 1),
        ]
        faults = _check_cross_relation([soprano, bass], "4/4")
        assert len(faults) == 0


class TestSpacing:
    """Tests for voice spacing errors. Disabled for 2-voice texture."""

    def test_spacing_skipped_for_two_voices(self) -> None:
        """Two-voice texture should not check spacing."""
        soprano = [Note(Fraction(0), 84, Fraction(1, 4), 0)]
        bass = [Note(Fraction(0), 48, Fraction(1, 4), 1)]
        faults = _check_spacing([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_spacing_too_wide_three_voices(self) -> None:
        """Three voices should check spacing."""
        soprano = [Note(Fraction(0), 84, Fraction(1, 4), 0)]
        alto = [Note(Fraction(0), 55, Fraction(1, 4), 1)]
        bass = [Note(Fraction(0), 48, Fraction(1, 4), 2)]
        faults = _check_spacing([soprano, alto, bass], "4/4")
        assert len(faults) >= 1
        assert faults[0].category == "spacing_error"

    def test_spacing_ok_three_voices(self) -> None:
        soprano = [Note(Fraction(0), 72, Fraction(1, 4), 0)]
        alto = [Note(Fraction(0), 64, Fraction(1, 4), 1)]
        bass = [Note(Fraction(0), 48, Fraction(1, 4), 2)]
        faults = _check_spacing([soprano, alto, bass], "4/4")
        assert len(faults) == 0

    def test_single_voice_no_spacing(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        faults = _check_spacing([soprano], "4/4")
        assert len(faults) == 0


# =============================================================================
# Info category tests
# =============================================================================

class TestParallelRhythm:
    """Tests for homorhythmic passages."""

    def test_homorhythm_detected(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 64, Fraction(1, 4), 0),
            Note(Fraction(3, 4), 65, Fraction(1, 4), 0),
            Note(Fraction(1), 67, Fraction(1, 4), 0),
            Note(Fraction(5, 4), 69, Fraction(1, 4), 0),
            Note(Fraction(3, 2), 71, Fraction(1, 4), 0),
            Note(Fraction(7, 4), 72, Fraction(1, 4), 0),
            Note(Fraction(2), 74, Fraction(1, 4), 0),
            Note(Fraction(9, 4), 76, Fraction(1, 4), 0),
            Note(Fraction(5, 2), 77, Fraction(1, 4), 0),
            Note(Fraction(11, 4), 79, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 50, Fraction(1, 4), 1),
            Note(Fraction(1, 2), 52, Fraction(1, 4), 1),
            Note(Fraction(3, 4), 53, Fraction(1, 4), 1),
            Note(Fraction(1), 55, Fraction(1, 4), 1),
            Note(Fraction(5, 4), 57, Fraction(1, 4), 1),
            Note(Fraction(3, 2), 59, Fraction(1, 4), 1),
            Note(Fraction(7, 4), 60, Fraction(1, 4), 1),
            Note(Fraction(2), 62, Fraction(1, 4), 1),
            Note(Fraction(9, 4), 64, Fraction(1, 4), 1),
            Note(Fraction(5, 2), 65, Fraction(1, 4), 1),
            Note(Fraction(11, 4), 67, Fraction(1, 4), 1),
        ]
        faults = _check_parallel_rhythm([soprano, bass], "4/4")
        assert len(faults) >= 1
        assert faults[0].category == "parallel_rhythm"

    def test_varied_rhythm_ok(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 2), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 2), 1),
            Note(Fraction(1, 2), 50, Fraction(1, 4), 1),
        ]
        faults = _check_parallel_rhythm([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_single_voice_no_parallel_rhythm(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        faults = _check_parallel_rhythm([soprano], "4/4")
        assert len(faults) == 0


class TestParallelImperfect:
    """Tests for extended parallel thirds/sixths."""

    def test_parallel_thirds_detected(self) -> None:
        soprano = [Note(Fraction(i, 4), 64 + i, Fraction(1, 4), 0) for i in range(6)]
        bass = [Note(Fraction(i, 4), 60 + i, Fraction(1, 4), 1) for i in range(6)]
        faults = _check_parallel_imperfect([soprano, bass], "4/4")
        thirds = [f for f in faults if f.category == "parallel_thirds"]
        assert len(thirds) >= 1

    def test_parallel_sixths_detected(self) -> None:
        soprano = [Note(Fraction(i, 4), 69 + i, Fraction(1, 4), 0) for i in range(6)]
        bass = [Note(Fraction(i, 4), 60 + i, Fraction(1, 4), 1) for i in range(6)]
        faults = _check_parallel_imperfect([soprano, bass], "4/4")
        sixths = [f for f in faults if f.category == "parallel_sixths"]
        assert len(sixths) >= 1

    def test_varied_intervals_ok(self) -> None:
        soprano = [
            Note(Fraction(0), 64, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 60, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 60, Fraction(1, 4), 1),
        ]
        faults = _check_parallel_imperfect([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_single_voice_no_parallel_imperfect(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        faults = _check_parallel_imperfect([soprano], "4/4")
        assert len(faults) == 0


class TestMelodicRepetition:
    """Tests for literal bar repetition."""

    def test_repetition_detected(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
            Note(Fraction(1), 60, Fraction(1, 4), 0),
            Note(Fraction(5, 4), 62, Fraction(1, 4), 0),
        ]
        faults = _check_melodic_repetition(notes, 0, "4/4")
        assert len(faults) == 1
        assert faults[0].category == "melodic_repetition"

    def test_varied_bars_ok(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1), 64, Fraction(1, 4), 0),
        ]
        faults = _check_melodic_repetition(notes, 0, "4/4")
        assert len(faults) == 0


class TestSequenceOveruse:
    """Tests for excessive sequence repetition."""

    def test_sequence_overuse_detected(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 62, Fraction(1, 4), 0),
            Note(Fraction(3, 4), 64, Fraction(1, 4), 0),
            Note(Fraction(1), 64, Fraction(1, 4), 0),
            Note(Fraction(5, 4), 66, Fraction(1, 4), 0),
            Note(Fraction(3, 2), 66, Fraction(1, 4), 0),
            Note(Fraction(7, 4), 68, Fraction(1, 4), 0),
        ]
        faults = _check_sequence_overuse(notes, 0, "4/4")
        assert len(faults) >= 1
        assert faults[0].category == "sequence_overuse"

    def test_short_sequence_ok(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 64, Fraction(1, 4), 0),
        ]
        faults = _check_sequence_overuse(notes, 0, "4/4")
        assert len(faults) == 0


class TestMonotonousContour:
    """Tests for excessive stepwise motion."""

    def test_monotonous_detected(self) -> None:
        notes = [Note(Fraction(i, 4), 60 + i, Fraction(1, 4), 0) for i in range(8)]
        faults = _check_monotonous_contour(notes, 0, "4/4")
        assert len(faults) >= 1
        assert faults[0].category == "monotonous_contour"

    def test_varied_contour_ok(self) -> None:
        notes = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 65, Fraction(1, 4), 0),
        ]
        faults = _check_monotonous_contour(notes, 0, "4/4")
        assert len(faults) == 0


class TestExcessiveLeaps:
    """Tests for high leap ratio."""

    def test_excessive_leaps_detected(self) -> None:
        notes = [Note(Fraction(i, 4), 60 + (i * 7) % 24, Fraction(1, 4), 0) for i in range(12)]
        faults = _check_excessive_leaps(notes, 0, "4/4")
        assert len(faults) >= 1
        assert faults[0].category == "excessive_leaps"

    def test_stepwise_ok(self) -> None:
        notes = [Note(Fraction(i, 4), 60 + i, Fraction(1, 4), 0) for i in range(12)]
        faults = _check_excessive_leaps(notes, 0, "4/4")
        assert len(faults) == 0

    def test_short_melody_no_check(self) -> None:
        notes = [Note(Fraction(i, 4), 60 + i * 7, Fraction(1, 4), 0) for i in range(5)]
        faults = _check_excessive_leaps(notes, 0, "4/4")
        assert len(faults) == 0


class TestWeakCadence:
    """Tests for improper cadence."""

    def test_weak_cadence_detected(self) -> None:
        soprano = [Note(Fraction(0), 64, Fraction(1, 4), 0)]
        bass = [Note(Fraction(0), 48, Fraction(1, 4), 1)]
        faults = _check_weak_cadence([soprano, bass], "4/4")
        assert len(faults) == 1
        assert faults[0].category == "weak_cadence"

    def test_octave_cadence_ok(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        bass = [Note(Fraction(0), 48, Fraction(1, 4), 1)]
        faults = _check_weak_cadence([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_fifth_cadence_ok(self) -> None:
        soprano = [Note(Fraction(0), 67, Fraction(1, 4), 0)]
        bass = [Note(Fraction(0), 48, Fraction(1, 4), 1)]
        faults = _check_weak_cadence([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_unison_cadence_ok(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        bass = [Note(Fraction(0), 60, Fraction(1, 4), 1)]
        faults = _check_weak_cadence([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_empty_voices_no_fault(self) -> None:
        faults = _check_weak_cadence([[], []], "4/4")
        assert len(faults) == 0


class TestMissingContrary:
    """Tests for missing contrary motion."""

    def test_missing_contrary_detected(self) -> None:
        soprano = [Note(Fraction(i, 4), 60 + i, Fraction(1, 4), 0) for i in range(10)]
        bass = [Note(Fraction(i, 4), 48 + i, Fraction(1, 4), 1) for i in range(10)]
        faults = _check_missing_contrary([soprano, bass], "4/4")
        assert len(faults) >= 1
        assert faults[0].category == "missing_contrary_motion"

    def test_contrary_motion_present(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 46, Fraction(1, 4), 1),
        ]
        faults = _check_missing_contrary([soprano, bass], "4/4")
        assert len(faults) == 0

    def test_single_voice_no_missing_contrary(self) -> None:
        soprano = [Note(Fraction(0), 60, Fraction(1, 4), 0)]
        faults = _check_missing_contrary([soprano], "4/4")
        assert len(faults) == 0


# =============================================================================
# Integration tests
# =============================================================================

class TestFindFaults:
    """Integration tests for find_faults."""

    def test_valid_inputs(self) -> None:
        soprano = [Note(Fraction(0), 67, Fraction(1, 4), 0)]
        bass = [Note(Fraction(0), 48, Fraction(1, 4), 1)]
        faults = find_faults([soprano, bass], "4/4")
        assert isinstance(faults, list)

    def test_tessitura_with_fixed_ranges(self) -> None:
        """Pitches within standard ranges should have no tessitura faults."""
        soprano = [Note(Fraction(0), 70, Fraction(1, 4), 0)]
        bass = [Note(Fraction(0), 50, Fraction(1, 4), 1)]
        faults = find_faults([soprano, bass], "4/4")
        tess_faults = [f for f in faults if f.category == "tessitura_excursion"]
        assert len(tess_faults) == 0

    def test_invalid_voice_count_low(self) -> None:
        with pytest.raises(AssertionError):
            find_faults([], "4/4")

    def test_invalid_voice_count_high(self) -> None:
        with pytest.raises(AssertionError):
            find_faults([[], [], [], [], []], "4/4")

    def test_invalid_metre(self) -> None:
        with pytest.raises(AssertionError):
            find_faults([[]], "invalid")

    def test_faults_sorted_by_severity(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 62, Fraction(1, 4), 0),
        ]
        bass = [
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 4), 50, Fraction(1, 4), 1),
        ]
        faults = find_faults([soprano, bass], "4/4")
        severities = [f.severity for f in faults]
        error_indices = [i for i, s in enumerate(severities) if s == "error"]
        warning_indices = [i for i, s in enumerate(severities) if s == "warning"]
        info_indices = [i for i, s in enumerate(severities) if s == "info"]
        if error_indices and warning_indices:
            assert max(error_indices) < min(warning_indices)
        if warning_indices and info_indices:
            assert max(warning_indices) < min(info_indices)


class TestPrintFaults:
    """Tests for print_faults."""

    def test_print_no_faults(self, capsys) -> None:
        print_faults([])
        captured = capsys.readouterr()
        assert "No faults found" in captured.out

    def test_print_with_faults(self, capsys) -> None:
        faults = [
            Fault("error", "parallel_fifth", "1.2", (0, 1), "Test message"),
            Fault("warning", "ugly_leap", "1.3", (0,), "Another message"),
        ]
        print_faults(faults)
        captured = capsys.readouterr()
        assert "[ERROR]" in captured.out
        assert "[WARNING]" in captured.out
        assert "parallel_fifth" in captured.out
        assert "1 errors" in captured.out
        assert "1 warnings" in captured.out


class TestMultipleVoices:
    """Tests for 3 and 4 voice scenarios."""

    def test_three_voices(self) -> None:
        soprano = [Note(Fraction(0), 72, Fraction(1, 4), 0)]
        alto = [Note(Fraction(0), 64, Fraction(1, 4), 1)]
        bass = [Note(Fraction(0), 48, Fraction(1, 4), 2)]
        faults = find_faults([soprano, alto, bass], "4/4")
        assert isinstance(faults, list)

    def test_four_voices(self) -> None:
        soprano = [Note(Fraction(0), 72, Fraction(1, 4), 0)]
        alto = [Note(Fraction(0), 67, Fraction(1, 4), 1)]
        tenor = [Note(Fraction(0), 60, Fraction(1, 4), 2)]
        bass = [Note(Fraction(0), 48, Fraction(1, 4), 3)]
        faults = find_faults([soprano, alto, tenor, bass], "4/4")
        assert isinstance(faults, list)

    def test_single_voice(self) -> None:
        soprano = [
            Note(Fraction(0), 60, Fraction(1, 4), 0),
            Note(Fraction(1, 4), 66, Fraction(1, 4), 0),
        ]
        faults = find_faults([soprano], "4/4")
        ugly = [f for f in faults if f.category == "ugly_leap"]
        assert len(ugly) == 1
