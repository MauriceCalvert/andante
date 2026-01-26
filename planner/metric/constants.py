"""Constants for metric planning."""

# Key area transpositions in semitones from tonic
KEY_AREA_SEMITONES: dict[str, int] = {
    "I": 0,
    "II": 2,
    "ii": 2,
    "III": 4,
    "iii": 4,
    "IV": 5,
    "iv": 5,
    "V": 7,
    "v": 7,
    "VI": 9,
    "vi": 9,
    "VII": 11,
    "vii": 11,
}

# Maximum semitones from median before octave snap-back triggers
DRIFT_THRESHOLD: int = 16  # octave + major third

# Clausula cantizans pattern for sequential schemas (Monte, Fonte)
# Approach: suspended fourth over dominant (scale degrees)
CLAUSULA_APPROACH_SOPRANO: int = 4
CLAUSULA_APPROACH_BASS: int = 7
# Arrival: third over tonic (scale degrees)
CLAUSULA_ARRIVAL_SOPRANO: int = 3
CLAUSULA_ARRIVAL_BASS: int = 1
