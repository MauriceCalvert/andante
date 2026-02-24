"""Subject generator data models."""
from dataclasses import dataclass

from motifs.stretto_constraints import OffsetResult

@dataclass(frozen=True)
class GeneratedSubject:
    """A fully scored subject ready for answer/CS generation."""
    scale_indices: tuple[int, ...]
    durations: tuple[float, ...]
    midi_pitches: tuple[int, ...]
    bars: int
    score: float
    seed: int
    mode: str
    head_name: str
    leap_size: int
    leap_direction: str
    tail_direction: str
    stretto_offsets: tuple[OffsetResult, ...] = ()
    affect: str | None = None
    figurae_score: float = 0.0
    satisfied_figurae: tuple[str, ...] = ()

@dataclass(frozen=True)
class _ScoredPitch:
    """A scored, validated, shape-classified pitch sequence."""
    score: float
    ivs: tuple[int, ...]
    degrees: tuple[int, ...]
    shape: str
