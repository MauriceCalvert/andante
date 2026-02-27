"""Aesthetic scoring for subject candidates.

Each criterion returns 0–1. The weighted sum is the aesthetic score.
Feature vector extraction for diversity selection lives here too.
"""
import math

from motifs.subject_gen.constants import (
    DEGREES_PER_OCTAVE,
    DURATION_TICKS,
    HEAD_IV_FEATURE_SCALE,
    HEAD_IV_FEATURE_WINDOW,
    HEAD_SIZE,
    W_DENSITY_TRAJECTORY,
    W_DIRECTION_COMMITMENT,
    W_DURATION_VARIETY,
    W_FAST_NOTE_DENSITY,
    W_HARMONIC_VARIETY,
    W_HEAD_CHARACTER,
    W_RANGE,
    W_REPETITION_PENALTY,
    W_SCALIC_MONOTONY,
    W_TAIL_MOMENTUM,
)

# Semiquaver tick value for fast-note density scoring.
_SEMIQUAVER_TICKS: int = 1


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


def _duration_variety(dur_indices: tuple[int, ...]) -> float:
    """Score 0–1 for count of distinct duration values used."""
    distinct: int = len(set(DURATION_TICKS[d] for d in dur_indices))
    return min((distinct - 1) / 3.0, 1.0)


def _fast_note_density(dur_indices: tuple[int, ...]) -> float:
    """Score 0–1 for proportion of notes at semiquaver duration."""
    n: int = len(dur_indices)
    if n == 0:
        return 0.0
    fast_count: int = sum(1 for d in dur_indices if DURATION_TICKS[d] == _SEMIQUAVER_TICKS)
    return min(fast_count / (n * 0.4), 1.0)


def _harmonic_variety(degrees: tuple[int, ...]) -> float:
    """Score 0-1 for how many distinct chords the degree sequence touches.

    Checks I ({0,2,4}), IV ({3,5,0}), V ({4,6,1}), ii ({1,3,5}) in major.
    Score = (touched - 1) / 3.0, clamped to [0.0, 1.0].
    """
    _CHORD_SETS: tuple[frozenset[int], ...] = (
        frozenset({0, 2, 4}),  # I
        frozenset({3, 5, 0}),  # IV
        frozenset({4, 6, 1}),  # V
        frozenset({1, 3, 5}),  # ii
    )
    degree_classes: frozenset[int] = frozenset(d % 7 for d in degrees)
    touched: int = sum(1 for chord in _CHORD_SETS if chord & degree_classes)
    return min(max((touched - 1) / 3.0, 0.0), 1.0)


def _head_character(ivs: tuple[int, ...]) -> float:
    """Score 0–1 for a characteristic interval in the Kopfmotiv."""
    head_ivs: tuple[int, ...] = ivs[:HEAD_SIZE]
    if not head_ivs:
        return 0.0
    max_leap: int = max(abs(iv) for iv in head_ivs)
    if max_leap <= 1:
        return 0.0
    if max_leap == 2:
        return 0.5
    if max_leap == 3:
        return 0.8
    return 1.0


def _intervallic_range(degrees: tuple[int, ...]) -> float:
    """Score 0–1 for pitch span. 5th (range 4) = 0.5, octave (7) = 1.0, >octave clipped."""
    span: int = max(degrees) - min(degrees)
    if span <= 2:
        return 0.0
    return min(span / 7.0, 1.0)


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



def _tail_momentum(dur_indices: tuple[int, ...]) -> float:
    """Score 0-1 penalising consecutive long notes at the subject's end.

    One long final note is fine (standard practice). Two or more consecutive
    crotchets-or-longer at the tail kills rhythmic drive.
    """
    _LONG_THRESHOLD: int = 6  # dotted crotchet in x2 ticks
    n: int = len(dur_indices)
    if n < 3:
        return 1.0
    tail_long_run: int = 0
    for i in range(n - 1, -1, -1):
        if DURATION_TICKS[dur_indices[i]] >= _LONG_THRESHOLD:
            tail_long_run += 1
        else:
            break
    if tail_long_run <= 1:
        return 1.0
    if tail_long_run == 2:
        return 0.3
    return 0.0


def _scalic_monotony(ivs: tuple[int, ...]) -> float:
    """Score 0–1 penalising overwhelmingly stepwise motion."""
    if not ivs:
        return 1.0
    step_count: int = sum(1 for iv in ivs if abs(iv) <= 1)
    step_frac: float = step_count / len(ivs)
    if step_frac <= 0.55:
        return 1.0
    if step_frac >= 0.80:
        return 0.0
    return 1.0 - (step_frac - 0.55) / 0.25


def _density_trajectory(
    dur_indices: tuple[int, ...],
    head_n: int,
) -> float:
    """Score 0-1 rewarding measurable density shift between head and tail.

    Computes mean tick duration for head vs tail notes and returns
    the normalised absolute difference.
    """
    assert head_n > 0, f"head_n must be positive, got {head_n}"
    assert head_n < len(dur_indices), (
        f"head_n={head_n} must be < total notes={len(dur_indices)}"
    )
    head_ticks: list[int] = [DURATION_TICKS[d] for d in dur_indices[:head_n]]
    tail_ticks: list[int] = [DURATION_TICKS[d] for d in dur_indices[head_n:]]
    head_mean: float = sum(head_ticks) / len(head_ticks)
    tail_mean: float = sum(tail_ticks) / len(tail_ticks)
    denom: float = max(head_mean, tail_mean)
    if denom == 0.0:
        return 0.0
    return min(abs(head_mean - tail_mean) / denom, 1.0)


def score_subject(
    degrees: tuple[int, ...],
    ivs: tuple[int, ...],
    dur_indices: tuple[int, ...],
    head_n: int = 0,
) -> float:
    """Weighted aesthetic score for a subject candidate. Returns 0–12.5."""
    density_traj: float = (
        _density_trajectory(dur_indices=dur_indices, head_n=head_n)
        if head_n > 0
        else 0.0
    )
    return (
        W_RANGE * _intervallic_range(degrees=degrees)
        + W_DIRECTION_COMMITMENT * _direction_commitment(degrees=degrees)
        + W_REPETITION_PENALTY * _repetition_penalty(degrees=degrees)
        + W_HARMONIC_VARIETY * _harmonic_variety(degrees=degrees)
        + W_FAST_NOTE_DENSITY * _fast_note_density(dur_indices=dur_indices)
        + W_DURATION_VARIETY * _duration_variety(dur_indices=dur_indices)
        + W_SCALIC_MONOTONY * _scalic_monotony(ivs=ivs)
        + W_HEAD_CHARACTER * _head_character(ivs=ivs)
        + W_TAIL_MOMENTUM * _tail_momentum(dur_indices=dur_indices)
        + W_DENSITY_TRAJECTORY * density_traj
    )


def subject_features(
    degrees: tuple[int, ...],
    ivs: tuple[int, ...],
    dur_indices: tuple[int, ...],
    head_n: int = 0,
) -> tuple[float, ...]:
    """Feature vector for diversity distance computation."""
    n: int = len(degrees)
    span: int = max(degrees) - min(degrees)
    # range normalised to octave
    f_range: float = min(span / 7.0, 1.0)
    # climax position: index of highest pitch / note_count
    hi_idx: int = 0
    for i in range(n):
        if degrees[i] > degrees[hi_idx]:
            hi_idx = i
    f_climax_pos: float = hi_idx / (n - 1) if n > 1 else 0.5
    # direction: net displacement / range
    net: int = degrees[-1] - degrees[0]
    f_direction: float = (net / span) if span > 0 else 0.0
    # harmonic variety score
    f_harmonic_variety: float = _harmonic_variety(degrees=degrees)
    # fast note density
    f_fast_density: float = _fast_note_density(dur_indices=dur_indices)
    # duration variety
    f_dur_variety: float = _duration_variety(dur_indices=dur_indices)
    # scalic monotony
    f_scalic: float = _scalic_monotony(ivs=ivs)
    # head intervals (normalised) — sequential similarity of opening gesture
    head_ivs: tuple[int, ...] = ivs[:HEAD_IV_FEATURE_WINDOW] if len(ivs) >= HEAD_IV_FEATURE_WINDOW else ivs
    f_head_ivs: tuple[float, ...] = tuple(iv * HEAD_IV_FEATURE_SCALE / DEGREES_PER_OCTAVE for iv in head_ivs)
    # tail intervals (normalised) — sequential similarity of closing gesture
    tail_ivs: tuple[int, ...] = ivs[-HEAD_IV_FEATURE_WINDOW:] if len(ivs) >= HEAD_IV_FEATURE_WINDOW else ivs
    f_tail_ivs: tuple[float, ...] = tuple(iv * HEAD_IV_FEATURE_SCALE / DEGREES_PER_OCTAVE for iv in tail_ivs)
    # density trajectory (SUB-2)
    f_density_traj: float = (
        _density_trajectory(dur_indices=dur_indices, head_n=head_n)
        if head_n > 0
        else 0.0
    )
    return (f_range, f_climax_pos, f_direction, f_harmonic_variety, f_fast_density, f_dur_variety, f_scalic, f_density_traj) + f_head_ivs + f_tail_ivs
