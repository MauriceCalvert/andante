"""Tests for Bob REFUSES (hard constraint) checks."""
import pytest
from fractions import Fraction

from engine.bob.refuses import (
    check_parallel_fifths_refuses,
    check_parallel_octaves_refuses,
    check_parallel_unisons_refuses,
    check_direct_perfect_refuses,
    check_dissonance_refuses,
    check_voice_overlap_refuses,
    check_voice_crossing_refuses,
    collect_refuses,
)
from engine.engine_types import RealisedNote, RealisedPhrase, RealisedVoice


def make_phrase(soprano_pitches: list[int], bass_pitches: list[int]) -> RealisedPhrase:
    """Create a simple two-voice phrase for testing."""
    soprano_notes = [
        RealisedNote(offset=Fraction(i), pitch=p, duration=Fraction(1), voice="soprano")
        for i, p in enumerate(soprano_pitches)
    ]
    bass_notes = [
        RealisedNote(offset=Fraction(i), pitch=p, duration=Fraction(1), voice="bass")
        for i, p in enumerate(bass_pitches)
    ]
    return RealisedPhrase(
        index=0,
        voices=[
            RealisedVoice(voice_index=0, notes=soprano_notes),
            RealisedVoice(voice_index=1, notes=bass_notes),
        ],
    )


class TestParallelFifths:
    """Tests for parallel fifths detection."""

    def test_parallel_fifths_detected(self):
        """Parallel fifths should be detected."""
        # C-G (60-67) then D-A (62-69) - both fifths, both ascending
        phrase = make_phrase([67, 69], [60, 62])
        issues = check_parallel_fifths_refuses([phrase], Fraction(4))
        assert len(issues) == 1
        assert issues[0].category == "REFUSES"
        assert "fifth" in issues[0].message.lower()

    def test_no_parallel_fifths_contrary_motion(self):
        """Contrary motion to fifth should not be flagged."""
        # G up to A, C down to B - arriving at fifth but contrary motion
        phrase = make_phrase([67, 69], [60, 57])
        issues = check_parallel_fifths_refuses([phrase], Fraction(4))
        assert len(issues) == 0

    def test_no_parallel_fifths_different_intervals(self):
        """Different intervals should not be flagged as parallel fifths."""
        phrase = make_phrase([60, 65], [48, 53])  # Fourth to fourth
        issues = check_parallel_fifths_refuses([phrase], Fraction(4))
        assert len(issues) == 0


class TestParallelOctaves:
    """Tests for parallel octaves detection."""

    def test_parallel_octaves_detected(self):
        """Parallel octaves should be detected."""
        # C-C (60-48) then D-D (62-50) - both octaves, both ascending
        phrase = make_phrase([60, 62], [48, 50])
        issues = check_parallel_octaves_refuses([phrase], Fraction(4))
        assert len(issues) == 1
        assert "octave" in issues[0].message.lower()

    def test_no_parallel_octaves_one_stationary(self):
        """If one voice is stationary, not parallel octaves."""
        phrase = make_phrase([60, 60], [48, 50])
        issues = check_parallel_octaves_refuses([phrase], Fraction(4))
        assert len(issues) == 0


class TestDirectPerfect:
    """Tests for direct (hidden) fifths and octaves."""

    def test_direct_fifth_detected(self):
        """Direct fifth with soprano leap should be detected."""
        # Both voices leap to a fifth (soprano leaps more than step)
        phrase = make_phrase([60, 67], [48, 60])  # Soprano leaps 7, arriving at fifth
        issues = check_direct_perfect_refuses([phrase], Fraction(4))
        assert len(issues) == 1
        assert "leap to a fifth" in issues[0].message.lower()

    def test_no_direct_fifth_soprano_step(self):
        """Stepwise soprano motion to fifth is allowed."""
        phrase = make_phrase([65, 67], [57, 60])  # Soprano steps up 2
        issues = check_direct_perfect_refuses([phrase], Fraction(4))
        assert len(issues) == 0


class TestDissonance:
    """Tests for dissonance preparation and resolution."""

    def test_unprepared_dissonance_detected(self):
        """Unprepared strong-beat dissonance should be detected."""
        # Beat 0 (strong): m2 interval without preparation
        phrase = make_phrase([61, 62], [60, 60])  # m2 then M2
        issues = check_dissonance_refuses([phrase], Fraction(4))
        # First beat has dissonance (61-60 = m2), no previous beat = unprepared
        assert any("clashes" in i.message.lower() for i in issues)

    def test_prepared_dissonance_ok(self):
        """Properly prepared and resolved dissonance should not be flagged."""
        # Preparation: same pitch on weak beat, dissonance on strong beat
        # 64-60 consonant, 64-62 dissonance (prepared by tie), 62-62 resolution
        # This is simplified - real suspension needs tie semantics
        pass  # Complex test - would need more setup


class TestVoiceOverlap:
    """Tests for voice overlap detection."""

    def test_voice_overlap_detected(self):
        """Voice overlap should be detected."""
        # Soprano was at 60, bass was at 55. Next: soprano at 52 (below where bass was)
        phrase = make_phrase([60, 52], [55, 48])
        issues = check_voice_overlap_refuses([phrase], Fraction(4))
        # Upper voice goes below previous lower position
        assert len(issues) >= 1
        assert any("below" in i.message.lower() for i in issues)


class TestVoiceCrossing:
    """Tests for prolonged voice crossing."""

    def test_brief_crossing_ok(self):
        """Brief voice crossing (<= 1 beat) should not be flagged."""
        phrase = make_phrase([50, 60], [55, 48])  # Crosses then uncrosses
        issues = check_voice_crossing_refuses([phrase], Fraction(4))
        # Duration of crossing is 1 beat, threshold is > 1
        assert len(issues) == 0

    def test_prolonged_crossing_detected(self):
        """Prolonged voice crossing should be detected."""
        # Soprano below bass for 3 beats
        phrase = make_phrase([48, 48, 48, 60], [60, 60, 60, 48])
        issues = check_voice_crossing_refuses([phrase], Fraction(4), max_beats=Fraction(1))
        assert len(issues) >= 1


class TestCollectRefuses:
    """Tests for collect_refuses aggregation."""

    def test_collect_all_refuses(self):
        """All REFUSES checks should run."""
        phrase = make_phrase([67, 69], [60, 62])  # Parallel fifths
        issues = collect_refuses([phrase], Fraction(4))
        assert all(i.category == "REFUSES" for i in issues)
        assert len(issues) >= 1
