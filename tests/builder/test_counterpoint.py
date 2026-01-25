"""Tests for builder.counterpoint module.

Category A tests: Pure functions, no mocks, specification-based.

Specification source: architecture.md
- Consonant intervals: P1, m3, M3, P5, m6, M6, P8 (and compounds)
- Parallel P5/P8/P1 forbidden when both voices move in same direction
- Voice ranges: soprano C4-G5 (60-79), bass C2-C4 (36-60)
- Diatonic pitch-class set: {0,2,4,5,7,9,11} for C major
"""
from fractions import Fraction

import pytest

from builder.counterpoint import (
    check_parallels,
    check_pitch_class,
    check_voice_range,
    interval_class,
    is_consonant,
    is_perfect,
    is_strong_beat,
    validate_passage,
)
from builder.types import Note


class TestIntervalClass:
    """Tests for interval_class function."""

    def test_unison(self) -> None:
        assert interval_class(60, 60) == 0

    def test_octave(self) -> None:
        assert interval_class(72, 60) == 0

    def test_fifth(self) -> None:
        assert interval_class(67, 60) == 7

    def test_fifth_compound(self) -> None:
        assert interval_class(79, 60) == 7

    def test_third_major(self) -> None:
        assert interval_class(64, 60) == 4

    def test_third_minor(self) -> None:
        assert interval_class(63, 60) == 3

    def test_tritone(self) -> None:
        assert interval_class(66, 60) == 6

    def test_bass_above_soprano(self) -> None:
        assert interval_class(60, 67) == 7


class TestIsConsonant:
    """Tests for is_consonant function."""

    def test_unison_consonant(self) -> None:
        assert is_consonant(60, 60)

    def test_octave_consonant(self) -> None:
        assert is_consonant(72, 60)

    def test_fifth_consonant(self) -> None:
        assert is_consonant(67, 60)

    def test_major_third_consonant(self) -> None:
        assert is_consonant(64, 60)

    def test_minor_third_consonant(self) -> None:
        assert is_consonant(63, 60)

    def test_major_sixth_consonant(self) -> None:
        assert is_consonant(69, 60)

    def test_minor_sixth_consonant(self) -> None:
        assert is_consonant(68, 60)

    def test_second_dissonant(self) -> None:
        assert not is_consonant(62, 60)

    def test_tritone_dissonant(self) -> None:
        assert not is_consonant(66, 60)

    def test_seventh_dissonant(self) -> None:
        assert not is_consonant(71, 60)


class TestIsPerfect:
    """Tests for is_perfect function."""

    def test_unison_perfect(self) -> None:
        assert is_perfect(60, 60)

    def test_fifth_perfect(self) -> None:
        assert is_perfect(67, 60)

    def test_octave_perfect(self) -> None:
        assert is_perfect(72, 60)

    def test_third_not_perfect(self) -> None:
        assert not is_perfect(64, 60)

    def test_sixth_not_perfect(self) -> None:
        assert not is_perfect(69, 60)


class TestCheckParallels:
    """Tests for parallel motion detection."""

    def test_parallel_fifths_forbidden(self) -> None:
        assert not check_parallels(67, 60, 69, 62)

    def test_parallel_octaves_forbidden(self) -> None:
        assert not check_parallels(72, 60, 74, 62)

    def test_parallel_unisons_forbidden(self) -> None:
        assert not check_parallels(60, 60, 62, 62)

    def test_contrary_motion_to_fifth_ok(self) -> None:
        assert check_parallels(64, 60, 67, 55)

    def test_oblique_motion_ok(self) -> None:
        assert check_parallels(67, 60, 69, 60)

    def test_similar_motion_to_imperfect_ok(self) -> None:
        assert check_parallels(64, 60, 67, 64)

    def test_parallel_thirds_ok(self) -> None:
        assert check_parallels(64, 60, 66, 62)

    def test_same_pitch_no_motion(self) -> None:
        assert check_parallels(60, 48, 60, 48)


class TestCheckVoiceRange:
    """Tests for voice range constraints."""

    def test_soprano_in_range(self) -> None:
        registers: dict[str, tuple[int, int]] = {"soprano": (60, 79), "bass": (36, 60)}
        assert check_voice_range(60, "soprano", registers)
        assert check_voice_range(72, "soprano", registers)
        assert check_voice_range(79, "soprano", registers)

    def test_soprano_out_of_range_low(self) -> None:
        registers: dict[str, tuple[int, int]] = {"soprano": (60, 79), "bass": (36, 60)}
        assert not check_voice_range(59, "soprano", registers)

    def test_soprano_out_of_range_high(self) -> None:
        registers: dict[str, tuple[int, int]] = {"soprano": (60, 79), "bass": (36, 60)}
        assert not check_voice_range(80, "soprano", registers)

    def test_bass_in_range(self) -> None:
        registers: dict[str, tuple[int, int]] = {"soprano": (60, 79), "bass": (36, 60)}
        assert check_voice_range(48, "bass", registers)
        assert check_voice_range(36, "bass", registers)
        assert check_voice_range(60, "bass", registers)

    def test_bass_out_of_range(self) -> None:
        registers: dict[str, tuple[int, int]] = {"soprano": (60, 79), "bass": (36, 60)}
        assert not check_voice_range(35, "bass", registers)
        assert not check_voice_range(61, "bass", registers)

    def test_unknown_voice_ok(self) -> None:
        registers: dict[str, tuple[int, int]] = {"soprano": (60, 79)}
        assert check_voice_range(30, "tenor", registers)


class TestCheckPitchClass:
    """Tests for diatonic pitch-class membership."""

    def test_c_major_pitches(self) -> None:
        c_major: frozenset[int] = frozenset({0, 2, 4, 5, 7, 9, 11})
        assert check_pitch_class(60, c_major)
        assert check_pitch_class(62, c_major)
        assert check_pitch_class(64, c_major)
        assert check_pitch_class(65, c_major)
        assert check_pitch_class(67, c_major)
        assert check_pitch_class(69, c_major)
        assert check_pitch_class(71, c_major)

    def test_chromatic_pitch_rejected(self) -> None:
        c_major: frozenset[int] = frozenset({0, 2, 4, 5, 7, 9, 11})
        assert not check_pitch_class(61, c_major)
        assert not check_pitch_class(63, c_major)
        assert not check_pitch_class(66, c_major)
        assert not check_pitch_class(68, c_major)
        assert not check_pitch_class(70, c_major)

    def test_octave_equivalence(self) -> None:
        c_major: frozenset[int] = frozenset({0, 2, 4, 5, 7, 9, 11})
        assert check_pitch_class(48, c_major)
        assert check_pitch_class(84, c_major)


class TestIsStrongBeat:
    """Tests for strong beat detection.
    
    In 4/4: strong beats at offset 0 (beat 1) and 1/2 (beat 3)
    In 3/4: strong beat at offset 0 (beat 1) only
    """

    def test_4_4_beat_1_strong(self) -> None:
        assert is_strong_beat(Fraction(0), "4/4")

    def test_4_4_beat_3_strong(self) -> None:
        assert is_strong_beat(Fraction(1, 2), "4/4")

    def test_4_4_beat_2_weak(self) -> None:
        assert not is_strong_beat(Fraction(1, 4), "4/4")

    def test_4_4_beat_4_weak(self) -> None:
        assert not is_strong_beat(Fraction(3, 4), "4/4")

    def test_4_4_bar_2_beat_1(self) -> None:
        assert is_strong_beat(Fraction(1), "4/4")

    def test_4_4_bar_2_beat_3(self) -> None:
        assert is_strong_beat(Fraction(3, 2), "4/4")

    def test_3_4_beat_1_strong(self) -> None:
        assert is_strong_beat(Fraction(0), "3/4")

    def test_3_4_beat_2_weak(self) -> None:
        assert not is_strong_beat(Fraction(1, 4), "3/4")

    def test_3_4_beat_3_weak(self) -> None:
        assert not is_strong_beat(Fraction(1, 2), "3/4")


class TestValidatePassage:
    """Integration tests for validate_passage."""

    def test_valid_passage_no_violations(self) -> None:
        soprano: tuple[Note, ...] = (
            Note(Fraction(0), 64, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 67, Fraction(1, 4), 0),
        )
        bass: tuple[Note, ...] = (
            Note(Fraction(0), 48, Fraction(1, 4), 1),
            Note(Fraction(1, 2), 48, Fraction(1, 4), 1),
        )
        violations = validate_passage(
            soprano,
            bass,
            frozenset({0, 2, 4, 5, 7, 9, 11}),
            {"soprano": (60, 79), "bass": (36, 60)},
            "4/4",
        )
        assert len(violations) == 0

    def test_chromatic_pitch_violation(self) -> None:
        soprano: tuple[Note, ...] = (Note(Fraction(0), 61, Fraction(1, 4), 0),)
        bass: tuple[Note, ...] = (Note(Fraction(0), 48, Fraction(1, 4), 1),)
        violations = validate_passage(
            soprano,
            bass,
            frozenset({0, 2, 4, 5, 7, 9, 11}),
            {"soprano": (60, 79), "bass": (36, 60)},
            "4/4",
        )
        assert any(v.rule == "pitch_class" for v in violations)

    def test_range_violation(self) -> None:
        soprano: tuple[Note, ...] = (Note(Fraction(0), 80, Fraction(1, 4), 0),)
        bass: tuple[Note, ...] = (Note(Fraction(0), 48, Fraction(1, 4), 1),)
        violations = validate_passage(
            soprano,
            bass,
            frozenset({0, 2, 4, 5, 7, 9, 11}),
            {"soprano": (60, 79), "bass": (36, 60)},
            "4/4",
        )
        assert any(v.rule == "voice_range" for v in violations)

    def test_dissonance_on_strong_beat_violation(self) -> None:
        soprano: tuple[Note, ...] = (Note(Fraction(0), 62, Fraction(1, 4), 0),)
        bass: tuple[Note, ...] = (Note(Fraction(0), 60, Fraction(1, 4), 1),)
        violations = validate_passage(
            soprano,
            bass,
            frozenset({0, 2, 4, 5, 7, 9, 11}),
            {"soprano": (60, 79), "bass": (36, 60)},
            "4/4",
        )
        assert any(v.rule == "consonance" for v in violations)

    def test_parallel_fifths_violation(self) -> None:
        soprano: tuple[Note, ...] = (
            Note(Fraction(0), 67, Fraction(1, 4), 0),
            Note(Fraction(1, 2), 69, Fraction(1, 4), 0),
        )
        bass: tuple[Note, ...] = (
            Note(Fraction(0), 60, Fraction(1, 4), 1),
            Note(Fraction(1, 2), 62, Fraction(1, 4), 1),
        )
        violations = validate_passage(
            soprano,
            bass,
            frozenset({0, 2, 4, 5, 7, 9, 11}),
            {"soprano": (60, 79), "bass": (36, 60)},
            "4/4",
        )
        assert any(v.rule == "parallels" for v in violations)
