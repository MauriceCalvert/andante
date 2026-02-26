"""Cell-based baroque rhythm generator.

Builds duration sequences by concatenating named rhythm cells (iamb,
trochee, dotted, dactyl, anapaest, tirata) subject to a transition
table that encodes idiomatic successions.

Supports mixed-scale sequences: each cell can independently use scale 1
(semiquaver level) or scale 2 (quaver level), allowing semiquaver runs
embedded in a mostly-quaver rhythm framework.
"""
import logging
from itertools import product as iter_product
from typing import Iterator

from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.constants import (
    DURATION_TICKS,
    MAX_DURS_PER_COUNT,
    MAX_SUBJECT_NOTES,
    MIN_LAST_DUR_TICKS,
    MIN_SUBJECT_NOTES,
)
from motifs.subject_gen.rhythm_cells import (
    CELLS_BY_SIZE,
    Cell,
    SCALES,
    TRANSITION,
)

logger = logging.getLogger(__name__)

# ── Tick-to-index lookup (built once at import) ──────────────────────

_TICK_TO_INDEX: dict[int, int] = {
    tick: idx for idx, tick in enumerate(DURATION_TICKS)
}


def _cached_scored_durations(
    n_bars: int,
    bar_ticks: int,
    verbose: bool = False,
) -> dict[int, list[tuple[tuple[int, ...], tuple[Cell, ...]]]]:
    """Top-K valid duration patterns per note count, cached to disk.

    Each entry is (dur_indices, cell_sequence).
    """
    assert n_bars > 0, f"n_bars must be positive, got {n_bars}"
    assert bar_ticks > 0, f"bar_ticks must be positive, got {bar_ticks}"

    key: str = f"cell_dur_v6_{n_bars}b_{bar_ticks}t_{MAX_DURS_PER_COUNT}.pkl"
    cached = _load_cache(key)
    if cached is not None:
        if verbose:
            for nc in sorted(cached.keys()):
                logger.info("    durations %dn: %d (cached)", nc, len(cached[nc]))
        return cached

    total_ticks: int = n_bars * bar_ticks
    by_count: dict[int, list[tuple[tuple[int, ...], tuple[Cell, ...], float]]] = {}

    for n_notes in range(MIN_SUBJECT_NOTES, MAX_SUBJECT_NOTES + 1):
        for seq, cells, score in _generate_sequences(
            n_notes=n_notes,
            total_ticks=total_ticks,
            bar_ticks=bar_ticks,
        ):
            by_count.setdefault(n_notes, []).append((seq, cells, score))

    result: dict[int, list[tuple[tuple[int, ...], tuple[Cell, ...]]]] = {}
    for nc in sorted(by_count.keys()):
        entries: list[tuple[tuple[int, ...], tuple[Cell, ...], float]] = by_count[nc]
        entries.sort(key=lambda x: x[2], reverse=True)
        raw: int = len(entries)
        if raw > MAX_DURS_PER_COUNT:
            entries = entries[:MAX_DURS_PER_COUNT]
        result[nc] = [(seq, cells) for seq, cells, _ in entries]
        if verbose:
            kept: int = len(result[nc])
            capped: str = f" (capped from {raw})" if raw > kept else ""
            logger.info("    durations %dn: %d%s", nc, kept, capped)

    _save_cache(key, result)
    return result


def _spans_barline(
    indices: tuple[int, ...],
    bar_ticks: int,
) -> bool:
    """True if any note's duration crosses a bar boundary."""
    if bar_ticks <= 0:
        return False
    onset: int = 0
    for idx in indices:
        dur: int = DURATION_TICKS[idx]
        bar_of_onset: int = onset // bar_ticks
        bar_of_end: int = (onset + dur - 1) // bar_ticks
        if bar_of_end != bar_of_onset:
            return True
        onset += dur
    return False


def _distinct_permutations(seq: list[int]) -> Iterator[tuple[int, ...]]:
    """Yield all distinct permutations of a sorted sequence.

    Uses the Pandita next-permutation algorithm on a mutable list.
    The input must be sorted ascending.
    """
    arr: list[int] = list(seq)
    n: int = len(arr)
    yield tuple(arr)
    while True:
        # Find largest i such that arr[i] < arr[i+1]
        i: int = n - 2
        while i >= 0 and arr[i] >= arr[i + 1]:
            i -= 1
        if i < 0:
            return
        # Find largest j such that arr[i] < arr[j]
        j: int = n - 1
        while arr[j] <= arr[i]:
            j -= 1
        arr[i], arr[j] = arr[j], arr[i]
        # Reverse from i+1 to end
        arr[i + 1:] = arr[i + 1:][::-1]
        yield tuple(arr)


def _generate_sequences(
    n_notes: int,
    total_ticks: int,
    bar_ticks: int = 0,
) -> Iterator[tuple[tuple[int, ...], tuple[Cell, ...], float]]:
    """Yield (duration_index_tuple, cell_sequence, score) for all valid cell sequences.

    Two passes:
      1. Standard partitions from {2,3,4} — no longa cells.
      2. Longa-final: partitions of (n_notes-1) from {2,3,4} with a
         single longa appended at the end.  This gives minim/crotchet/
         quaver finals without permuting longa into every position.
    """
    import time
    t0 = time.time()
    checked: int = 0
    yielded: int = 0
    last_report: float = t0
    # Phase 1: no-longa partitions
    for seq, cells, score, checked, yielded, last_report in _emit_partitions(
        partitions=list(_partitions(n=n_notes)),
        n_notes=n_notes,
        total_ticks=total_ticks,
        bar_ticks=bar_ticks,
        longa_suffix=False,
        checked=checked,
        yielded=yielded,
        t0=t0,
        last_report=last_report,
    ):
        yield (seq, cells, score)
    # Phase 2: longa-final (only if n_notes > 1)
    if n_notes > 1:
        for seq, cells, score, checked, yielded, last_report in _emit_partitions(
            partitions=list(_partitions(n=n_notes - 1)),
            n_notes=n_notes,
            total_ticks=total_ticks,
            bar_ticks=bar_ticks,
            longa_suffix=True,
            checked=checked,
            yielded=yielded,
            t0=t0,
            last_report=last_report,
        ):
            yield (seq, cells, score)
    elapsed = time.time() - t0
    print(f"[dur_gen] {n_notes}n done: checked {checked:,} yielded {yielded} in {elapsed:.1f}s")


def _emit_partitions(
    partitions: list[tuple[int, ...]],
    n_notes: int,
    total_ticks: int,
    bar_ticks: int,
    longa_suffix: bool,
    checked: int,
    yielded: int,
    t0: float,
    last_report: float,
) -> Iterator[tuple[tuple[int, ...], tuple[Cell, ...], float, int, int, float]]:
    """Inner loop shared by both passes of _generate_sequences."""
    import time
    longa_cells: list[Cell] = CELLS_BY_SIZE.get(1, [])
    for pi, partition in enumerate(partitions):
        sorted_sizes: list[int] = sorted(partition)
        for perm in _distinct_permutations(sorted_sizes):
            cell_lists: list[list[Cell]] = [CELLS_BY_SIZE[s] for s in perm]
            if longa_suffix:
                cell_lists.append(longa_cells)
            for cells in iter_product(*cell_lists):
                score: float = _transition_score(cells=cells)
                if score <= 0.0:
                    continue
                n_cells: int = len(cells)
                for scale_combo in iter_product(SCALES, repeat=n_cells):
                    checked += 1
                    now = time.time()
                    if now - last_report >= 10.0:
                        tag: str = "+longa" if longa_suffix else "std"
                        print(f"[dur_gen] {n_notes}n ({tag}): checked {checked:,} "
                              f"yielded={yielded} partition {pi+1}/{len(partitions)} "
                              f"{partition} elapsed={now - t0:.1f}s")
                        last_report = now
                    indices: tuple[int, ...] | None = _cells_to_indices(
                        cells=cells,
                        scales=scale_combo,
                    )
                    if indices is None:
                        continue
                    tick_sum: int = sum(DURATION_TICKS[i] for i in indices)
                    if tick_sum != total_ticks:
                        continue
                    if _spans_barline(indices=indices, bar_ticks=bar_ticks):
                        continue
                    if DURATION_TICKS[indices[-1]] < MIN_LAST_DUR_TICKS:
                        continue
                    if DURATION_TICKS[indices[-1]] < DURATION_TICKS[indices[-2]]:
                        continue
                    yielded += 1
                    yield (indices, cells, score, checked, yielded, last_report)


def _cells_to_indices(
    cells: tuple[Cell, ...],
    scales: tuple[int, ...],
) -> tuple[int, ...] | None:
    """Convert a cell sequence to duration-index tuple with per-cell scales.

    Returns None if any scaled tick has no matching DURATION_TICKS entry.
    """
    assert len(cells) == len(scales), (
        f"cells length {len(cells)} != scales length {len(scales)}"
    )
    indices: list[int] = []
    for cell, scale in zip(cells, scales):
        for tick in cell.ticks:
            scaled: int = tick * scale
            idx: int | None = _TICK_TO_INDEX.get(scaled)
            if idx is None:
                return None
            indices.append(idx)
    return tuple(indices)


def _partitions(n: int) -> Iterator[tuple[int, ...]]:
    """Yield all ways to write n as an ordered multiset of 2s, 3s, and 4s.

    Each result is a tuple of sizes summing to n. Only one representative
    per multiset is yielded (sorted ascending); distinct orderings are
    handled by _distinct_permutations in the caller.
    """
    assert n >= 0, f"Cannot partition negative n={n}"
    yield from _partition_recurse(
        remaining=n,
        min_size=2,
        acc=[],
    )


def _partition_recurse(
    remaining: int,
    min_size: int,
    acc: list[int],
) -> Iterator[tuple[int, ...]]:
    """Recursive helper for _partitions."""
    if remaining == 0:
        yield tuple(acc)
        return
    if remaining == 1:
        return
    for size in (2, 3, 4):
        if size < min_size:
            continue
        if size > remaining:
            continue
        acc.append(size)
        yield from _partition_recurse(
            remaining=remaining - size,
            min_size=size,
            acc=acc,
        )
        acc.pop()


def _transition_score(cells: tuple[Cell, ...]) -> float:
    """Product of transition weights for adjacent cell pairs.

    Returns 0.0 if any pair is forbidden (N). Otherwise the product
    of all Y (1.0) and W (0.5) weights.
    """
    score: float = 1.0
    for i in range(len(cells) - 1):
        weight: float = TRANSITION[(cells[i].name, cells[i + 1].name)]
        if weight <= 0.0:
            return 0.0
        score *= weight
    return score
