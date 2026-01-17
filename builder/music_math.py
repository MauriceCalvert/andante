"""Musical arithmetic using exact fractions.

All durations are Fraction objects internally. Floats only at I/O boundaries.
All values must be valid musical note durations - no approximation.

Copied from shared/music_math.py for builder package independence.
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


def validate_duration(duration: Fraction) -> Fraction:
    """Validate duration is in VALID_DURATIONS, raise if not."""
    if duration not in VALID_DURATIONS:
        raise MusicMathError(f"Invalid duration: {duration}")
    return duration


def bar_duration(time_num: int, time_den: int) -> Fraction:
    """Bar duration from time signature. E.g., 3/4 → Fraction(3, 4)."""
    return Fraction(time_num, time_den)


def beat_duration(time_den: int) -> Fraction:
    """Beat duration from denominator. E.g., 4 → Fraction(1, 4)."""
    return Fraction(1, time_den)


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
    candidate: Fraction = target / note_count
    if candidate in VALID_DURATIONS:
        return [candidate] * note_count
    # Try nearby counts
    delta: int
    count: int
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
    dotted_pairs: list[tuple[Fraction, Fraction]] = [
        (Fraction(3, 8), Fraction(1, 8)),
        (Fraction(3, 16), Fraction(1, 16)),
        (Fraction(3, 4), Fraction(1, 4)),
    ]
    long: Fraction
    short: Fraction
    for long, short in dotted_pairs:
        pair_dur: Fraction = long + short
        if target % pair_dur == 0:
            pair_count: int = int(target // pair_dur)
            result: list[Fraction] = []
            for _ in range(pair_count):
                result.extend([long, short])
            return result
    return _fill_uniform(target, note_count)


def _fill_varied(target: Fraction, note_count: int) -> list[Fraction]:
    """Fill with greedy selection of largest valid durations."""
    result: list[Fraction] = []
    remaining: Fraction = target
    while remaining > 0:
        found: bool = False
        dur: Fraction
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


def repeat_to_fill(
    target: Fraction,
    degrees: list[int],
    durations: list[Fraction],
) -> tuple[list[int], list[Fraction]]:
    """Repeat motif to exactly fill target duration.

    Raises:
        MusicMathError: If motif doesn't divide target evenly
    """
    if not durations:
        raise MusicMathError("Cannot repeat empty motif")
    motif_dur: Fraction = sum(durations, Fraction(0))
    if motif_dur == 0:
        raise MusicMathError("Motif has zero duration")
    if target % motif_dur != 0:
        raise MusicMathError(
            f"Motif duration {motif_dur} doesn't divide target {target}"
        )
    reps: int = int(target // motif_dur)
    return degrees * reps, list(durations) * reps


def build_offsets(start: Fraction, durations: list[Fraction]) -> list[Fraction]:
    """Build note onset offsets from start position."""
    offsets: list[Fraction] = []
    current: Fraction = start
    dur: Fraction
    for dur in durations:
        offsets.append(current)
        current += dur
    return offsets


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


def augment_duration(duration: Fraction) -> Fraction:
    """Double a duration via lookup. Raises if no valid mapping."""
    if duration not in AUGMENTATION:
        raise MusicMathError(f"Cannot augment duration: {duration}")
    return AUGMENTATION[duration]


def diminish_duration(duration: Fraction) -> Fraction:
    """Halve a duration via lookup. Raises if no valid mapping."""
    if duration not in DIMINUTION:
        raise MusicMathError(f"Cannot diminish duration: {duration}")
    return DIMINUTION[duration]
