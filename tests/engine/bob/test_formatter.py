"""Tests for Bob formatter and output."""
import pytest
from fractions import Fraction

from engine.bob.formatter import Issue, Report, offset_to_bar_beat


class TestOffsetToBarBeat:
    """Tests for offset conversion."""

    def test_downbeat_bar_1(self):
        """Offset 0 should be bar 1 beat 1."""
        bar, beat = offset_to_bar_beat(Fraction(0), Fraction(4))
        assert bar == 1
        assert beat == 1.0

    def test_beat_2_bar_1(self):
        """Offset 1 in 4/4 should be bar 1 beat 2."""
        bar, beat = offset_to_bar_beat(Fraction(1), Fraction(4))
        assert bar == 1
        assert beat == 2.0

    def test_downbeat_bar_2(self):
        """Offset 4 in 4/4 should be bar 2 beat 1."""
        bar, beat = offset_to_bar_beat(Fraction(4), Fraction(4))
        assert bar == 2
        assert beat == 1.0

    def test_offbeat(self):
        """Offset 0.5 in 4/4 should be bar 1 beat 1.5."""
        bar, beat = offset_to_bar_beat(Fraction(1, 2), Fraction(4))
        assert bar == 1
        assert beat == 1.5

    def test_3_4_metre(self):
        """In 3/4, bar duration is 3."""
        bar, beat = offset_to_bar_beat(Fraction(3), Fraction(3))
        assert bar == 2
        assert beat == 1.0


class TestIssue:
    """Tests for Issue dataclass."""

    def test_issue_creation(self):
        """Issue should store all fields."""
        issue = Issue(
            category="REFUSES",
            bar=5,
            beat=2.5,
            voices="soprano-bass",
            message="Test message",
        )
        assert issue.category == "REFUSES"
        assert issue.bar == 5
        assert issue.beat == 2.5
        assert issue.voices == "soprano-bass"
        assert issue.message == "Test message"
        assert issue.end_bar is None

    def test_issue_with_range(self):
        """Issue can have end_bar for ranges."""
        issue = Issue(
            category="COMPLAINS",
            bar=8,
            beat=1.0,
            voices="soprano",
            message="Same rhythm",
            end_bar=11,
        )
        assert issue.bar == 8
        assert issue.end_bar == 11


class TestReport:
    """Tests for Report dataclass and formatting."""

    def test_empty_report(self):
        """Empty report should say no issues."""
        report = Report(issues=[])
        output = report.to_clipboard()
        assert "No issues found" in output

    def test_report_with_refuses(self):
        """Report should format REFUSES section."""
        issues = [
            Issue("REFUSES", 1, 1.0, "soprano-bass", "Parallel fifths"),
            Issue("REFUSES", 3, 2.0, "soprano-bass", "Parallel octaves"),
        ]
        report = Report(issues=issues)
        output = report.to_clipboard()
        assert "REFUSES (2):" in output
        assert "Bar 1 beat 1" in output
        assert "Bar 3 beat 2" in output
        assert "Parallel fifths" in output
        assert "Parallel octaves" in output

    def test_report_with_complains(self):
        """Report should format COMPLAINS section."""
        issues = [
            Issue("COMPLAINS", 5, 1.0, "soprano", "Large jump up"),
        ]
        report = Report(issues=issues)
        output = report.to_clipboard()
        assert "COMPLAINS (1):" in output
        assert "Bar 5 beat 1" in output

    def test_report_with_notes(self):
        """Report should format NOTES section."""
        issues = [
            Issue("NOTES", 16, 1.0, "", "Feels conclusive"),
        ]
        report = Report(issues=issues)
        output = report.to_clipboard()
        assert "NOTES (1):" in output
        assert "Bar 16 beat 1" in output
        # Empty voices should not add extra comma
        assert "Bar 16 beat 1: Feels conclusive" in output

    def test_report_with_range(self):
        """Report should format bar ranges correctly."""
        issues = [
            Issue("COMPLAINS", 8, 1.0, "soprano", "Same rhythm", end_bar=11),
        ]
        report = Report(issues=issues)
        output = report.to_clipboard()
        assert "Bars 8-11" in output

    def test_report_mixed_categories(self):
        """Report should separate categories correctly."""
        issues = [
            Issue("REFUSES", 1, 1.0, "soprano-bass", "Problem 1"),
            Issue("COMPLAINS", 2, 1.0, "soprano", "Warning 1"),
            Issue("NOTES", 3, 1.0, "", "Observation 1"),
        ]
        report = Report(issues=issues)
        output = report.to_clipboard()
        assert "REFUSES (1):" in output
        assert "COMPLAINS (1):" in output
        assert "NOTES (1):" in output

    def test_report_header(self):
        """Report should have Bob's header."""
        report = Report(issues=[])
        output = report.to_clipboard()
        assert "=== Bob's Report ===" in output
