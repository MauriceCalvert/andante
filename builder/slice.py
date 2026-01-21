"""Vertical slice extraction and interval analysis."""

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Slice:
    """Vertical sonority at a single offset."""
    offset: Fraction
    pitches: tuple[int | None, ...]  # Index = voice, None = no attack at this offset


@dataclass(frozen=True)
class SlicePair:
    """Two consecutive slices for parallel motion checking."""
    first: Slice
    second: Slice


def extract_slices(
    pitches: dict[tuple[Fraction, int], int],
    voice_count: int,
) -> list[Slice]:
    """
    Extract vertical slices from pitch assignments.

    Args:
        pitches: (offset, voice) -> MIDI pitch
        voice_count: Number of voices (2, 3, or 4)

    Returns:
        List of Slice ordered by offset ascending.
        Each slice contains pitches for all voices at that offset.
        Voice has None if no pitch assigned at that offset.

    Algorithm:
        1. Collect all unique offsets from pitches.keys()
        2. Sort offsets ascending
        3. For each offset, build tuple of pitches (None if voice missing)
    """
    assert voice_count in {2, 3, 4}, f"voice_count must be 2, 3, or 4, got {voice_count}"

    offsets: set[Fraction] = {key[0] for key in pitches.keys()}
    sorted_offsets: list[Fraction] = sorted(offsets)

    slices: list[Slice] = []
    for offset in sorted_offsets:
        voice_pitches: list[int | None] = []
        for voice in range(voice_count):
            key = (offset, voice)
            voice_pitches.append(pitches.get(key))
        slices.append(Slice(offset=offset, pitches=tuple(voice_pitches)))

    return slices


def extract_slice_pairs(
    slices: list[Slice],
    voice_a: int,
    voice_b: int,
) -> list[SlicePair]:
    """
    Extract consecutive slice pairs where both voices have attacks.

    Args:
        slices: Ordered slices from extract_slices()
        voice_a: First voice index (0 = soprano)
        voice_b: Second voice index (must be > voice_a)

    Returns:
        List of SlicePair where:
        - Both slices have non-None pitch for voice_a
        - Both slices have non-None pitch for voice_b
        - Pairs are consecutive in the filtered sequence

    Algorithm:
        1. Filter slices to those where both voices have pitches
        2. Zip filtered[:-1] with filtered[1:] to get consecutive pairs
    """
    assert voice_a < voice_b, f"voice_a ({voice_a}) must be < voice_b ({voice_b})"

    # Filter to slices where both voices have pitches
    filtered: list[Slice] = [
        s for s in slices
        if s.pitches[voice_a] is not None and s.pitches[voice_b] is not None
    ]

    # Build consecutive pairs
    pairs: list[SlicePair] = []
    for i in range(len(filtered) - 1):
        pairs.append(SlicePair(first=filtered[i], second=filtered[i + 1]))

    return pairs


def interval_class(pitch_a: int, pitch_b: int) -> int:
    """
    Compute interval class (0-11) between two MIDI pitches.

    Args:
        pitch_a: First MIDI pitch
        pitch_b: Second MIDI pitch

    Returns:
        Absolute interval mod 12, range 0-11.
        0 = unison/octave, 7 = fifth, etc.

    Formula:
        abs(pitch_a - pitch_b) % 12
    """
    return abs(pitch_a - pitch_b) % 12


def simple_interval(pitch_a: int, pitch_b: int) -> int:
    """
    Compute simple interval in semitones (0-12).

    Args:
        pitch_a: First MIDI pitch
        pitch_b: Second MIDI pitch

    Returns:
        Absolute interval reduced to single octave, range 0-12.
        Compound intervals reduce: 15 -> 3, 19 -> 7, etc.

    Formula:
        diff = abs(pitch_a - pitch_b)
        if diff == 0: return 0
        return ((diff - 1) % 12) + 1

    Examples:
        (60, 60) -> 0   (unison)
        (60, 64) -> 4   (major third)
        (60, 67) -> 7   (fifth)
        (60, 72) -> 12  (octave, not reduced to 0)
        (60, 76) -> 4   (compound major third -> 4)
        (60, 79) -> 7   (compound fifth -> 7)
    """
    diff: int = abs(pitch_a - pitch_b)
    if diff == 0:
        return 0
    return ((diff - 1) % 12) + 1


def melodic_interval(pitch_from: int, pitch_to: int) -> int:
    """
    Compute signed melodic interval in semitones.

    Args:
        pitch_from: Starting MIDI pitch
        pitch_to: Ending MIDI pitch

    Returns:
        Signed difference: positive = ascending, negative = descending.

    Formula:
        pitch_to - pitch_from
    """
    return pitch_to - pitch_from


def motion_type(
    voice_a_from: int,
    voice_a_to: int,
    voice_b_from: int,
    voice_b_to: int,
) -> str:
    """
    Classify motion between two voices across two slices.

    Args:
        voice_a_from: Voice A pitch at first slice
        voice_a_to: Voice A pitch at second slice
        voice_b_from: Voice B pitch at first slice
        voice_b_to: Voice B pitch at second slice

    Returns:
        One of: "contrary", "similar", "parallel", "oblique"

    Definitions:
        - contrary: voices move in opposite directions
        - similar: voices move same direction by different intervals
        - parallel: voices move same direction by same interval
        - oblique: one voice stationary, other moves

    Algorithm:
        delta_a = voice_a_to - voice_a_from
        delta_b = voice_b_to - voice_b_from

        if delta_a == 0 and delta_b == 0:
            return "oblique"  # Both stationary (edge case)
        if delta_a == 0 or delta_b == 0:
            return "oblique"
        if delta_a == delta_b:
            return "parallel"
        if (delta_a > 0) == (delta_b > 0):
            return "similar"
        return "contrary"
    """
    delta_a: int = voice_a_to - voice_a_from
    delta_b: int = voice_b_to - voice_b_from

    if delta_a == 0 and delta_b == 0:
        return "oblique"  # Both stationary (edge case)
    if delta_a == 0 or delta_b == 0:
        return "oblique"
    if delta_a == delta_b:
        return "parallel"
    if (delta_a > 0) == (delta_b > 0):
        return "similar"
    return "contrary"
