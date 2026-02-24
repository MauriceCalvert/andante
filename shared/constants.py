"""Shared constants for andante packages.

Organised into alphabetical sections; constants alphabetical within each section.
"""
from fractions import Fraction


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

# Number of bars a terminal cadence occupies in subject plans
CADENCE_BARS: int = 2

# Cadence target degrees (soprano, bass) by cadence type
CADENCE_DEGREES: dict[str, tuple[int, int]] = {
    "authentic": (1, 1),
    "half": (2, 5),
    "deceptive": (1, 6),
    "phrygian": (5, 6),
    "open": (3, 1),
}

# Valid cadence types for tonal planning
TONAL_CADENCE_TYPES: frozenset[str] = frozenset({
    "authentic", "half", "deceptive", "open",
})

# Valid key areas for tonal planning
VALID_KEY_AREAS: frozenset[str] = frozenset({
    "I", "II", "III", "IV", "V", "VI",
    "ii", "iii", "iv", "v", "vi",
})

# Cadential states that indicate a phrase is cadential
CADENTIAL_POSITION: str = "cadential"

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

# Imperfect consonances (semitones): 3rds and 6ths
IMPERFECT_CONSONANCES: frozenset[int] = frozenset({3, 4, 8, 9})

# Invertible consonances: 3rds and 6ths only (Bach's practice)
# 5ths become 4ths when inverted (dissonant against bass), unisons reduce independence
INVERTIBLE_CONSONANCES: frozenset[int] = IMPERFECT_CONSONANCES

# Perfect intervals (semitones): unison (0), P5 (7) - forbidden in parallel motion
PERFECT_INTERVALS: frozenset[int] = frozenset({0, 7})

# Strong-beat dissonant intervals (semitones, reduced to single octave)
# Forbidden on downbeats without preparation: m2, M2, tritone, m7, M7
STRONG_BEAT_DISSONANT: frozenset[int] = frozenset({1, 2, 6, 10, 11})

# Augmented/diminished intervals (semitones mod 12) to reject melodically
# m2 (1), tritone (6), m7 (10), M7 (11)
UGLY_INTERVALS: frozenset[int] = frozenset({1, 6, 10, 11})


# =============================================================================
# Consonance & Dissonance (mod-7 degree space, for stretto evaluation)
# =============================================================================

# Consonant intervals in mod-7 degree space: unison (0), 3rd (2), 5th (4), 6th (5)
# Fourth (3) excluded: dissonant in two-voice counterpoint.
CONSONANT_MOD7: frozenset[int] = frozenset({0, 2, 4, 5})

# Fourth in mod-7 degree space — includes both perfect and augmented (tritone).
# Mod-7 cannot distinguish them.  Treated as: fatal on strong beats (via
# exclusion from CONSONANT_MOD7), passing cost on weak beats.
FOURTH_MOD7: int = 3
SECOND_MOD7: int = 1
SEVENTH_MOD7: int = 6

# Normalisation ceiling for stretto offset count scoring
STRETTO_MIN_QUALITY: float = 0.6
STRETTO_OFFSET_COUNT_CEILING: int = 6


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

# Maximum consecutive simultaneous attacks before parallel_rhythm fault
MAX_PARALLEL_RHYTHM_ATTACKS: int = 5

# Strong beat offsets within a bar, keyed by metre string
# Beat 1 is always strong; 4/4 also has beat 3 (offset 1/2)
STRONG_BEAT_OFFSETS: dict[str, tuple[Fraction, ...]] = {
    "3/4": (Fraction(0),),
    "4/4": (Fraction(0), Fraction(1, 2)),
}

# Valid note durations as fractions of a whole note (descending)
# Maximum denominator when simplifying duration fractions (e.g. Fraction.limit_denominator)
DURATION_DENOMINATOR_LIMIT: int = 64

VALID_DURATIONS: tuple[Fraction, ...] = (
    Fraction(1, 1), Fraction(3, 4), Fraction(1, 2), Fraction(3, 8),
    Fraction(1, 4), Fraction(3, 16), Fraction(1, 8), Fraction(3, 32),
    Fraction(1, 16), Fraction(1, 32),
)
VALID_DURATIONS_SET: frozenset[Fraction] = frozenset(VALID_DURATIONS)
VALID_DURATIONS_SORTED: tuple[Fraction, ...] = tuple(sorted(VALID_DURATIONS, reverse=True))

# Bar length by metre string (whole-note fractions)
METRE_BAR_LENGTH: dict[str, Fraction] = {
    "3/4": Fraction(3, 4),
    "4/4": Fraction(1),
}

# Melodic interval thresholds (semitones)
MAX_MELODIC_INTERVAL: int = 12
# Sentinel durations for bass patterns: "bar" and "half" tokens in YAML
DURATION_SENTINEL_BAR: Fraction = Fraction(-1)
DURATION_SENTINEL_HALF: Fraction = Fraction(-2)

# Sentinel beat position for "half" token when metre is unknown at parse time
BEAT_SENTINEL_HALF: Fraction = Fraction(-3)


# Valid motif character types
VALID_MOTIF_CHARACTERS: frozenset[str] = frozenset({
    "plain", "expressive", "energetic", "ornate", "bold",
})


# Valid phrase positions for motif selection
VALID_PHRASE_POSITIONS: frozenset[str] = frozenset({
    "opening", "interior", "cadential",
})


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


# =============================================================================
# Fragment Analyser
# =============================================================================

# Maximum diatonic degree interval for clean sequential treatment
MAX_SEQUENTIAL_INTERVAL: int = 4

# Multiplier over median duration to classify a note as "long"
LONG_NOTE_MULTIPLIER: int = 2

# Ideal episode cell length range (quarter-note beats)
IDEAL_CELL_MAX_BEATS: int = 4
IDEAL_CELL_MIN_BEATS: int = 2


# =============================================================================
# Intervals
# =============================================================================

# Only >M3 counts as leap for direct 5ths/8ves (semitones)
DIRECT_MOTION_LEAP_SEMITONES: int = 4

# Octave + fifth: error threshold (semitones)
GROTESQUE_LEAP_SEMITONES: int = 19

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

# Major third: small skip threshold (semitones)
SKIP_SEMITONES: int = 4

# Major second: stepwise motion threshold (semitones)
STEP_SEMITONES: int = 2

# Tritone interval (semitones)
TRITONE_SEMITONES: int = 6


# =============================================================================
# Keys & Scales
# =============================================================================

FLAT_KEYS_MAJOR: frozenset[str] = frozenset({"Ab", "Bb", "Cb", "Db", "Eb", "F", "Gb"})
FLAT_KEYS_MINOR: frozenset[str] = frozenset({"Ab", "Bb", "C", "D", "Eb", "F", "G"})

MAJOR_SCALE: tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)
NATURAL_MINOR_SCALE: tuple[int, ...] = (0, 2, 3, 5, 7, 8, 10)
MINOR_SCALE: tuple[int, ...] = NATURAL_MINOR_SCALE  # alias
HARMONIC_MINOR_SCALE: tuple[int, ...] = (0, 2, 3, 5, 7, 8, 11)


# =============================================================================
# MIDI & Voices
# =============================================================================

# MIDI gate time fraction (L013: 95% to avoid legato rendering in players)
MIDI_GATE_TIME: float = 0.95

# MIDI pitch threshold for bass clef assignment
BASS_CLEF_THRESHOLD: int = 60

# Lowest acceptable soprano pitch (C4, MIDI) — practical floor for voice separation
MIN_SOPRANO_MIDI: int = 60

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

# Voice name to VOICE_RANGES index mapping
VOICE_NAME_TO_RANGE_IDX: dict[str, int] = {
    "soprano": 0,
    "upper": 0,
    "alto": 1,
    "tenor": 2,
    "bass": 3,
    "lower": 3,
}

# Phrase-path voice indices (2-voice texture: soprano=0, bass=1)
# PHRASE_VOICE_BASS retired — use TRACK_BASS (=3) instead


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

NOTE_NAMES_FLAT: tuple[str, ...] = (
    "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
)

NOTE_NAMES_SHARP: tuple[str, ...] = (
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
)

# Alias for NOTE_NAMES_SHARP (common usage)
NOTE_NAMES: tuple[str, ...] = NOTE_NAMES_SHARP


# =============================================================================
# Registral Bias
# =============================================================================

# Per-phrase soprano registral bias (semitones) by tension energy level.
# Maps tension_to_energy() output to upward semitone shift of upper_median.
ENERGY_TO_CHARACTER: dict[str, str] = {
    "low": "plain",
    "moderate": "expressive",
    "rising": "energetic",
    "high": "ornate",
    "peak": "bold",
}

# Character rank for floor comparison (higher = more energetic)
CHARACTER_RANK: dict[str, int] = {
    "plain": 0,
    "expressive": 1,
    "energetic": 2,
    "ornate": 3,
    "bold": 4,
}

ENERGY_TO_REGISTRAL_BIAS: dict[str, int] = {
    "low": 0,
    "moderate": 2,
    "rising": 4,
    "high": 6,
    "peak": 7,
}

# Maximum character rank permitted by the genre's rhythmic_unit.
# Prevents the tension curve from pushing density beyond the genre ceiling.
RHYTHMIC_UNIT_MAX_RANK: dict[Fraction, int] = {
    Fraction(1, 4): 0,   # plain (crotchets)
    Fraction(1, 8): 1,   # expressive (quavers)
    Fraction(1, 16): 4,  # bold (semiquavers) — effectively no cap
}

# Maximum per-phrase registral bias drop (semitones) during descent.
# Prevents the soprano from plunging after peak energy.
DESCENT_BIAS_STEP: int = 2


# =============================================================================
# Tessitura
# =============================================================================

# Voice ranges (MIDI pitch): (low, high) - standard Baroque ranges
VOICE_RANGES: dict[int, tuple[int, int]] = {
    0: (55, 84),  # Soprano: G3 to C6
    1: (50, 74),  # Alto: D3 to D5
    2: (45, 69),  # Tenor: A2 to A4
    3: (36, 62),  # Bass: C2 to D4
}


# =============================================================================
# Fraction safety
# =============================================================================

_MAX_MUSICAL_DENOM: int = 128  # largest denominator for any musical duration


def exact_fraction(value: float, label: str = "value") -> Fraction:
    """Convert a float to Fraction, asserting it is exactly representable."""
    f: Fraction = Fraction(value)
    assert f.denominator <= _MAX_MUSICAL_DENOM, (
        f"{label}: float {value} produces denominator {f.denominator} "
        f"(max {_MAX_MUSICAL_DENOM}). Source data contains a non-exact float."
    )
    return f
