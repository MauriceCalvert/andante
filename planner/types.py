"""Planner types: Brief, Frame, Material, Motif, Section, Phrase, Structure, Plan."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Brief:
    """User input specifying compositional intent."""
    affect: str
    genre: str
    forces: str
    bars: int
    virtuosic: bool = False


@dataclass(frozen=True)
class Frame:
    """Derived musical parameters."""
    key: str
    mode: str
    metre: str
    tempo: str
    voices: int
    upbeat: Fraction
    form: str


@dataclass(frozen=True)
class Motif:
    """Musical subject with degrees and durations."""
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    bars: int


@dataclass(frozen=True)
class DerivedMotif:
    """Pre-computed derived motif from subject or counter-subject."""
    name: str
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    source: str  # "subject" or "counter_subject"
    transforms: tuple[str, ...]  # e.g., ("head", "invert")


@dataclass(frozen=True)
class Material:
    """Thematic material for the piece."""
    subject: Motif
    counter_subject: Motif | None = None


@dataclass(frozen=True)
class Phrase:
    """Musical phrase within an episode."""
    index: int
    bars: int
    tonal_target: str
    cadence: str | None
    treatment: str
    surprise: str | None
    is_climax: bool = False
    energy: str | None = None


@dataclass(frozen=True)
class Episode:
    """Dramatic unit within a section containing phrases."""
    type: str
    bars: int
    texture: str
    phrases: tuple[Phrase, ...]
    is_transition: bool = False


@dataclass(frozen=True)
class Section:
    """Formal section containing episodes."""
    label: str
    tonal_path: tuple[str, ...]
    final_cadence: str
    episodes: tuple['Episode', ...]


@dataclass(frozen=True)
class Structure:
    """Complete formal structure."""
    sections: tuple[Section, ...]
    arc: str


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
class EpisodeSpec:
    """Episode specification from generator (before phrases added)."""
    type: str
    bars: int
    is_transition: bool = False


@dataclass(frozen=True)
class SectionPlan:
    """Breakdown of a macro-section into episodes."""
    label: str
    character: str
    texture: str
    key_area: str
    episodes: tuple[EpisodeSpec, ...]
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


@dataclass(frozen=True)
class Plan:
    """Complete plan output."""
    brief: Brief
    frame: Frame
    material: Material
    structure: Structure
    actual_bars: int
    macro_form: MacroForm | None = None
    tension_curve: TensionCurve | None = None
