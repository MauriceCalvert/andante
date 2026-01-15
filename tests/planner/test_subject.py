"""Tests for planner.subject.

Category B tests: Subject class with counter-subject generation.
Tests import only:
- planner.subject (module under test)
- planner.types (shared types)
- stdlib
"""
from fractions import Fraction

import pytest

from planner.subject import (
    DEFAULT_MIN_CS_DURATION,
    Subject,
    VALID_DURATIONS,
)
from planner.plannertypes import Motif


class TestSubjectCreation:
    """Test Subject class instantiation."""

    def test_basic_creation(self) -> None:
        """Subject can be created with valid parameters."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4),) * 4,
            bars=1,
            mode="major",
        )
        assert subj.degrees == (1, 2, 3, 4)
        assert subj.durations == (Fraction(1, 4),) * 4
        assert subj.bars == 1

    def test_mismatched_lengths_raises(self) -> None:
        """Mismatched degrees/durations raises assertion."""
        with pytest.raises(AssertionError, match="Degrees and durations must match"):
            Subject(
                degrees=(1, 2, 3),
                durations=(Fraction(1, 4),) * 4,
                bars=1,
            )

    def test_invalid_degree_raises(self) -> None:
        """Degree outside 1-7 raises assertion."""
        with pytest.raises(AssertionError, match="Degrees must be 1-7"):
            Subject(
                degrees=(1, 2, 8),  # 8 is invalid
                durations=(Fraction(1, 4),) * 3,
                bars=1,
            )

    def test_invalid_degree_zero_raises(self) -> None:
        """Degree 0 raises assertion."""
        with pytest.raises(AssertionError, match="Degrees must be 1-7"):
            Subject(
                degrees=(0, 1, 2),
                durations=(Fraction(1, 4),) * 3,
                bars=1,
            )

    def test_voice_count_minimum(self) -> None:
        """Voice count must be at least 2."""
        with pytest.raises(AssertionError, match="at least 2 voices"):
            Subject(
                degrees=(1, 2, 3),
                durations=(Fraction(1, 4),) * 3,
                bars=1,
                voice_count=1,
            )


class TestSubjectProperties:
    """Test Subject property accessors."""

    def test_subject_property(self) -> None:
        """subject property returns Motif."""
        subj: Subject = Subject(
            degrees=(1, 3, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1,
        )
        motif: Motif = subj.subject
        assert isinstance(motif, Motif)
        assert motif.degrees == (1, 3, 5)
        assert motif.bars == 1

    def test_counter_subject_property(self) -> None:
        """counter_subject property returns generated Motif."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4),) * 4,
            bars=1,
            mode="major",
        )
        cs: Motif = subj.counter_subject
        assert isinstance(cs, Motif)
        assert len(cs.degrees) > 0

    def test_counter_subject_lazy_generation(self) -> None:
        """Counter-subject is lazily generated on first access."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4),) * 3,
            bars=1,
        )
        # Access twice - should be same result
        cs1: Motif = subj.counter_subject
        cs2: Motif = subj.counter_subject
        assert cs1 == cs2


class TestCounterSubjectGeneration:
    """Test counter-subject generation."""

    def test_cs_valid_degrees(self) -> None:
        """Counter-subject has valid scale degrees."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 8),) * 5,
            bars=1,
            mode="major",
        )
        cs: Motif = subj.counter_subject
        assert all(1 <= d <= 7 for d in cs.degrees)

    def test_cs_durations_sum_matches(self) -> None:
        """Counter-subject durations sum equals subject."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4),) * 4,
            bars=1,
        )
        cs: Motif = subj.counter_subject
        subj_total: Fraction = sum(subj.subject.durations, Fraction(0))
        cs_total: Fraction = sum(cs.durations, Fraction(0))
        assert cs_total == subj_total

    def test_cs_avoids_leading_tone_major(self) -> None:
        """In major mode, CS avoids degree 7."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4, 5, 6, 1),
            durations=(Fraction(1, 8),) * 7,
            bars=1,
            mode="major",
        )
        cs: Motif = subj.counter_subject
        assert 7 not in cs.degrees

    def test_cs_avoids_6_and_7_minor(self) -> None:
        """In minor mode, CS avoids degrees 6 and 7."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4, 5, 1),
            durations=(Fraction(1, 8),) * 6,
            bars=1,
            mode="minor",
        )
        cs: Motif = subj.counter_subject
        assert 6 not in cs.degrees
        assert 7 not in cs.degrees


class TestExtendTo:
    """Test extend_to method."""

    def test_trim_when_budget_smaller(self) -> None:
        """Trims both motifs when budget is smaller than duration."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4),) * 4,
            bars=1,
        )
        ext_subj, ext_cs = subj.extend_to(Fraction(1, 2))
        assert sum(ext_subj.durations, Fraction(0)) == Fraction(1, 2)
        assert sum(ext_cs.durations, Fraction(0)) == Fraction(1, 2)

    def test_cycle_when_budget_larger(self) -> None:
        """Cycles motifs when budget is larger than duration."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4),) * 4,
            bars=1,
        )
        ext_subj, ext_cs = subj.extend_to(Fraction(2))  # 2 bars
        assert sum(ext_subj.durations, Fraction(0)) == Fraction(2)
        assert sum(ext_cs.durations, Fraction(0)) == Fraction(2)

    def test_exact_budget(self) -> None:
        """When budget equals duration, returns copies."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4),) * 4,
            bars=1,
        )
        ext_subj, ext_cs = subj.extend_to(Fraction(1))
        assert sum(ext_subj.durations, Fraction(0)) == Fraction(1)


class TestGetMotif:
    """Test get_motif method."""

    def test_get_subject(self) -> None:
        """get_motif('subject') returns subject."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4),) * 3,
            bars=1,
        )
        motif: Motif = subj.get_motif("subject")
        assert motif == subj.subject

    def test_get_counter_subject(self) -> None:
        """get_motif('counter_subject') returns counter-subject."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4),) * 3,
            bars=1,
        )
        motif: Motif = subj.get_motif("counter_subject")
        assert motif == subj.counter_subject

    def test_get_cs_1(self) -> None:
        """get_motif('cs_1') returns counter-subject."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4),) * 3,
            bars=1,
        )
        motif: Motif = subj.get_motif("cs_1")
        assert motif == subj.counter_subject

    def test_unknown_name_raises(self) -> None:
        """Unknown motif name raises ValueError."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4),) * 3,
            bars=1,
        )
        with pytest.raises(ValueError, match="Unknown motif name"):
            subj.get_motif("unknown")


class TestGetMotifExtended:
    """Test get_motif_extended method."""

    def test_extends_subject(self) -> None:
        """get_motif_extended extends subject to budget."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4),) * 4,
            bars=1,
        )
        extended: Motif = subj.get_motif_extended("subject", Fraction(2))
        assert sum(extended.durations, Fraction(0)) == Fraction(2)

    def test_trims_subject(self) -> None:
        """get_motif_extended trims subject to budget."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4),) * 4,
            bars=1,
        )
        extended: Motif = subj.get_motif_extended("subject", Fraction(1, 2))
        assert sum(extended.durations, Fraction(0)) == Fraction(1, 2)


class TestMotifNames:
    """Test motif_names property."""

    def test_two_voice_names(self) -> None:
        """2-voice subject has subject and cs_1."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4),) * 3,
            bars=1,
            voice_count=2,
        )
        names: tuple[str, ...] = subj.motif_names
        assert names == ("subject", "cs_1")

    def test_three_voice_names(self) -> None:
        """3-voice subject has subject, cs_1, cs_2."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4),) * 3,
            bars=1,
            voice_count=3,
        )
        names: tuple[str, ...] = subj.motif_names
        assert names == ("subject", "cs_1", "cs_2")


class TestConstants:
    """Test module constants."""

    def test_default_min_cs_duration(self) -> None:
        """DEFAULT_MIN_CS_DURATION is 1/16."""
        assert DEFAULT_MIN_CS_DURATION == Fraction(1, 16)

    def test_valid_durations_ordered(self) -> None:
        """VALID_DURATIONS in descending order."""
        durations: list[Fraction] = list(VALID_DURATIONS)
        assert durations == sorted(durations, reverse=True)


class TestIntegration:
    """Integration tests for Subject class."""

    def test_full_workflow(self) -> None:
        """Complete subject/counter-subject workflow."""
        subj: Subject = Subject(
            degrees=(1, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                       Fraction(1, 8), Fraction(1, 8), Fraction(1, 4)),
            bars=1,
            mode="major",
            genre="invention",
        )
        # Get subject and CS
        subject: Motif = subj.subject
        cs: Motif = subj.counter_subject
        # Both should be valid
        assert len(subject.degrees) == len(subject.durations)
        assert len(cs.degrees) == len(cs.durations)
        # Both should sum to same duration
        subj_dur: Fraction = sum(subject.durations, Fraction(0))
        cs_dur: Fraction = sum(cs.durations, Fraction(0))
        assert subj_dur == cs_dur
        # Extend and verify
        ext_subj, ext_cs = subj.extend_to(Fraction(2))
        assert sum(ext_subj.durations, Fraction(0)) == Fraction(2)
        assert sum(ext_cs.durations, Fraction(0)) == Fraction(2)
