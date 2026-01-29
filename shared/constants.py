"""Shared constants for andante packages."""
from fractions import Fraction
from typing import Tuple

# Augmentation lookup: duration -> doubled duration
AUGMENTATION: dict[Fraction, Fraction] = {
    Fraction(1, 32): Fraction(1, 16),
    Fraction(1, 16): Fraction(1, 8),
    Fraction(3, 32): Fraction(3, 16),
    Fraction(1, 8): Fraction(1, 4),
    Fraction(3, 16): Fraction(3, 8),
    Fraction(1, 4): Fraction(1, 2),
    Fraction(3, 8): Fraction(3, 4),
    Fraction(1, 2): Fraction(1, 1),
    Fraction(3, 4): Fraction(3, 2),
    Fraction(1, 1): Fraction(2, 1),
}

# Default minimum diatonic pitches per voice role
DIATONIC_DEFAULTS: dict[str, int] = {
    'soprano': 28,  # C4 (octave 4, degree 0) - allows keyboard RH from middle C
    'bass': 21,     # C3 (octave 3, degree 0)
    'alto': 28,     # C4 (octave 4, degree 0)
    'tenor': 25,    # A3 (octave 3, degree 5)
}

# Diminution lookup: duration -> halved duration
DIMINUTION: dict[Fraction, Fraction] = {
    Fraction(2, 1): Fraction(1, 1),
    Fraction(3, 2): Fraction(3, 4),
    Fraction(1, 1): Fraction(1, 2),
    Fraction(3, 4): Fraction(3, 8),
    Fraction(1, 2): Fraction(1, 4),
    Fraction(3, 8): Fraction(3, 16),
    Fraction(1, 4): Fraction(1, 8),
    Fraction(3, 16): Fraction(3, 32),
    Fraction(1, 8): Fraction(1, 16),
    Fraction(1, 16): Fraction(1, 32),
}

# Dissonant intervals (in semitones) to warn about when occurring simultaneously
# Minor 2nd (1), Major 7th (11) are harsh; Tritone (6) is contextually acceptable
DISSONANT_INTERVALS: frozenset[int] = frozenset({1, 11})

# Strong-beat dissonant intervals (in semitones, reduced to single octave)
# These intervals are forbidden on downbeats without preparation:
# m2 (1), M2 (2), tritone (6), m7 (10), M7 (11)
STRONG_BEAT_DISSONANT: frozenset[int] = frozenset({1, 2, 6, 10, 11})

# Consonant intervals (in semitones, reduced to single octave)
# Unison (0), m3 (3), M3 (4), P4 (5), P5 (7), m6 (8), M6 (9), P8 (12->0)
CONSONANT_INTERVALS: frozenset[int] = frozenset({0, 3, 4, 5, 7, 8, 9})

# Perfect intervals (in semitones, reduced to single octave)
# Unison (0), P5 (7), P8 (12->0) - forbidden in parallel/direct motion
PERFECT_INTERVALS: frozenset[int] = frozenset({0, 7})

# Step threshold for direct motion rule (semitones)
# Direct fifths/octaves are only problematic if soprano leaps (> M2)
DIRECT_MOTION_STEP_THRESHOLD: int = 2

DOMINANT_TARGETS: frozenset[str] = frozenset({"V", "v", "vii", "VII"})

FLAT_KEYS_MAJOR: frozenset[str] = frozenset({"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"})
FLAT_KEYS_MINOR: frozenset[str] = frozenset({"D", "G", "C", "F", "Bb", "Eb", "Ab"})

HARMONIC_MINOR_SCALE: Tuple[int, ...] = (0, 2, 3, 5, 7, 8, 11)

MAJOR_SCALE: Tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)

MELODIC_MINOR_SCALE: Tuple[int, ...] = (0, 2, 3, 5, 7, 9, 11)

MODULATION_TARGETS: dict[str, dict[str, tuple[int, str]]] = {
    "major": {
        "I": (0, "major"),
        "V": (7, "major"),
        "vi": (9, "minor"),
        "IV": (5, "major"),
        "ii": (2, "minor"),
        "iii": (4, "minor"),
    },
    "minor": {
        "i": (0, "minor"),
        "I": (0, "minor"),
        "III": (3, "major"),
        "iii": (3, "major"),
        "v": (7, "minor"),
        "V": (7, "major"),
        "iv": (5, "minor"),
        "IV": (5, "minor"),
        "ii": (2, "minor"),
        "VI": (8, "major"),
        "vi": (8, "major"),
    },
}

NATURAL_MINOR_SCALE: Tuple[int, ...] = (0, 2, 3, 5, 7, 8, 10)
MINOR_SCALE: Tuple[int, ...] = NATURAL_MINOR_SCALE  # alias

NOTE_NAME_MAP: dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}

NOTE_NAMES_FLAT: Tuple[str, ...] = (
    "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
)

NOTE_NAMES_SHARP: Tuple[str, ...] = (
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
)

# Alias for NOTE_NAMES_SHARP (common usage)
NOTE_NAMES: Tuple[str, ...] = NOTE_NAMES_SHARP

# Number of scale degrees in diatonic system
SCALE_DEGREES: int = 7

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

TONAL_ROOTS: dict[str, int] = {
    "I": 1, "i": 1, "V": 5, "v": 5, "IV": 4, "iv": 4,
    "vi": 6, "VI": 6, "ii": 2, "iii": 3, "III": 3, "VII": 7, "vii": 7,
}

# Key area semitone offsets from tonic (for tonal journey planning)
KEY_AREA_OFFSETS: dict[str, int] = {
    "I": 0, "i": 0,
    "II": 2, "ii": 2,
    "III": 3, "iii": 4,  # minor 3rd for minor mode, major 3rd for major
    "IV": 5, "iv": 5,
    "V": 7, "v": 7,
    "VI": 8, "vi": 9,  # minor 6th for minor mode, major 6th for major
    "VII": 10, "vii": 11,
}


def normalise_key_area(area: str) -> str:
    """Normalise key area notation to standard form.

    Accepts various notations and returns uppercase Roman numeral.
    Examples: 'tonic' -> 'I', 'dominant' -> 'V', 'v' -> 'V'
    """
    area_lower = area.lower().strip()
    aliases: dict[str, str] = {
        "tonic": "I",
        "dominant": "V",
        "subdominant": "IV",
        "relative": "VI",
        "relative_major": "III",
        "relative_minor": "VI",
        "supertonic": "II",
        "mediant": "III",
        "submediant": "VI",
        "leading": "VII",
    }
    if area_lower in aliases:
        return aliases[area_lower]
    return area.upper()

VALID_DURATION_OPS: frozenset[str] = frozenset({'reverse', 'augment', 'diminish'})

VALID_DURATIONS: tuple[Fraction, ...] = (
    Fraction(1, 1), Fraction(3, 4), Fraction(1, 2), Fraction(3, 8),
    Fraction(1, 4), Fraction(3, 16), Fraction(1, 8), Fraction(3, 32),
    Fraction(1, 16), Fraction(1, 32),
)
VALID_DURATIONS_SORTED: tuple[Fraction, ...] = tuple(sorted(VALID_DURATIONS, reverse=True))

VALID_PITCH_OPS: frozenset[str] = frozenset({'negate', 'reverse', 'transpose'})

# Voice role to MIDI track mapping
VOICE_TRACKS: dict[str, int] = {
    'soprano': 0,
    'alto': 1,
    'tenor': 2,
    'bass': 3,
}

# =============================================================================
# Schema-First Planning Constants (planner_design.md)
# =============================================================================

# Treatment vocabulary for schema-first planning (5 contrapuntal treatments only)
SCHEMA_TREATMENTS: tuple[str, ...] = (
    "statement",    # Literal subject presentation
    "imitation",    # Answer at octave/fifth
    "transposition", # Transposed repetition
    "inversion",    # Melodic mirror
    "stretto",      # Overlapped entries
)

# Texture types for schema slots
SCHEMA_TEXTURES: tuple[str, ...] = (
    "imitative",    # Both voices derive from schema (invention, fugue)
    "melody_bass",  # Soprano realizes, bass supports (minuet, dance)
    "free",         # Counterpoint fills (inner voices in 4-part)
)

# Cadence types for schema-first planning
CADENCE_TYPES: tuple[str, ...] = (
    "half",
    "authentic",
    "deceptive",
    "phrygian",
    "plagal",
)

# Cadence density levels (bars between cadences)
CADENCE_DENSITY: dict[str, tuple[int, int]] = {
    "high": (2, 4),     # Every 2-4 bars (invention)
    "medium": (4, 8),   # Every 4-8 bars (minuet)
    "low": (8, 16),     # Every 8+ bars (sarabande)
}

# Dux voice options for schema slots (voice that presents subject first)
DUX_VOICES: tuple[str, ...] = (
    "soprano",
    "bass",
)

# Tonal journey constants
MIN_TONAL_SECTION_BARS: int = 2  # Minimum bars for a tonal section
TONAL_PROPORTION_TOLERANCE: float = 0.01  # Allowed deviation from proportions summing to 1.0

# Scale degree to chord symbol mapping
DEGREE_TO_CHORD: dict[int, str] = {
    1: "I", 2: "ii", 3: "iii", 4: "IV", 5: "V", 6: "vi", 7: "viio"
}

# =============================================================================
# Figuration System Constants (figuration.md)
# =============================================================================

# Figuration intervals for diminution table indexing
FIGURATION_INTERVALS: tuple[str, ...] = (
    "unison", "step_up", "step_down", "third_up", "third_down",
    "fourth_up", "fourth_down", "fifth_up", "fifth_down",
    "sixth_up", "sixth_down", "octave_up", "octave_down",
)

# Phrase positions within standard 8-bar phrase
PHRASE_POSITIONS: tuple[str, ...] = ("opening", "continuation", "cadence")

# Figure character types
FIGURE_CHARACTERS: tuple[str, ...] = ("plain", "expressive", "energetic", "ornate", "bold")

# Harmonic tension levels
TENSION_LEVELS: tuple[str, ...] = ("low", "medium", "high")

# Density levels
DENSITY_LEVELS: tuple[str, ...] = ("low", "medium", "high")

# Misbehaviour probability for controlled violations
MISBEHAVIOUR_PROBABILITY: float = 0.05

# Maximum sequence repetitions before fragmentation (Rule of Three)
MAX_SEQUENCE_REPETITIONS: int = 2

# Phrase deformation types
PHRASE_DEFORMATIONS: tuple[str, ...] = ("early_cadence", "extended_continuation")

# Figure polarity options
FIGURE_POLARITIES: tuple[str, ...] = ("upper", "lower", "balanced")

# Figure arrival types
FIGURE_ARRIVALS: tuple[str, ...] = ("direct", "stepwise", "accented")

# Figure placement options
FIGURE_PLACEMENTS: tuple[str, ...] = ("start", "end", "span")

# =============================================================================
# Tessitura Constants (L003: soft hints only, no hard constraints)
# =============================================================================

# Default tessitura medians by voice index (MIDI pitch)
# Voice 0 = soprano, 1 = alto, 2 = tenor, 3 = bass
DEFAULT_TESSITURA_MEDIANS: dict[int, int] = {
    0: 70,  # Bb4 - soprano
    1: 60,  # C4 - alto
    2: 54,  # F#3 - tenor
    3: 48,  # C3 - bass
}

# DEPRECATED: Use scoring -> actuator -> range lookup per voices.md
# Fixed voice ranges (MIDI pitch): (low, high) - standard Baroque ranges
# Kept for backward compatibility only. New code should not reference this.
# See builder/faults.py DEFAULT_VOICE_RANGES for the replacement constant.
VOICE_RANGES: dict[int, tuple[int, int]] = {
    0: (60, 81),  # Soprano: C4 to A5
    1: (53, 72),  # Alto: F3 to C5
    2: (48, 67),  # Tenor: C3 to G4
    3: (40, 62),  # Bass: E2 to D4
}

# Soft tessitura span: semitones from median before cost increases
# Notes within this span incur no penalty; beyond incurs graduated cost
TESSITURA_COMFORTABLE_SPAN: int = 7

# Cost multiplier for notes beyond comfortable span (soft penalty)
# Applied per semitone beyond the span
TESSITURA_DEVIATION_COST: float = 2.0

# Cost for notes far beyond comfortable range (additional penalty)
# Applied when note is more than 2x the comfortable span from median
TESSITURA_EXTREME_COST: float = 100.0

# Maximum semitones from median before octave reset triggers in voice leading
# One octave allows natural melodic exploration; beyond risks runaway drift
TESSITURA_DRIFT_THRESHOLD: int = 12

# =============================================================================
# Melodic Interval Thresholds (semitones)
# =============================================================================

STEP_SEMITONES: int = 2                    # Major second - stepwise motion
SKIP_SEMITONES: int = 4                    # Major third - small skip
LEAP_SEMITONES: int = 7                    # Perfect fifth - moderate leap
LARGE_LEAP_SEMITONES: int = 12             # Octave - warning threshold
GROTESQUE_LEAP_SEMITONES: int = 19         # Octave + fifth - error threshold
DIRECT_MOTION_LEAP_SEMITONES: int = 4      # Only >M3 counts as leap for direct 5ths/8ves
UGLY_LEAP_SEMITONES: int = 10              # Minor 7th - maximum internal figure leap

# Maximum consecutive simultaneous attacks before parallel_rhythm fault
# 4 attacks = 3 parallel motions, which starts to sound mechanical
MAX_PARALLEL_RHYTHM_ATTACKS: int = 4

# Duration threshold for articulation tagging (eighth note in 4/4)
STACCATO_DURATION_THRESHOLD: Fraction = Fraction(1, 8)

