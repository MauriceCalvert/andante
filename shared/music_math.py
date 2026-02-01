"""Musical arithmetic using exact fractions.

All durations are Fraction objects internally. Floats only at I/O boundaries.
All values must be valid musical note durations - no approximation.

Ported from imperfect/pipeline/music_math.py
"""
from fractions import Fraction


class MusicMathError(Exception):
    """Invalid duration or unfillable slot."""


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


def is_valid_duration(duration: Fraction) -> bool:
    """Check if duration is a valid musical note value."""
    return duration in VALID_DURATIONS



def fill_slot(
    target: Fraction,
    note_count: int,
    style: str = "uniform",
) -> list[Fraction]:
    """Generate valid durations that sum exactly to target.

    Args:
        target: Total duration to fill
        note_count: Desired number of notes
        style: "uniform", "long_short", or "varied"

    Returns:
        List of valid Fraction durations summing to target

    Raises:
        MusicMathError: If target cannot be filled
    """
    if note_count <= 0:
        raise MusicMathError(f"note_count must be positive, got {note_count}")
    if style == "uniform":
        return _fill_uniform(target, note_count)
    elif style == "long_short":
        return _fill_long_short(target, note_count)
    elif style == "varied":
        return _fill_varied(target, note_count)
    else:
        raise MusicMathError(f"Unknown fill style: {style}")


def _fill_uniform(target: Fraction, note_count: int) -> list[Fraction]:
    """Fill with equal durations, fallback to varied if needed."""
    # Try exact division
    candidate = target / note_count
    if candidate in VALID_DURATIONS:
        return [candidate] * note_count
    # Try nearby counts
    for delta in range(1, note_count):
        for count in [note_count - delta, note_count + delta]:
            if count <= 0:
                continue
            candidate = target / count
            if candidate in VALID_DURATIONS:
                return [candidate] * count
    # Fallback to greedy
    return _fill_varied(target, note_count)


def _fill_long_short(target: Fraction, note_count: int) -> list[Fraction]:
    """Fill with alternating dotted pattern."""
    dotted_pairs = [
        (Fraction(3, 8), Fraction(1, 8)),
        (Fraction(3, 16), Fraction(1, 16)),
        (Fraction(3, 4), Fraction(1, 4)),
    ]
    for long, short in dotted_pairs:
        pair_dur = long + short
        if target % pair_dur == 0:
            pair_count = int(target // pair_dur)
            result: list[Fraction] = []
            for _ in range(pair_count):
                result.extend([long, short])
            return result
    return _fill_uniform(target, note_count)


def _fill_varied(target: Fraction, note_count: int) -> list[Fraction]:
    """Fill with greedy selection of largest valid durations."""
    result: list[Fraction] = []
    remaining = target
    while remaining > 0:
        found = False
        for dur in VALID_DURATIONS_SORTED:
            if dur <= remaining:
                result.append(dur)
                remaining -= dur
                found = True
                break
        if not found:
            raise MusicMathError(
                f"Cannot fill remaining {remaining} with valid durations"
            )
    return result


