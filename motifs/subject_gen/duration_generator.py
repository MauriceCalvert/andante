"""Stage 2: Bar-fill duration enumeration."""
from itertools import product as iter_product

from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.constants import (
    DURATION_TICKS,
    MAX_NOTES_PER_BAR,
    MAX_SAME_DUR_RUN,
    MAX_SUBJECT_NOTES,
    MIN_LAST_DUR_TICKS,
    MIN_NOTES_PER_BAR,
    MIN_SUBJECT_NOTES,
    NUM_DURATIONS,
    SEMIQUAVER_DI,
)


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
        if n_notes < MIN_SUBJECT_NOTES or n_notes > MAX_SUBJECT_NOTES:
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


def _cached_scored_durations(
    n_bars: int,
    bar_ticks: int,
) -> dict[int, list[tuple[int, ...]]]:
    """All duration patterns per note count, cached to disk."""
    key = f"dur_scored_{n_bars}b_{bar_ticks}t.pkl"
    cached = _load_cache(key)
    if cached is not None:
        return cached
    all_durs = enumerate_durations(n_bars=n_bars, bar_ticks=bar_ticks)
    result: dict[int, list[tuple[int, ...]]] = {}
    for d in all_durs:
        result.setdefault(len(d), []).append(d)
    _save_cache(key, result)
    return result
