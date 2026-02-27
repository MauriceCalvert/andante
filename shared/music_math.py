"""Musical arithmetic using exact fractions.

All durations are Fraction objects internally. Floats only at I/O boundaries.
All values must be valid musical note durations - no approximation.

Ported from imperfect/pipeline/music_math.py
"""
from fractions import Fraction


def parse_fraction(s: str) -> Fraction:
    """Parse fraction string like '1/4' or '1' to Fraction."""
    if "/" in s:
        num, denom = s.split("/")
        return Fraction(int(num), int(denom))
    return Fraction(int(s))


def parse_metre(metre: str) -> tuple[Fraction, Fraction]:
    """Parse '3/4' to (bar_length, beat_unit)."""
    num, denom = metre.split("/")
    beats_per_bar: int = int(num)
    beat_value: int = int(denom)
    beat_unit: Fraction = Fraction(1, beat_value)
    bar_length: Fraction = beat_unit * beats_per_bar
    return bar_length, beat_unit


# Valid note durations as fractions of a semibreve (whole note)
VALID_DURATIONS: frozenset[Fraction] = frozenset({
    Fraction(2, 1),     # breve
    Fraction(3, 2),     # dotted whole
    Fraction(1, 1),     # whole
    Fraction(3, 4),     # dotted half
    Fraction(1, 2),     # half
    Fraction(3, 8),     # dotted quarter
    Fraction(1, 4),     # quarter
    Fraction(3, 16),    # dotted eighth
    Fraction(1, 8),     # eighth
    Fraction(3, 32),    # dotted sixteenth
    Fraction(1, 16),    # sixteenth
    Fraction(1, 32),    # thirty-second
})

# Sorted largest first for greedy selection
VALID_DURATIONS_SORTED: tuple[Fraction, ...] = tuple(
    sorted(VALID_DURATIONS, reverse=True)
)
