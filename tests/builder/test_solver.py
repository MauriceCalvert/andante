"""Tests for builder.solver module.

Category A tests: Pure functions, specification-based.

Specification source: solver_specs.md
- CP-SAT solver finds valid pitch sequences
- Anchors constrain specific positions
- Solution respects pitch class set and tessitura
- Determinism: same inputs produce same outputs
"""
from fractions import Fraction

import pytest

from builder.solver import (
    solve,
    Anchor,
    Slot,
    SolverConfig,
    Solution,
    _validate_inputs,
    _compute_domain,
)
from builder.costs import VoiceMode
from shared.errors import SolverInfeasibleError


# Default test configuration
C_MAJOR: frozenset[int] = frozenset({0, 2, 4, 5, 7, 9, 11})
DEFAULT_WEIGHTS: dict[str, float] = {
    "step": 0.2,
    "skip": 0.4,
    "leap": 0.8,
    "large_leap": 1.5,
}
DEFAULT_MEDIANS: dict[int, int] = {0: 70, 1: 48}
DEFAULT_SPAN: int = 12


def make_config(
    voice_count: int = 2,
    pitch_class_set: frozenset[int] = C_MAJOR,
    tessitura_medians: dict[int, int] | None = None,
    tessitura_span: int = DEFAULT_SPAN,
    invertible_at: int | None = None,
    voice_mode: VoiceMode = VoiceMode.STANDARD,
    motive_weights: dict[str, float] | None = None,
    metre_numerator: int = 4,
) -> SolverConfig:
    """Helper to create SolverConfig."""
    return SolverConfig(
        voice_count=voice_count,
        pitch_class_set=pitch_class_set,
        tessitura_medians=tessitura_medians or DEFAULT_MEDIANS,
        tessitura_span=tessitura_span,
        invertible_at=invertible_at,
        voice_mode=voice_mode,
        motive_weights=motive_weights or DEFAULT_WEIGHTS,
        metre_numerator=metre_numerator,
    )


class TestValidateInputs:
    """Tests for _validate_inputs function."""

    def test_valid_inputs_pass(self) -> None:
        config = make_config()
        slots = [
            Slot(Fraction(0), 0, Fraction(1, 4)),
            Slot(Fraction(0), 1, Fraction(1, 4)),
        ]
        anchors = [Anchor(Fraction(0), 0, 72)]
        _validate_inputs(anchors, slots, config)  # Should not raise

    def test_invalid_voice_count_fails(self) -> None:
        config = SolverConfig(
            voice_count=5,  # Invalid
            pitch_class_set=C_MAJOR,
            tessitura_medians={0: 70, 1: 60, 2: 55, 3: 48, 4: 40},
            tessitura_span=12,
            invertible_at=None,
            voice_mode=VoiceMode.STANDARD,
            motive_weights=DEFAULT_WEIGHTS,
            metre_numerator=4,
        )
        with pytest.raises(AssertionError):
            _validate_inputs([], [], config)

    def test_anchor_voice_out_of_range_fails(self) -> None:
        config = make_config(voice_count=2)
        anchors = [Anchor(Fraction(0), 5, 72)]  # Voice 5 out of range for 2 voices
        slots = [Slot(Fraction(0), 0, Fraction(1, 4))]
        with pytest.raises(AssertionError):
            _validate_inputs(anchors, slots, config)

    def test_anchor_pitch_not_in_set_fails(self) -> None:
        config = make_config()
        anchors = [Anchor(Fraction(0), 0, 61)]  # C#, not in C major
        slots = [Slot(Fraction(0), 0, Fraction(1, 4))]
        with pytest.raises(AssertionError):
            _validate_inputs(anchors, slots, config)

    def test_invalid_invertible_at_fails(self) -> None:
        config = SolverConfig(
            voice_count=2,
            pitch_class_set=C_MAJOR,
            tessitura_medians=DEFAULT_MEDIANS,
            tessitura_span=12,
            invertible_at=8,  # Invalid, must be 10 or 12
            voice_mode=VoiceMode.STANDARD,
            motive_weights=DEFAULT_WEIGHTS,
            metre_numerator=4,
        )
        with pytest.raises(AssertionError):
            _validate_inputs([], [], config)


class TestComputeDomain:
    """Tests for _compute_domain function."""

    def test_domain_within_span(self) -> None:
        config = make_config(tessitura_span=12)
        domain = _compute_domain(0, config)
        median = DEFAULT_MEDIANS[0]  # 70
        for pitch in domain:
            assert median - 12 <= pitch <= median + 12
            assert pitch % 12 in C_MAJOR

    def test_domain_respects_pitch_class_set(self) -> None:
        config = make_config()
        domain = _compute_domain(0, config)
        for pitch in domain:
            assert pitch % 12 in C_MAJOR

    def test_different_voices_different_domains(self) -> None:
        config = make_config()
        soprano_domain = _compute_domain(0, config)  # median 70
        bass_domain = _compute_domain(1, config)  # median 48
        # Domains should be mostly disjoint given different medians
        soprano_set = set(soprano_domain)
        bass_set = set(bass_domain)
        assert soprano_set != bass_set


class TestSolve:
    """Tests for solve function."""

    def test_solve_respects_single_anchor(self) -> None:
        """Solver places anchor at correct position."""
        config = make_config()
        slots = [
            Slot(Fraction(0), 0, Fraction(1, 4)),
            Slot(Fraction(0), 1, Fraction(1, 4)),
            Slot(Fraction(1, 4), 0, Fraction(1, 4)),
            Slot(Fraction(1, 4), 1, Fraction(1, 4)),
        ]
        anchors = [
            Anchor(Fraction(0), 0, 72),  # C5 - soprano
            Anchor(Fraction(0), 1, 48),  # C3 - bass
        ]
        solution = solve(anchors, slots, config)
        assert solution.pitches[(Fraction(0), 0)] == 72
        assert solution.pitches[(Fraction(0), 1)] == 48

    def test_solve_respects_multiple_anchors(self) -> None:
        """Solver places multiple anchors correctly."""
        config = make_config()
        # All slots are anchored to avoid complexity with intermediate notes
        slots = [
            Slot(Fraction(0), 0, Fraction(1, 4)),
            Slot(Fraction(0), 1, Fraction(1, 4)),
            Slot(Fraction(1, 4), 0, Fraction(1, 4)),
            Slot(Fraction(1, 4), 1, Fraction(1, 4)),
        ]
        # Anchors chosen to avoid parallel perfect intervals
        # Beat 0: C5/E3 (M6), Beat 1/4: D5/F3 (M6) - parallel sixths are OK
        anchors = [
            Anchor(Fraction(0), 0, 72),   # C5
            Anchor(Fraction(0), 1, 52),   # E3 - M6 interval
            Anchor(Fraction(1, 4), 0, 74),  # D5
            Anchor(Fraction(1, 4), 1, 53),  # F3 - M6 interval (parallel sixths OK)
        ]
        solution = solve(anchors, slots, config)
        assert solution.pitches[(Fraction(0), 0)] == 72
        assert solution.pitches[(Fraction(0), 1)] == 52
        assert solution.pitches[(Fraction(1, 4), 0)] == 74
        assert solution.pitches[(Fraction(1, 4), 1)] == 53

    def test_solve_deterministic(self) -> None:
        """Same inputs produce identical outputs."""
        config = make_config()
        slots = [
            Slot(Fraction(0), 0, Fraction(1, 4)),
            Slot(Fraction(0), 1, Fraction(1, 4)),
            Slot(Fraction(1, 4), 0, Fraction(1, 4)),
            Slot(Fraction(1, 4), 1, Fraction(1, 4)),
        ]
        anchors = [Anchor(Fraction(0), 0, 72)]
        sol1 = solve(anchors, slots, config)
        sol2 = solve(anchors, slots, config)
        assert sol1.pitches == sol2.pitches

    def test_solve_respects_tessitura_span(self) -> None:
        """All pitches within tessitura span around median."""
        config = make_config(tessitura_span=12)
        slots = [
            Slot(Fraction(i, 4), v, Fraction(1, 4))
            for i in range(4)
            for v in range(2)
        ]
        anchors = [Anchor(Fraction(0), 0, 72)]
        solution = solve(anchors, slots, config)
        for (offset, voice), pitch in solution.pitches.items():
            median = DEFAULT_MEDIANS[voice]
            assert median - 12 <= pitch <= median + 12

    def test_solve_respects_pitch_class_set(self) -> None:
        """All pitches belong to pitch class set."""
        config = make_config()
        slots = [
            Slot(Fraction(i, 4), v, Fraction(1, 4))
            for i in range(4)
            for v in range(2)
        ]
        anchors = []
        solution = solve(anchors, slots, config)
        for pitch in solution.pitches.values():
            assert pitch % 12 in C_MAJOR

    def test_solve_empty_slots_returns_empty(self) -> None:
        """Solver returns empty solution for no slots."""
        config = make_config()
        solution = solve([], [], config)
        assert solution.pitches == {}
        assert solution.cost == 0.0

    def test_solve_returns_cost(self) -> None:
        """Solution includes cost."""
        config = make_config()
        slots = [
            Slot(Fraction(0), 0, Fraction(1, 4)),
            Slot(Fraction(0), 1, Fraction(1, 4)),
            Slot(Fraction(1, 4), 0, Fraction(1, 4)),
            Slot(Fraction(1, 4), 1, Fraction(1, 4)),
        ]
        solution = solve([], slots, config)
        assert isinstance(solution.cost, float)


class TestSolveConstraints:
    """Tests for solver constraint satisfaction."""

    def test_no_parallel_fifths(self) -> None:
        """Solver avoids parallel fifths."""
        config = make_config()
        # Create slots that might tempt parallel fifths
        slots = [
            Slot(Fraction(i, 4), v, Fraction(1, 4))
            for i in range(4)
            for v in range(2)
        ]
        solution = solve([], slots, config)

        # Check no parallel fifths
        pitches = solution.pitches
        offsets = sorted(set(k[0] for k in pitches.keys()))
        for i in range(len(offsets) - 1):
            o1, o2 = offsets[i], offsets[i + 1]
            s1, b1 = pitches.get((o1, 0)), pitches.get((o1, 1))
            s2, b2 = pitches.get((o2, 0)), pitches.get((o2, 1))
            if all(p is not None for p in [s1, b1, s2, b2]):
                int1 = abs(s1 - b1) % 12
                int2 = abs(s2 - b2) % 12
                # If both are fifths (7 semitones)
                if int1 == 7 and int2 == 7:
                    # Must not both move in same direction
                    s_motion = s2 - s1
                    b_motion = b2 - b1
                    if s_motion != 0 and b_motion != 0:
                        assert (s_motion > 0) != (b_motion > 0), "Parallel fifths detected"
