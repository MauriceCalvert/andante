"""Stage 1: Exhaustive pitch generation and scoring."""
import math

from motifs.head_generator import degrees_to_midi
from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.constants import (
    ALLOWED_FINALS,
    IDEAL_CLIMAX_HI,
    IDEAL_CLIMAX_LO,
    LEAP_RECOVERY_WINDOW,
    MAX_LARGE_LEAPS,
    MAX_PITCH_FREQ,
    MAX_SAME_SIGN_RUN,
    MAX_STEPWISE_RUN,
    MIN_DISTINCT_INTERVALS,
    MIN_SIGNATURE_LEAP,
    MIN_STEP_FRACTION,
    PITCH_HI,
    PITCH_LO,
    RANGE_HI,
    RANGE_LO,
)
from motifs.subject_gen.cpsat_generator import generate_cpsat_degrees
from motifs.subject_gen.contour import _derive_shape_name, _find_climax
from motifs.subject_gen.models import _ScoredPitch
from motifs.subject_gen.validator import is_melodically_valid


def _direction_changes(ivs: tuple[int, ...]) -> int:
    """Count sign changes in interval sequence (ignoring zeros)."""
    changes = 0
    last_sign = 0
    for iv in ivs:
        if iv > 0:
            sign = 1
        elif iv < 0:
            sign = -1
        else:
            continue
        if last_sign != 0 and sign != last_sign:
            changes += 1
        last_sign = sign
    return changes


def _tension_arc_score(ivs: tuple[int, ...], climax_pos: int) -> float:
    """Score how well interval magnitudes intensify toward climax and relax after."""
    n = len(ivs)
    if climax_pos < 2 or climax_pos >= n:
        return 0.0
    pre = ivs[:climax_pos]
    post = ivs[climax_pos:]
    def _trend(segment: tuple[int, ...] | list) -> float:
        m = len(segment)
        if m < 2:
            return 0.0
        abs_vals = [abs(v) for v in segment]
        mean_pos = (m - 1) / 2.0
        mean_abs = sum(abs_vals) / m
        num = sum((i - mean_pos) * (a - mean_abs) for i, a in enumerate(abs_vals))
        den_pos = sum((i - mean_pos) ** 2 for i in range(m))
        den_abs = sum((a - mean_abs) ** 2 for a in abs_vals)
        denom = math.sqrt(den_pos * den_abs) if den_pos > 0 and den_abs > 0 else 1.0
        return num / denom if denom > 0 else 0.0
    pre_trend = _trend(pre)
    post_trend = _trend(post)
    score_a = (max(0.0, pre_trend) + max(0.0, -post_trend)) / 2.0
    score_b = (max(0.0, -pre_trend) + max(0.0, post_trend)) / 2.0
    return max(score_a, score_b)


def _longest_stepwise_run(ivs: tuple[int, ...]) -> int:
    """Longest consecutive same-direction steps (|iv| <= 1)."""
    best = 0
    run = 0
    last_sign = 0
    for iv in ivs:
        if abs(iv) <= 1:
            sign = 1 if iv > 0 else -1
            if sign == last_sign:
                run += 1
            else:
                run = 1
                last_sign = sign
        else:
            run = 0
            last_sign = 0
        best = max(best, run)
    return best


def _leap_recovery_rate(ivs: tuple[int, ...]) -> float:
    """Fraction of leaps followed by a contrary-motion step within window."""
    leaps = 0
    recovered = 0
    for i, iv in enumerate(ivs):
        if abs(iv) < MIN_SIGNATURE_LEAP:
            continue
        leaps += 1
        leap_sign = 1 if iv > 0 else -1
        for j in range(i + 1, min(i + 1 + LEAP_RECOVERY_WINDOW, len(ivs))):
            if abs(ivs[j]) <= 1 and (ivs[j] > 0) != (leap_sign > 0):
                recovered += 1
                break
    return recovered / leaps if leaps > 0 else 0.0


def score_pitch_sequence(ivs: tuple[int, ...]) -> float:
    """Score a pitch sequence for memorability and dramatic shape."""
    num_intervals = len(ivs)
    num_notes = num_intervals + 1
    pitches = [0]
    for iv in ivs:
        pitches.append(pitches[-1] + iv)
    # ── Signature leap (25%) ────────────────────────────────────
    leap_sizes = [(i, abs(iv)) for i, iv in enumerate(ivs) if abs(iv) >= MIN_SIGNATURE_LEAP]
    if not leap_sizes:
        s_leap = 0.0
    else:
        first_pos = leap_sizes[0][0] / max(num_intervals - 1, 1)
        placement = 1.0 if first_pos < 0.4 else 0.5
        s_leap = 0.7 + 0.3 * placement
    # ── Leap recovery (20%) ─────────────────────────────────────
    s_recovery = _leap_recovery_rate(ivs)
    # ── Run penalty (20%) ───────────────────────────────────────
    longest_run = _longest_stepwise_run(ivs)
    if longest_run <= MAX_STEPWISE_RUN:
        s_run = 1.0
    else:
        excess = longest_run - MAX_STEPWISE_RUN
        s_run = max(0.0, 1.0 - 0.3 * excess)
    # ── Interval profile (15%) ──────────────────────────────────
    distinct = len(set(abs(iv) for iv in ivs))
    s_variety = min(distinct / MIN_DISTINCT_INTERVALS, 1.0)
    # ── Climax (20%) ────────────────────────────────────────────
    ci, cp, cdir = _find_climax(pitches)
    if ci < 0:
        s_climax = 0.0
    else:
        frac = ci / (num_notes - 1)
        if frac < IDEAL_CLIMAX_LO or frac > IDEAL_CLIMAX_HI:
            s_climax = 1.0
        else:
            dist = abs(frac - 0.45)
            s_climax = min(dist / 0.15, 1.0)
    # ── Direction changes (bonus, 0..0.05) ──────────────────────
    changes = _direction_changes(ivs)
    if changes == 1:
        s_direction_bonus = 0.05
    elif changes == 2:
        s_direction_bonus = 0.03
    else:
        s_direction_bonus = 0.0
    return (
        0.25 * s_leap
        + 0.20 * s_recovery
        + 0.20 * s_run
        + 0.15 * s_variety
        + 0.20 * s_climax
        + s_direction_bonus
    )


def _degrees_to_ivs(degrees: tuple[int, ...]) -> tuple[int, ...]:
    """Convert degree sequence to interval sequence."""
    return tuple(degrees[i + 1] - degrees[i] for i in range(len(degrees) - 1))


def _cached_validated_pitch(
    num_notes: int,
    tonic_midi: int,
    mode: str,
) -> list[_ScoredPitch]:
    """All scored+validated+classified pitch sequences, cached to disk."""
    stretto_k = num_notes // 2
    key = f"cpsat_pitch_{num_notes}n_{mode}_k{stretto_k}.pkl"
    cached = _load_cache(key)
    if cached is not None:
        return cached
    degree_sequences = generate_cpsat_degrees(
        num_notes=num_notes,
        mode=mode,
        stretto_k=stretto_k,
    )
    result: list[_ScoredPitch] = []
    for degs in degree_sequences:
        midi = degrees_to_midi(degrees=degs, tonic_midi=tonic_midi, mode=mode)
        if not is_melodically_valid(midi):
            continue
        ivs = _degrees_to_ivs(degs)
        sc = score_pitch_sequence(ivs)
        shape = _derive_shape_name(list(degs))
        result.append(_ScoredPitch(score=sc, ivs=ivs, degrees=degs, shape=shape))
    result.sort(key=lambda x: x.score, reverse=True)
    _save_cache(key, result)
    return result
