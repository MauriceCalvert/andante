"""Planner types: Brief, Frame, Material, Motif, Section, Phrase, Structure, Plan."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class TonalSection:
    """Section of a piece in a single key area.

    Tonal sections drive structure in schema-first planning. They define
    where the piece spends time in each key area before cadences are placed.
    """
    start_bar: int      # 1-indexed inclusive
    end_bar: int        # 1-indexed inclusive
    key_area: str       # Roman numeral: I, V, vi, etc.
    relationship: str   # tonic, dominant, relative, subdominant


@dataclass(frozen=True)
class VoiceSpec:
    """Voice specification per voices.md."""
    id: str
    role: str  # schema_upper, schema_lower, imitative, harmony_fill
    follows: str | None = None      # For imitative: voice id to follow
    delay_bars: int | None = None   # For imitative: delay in bars
    interval: int | None = None     # For imitative: transposition interval


@dataclass(frozen=True)
class InstrumentSpec:
    """Instrument instance in a piece."""
    id: str
    type: str  # Reference to instrument definition in data/instruments/


@dataclass(frozen=True)
class TrackSpec:
    """MIDI track assignment."""
    voice_id: str
    channel: int
    program: int


@dataclass(frozen=True)
class Brief:
    """User input specifying compositional intent.

    Required fields define the commission. Optional fields override genre defaults.
    
    Per voices.md, the Brief now includes:
    - voices: voice definitions with roles
    - instruments: physical instruments used
    - scoring: voice-to-actuator assignments
    - tracks: MIDI channel assignments
    """
    affect: str
    genre: str
    forces: str
    bars: int
    # Voice/instrument architecture (voices.md)
    voices: tuple['VoiceSpec', ...] | None = None
    instruments: tuple['InstrumentSpec', ...] | None = None
    scoring: dict[str, str] | None = None  # voice_id -> "instrument.actuator"
    tracks: tuple['TrackSpec', ...] | None = None
    # Optional: override genre defaults
    key: str | None = None
    mode: str | None = None
    metre: str | None = None
    tempo: str | None = None
    # Optional: provide subject (otherwise derived from opening schema)
    subject: 'Motif | None' = None
    # Optional: override specific genre settings
    overrides: dict | None = None
    # Deprecated: kept for backward compatibility during migration
    virtuosic: bool = False
    motif_source: str | None = None


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
    """Musical subject with pitches (MIDI) or degrees and durations.

    Use pitches for subjects loaded from .note files (preserves contour).
    Use degrees for programmatically generated subjects.
    """
    durations: tuple[Fraction, ...]
    bars: int
    pitches: tuple[int, ...] | None = None  # MIDI pitch values
    degrees: tuple[int, ...] | None = None  # Scale degrees 1-7
    source_key: str | None = None  # Key of pitches (e.g., "G" for G major)


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
    harmony: tuple[str, ...] | None = None  # one Roman numeral per bar


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
class RhetoricalSection:
    """A section of the classical rhetorical structure."""
    name: str           # exordium, narratio, confutatio, confirmatio, peroratio
    start_bar: int      # 1-indexed bar where section starts
    end_bar: int        # 1-indexed bar where section ends
    function: str       # Description of rhetorical function
    proportion: float   # Proportion of total piece (0.0 to 1.0)


@dataclass(frozen=True)
class RhetoricalStructure:
    """Complete rhetorical disposition of the piece."""
    archetype: str                              # Name of the archetype
    sections: tuple[RhetoricalSection, ...]     # The five classical sections
    climax_position: float                      # Position of climax (0.0 to 1.0)
    climax_bar: int                             # 1-indexed bar of climax


@dataclass(frozen=True)
class HarmonicTarget:
    """Harmonic target for a section or phrase."""
    key_area: str       # Roman numeral (I, iv, V, etc.)
    cadence_type: str   # perfect, half, deceptive, etc.
    bar: int            # Target bar (1-indexed)


@dataclass(frozen=True)
class HarmonicPlan:
    """Harmonic architecture across the piece."""
    targets: tuple[HarmonicTarget, ...]
    modulations: tuple[tuple[int, str, str], ...]  # (bar, from_key, to_key)


@dataclass(frozen=True)
class Callback:
    """Motivic callback - reference to earlier material."""
    target_bar: int     # Bar where callback occurs (1-indexed)
    source_bar: int     # Bar being referenced
    transform: str      # exact, invert, retrograde, augment, diminish
    voice: int          # Voice number (0-indexed)
    material: str       # subject, counter_subject, derived_X


@dataclass(frozen=True)
class Surprise:
    """Rhetorical surprise device."""
    bar: int            # Bar where surprise occurs (1-indexed)
    beat: float         # Beat within bar
    type: str           # pause, deceptive_cadence, sudden_piano, etc.
    duration: float     # Duration of surprise effect in beats


@dataclass(frozen=True)
class CoherencePlan:
    """Long-range coherence plan."""
    callbacks: tuple[Callback, ...]
    climax_bar: int
    surprises: tuple[Surprise, ...]
    golden_ratio_bar: int   # Bar at golden ratio point
    proportion_score: float  # How well proportions match ideal


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
    rhetoric: RhetoricalStructure | None = None
    harmonic_plan: HarmonicPlan | None = None
    coherence: CoherencePlan | None = None


# =============================================================================
# Schema-First Planning Types (planner_design.md)
# =============================================================================


@dataclass(frozen=True)
class CadencePoint:
    """Arrival point in piece structure.

    Cadences drive structure in schema-first planning. They are placed before
    any melodic content, determining where phrases end and new sections begin.
    """
    bar: int            # 1-indexed bar number where cadence occurs
    type: str           # half, authentic, deceptive, phrygian
    target: str         # Harmonic target: I, V, vi, etc.
    in_key_area: str = "I"        # Key area where cadence occurs
    beat: Fraction | None = None  # Beat within bar; None = downbeat


@dataclass(frozen=True)
class SchemaSlot:
    """Atomic planning unit replacing Episode+Phrase.

    A SchemaSlot specifies a partimento schema tiled to fill a given number
    of bars, with texture, treatment, and dux voice. The schema's bass_degrees
    and soprano_degrees encode the harmonic content; no separate harmony field needed.
    """
    type: str           # Schema name: romanesca, prinner, fonte, etc.
    bars: int           # Actual bars (tiled from schema's base bars)
    texture: str        # imitative, melody_bass, free
    treatment: str      # statement, imitation, sequence, inversion, stretto
    dux_voice: str      # soprano, bass (voice that presents subject first)
    cadence: str | None  # Cadence type if this slot ends on a cadence point
    key_area: str = "I"  # Key area for this slot
    stretto_overlap_beats: Fraction | None = None  # Overlap for stretto treatment
    sequence_repetitions: int | None = None        # Repetitions for sequence treatment


@dataclass(frozen=True)
class SectionSchema:
    """Section defined by cadence points and schema chain.

    Replaces Section (which used Episode > Phrase hierarchy). A SectionSchema
    contains a flat sequence of SchemaSlots that land on the cadence points.
    """
    label: str                                # A, B, etc.
    key_area: str                             # I, V, vi, etc.
    cadence_plan: tuple[CadencePoint, ...]    # Cadences in this section
    schemas: tuple[SchemaSlot, ...]           # Schema chain filling the section


@dataclass(frozen=True)
class SubjectValidation:
    """Result of validating subject against opening schema.

    Used when user provides a subject to ensure it fits the schema-first model:
    - First degree must be consonant with schema's opening bass
    - Must be invertible (intervals stay consonant when flipped)
    - Must be answerable at the fifth (transposition stays in mode)
    """
    valid: bool
    invertible: bool
    answerable: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class SchemaStructure:
    """Schema-first structure replacing episode/phrase hierarchy.

    Used by the new schema-first planner. Contains SectionSchema objects
    instead of Section objects.
    """
    sections: tuple[SectionSchema, ...]


# =============================================================================
# Genre Template Types (brief_upgrade.md)
# =============================================================================


@dataclass(frozen=True)
class CadenceTemplate:
    """Cadence planning rules for a genre.

    Specifies how frequently cadences occur and what types are used at
    different structural positions.
    """
    density: str              # high (2-4 bars), medium (4-8), low (8+)
    first_cadence_bar: int    # Typical first cadence location
    first_cadence_type: str   # half, authentic
    section_end_type: str     # Cadence type at section boundaries
    final_type: str           # Final cadence type (always authentic for baroque)


@dataclass(frozen=True)
class GenreSection:
    """Section template in genre definition.

    Defines proportions and cadence types for formal sections.
    """
    label: str                # A, B, etc.
    key_area: str             # I, V, vi, etc.
    proportion: float         # Proportion of total piece (0.0 to 1.0)
    end_cadence: str          # half, authentic


@dataclass(frozen=True)
class SubjectConstraints:
    """Rules for subject validation and derivation.

    Used to validate user-provided subjects or constrain generated ones.
    """
    min_notes: int
    max_notes: int
    max_bars: int
    require_invertible: bool   # Must work in melodic inversion
    require_answerable: bool   # Must work transposed at fifth
    first_degree: tuple[int, ...]  # Allowed starting degrees
    last_degree: tuple[int, ...]   # Allowed ending degrees (avoid strong closure)


@dataclass(frozen=True)
class TreatmentSpec:
    """Treatment vocabulary for a genre.

    Defines which contrapuntal treatments are required, optional, and
    where they appear in the structure.
    """
    required: tuple[str, ...]   # Must appear: statement, imitation, etc.
    optional: tuple[str, ...]   # May appear: sequence, inversion, stretto
    opening: str                # First slot treatment (usually statement)
    answer: str                 # Second slot treatment (usually imitation)


@dataclass(frozen=True)
class GenreTemplate:
    """Complete schema-first genre specification.

    Loaded from data/genres/*.yaml. Encodes all style-specific knowledge:
    schema preferences, cadence rules, section structure, subject constraints,
    and treatment vocabulary.
    """
    name: str                                     # Human-readable name
    voices: int                                   # Voice count (2, 3, or 4)
    metre: str                                    # Default metre (e.g., "4/4")
    texture: str                                  # imitative, melody_bass, homophonic
    schema_preferences: dict[str, list[str]]      # Position → schema names
    cadence_template: CadenceTemplate
    sections: tuple[GenreSection, ...]
    subject_constraints: SubjectConstraints
    treatments: TreatmentSpec
