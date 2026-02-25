"""Exhaustive enumeration of valid subject heads (Kopfmotiv)."""

from motifs.subject_gen.constants import (
    MIN_HEAD_LEAP,
    PITCH_HI,
    PITCH_LO,
)

_INTERVALS: tuple[int, ...] = tuple(v for v in range(-5, 6) if v != 0)


def enumerate_heads(head_size: int) -> list[tuple[int, ...]]:
    """Return all valid heads of given length, sorted and unique."""
    n_ivs: int = head_size - 1
    results: set[tuple[int, ...]] = set()
    def _recurse(depth: int, pitch: int, ivs: list[int]) -> None:
        if depth == n_ivs:
            for j in range(n_ivs - 1):
                if abs(ivs[j]) < MIN_HEAD_LEAP:
                    continue
                if ivs[j] * ivs[j + 1] >= 0:
                    continue
                if abs(ivs[j + 1]) not in {1, 2}:
                    continue
                degrees: list[int] = [0]
                p: int = 0
                for iv in ivs:
                    p += iv
                    degrees.append(p)
                results.add(tuple(degrees))
                return
            return
        for iv in _INTERVALS:
            next_pitch: int = pitch + iv
            if PITCH_LO <= next_pitch <= PITCH_HI:
                ivs.append(iv)
                _recurse(depth + 1, next_pitch, ivs)
                ivs.pop()
    _recurse(0, 0, [])
    return sorted(results)
