"""
subject_scorer.py — Score and rank enumerated subjects.

Intervals and durations are scored independently, top-k from each selected,
then the cross-product is jointly scored and ranked.

Scores are 0..1, higher is better. Interval scoring is NumPy-vectorised.
"""

import math
import time
from collections import Counter

import numpy as np

from subject_contours import CONTOUR_SCORE_WIDTH, interpolate_contour
from subject_generator import (
    DURATION_NAMES,
    DURATION_TICKS,
    HEAD_LEN,
    NUM_INTERVALS,
    NUM_NOTES,
    TICK_HI,
    TICK_LO,
    enumerate_durations,
    enumerate_intervals,
)

# ── Selection parameters ────────────────────────────────────────────
TOP_K_INTERVALS = 500
TOP_K_DURATIONS = 200
TOP_K_SUBJECTS = 200
MIN_IV_HAMMING = 3           # min interval diffs to count as distinct
MIN_DUR_HAMMING = 3          # min duration diffs to count as distinct

# ── Ideal targets ───────────────────────────────────────────────────
IDEAL_STEP_FRACTION = 0.67       # sweet spot for step proportion
IDEAL_RHYTHMIC_ENTROPY = 0.75    # normalised Shannon entropy


def _closeness_np(
    values: np.ndarray,
    target: float,
    width: float,
) -> np.ndarray:
    """Vectorised Gaussian closeness, 1.0 at target."""
    return np.exp(-((values - target) ** 2) / (2 * width * width))


def score_intervals(
    sequences: list,
    contour_waypoints: list = None,
) -> list:
    """Score all interval sequences vectorised. Returns list of (score, index)."""
    n = len(sequences)
    if n == 0:
        return []
    t0 = time.time()
    # (N, NUM_INTERVALS)
    iv = np.array(sequences, dtype=np.float32)
    # Cumulative pitches: prepend 0 → (N, NUM_NOTES)
    pitches = np.concatenate([np.zeros((n, 1), dtype=np.float32), iv.cumsum(axis=1)], axis=1)
    # 1. Step proportion (first interval exempt)
    abs_iv_tail = np.abs(iv[:, 1:])
    steps = (abs_iv_tail <= 1).sum(axis=1).astype(np.float32)
    step_frac = steps / (NUM_INTERVALS - 1)
    s_steps = _closeness_np(step_frac, IDEAL_STEP_FRACTION, 0.12)
    # 2. Interval variety: count distinct absolute intervals per row
    abs_iv_all = np.abs(iv).astype(np.int32)
    variety = np.zeros(n, dtype=np.float32)
    for v in range(6):
        variety += np.any(abs_iv_all == v, axis=1).astype(np.float32)
    s_variety = np.minimum(variety / 4.0, 1.0)
    # 3. Tail variety: fraction of distinct pairs in tail intervals
    tail_iv = iv[:, HEAD_LEN - 1:]
    ncols = tail_iv.shape[1]
    pair_diffs = 0.0
    pair_count = 0
    for c1 in range(ncols):
        for c2 in range(c1 + 1, ncols):
            pair_diffs += (tail_iv[:, c1] != tail_iv[:, c2]).astype(np.float32)
            pair_count += 1
    s_tail_var = np.minimum(pair_diffs / pair_count, 1.0) if pair_count > 0 else np.zeros(n)
    # 4. Opening tessitura: span of first 3 pitches
    open_p = pitches[:, :3]
    open_span = open_p.max(axis=1) - open_p.min(axis=1)
    s_opening = _closeness_np(open_span, 4.0, 1.5)
    # 5. Contour fit
    if contour_waypoints is not None:
        targets = interpolate_contour(contour_waypoints, NUM_NOTES)
        targets_np = np.array(targets, dtype=np.float32).reshape(1, -1)
        diff_sq = (pitches - targets_np) ** 2
        rms = np.sqrt(diff_sq.mean(axis=1))
        w = CONTOUR_SCORE_WIDTH
        s_contour = np.exp(-(rms ** 2) / (2 * w * w))
    else:
        s_contour = np.full(n, 0.5, dtype=np.float32)
    # Weighted combination
    scores = (
        0.15 * s_steps +
        0.10 * s_variety +
        0.20 * s_tail_var +
        0.20 * s_opening +
        0.35 * s_contour
    )
    elapsed = time.time() - t0
    print(f"  Vectorised {n:,} intervals in {elapsed:.2f}s")
    return [(float(scores[i]), i) for i in range(n)]


def score_durations(sequences: list) -> list:
    """Score each duration sequence. Returns list of (score, index)."""
    scored = []
    for idx, durs in enumerate(sequences):
        ticks = [DURATION_TICKS[d] for d in durs]
        total_ticks = sum(ticks)
        # 1. Rhythmic entropy
        counts = list(Counter(durs).values())
        ent = _shannon_entropy(counts, NUM_NOTES)
        s_entropy = _closeness(ent, IDEAL_RHYTHMIC_ENTROPY, 0.2)
        # 2. Head-tail contrast
        head_mean = sum(ticks[:HEAD_LEN]) / HEAD_LEN
        tail_mean = sum(ticks[HEAD_LEN:]) / (NUM_NOTES - HEAD_LEN)
        ratio = tail_mean / head_mean if head_mean > 0 else 1.0
        s_contrast = _closeness(ratio, 2.5, 0.6)
        # 3. Rhythmic coherence
        changes = sum(1 for i in range(1, NUM_NOTES) if durs[i] != durs[i - 1])
        change_frac = changes / (NUM_NOTES - 1)
        s_coherence = _closeness(change_frac, 0.4, 0.15)
        # 4. Distinct durations used
        distinct = len(set(durs))
        s_distinct = min(distinct / 3.0, 1.0)
        # 5. Total length: prefer middle of range
        mid_ticks = (TICK_LO + TICK_HI) / 2.0
        s_length = _closeness(total_ticks, mid_ticks, 5.0)
        # 6. Final lengthening
        s_final = 1.0 if ticks[-1] > ticks[-2] else (0.5 if ticks[-1] == ticks[-2] else 0.0)
        score = (
            0.10 * s_entropy +
            0.35 * s_contrast +
            0.20 * s_coherence +
            0.10 * s_distinct +
            0.10 * s_length +
            0.15 * s_final
        )
        scored.append((score, idx))
    return scored


def _shannon_entropy(counts: list, total: int) -> float:
    """Normalised Shannon entropy, 0..1."""
    if total == 0:
        return 0.0
    n_classes = len(counts)
    if n_classes <= 1:
        return 0.0
    max_ent = math.log(n_classes)
    if max_ent == 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log(p)
    return ent / max_ent


def _closeness(value: float, target: float, width: float) -> float:
    """Gaussian-like closeness score, 1.0 at target, decaying with distance."""
    return math.exp(-((value - target) ** 2) / (2 * width * width))


def score_joint(
    iv_seq: tuple,
    dur_seq: tuple,
) -> float:
    """Score a paired (interval, duration) subject."""
    ticks = [DURATION_TICKS[d] for d in dur_seq]
    iv_abs = [abs(iv) for iv in iv_seq]
    leap_dur_bonus = 0.0
    for i in range(len(iv_seq)):
        if iv_abs[i] >= 2:
            if ticks[i + 1] >= 4:
                leap_dur_bonus += 1.0
            elif ticks[i + 1] <= 2:
                leap_dur_bonus -= 0.5
    max_leaps = sum(1 for a in iv_abs if a >= 2)
    if max_leaps > 0:
        s_leap_dur = max(0.0, min(1.0, 0.5 + leap_dur_bonus / max_leaps))
    else:
        s_leap_dur = 0.5
    pre_leap_bonus = 0.0
    pre_leap_count = 0
    for i in range(len(iv_seq)):
        if iv_abs[i] >= 2:
            if ticks[i] <= 3:
                pre_leap_bonus += 1.0
            pre_leap_count += 1
    if pre_leap_count > 0:
        s_pre_leap = pre_leap_bonus / pre_leap_count
    else:
        s_pre_leap = 0.5
    return 0.6 * s_leap_dur + 0.4 * s_pre_leap


def _contour_class(ivs: tuple) -> str:
    """Classify the contour shape of an interval sequence."""
    pitches = [0]
    for iv in ivs:
        pitches.append(pitches[-1] + iv)
    mid = len(pitches) // 2
    mid_pitch = pitches[mid]
    peak_pos = pitches.index(max(pitches))
    trough_pos = pitches.index(min(pitches))
    if mid_pitch > 0:
        if trough_pos > mid:
            return 'arch'
        return 'rise_dip_fall'
    elif mid_pitch == 0:
        if peak_pos < mid:
            return 'plateau_fall'
        return 'late_peak'
    else:
        if peak_pos > mid:
            return 'valley_arch'
        return 'descent'


def _hamming_iv(a: tuple, b: tuple) -> int:
    """Hamming distance between two interval sequences."""
    return sum(1 for x, y in zip(a, b) if x != y)


def _hamming_dur(a: tuple, b: tuple) -> int:
    """Hamming distance between two duration sequences."""
    return sum(1 for x, y in zip(a, b) if x != y)


def _diverse_select(
    candidates: list,
    n: int,
    min_iv_dist: int,
    min_dur_dist: int,
) -> list:
    """Greedy diversity selection from scored candidates."""
    if not candidates:
        return []
    first = candidates[0]
    selected = [first]
    used_openings = {first[1][0]}
    used_contours = {_contour_class(first[1])}
    n_contour_types = 6
    for score, ivs, durs in candidates[1:]:
        if len(selected) >= n:
            break
        contour = _contour_class(ivs)
        opening = ivs[0]
        if len(used_contours) < n_contour_types:
            if contour in used_contours:
                continue
        elif len(used_openings) < 10:
            if opening in used_openings:
                continue
        too_close = False
        for _, s_ivs, s_durs in selected:
            if _hamming_iv(ivs, s_ivs) < min_iv_dist or _hamming_dur(durs, s_durs) < min_dur_dist:
                too_close = True
                break
        if not too_close:
            selected.append((score, ivs, durs))
            used_openings.add(opening)
            used_contours.add(contour)
    return selected


def run() -> list:
    """Full pipeline. Returns top-k subjects as (score, interval_tuple, duration_tuple)."""
    ivs = enumerate_intervals()
    durs = enumerate_durations()
    print(f"\nScoring {len(ivs):,} interval sequences...")
    t0 = time.time()
    iv_scores = score_intervals(ivs)
    print(f"  done in {time.time() - t0:.1f}s")
    print(f"Scoring {len(durs):,} duration sequences...")
    t0 = time.time()
    dur_scores = score_durations(durs)
    print(f"  done in {time.time() - t0:.1f}s")
    iv_scores.sort(key=lambda x: x[0], reverse=True)
    dur_scores.sort(key=lambda x: x[0], reverse=True)
    buckets = {}
    for score, idx in iv_scores:
        first_iv = ivs[idx][0]
        if first_iv not in buckets:
            buckets[first_iv] = []
        buckets[first_iv].append((score, idx))
    n_buckets = len(buckets)
    per_bucket = max(1, TOP_K_INTERVALS // n_buckets)
    top_ivs = []
    for first_iv in sorted(buckets.keys()):
        top_ivs.extend(buckets[first_iv][:per_bucket])
    print(f"\n{n_buckets} opening intervals, {per_bucket} per bucket, {len(top_ivs)} total")
    top_durs = dur_scores[:TOP_K_DURATIONS]
    print(f"Top interval score: {top_ivs[0][0]:.3f}, bottom: {top_ivs[-1][0]:.3f}")
    print(f"Top duration score: {top_durs[0][0]:.3f}, bottom: {top_durs[-1][0]:.3f}")
    n_pairs = len(top_ivs) * len(top_durs)
    print(f"\nJoint-scoring {n_pairs:,} pairs...")
    t0 = time.time()
    subjects = []
    for iv_score, iv_idx in top_ivs:
        iv_seq = ivs[iv_idx]
        for dur_score, dur_idx in top_durs:
            dur_seq = durs[dur_idx]
            j_score = score_joint(iv_seq, dur_seq)
            combined = 0.4 * iv_score + 0.3 * dur_score + 0.3 * j_score
            subjects.append((combined, iv_seq, dur_seq))
    print(f"  done in {time.time() - t0:.1f}s")
    subjects.sort(key=lambda x: x[0], reverse=True)
    subjects = subjects[:10000]
    print(f"\nDiversity selection from {len(subjects):,} candidates...")
    t0 = time.time()
    top = _diverse_select(subjects, TOP_K_SUBJECTS, MIN_IV_HAMMING, MIN_DUR_HAMMING)
    print(f"  selected {len(top):,} in {time.time() - t0:.1f}s")
    if top:
        print(f"  Best score:  {top[0][0]:.4f}")
        print(f"  Worst score: {top[-1][0]:.4f}")
    return top


def display_subject(rank: int, score: float, ivs: tuple, durs: tuple) -> None:
    """Pretty-print a ranked subject."""
    pitches = [0]
    for iv in ivs:
        pitches.append(pitches[-1] + iv)
    dur_names = [DURATION_NAMES[d] for d in durs]
    dur_ticks = [DURATION_TICKS[d] for d in durs]
    total = sum(dur_ticks)
    contour = _contour_class(ivs)
    print(f"#{rank + 1}  score={score:.4f}  contour={contour}")
    print(f"  Pitches:    {pitches}")
    print(f"  Intervals:  {list(ivs)}")
    print(f"  Rhythm:     {dur_names}")
    print(f"  Ticks:      {dur_ticks}  total={total} ({total / 2:.1f} semiquavers)")
    print()


if __name__ == '__main__':
    top = run()
    print(f"\n{'=' * 60}")
    print(f"TOP 20 SUBJECTS")
    print(f"{'=' * 60}\n")
    for i in range(min(20, len(top))):
        score, ivs, durs = top[i]
        display_subject(i, score, ivs, durs)
