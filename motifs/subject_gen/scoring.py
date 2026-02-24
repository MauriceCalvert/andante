"""Aesthetic scoring for subject candidates.

Each criterion returns 0–1. The weighted sum is the aesthetic score.
Feature vector extraction for diversity selection lives here too.
"""
import math

from motifs.subject_gen.constants import (
    DURATION_TICKS,
    W_DIRECTION_COMMITMENT,
    W_RANGE,
    W_REPETITION_PENALTY,
    W_RHYTHMIC_CONTRAST,
    W_SIGNATURE_INTERVAL,
)


def _intervallic_range(degrees: tuple[int, ...]) -> float:
    """Score 0–1 for pitch span. 5th (range 4) = 0.5, octave (7) = 1.0, >octave clipped."""
    span: int = max(degrees) - min(degrees)
    if span <= 2:
        return 0.0
    return min(span / 7.0, 1.0)


def _signature_interval(ivs: tuple[int, ...]) -> float:
    """Score 0–1 for largest single interval. 2nd=0, 3rd=0.4, 4th=0.6, 5th=0.8, >=6th=1."""
    max_leap: int = max(abs(iv) for iv in ivs)
    if max_leap <= 1:
        return 0.0
    if max_leap == 2:
        return 0.4
    if max_leap == 3:
        return 0.6
    if max_leap == 4:
        return 0.8
    return 1.0


def _rhythmic_contrast(dur_indices: tuple[int, ...]) -> float:
    """Score 0–1 for ratio of longest to shortest duration tick."""
    ticks: list[int] = [DURATION_TICKS[d] for d in dur_indices]
    shortest: int = min(ticks)
    longest: int = max(ticks)
    if shortest == longest:
        return 0.0
    ratio: float = longest / shortest
    # ratio 2 (quaver vs semiquaver) = 0.5; ratio 4 (crotchet vs semiquaver) = 1.0
    return min((ratio - 1.0) / 3.0, 1.0)


def _direction_commitment(degrees: tuple[int, ...]) -> float:
    """Score 0–1 for net displacement in first half relative to range.

    Subjects that oscillate around start score low. Decisive motion scores high.
    """
    n: int = len(degrees)
    half: int = max(2, n // 2)
    net: int = abs(degrees[half] - degrees[0])
    span: int = max(degrees) - min(degrees)
    if span == 0:
        return 0.0
    return min(net / (span * 0.6), 1.0)


def _repetition_penalty(degrees: tuple[int, ...]) -> float:
    """Score 0–1, where 1 = no repetition, 0 = heavy repetition.

    Counts consecutive degree-pairs that repeat OR oscillate.
    (0,1),(0,1) is a repeat; (0,1),(1,0) is an oscillation. Both penalised.
    """
    n: int = len(degrees)
    if n < 4:
        return 1.0
    pairs: list[tuple[int, int]] = [(degrees[i], degrees[i + 1]) for i in range(n - 1)]
    repeat_count: int = 0
    for i in range(1, len(pairs)):
        if pairs[i] == pairs[i - 1]:
            repeat_count += 1
        elif pairs[i] == (pairs[i - 1][1], pairs[i - 1][0]):
            repeat_count += 1
    max_possible: int = len(pairs) - 1
    if max_possible == 0:
        return 1.0
    return 1.0 - (repeat_count / max_possible)


def score_subject(
    degrees: tuple[int, ...],
    ivs: tuple[int, ...],
    dur_indices: tuple[int, ...],
) -> float:
    """Weighted aesthetic score for a subject candidate. Returns 0–5."""
    return (
        W_RANGE * _intervallic_range(degrees=degrees)
        + W_SIGNATURE_INTERVAL * _signature_interval(ivs=ivs)
        + W_RHYTHMIC_CONTRAST * _rhythmic_contrast(dur_indices=dur_indices)
        + W_DIRECTION_COMMITMENT * _direction_commitment(degrees=degrees)
        + W_REPETITION_PENALTY * _repetition_penalty(degrees=degrees)
    )


def subject_features(
    degrees: tuple[int, ...],
    ivs: tuple[int, ...],
    dur_indices: tuple[int, ...],
) -> tuple[float, ...]:
    """6D feature vector for diversity distance computation."""
    n: int = len(degrees)
    span: int = max(degrees) - min(degrees)
    # range normalised to octave
    f_range: float = min(span / 7.0, 1.0)
    # leap fraction: proportion of intervals >= 3rd
    leap_count: int = sum(1 for iv in ivs if abs(iv) >= 2)
    f_leap_fraction: float = leap_count / len(ivs) if ivs else 0.0
    # max interval normalised
    max_iv: int = max(abs(iv) for iv in ivs) if ivs else 0
    f_max_interval: float = min(max_iv / 7.0, 1.0)
    # rhythmic contrast
    ticks: list[int] = [DURATION_TICKS[d] for d in dur_indices]
    ratio: float = max(ticks) / min(ticks) if min(ticks) > 0 else 1.0
    f_rhythmic_contrast: float = min(math.log2(ratio) / 2.0, 1.0)
    # climax position: index of highest pitch / note_count
    hi_idx: int = 0
    for i in range(n):
        if degrees[i] > degrees[hi_idx]:
            hi_idx = i
    f_climax_pos: float = hi_idx / (n - 1) if n > 1 else 0.5
    # direction: net displacement / range
    net: int = degrees[-1] - degrees[0]
    f_direction: float = (net / span) if span > 0 else 0.0
    return (f_range, f_leap_fraction, f_max_interval, f_rhythmic_contrast, f_climax_pos, f_direction)
