"""Musical arithmetic using exact fractions.

All durations are Fraction objects internally. Floats only at I/O boundaries.
All values must be valid musical note durations - no approximation.
"""
from fractions import Fraction

from shared.constants import (
    AUGMENTATION,
    DIMINUTION,
    VALID_DURATIONS,
    VALID_DURATIONS_SORTED,
)


# Convert tuple to frozenset for O(1) membership testing
_VALID_DURATIONS_SET: frozenset[Fraction] = frozenset(VALID_DURATIONS)


def is_valid_duration(duration: Fraction) -> bool:
    """Check if duration is a valid musical note value."""
    return duration in _VALID_DURATIONS_SET


def validate_duration(duration: Fraction) -> Fraction:
    """Validate duration is in VALID_DURATIONS, raise if not."""
    assert duration in _VALID_DURATIONS_SET, f"Invalid duration: {duration}. Valid: {sorted(_VALID_DURATIONS_SET)}"
    return duration


def bar_duration(time_num: int, time_den: int) -> Fraction:
    """Bar duration from time signature. E.g., 3/4 → Fraction(3, 4)."""
    assert time_num > 0, f"time_num must be positive, got {time_num}"
    assert time_den > 0, f"time_den must be positive, got {time_den}"
    return Fraction(time_num, time_den)


def beat_duration(time_den: int) -> Fraction:
    """Beat duration from denominator. E.g., 4 → Fraction(1, 4)."""
    assert time_den > 0, f"time_den must be positive, got {time_den}"
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
    """
    assert target > 0, f"target must be positive, got {target}"
    assert note_count > 0, f"note_count must be positive, got {note_count}"
    valid_styles: frozenset[str] = frozenset({'uniform', 'long_short', 'varied'})
    assert style in valid_styles, f"Unknown fill style: '{style}'. Valid: {sorted(valid_styles)}"
    if style == "uniform":
        return _fill_uniform(target, note_count)
    if style == "long_short":
        return _fill_long_short(target, note_count)
    return _fill_varied(target, note_count)


def _fill_uniform(target: Fraction, note_count: int) -> list[Fraction]:
    """Fill with equal durations, fallback to varied if needed."""
    # Try exact division
    candidate: Fraction = target / note_count
    if candidate in _VALID_DURATIONS_SET:
        return [candidate] * note_count
    # Try nearby counts
    delta: int
    count: int
    for delta in range(1, note_count):
        for count in [note_count - delta, note_count + delta]:
            if count <= 0:
                continue
            candidate = target / count
            if candidate in _VALID_DURATIONS_SET:
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
        assert found, f"Cannot fill remaining {remaining} with valid durations (target={target})"
    return result


def repeat_to_fill(
    target: Fraction,
    degrees: list[int],
    durations: list[Fraction],
) -> tuple[list[int], list[Fraction]]:
    """Repeat motif to exactly fill target duration."""
    assert target > 0, f"target must be positive, got {target}"
    assert len(degrees) == len(durations), (
        f"degrees ({len(degrees)}) and durations ({len(durations)}) must have same length"
    )
    assert durations, "Cannot repeat empty motif"
    for i, d in enumerate(durations):
        assert d in _VALID_DURATIONS_SET, f"Invalid duration at index {i}: {d}"
    motif_dur: Fraction = sum(durations, Fraction(0))
    assert motif_dur > 0, "Motif has zero duration"
    assert target % motif_dur == 0, f"Motif duration {motif_dur} doesn't divide target {target}"
    repeat_count: int = int(target // motif_dur)
    assert repeat_count > 0, f"repeat_count must be positive, got {repeat_count} (target={target}, motif_dur={motif_dur})"
    repeated_degrees: list[int] = degrees * repeat_count
    repeated_durations: list[Fraction] = list(durations) * repeat_count
    return repeated_degrees, repeated_durations


def build_offsets(start: Fraction, durations: list[Fraction]) -> list[Fraction]:
    """Build note onset offsets from start position."""
    assert start >= 0, f"start must be non-negative, got {start}"
    for i, d in enumerate(durations):
        assert d in _VALID_DURATIONS_SET, f"Invalid duration at index {i}: {d}"
    offsets: list[Fraction] = []
    current: Fraction = start
    dur: Fraction
    for dur in durations:
        offsets.append(current)
        current += dur
    return offsets


def augment_duration(duration: Fraction) -> Fraction:
    """Double a duration via lookup. Raises if no valid mapping."""
    assert duration in AUGMENTATION, (
        f"Cannot augment duration: {duration}. Valid: {sorted(AUGMENTATION.keys())}"
    )
    return AUGMENTATION[duration]


def diminish_duration(duration: Fraction) -> Fraction:
    """Halve a duration via lookup. Raises if no valid mapping."""
    assert duration in DIMINUTION, (
        f"Cannot diminish duration: {duration}. Valid: {sorted(DIMINUTION.keys())}"
    )
    return DIMINUTION[duration]


def slice_for_bar(
    degrees: tuple[int, ...],
    durations: tuple[Fraction, ...],
    bar_idx: int,
    bar_duration: Fraction,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Extract notes that fall within a specific bar.

    Args:
        degrees: All pitches in the source material
        durations: All durations in the source material
        bar_idx: 0-based bar index to extract
        bar_duration: Duration of one bar

    Returns:
        (degrees, durations) for notes in the specified bar
    """
    assert len(degrees) == len(durations), (
        f"degrees ({len(degrees)}) and durations ({len(durations)}) must have same length"
    )
    assert bar_idx >= 0, f"bar_idx must be non-negative, got {bar_idx}"
    assert bar_duration > 0, f"bar_duration must be positive, got {bar_duration}"

    # Calculate source material total duration
    source_duration: Fraction = sum(durations, Fraction(0))
    assert source_duration > 0, "Source material has zero duration"

    # Calculate bar range
    bar_start: Fraction = bar_idx * bar_duration
    bar_end: Fraction = bar_start + bar_duration

    # Find notes that fall within [bar_start, bar_end)
    # Wrap source material if bar extends beyond it
    result_degrees: list[int] = []
    result_durations: list[Fraction] = []

    # Build cumulative offsets
    offset: Fraction = Fraction(0)
    for i, dur in enumerate(durations):
        # Map source offset to bar-relative offset using modulo
        note_start: Fraction = offset % source_duration
        # Check if this note appears in the bar (accounting for wrapping)
        effective_start: Fraction = bar_start % source_duration
        effective_end: Fraction = bar_end % source_duration

        in_bar: bool
        if effective_end > effective_start:
            # Normal case: bar doesn't wrap around source
            in_bar = effective_start <= note_start < effective_end
        else:
            # Bar wraps around source boundary
            in_bar = note_start >= effective_start or note_start < effective_end

        if in_bar:
            result_degrees.append(degrees[i])
            result_durations.append(dur)

        offset += dur

    # If we got nothing (bar_idx beyond source), repeat the whole source
    if not result_degrees:
        return degrees, durations

    return tuple(result_degrees), tuple(result_durations)
