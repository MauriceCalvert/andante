"""Episode kernel demo 2 — clean rewrite with EpisodeKernelSource class.

The class extracts kernels from a SubjectTriple and generates unique
sequential episodes in both ascending and descending directions.
Each call to generate() returns a different kernel combination until
all are exhausted.

Key insight: given the last kernel and step direction, total_iters
is fully determined by the requested distance.  For step=-1:
    total_iters = distance + last_deg + 1
For step=+1:
    total_iters = distance - last_deg + 1
This turns a combinatorial explosion into a bounded prefix search
with exact iteration count.

Usage:
    python -m scripts.episode_kernel_demo2 [--subject NAME] [-o OUTPUT_DIR]
"""
from __future__ import annotations

import argparse
import logging
import math
import random
from fractions import Fraction
from pathlib import Path

from motifs.fragen import Kernel, Note, extract_kernels, sequence_kernels
from motifs.head_generator import degrees_to_midi
from motifs.subject_loader import SubjectTriple, list_triples, load_triple
from shared.midi_writer import SimpleNote, write_midi_notes
from shared.music_math import parse_metre

logging.basicConfig(level=logging.WARNING)
_log: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT_DIR: str = "output"
_DEFAULT_TEMPO: int = 100
_DEFAULT_VELOCITY: int = 80
_KERNELS_PER_FAMILY: int = 3
_MAX_BAR_COUNT: int = 3
_MAX_NODES: int = 50000  # DFS node budget per prefix search
_MAX_CANDIDATES: int = 200
_MAX_KERNEL_DURATION: Fraction = Fraction(1, 2)
_MAX_JUNCTION_DEGREES: int = 5  # max diatonic interval at segment boundaries
_MAX_SEGMENTS: int = 5
_OCTAVE_STEPS: int = 7
_SEED: int = 42
_START_DEGREE: int = 7


# ---------------------------------------------------------------------------
# Closure constraint
# ---------------------------------------------------------------------------


def _closure_ok(segments: list[tuple[Kernel, int]]) -> bool:
    """Last 2 note durations must be >= the preceding 2."""
    durations: list[Fraction] = []
    for k, reps in segments:
        for _ in range(reps):
            durations.extend(k.durations)
    if len(durations) < 4:
        return True
    return (
        durations[-2] >= durations[-4]
        and durations[-1] >= durations[-3]
    )


def _junctions_ok(segments: list[tuple[Kernel, int]], step: int) -> bool:
    """All inter-iteration junctions within _MAX_JUNCTION_DEGREES."""
    for i, (k, reps) in enumerate(segments):
        has_successor: bool = i < len(segments) - 1 or reps > 1
        if has_successor:
            junction: int = step - k.degrees[-1]
            if abs(junction) > _MAX_JUNCTION_DEGREES:
                return False
    return True


# ---------------------------------------------------------------------------
# EpisodeKernelSource
# ---------------------------------------------------------------------------


class EpisodeKernelSource:
    """Generates unique episode sequences from subject material.

    Supports both ascending (step=+1) and descending (step=-1) direction.
    Tracks used family-level patterns so the same combination is never
    returned twice, unless all combinations are exhausted.
    """

    def __init__(self, triple: SubjectTriple):
        metre_str: str = f"{triple.metre[0]}/{triple.metre[1]}"
        self._bar_length: Fraction = parse_metre(metre=metre_str)[0]
        self._tonic_midi: int = triple.tonic_midi
        self._mode: str = triple.subject.mode
        all_kernels: list[Kernel] = extract_kernels(fugue=triple)
        self._pool: list[Kernel] = _build_pool(kernels=all_kernels)
        # Atoms: (pool_index, reps, duration) — sorted longest-first for pruning
        self._atoms: list[tuple[int, int, Fraction]] = sorted(
            [
                (idx, reps, k.total_duration * reps)
                for idx, k in enumerate(self._pool)
                for reps in (1, 2)
            ],
            key=lambda a: a[2],
            reverse=True,
        )
        self._used: set[tuple[tuple[str, int], ...]] = set()
        self._rng: random.Random = random.Random(_SEED)

    @property
    def pool(self) -> list[Kernel]:
        return list(self._pool)

    @property
    def bar_length(self) -> Fraction:
        return self._bar_length

    @property
    def tonic_midi(self) -> int:
        return self._tonic_midi

    @property
    def mode(self) -> str:
        return self._mode

    def generate(
        self,
        start_degree: int,
        finish_degree: int,
        bar_count: int,
    ) -> list[Note] | None:
        """Return notes for an episode from start to finish degree.

        Direction is inferred: start > finish => descending, start < finish => ascending.
        """
        assert start_degree != finish_degree, (
            f"start {start_degree} must differ from finish {finish_degree}"
        )
        assert bar_count >= 1, f"bar_count must be >= 1, got {bar_count}"
        distance: int = abs(start_degree - finish_degree)
        step: int = -1 if start_degree > finish_degree else 1
        target_dur: Fraction = self._bar_length * bar_count
        segments: list[tuple[Kernel, int]] | None = self._solve(
            target_dur=target_dur,
            distance=distance,
            step=step,
        )
        if segments is None:
            return None
        return sequence_kernels(
            segments=tuple(segments),
            start_degree=start_degree,
            step=step,
        )

    def _solve(
        self,
        target_dur: Fraction,
        distance: int,
        step: int,
    ) -> list[tuple[Kernel, int]] | None:
        """Find a unique segment list filling target_dur and landing at ±distance.

        For step=-1: total_iters = distance + last_deg + 1
        For step=+1: total_iters = distance - last_deg + 1
        """
        candidates: list[list[tuple[Kernel, int]]] = []
        for last_idx in range(len(self._pool)):
            last_k: Kernel = self._pool[last_idx]
            last_deg: int = last_k.degrees[-1]
            for last_reps in (1, 2):
                last_dur: Fraction = last_k.total_duration * last_reps
                if last_dur > target_dur:
                    continue
                # Compute total iterations from direction and last kernel
                if step == -1:
                    total_iters: int = distance + last_deg + 1
                else:
                    total_iters = distance - last_deg + 1
                if total_iters < last_reps or total_iters < 1:
                    continue
                prefix_iters: int = total_iters - last_reps
                prefix_dur: Fraction = target_dur - last_dur
                suffix: list[tuple[Kernel, int]] = [(last_k, last_reps)]
                if prefix_iters == 0 and prefix_dur == Fraction(0):
                    candidates.append(suffix)
                    if len(candidates) >= _MAX_CANDIDATES:
                        break
                    continue
                if prefix_iters <= 0 or prefix_dur <= Fraction(0):
                    continue
                prefixes: list[list[tuple[int, int]]] = []
                self._find_prefixes(
                    remaining_dur=prefix_dur,
                    remaining_iters=prefix_iters,
                    forbidden_last=last_idx,
                    path=[],
                    results=prefixes,
                    budget=[_MAX_NODES],
                )
                for p in prefixes:
                    segments: list[tuple[Kernel, int]] = [
                        (self._pool[idx], reps) for idx, reps in p
                    ] + suffix
                    candidates.append(segments)
                    if len(candidates) >= _MAX_CANDIDATES:
                        break
                if len(candidates) >= _MAX_CANDIDATES:
                    break
            if len(candidates) >= _MAX_CANDIDATES:
                break
        self._rng.shuffle(candidates)
        # Pick first with novel family key, valid closure, and smooth junctions
        for c in candidates:
            if not _closure_ok(segments=c):
                continue
            if not _junctions_ok(segments=c, step=step):
                continue
            key: tuple[tuple[str, int], ...] = tuple(
                (k.source.removesuffix("_inv"), r) for k, r in c
            )
            if key not in self._used:
                self._used.add(key)
                return c
        # Exhaustion: reset used set and retry with fresh tracking
        self._used.clear()
        for c in candidates:
            if not _closure_ok(segments=c):
                continue
            if not _junctions_ok(segments=c, step=step):
                continue
            key = tuple(
                (k.source.removesuffix("_inv"), r) for k, r in c
            )
            if key not in self._used:
                self._used.add(key)
                return c
        return None

    def _find_prefixes(
        self,
        remaining_dur: Fraction,
        remaining_iters: int,
        forbidden_last: int,
        path: list[tuple[int, int]],
        results: list[list[tuple[int, int]]],
        budget: list[int],
    ) -> None:
        """DFS for prefix segments summing to exact (dur, iters)."""
        budget[0] -= 1
        if budget[0] <= 0:
            return
        if remaining_dur == Fraction(0) and remaining_iters == 0:
            if not path or path[-1][0] != forbidden_last:
                results.append(list(path))
            return
        if remaining_iters <= 0 or remaining_dur <= Fraction(0):
            return
        if len(path) >= _MAX_SEGMENTS - 1:
            return
        if len(results) >= _MAX_CANDIDATES:
            return
        for idx, reps, dur in self._atoms:
            if dur > remaining_dur:
                continue
            if reps > remaining_iters:
                continue
            if path and path[-1][0] == idx:
                continue
            path.append((idx, reps))
            self._find_prefixes(
                remaining_dur=remaining_dur - dur,
                remaining_iters=remaining_iters - reps,
                forbidden_last=forbidden_last,
                path=path,
                results=results,
                budget=budget,
            )
            path.pop()
            if len(results) >= _MAX_CANDIDATES or budget[0] <= 0:
                return


# ---------------------------------------------------------------------------
# Pool builder (shared with demo1)
# ---------------------------------------------------------------------------


def _build_pool(kernels: list[Kernel]) -> list[Kernel]:
    """Keep up to _KERNELS_PER_FAMILY distinct kernels per source family."""
    families: dict[str, list[Kernel]] = {}
    for k in kernels:
        if k.total_duration > _MAX_KERNEL_DURATION:
            continue
        fam: str = k.source.removesuffix("_inv")
        families.setdefault(fam, []).append(k)
    pool: list[Kernel] = []
    for fam in sorted(families.keys()):
        candidates: list[Kernel] = families[fam]
        candidates.sort(key=lambda k: (len(k.degrees), k.total_duration))
        seen_lengths: set[int] = set()
        selected: list[Kernel] = []
        for c in candidates:
            n: int = len(c.degrees)
            if n not in seen_lengths:
                selected.append(c)
                seen_lengths.add(n)
            if len(selected) >= _KERNELS_PER_FAMILY:
                break
        if len(selected) < _KERNELS_PER_FAMILY:
            for c in candidates:
                if c not in selected:
                    selected.append(c)
                if len(selected) >= _KERNELS_PER_FAMILY:
                    break
        pool.extend(selected)
    return pool


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


_EXAMPLES_PER_DISTANCE: int = 2


def _run_subject(
    triple: SubjectTriple,
    subject_name: str,
    output_dir: Path,
) -> None:
    """Generate demo MIDI: examples for each distance level, both directions."""
    source: EpisodeKernelSource = EpisodeKernelSource(triple=triple)
    if len(source.pool) < 2:
        print(f"  Too few kernels for {subject_name}")
        return
    print(f"\n  Kernel pool ({len(source.pool)}):")
    for i, k in enumerate(source.pool):
        print(
            f"    {i:>2}. {k.name:<25} {k.source:<12} "
            f"{len(k.degrees)} notes  dur={k.total_duration}  last_deg={k.degrees[-1]}"
        )
    all_midi: list[SimpleNote] = []
    cursor: Fraction = Fraction(0)
    seq_num: int = 0
    for direction_label, step in (("descending", -1), ("ascending", 1)):
        for n_bars in range(1, _MAX_BAR_COUNT + 1):
            print(f"\n  --- {n_bars}-bar {direction_label} episodes ---")
            for distance in range(1, _OCTAVE_STEPS + 1):
                start: int = _START_DEGREE
                if step == -1:
                    finish: int = start - distance
                else:
                    finish = start + distance
                found: int = 0
                for _ in range(_EXAMPLES_PER_DISTANCE):
                    notes: list[Note] | None = source.generate(
                        start_degree=start,
                        finish_degree=finish,
                        bar_count=n_bars,
                    )
                    if notes is None:
                        break
                    actual: int = notes[-1].degree
                    assert actual == finish, (
                        f"Landing {actual} != expected {finish} "
                        f"({direction_label}, distance={distance})"
                    )
                    seq_num += 1
                    found += 1
                    for note in notes:
                        midi_pitch: int = degrees_to_midi(
                            degrees=(note.degree,),
                            tonic_midi=source.tonic_midi,
                            mode=source.mode,
                        )[0]
                        if midi_pitch < 0 or midi_pitch > 127:
                            continue
                        abs_offset: Fraction = cursor + note.offset
                        all_midi.append(SimpleNote(
                            pitch=midi_pitch,
                            offset=float(abs_offset),
                            duration=float(note.duration),
                            velocity=_DEFAULT_VELOCITY,
                            track=0,
                        ))
                    end: Fraction = cursor + notes[-1].offset + notes[-1].duration
                    bars_used: int = math.ceil(end / source.bar_length)
                    cursor = source.bar_length * (bars_used + 1)
                if found > 0:
                    print(f"    distance={distance}: {found}/{_EXAMPLES_PER_DISTANCE}")
                else:
                    print(f"    distance={distance}: --")
    if not all_midi:
        print(f"  No output for {subject_name}")
        return
    out_path: Path = output_dir / f"episode_kernels_{subject_name}.mid"
    success: bool = write_midi_notes(
        path=str(out_path),
        notes=all_midi,
        tempo=_DEFAULT_TEMPO,
        time_signature=triple.metre,
        tonic=triple.tonic,
        mode=triple.subject.mode,
    )
    if success:
        print(f"\n  -> {out_path}  ({len(all_midi)} notes, {seq_num} sequences)")


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Episode kernel demo 2: EpisodeKernelSource class",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default=None,
        help="Subject name (default: all)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=_DEFAULT_OUTPUT_DIR,
    )
    args: argparse.Namespace = parser.parse_args()
    output_dir: Path = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    subjects: list[str] = [args.subject] if args.subject else sorted(list_triples())
    assert len(subjects) > 0
    for name in subjects:
        print(f"\n{'='*60}")
        print(f"Subject: {name}")
        print(f"{'='*60}")
        triple: SubjectTriple = load_triple(name=name)
        _run_subject(triple=triple, subject_name=name, output_dir=output_dir)
    print(f"\nDone. {len(subjects)} subject(s) processed.")


if __name__ == "__main__":
    main()
