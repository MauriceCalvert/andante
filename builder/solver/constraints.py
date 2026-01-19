"""Constraint checking for voice coordination.

Checks for:
- Dissonant intervals (2nd, 7th) between simultaneous notes
- Parallel fifths and octaves between consecutive slices

Uses diatonic (degree-based) intervals since builder operates in degree space.
"""
from typing import NamedTuple

from builder.solver.subdivision import VerticalSlice
from shared.parallels import (
    is_parallel_fifth_diatonic,
    is_parallel_octave_diatonic,
)


# Dissonant intervals in diatonic space (mod 7)
# 1 = 2nd, 6 = 7th
DISSONANT_DIATONIC_INTERVALS: frozenset[int] = frozenset({1, 6})


class DissonanceViolation(NamedTuple):
    """A dissonance violation between two voices at a slice."""

    voice_i: int
    voice_j: int
    interval: int


class ParallelViolation(NamedTuple):
    """A parallel motion violation between two slices."""

    voice_i: int
    voice_j: int
    violation_type: str  # "fifth" or "octave"


def is_dissonant_diatonic(degree1: int, degree2: int) -> bool:
    """Check if two diatonic degrees form a dissonant interval.

    Args:
        degree1: First diatonic pitch (any octave).
        degree2: Second diatonic pitch (any octave).

    Returns:
        True if interval is a 2nd or 7th (dissonant).
    """
    interval: int = abs(degree1 - degree2) % 7
    return interval in DISSONANT_DIATONIC_INTERVALS


def check_slice_dissonances(slice: VerticalSlice) -> list[DissonanceViolation]:
    """Check for dissonant intervals between any voice pair in a slice.

    Returns list of violations (empty if none).
    """
    violations: list[DissonanceViolation] = []
    n: int = slice.voice_count
    for i in range(n):
        for j in range(i + 1, n):
            p1: int | None = slice.pitches[i]
            p2: int | None = slice.pitches[j]
            if p1 is not None and p2 is not None:
                interval: int = abs(p1 - p2) % 7
                if interval in DISSONANT_DIATONIC_INTERVALS:
                    violations.append(DissonanceViolation(i, j, interval))
    return violations


def check_parallel_motion(
    prev_slice: VerticalSlice,
    curr_slice: VerticalSlice,
) -> list[ParallelViolation]:
    """Check for parallel fifths and octaves between consecutive slices.

    Checks all voice pairs for parallel motion violations.

    Returns list of violations (empty if none).
    """
    violations: list[ParallelViolation] = []
    n: int = prev_slice.voice_count
    assert n == curr_slice.voice_count, "Slice voice counts must match"

    for i in range(n):
        for j in range(i + 1, n):
            prev_upper: int | None = prev_slice.pitches[i]
            prev_lower: int | None = prev_slice.pitches[j]
            curr_upper: int | None = curr_slice.pitches[i]
            curr_lower: int | None = curr_slice.pitches[j]

            # Skip if any voice is resting
            if (
                prev_upper is None
                or prev_lower is None
                or curr_upper is None
                or curr_lower is None
            ):
                continue

            # Check parallel fifths
            if is_parallel_fifth_diatonic(prev_upper, prev_lower, curr_upper, curr_lower):
                violations.append(ParallelViolation(i, j, "fifth"))

            # Check parallel octaves
            if is_parallel_octave_diatonic(prev_upper, prev_lower, curr_upper, curr_lower):
                violations.append(ParallelViolation(i, j, "octave"))

    return violations


# Re-export from shared for convenience
__all__ = [
    "DISSONANT_DIATONIC_INTERVALS",
    "DissonanceViolation",
    "ParallelViolation",
    "is_dissonant_diatonic",
    "check_slice_dissonances",
    "is_parallel_fifth_diatonic",
    "is_parallel_octave_diatonic",
    "check_parallel_motion",
]
