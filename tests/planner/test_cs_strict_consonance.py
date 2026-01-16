"""Strict consonance tests for counter-subject generator.

These tests verify that generated counter-subjects maintain consonance
at ALL subject attack times, not just at aligned note indices.

The key insight: Subject and CS may have different note counts and rhythms.
What matters is: at every point in time where the subject attacks, the CS
note sounding at that time must form a consonant interval.

This is what Bob's diagnostic checks, and these tests must verify the same.
"""
from fractions import Fraction
from typing import Optional

import pytest

from planner.cs_generator import (
    ALL_CONSONANCES,
    CounterSubject,
    Subject,
    generate_countersubject,
    _degree_to_semitone,
    _interval_class,
    MAJOR_SCALE,
    MINOR_SCALE,
)


def compute_cs_sounding_at(
    cs: CounterSubject,
    time: Fraction,
    total_duration: Fraction,
) -> Optional[int]:
    """Find which CS degree is sounding at a given time.

    Returns the CS degree, or None if no CS note is sounding at that time.
    """
    pos = Fraction(0)
    for deg, dur in zip(cs.degrees, cs.durations):
        if pos <= time < pos + dur:
            return deg
        pos += dur
    return None


def verify_consonance_at_subject_attacks(
    subject: Subject,
    cs: CounterSubject,
    delay: Fraction = Fraction(0),
) -> list[tuple[Fraction, int, int, int]]:
    """Verify consonance at every subject attack time.

    Returns list of violations as (time, subject_degree, cs_degree, interval_class).
    Empty list means all intervals are consonant.
    """
    violations: list[tuple[Fraction, int, int, int]] = []
    scale = subject.scale
    total = subject.total_duration

    # Build subject attack times
    pos = Fraction(0)
    for i, (subj_deg, dur) in enumerate(zip(subject.degrees, subject.durations)):
        # Find what CS note is sounding at this time (accounting for delay)
        cs_time = pos - delay  # CS starts at `delay`, so we offset

        if cs_time >= Fraction(0) and pos < total:
            cs_deg = compute_cs_sounding_at(cs, cs_time, total)

            if cs_deg is not None:
                ic = _interval_class(subj_deg, cs_deg, scale)
                if ic not in ALL_CONSONANCES:
                    violations.append((pos, subj_deg, cs_deg, ic))

        pos += dur

    return violations


def verify_consonance_at_cs_attacks(
    subject: Subject,
    cs: CounterSubject,
    delay: Fraction = Fraction(0),
) -> list[tuple[Fraction, int, int, int]]:
    """Verify consonance at every CS attack time.

    Returns list of violations as (time, subject_degree, cs_degree, interval_class).
    """
    violations: list[tuple[Fraction, int, int, int]] = []
    scale = subject.scale
    total = subject.total_duration

    # Build subject time-pitch map
    subj_events: list[tuple[Fraction, Fraction, int]] = []
    pos = Fraction(0)
    for deg, dur in zip(subject.degrees, subject.durations):
        subj_events.append((pos, pos + dur, deg))
        pos += dur

    # Check each CS attack time
    cs_pos = delay
    for cs_deg, dur in zip(cs.degrees, cs.durations):
        if cs_pos >= total:
            break

        # Find subject degree sounding at this time
        for start, end, subj_deg in subj_events:
            if start <= cs_pos < end:
                ic = _interval_class(subj_deg, cs_deg, scale)
                if ic not in ALL_CONSONANCES:
                    violations.append((cs_pos, subj_deg, cs_deg, ic))
                break

        cs_pos += dur

    return violations


def verify_all_alignment_points(
    subject: Subject,
    cs: CounterSubject,
    delay: Fraction = Fraction(0),
) -> list[tuple[Fraction, int, int, int]]:
    """Verify consonance at ALL alignment points (union of all attack times).

    This is the most comprehensive check: at every point where either voice
    attacks, check the interval.
    """
    violations: list[tuple[Fraction, int, int, int]] = []
    scale = subject.scale
    total = subject.total_duration

    # Build time-pitch maps
    subj_events: list[tuple[Fraction, Fraction, int]] = []
    pos = Fraction(0)
    for deg, dur in zip(subject.degrees, subject.durations):
        subj_events.append((pos, pos + dur, deg))
        pos += dur

    cs_events: list[tuple[Fraction, Fraction, int]] = []
    pos = delay
    for deg, dur in zip(cs.degrees, cs.durations):
        if pos >= total:
            break
        end = min(pos + dur, total)
        cs_events.append((pos, end, deg))
        pos += dur

    # Collect all attack times
    attack_times: set[Fraction] = set()
    for start, _, _ in subj_events:
        attack_times.add(start)
    for start, _, _ in cs_events:
        attack_times.add(start)

    # Check each attack time
    for t in sorted(attack_times):
        if t >= total:
            continue

        # Find subject degree at time t
        subj_deg = None
        for start, end, deg in subj_events:
            if start <= t < end:
                subj_deg = deg
                break

        # Find CS degree at time t
        cs_deg = None
        for start, end, deg in cs_events:
            if start <= t < end:
                cs_deg = deg
                break

        # Check consonance if both are sounding
        if subj_deg is not None and cs_deg is not None:
            ic = _interval_class(subj_deg, cs_deg, scale)
            if ic not in ALL_CONSONANCES:
                violations.append((t, subj_deg, cs_deg, ic))

    return violations


# =============================================================================
# TEST SUBJECTS - Diverse rhythmic patterns
# =============================================================================

# Simple uniform rhythm
SUBJECT_UNIFORM = Subject(
    degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1),
    durations=(Fraction(1, 8),) * 9,
    mode="major",
)

# Mixed rhythm (quarters and eighths)
SUBJECT_MIXED = Subject(
    degrees=(1, 3, 5, 4, 2, 1),
    durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
               Fraction(1, 4), Fraction(1, 8), Fraction(1, 8)),
    mode="major",
)

# Syncopated rhythm
SUBJECT_SYNCOPATED = Subject(
    degrees=(5, 4, 3, 2, 1),
    durations=(Fraction(3, 8), Fraction(1, 8), Fraction(1, 4),
               Fraction(1, 8), Fraction(1, 8)),
    mode="major",
)

# Bach-style invention subject
SUBJECT_BACH_1 = Subject(
    degrees=(5, 5, 1, 7, 6, 4, 5, 3, 1),
    durations=(Fraction(3, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8),
               Fraction(1, 4), Fraction(1, 8), Fraction(3, 8), Fraction(1, 8),
               Fraction(3, 8)),
    mode="major",
)

# Minor mode subject
SUBJECT_MINOR = Subject(
    degrees=(1, 5, 4, 3, 2, 3, 1, 5),
    durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
               Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 4)),
    mode="minor",
)

# Long subject (16 notes)
SUBJECT_LONG = Subject(
    degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1, 2, 3, 4, 5, 4, 3, 1),
    durations=(Fraction(1, 8),) * 16,
    mode="major",
)

# Short subject (3 notes)
SUBJECT_SHORT = Subject(
    degrees=(1, 3, 5),
    durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
    mode="major",
)

# All quarters
SUBJECT_ALL_QUARTERS = Subject(
    degrees=(1, 2, 3, 4),
    durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
    mode="major",
)

# Ascending scale
SUBJECT_ASCENDING = Subject(
    degrees=(1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1),
    durations=(Fraction(1, 8),) * 11,
    mode="major",
)

# Arpeggio pattern
SUBJECT_ARPEGGIO = Subject(
    degrees=(1, 3, 5, 3, 1, 5, 3, 1),
    durations=(Fraction(1, 8),) * 8,
    mode="major",
)


# =============================================================================
# STRICT CONSONANCE TESTS
# =============================================================================

class TestStrictConsonanceAtSubjectAttacks:
    """Verify consonance at every subject attack time."""

    @pytest.mark.parametrize("subject", [
        SUBJECT_UNIFORM,
        SUBJECT_MIXED,
        SUBJECT_SYNCOPATED,
        SUBJECT_BACH_1,
        SUBJECT_MINOR,
        SUBJECT_LONG,
        SUBJECT_SHORT,
        SUBJECT_ALL_QUARTERS,
        SUBJECT_ASCENDING,
        SUBJECT_ARPEGGIO,
    ])
    def test_consonance_at_subject_attacks(self, subject: Subject) -> None:
        """Every subject attack must have consonant CS note."""
        cs = generate_countersubject(subject, timeout_seconds=15.0)
        assert cs is not None, f"Failed to generate CS for {subject.degrees}"

        violations = verify_consonance_at_subject_attacks(subject, cs)

        assert len(violations) == 0, (
            f"Dissonance at subject attacks:\n"
            + "\n".join(
                f"  t={v[0]}: subj_deg={v[1]}, cs_deg={v[2]}, ic={v[3]}"
                for v in violations
            )
        )


class TestStrictConsonanceAtCSAttacks:
    """Verify consonance at every CS attack time."""

    @pytest.mark.parametrize("subject", [
        SUBJECT_UNIFORM,
        SUBJECT_MIXED,
        SUBJECT_SYNCOPATED,
        SUBJECT_BACH_1,
        SUBJECT_MINOR,
        SUBJECT_LONG,
        SUBJECT_SHORT,
        SUBJECT_ALL_QUARTERS,
        SUBJECT_ASCENDING,
        SUBJECT_ARPEGGIO,
    ])
    def test_consonance_at_cs_attacks(self, subject: Subject) -> None:
        """Every CS attack must have consonant subject note."""
        cs = generate_countersubject(subject, timeout_seconds=15.0)
        assert cs is not None, f"Failed to generate CS for {subject.degrees}"

        violations = verify_consonance_at_cs_attacks(subject, cs)

        assert len(violations) == 0, (
            f"Dissonance at CS attacks:\n"
            + "\n".join(
                f"  t={v[0]}: subj_deg={v[1]}, cs_deg={v[2]}, ic={v[3]}"
                for v in violations
            )
        )


class TestStrictConsonanceAllAlignments:
    """Verify consonance at ALL alignment points (most comprehensive)."""

    @pytest.mark.parametrize("subject", [
        SUBJECT_UNIFORM,
        SUBJECT_MIXED,
        SUBJECT_SYNCOPATED,
        SUBJECT_BACH_1,
        SUBJECT_MINOR,
        SUBJECT_LONG,
        SUBJECT_SHORT,
        SUBJECT_ALL_QUARTERS,
        SUBJECT_ASCENDING,
        SUBJECT_ARPEGGIO,
    ])
    def test_consonance_all_alignments(self, subject: Subject) -> None:
        """Every alignment point must be consonant."""
        cs = generate_countersubject(subject, timeout_seconds=15.0)
        assert cs is not None, f"Failed to generate CS for {subject.degrees}"

        violations = verify_all_alignment_points(subject, cs)

        assert len(violations) == 0, (
            f"Dissonance at alignment points:\n"
            + "\n".join(
                f"  t={v[0]}: subj_deg={v[1]}, cs_deg={v[2]}, ic={v[3]}"
                for v in violations
            )
        )


class TestStrictDurationMatch:
    """Verify CS total duration matches subject."""

    @pytest.mark.parametrize("subject", [
        SUBJECT_UNIFORM,
        SUBJECT_MIXED,
        SUBJECT_SYNCOPATED,
        SUBJECT_BACH_1,
        SUBJECT_MINOR,
        SUBJECT_LONG,
        SUBJECT_SHORT,
        SUBJECT_ALL_QUARTERS,
        SUBJECT_ASCENDING,
        SUBJECT_ARPEGGIO,
    ])
    def test_duration_match(self, subject: Subject) -> None:
        """CS total duration must equal subject total duration."""
        cs = generate_countersubject(subject, timeout_seconds=15.0)
        assert cs is not None, f"Failed to generate CS for {subject.degrees}"

        assert cs.total_duration == subject.total_duration, (
            f"Duration mismatch: CS={cs.total_duration}, subj={subject.total_duration}"
        )


class TestStrictValidDelays:
    """Verify valid_delays field accuracy."""

    @pytest.mark.parametrize("subject", [
        SUBJECT_UNIFORM,
        SUBJECT_MIXED,
        SUBJECT_SHORT,
        SUBJECT_ALL_QUARTERS,
    ])
    def test_valid_delays_are_consonant(self, subject: Subject) -> None:
        """Each valid delay must produce consonant counterpoint."""
        cs = generate_countersubject(subject, timeout_seconds=15.0)
        assert cs is not None, f"Failed to generate CS for {subject.degrees}"

        for delay in cs.valid_delays:
            violations = verify_all_alignment_points(subject, cs, delay)

            assert len(violations) == 0, (
                f"Invalid delay {delay} marked as valid:\n"
                + "\n".join(
                    f"  t={v[0]}: subj_deg={v[1]}, cs_deg={v[2]}, ic={v[3]}"
                    for v in violations
                )
            )

    def test_delay_zero_always_valid(self) -> None:
        """Delay 0 should always be in valid_delays (primary alignment)."""
        cs = generate_countersubject(SUBJECT_UNIFORM)
        assert cs is not None

        assert Fraction(0) in cs.valid_delays, (
            f"Delay 0 not in valid_delays: {cs.valid_delays}"
        )


class TestStrictForbiddenDegrees:
    """Verify forbidden degrees are never used."""

    @pytest.mark.parametrize("subject", [
        SUBJECT_UNIFORM,
        SUBJECT_MIXED,
        SUBJECT_SYNCOPATED,
        SUBJECT_BACH_1,
        SUBJECT_ASCENDING,
        SUBJECT_ARPEGGIO,
    ])
    def test_no_degree_7_in_major(self, subject: Subject) -> None:
        """CS must not use degree 7 in major mode."""
        cs = generate_countersubject(subject, timeout_seconds=15.0)
        assert cs is not None, f"Failed to generate CS for {subject.degrees}"

        assert 7 not in cs.degrees, (
            f"Degree 7 found in major mode CS: {cs.degrees}"
        )

    def test_no_degree_6_or_7_in_minor(self) -> None:
        """CS must not use degrees 6 or 7 in minor mode."""
        cs = generate_countersubject(SUBJECT_MINOR, timeout_seconds=15.0)
        assert cs is not None

        assert 6 not in cs.degrees, f"Degree 6 found in minor mode CS: {cs.degrees}"
        assert 7 not in cs.degrees, f"Degree 7 found in minor mode CS: {cs.degrees}"


class TestStrictIntervalClassification:
    """Verify interval classification is correct."""

    def test_consonance_set_is_correct(self) -> None:
        """ALL_CONSONANCES should contain exactly the consonant intervals."""
        # Perfect consonances: unison (0), fifth (7)
        # Imperfect consonances: minor 3rd (3), major 3rd (4), minor 6th (8), major 6th (9)
        expected = {0, 3, 4, 7, 8, 9}
        assert ALL_CONSONANCES == expected, (
            f"ALL_CONSONANCES mismatch: got {ALL_CONSONANCES}, expected {expected}"
        )

    def test_dissonances_are_excluded(self) -> None:
        """Dissonant intervals should not be in ALL_CONSONANCES."""
        dissonances = {1, 2, 5, 6, 10, 11}  # 2nds, 4ths, tritone, 7ths
        for d in dissonances:
            assert d not in ALL_CONSONANCES, f"Dissonant interval {d} in consonances"

    def test_interval_class_symmetric(self) -> None:
        """Interval class should be symmetric (|A-B| = |B-A|)."""
        for d1 in range(1, 8):
            for d2 in range(1, 8):
                ic1 = _interval_class(d1, d2, MAJOR_SCALE)
                ic2 = _interval_class(d2, d1, MAJOR_SCALE)
                assert ic1 == ic2, f"Asymmetric interval: {d1},{d2} -> {ic1} vs {ic2}"


class TestStrictEdgeCases:
    """Edge cases that might expose bugs."""

    def test_first_note_consonance(self) -> None:
        """First note of CS must be consonant with first note of subject."""
        for subject in [SUBJECT_UNIFORM, SUBJECT_MIXED, SUBJECT_SYNCOPATED]:
            cs = generate_countersubject(subject)
            assert cs is not None

            ic = _interval_class(subject.degrees[0], cs.degrees[0], subject.scale)
            assert ic in ALL_CONSONANCES, (
                f"First note dissonance: subj={subject.degrees[0]}, "
                f"cs={cs.degrees[0]}, ic={ic}"
            )

    def test_last_note_consonance(self) -> None:
        """Last note of CS must be consonant with subject note at that time."""
        for subject in [SUBJECT_UNIFORM, SUBJECT_MIXED, SUBJECT_SHORT]:
            cs = generate_countersubject(subject)
            assert cs is not None

            # Find what subject degree is sounding at CS end
            cs_end_time = cs.total_duration - Fraction(1, 32)  # Just before end

            subj_pos = Fraction(0)
            subj_deg_at_end = None
            for deg, dur in zip(subject.degrees, subject.durations):
                if subj_pos <= cs_end_time < subj_pos + dur:
                    subj_deg_at_end = deg
                    break
                subj_pos += dur

            if subj_deg_at_end is not None:
                ic = _interval_class(subj_deg_at_end, cs.degrees[-1], subject.scale)
                assert ic in ALL_CONSONANCES, (
                    f"Last note dissonance: subj={subj_deg_at_end}, "
                    f"cs={cs.degrees[-1]}, ic={ic}"
                )

    def test_syncopation_crossing_consonance(self) -> None:
        """When CS note sustains across subject attack, must be consonant."""
        # Use syncopated subject where CS might have long notes
        cs = generate_countersubject(SUBJECT_SYNCOPATED)
        assert cs is not None

        # Check all subject attack points
        violations = verify_consonance_at_subject_attacks(SUBJECT_SYNCOPATED, cs)
        assert len(violations) == 0, f"Syncopation violations: {violations}"

    def test_uniform_against_varied(self) -> None:
        """Uniform rhythm CS against varied subject must maintain consonance."""
        cs = generate_countersubject(SUBJECT_MIXED)
        assert cs is not None

        violations = verify_all_alignment_points(SUBJECT_MIXED, cs)
        assert len(violations) == 0, f"Alignment violations: {violations}"


class TestStrictManySubjects:
    """Generate many random-ish subjects to stress test."""

    @pytest.mark.parametrize("degrees,durations,mode", [
        # Stepwise ascending (more notes for feasibility)
        ((1, 2, 3, 4, 5, 4, 3), (Fraction(1, 8),) * 7, "major"),
        # Stepwise descending (more notes for feasibility)
        ((5, 4, 3, 2, 1, 2, 3), (Fraction(1, 8),) * 7, "major"),
        # Arpeggio up
        ((1, 3, 5, 1, 3, 5), (Fraction(1, 8),) * 6, "major"),
        # Mixed leaps
        ((1, 5, 3, 6, 4, 2, 1), (Fraction(1, 8),) * 7, "major"),
        # Repeated notes
        ((1, 1, 2, 2, 3, 3, 2, 1), (Fraction(1, 8),) * 8, "major"),
        # Large range
        ((1, 6, 2, 5, 3, 4, 1), (Fraction(1, 8),) * 7, "major"),
        # Minor arpeggio
        ((1, 3, 5, 3, 1), (Fraction(1, 4),) * 5, "minor"),
        # Minor stepwise (more notes for feasibility)
        ((5, 4, 3, 2, 1, 2, 3), (Fraction(1, 8),) * 7, "minor"),
        # Dotted rhythm
        ((1, 2, 3, 4), (Fraction(3, 8), Fraction(1, 8), Fraction(3, 8), Fraction(1, 8)), "major"),
        # Long and short
        ((1, 2, 3, 4, 5), (Fraction(1, 2), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)), "major"),
    ])
    def test_varied_subjects(
        self, degrees: tuple, durations: tuple, mode: str
    ) -> None:
        """Test consonance for various subject patterns."""
        subject = Subject(degrees=degrees, durations=durations, mode=mode)
        cs = generate_countersubject(subject, timeout_seconds=15.0)

        assert cs is not None, f"Failed to generate CS for {degrees}"
        assert cs.total_duration == subject.total_duration

        violations = verify_all_alignment_points(subject, cs)
        assert len(violations) == 0, (
            f"Dissonance for {degrees}:\n"
            + "\n".join(
                f"  t={v[0]}: subj={v[1]}, cs={v[2]}, ic={v[3]}"
                for v in violations
            )
        )


class TestStrictDeterminism:
    """Verify solver produces valid solutions consistently.

    Note: CP-SAT with multiple workers may produce different valid solutions.
    What matters is that all solutions satisfy constraints.
    """

    def test_multiple_runs_all_valid(self) -> None:
        """Multiple runs should all produce valid (consonant) counter-subjects."""
        for _ in range(3):
            cs = generate_countersubject(SUBJECT_UNIFORM)
            assert cs is not None

            # Verify each solution is valid
            violations = verify_all_alignment_points(SUBJECT_UNIFORM, cs)
            assert len(violations) == 0, f"Invalid solution: {violations}"

            # Verify duration matches
            assert cs.total_duration == SUBJECT_UNIFORM.total_duration


class TestStrictInvertibility:
    """Verify counter-subjects work when inverted."""

    @pytest.mark.parametrize("subject", [
        SUBJECT_UNIFORM,
        SUBJECT_MIXED,
        SUBJECT_SHORT,
    ])
    def test_inverted_consonance(self, subject: Subject) -> None:
        """When CS becomes bass, intervals should mostly be consonant.

        Interval inversion: new_ic = (12 - old_ic) % 12
        5th (7) -> 4th (5) which is dissonant
        """
        cs = generate_countersubject(subject)
        assert cs is not None

        scale = subject.scale
        dissonance_count = 0
        total_checks = 0

        # Check at aligned positions (simplified check)
        min_len = min(len(subject.degrees), len(cs.degrees))
        for i in range(min_len):
            subj_semi = _degree_to_semitone(subject.degrees[i], scale)
            cs_semi = _degree_to_semitone(cs.degrees[i], scale)
            original_ic = abs(cs_semi - subj_semi) % 12

            # Inverted interval
            inverted_ic = (12 - original_ic) % 12

            total_checks += 1
            if inverted_ic not in ALL_CONSONANCES:
                dissonance_count += 1

        # Allow some dissonance but not majority (fifths become 4ths when inverted)
        # Threshold is <= 50% because fifths are penalized but not forbidden
        if total_checks > 0:
            dissonance_ratio = dissonance_count / total_checks
            assert dissonance_ratio <= 0.5, (
                f"Too many inverted dissonances: {dissonance_count}/{total_checks} "
                f"({dissonance_ratio:.1%})"
            )
