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

# Default diatonic pitches per voice role
DIATONIC_DEFAULTS: dict[str, int] = {
    'soprano': 32,  # G4 (octave 4, degree 5)
    'bass': 21,     # C3 (octave 3, degree 1)
    'alto': 28,     # C4 (octave 4, degree 1)
    'tenor': 25,    # A3 (octave 3, degree 6)
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

TONAL_ROOTS: dict[str, int] = {
    "I": 1, "i": 1, "V": 5, "v": 5, "IV": 4, "iv": 4,
    "vi": 6, "VI": 6, "ii": 2, "iii": 3, "III": 3, "VII": 7, "vii": 7,
}

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
