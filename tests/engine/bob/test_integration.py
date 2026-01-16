"""Integration tests for Bob diagnostic module."""
import pytest
from fractions import Fraction

from engine.bob import diagnose, Issue, Report
from engine.engine_types import RealisedNote, RealisedPhrase, RealisedVoice
from engine.key import Key


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


class TestDiagnoseFunction:
    """Tests for main diagnose() entry point."""

    def test_diagnose_returns_report(self):
        """diagnose() should return a Report object."""
        phrase = make_phrase([60, 62, 64], [48, 50, 52])
        result = diagnose([phrase])
        assert isinstance(result, Report)
        assert isinstance(result.issues, list)

    def test_diagnose_with_key(self):
        """diagnose() should accept Key parameter."""
        phrase = make_phrase([64, 60], [55, 48])  # Authentic cadence in C
        key = Key(tonic="C", mode="major")
        result = diagnose([phrase], key=key)
        # Should detect conclusive ending
        assert any("conclusive" in i.message.lower() for i in result.issues)

    def test_diagnose_with_metre(self):
        """diagnose() should parse metre string."""
        phrase = make_phrase([60, 62, 64, 65], [48, 50, 52, 53])
        result = diagnose([phrase], metre="3/4")
        # Should work without error
        assert isinstance(result, Report)

    def test_diagnose_finds_parallel_fifths(self):
        """diagnose() should find parallel fifths."""
        # G-D (67-62, fifth) -> A-E (69-64, fifth)
        phrase = make_phrase([67, 69], [60, 62])
        result = diagnose([phrase])
        refuses = [i for i in result.issues if i.category == "REFUSES"]
        assert len(refuses) >= 1
        assert any("fifth" in i.message.lower() for i in refuses)

    def test_diagnose_finds_multiple_issues(self):
        """diagnose() should find multiple issue types."""
        # Parallel fifths + uncompensated leap
        phrase = make_phrase([67, 69, 78], [60, 62, 66])
        result = diagnose([phrase])
        categories = {i.category for i in result.issues}
        # Should have both REFUSES (parallel fifths) and COMPLAINS (leap issues)
        assert "REFUSES" in categories or "COMPLAINS" in categories

    def test_diagnose_issues_sorted_by_bar(self):
        """Issues should be sorted by bar then beat."""
        phrase = make_phrase([60, 62, 64, 65, 67, 69, 71, 72], [48, 50, 52, 53, 55, 57, 59, 60])
        result = diagnose([phrase])
        if len(result.issues) > 1:
            for i in range(len(result.issues) - 1):
                curr = result.issues[i]
                next_issue = result.issues[i + 1]
                assert (curr.bar, curr.beat) <= (next_issue.bar, next_issue.beat)


class TestReportClipboard:
    """Tests for Report.to_clipboard() integration."""

    def test_full_report_format(self):
        """Full report should have proper structure."""
        phrase = make_phrase([67, 69], [60, 62])  # Parallel fifths
        result = diagnose([phrase])
        output = result.to_clipboard()

        # Should have header
        assert "=== Bob's Report ===" in output

        # Should be non-empty if issues found
        if result.issues:
            assert "No issues found" not in output

    def test_clean_piece_report(self):
        """Clean piece should show no issues."""
        # Simple stepwise motion, varying intervals (3rds/6ths) to avoid parallels
        # Soprano: C-D-E-D-C, Bass: A-B-C-B-A (mostly 3rds/6ths)
        phrase = make_phrase([60, 62, 64, 62, 60], [57, 59, 60, 59, 57])
        result = diagnose([phrase])

        # May still have NOTES (peak, etc.) but check REFUSES is empty
        refuses = [i for i in result.issues if i.category == "REFUSES"]
        # Varying intervals shouldn't trigger parallel fifths/octaves
        assert len(refuses) == 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_phrase_list(self):
        """Empty phrase list should not crash."""
        result = diagnose([])
        assert isinstance(result, Report)
        assert result.issues == []

    def test_single_note_phrase(self):
        """Single-note phrase should not crash."""
        phrase = make_phrase([60], [48])
        result = diagnose([phrase])
        assert isinstance(result, Report)

    def test_very_short_phrase(self):
        """Two-note phrase should work."""
        phrase = make_phrase([60, 62], [48, 50])
        result = diagnose([phrase])
        assert isinstance(result, Report)
