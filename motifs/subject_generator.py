"""Subject generator — shape-scored exhaustive generation and selection.

Generates pitch sequences by exhaustive walk (no contour band), scores
them for dramatic shape, assigns the best-scoring duration sequence of
matching length, then evaluates stretto potential at every possible offset.

Duration sequences are assembled from per-bar fills so that no note
crosses a bar boundary.  Note counts vary with the fills chosen.
"""
import math
import os
import pickle
import time
from collections import Counter
from dataclasses import dataclass
from itertools import product as iter_product
from pathlib import Path
from typing import Tuple

from motifs.head_generator import degrees_to_midi
from motifs.stretto_constraints import (
    OffsetResult,
    evaluate_all_offsets,
    score_stretto,
)


# ── Cache ────────────────────────────────────────────────────────────
_CACHE_DIR: Path = Path(__file__).resolve().parent.parent / ".cache" / "subject"


def _cache_path(name: str) -> Path:
    """Return cache file path, creating directory if needed."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / name


def _load_cache(name: str) -> object | None:
    """Load pickled object from cache, or None if missing/corrupt."""
    p = _cache_path(name)
    if not p.exists():
        return None
    try:
        with open(p, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _save_cache(name: str, obj: object) -> None:
    """Save object to cache."""
    p = _cache_path(name)
    with open(p, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)


# ── Duration vocabulary ─────────────────────────────────────────────
DURATION_TICKS: tuple[int, ...] = (1, 2, 4, 8)
DURATION_NAMES: tuple[str, ...] = ('semiquaver', 'quaver', 'crotchet', 'minim')
NUM_DURATIONS: int = len(DURATION_TICKS)
SEMIQUAVER_DI: int = 0

# ── Tick / bar geometry ─────────────────────────────────────────────
X2_TICKS_PER_WHOLE: int = 16


def _bar_x2_ticks(metre: tuple[int, int]) -> int:
    """X2-ticks per bar for the given metre."""
    return X2_TICKS_PER_WHOLE * metre[0] // metre[1]


# ── Bar-fill constraints ────────────────────────────────────────────
MIN_NOTES_PER_BAR: int = 2
MAX_NOTES_PER_BAR: int = 8
MAX_SAME_DUR_RUN: int = 4
MIN_LAST_DUR_TICKS: int = 4
MAX_SUBJECT_NOTES: int = 10
MIN_SEMIQUAVER_GROUP: int = 2

# ── Pitch constraints ───────────────────────────────────────────────
PITCH_LO: int = -7
PITCH_HI: int = 7
MAX_LARGE_LEAPS: int = 4
MIN_STEP_FRACTION: float = 0.5
RANGE_LO: int = 4
RANGE_HI: int = 11
MAX_SAME_SIGN_RUN: int = 5
ALLOWED_FINALS: frozenset[int] = frozenset({0, 2, 4})
MAX_PITCH_FREQ: int = 3

# ── Shape scoring parameters ────────────────────────────────────────
IDEAL_CLIMAX_LO: float = 0.3
IDEAL_CLIMAX_HI: float = 0.6
IDEAL_STEP_FRACTION: float = 0.67
IDEAL_RHYTHMIC_ENTROPY: float = 0.75

# ── Selection parameters ────────────────────────────────────────────
TOP_K_PER_SHAPE: int = 150  # per-contour quota within the shortlist
TOP_K_PITCH: int = 2000  # max pitch sequences per note-count for pairing


# ═══════════════════════════════════════════════════════════════════
#  GeneratedSubject
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GeneratedSubject:
    """A fully scored subject ready for answer/CS generation."""
    scale_indices: Tuple[int, ...]
    durations: Tuple[float, ...]
    midi_pitches: Tuple[int, ...]
    bars: int
    score: float
    seed: int
    mode: str
    head_name: str
    leap_size: int
    leap_direction: str
    tail_direction: str
    stretto_offsets: Tuple[OffsetResult, ...] = ()
    affect: str | None = None
    figurae_score: float = 0.0
    satisfied_figurae: Tuple[str, ...] = ()


# ═══════════════════════════════════════════════════════════════════
#  Stage 1: Exhaustive pitch generation (no contour band)
# ═══════════════════════════════════════════════════════════════════

def generate_pitch_sequences(num_notes: int) -> list[tuple[int, ...]]:
    """Exhaustive interval enumeration with hard constraints only."""
    num_intervals = num_notes - 1
    min_steps = math.ceil(MIN_STEP_FRACTION * num_intervals)
    results: list[tuple[int, ...]] = []
    buf: list[int] = [0] * num_intervals
    pitch_counts: list[int] = [0] * (PITCH_HI - PITCH_LO + 1)
    pitch_counts[0 - PITCH_LO] = 1
    def _recurse(
        pos: int,
        pitch: int,
        pitch_lo: int,
        pitch_hi: int,
        large_leaps: int,
        step_count: int,
        last_iv: int,
        same_sign_run: int,
    ) -> None:
        if pos == num_intervals:
            if pitch not in ALLOWED_FINALS:
                return
            if buf[num_intervals - 1] == 0:
                return
            span = pitch_hi - pitch_lo
            if span < RANGE_LO or span > RANGE_HI:
                return
            if step_count < min_steps:
                return
            results.append(tuple(buf))
            return
        remaining = num_intervals - pos
        for iv in range(-5, 6):
            if iv == 0:
                continue  # no repeated pitches
            abs_iv = abs(iv)
            new_pitch = pitch + iv
            if new_pitch < PITCH_LO or new_pitch > PITCH_HI:
                continue
            new_large = large_leaps + (1 if abs_iv >= 3 and pos > 0 else 0)
            if new_large > MAX_LARGE_LEAPS:
                continue
            new_lo = min(pitch_lo, new_pitch)
            new_hi = max(pitch_hi, new_pitch)
            if new_hi - new_lo > RANGE_HI:
                continue
            pi = new_pitch - PITCH_LO
            if pitch_counts[pi] >= MAX_PITCH_FREQ:
                continue
            new_step = step_count + (1 if abs_iv <= 1 and pos > 0 else 0)
            if pos > 0 and new_step + (remaining - 1) < min_steps:
                continue
            if iv > 0:
                new_run = (same_sign_run + 1) if same_sign_run > 0 else 1
            elif iv < 0:
                new_run = (same_sign_run - 1) if same_sign_run < 0 else -1
            else:
                new_run = 0
            if abs(new_run) > MAX_SAME_SIGN_RUN:
                continue
            buf[pos] = iv
            pitch_counts[pi] += 1
            _recurse(
                pos + 1, new_pitch, new_lo, new_hi,
                new_large, new_step, iv, new_run,
            )
            pitch_counts[pi] -= 1
    _recurse(0, 0, 0, 0, 0, 0, 0, 0)
    return results


TOP_PER_BUCKET: int = 200  # top sequences per opening-interval bucket


def _cached_scored_pitch(num_notes: int) -> list[tuple[float, tuple[int, ...]]]:
    """Stratified scored pitch sequences, cached to disk.

    Buckets by opening interval to ensure diversity: ascending 3rds,
    descending 4ths, etc. all get representation in the pool.
    """
    key = f"pitch_scored_{num_notes}n.pkl"
    cached = _load_cache(key)
    if cached is not None:
        return cached
    sequences = generate_pitch_sequences(num_notes)
    scored = [(score_pitch_sequence(s), s) for s in sequences]
    # Stratify by opening interval
    buckets: dict[int, list[tuple[float, tuple[int, ...]]]] = {}
    for sc, ivs in scored:
        buckets.setdefault(ivs[0], []).append((sc, ivs))
    result: list[tuple[float, tuple[int, ...]]] = []
    for opening_iv in sorted(buckets.keys()):
        bucket = buckets[opening_iv]
        bucket.sort(key=lambda x: x[0], reverse=True)
        result.extend(bucket[:TOP_PER_BUCKET])
    result.sort(key=lambda x: x[0], reverse=True)
    _save_cache(key, result)
    return result


def _cached_scored_durations(
    n_bars: int,
    bar_ticks: int,
) -> dict[int, list[tuple[float, tuple[int, ...]]]]:
    """All scored durations per note count, sorted descending, cached to disk."""
    key = f"dur_scored_{n_bars}b_{bar_ticks}t.pkl"
    cached = _load_cache(key)
    if cached is not None:
        return cached
    all_durs = enumerate_durations(n_bars=n_bars, bar_ticks=bar_ticks)
    by_count: dict[int, list[tuple[int, ...]]] = {}
    for d in all_durs:
        by_count.setdefault(len(d), []).append(d)
    result: dict[int, list[tuple[float, tuple[int, ...]]]] = {}
    for nc, seqs in by_count.items():
        scored = [(score_duration_sequence(d), d) for d in seqs]
        scored.sort(key=lambda x: x[0], reverse=True)
        result[nc] = scored
    _save_cache(key, result)
    return result


# ═══════════════════════════════════════════════════════════════════
#  Stage 1 scoring: shape quality
# ═══════════════════════════════════════════════════════════════════

def _find_climax(pitches: list[int]) -> tuple[int, int, str]:
    """Find the climax: extreme pitch that is unique and followed by direction change.

    Returns (climax_index, climax_pitch, direction) where direction is
    'high' or 'low'.  Returns (-1, 0, '') if no valid climax found.
    """
    n = len(pitches)
    hi_val = max(pitches)
    lo_val = min(pitches)
    hi_span = hi_val - pitches[0]
    lo_span = pitches[0] - lo_val
    # Choose whichever extreme is more dramatic
    if hi_span >= lo_span:
        candidates = [i for i in range(n) if pitches[i] == hi_val]
        direction = 'high'
    else:
        candidates = [i for i in range(n) if pitches[i] == lo_val]
        direction = 'low'
    # Must be a single occurrence
    if len(candidates) != 1:
        return (-1, 0, '')
    ci = candidates[0]
    # Must not be first or last note
    if ci == 0 or ci == n - 1:
        return (-1, 0, '')
    # Must be followed by direction change
    if direction == 'high':
        if pitches[ci + 1] >= pitches[ci]:
            return (-1, 0, '')
    else:
        if pitches[ci + 1] <= pitches[ci]:
            return (-1, 0, '')
    return (ci, pitches[ci], direction)


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
    """Score how well interval magnitudes intensify toward climax and relax after.

    Computes rank correlation between position and |interval| for
    pre-climax and post-climax segments separately.  Pre-climax should
    have positive correlation (growing), post-climax negative (shrinking),
    OR the reverse (shrinking then growing).  Either pattern scores well.
    """
    n = len(ivs)
    if climax_pos < 2 or climax_pos >= n:
        return 0.0
    pre = ivs[:climax_pos]
    post = ivs[climax_pos:]
    def _trend(segment: tuple[int, ...] | list) -> float:
        """Spearman-like: correlation of position with |interval|."""
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
    # Pattern A: intensify then relax (pre positive, post negative)
    score_a = (max(0.0, pre_trend) + max(0.0, -post_trend)) / 2.0
    # Pattern B: relax then intensify (pre negative, post positive)
    score_b = (max(0.0, -pre_trend) + max(0.0, post_trend)) / 2.0
    return max(score_a, score_b)


# ── Pitch scoring parameters ─────────────────────────────────────
MIN_SIGNATURE_LEAP: int = 3       # scale-degree interval to count as a leap
MAX_STEPWISE_RUN: int = 3         # consecutive same-direction steps before penalty
MIN_DISTINCT_INTERVALS: int = 3   # target for interval variety
LEAP_RECOVERY_WINDOW: int = 2     # intervals after leap to check for contrary step


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
    # At least one leap >= 3; bonus for early placement or at climax.
    leap_sizes = [(i, abs(iv)) for i, iv in enumerate(ivs) if abs(iv) >= MIN_SIGNATURE_LEAP]
    if not leap_sizes:
        s_leap = 0.0
    else:
        # Any leap >= 3 is equally good as a signature interval.
        # Placement bonus: first leap in first 40% of subject.
        first_pos = leap_sizes[0][0] / max(num_intervals - 1, 1)
        placement = 1.0 if first_pos < 0.4 else 0.5
        s_leap = 0.7 + 0.3 * placement
    # ── Leap recovery (20%) ─────────────────────────────────────
    # Leaps resolved by contrary-motion step sound purposeful.
    s_recovery = _leap_recovery_rate(ivs)
    # ── Run penalty (20%) ───────────────────────────────────────
    # Consecutive same-direction steps > 3 = scale run.
    longest_run = _longest_stepwise_run(ivs)
    if longest_run <= MAX_STEPWISE_RUN:
        s_run = 1.0
    else:
        # Each extra step beyond limit halves the score
        excess = longest_run - MAX_STEPWISE_RUN
        s_run = max(0.0, 1.0 - 0.3 * excess)
    # ── Interval profile (15%) ──────────────────────────────────
    # Reward distinct absolute interval sizes (target >= 3).
    distinct = len(set(abs(iv) for iv in ivs))
    s_variety = min(distinct / MIN_DISTINCT_INTERVALS, 1.0)
    # ── Climax (20%) ────────────────────────────────────────────
    # Unique extreme pitch, off-centre placement.
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
    # Tiebreaker: 1–2 direction changes better than 0 or 3+.
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


# ═══════════════════════════════════════════════════════════════════
#  Stage 2: Bar-fill duration enumeration
# ═══════════════════════════════════════════════════════════════════

def enumerate_bar_fills(bar_ticks: int) -> list[tuple[int, ...]]:
    """Enumerate all valid duration-index sequences filling one bar."""
    results: list[tuple[int, ...]] = []
    max_notes: int = min(MAX_NOTES_PER_BAR, bar_ticks // min(DURATION_TICKS))
    buf: list[int] = [0] * max_notes
    def _recurse(
        pos: int,
        remaining: int,
        last_di: int,
        same_run: int,
    ) -> None:
        if remaining == 0:
            if pos >= MIN_NOTES_PER_BAR:
                results.append(tuple(buf[:pos]))
            return
        if pos >= max_notes:
            return
        for di in range(NUM_DURATIONS):
            dt = DURATION_TICKS[di]
            if dt > remaining:
                continue
            if remaining - dt > 0 and remaining - dt < min(DURATION_TICKS):
                continue
            new_run = (same_run + 1) if di == last_di else 1
            if new_run > MAX_SAME_DUR_RUN:
                continue
            buf[pos] = di
            _recurse(pos + 1, remaining - dt, di, new_run)
    _recurse(0, bar_ticks, -1, 0)
    return results


def _has_isolated_semiquaver(fill: tuple[int, ...]) -> bool:
    """True if any semiquaver has no adjacent semiquaver neighbour."""
    for i, d in enumerate(fill):
        if d == SEMIQUAVER_DI:
            prev_sq = i > 0 and fill[i - 1] == SEMIQUAVER_DI
            next_sq = i < len(fill) - 1 and fill[i + 1] == SEMIQUAVER_DI
            if not prev_sq and not next_sq:
                return True
    return False


def enumerate_durations(
    n_bars: int,
    bar_ticks: int,
    note_counts: tuple[int, ...] | None = None,
) -> list[tuple[int, ...]]:
    """Combine per-bar fills into full-subject duration sequences."""
    raw_fills = enumerate_bar_fills(bar_ticks)
    if not raw_fills:
        return []
    fills = [f for f in raw_fills if not _has_isolated_semiquaver(f)]
    results: list[tuple[int, ...]] = []
    for combo in iter_product(fills, repeat=n_bars):
        seq: tuple[int, ...] = sum(combo, ())
        n_notes = len(seq)
        if n_notes > MAX_SUBJECT_NOTES:
            continue
        if note_counts is not None and n_notes not in note_counts:
            continue
        if len(set(seq)) < 2:
            continue
        if DURATION_TICKS[seq[-1]] < MIN_LAST_DUR_TICKS:
            continue
        head_n = len(combo[0])
        tail_n = n_notes - head_n
        if tail_n > 0:
            head_ticks = sum(DURATION_TICKS[d] for d in combo[0])
            tail_ticks = sum(DURATION_TICKS[d] for d in seq[head_n:])
            if head_ticks / head_n < tail_ticks / tail_n:
                continue
        results.append(seq)
    return results


# ═══════════════════════════════════════════════════════════════════
#  Stage 2 scoring: duration quality
# ═══════════════════════════════════════════════════════════════════

def _shannon_entropy(counts: list[int], total: int) -> float:
    """Normalised Shannon entropy, 0..1."""
    if total == 0 or len(counts) <= 1:
        return 0.0
    max_ent = math.log(len(counts))
    if max_ent == 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log(p)
    return ent / max_ent


def _closeness(value: float, target: float, width: float) -> float:
    """Gaussian closeness score, 1.0 at target."""
    return math.exp(-((value - target) ** 2) / (2 * width * width))


MAX_OPENING_TICKS: int = 4  # crotchet max for first note


MIN_DURATION_KINDS: int = 3  # need at least 3 distinct durations for interest


def score_duration_sequence(durs: tuple[int, ...]) -> float:
    """Score a duration sequence for baroque rhythmic character."""
    n_notes = len(durs)
    ticks = [DURATION_TICKS[d] for d in durs]
    distinct_durs = len(set(durs))
    # ── Duration variety (25%) ───────────────────────────────────
    # Need at least 3 distinct note values (e.g. semiquaver+quaver+crotchet).
    s_variety = min(distinct_durs / MIN_DURATION_KINDS, 1.0)
    # ── Semiquaver presence (20%) ───────────────────────────────
    # Baroque subjects typically have a semiquaver burst. Reward 2–4
    # semiquavers; penalise 0 or > 6 (too frenetic).
    sq_count = sum(1 for d in durs if d == SEMIQUAVER_DI)
    if sq_count == 0:
        s_semiquaver = 0.0
    elif 2 <= sq_count <= 4:
        s_semiquaver = 1.0
    elif sq_count <= 6:
        s_semiquaver = 0.6
    else:
        s_semiquaver = 0.3
    # ── Long-short contrast (20%) ──────────────────────────────
    # Ratio of longest to shortest tick. Target: 4–8x (e.g. minim vs
    # semiquaver). Bland if < 2x.
    longest = max(ticks)
    shortest = min(ticks)
    ratio = longest / shortest
    if ratio >= 4:
        s_contrast = 1.0
    elif ratio >= 2:
        s_contrast = (ratio - 1) / 3.0
    else:
        s_contrast = 0.0
    # ── Final note weight (15%) ─────────────────────────────────
    s_final = 1.0 if ticks[-1] > ticks[-2] else (0.5 if ticks[-1] == ticks[-2] else 0.0)
    # ── Opening not too long (10%) ──────────────────────────────
    s_opening = 1.0 if ticks[0] <= MAX_OPENING_TICKS else 0.5
    # ── No monotony (10%) ───────────────────────────────────────
    # Penalise long runs of identical durations.
    max_run = 1
    run = 1
    for i in range(1, n_notes):
        if durs[i] == durs[i - 1]:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    s_monotony = 1.0 if max_run <= 3 else max(0.0, 1.0 - 0.25 * (max_run - 3))
    return (
        0.25 * s_variety
        + 0.20 * s_semiquaver
        + 0.20 * s_contrast
        + 0.15 * s_final
        + 0.10 * s_opening
        + 0.10 * s_monotony
    )


# ═══════════════════════════════════════════════════════════════════
#  Melodic validators
# ═══════════════════════════════════════════════════════════════════

def _midi_intervals(midi: tuple[int, ...]) -> list[int]:
    """Semitone intervals between adjacent MIDI pitches."""
    return [midi[i + 1] - midi[i] for i in range(len(midi) - 1)]


def is_melodically_valid(midi: tuple[int, ...]) -> bool:
    """Check MIDI pitch sequence for forbidden intervals."""
    ivs = _midi_intervals(midi)
    for iv in ivs:
        a = abs(iv)
        if a == 6 or a in (10, 11):
            return False
    for i in range(len(ivs) - 1):
        if abs(ivs[i]) > 2 and abs(ivs[i + 1]) > 2:
            if (ivs[i] > 0) == (ivs[i + 1] > 0):
                return False
    if len(midi) >= 4:
        for i in range(len(midi) - 3):
            if abs(midi[i + 3] - midi[i]) == 6:
                return False
    return True


# ═══════════════════════════════════════════════════════════════════
#  Pipeline
# ═══════════════════════════════════════════════════════════════════

def _find_high_climax(pitches: list[int]) -> tuple[int, int]:
    """Find unique high-point index and pitch, or (-1, 0) if none."""
    hi_val = max(pitches)
    candidates = [i for i in range(len(pitches)) if pitches[i] == hi_val]
    if len(candidates) != 1:
        return (-1, 0)
    ci = candidates[0]
    if ci == 0 or ci == len(pitches) - 1:
        return (-1, 0)
    if pitches[ci + 1] >= pitches[ci]:
        return (-1, 0)
    return (ci, hi_val)


def _find_low_climax(pitches: list[int]) -> tuple[int, int]:
    """Find unique low-point index and pitch, or (-1, 0) if none."""
    lo_val = min(pitches)
    candidates = [i for i in range(len(pitches)) if pitches[i] == lo_val]
    if len(candidates) != 1:
        return (-1, 0)
    ci = candidates[0]
    if ci == 0 or ci == len(pitches) - 1:
        return (-1, 0)
    if pitches[ci + 1] <= pitches[ci]:
        return (-1, 0)
    return (ci, lo_val)


def _opening_direction(pitches: list[int]) -> int:
    """Net direction of the first third of the melody: +1 up, -1 down, 0 flat."""
    third = max(2, len(pitches) // 3)
    net = pitches[third] - pitches[0]
    return 1 if net > 0 else (-1 if net < 0 else 0)


def _derive_shape_name(pitches: list[int]) -> str:
    """Derive shape from pitch contour using dominant climax and opening direction."""
    n = len(pitches)
    hi_ci, _ = _find_high_climax(pitches)
    lo_ci, _ = _find_low_climax(pitches)
    hi_span = max(pitches) - pitches[0]
    lo_span = pitches[0] - min(pitches)
    opens_up = _opening_direction(pitches) >= 0
    # Determine dominant extreme
    if hi_ci >= 0 and lo_ci >= 0:
        use_high = (hi_span > lo_span) or (hi_span == lo_span and hi_ci <= lo_ci)
    elif hi_ci >= 0:
        use_high = True
    elif lo_ci >= 0:
        use_high = False
    else:
        net = pitches[-1] - pitches[0]
        return 'ascending' if net > 0 else 'descending' if net < 0 else 'flat'
    # Classify: arch/swoop require ascending opening + high climax;
    # dip/valley require descending opening + low climax.
    # Mismatches (descends first then peaks high) get swoop/dip.
    if use_high:
        if opens_up:
            return 'arch'
        else:
            return 'swoop'
    else:
        if not opens_up:
            return 'dip'
        else:
            return 'valley'


def _derive_leap_info(ivs: tuple[int, ...]) -> tuple[int, str, str]:
    """Derive leap_size, leap_direction, tail_direction."""
    max_abs = 0
    max_iv = 0
    for iv in ivs:
        if abs(iv) > max_abs:
            max_abs = abs(iv)
            max_iv = iv
    second_half = ivs[len(ivs) // 2:]
    net = sum(second_half)
    return (
        max_abs,
        "up" if max_iv > 0 else "down",
        "down" if net < 0 else "up",
    )


def select_subject(
    mode: str = "major",
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    target_bars: int | None = None,
    pitch_contour: str | None = None,
    rhythm_contour: str | None = None,
    note_counts: tuple[int, ...] | None = None,
    seed: int = 0,
    verbose: bool = False,
) -> GeneratedSubject:
    """Select best subject: generate, score, assign best duration, stretto-filter."""
    if target_bars is None:
        target_bars = 3
    bar_ticks = _bar_x2_ticks(metre)
    t_start = time.time()
    if verbose:
        print(f"select_subject: mode={mode} metre={metre} bars={target_bars} seed={seed}")
    # ── Stages 1+2: cached scored sequences ─────────────────────
    all_scored_durs = _cached_scored_durations(n_bars=target_bars, bar_ticks=bar_ticks)
    assert len(all_scored_durs) > 0, f"No durations for bars={target_bars} metre={metre}"
    if verbose:
        total_durs = sum(len(v) for v in all_scored_durs.values())
        print(f"  Durations: {total_durs} scored, counts={sorted(all_scored_durs.keys())}")
    # Best duration per note count — the combined score has no
    # cross-term so best pair is always (best pitch, best duration).
    best_dur_by_count: dict[int, tuple[float, tuple[int, ...]]] = {}
    for nc, scored_list in all_scored_durs.items():
        if scored_list:
            best_dur_by_count[nc] = scored_list[0]
    all_candidates: list[tuple[float, tuple[int, ...], tuple[int, ...], str]] = []
    for nc in sorted(all_scored_durs.keys()):
        if note_counts is not None and nc not in note_counts:
            continue
        if nc not in best_dur_by_count:
            continue
        t0 = time.time()
        all_pitch = _cached_scored_pitch(nc)
        t_gen = time.time() - t0
        if not all_pitch:
            if verbose:
                print(f"  {nc}n: 0 sequences")
            continue
        best_d_sc, best_d_seq = best_dur_by_count[nc]
        n_used = min(len(all_pitch), TOP_K_PITCH)
        if verbose:
            print(f"  {nc}n: {len(all_pitch):,} pitch (using {n_used}), "
                  f"top={all_pitch[0][0]:.3f} in {t_gen:.2f}s")
        # ── Validate, classify by contour, evaluate stretto ──────
        shape_counts: dict[str, int] = {}
        dur_slots = tuple(DURATION_TICKS[d] for d in best_d_seq)
        total_slots = sum(dur_slots)
        for p_sc, ivs in all_pitch[:TOP_K_PITCH]:
            degs = (0,) + tuple(sum(ivs[:j + 1]) for j in range(len(ivs)))
            midi = degrees_to_midi(degrees=degs, tonic_midi=tonic_midi, mode=mode)
            if not is_melodically_valid(midi):
                continue
            pitches = list(degs)
            shape = _derive_shape_name(pitches)
            count_in_shape = shape_counts.get(shape, 0)
            if count_in_shape >= TOP_K_PER_SHAPE:
                continue
            shape_counts[shape] = count_in_shape + 1
            combined = 0.50 * p_sc + 0.50 * best_d_sc
            offset_results = evaluate_all_offsets(
                midi=midi,
                dur_slots=dur_slots,
                metre=metre,
            )
            stretto_sc = score_stretto(
                offset_results=offset_results,
                total_slots=total_slots,
            )
            final_score = 0.60 * combined + 0.40 * stretto_sc
            all_candidates.append((final_score, ivs, best_d_seq, shape))
    assert len(all_candidates) > 0, "No valid subject found"
    all_candidates.sort(key=lambda x: x[0], reverse=True)
    # Filter by requested contour if specified
    if pitch_contour is not None:
        if verbose:
            from collections import Counter as _Ctr
            contour_dist = _Ctr(c[3] for c in all_candidates)
            print(f"  Contour distribution: {dict(contour_dist)}")
        all_candidates = [c for c in all_candidates if c[3] == pitch_contour]
        assert len(all_candidates) > 0, f"No candidates with contour '{pitch_contour}'"
    # Deduplicate: no two picks share the same pitch sequence
    seen_pitch: set[tuple[int, ...]] = set()
    unique: list[tuple[float, tuple[int, ...], tuple[int, ...], str]] = []
    for entry in all_candidates:
        if entry[1] not in seen_pitch:
            seen_pitch.add(entry[1])
            unique.append(entry)
    pick = seed % len(unique)
    best_score, best_ivs, best_durs, best_shape = unique[pick]
    if verbose:
        print(f"  Candidates: {len(all_candidates)} total, {len(unique)} unique, pick={pick}")
    # ── Convert to GeneratedSubject ──────────────────────────────
    degrees = (0,) + tuple(sum(best_ivs[:i + 1]) for i in range(len(best_ivs)))
    dur_ticks = [DURATION_TICKS[d] for d in best_durs]
    bars = sum(dur_ticks) // bar_ticks
    durations = tuple(t / X2_TICKS_PER_WHOLE for t in dur_ticks)
    midi_pitches = degrees_to_midi(degrees=degrees, tonic_midi=tonic_midi, mode=mode)
    leap_size, leap_direction, tail_direction = _derive_leap_info(best_ivs)
    # ── Stretto offsets (always computed) ────────────────────────
    dur_slots = tuple(DURATION_TICKS[d] for d in best_durs)
    total_slots = sum(dur_slots)
    all_offsets = evaluate_all_offsets(
        midi=midi_pitches,
        dur_slots=dur_slots,
        metre=metre,
    )
    viable_offsets = tuple(r for r in all_offsets if r.viable)
    elapsed = time.time() - t_start
    if verbose:
        stretto_sc = score_stretto(
            offset_results=all_offsets,
            total_slots=total_slots,
        )
        tightest = min(r.offset_slots for r in viable_offsets) if viable_offsets else 0
        print(f"  Stretto: {len(viable_offsets)} offsets, "
              f"tightest={tightest} slots, score={stretto_sc:.3f}")
        slots_per_beat = 4 if metre[1] == 4 else 2
        for r in sorted(viable_offsets, key=lambda r: r.offset_slots):
            print(f"    offset={r.offset_slots} slots "
                  f"({r.offset_slots / slots_per_beat:.1f} beats) "
                  f"cost={r.dissonance_cost}")
        print(f"  Selected: {best_shape} {len(degrees)}n score={best_score:.4f} "
              f"bars={bars} in {elapsed:.2f}s")
        print(f"  Degrees: {degrees}")
        print(f"  Durations: {durations}")
    return GeneratedSubject(
        scale_indices=degrees,
        durations=durations,
        midi_pitches=midi_pitches,
        bars=bars,
        score=best_score,
        seed=0,
        mode=mode,
        head_name=best_shape,
        leap_size=leap_size,
        leap_direction=leap_direction,
        tail_direction=tail_direction,
        stretto_offsets=viable_offsets,
    )


# ═══════════════════════════════════════════════════════════════════
#  Display helpers
# ═══════════════════════════════════════════════════════════════════

def display_subject(rank: int, score: float, ivs: tuple, durs: tuple) -> None:
    """Pretty-print a ranked subject."""
    pitches = [0]
    for iv in ivs:
        pitches.append(pitches[-1] + iv)
    dur_names = [DURATION_NAMES[d] for d in durs]
    dur_ticks = [DURATION_TICKS[d] for d in durs]
    print(f"#{rank + 1}  score={score:.4f}")
    print(f"  Pitches:    {pitches}")
    print(f"  Intervals:  {list(ivs)}")
    print(f"  Rhythm:     {dur_names}")
    print(f"  Ticks:      {dur_ticks}  total={sum(dur_ticks)}")
    print()


def decode_subject(intervals: tuple, durations: tuple) -> None:
    """Print a human-readable subject."""
    pitches = [0]
    for iv in intervals:
        pitches.append(pitches[-1] + iv)
    print(f"  Pitches:   {pitches}")
    print(f"  Intervals: {list(intervals)}")
    print(f"  Durations: {[DURATION_NAMES[d] for d in durations]}")
    print(f"  Ticks:     {[DURATION_TICKS[d] for d in durations]}")


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a fugue subject")
    parser.add_argument("--mode", type=str, default="major",
                        choices=["major", "minor"])
    parser.add_argument("--metre", type=int, nargs=2, default=[4, 4],
                        metavar=("NUM", "DEN"))
    parser.add_argument("--bars", type=int, default=2)
    parser.add_argument("--tonic", type=int, default=60)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--contour", type=str, default=None,
                        choices=["arch", "valley", "swoop", "dip",
                                 "ascending", "descending"])
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    result = select_subject(
        mode=args.mode,
        metre=tuple(args.metre),
        tonic_midi=args.tonic,
        target_bars=args.bars,
        pitch_contour=args.contour,
        seed=args.seed,
        verbose=args.verbose,
    )
    print(f"\nResult: {len(result.scale_indices)}n, score={result.score:.4f}")
    print(f"  Degrees: {result.scale_indices}")
    print(f"  MIDI:    {result.midi_pitches}")
    print(f"  Durs:    {result.durations}")