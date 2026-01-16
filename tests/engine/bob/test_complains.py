"""Tests for Bob COMPLAINS (soft constraint) checks."""
import pytest
from fractions import Fraction

from engine.bob.complains import (
    check_leap_compensation_complains,
    check_consecutive_leaps_complains,
    check_tritone_outline_complains,
    check_forbidden_intervals_complains,
    check_spacing_complains,
    check_monotonous_rhythm_complains,
    check_static_voice_complains,
    check_static_harmony_complains,
    check_endless_alternation_complains,
    check_bar_duplication_complains,
    collect_complains,
)
from engine.engine_types import RealisedNote, RealisedPhrase, RealisedVoice


def make_phrase(
    soprano_pitches: list[int],
    bass_pitches: list[int] | None = None,
    durations: list[Fraction] | None = None,
) -> RealisedPhrase:
    """Create a phrase for testing."""
    if durations is None:
        durations = [Fraction(1)] * len(soprano_pitches)

    offsets = []
    offset = Fraction(0)
    for d in durations:
        offsets.append(offset)
        offset += d

    soprano_notes = [
        RealisedNote(offset=offsets[i], pitch=p, duration=durations[i], voice="soprano")
        for i, p in enumerate(soprano_pitches)
    ]

    if bass_pitches is None:
        bass_pitches = [p - 12 for p in soprano_pitches]

    bass_notes = [
        RealisedNote(offset=offsets[i], pitch=p, duration=durations[i], voice="bass")
        for i, p in enumerate(bass_pitches)
    ]

    return RealisedPhrase(
        index=0,
        voices=[
            RealisedVoice(voice_index=0, notes=soprano_notes),
            RealisedVoice(voice_index=1, notes=bass_notes),
        ],
    )


class TestLeapCompensation:
    """Tests for uncompensated leap detection."""

    def test_uncompensated_leap_detected(self):
        """Large leap not followed by step in opposite direction."""
        # C5 -> A5 (9 semitones up) -> B5 (2 semitones up) - not compensated
        phrase = make_phrase([60, 69, 71])
        issues = check_leap_compensation_complains([phrase], Fraction(4))
        assert len(issues) >= 1
        assert "jump" in issues[0].message.lower()

    def test_compensated_leap_ok(self):
        """Large leap followed by step down should not be flagged."""
        # C5 -> A5 (9 up) -> G5 (2 down) - properly compensated
        phrase = make_phrase([60, 69, 67])
        issues = check_leap_compensation_complains([phrase], Fraction(4))
        assert len(issues) == 0


class TestConsecutiveLeaps:
    """Tests for consecutive leaps in same direction."""

    def test_consecutive_leaps_detected(self):
        """Two leaps in same direction should be flagged."""
        # C5 -> F5 (5 up) -> B5 (6 up) - two leaps ascending
        phrase = make_phrase([60, 65, 71])
        issues = check_consecutive_leaps_complains([phrase], Fraction(4))
        assert len(issues) >= 1
        assert "jump" in issues[0].message.lower()

    def test_leap_then_step_ok(self):
        """Leap followed by step should not be flagged."""
        phrase = make_phrase([60, 67, 69])  # 7 up, 2 up (step)
        issues = check_consecutive_leaps_complains([phrase], Fraction(4))
        assert len(issues) == 0


class TestTritoneOutline:
    """Tests for tritone outline in melody."""

    def test_tritone_outline_detected(self):
        """Four notes outlining tritone should be flagged."""
        # C5 -> D5 -> E5 -> F#5 - outlines C to F# (tritone)
        phrase = make_phrase([60, 62, 64, 66])
        issues = check_tritone_outline_complains([phrase], Fraction(4))
        assert len(issues) >= 1
        assert "awkward" in issues[0].message.lower()

    def test_no_tritone_outline_ok(self):
        """Four notes not outlining tritone should not be flagged."""
        # C5 -> D5 -> E5 -> G5 - outlines C to G (fifth, not tritone)
        phrase = make_phrase([60, 62, 64, 67])
        issues = check_tritone_outline_complains([phrase], Fraction(4))
        assert len(issues) == 0


class TestForbiddenIntervals:
    """Tests for forbidden melodic intervals."""

    def test_seventh_leap_detected(self):
        """Seventh leap should be flagged."""
        # C5 -> B5 (major 7th = 11 semitones)
        phrase = make_phrase([60, 71])
        issues = check_forbidden_intervals_complains([phrase], Fraction(4))
        assert len(issues) >= 1
        assert "jump" in issues[0].message.lower()

    def test_octave_leap_ok(self):
        """Octave leap should not be flagged (it's <= 12 semitones)."""
        phrase = make_phrase([60, 72])  # Exactly octave
        issues = check_forbidden_intervals_complains([phrase], Fraction(4))
        assert len(issues) == 0

    def test_beyond_octave_detected(self):
        """Leap beyond octave should be flagged."""
        phrase = make_phrase([60, 74])  # 14 semitones
        issues = check_forbidden_intervals_complains([phrase], Fraction(4))
        assert len(issues) >= 1


class TestSpacing:
    """Tests for spacing constraints."""

    def test_wide_outer_spacing_detected(self):
        """Very wide outer voice spacing should be flagged."""
        # Soprano at C6 (84), bass at C2 (36) = 48 semitones (> 36 max)
        phrase = make_phrase([84], [36])
        issues = check_spacing_complains([phrase], Fraction(4))
        assert any("wide" in i.message.lower() for i in issues)


class TestMonotonousRhythm:
    """Tests for monotonous rhythm detection."""

    def test_monotonous_rhythm_detected(self):
        """Same rhythm pattern for 4+ bars should be flagged."""
        # 4 bars of quarter notes
        durations = [Fraction(1)] * 16  # 4 notes per bar, 4 bars
        phrase = make_phrase(
            [60, 62, 64, 65] * 4,
            [48, 50, 52, 53] * 4,
            durations,
        )
        issues = check_monotonous_rhythm_complains([phrase], Fraction(4))
        assert len(issues) >= 1
        assert "rhythm" in issues[0].message.lower()


class TestStaticVoice:
    """Tests for static voice detection."""

    def test_static_voice_detected(self):
        """Same pitch for 4+ beats should be flagged."""
        # C5 for 5 beats
        phrase = make_phrase(
            [60, 60, 60, 60, 60],
            [48, 48, 48, 48, 48],
        )
        issues = check_static_voice_complains([phrase], Fraction(4), threshold_beats=4)
        assert len(issues) >= 1
        assert "same note" in issues[0].message.lower()

    def test_moving_voice_ok(self):
        """Moving voice should not be flagged."""
        phrase = make_phrase([60, 62, 64, 65])
        issues = check_static_voice_complains([phrase], Fraction(4))
        assert len(issues) == 0


class TestStaticHarmony:
    """Tests for static harmony detection."""

    def test_static_harmony_detected(self):
        """Same bass pitch class for 4+ bars should be flagged."""
        # C in bass for 5 bars (20 beats at 4/4)
        durations = [Fraction(4)] * 5
        phrase = make_phrase(
            [60, 62, 64, 65, 67],
            [48, 48, 48, 48, 48],  # All C
            durations,
        )
        issues = check_static_harmony_complains([phrase], Fraction(4), threshold_bars=4)
        assert len(issues) >= 1
        assert "harmony" in issues[0].message.lower()


class TestEndlessAlternation:
    """Tests for endless trill/alternation."""

    def test_endless_alternation_detected(self):
        """More than 8 alternating notes should be flagged."""
        # C-D-C-D-C-D-C-D-C-D (10 alternations)
        phrase = make_phrase([60, 62] * 5)
        issues = check_endless_alternation_complains([phrase], Fraction(4))
        assert len(issues) >= 1
        assert "back and forth" in issues[0].message.lower()


class TestBarDuplication:
    """Tests for identical consecutive bars."""

    def test_bar_duplication_detected(self):
        """Identical consecutive bars should be flagged."""
        # Bar 1: C-D-E-F, Bar 2: C-D-E-F (same)
        phrase = make_phrase(
            [60, 62, 64, 65, 60, 62, 64, 65],
            [48, 50, 52, 53, 48, 50, 52, 53],
        )
        issues = check_bar_duplication_complains([phrase], Fraction(4))
        assert len(issues) >= 1
        assert "identical" in issues[0].message.lower()


class TestCollectComplains:
    """Tests for collect_complains aggregation."""

    def test_collect_all_complains(self):
        """All COMPLAINS checks should run and return correct category."""
        phrase = make_phrase([60, 69, 78])  # Two big leaps up
        issues = collect_complains([phrase], Fraction(4))
        assert all(i.category == "COMPLAINS" for i in issues)
