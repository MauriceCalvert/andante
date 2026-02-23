"""Subject generator data models."""
from dataclasses import dataclass
from typing import Tuple

from motifs.stretto_constraints import OffsetResult


@dataclass(frozen=True)
class GeneratedSubject:
    """A fully scored subject ready for answer/CS generation."""
    scale_indices: Tuple[int, ...]
    durations: Tuple[float, ...]
    midi_pitches: Tuple[int, ...]
    bars: int
    score: float
    seed: int
    mode: str
    head_name: str
    leap_size: int
    leap_direction: str
    tail_direction: str
    stretto_offsets: Tuple[OffsetResult, ...] = ()
    affect: str | None = None
    figurae_score: float = 0.0
    satisfied_figurae: Tuple[str, ...] = ()


@dataclass(frozen=True)
class _ScoredPitch:
    """A scored, validated, shape-classified pitch sequence."""
    score: float
    ivs: tuple[int, ...]
    degrees: tuple[int, ...]
    shape: str
