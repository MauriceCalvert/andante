"""Shared constants for andante packages.

Organised into alphabetical sections; constants alphabetical within each section.
"""
from fractions import Fraction
from typing import Tuple


# =============================================================================
# Bass
# =============================================================================

# Maximum acceptable leap in bass voice (octave, semitones)
MAX_BASS_LEAP: int = 12

# Lowest acceptable bass note (E2, MIDI pitch)
MIN_BASS_MIDI: int = 40

# Valid bass voice modes
VALID_BASS_MODES: frozenset[str] = frozenset({"pattern", "schema"})

# Valid bass treatment types
VALID_BASS_TREATMENTS: frozenset[str] = frozenset({"contrapuntal", "patterned"})

# Valid bass harmonic rhythm types
VALID_HARMONIC_RHYTHMS: frozenset[str] = frozenset({
    "none", "per_bar", "per_beat", "per_half",
})

# Valid bass texture types
VALID_TEXTURES: frozenset[str] = frozenset({
    "arpeggiated", "continuo", "ostinato", "pedal",
})


# =============================================================================
# Cadences
# =============================================================================

# Cadence target degrees (soprano, bass) by cadence type
CADENCE_DEGREES: dict[str, tuple[int, int]] = {
    "authentic": (1, 1),
    "half": (2, 5),
    "deceptive": (1, 6),
    "phrygian": (5, 6),
    "open": (3, 1),
}

# Cadence types for schema-first planning
CADENCE_TYPES: tuple[str, ...] = (
    "authentic",
    "deceptive",
    "half",
    "phrygian",
    "plagal",
)

# Valid cadence types for tonal planning
TONAL_CADENCE_TYPES: frozenset[str] = frozenset({
    "authentic", "half", "deceptive", "open",
})

# Valid key areas for tonal planning
VALID_KEY_AREAS: frozenset[str] = frozenset({
    "I", "II", "III", "IV", "V", "VI",
    "ii", "iii", "iv", "v", "vi",
})

# Interval names that trigger cadential writing mode
CADENTIAL_INTERVALS: frozenset[str] = frozenset({
    "step_down", "step_up", "third_down", "third_up", "unison",
})

# Cadential schema names - schemas that resolve a section
CADENTIAL_SCHEMA_NAMES: frozenset[str] = frozenset({
    "cadenza_composta",
    "cadenza_semplice",
    "comma",
    "half_cadence",
})

# Cadential states that indicate a phrase is cadential
CADENTIAL_POSITION: str = "cadential"

# Cadential target degree by approach interval
CADENTIAL_TARGET_DEGREE: dict[str, str] = {
    "step_down": "target_1",
    "step_up": "target_5",
    "third_down": "target_1",
    "third_up": "target_5",
    "unison": "target_1",
}

# Clausula cantizans pattern (scale degrees)
CLAUSULA_APPROACH_BASS: int = 7
CLAUSULA_APPROACH_SOPRANO: int = 4
CLAUSULA_ARRIVAL_BASS: int = 1
CLAUSULA_ARRIVAL_SOPRANO: int = 3


# =============================================================================
# Consonance & Dissonance
# =============================================================================

# Consonant intervals (semitones, reduced to single octave)
# Unison (0), m3 (3), M3 (4), P4 (5), P5 (7), m6 (8), M6 (9), P8 (12->0)
CONSONANT_INTERVALS: frozenset[int] = frozenset({0, 3, 4, 5, 7, 8, 9})

# Two-voice consonances: P4 excluded (dissonant when above bass voice)
CONSONANT_INTERVALS_ABOVE_BASS: frozenset[int] = frozenset({0, 3, 4, 7, 8, 9})

# Consonant intervals including octave (for invertibility checks)
CONSONANT_INTERVALS_WITH_OCTAVE: frozenset[int] = frozenset({0, 3, 4, 5, 7, 8, 9, 12})

# Consonant pitch offsets in diatonic steps, ordered by preference
# Used for pillar fallback when anchor pitch fails candidate filter
CONSONANT_PITCH_OFFSETS: tuple[int, ...] = (0, -7, 7, -2, 2, -4, 4, -5, 5, -3, 3)

# Dissonant intervals (semitones): m2 (1), M7 (11) are harsh
DISSONANT_INTERVALS: frozenset[int] = frozenset({1, 11})

# Imperfect consonances (semitones): 3rds and 6ths
IMPERFECT_CONSONANCES: frozenset[int] = frozenset({3, 4, 8, 9})

# Invertible consonances: 3rds and 6ths only (Bach's practice)
# 5ths become 4ths when inverted (dissonant against bass), unisons reduce independence
INVERTIBLE_CONSONANCES: frozenset[int] = IMPERFECT_CONSONANCES

# Perfect intervals (semitones): unison (0), P5 (7) - forbidden in parallel motion
PERFECT_INTERVALS: frozenset[int] = frozenset({0, 7})

# All consonances excluding P4: perfect + imperfect (for counterpoint)
ALL_CONSONANCES: frozenset[int] = PERFECT_INTERVALS | IMPERFECT_CONSONANCES

# Strong-beat dissonant intervals (semitones, reduced to single octave)
# Forbidden on downbeats without preparation: m2, M2, tritone, m7, M7
STRONG_BEAT_DISSONANT: frozenset[int] = frozenset({1, 2, 6, 10, 11})

# Augmented/diminished intervals (semitones mod 12) to reject melodically
# m2 (1), tritone (6), m7 (10), M7 (11)
UGLY_INTERVALS: frozenset[int] = frozenset({1, 6, 10, 11})


# =============================================================================
# Cross-Relations
# =============================================================================

# Pitch class pairs that form chromatic cross-relations between voices
CROSS_RELATION_PAIRS: frozenset[tuple[int, int]] = frozenset({
    (0, 1),   # C / C#
    (2, 3),   # D / D#
    (5, 6),   # F / F#
    (7, 8),   # G / G#
    (9, 10),  # A / A#
})


# =============================================================================
# Degrees
# =============================================================================

# Degrees consonant with bass degree 1 (tonic triad: 1, 3, 5)
CONSONANT_DEGREES_WITH_TONIC: frozenset[int] = frozenset({1, 3, 5})

# Valid scale degrees in diatonic system (both major and minor)
DIATONIC_DEGREES: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6, 7})

# Number of scale degrees in diatonic system
SCALE_DEGREES: int = 7

# Stable resolution target degrees (tonic triad across two octaves, 0-indexed)
STABLE_DEGREES: frozenset[int] = frozenset({0, 2, 4, 7, 9, 11, 14})

# Starting degrees for subjects (tonic triad, 0-indexed)
TONIC_TRIAD_DEGREES: tuple[int, ...] = (0, 2, 4)


# =============================================================================
# Duration & Rhythm
# =============================================================================

# Preferred rhythmic unit per density level (whole-note fractions)
DENSITY_RHYTHMIC_UNIT: dict[str, Fraction] = {
    "high": Fraction(1, 16),
    "low": Fraction(1, 4),
    "medium": Fraction(1, 8),
}

# MIDI gate factor per L013: notes shortened to 95% of notated duration
GATE_FACTOR: Fraction = Fraction(19, 20)

# Maximum consecutive simultaneous attacks before parallel_rhythm fault
MAX_PARALLEL_RHYTHM_ATTACKS: int = 4

# Maximum sequence repetitions before fragmentation (Rule of Three)
MAX_SEQUENCE_REPETITIONS: int = 2

# Rhythmic contrast threshold: if soprano has <= this many notes, bass maintains density
RHYTHMIC_CONTRAST_THRESHOLD: int = 4

# Duration threshold for articulation tagging (eighth note)
STACCATO_DURATION_THRESHOLD: Fraction = Fraction(1, 8)

# Valid musical duration denominators (powers of 2, with triplet variants)
VALID_DENOMINATORS: frozenset[int] = frozenset({
    1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64,
})

# Valid note durations as fractions of a whole note (descending)
VALID_DURATIONS: tuple[Fraction, ...] = (
    Fraction(1, 1), Fraction(3, 4), Fraction(1, 2), Fraction(3, 8),
    Fraction(1, 4), Fraction(3, 16), Fraction(1, 8), Fraction(3, 32),
    Fraction(1, 16), Fraction(1, 32),
)
VALID_DURATIONS_SORTED: tuple[Fraction, ...] = tuple(sorted(VALID_DURATIONS, reverse=True))


# Valid density trajectory types
VALID_DENSITY_TRAJECTORIES: frozenset[str] = frozenset({
    "constant", "rising", "falling", "arc",
})

# Valid development plan types
VALID_DEVELOPMENT_PLANS: frozenset[str] = frozenset({
    "intensifying", "relaxing", "contrasting",
})


# Valid motif character types
VALID_MOTIF_CHARACTERS: frozenset[str] = frozenset({
    "plain", "expressive", "energetic", "ornate", "bold",
})


# Valid phrase positions for motif selection
VALID_PHRASE_POSITIONS: frozenset[str] = frozenset({
    "opening", "interior", "cadential",
})

# Climax position within section (fraction of section length)
SECTION_CLIMAX_POSITION: float = 0.67


# =============================================================================
# Figuration
# =============================================================================

# Figuration interval display names: internal key -> human-readable name
# Single source of truth for interval naming (L017)
INTERVAL_DISPLAY_NAMES: dict[str, str] = {
    "fifth_down": "descending 5th",
    "fifth_up": "ascending 5th",
    "fourth_down": "descending 4th",
    "fourth_up": "ascending 4th",
    "octave_down": "descending octave",
    "octave_up": "ascending octave",
    "sixth_down": "descending 6th",
    "sixth_up": "ascending 6th",
    "step_down": "descending 2nd",
    "step_up": "ascending 2nd",
    "third_down": "descending 3rd",
    "third_up": "ascending 3rd",
    "unison": "unison",
}

# Figuration intervals for diminution table indexing (derived from display names)
FIGURATION_INTERVALS: tuple[str, ...] = tuple(INTERVAL_DISPLAY_NAMES.keys())

# Diatonic interval size (scale steps) for gap interval names
INTERVAL_DIATONIC_SIZE: dict[str, int] = {
    "fifth_down": 4, "fifth_up": 4,
    "fourth_down": 3, "fourth_up": 3,
    "octave_down": 7, "octave_up": 7,
    "sixth_down": 5, "sixth_up": 5,
    "step_down": 1, "step_up": 1,
    "third_down": 2, "third_up": 2,
    "unison": 0,
}

# Exit degree offset by interval name (signed diatonic steps)
INTERVAL_EXIT_DEGREES: dict[str, int] = {
    "fifth_down": -4,
    "fifth_up": 4,
    "fourth_down": -3,
    "fourth_up": 3,
    "octave_down": -7,
    "octave_up": 7,
    "sixth_down": -5,
    "sixth_up": 5,
    "step_down": -1,
    "step_up": 1,
    "third_down": -2,
    "third_up": 2,
    "unison": 0,
}

# Minimum notes for a figuration gap
MIN_FIGURATION_NOTES: int = 2

# Note count reduction from base, keyed by diatonic interval size.
# Removed: small intervals in baroque music are filled with running passages
# and neighbour-tone figurations that need MORE notes, not fewer.
# Kept as empty dict for backward compatibility.
SMALL_INTERVAL_NOTE_REDUCTION: dict[int, int] = {}


# =============================================================================
# Intervals
# =============================================================================

# Only >M3 counts as leap for direct 5ths/8ves (semitones)
DIRECT_MOTION_LEAP_SEMITONES: int = 4

# Step threshold for direct motion rule (semitones)
DIRECT_MOTION_STEP_THRESHOLD: int = 2

# Octave + fifth: error threshold (semitones)
GROTESQUE_LEAP_SEMITONES: int = 19

# Interval names by semitone count
INTERVAL_NAMES: dict[int, str] = {
    0: "unison",
    1: "minor_2nd",
    2: "major_2nd",
    3: "minor_3rd",
    4: "major_3rd",
    5: "perfect_4th",
    6: "tritone",
    7: "perfect_5th",
    8: "minor_6th",
    9: "major_6th",
    10: "minor_7th",
    11: "major_7th",
    12: "octave",
}

# Short interval names indexed by semitone (0-11)
INTERVAL_NAMES_SHORT: tuple[str, ...] = (
    "unison", "m2", "M2", "m3", "M3", "P4",
    "tritone", "P5", "m6", "M6", "m7", "M7",
)

# Key area transpositions in semitones from tonic
KEY_AREA_SEMITONES: dict[str, int] = {
    "I": 0,
    "II": 2,
    "III": 4,
    "IV": 5,
    "V": 7,
    "VI": 9,
    "VII": 11,
    "ii": 2,
    "iii": 4,
    "iv": 5,
    "v": 7,
    "vi": 9,
    "vii": 11,
}

# Maximum leap between consecutive gaps (octave, semitones)
MAX_LEAP_SEMITONES: int = 12

# Major third: small skip threshold (semitones)
SKIP_SEMITONES: int = 4

# Major second: stepwise motion threshold (semitones)
STEP_SEMITONES: int = 2

# Tritone interval (semitones)
TRITONE_SEMITONES: int = 6

# Minor 7th: maximum internal figure leap (semitones)
UGLY_LEAP_SEMITONES: int = 10


# =============================================================================
# Keys & Scales
# =============================================================================

FLAT_KEYS_MAJOR: frozenset[str] = frozenset({"Ab", "Bb", "Cb", "Db", "Eb", "F", "Gb"})
FLAT_KEYS_MINOR: frozenset[str] = frozenset({"Ab", "Bb", "C", "D", "Eb", "F", "G"})

MAJOR_SCALE: Tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)
NATURAL_MINOR_SCALE: Tuple[int, ...] = (0, 2, 3, 5, 7, 8, 10)
MINOR_SCALE: Tuple[int, ...] = NATURAL_MINOR_SCALE  # alias


# =============================================================================
# MIDI & Voices
# =============================================================================

# MIDI pitch threshold for bass clef assignment
BASS_CLEF_THRESHOLD: int = 60

# Voice index into VOICE_RANGES for bass
BASS_VOICE_IDX: int = 3

# Voice index into VOICE_RANGES for soprano
SOPRANO_VOICE_IDX: int = 0

# Tonic note name to MIDI pitch (octave 4)
TONIC_TO_MIDI: dict[str, int] = {
    "A": 69, "A#": 70, "Ab": 68,
    "B": 71, "Bb": 70,
    "C": 60, "C#": 61,
    "D": 62, "D#": 63, "Db": 61,
    "E": 64, "Eb": 63,
    "F": 65, "F#": 66,
    "G": 67, "G#": 68, "Gb": 66,
}

# MIDI track indices
TRACK_BASS: int = 3
TRACK_SOPRANO: int = 0


# =============================================================================
# Modulation
# =============================================================================

MODULATION_TARGETS: dict[str, dict[str, tuple[int, str]]] = {
    "major": {
        "I": (0, "major"),
        "IV": (5, "major"),
        "V": (7, "major"),
        "ii": (2, "minor"),
        "iii": (4, "minor"),
        "vi": (9, "minor"),
    },
    "minor": {
        "I": (0, "minor"),
        "III": (3, "major"),
        "IV": (5, "minor"),
        "V": (7, "major"),
        "VI": (8, "major"),
        "i": (0, "minor"),
        "ii": (2, "minor"),
        "iii": (3, "major"),
        "iv": (5, "minor"),
        "v": (7, "minor"),
        "vi": (8, "major"),
    },
}


# =============================================================================
# Notes
# =============================================================================

NOTE_NAME_MAP: dict[str, int] = {
    "A": 9, "A#": 10, "Ab": 8,
    "B": 11, "Bb": 10,
    "C": 0, "C#": 1,
    "D": 2, "D#": 3, "Db": 1,
    "E": 4, "Eb": 3,
    "F": 5, "F#": 6,
    "G": 7, "G#": 8, "Gb": 6,
}

NOTE_NAMES_FLAT: Tuple[str, ...] = (
    "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
)

NOTE_NAMES_SHARP: Tuple[str, ...] = (
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
)

# Alias for NOTE_NAMES_SHARP (common usage)
NOTE_NAMES: Tuple[str, ...] = NOTE_NAMES_SHARP


# =============================================================================
# Schema & Planning
# =============================================================================

# Dux voice options for schema slots (voice that presents subject first)
DUX_VOICES: tuple[str, ...] = (
    "bass",
    "soprano",
)

# Misbehaviour probability for controlled violations
MISBEHAVIOUR_PROBABILITY: float = 0.05

# Texture types for schema slots
SCHEMA_TEXTURES: tuple[str, ...] = (
    "free",         # Counterpoint fills (inner voices in 4-part)
    "imitative",    # Both voices derive from schema (invention, fugue)
    "melody_bass",  # Soprano realizes, bass supports (minuet, dance)
)

# Treatment vocabulary for schema-first planning (5 contrapuntal treatments only)
SCHEMA_TREATMENTS: tuple[str, ...] = (
    "imitation",     # Answer at octave/fifth
    "inversion",     # Melodic mirror
    "statement",     # Literal subject presentation
    "stretto",       # Overlapped entries
    "transposition", # Transposed repetition
)

# Valid direction types for schema degrees
VALID_DIRECTIONS: frozenset[str] = frozenset({"down", "same", "up"})


# =============================================================================
# Tessitura
# =============================================================================

# Headroom (semitones) to leave for figuration departure direction
# Ascending figuration needs room above; descending needs room below
ANCHOR_DEPARTURE_HEADROOM: int = 12

# Default tessitura medians by voice index (MIDI pitch)
# Voice 0 = soprano, 1 = alto, 2 = tenor, 3 = bass
DEFAULT_TESSITURA_MEDIANS: dict[int, int] = {
    0: 70,  # Bb4 - soprano
    1: 60,  # C4 - alto
    2: 54,  # F#3 - tenor
    3: 48,  # C3 - bass
}

# Soft tessitura span: semitones from median before cost increases
TESSITURA_COMFORTABLE_SPAN: int = 7

# Cost multiplier for notes beyond comfortable span (per semitone)
TESSITURA_DEVIATION_COST: float = 2.0

# Cost for notes far beyond comfortable range (>2x comfortable span from median)
TESSITURA_EXTREME_COST: float = 100.0

# Voice ranges (MIDI pitch): (low, high) - standard Baroque ranges
VOICE_RANGES: dict[int, tuple[int, int]] = {
    0: (55, 84),  # Soprano: G3 to C6
    1: (50, 74),  # Alto: D3 to D5
    2: (45, 69),  # Tenor: A2 to A4
    3: (36, 62),  # Bass: C2 to D4
}
