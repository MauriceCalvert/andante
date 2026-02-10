"""Planner types: Brief, MacroForm, TensionCurve, TensionPoint."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Brief:
    """User input specifying compositional intent."""
    affect: str
    genre: str
    forces: str
    bars: int
    key: str | None = None
    mode: str | None = None
    metre: str | None = None
    tempo: str | None = None
    overrides: dict | None = None


@dataclass(frozen=True)
class MacroSection:
    """High-level section in fantasia macro-form."""
    label: str
    character: str
    bars: int
    texture: str
    key_area: str
    energy_arc: str


@dataclass(frozen=True)
class MacroForm:
    """Large-scale sectional structure for extended pieces."""
    sections: tuple[MacroSection, ...]
    climax_section: str
    total_bars: int


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
