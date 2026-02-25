"""Stage 2: Bar-fill duration enumeration."""
from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.constants import (
    DURATION_TICKS,
    MAX_DUR_RATIO,
    MAX_DURS_PER_COUNT,
    MAX_NOTES_PER_BAR,
    MAX_SAME_DUR_RUN,
    MAX_SUBJECT_NOTES,
    MIN_LAST_DUR_TICKS,
    MIN_NOTES_PER_BAR,
    MIN_SUBJECT_NOTES,
    NUM_DURATIONS,
)

MAX_FILLS_PER_BAR_GROUP: int = 200


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
            if last_di >= 0:
                prev_t = DURATION_TICKS[last_di]
                if max(dt, prev_t) > MAX_DUR_RATIO * min(dt, prev_t):
                    continue
            new_run = (same_run + 1) if di == last_di else 1
            if new_run > MAX_SAME_DUR_RUN:
                continue
            buf[pos] = di
            _recurse(pos + 1, remaining - dt, di, new_run)
    _recurse(0, bar_ticks, -1, 0)
    return results


def _bar_fill_score(fill: tuple[int, ...]) -> float:
    """Score a single bar fill by rhythmic interest."""
    ticks = [DURATION_TICKS[d] for d in fill]
    shortest = min(ticks)
    longest = max(ticks)
    if shortest == longest:
        return 0.0
    contrast = min((longest / shortest - 1.0) / 5.0, 1.0)
    distinct = len(set(fill)) / NUM_DURATIONS
    return contrast + distinct


def _group_and_cap_fills(
    fills: list[tuple[int, ...]],
    cap: int,
) -> dict[int, list[tuple[int, ...]]]:
    """Group fills by note count, keep top `cap` per group by score."""
    by_count: dict[int, list[tuple[int, ...]]] = {}
    for f in fills:
        by_count.setdefault(len(f), []).append(f)
    for nc in by_count:
        if len(by_count[nc]) > cap:
            by_count[nc].sort(key=_bar_fill_score, reverse=True)
            by_count[nc] = by_count[nc][:cap]
    return by_count


def enumerate_durations(
    n_bars: int,
    bar_ticks: int,
    note_counts: tuple[int, ...] | None = None,
) -> list[tuple[int, ...]]:
    """Combine per-bar fills into full-subject duration sequences."""
    raw_fills = enumerate_bar_fills(bar_ticks)
    if not raw_fills:
        return []
    fills_by_count = _group_and_cap_fills(raw_fills, MAX_FILLS_PER_BAR_GROUP)
    results: list[tuple[int, ...]] = []
    all_counts = sorted(fills_by_count.keys())
    if n_bars == 2:
        _combine_2bars(fills_by_count, all_counts, note_counts, results)
    elif n_bars == 3:
        _combine_3bars(fills_by_count, all_counts, note_counts, results)
    else:
        _combine_nbars(fills_by_count, all_counts, note_counts, n_bars, results)
    return results


def _valid_ending(seq: tuple[int, ...]) -> bool:
    """Last note must be at least MIN_LAST_DUR_TICKS."""
    return DURATION_TICKS[seq[-1]] >= MIN_LAST_DUR_TICKS


def _smooth_boundary(fill_a: tuple[int, ...], fill_b: tuple[int, ...]) -> bool:
    """Check adjacent-duration ratio at the bar boundary."""
    t_a: int = DURATION_TICKS[fill_a[-1]]
    t_b: int = DURATION_TICKS[fill_b[0]]
    return max(t_a, t_b) <= MAX_DUR_RATIO * min(t_a, t_b)


def _combine_2bars(
    fills_by_count: dict[int, list[tuple[int, ...]]],
    all_counts: list[int],
    note_counts: tuple[int, ...] | None,
    results: list[tuple[int, ...]],
) -> None:
    """Combine two bars, skipping pairs that can't hit target note counts."""
    for nc1 in all_counts:
        for nc2 in all_counts:
            total_n = nc1 + nc2
            if total_n < MIN_SUBJECT_NOTES or total_n > MAX_SUBJECT_NOTES:
                continue
            if note_counts is not None and total_n not in note_counts:
                continue
            for f1 in fills_by_count[nc1]:
                for f2 in fills_by_count[nc2]:
                    if f1 == f2:
                        continue
                    if not _smooth_boundary(f1, f2):
                        continue
                    seq = f1 + f2
                    if not _valid_ending(seq):
                        continue
                    if len(set(seq)) < 2:
                        continue
                    results.append(seq)


def _combine_3bars(
    fills_by_count: dict[int, list[tuple[int, ...]]],
    all_counts: list[int],
    note_counts: tuple[int, ...] | None,
    results: list[tuple[int, ...]],
) -> None:
    """Combine three bars."""
    for nc1 in all_counts:
        for nc2 in all_counts:
            for nc3 in all_counts:
                total_n = nc1 + nc2 + nc3
                if total_n < MIN_SUBJECT_NOTES or total_n > MAX_SUBJECT_NOTES:
                    continue
                if note_counts is not None and total_n not in note_counts:
                    continue
                for f1 in fills_by_count[nc1]:
                    for f2 in fills_by_count[nc2]:
                        if f2 == f1:
                            continue
                        if not _smooth_boundary(f1, f2):
                            continue
                        for f3 in fills_by_count[nc3]:
                            if f3 == f1 or f3 == f2:
                                continue
                            if not _smooth_boundary(f2, f3):
                                continue
                            seq = f1 + f2 + f3
                            if not _valid_ending(seq):
                                continue
                            if len(set(seq)) < 2:
                                continue
                            results.append(seq)


def _combine_nbars(
    fills_by_count: dict[int, list[tuple[int, ...]]],
    all_counts: list[int],
    note_counts: tuple[int, ...] | None,
    n_bars: int,
    results: list[tuple[int, ...]],
) -> None:
    """Generic n-bar combiner (fallback for 4+ bars)."""
    from itertools import product as iter_product
    all_fills: list[tuple[int, ...]] = []
    for nc in all_counts:
        all_fills.extend(fills_by_count[nc])
    for combo in iter_product(all_fills, repeat=n_bars):
        if len(set(combo)) < len(combo):
            continue
        if not all(_smooth_boundary(combo[i], combo[i + 1]) for i in range(len(combo) - 1)):
            continue
        seq: tuple[int, ...] = sum(combo, ())
        n_notes = len(seq)
        if n_notes < MIN_SUBJECT_NOTES or n_notes > MAX_SUBJECT_NOTES:
            continue
        if note_counts is not None and n_notes not in note_counts:
            continue
        if not _valid_ending(seq):
            continue
        if len(set(seq)) < 2:
            continue
        results.append(seq)


def _rhythm_score(dur_seq: tuple[int, ...]) -> float:
    """Score rhythm pattern by contrast and variety. Higher = more interesting."""
    ticks = [DURATION_TICKS[d] for d in dur_seq]
    shortest = min(ticks)
    longest = max(ticks)
    if shortest == longest:
        return 0.0
    contrast = min((longest / shortest - 1.0) / 5.0, 1.0)
    distinct = len(set(dur_seq)) / NUM_DURATIONS
    return contrast + distinct


def _cached_scored_durations(
    n_bars: int,
    bar_ticks: int,
    verbose: bool = False,
) -> dict[int, list[tuple[int, ...]]]:
    """Top-K valid duration patterns per note count, cached to disk."""
    key = f"dur_top_{n_bars}b_{bar_ticks}t_{MAX_DURS_PER_COUNT}.pkl"
    cached = _load_cache(key)
    if cached is not None:
        if verbose:
            for nc in sorted(cached.keys()):
                print(f"    durations {nc}n: {len(cached[nc])} (cached)")
        return cached
    all_durs = enumerate_durations(n_bars=n_bars, bar_ticks=bar_ticks)
    by_count: dict[int, list[tuple[int, ...]]] = {}
    for d in all_durs:
        by_count.setdefault(len(d), []).append(d)
    for nc in sorted(by_count.keys()):
        raw: int = len(by_count[nc])
        if raw > MAX_DURS_PER_COUNT:
            by_count[nc].sort(key=_rhythm_score, reverse=True)
            by_count[nc] = by_count[nc][:MAX_DURS_PER_COUNT]
        if verbose:
            kept: int = len(by_count[nc])
            capped: str = f" (capped from {raw})" if raw > kept else ""
            print(f"    durations {nc}n: {kept}{capped}")
    _save_cache(key, by_count)
    return by_count
