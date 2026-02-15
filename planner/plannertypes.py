"""Planner types: TensionCurve, TensionPoint."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TensionPoint:
    """Single point on tension curve."""
    position: float  # 0.0 to 1.0 (ratio through piece)
    level: float     # 0.0 to 1.0 (tension intensity)


@dataclass(frozen=True)
class TensionCurve:
    """Tension arc across entire piece."""
    points: tuple[TensionPoint, ...]
    climax_position: float
    climax_level: float
