"""Domain types for Andante builder.

All types are frozen dataclasses for immutability.
Durations are Fraction. Pitches are MIDI integers.
"""
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from shared.key import Key


# =============================================================================
# Voice/Instrument Architecture (voices.md)
# =============================================================================


class Role(Enum):
    """How a voice's pitches are determined."""
    SCHEMA_UPPER = "schema_upper"  # Reads upper_degree from anchor
    SCHEMA_LOWER = "schema_lower"  # Reads lower_degree from anchor
    IMITATIVE = "imitative"        # Transforms from followed voice
    HARMONY_FILL = "harmony_fill"  # Derived from vertical harmony


@dataclass(frozen=True)
class Range:
    """Pitch limits for an actuator (MIDI pitch values)."""
    low: int
    high: int


@dataclass(frozen=True)
class Actuator:
    """Mechanism that produces notes on an instrument."""
    id: str
    range: Range


@dataclass(frozen=True)
class InstrumentDef:
    """Instrument definition from library."""
    id: str
    actuators: tuple[Actuator, ...]


@dataclass(frozen=True)
class Voice:
    """Single monophonic melodic line with continuity."""
    id: str
    role: Role
    follows: str | None = None      # For imitative: voice id to follow
    delay_bars: int | None = None   # For imitative: delay in bars
    interval: int | None = None     # For imitative: transposition interval


@dataclass(frozen=True)
class Instrument:
    """Physical instrument instance in a piece."""
    id: str
    type: str  # Reference to instrument definition


@dataclass(frozen=True)
class ScoringAssignment:
    """Single voice-to-actuator assignment."""
    voice_id: str
    instrument_id: str
    actuator_id: str


@dataclass(frozen=True)
class TrackAssignment:
    """MIDI track assignment for a voice."""
    voice_id: str
    channel: int
    program: int


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
class NoteFile:
    """Collection of notes for export."""
    soprano: tuple[Note, ...]
    bass: tuple[Note, ...]
    metre: str
    tempo: int
    upbeat: Fraction = Fraction(0)  # Anacrusis duration in whole notes


@dataclass(frozen=True)
class Anchor:
    """Schema arrival constraint at specific bar.beat position.
    
    Fields renamed per voices.md:
    - upper_degree: degree for schema_upper role (was soprano_degree)
    - lower_degree: degree for schema_lower role (was bass_degree)
    """
    bar_beat: str
    upper_degree: int
    lower_degree: int
    local_key: "Key"
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
    typical_keys: tuple[str, ...] | None = None


@dataclass(frozen=True)
class FunctionMapConfig:
    """Maps passage functions to voice expansions (from genre YAML).
    
    Per vocabulary.md: function_map links passage function names
    (subject, answer, episode...) to voice expansion names
    (statement, imitation, schema...).
    """
    required: tuple[str, ...]   # Required expansion names
    optional: tuple[str, ...]   # Optional expansion names
    subject: str                # Expansion for 'subject' function
    answer: str                 # Expansion for 'answer' function
    episode: str                # Expansion for 'episode' function
    development: str            # Expansion for 'development' function
    cadential: str              # Expansion for 'cadential' function
    return_: str                # Expansion for 'return' function (trailing _ avoids keyword)
    coda: str                   # Expansion for 'coda' function


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
    function_map: FunctionMapConfig
    sections: tuple[dict[str, Any], ...]
    passage_sequence: tuple[dict[str, Any], ...]
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
class PassageAssignment:
    """Passage function assignment for a bar range (Layer 5 output).
    
    Per vocabulary.md: binds a bar range to a passage function
    (subject, answer, episode...) and indicates which voice leads.
    """
    start_bar: int
    end_bar: int
    function: str           # Passage function: "subject", "answer", "episode", etc.
    lead_voice: int | None  # 0=upper, 1=lower, None=equal


@dataclass(frozen=True)
class RhythmPlan:
    """Output of Layer 6: which slots are active per voice."""
    soprano_active: frozenset[int]  # slot indices (0 to total_slots-1)
    bass_active: frozenset[int]
    soprano_durations: dict[int, Fraction]  # slot index -> duration
    bass_durations: dict[int, Fraction]


@dataclass(frozen=True)
class VoiceExpansionConfig:
    """Voice expansion configuration from treatments.yaml.
    
    Per vocabulary.md: defines HOW a voice's notes are derived.
    Fields prefixed soprano_/bass_ for each voice.
    """
    name: str
    soprano_source: str          # subject, counter_subject, sustained, pedal, schema, accompaniment
    soprano_transform: str       # none, invert, retrograde, augment, diminish, head, tail
    soprano_transform_params: dict[str, int | str]
    soprano_derivation: str | None  # null, imitation
    soprano_derivation_params: dict[str, int | str]
    soprano_delay: Fraction
    soprano_direct: bool
    bass_source: str
    bass_transform: str
    bass_transform_params: dict[str, int | str]
    bass_derivation: str | None
    bass_derivation_params: dict[str, int | str]
    bass_delay: Fraction
    bass_direct: bool
    interdictions: tuple[str, ...]  # disabled features: ornaments, inner_voice_gen
