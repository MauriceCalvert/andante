"""Segment-level rhythm generation.

Generates cell sequences for a single segment (head or tail) using
a restricted vocabulary of cells.  Each cell can independently use
any allowed scale factor.
"""
import logging
from itertools import product as iter_product
from typing import Iterator

from motifs.subject_gen.constants import DURATION_TICKS
from motifs.subject_gen.rhythm_cells import (
    CELLS_BY_SIZE,
    Cell,
    TRANSITION,
)

logger: logging.Logger = logging.getLogger(__name__)

# ── Tick-to-index lookup ─────────────────────────────────────────────

_TICK_TO_INDEX: dict[int, int] = {
    tick: idx for idx, tick in enumerate(DURATION_TICKS)
}


def _cells_to_indices(
    cells: tuple[Cell, ...],
    scales: tuple[int, ...],
) -> tuple[int, ...] | None:
    """Convert cells + per-cell scales to duration index tuple."""
    assert len(cells) == len(scales)
    indices: list[int] = []
    for cell, scale in zip(cells, scales):
        for tick in cell.ticks:
            scaled: int = tick * scale
            idx: int | None = _TICK_TO_INDEX.get(scaled)
            if idx is None:
                return None
            indices.append(idx)
    return tuple(indices)


def _partition_segment(
    n_notes: int,
    allowed_sizes: tuple[int, ...],
) -> Iterator[tuple[int, ...]]:
    """Yield all ways to partition n_notes into allowed cell sizes."""
    yield from _partition_recurse(
        remaining=n_notes,
        min_size=min(allowed_sizes),
        allowed=allowed_sizes,
        acc=[],
    )


def _partition_recurse(
    remaining: int,
    min_size: int,
    allowed: tuple[int, ...],
    acc: list[int],
) -> Iterator[tuple[int, ...]]:
    """Recursive partition helper."""
    if remaining == 0:
        yield tuple(acc)
        return
    for size in allowed:
        if size < min_size:
            continue
        if size > remaining:
            continue
        acc.append(size)
        yield from _partition_recurse(
            remaining=remaining - size,
            min_size=size,
            allowed=allowed,
            acc=acc,
        )
        acc.pop()


def _distinct_permutations(seq: list[int]) -> Iterator[tuple[int, ...]]:
    """Yield all distinct permutations of a sorted sequence."""
    arr: list[int] = list(seq)
    n: int = len(arr)
    yield tuple(arr)
    while True:
        i: int = n - 2
        while i >= 0 and arr[i] >= arr[i + 1]:
            i -= 1
        if i < 0:
            return
        j: int = n - 1
        while arr[j] <= arr[i]:
            j -= 1
        arr[i], arr[j] = arr[j], arr[i]
        arr[i + 1:] = arr[i + 1:][::-1]
        yield tuple(arr)


def _transition_score(cells: tuple[Cell, ...]) -> float:
    """Product of transition weights for adjacent pairs."""
    score: float = 1.0
    for i in range(len(cells) - 1):
        weight: float = TRANSITION[(cells[i].name, cells[i + 1].name)]
        if weight <= 0.0:
            return 0.0
        score *= weight
    return score


def generate_segment_rhythms(
    n_notes: int,
    total_ticks: int,
    allowed_cell_names: tuple[str, ...],
    allowed_scales: tuple[int, ...],
) -> list[tuple[tuple[int, ...], tuple[Cell, ...], float]]:
    """Generate all valid (dur_indices, cells, score) for a segment.

    Only uses cells whose names are in allowed_cell_names.
    Each cell independently picks from allowed_scales.
    """
    # Build restricted CELLS_BY_SIZE from allowed names.
    allowed_cells: dict[int, list[Cell]] = {}
    for cell_list in CELLS_BY_SIZE.values():
        for cell in cell_list:
            if cell.name in allowed_cell_names:
                allowed_cells.setdefault(cell.notes, []).append(cell)
    allowed_sizes: tuple[int, ...] = tuple(sorted(allowed_cells.keys()))
    if not allowed_sizes:
        return []
    results: list[tuple[tuple[int, ...], tuple[Cell, ...], float]] = []
    for partition in _partition_segment(n_notes=n_notes, allowed_sizes=allowed_sizes):
        sorted_sizes: list[int] = sorted(partition)
        for perm in _distinct_permutations(sorted_sizes):
            cell_lists: list[list[Cell]] = [allowed_cells[s] for s in perm]
            for cells in iter_product(*cell_lists):
                score: float = _transition_score(cells=cells)
                if score <= 0.0:
                    continue
                n_cells: int = len(cells)
                for scale_combo in iter_product(allowed_scales, repeat=n_cells):
                    indices: tuple[int, ...] | None = _cells_to_indices(
                        cells=cells,
                        scales=scale_combo,
                    )
                    if indices is None:
                        continue
                    tick_sum: int = sum(DURATION_TICKS[i] for i in indices)
                    if tick_sum != total_ticks:
                        continue
                    results.append((indices, cells, score))
    return results


def boundary_transition_ok(
    head_cells: tuple[Cell, ...],
    tail_cells: tuple[Cell, ...],
) -> bool:
    """Check that the last head cell transitions acceptably to the first tail cell."""
    if not head_cells or not tail_cells:
        return False
    weight: float = TRANSITION[(head_cells[-1].name, tail_cells[0].name)]
    return weight > 0.0
