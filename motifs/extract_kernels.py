"""extract_kernels — Sub-bar motivic kernel extraction from fugue subject material.

Extracts 2–4 note kernels from head, tail, countersubject, and answer,
adds diatonic inversions, and deduplicates by (degrees, durations).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from motifs.fragment_catalogue import extract_head, extract_tail
from motifs.subject_loader import SubjectTriple
from shared.constants import exact_fraction
from shared.music_math import parse_metre

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_KERNEL_MAX_NOTES: int = 4   # cap: longer fragments sound like subject quotations
_KERNEL_MIN_NOTES: int = 2   # minimum for a recognisable gesture

# ---------------------------------------------------------------------------
# Data type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Kernel:
    """Sub-bar motivic kernel for sequential episode generation."""
    name: str                        # e.g. "head[0:3]", "cs[2:5]_inv"
    degrees: tuple[int, ...]         # relative degrees (first = 0)
    durations: tuple[Fraction, ...]
    total_duration: Fraction
    source: str                      # "head", "tail", "cs", "answer"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_kernels(fugue: SubjectTriple) -> list[Kernel]:
    """Extract short motivic kernels (2-4 notes) from all subject material.

    Returns deduplicated kernels including inversions. Does NOT chain
    kernels -- the kernel IS the episode unit.
    """
    metre_str: str = f"{fugue.metre[0]}/{fugue.metre[1]}"
    bar_length: Fraction = parse_metre(metre=metre_str)[0]
    head = extract_head(fugue=fugue, bar_length=bar_length)
    tail = extract_tail(fugue=fugue, bar_length=bar_length)

    sources: list[tuple[str, tuple[int, ...], tuple[Fraction, ...]]] = [
        (
            "head",
            head.degrees,
            head.durations,
        ),
        (
            "tail",
            tail.degrees,
            tail.durations,
        ),
        (
            "cs",
            fugue.countersubject.degrees,
            tuple(
                exact_fraction(value=d, label="cs duration")
                for d in fugue.countersubject.durations
            ),
        ),
        (
            "answer",
            fugue.answer.degrees,
            tuple(
                exact_fraction(value=d, label="answer duration")
                for d in fugue.answer.durations
            ),
        ),
    ]

    raw: list[Kernel] = []
    for source, degrees, durations in sources:
        if len(degrees) == 0:
            continue
        raw.extend(_kernel_subsequences(
            degrees=degrees,
            durations=durations,
            source=source,
        ))

    inverted: list[Kernel] = [_invert_kernel(k=k) for k in raw]

    return _dedup_kernels(kernels=raw + inverted)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _kernel_subsequences(
    degrees: tuple[int, ...],
    durations: tuple[Fraction, ...],
    source: str,
) -> list[Kernel]:
    """Extract contiguous subsequences of 2, 3, and 4 notes as kernels."""
    n: int = len(degrees)
    kernels: list[Kernel] = []
    for start in range(n):
        for length in range(_KERNEL_MIN_NOTES, _KERNEL_MAX_NOTES + 1):
            end: int = start + length
            if end > n:
                break
            sub_deg: tuple[int, ...] = degrees[start:end]
            sub_dur: tuple[Fraction, ...] = durations[start:end]
            base: int = sub_deg[0]
            relative: tuple[int, ...] = tuple(d - base for d in sub_deg)
            total: Fraction = sum(sub_dur)
            tag: str = f"{source}[{start}:{end}]"
            kernels.append(Kernel(
                name=tag,
                degrees=relative,
                durations=sub_dur,
                total_duration=total,
                source=source,
            ))
    return kernels


def _invert_kernel(k: Kernel) -> Kernel:
    """Diatonic inversion of a kernel (negate all degrees)."""
    return Kernel(
        name=k.name + "_inv",
        degrees=tuple(-d for d in k.degrees),
        durations=k.durations,
        total_duration=k.total_duration,
        source=k.source + "_inv",
    )


def _dedup_kernels(kernels: list[Kernel]) -> list[Kernel]:
    """Remove kernels with identical (degrees, durations)."""
    seen: set[tuple[tuple[int, ...], tuple[Fraction, ...]]] = set()
    result: list[Kernel] = []
    for k in kernels:
        key = (k.degrees, k.durations)
        if key not in seen:
            seen.add(key)
            result.append(k)
    return result
