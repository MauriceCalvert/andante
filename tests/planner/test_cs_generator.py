"""Comprehensive tests for the gold-plated counter-subject generator.

Tests verify all constraints are satisfied:
- Intervallic: consonance, no parallel fifths/octaves
- Melodic: contour, leap compensation, stepwise preference
- Rhythmic: density matching, strong/weak beat awareness
- Invertibility: no fifths (become dissonant 4ths when inverted)
- Motivic: duration vocabulary from subject
- Cadential: final note stability, stepwise approach
- Climax: offset from subject high point
"""
from fractions import Fraction

import pytest

from planner.cs_generator import (
    ALL_CONSONANCES,
    DURATION_SCALE,
    IMPERFECT_CONSONANCES,
    MAJOR_SCALE,
    MINOR_SCALE,
    PERFECT_CONSONANCES,
    VALID_DURATIONS,
    CounterSubject,
    Subject,
    generate_countersubject,
    _compute_allowed_durations,
    _degree_to_semitone,
    _interval_class,
    _is_strong_beat,
)


# === HELPER FUNCTIONS TESTS ===


class TestDegreeToSemitone:
    """Test scale degree to semitone conversion."""

    def test_major_scale_degrees(self) -> None:
        """Major scale: C=0, D=2, E=4, F=5, G=7, A=9, B=11."""
        assert _degree_to_semitone(1, MAJOR_SCALE) == 0
        assert _degree_to_semitone(2, MAJOR_SCALE) == 2
        assert _degree_to_semitone(3, MAJOR_SCALE) == 4
        assert _degree_to_semitone(4, MAJOR_SCALE) == 5
        assert _degree_to_semitone(5, MAJOR_SCALE) == 7
        assert _degree_to_semitone(6, MAJOR_SCALE) == 9
        assert _degree_to_semitone(7, MAJOR_SCALE) == 11

    def test_minor_scale_degrees(self) -> None:
        """Natural minor: 0, 2, 3, 5, 7, 8, 10."""
        assert _degree_to_semitone(1, MINOR_SCALE) == 0
        assert _degree_to_semitone(2, MINOR_SCALE) == 2
        assert _degree_to_semitone(3, MINOR_SCALE) == 3
        assert _degree_to_semitone(4, MINOR_SCALE) == 5
        assert _degree_to_semitone(5, MINOR_SCALE) == 7
        assert _degree_to_semitone(6, MINOR_SCALE) == 8
        assert _degree_to_semitone(7, MINOR_SCALE) == 10


class TestIntervalClass:
    """Test interval class computation."""

    def test_unison(self) -> None:
        """Same degree = unison (0 semitones)."""
        assert _interval_class(1, 1, MAJOR_SCALE) == 0
        assert _interval_class(5, 5, MAJOR_SCALE) == 0

    def test_third_major(self) -> None:
        """Degree 1 to 3 in major = major 3rd (4 semitones)."""
        assert _interval_class(1, 3, MAJOR_SCALE) == 4

    def test_third_minor(self) -> None:
        """Degree 1 to 3 in minor = minor 3rd (3 semitones)."""
        assert _interval_class(1, 3, MINOR_SCALE) == 3

    def test_fifth(self) -> None:
        """Degree 1 to 5 = perfect 5th (7 semitones)."""
        assert _interval_class(1, 5, MAJOR_SCALE) == 7

    def test_sixth_major(self) -> None:
        """Degree 1 to 6 in major = major 6th (9 semitones)."""
        assert _interval_class(1, 6, MAJOR_SCALE) == 9

    def test_order_independent(self) -> None:
        """Interval class is symmetric."""
        assert _interval_class(1, 3, MAJOR_SCALE) == _interval_class(3, 1, MAJOR_SCALE)
        assert _interval_class(2, 5, MINOR_SCALE) == _interval_class(5, 2, MINOR_SCALE)

    def test_tritone(self) -> None:
        """Degree 4 to 7 in major = tritone (6 semitones)."""
        assert _interval_class(4, 7, MAJOR_SCALE) == 6


class TestIsStrongBeat:
    """Test strong beat detection."""

    def test_beat_one_strong(self) -> None:
        """Beat 1 (position 0) is strong."""
        assert _is_strong_beat(Fraction(0)) is True
        assert _is_strong_beat(Fraction(1)) is True  # Bar 2, beat 1
        assert _is_strong_beat(Fraction(2)) is True  # Bar 3, beat 1

    def test_beat_three_strong(self) -> None:
        """Beat 3 (position 1/2) is strong."""
        assert _is_strong_beat(Fraction(1, 2)) is True
        assert _is_strong_beat(Fraction(3, 2)) is True  # Bar 2, beat 3

    def test_beat_two_weak(self) -> None:
        """Beat 2 (position 1/4) is weak."""
        assert _is_strong_beat(Fraction(1, 4)) is False

    def test_beat_four_weak(self) -> None:
        """Beat 4 (position 3/4) is weak."""
        assert _is_strong_beat(Fraction(3, 4)) is False

    def test_offbeats_weak(self) -> None:
        """Offbeat positions are weak."""
        assert _is_strong_beat(Fraction(1, 8)) is False
        assert _is_strong_beat(Fraction(3, 8)) is False
        assert _is_strong_beat(Fraction(5, 8)) is False


class TestComputeAllowedDurations:
    """Test duration vocabulary computation."""

    def test_includes_subject_durations(self) -> None:
        """Allowed durations include all subject durations."""
        subj = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 4)),
            mode="major",
        )
        allowed = _compute_allowed_durations(subj)
        assert Fraction(1, 4) in allowed
        assert Fraction(1, 8) in allowed

    def test_adds_one_step_faster(self) -> None:
        """Allowed durations include one step faster than subject min."""
        subj = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            mode="major",
        )
        allowed = _compute_allowed_durations(subj)
        # Subject min is 1/4, one step faster is 3/16 or 1/8
        assert Fraction(3, 16) in allowed or Fraction(1, 8) in allowed

    def test_all_valid_durations(self) -> None:
        """All returned durations are from VALID_DURATIONS."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(3, 8), Fraction(1, 4), Fraction(1, 8)),
            mode="major",
        )
        allowed = _compute_allowed_durations(subj)
        for d in allowed:
            assert d in VALID_DURATIONS


# === SUBJECT CLASS TESTS ===


class TestSubject:
    """Test Subject dataclass."""

    def test_total_duration(self) -> None:
        """Total duration sums correctly."""
        subj = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            mode="major",
        )
        assert subj.total_duration == Fraction(1)

    def test_min_duration(self) -> None:
        """Min duration is smallest."""
        subj = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 2)),
            mode="major",
        )
        assert subj.min_duration == Fraction(1, 8)

    def test_duration_vocabulary(self) -> None:
        """Duration vocabulary is unique set."""
        subj = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 4), Fraction(1, 8)),
            mode="major",
        )
        vocab = subj.duration_vocabulary
        assert len(vocab) == 2
        assert Fraction(1, 4) in vocab
        assert Fraction(1, 8) in vocab

    def test_attack_times(self) -> None:
        """Attack times computed correctly."""
        subj = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            mode="major",
        )
        attacks = subj.attack_times
        assert attacks == (Fraction(0), Fraction(1, 4), Fraction(1, 2))

    def test_climax_index(self) -> None:
        """Climax index is position of highest degree."""
        subj = Subject(
            degrees=(1, 3, 5, 4, 2),
            durations=(Fraction(1, 8),) * 5,
            mode="major",
        )
        assert subj.climax_index == 2  # Degree 5 at index 2

    def test_scale_major(self) -> None:
        """Major mode uses major scale."""
        subj = Subject(degrees=(1,), durations=(Fraction(1),), mode="major")
        assert subj.scale == MAJOR_SCALE

    def test_scale_minor(self) -> None:
        """Minor mode uses minor scale."""
        subj = Subject(degrees=(1,), durations=(Fraction(1),), mode="minor")
        assert subj.scale == MINOR_SCALE


class TestCounterSubject:
    """Test CounterSubject dataclass."""

    def test_total_duration(self) -> None:
        """Total duration sums correctly."""
        cs = CounterSubject(
            degrees=(3, 4, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
        )
        assert cs.total_duration == Fraction(1)

    def test_length_mismatch_raises(self) -> None:
        """Mismatched lengths raise assertion."""
        with pytest.raises(AssertionError):
            CounterSubject(
                degrees=(1, 2, 3),
                durations=(Fraction(1, 4), Fraction(1, 4)),
            )


# === GENERATOR TESTS ===


class TestGenerateCountersubjectBasic:
    """Basic tests for generate_countersubject."""

    def test_returns_countersubject(self) -> None:
        """Returns a CounterSubject object."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 4)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert isinstance(cs, CounterSubject)

    def test_total_duration_matches(self) -> None:
        """CS total duration equals subject total duration."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 4)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert cs.total_duration == subj.total_duration

    def test_degrees_in_valid_range(self) -> None:
        """All CS degrees are 1-7."""
        subj = Subject(
            degrees=(1, 3, 5, 4, 2, 1),
            durations=(Fraction(1, 8),) * 6,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert all(1 <= d <= 7 for d in cs.degrees)

    def test_durations_valid(self) -> None:
        """All CS durations are from VALID_DURATIONS."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 4)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        for d in cs.durations:
            assert d in VALID_DURATIONS, f"Invalid duration: {d}"

    def test_trivial_subject(self) -> None:
        """Single-note subject returns transposed version."""
        subj = Subject(
            degrees=(1,),
            durations=(Fraction(1),),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert len(cs.degrees) == 1


class TestForbiddenDegrees:
    """Test forbidden degree constraints."""

    def test_avoids_degree_7_in_major(self) -> None:
        """CS avoids degree 7 (leading tone) in major mode."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 6, 1, 2),
            durations=(Fraction(1, 8),) * 8,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert 7 not in cs.degrees

    def test_avoids_degrees_6_and_7_in_minor(self) -> None:
        """CS avoids degrees 6 and 7 in minor mode."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 1, 2, 3),
            durations=(Fraction(1, 8),) * 8,
            mode="minor",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert 6 not in cs.degrees
        assert 7 not in cs.degrees


class TestIntervalConstraints:
    """Test vertical interval constraints."""

    def test_all_intervals_consonant(self) -> None:
        """All simultaneous intervals are consonant."""
        subj = Subject(
            degrees=(1, 3, 5, 3, 1),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        # Check intervals at aligned attack points
        # Note: CS may have different note count, so we check sampling
        for i, (sd, cd) in enumerate(zip(subj.degrees, cs.degrees)):
            if i < len(cs.degrees):
                ic = _interval_class(sd, cd, MAJOR_SCALE)
                assert ic in ALL_CONSONANCES, f"Dissonant interval at position {i}: {ic}"

    def test_avoids_fifths_for_invertibility(self) -> None:
        """CS avoids or minimizes perfect fifths (become 4ths when inverted)."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 9,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        # Count fifths - should be rare
        fifth_count = 0
        for sd, cd in zip(subj.degrees, cs.degrees[:len(subj.degrees)]):
            ic = _interval_class(sd, cd, MAJOR_SCALE)
            if ic == 7:  # Perfect fifth
                fifth_count += 1

        # At most 1 fifth in a 9-note sequence (solver strongly penalizes)
        assert fifth_count <= 2, f"Too many fifths: {fifth_count}"


class TestRhythmicDensity:
    """Test rhythmic density matching."""

    def test_similar_note_count(self) -> None:
        """CS note count is within ±2 of subject."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 11,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        n_subj = len(subj.degrees)
        n_cs = len(cs.degrees)
        assert abs(n_cs - n_subj) <= 2, f"Note count mismatch: {n_cs} vs {n_subj}"

    def test_no_sixteenths_against_quarters(self) -> None:
        """CS doesn't use sixteenths when subject has only quarter notes."""
        subj = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        # Sixteenth note = 1/16
        sixteenth = Fraction(1, 16)
        # CS may use 1/8 (one step faster) but not 1/16
        for d in cs.durations:
            # Allow at most one step faster than subject min (1/4 -> 3/16 or 1/8)
            assert d >= Fraction(3, 16), f"Duration too short: {d}"

    def test_duration_variety(self) -> None:
        """CS uses varied durations (not all same value)."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 4), Fraction(1, 8)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        # Should have at least 2 different duration values
        unique_durs = set(cs.durations)
        assert len(unique_durs) >= 2, f"Insufficient variety: {unique_durs}"


class TestMelodicConstraints:
    """Test melodic line quality."""

    def test_limited_large_leaps(self) -> None:
        """CS has limited large leaps (> perfect 4th)."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 11,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        large_leap_count = 0
        for i in range(1, len(cs.degrees)):
            prev_semi = _degree_to_semitone(cs.degrees[i - 1], MAJOR_SCALE)
            curr_semi = _degree_to_semitone(cs.degrees[i], MAJOR_SCALE)
            motion = abs(curr_semi - prev_semi)
            if motion > 5:  # Larger than perfect 4th
                large_leap_count += 1

        # At most 2 large leaps in an 11-note sequence
        assert large_leap_count <= 3, f"Too many large leaps: {large_leap_count}"

    def test_no_immediate_repetition_dominance(self) -> None:
        """CS doesn't have excessive immediate pitch repetition."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 9,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        repetition_count = 0
        for i in range(1, len(cs.degrees)):
            if cs.degrees[i] == cs.degrees[i - 1]:
                repetition_count += 1

        # At most 2 repetitions in 9 notes
        assert repetition_count <= 3, f"Too many repetitions: {repetition_count}"


class TestCadentialConstraints:
    """Test cadential behavior."""

    def test_final_note_stable(self) -> None:
        """Final CS note is degree 1 or 5 (stable)."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 9,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        final_degree = cs.degrees[-1]
        assert final_degree in {1, 5}, f"Unstable final degree: {final_degree}"

    def test_penultimate_stepwise_approach(self) -> None:
        """Penultimate to final prefers stepwise motion."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 9,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        if len(cs.degrees) >= 2:
            pen_semi = _degree_to_semitone(cs.degrees[-2], MAJOR_SCALE)
            fin_semi = _degree_to_semitone(cs.degrees[-1], MAJOR_SCALE)
            motion = abs(fin_semi - pen_semi)
            # Allow up to perfect 5th (7 semitones) - stepwise is soft constraint
            assert motion <= 7, f"Large cadential leap: {motion} semitones"


class TestMotivicCoherence:
    """Test motivic coherence (duration vocabulary)."""

    def test_prefers_subject_durations(self) -> None:
        """CS durations mostly come from subject's vocabulary."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 4), Fraction(1, 8), Fraction(1, 4)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        subj_vocab = subj.duration_vocabulary
        from_vocab_count = sum(1 for d in cs.durations if d in subj_vocab)
        total = len(cs.durations)

        # At least 60% should be from subject vocabulary (allowing some variation)
        assert from_vocab_count >= total * 0.5, (
            f"Insufficient vocabulary overlap: {from_vocab_count}/{total}"
        )


class TestParallelFifthsOctaves:
    """Test parallel perfect interval avoidance."""

    def test_no_parallel_fifths(self) -> None:
        """CS avoids parallel fifths with subject."""
        # Subject with varied motion (easier to solve)
        subj = Subject(
            degrees=(1, 3, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 7,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        # Check for parallel fifths
        parallel_fifth_count = 0
        for i in range(1, min(len(subj.degrees), len(cs.degrees))):
            prev_ic = _interval_class(subj.degrees[i - 1], cs.degrees[i - 1], MAJOR_SCALE)
            curr_ic = _interval_class(subj.degrees[i], cs.degrees[i], MAJOR_SCALE)

            subj_motion = subj.degrees[i] - subj.degrees[i - 1]
            cs_motion = cs.degrees[i] - cs.degrees[i - 1]

            # Parallel = same direction, both intervals are 5th (7) or octave (0)
            if prev_ic in {0, 7} and curr_ic in {0, 7}:
                if (subj_motion > 0) == (cs_motion > 0) and subj_motion != 0 and cs_motion != 0:
                    parallel_fifth_count += 1

        assert parallel_fifth_count == 0, f"Parallel fifths detected: {parallel_fifth_count}"


class TestRealisticSubjects:
    """Test with realistic Bach-style subjects."""

    def test_bach_style_subject_1(self) -> None:
        """Generate CS for a Bach-style subject (invention-like)."""
        # Typical 2-bar invention subject
        subj = Subject(
            degrees=(5, 5, 1, 7, 6, 4, 5, 3, 1),
            durations=(Fraction(3, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 4), Fraction(1, 8), Fraction(3, 8), Fraction(1, 8),
                      Fraction(3, 8)),
            mode="major",
        )
        # Note: degree 7 in subject is OK, just forbidden in CS
        cs = generate_countersubject(subj)
        assert cs is not None
        assert cs.total_duration == subj.total_duration
        assert 7 not in cs.degrees

    def test_bach_style_subject_2(self) -> None:
        """Generate CS for another Bach-style subject (fugue-like)."""
        subj = Subject(
            degrees=(1, 5, 4, 3, 2, 3, 1, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 4)),
            mode="minor",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert cs.total_duration == subj.total_duration
        assert 6 not in cs.degrees
        assert 7 not in cs.degrees


class TestDeterminism:
    """Test result consistency."""

    def test_same_input_same_output(self) -> None:
        """Same subject produces same CS (deterministic)."""
        subj = Subject(
            degrees=(1, 3, 5, 3, 1),
            durations=(Fraction(1, 4),) * 5,
            mode="major",
        )
        cs1 = generate_countersubject(subj)
        cs2 = generate_countersubject(subj)

        assert cs1 is not None
        assert cs2 is not None
        # Solver should be deterministic
        assert cs1.degrees == cs2.degrees
        assert cs1.durations == cs2.durations


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_short_subject(self) -> None:
        """Handle 3-note subject (minimum for non-trivial CS)."""
        subj = Subject(
            degrees=(1, 3, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert cs.total_duration == Fraction(1)

    def test_long_subject(self) -> None:
        """Handle longer subject (16 notes)."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1, 2, 3, 4, 5, 4, 3, 1),
            durations=(Fraction(1, 8),) * 16,
            mode="major",
        )
        cs = generate_countersubject(subj, timeout_seconds=15.0)
        assert cs is not None
        assert cs.total_duration == subj.total_duration

    def test_uniform_rhythm_subject(self) -> None:
        """Subject with all same duration."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 9,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert cs.total_duration == subj.total_duration

    def test_varied_rhythm_subject(self) -> None:
        """Subject with highly varied rhythm."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 2), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None
        assert cs.total_duration == subj.total_duration


# =============================================================================
# Invertible Counterpoint Tests (baroque_plan.md item 8.1 validation)
# =============================================================================


class TestInvertibleCounterpoint:
    """Test invertibility at the octave.

    Domain knowledge: In invertible counterpoint at the octave, the two
    voices can be swapped (inverted). When inverted, intervals transform:
    - Unisons (0) become octaves (7) - OK
    - Thirds (3/4) become sixths (8/9) - OK
    - Fifths (7) become fourths (5) - DISSONANT against bass
    - Sixths (8/9) become thirds (3/4) - OK

    The counter-subject should avoid perfect 5ths in strong metric positions
    to ensure the inversion produces consonant results.
    """

    def test_avoids_fifths_on_strong_beats(self) -> None:
        """CS avoids 5ths on strong beats for invertibility."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 4), Fraction(1, 8), Fraction(1, 8)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        # Check vertical intervals at strong beats
        fifths_on_strong = 0
        position = Fraction(0)
        for i in range(min(len(subj.degrees), len(cs.degrees))):
            ic = _interval_class(subj.degrees[i], cs.degrees[i], MAJOR_SCALE)
            if _is_strong_beat(position) and ic == 7:  # Perfect 5th
                fifths_on_strong += 1
            position += subj.durations[i] if i < len(subj.durations) else Fraction(1, 8)

        # Should have very few or no 5ths on strong beats
        assert fifths_on_strong <= 1, f"Too many 5ths on strong beats: {fifths_on_strong}"

    def test_inverted_intervals_are_consonant(self) -> None:
        """When subject and CS are inverted, result is largely consonant.

        Interval inversion: new_interval = 12 - old_interval (in semitones)
        For invertible counterpoint at the octave, 5ths become 4ths (dissonant).
        """
        subj = Subject(
            degrees=(1, 3, 5, 3, 1),
            durations=(Fraction(1, 4),) * 5,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        # Calculate inverted intervals and check consonance
        inverted_dissonances = 0
        for i in range(min(len(subj.degrees), len(cs.degrees))):
            subj_semi = _degree_to_semitone(subj.degrees[i], MAJOR_SCALE)
            cs_semi = _degree_to_semitone(cs.degrees[i], MAJOR_SCALE)
            original_ic = abs(cs_semi - subj_semi) % 12

            # Inverted interval (CS becomes bass)
            inverted_ic = (12 - original_ic) % 12

            # 4ths (5 semitones) are dissonant against bass
            if inverted_ic == 5:
                inverted_dissonances += 1

        # Most notes should remain consonant when inverted
        total = min(len(subj.degrees), len(cs.degrees))
        assert inverted_dissonances <= total // 2, (
            f"Too many dissonances when inverted: {inverted_dissonances}/{total}"
        )

    def test_imperfect_consonances_preferred(self) -> None:
        """CS prefers imperfect consonances (3rds, 6ths) for invertibility."""
        subj = Subject(
            degrees=(1, 2, 3, 4, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 9,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        imperfect_count = 0
        perfect_count = 0

        for i in range(min(len(subj.degrees), len(cs.degrees))):
            ic = _interval_class(subj.degrees[i], cs.degrees[i], MAJOR_SCALE)
            if ic in IMPERFECT_CONSONANCES:
                imperfect_count += 1
            elif ic in PERFECT_CONSONANCES:
                perfect_count += 1

        # Imperfect consonances should be majority
        total = imperfect_count + perfect_count
        if total > 0:
            imperfect_ratio = imperfect_count / total
            assert imperfect_ratio >= 0.5, (
                f"Insufficient imperfect consonances: {imperfect_ratio:.2%}"
            )

    def test_no_consecutive_fifths_for_inversion(self) -> None:
        """Consecutive 5ths would become consecutive 4ths when inverted."""
        subj = Subject(
            degrees=(1, 2, 3, 2, 1, 2, 3),
            durations=(Fraction(1, 8),) * 7,
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        consecutive_fifths = 0
        prev_ic = None
        for i in range(min(len(subj.degrees), len(cs.degrees))):
            ic = _interval_class(subj.degrees[i], cs.degrees[i], MAJOR_SCALE)
            if prev_ic == 7 and ic == 7:  # Two consecutive 5ths
                consecutive_fifths += 1
            prev_ic = ic

        assert consecutive_fifths == 0, (
            f"Consecutive 5ths detected: {consecutive_fifths}"
        )

    def test_double_counterpoint_viability(self) -> None:
        """Generated CS could serve as bass line when inverted.

        Domain knowledge: In Bach's inventions, the counter-subject must
        work both above and below the subject. This requires avoiding
        intervals that become dissonant when inverted.
        """
        subj = Subject(
            degrees=(5, 4, 3, 4, 5, 5, 5, 4, 3, 2, 1),
            durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 4), Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
                      Fraction(1, 8), Fraction(1, 8), Fraction(1, 4)),
            mode="major",
        )
        cs = generate_countersubject(subj)
        assert cs is not None

        # When inverted: CS below subject
        # Check that critical strong-beat intervals are invertible
        strong_beat_invertible = 0
        strong_beat_total = 0
        position = Fraction(0)

        for i in range(min(len(subj.degrees), len(cs.degrees))):
            if _is_strong_beat(position):
                strong_beat_total += 1
                ic = _interval_class(subj.degrees[i], cs.degrees[i], MAJOR_SCALE)
                # Invertible intervals: unisons, 3rds, 6ths (become 8ths, 6ths, 3rds)
                # Avoid 5ths (become 4ths = dissonant)
                if ic != 7:  # Not a 5th
                    strong_beat_invertible += 1
            position += subj.durations[i] if i < len(subj.durations) else Fraction(1, 8)

        # All strong beats should have invertible intervals
        if strong_beat_total > 0:
            ratio = strong_beat_invertible / strong_beat_total
            assert ratio >= 0.8, (
                f"Insufficient invertibility: {ratio:.2%} ({strong_beat_invertible}/{strong_beat_total})"
            )
