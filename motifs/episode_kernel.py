"""Episode kernel source — paired-kernel chain solver for sequential episodes.

Extracts two-voice PairedKernels from the fugue exposition and chains them
into sequences that fill a target bar count.  The chain is used by
EpisodeDialogue to drive the per-iteration texture.
"""
import logging
import random
from fractions import Fraction

from motifs.extract_kernels import PairedKernel, extract_paired_kernels
from motifs.subject_loader import SubjectTriple
from shared.music_math import parse_metre

_log: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_KERNELS_PER_FAMILY: int = 3
_MAX_CANDIDATES: int = 200
_MAX_KERNEL_DURATION_RATIO: Fraction = Fraction(1, 2)  # half-bar cap
_MAX_NODES: int = 50000
_MAX_SEGMENTS: int = 5
_SEED: int = 42


# ---------------------------------------------------------------------------
# Pool builder
# ---------------------------------------------------------------------------


def _build_pool(kernels: list[PairedKernel], bar_length: Fraction) -> list[PairedKernel]:
    """Build working pool: drop over-long kernels, keep up to 3 per source family.

    Prefers variety in note-count across the family.
    """
    cap: Fraction = bar_length * _MAX_KERNEL_DURATION_RATIO
    families: dict[str, list[PairedKernel]] = {}
    for pk in kernels:
        if pk.total_duration > cap:
            continue
        # Strip _inv and sub-pair suffixes to identify family.
        fam: str = pk.source
        for suffix in ("_inv", "_f2", "_l2", "_f2_inv", "_l2_inv"):
            fam = fam.removesuffix(suffix)
        families.setdefault(fam, []).append(pk)

    pool: list[PairedKernel] = []
    for fam in sorted(families.keys()):
        candidates: list[PairedKernel] = families[fam]
        # Sort by note count (prefer variety) then duration.
        candidates.sort(key=lambda pk: (
            max(len(pk.upper_degrees), len(pk.lower_degrees)),
            pk.total_duration,
        ))
        seen_note_counts: set[int] = set()
        selected: list[PairedKernel] = []
        for c in candidates:
            nc: int = max(len(c.upper_degrees), len(c.lower_degrees))
            if nc not in seen_note_counts:
                selected.append(c)
                seen_note_counts.add(nc)
            if len(selected) >= _KERNELS_PER_FAMILY:
                break
        # Fill up to cap if fewer than _KERNELS_PER_FAMILY distinct note counts.
        for c in candidates:
            if c not in selected:
                selected.append(c)
            if len(selected) >= _KERNELS_PER_FAMILY:
                break
        pool.extend(selected)

    return pool


# ---------------------------------------------------------------------------
# EpisodeKernelSource
# ---------------------------------------------------------------------------


class EpisodeKernelSource:
    """Generates unique paired-kernel chains for sequential episodes.

    Each call to generate() returns a flat list of PairedKernels whose
    total durations sum to bar_count * bar_length.  Successive calls use
    different family combinations for episode variety.
    """

    def __init__(self, triple: SubjectTriple, seed: int = _SEED) -> None:
        metre_str: str = f"{triple.metre[0]}/{triple.metre[1]}"
        self._bar_length: Fraction = parse_metre(metre=metre_str)[0]
        all_kernels: list[PairedKernel] = extract_paired_kernels(fugue=triple)
        self._pool: list[PairedKernel] = _build_pool(
            kernels=all_kernels, bar_length=self._bar_length,
        )
        _log.debug(
            "EpisodeKernelSource: %d kernels in pool (from %d raw)",
            len(self._pool), len(all_kernels),
        )

        # Atoms: (pool_index, reps, total_duration * reps), sorted duration desc.
        self._atoms: list[tuple[int, int, Fraction]] = sorted(
            [
                (idx, reps, pk.total_duration * reps)
                for idx, pk in enumerate(self._pool)
                for reps in (1, 2)
            ],
            key=lambda a: a[2],
            reverse=True,
        )
        self._used: set[tuple[tuple[str, int], ...]] = set()
        self._rng: random.Random = random.Random(seed)

    @property
    def pool(self) -> list[PairedKernel]:
        """Kernel pool available for episode construction."""
        return list(self._pool)

    def generate(self, bar_count: int) -> list[PairedKernel] | None:
        """Return a flat list of bar_count PairedKernels, or None if unsolvable.

        Each entry in the returned list corresponds to one episode iteration.
        Kernels are ordered so shorter ones fall toward the end (fragmentation).
        """
        assert bar_count >= 1, f"bar_count must be >= 1, got {bar_count}"
        if len(self._pool) < 2:
            _log.debug("EpisodeKernelSource.generate: pool too small (%d)", len(self._pool))
            return None

        target_dur: Fraction = self._bar_length * bar_count
        segments: list[tuple[PairedKernel, int]] | None = self._solve(
            target_dur=target_dur,
        )
        if segments is None:
            _log.debug("EpisodeKernelSource.generate: no solution for bar_count=%d", bar_count)
            return None

        # Log selected chain.
        chain_desc: str = " + ".join(
            f"{pk.source}×{reps}" for pk, reps in segments
        )
        _log.debug("EpisodeKernelSource chain: [%s]", chain_desc)

        # Expand to flat list (one PairedKernel per iteration).
        result: list[PairedKernel] = []
        for pk, reps in segments:
            for _ in range(reps):
                result.append(pk)

        assert len(result) == bar_count, (
            f"Chain expanded to {len(result)} iterations but bar_count={bar_count}. "
            "Solver produced incorrect total duration."
        )
        return result

    # -----------------------------------------------------------------------
    # DFS solver
    # -----------------------------------------------------------------------

    def _solve(
        self,
        target_dur: Fraction,
    ) -> list[tuple[PairedKernel, int]] | None:
        """Find a segment list whose durations sum to target_dur.

        Returns a chain sorted so the last segment has the shortest duration
        (fragmentation ordering). Returns None if no solution found.
        """
        candidates: list[list[tuple[int, int]]] = []
        budget: list[int] = [_MAX_NODES]
        self._dfs(
            remaining=target_dur,
            path=[],
            results=candidates,
            budget=budget,
        )

        # Shuffle for variety across calls.
        self._rng.shuffle(candidates)

        # Pick first candidate with a novel family combination.
        for raw in candidates:
            key: tuple[tuple[str, int], ...] = tuple(
                (self._pool[idx].source.split("_")[0], reps)
                for idx, reps in raw
            )
            if key not in self._used:
                self._used.add(key)
                return self._build_and_sort(raw)

        # Exhaustion: clear used tracking and retry.
        self._used.clear()
        for raw in candidates:
            key = tuple(
                (self._pool[idx].source.split("_")[0], reps)
                for idx, reps in raw
            )
            if key not in self._used:
                self._used.add(key)
                return self._build_and_sort(raw)

        return None

    def _dfs(
        self,
        remaining: Fraction,
        path: list[tuple[int, int]],
        results: list[list[tuple[int, int]]],
        budget: list[int],
    ) -> None:
        """DFS over (pool_index, reps) pairs to find sequences summing to remaining."""
        budget[0] -= 1
        if budget[0] <= 0:
            return
        if len(results) >= _MAX_CANDIDATES:
            return

        if remaining == Fraction(0):
            results.append(list(path))
            return

        if remaining < Fraction(0):
            return
        if len(path) >= _MAX_SEGMENTS:
            return

        last_idx: int = path[-1][0] if path else -1

        for idx, reps, dur in self._atoms:
            if dur > remaining:
                continue
            if idx == last_idx:
                continue  # No adjacent repeats of the same kernel.
            path.append((idx, reps))
            self._dfs(
                remaining=remaining - dur,
                path=path,
                results=results,
                budget=budget,
            )
            path.pop()
            if len(results) >= _MAX_CANDIDATES or budget[0] <= 0:
                return

    def _build_and_sort(
        self,
        raw: list[tuple[int, int]],
    ) -> list[tuple[PairedKernel, int]]:
        """Convert index-based segments to PairedKernel pairs, sorted for fragmentation.

        Sorts so the last segment has the shortest total_duration * reps.
        If sorting would create adjacent duplicates, keeps original order.
        """
        segments: list[tuple[PairedKernel, int]] = [
            (self._pool[idx], reps) for idx, reps in raw
        ]

        if len(segments) <= 1:
            return segments

        # Sort descending by duration; last segment ends up with shortest duration.
        sorted_segs: list[tuple[PairedKernel, int]] = sorted(
            segments,
            key=lambda s: s[0].total_duration * s[1],
            reverse=True,
        )

        # Verify sorted version has no adjacent duplicates.
        for i in range(len(sorted_segs) - 1):
            if sorted_segs[i][0] is sorted_segs[i + 1][0]:
                return segments  # Revert to original order.

        # Verify duration sum is unchanged (should always be true; defensive).
        orig_dur: Fraction = sum(pk.total_duration * r for pk, r in segments)
        sort_dur: Fraction = sum(pk.total_duration * r for pk, r in sorted_segs)
        assert orig_dur == sort_dur, (
            f"Sort changed total duration: {orig_dur} → {sort_dur}. "
            "This is a bug in _build_and_sort."
        )
        return sorted_segs
