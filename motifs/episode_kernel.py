"""Episode kernel source — paired-kernel chain solver for sequential episodes.

Extracts two-voice PairedKernels from the fugue exposition and chains them
into sequences that fill a target bar count.  The chain is used by
EpisodeDialogue to drive the per-iteration texture.
"""
import logging
import random
from fractions import Fraction
from pathlib import Path

from motifs.extract_kernels import PairedKernel, extract_paired_kernels
from motifs.subject_loader import SubjectTriple
from shared.music_math import parse_metre

_log: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_CANDIDATES: int = 200
_MAX_NODES: int = 50000
_MAX_SEGMENTS: int = 8
_SEED: int = 42


# ---------------------------------------------------------------------------
# Pool builder
# ---------------------------------------------------------------------------


_QUAVER: Fraction = Fraction(1, 8)


def _build_pool(kernels: list[PairedKernel], bar_length: Fraction) -> list[PairedKernel]:
    """Build working pool: all kernels up to full-bar duration, both voices active."""
    cap: Fraction = bar_length
    pool: list[PairedKernel] = []
    rejected: dict[str, int] = {"cap": 0, "upper<2": 0, "lower<2": 0, "upper_unique<2": 0, "lower_unique<2": 0, "quaver_grid": 0}
    for pk in kernels:
        if pk.total_duration > cap:
            rejected["cap"] += 1
            continue
        if len(pk.upper_degrees) < 2:
            rejected["upper<2"] += 1
            continue
        if len(pk.lower_degrees) < 2:
            rejected["lower<2"] += 1
            continue
        if len(set(pk.upper_degrees)) < 2:
            rejected["upper_unique<2"] += 1
            continue
        if len(set(pk.lower_degrees)) < 2:
            rejected["lower_unique<2"] += 1
            continue
        # Total duration must be a quaver multiple to stay on the beat grid.
        if pk.total_duration % _QUAVER != 0:
            rejected["quaver_grid"] += 1
            continue
        pool.append(pk)
    print(f"[EPI-6] _build_pool: {len(kernels)} in, {len(pool)} out, rejected={rejected}")
    if pool:
        dur_counts: dict[str, int] = {}
        for pk in pool:
            d = str(pk.total_duration)
            dur_counts[d] = dur_counts.get(d, 0) + 1
        print(f"[EPI-6] pool durations: {dur_counts}")
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
        print(f"[EPI-6] pool={len(self._pool)} kernels (from {len(all_kernels)} raw)")
        self.dump_kernels_midi(
            path=Path("output/kernels.midi"),
            tonic_midi=triple.tonic_midi,
            mode=triple.subject.mode,
        )
        if len(self._pool) < 2:
            print(
                f"[EPI-6] WARNING: pool has {len(self._pool)} kernels (need >= 2); "
                f"all episodes will use fallback. Check subject/CS rhythm overlap."
            )

        # Atoms: (pool_index, reps, total_duration * reps), sorted duration desc.
        # Each atom covers at most 1 bar to prevent monotonous repetition.
        self._atoms: list[tuple[int, int, Fraction]] = sorted(
            [
                (idx, reps, pk.total_duration * reps)
                for idx, pk in enumerate(self._pool)
                for reps in range(
                    1,
                    int(self._bar_length / pk.total_duration) + 1,
                )
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

    def dump_kernels_midi(
        self,
        path: Path,
        tonic_midi: int = 60,
        mode: str = "major",
    ) -> None:
        """Write all pool kernels to a MIDI file for listening review."""
        from motifs.head_generator import degrees_to_midi
        from shared.midi_writer import SimpleNote, write_midi_notes
        notes: list[SimpleNote] = []
        offset: float = 0.0
        gap: float = 0.5  # half-bar silence between kernels
        for i, pk in enumerate(self._pool):
            # Upper voice (track 0)
            t: float = offset
            for deg, dur in zip(pk.upper_degrees, pk.upper_durations):
                midi: int = degrees_to_midi((deg + 7,), tonic_midi, mode)[0]
                notes.append(SimpleNote(
                    pitch=midi, offset=t, duration=float(dur),
                    velocity=80, track=0,
                ))
                t += float(dur)
            # Lower voice (track 1)
            t = offset
            for deg, dur in zip(pk.lower_degrees, pk.lower_durations):
                midi = degrees_to_midi((deg,), tonic_midi, mode)[0]
                notes.append(SimpleNote(
                    pitch=midi, offset=t, duration=float(dur),
                    velocity=70, track=1,
                ))
                t += float(dur)
            offset += float(pk.total_duration) + gap
        write_midi_notes(
            path=str(path), notes=notes, tempo=80,
            time_signature=(4, 4), tonic="C", mode=mode,
        )
        print(f"[EPI-6] dumped {len(self._pool)} kernels to {path}")
        # Write companion .note file for score reading.
        note_path: Path = path.with_suffix(".note")
        with open(note_path, "w", encoding="utf-8") as f:
            f.write("# Paired kernel pool dump\n")
            f.write(f"# tonic_midi={tonic_midi} mode={mode}\n")
            f.write(f"# {len(self._pool)} kernels\n\n")
            for i, pk in enumerate(self._pool):
                f.write(f"--- kernel {i}: {pk.name} (source={pk.source}, dur={pk.total_duration})\n")
                f.write(f"  upper_degrees:   {pk.upper_degrees}\n")
                f.write(f"  upper_durations: {pk.upper_durations}\n")
                u_midi: tuple[int, ...] = degrees_to_midi(
                    tuple(d + 7 for d in pk.upper_degrees), tonic_midi, mode,
                )
                f.write(f"  upper_midi:      {u_midi}\n")
                f.write(f"  lower_degrees:   {pk.lower_degrees}\n")
                f.write(f"  lower_durations: {pk.lower_durations}\n")
                l_midi: tuple[int, ...] = degrees_to_midi(
                    tuple(pk.lower_degrees), tonic_midi, mode,
                )
                f.write(f"  lower_midi:      {l_midi}\n")
                # Vertical intervals at shared attacks.
                u_onsets: list[float] = []
                cum: float = 0.0
                for d in pk.upper_durations:
                    u_onsets.append(cum)
                    cum += float(d)
                l_onsets: list[float] = []
                cum = 0.0
                for d in pk.lower_durations:
                    l_onsets.append(cum)
                    cum += float(d)
                shared: list[float] = sorted(set(u_onsets) & set(l_onsets))
                intervals: list[str] = []
                for t in shared:
                    ui: int = u_onsets.index(t)
                    li: int = l_onsets.index(t)
                    semis: int = u_midi[ui] - l_midi[li]
                    intervals.append(f"t={t}:{semis}st")
                f.write(f"  verticals:       {', '.join(intervals)}\n")
                f.write("\n")

    def generate(self, bar_count: int) -> list[PairedKernel] | None:
        """Return a flat list of bar_count PairedKernels, or None if unsolvable.

        Each entry in the returned list corresponds to one episode iteration.
        Kernels are ordered so shorter ones fall toward the end (fragmentation).
        """
        assert bar_count >= 1, f"bar_count must be >= 1, got {bar_count}"
        if len(self._pool) < 2:
            print(f"[EPI-6] generate: pool too small ({len(self._pool)})")
            return None

        target_dur: Fraction = self._bar_length * bar_count
        print(f"[EPI-6] generate: bar_count={bar_count}, target={target_dur}, atoms={len(self._atoms)}, pool={len(self._pool)}")
        segments: list[tuple[PairedKernel, int]] | None = self._solve(
            target_dur=target_dur,
        )
        if segments is None:
            atom_durs: list[str] = [
                f"{self._pool[idx].name}x{reps}={dur}"
                for idx, reps, dur in self._atoms[:6]
            ]
            print(
                f"[EPI-6] no chain for bar_count={bar_count} "
                f"(target={target_dur}, max_segments={_MAX_SEGMENTS}, "
                f"atoms[:6]=[{', '.join(atom_durs)}])"
            )
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
        total_dur: Fraction = sum(pk.total_duration for pk in result)
        expected_dur: Fraction = self._bar_length * bar_count
        assert total_dur == expected_dur, (
            f"Chain total duration {total_dur} != expected {expected_dur}. "
            f"Got {len(result)} kernels for bar_count={bar_count}."
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
        if not candidates:
            if budget[0] <= 0:
                print(
                    f"[EPI-6] _solve: budget exhausted ({_MAX_NODES} nodes) "
                    f"with 0 candidates for target={target_dur}"
                )
            else:
                print(
                    f"[EPI-6] _solve: no candidates for target={target_dur} "
                    f"(budget remaining={budget[0]}, pool={len(self._pool)}, "
                    f"max_segments={_MAX_SEGMENTS})"
                )
            return None

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
