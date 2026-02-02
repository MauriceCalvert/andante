"""Domain types for Andante builder.

All types are frozen dataclasses for immutability.
Durations are Fraction. Pitches are MIDI integers.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from shared.key import Key
from shared.voice_types import (  # noqa: E402 — canonical source (voices.md)
    Actuator,
    Instrument,
    InstrumentDef,
    Range,
    Role,
    ScoringAssignment,
    TrackAssignment,
    Voice,
)


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
class CollectedNote:
    """Note collected for dissonance analysis."""
    offset: Fraction
    duration: Fraction
    diatonic: int
    role: str


@dataclass(frozen=True)
class Composition:
    """Complete composed output, voice-indexed."""
    voices: dict[str, tuple[Note, ...]]
    metre: str
    tempo: int
    upbeat: Fraction = Fraction(0)


@dataclass(frozen=True)
class Anchor:
    """Schema arrival constraint at specific bar.beat position.
    
    Fields renamed per voices.md:
    - upper_degree: degree for schema_upper role (was soprano_degree)
    - lower_degree: degree for schema_lower role (was bass_degree)
    - upper_direction: voice motion to reach this anchor (up/down/same/None for first)
    - lower_direction: voice motion to reach this anchor (up/down/same/None for first)
    - upper_midi: absolute MIDI pitch for upper voice (set by place_anchors_in_tessitura)
    - lower_midi: absolute MIDI pitch for lower voice (set by place_anchors_in_tessitura)
    """
    bar_beat: str
    upper_degree: int
    lower_degree: int
    local_key: "Key"
    schema: str
    stage: int
    upper_direction: str | None = None  # up, down, same, or None for first anchor
    lower_direction: str | None = None  # up, down, same, or None for first anchor
    section: str = ""  # rhetorical section (exordium, narratio, etc.)
    upper_midi: int | None = None  # absolute MIDI, set by tessitura placement
    lower_midi: int | None = None  # absolute MIDI, set by tessitura placement


@dataclass(frozen=True)
class MotiveWeights:
    """Motive cost weights from affect."""
    step: float = 0.2
    skip: float = 0.4
    leap: float = 0.8
    large_leap: float = 1.5


@dataclass(frozen=True)
class Solution:
    """Solver output with pitch sequences and cost."""
    soprano_pitches: tuple[int, ...]
    bass_pitches: tuple[int, ...]
    soprano_durations: tuple[Fraction, ...]
    bass_durations: tuple[Fraction, ...]
    cost: float


@dataclass(frozen=True)
class RhythmState:
    """Rhythmic state machine state."""
    state: str  # RUN, HOLD, CADENCE, TRANSITION
    density: float  # 0.0 to 1.0


@dataclass(frozen=True)
class SchemaConfig:
    """Schema definition from YAML."""
    name: str
    soprano_degrees: tuple[int, ...]
    soprano_directions: tuple[str | None, ...]  # up/down/same/None per degree
    bass_degrees: tuple[int, ...]
    bass_directions: tuple[str | None, ...]  # up/down/same/None per degree
    entry_soprano: int  # derived from soprano_degrees[0]
    entry_bass: int  # derived from bass_degrees[0]
    exit_soprano: int  # derived from soprano_degrees[-1]
    exit_bass: int  # derived from bass_degrees[-1]
    bars_min: int
    bars_max: int
    position: str
    cadential_state: str
    sequential: bool = False
    segments: tuple[int, ...] = (1,)
    direction: str | None = None
    segment_direction: str | None = None  # up/down between segments for sequential
    typical_keys: tuple[str, ...] | None = None


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
class SchemaChain:
    """Output of Layer 3: Ordered schema sequence with key areas."""
    schemas: tuple[str, ...]
    key_areas: tuple[str, ...]
    free_passages: frozenset[tuple[int, int]]


@dataclass(frozen=True)
class CounterpointViolation:
    """Record of a counterpoint rule violation."""
    rule: str
    bar_beat: str
    soprano_pitch: int
    bass_pitch: int
    message: str


@dataclass(frozen=True)
class PassageAssignment:
    """Passage function assignment for a bar range (Layer 5 output)."""
    start_bar: int
    end_bar: int
    function: str           # Section function from genre YAML
    lead_voice: int | None  # 0=upper, 1=lower, None=equal
    accompany_texture: str | None = None  # pillar, walking, staggered, complementary


@dataclass(frozen=True)
class RhythmPlan:
    """Output of Layer 6: which slots are active per voice."""
    soprano_active: frozenset[int]  # slot indices (0 to total_slots-1)
    bass_active: frozenset[int]
    soprano_durations: dict[int, Fraction]  # slot index -> duration
    bass_durations: dict[int, Fraction]
