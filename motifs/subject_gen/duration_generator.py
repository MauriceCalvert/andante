"""Stage 2: Bar-fill duration enumeration and scoring."""
from itertools import product as iter_product

from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.constants import (
    DURATION_TICKS,
    MAX_NOTES_PER_BAR,
    MAX_OPENING_TICKS,
    MAX_SAME_DUR_RUN,
    MAX_SUBJECT_NOTES,
    MIN_DURATION_KINDS,
    MIN_LAST_DUR_TICKS,
    MIN_NOTES_PER_BAR,
    NUM_DURATIONS,
    SEMIQUAVER_DI,
)
from motifs.subject_gen.scoring import _shannon_entropy


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


def score_duration_sequence(durs: tuple[int, ...]) -> float:
    """Score a duration sequence for baroque rhythmic character."""
    n_notes = len(durs)
    ticks = [DURATION_TICKS[d] for d in durs]
    distinct_durs = len(set(durs))
    # ── Duration variety (25%) ───────────────────────────────────
    s_variety = min(distinct_durs / MIN_DURATION_KINDS, 1.0)
    # ── Semiquaver presence (20%) ───────────────────────────────
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
