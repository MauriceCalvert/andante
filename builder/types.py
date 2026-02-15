"""Domain types for Andante builder.

All types are frozen dataclasses for immutability.
Durations are Fraction. Pitches are MIDI integers.
"""
from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shared.key import Key



# =============================================================================
# Core Builder Types
# =============================================================================


@dataclass(frozen=True)
class Note:
    """Single note with timing and pitch."""
    offset: Fraction
    pitch: int
    duration: Fraction
    voice: int
    lyric: str = ""


@dataclass(frozen=True)
class Composition:
    """Complete composed output, voice-indexed."""
    voices: dict[str, tuple[Note, ...]]
    metre: str
    tempo: int
    upbeat: Fraction = Fraction(0)
    phrase_offsets: tuple[Fraction, ...] = ()
    structural_offsets: dict[str, frozenset[Fraction]] = field(default_factory=dict)


@dataclass(frozen=True)
class Anchor:
    """Schema arrival constraint at specific bar.beat position.
    
    Degrees are 1-7 (scale degrees). Direction hints indicate approach:
    - up: ascending motion to reach this degree
    - down: descending motion to reach this degree  
    - same: unison (repeat)
    - None: first anchor, no previous context
    
    MIDI resolution is deferred to fill time (phrase_writer) when the
    previous pitch is known, avoiding premature octave decisions.
    """
    bar_beat: str
    upper_degree: int
    lower_degree: int
    local_key: "Key"
    schema: str
    stage: int
    upper_direction: str | None = None
    lower_direction: str | None = None
    section: str = ""


@dataclass(frozen=True)
class MotiveWeights:
    """Motive cost weights from affect."""
    step: float = 0.2
    skip: float = 0.4
    leap: float = 0.8
    large_leap: float = 1.5


@dataclass(frozen=True)
class GenreConfig:
    """Genre definition from YAML."""
    name: str
    voices: int
    form: str
    metre: str
    rhythmic_unit: str
    tempo: int
    bass_treatment: str  # 'contrapuntal' or 'patterned'
    bass_mode: str  # 'schema' or 'pattern'
    bass_pattern: str | None
    sections: tuple[dict[str, Any], ...]
    composition_model: str = "galant"  # "galant" or "imitative"
    tension: str | None = None  # Named tension curve, or None (no curve)
    upbeat: Fraction = Fraction(0)  # Anacrusis duration in whole notes


@dataclass(frozen=True)
class KeyConfig:
    """Key definition with computed pitch sets."""
    name: str
    pitch_class_set: frozenset[int]
    bridge_pitch_set: frozenset[int]


@dataclass(frozen=True)
class AffectConfig:
    """Affect definition from YAML."""
    name: str
    density: str
    articulation: str
    tempo_modifier: int
    tonal_path: dict[str, tuple[str, ...]]
    answer_interval: int
    anacrusis: bool
    motive_weights: MotiveWeights
    direction_limit: int
    density_minimum: float
    rhythm_states: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class FormConfig:
    """Form template from YAML."""
    name: str


@dataclass(frozen=True)
class SectionTonalPlan:
    """Tonal plan for a single section."""
    name: str
    key_area: str
    cadence_type: str


@dataclass(frozen=True)
class TonalPlan:
    """Output of Layer 2: tonal regions and cadence allocation."""
    sections: tuple[SectionTonalPlan, ...]
    home_key: str
    modality: str
    density: str


@dataclass(frozen=True)
class SchemaChain:
    """Output of Layer 3: Ordered schema sequence with key areas."""
    schemas: tuple[str, ...]
    key_areas: tuple[str, ...]
    free_passages: frozenset[tuple[int, int]]
    cadences: tuple[str | None, ...] = ()
    section_boundaries: tuple[int, ...] = ()

