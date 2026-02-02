"""Shared constants for andante packages."""
from fractions import Fraction
from typing import Tuple

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

# Two-voice consonances: P4 excluded (dissonant when above bass voice)
# Used by voice_checks.py for candidate filtering in 2-voice counterpoint
CONSONANT_INTERVALS_ABOVE_BASS: frozenset[int] = frozenset({0, 3, 4, 7, 8, 9})

# Perfect intervals (in semitones, reduced to single octave)
# Unison (0), P5 (7), P8 (12->0) - forbidden in parallel/direct motion
PERFECT_INTERVALS: frozenset[int] = frozenset({0, 7})

# Step threshold for direct motion rule (semitones)
# Direct fifths/octaves are only problematic if soprano leaps (> M2)
DIRECT_MOTION_STEP_THRESHOLD: int = 2

FLAT_KEYS_MAJOR: frozenset[str] = frozenset({"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"})
FLAT_KEYS_MINOR: frozenset[str] = frozenset({"D", "G", "C", "F", "Bb", "Eb", "Ab"})

MAJOR_SCALE: Tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)

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

VALID_DURATIONS: tuple[Fraction, ...] = (
    Fraction(1, 1), Fraction(3, 4), Fraction(1, 2), Fraction(3, 8),
    Fraction(1, 4), Fraction(3, 16), Fraction(1, 8), Fraction(3, 32),
    Fraction(1, 16), Fraction(1, 32),
)
VALID_DURATIONS_SORTED: tuple[Fraction, ...] = tuple(sorted(VALID_DURATIONS, reverse=True))

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

# Dux voice options for schema slots (voice that presents subject first)
DUX_VOICES: tuple[str, ...] = (
    "soprano",
    "bass",
)

# =============================================================================
# Figuration System Constants (figuration.md)
# =============================================================================

# Figuration intervals for diminution table indexing
FIGURATION_INTERVALS: tuple[str, ...] = (
    "unison", "step_up", "step_down", "third_up", "third_down",
    "fourth_up", "fourth_down", "fifth_up", "fifth_down",
    "sixth_up", "sixth_down", "octave_up", "octave_down",
)

# Misbehaviour probability for controlled violations
MISBEHAVIOUR_PROBABILITY: float = 0.05

# Maximum sequence repetitions before fragmentation (Rule of Three)
MAX_SEQUENCE_REPETITIONS: int = 2

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

# Voice ranges (MIDI pitch): (low, high) - standard Baroque ranges
# Used by realisation.py for anchor placement and faults.py for tessitura checks
VOICE_RANGES: dict[int, tuple[int, int]] = {
    0: (58, 84),  # Soprano: Bb3 to C6
    1: (53, 74),  # Alto: F3 to D5
    2: (48, 69),  # Tenor: C3 to A4
    3: (36, 67),  # Bass: C2 to G4
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

# =============================================================================
# Melodic Interval Thresholds (semitones)
# =============================================================================

STEP_SEMITONES: int = 2                    # Major second - stepwise motion
SKIP_SEMITONES: int = 4                    # Major third - small skip
GROTESQUE_LEAP_SEMITONES: int = 19         # Octave + fifth - error threshold
DIRECT_MOTION_LEAP_SEMITONES: int = 4      # Only >M3 counts as leap for direct 5ths/8ves
UGLY_LEAP_SEMITONES: int = 10              # Minor 7th - maximum internal figure leap

# Maximum consecutive simultaneous attacks before parallel_rhythm fault
# 4 attacks = 3 parallel motions, which starts to sound mechanical
MAX_PARALLEL_RHYTHM_ATTACKS: int = 4

# Rhythmic contrast threshold: if soprano has <= this many notes, bass maintains density
# Prevents lockstep when both voices relax toward cadence
RHYTHMIC_CONTRAST_THRESHOLD: int = 4

# MIDI gate factor per L013: notes shortened to 95% of notated duration
GATE_FACTOR: Fraction = Fraction(19, 20)

# Duration threshold for articulation tagging (eighth note in 4/4)
STACCATO_DURATION_THRESHOLD: Fraction = Fraction(1, 8)

