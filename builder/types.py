"""Domain types for Andante builder.

All types are frozen dataclasses for immutability.
Durations are Fraction. Pitches are MIDI integers.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Any


@dataclass(frozen=True)
class Note:
    """Single note with timing and pitch."""
    offset: Fraction
    pitch: int
    duration: Fraction
    voice: int
    lyric: str = ""


@dataclass(frozen=True)
class NoteFile:
    """Collection of notes for export."""
    soprano: tuple[Note, ...]
    bass: tuple[Note, ...]
    metre: str
    tempo: int


@dataclass(frozen=True)
class Anchor:
    """Schema arrival constraint at specific bar.beat position."""
    bar_beat: str
    soprano_midi: int
    bass_midi: int
    schema: str
    stage: int


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
    bass_degrees: tuple[int, ...]
    entry_soprano: int
    entry_bass: int
    exit_soprano: int
    exit_bass: int
    bars_min: int
    bars_max: int
    position: str
    cadential_state: str
    sequential: bool = False
    segments: tuple[int, ...] = (1,)
    direction: str | None = None


@dataclass(frozen=True)
class GenreConfig:
    """Genre definition from YAML."""
    name: str
    voices: int
    form: str
    metre: str
    rhythmic_unit: str
    sections: tuple[dict[str, Any], ...]
    imitation: str
    treatment_sequence: tuple[dict[str, Any], ...]
    rhythmic_vocabulary: dict[str, Any]
    subject_constraints: dict[str, Any]
    tessitura: dict[str, int]


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
    bar_allocation: dict[str, tuple[int, int]]
    schema_allocation: dict[str, dict[str, Any]]
    phrase_boundaries: tuple[dict[str, Any], ...]
    minimum_bars: int


@dataclass(frozen=True)
class SchemaChain:
    """Output of Layer 3: Ordered schema sequence with key areas."""
    schemas: tuple[str, ...]
    key_areas: tuple[str, ...]
    free_passages: frozenset[tuple[int, int]]


@dataclass(frozen=True)
class TextureSequence:
    """Output of Layer 6: Treatment assignments."""
    treatments: tuple[str, ...]
    voice_assignments: tuple[int | None, ...]


@dataclass(frozen=True)
class CounterpointViolation:
    """Record of a counterpoint rule violation."""
    rule: str
    bar_beat: str
    soprano_pitch: int
    bass_pitch: int
    message: str


@dataclass(frozen=True)
class TreatmentAssignment:
    """Voice role assignment for a bar range (Layer 5 output)."""
    start_bar: int
    end_bar: int
    treatment: str  # "subject", "answer", "episode", "cadential"
    subject_voice: int | None  # 0=soprano, 1=bass, None=both


@dataclass(frozen=True)
class RhythmPlan:
    """Output of Layer 6: which slots are active per voice."""
    soprano_active: frozenset[int]  # slot indices (0 to total_slots-1)
    bass_active: frozenset[int]
    soprano_durations: dict[int, Fraction]  # slot index -> duration
    bass_durations: dict[int, Fraction]
