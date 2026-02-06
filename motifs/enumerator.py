"""Exhaustive enumeration of valid subject candidates.

Enumerates all (pitch_sequence, rhythm_pattern) pairs that:
- Sum to exactly 1 bar
- Have 4-8 notes
- Use valid durations
- Have reasonable melodic intervals (±3 max)
- Start on tonic triad (0, 2, or 4)
"""
from typing import List, Tuple, Iterator
from functools import lru_cache

from shared.constants import SCALE_DEGREES, TONIC_TRIAD_DEGREES

# Valid durations in whole notes (4/4 bar = 1.0)
VALID_DURATIONS = (0.0625, 0.125, 0.1875, 0.25, 0.375, 0.5)

# Target bar duration
BAR_DURATION = 1.0

# Note count range
MIN_NOTES = 5
MAX_NOTES = 7

# Pitch constraints
MAX_INTERVAL = 3  # Max interval between adjacent notes (includes leaps)


@lru_cache(maxsize=1)
def enumerate_rhythm_patterns() -> Tuple[Tuple[float, ...], ...]:
    """Enumerate all rhythm patterns summing to 1 bar with 4-8 notes."""
    patterns: List[Tuple[float, ...]] = []

    def recurse(current: List[float], remaining: float):
        n = len(current)

        # Too many notes
        if n >= MAX_NOTES:
            return

        # Check if complete
        if abs(remaining) < 0.001:
            if n >= MIN_NOTES:
                patterns.append(tuple(current))
            return

        # Try each duration
        for dur in VALID_DURATIONS:
            if dur <= remaining + 0.001:
                current.append(dur)
                recurse(current=current, remaining=remaining - dur)
                current.pop()

    recurse(current=[], remaining=BAR_DURATION)
    return tuple(patterns)


@lru_cache(maxsize=1)
def enumerate_pitch_sequences(length: int) -> Tuple[Tuple[int, ...], ...]:
    """Enumerate all pitch sequences of given length with constrained intervals."""
    sequences: List[Tuple[int, ...]] = []

    def recurse(current: List[int]):
        if len(current) == length:
            sequences.append(tuple(current))
            return

        last = current[-1]
        # Try intervals -3 to +3
        for interval in range(-MAX_INTERVAL, MAX_INTERVAL + 1):
            new_pitch = last + interval
            if 0 <= new_pitch < SCALE_DEGREES:
                current.append(new_pitch)
                recurse(current=current)
                current.pop()

    # Start on tonic triad
    for start in TONIC_TRIAD_DEGREES:
        recurse(current=[start])

    return tuple(sequences)


def enumerate_all_candidates() -> Iterator[Tuple[Tuple[int, ...], Tuple[float, ...]]]:
    """Yield all valid (pitch_sequence, rhythm_pattern) pairs."""
    rhythm_patterns = enumerate_rhythm_patterns()

    # Cache pitch sequences by length
    pitch_cache = {}

    for rhythm in rhythm_patterns:
        n = len(rhythm)
        if n not in pitch_cache:
            pitch_cache[n] = enumerate_pitch_sequences(length=n)

        for pitches in pitch_cache[n]:
            yield (pitches, rhythm)


def count_candidates() -> dict:
    """Count total candidates and breakdowns."""
    rhythm_patterns = enumerate_rhythm_patterns()

    counts = {
        "rhythm_patterns": len(rhythm_patterns),
        "by_length": {},
        "total_pitch_sequences": 0,
        "total_candidates": 0,
    }

    for rhythm in rhythm_patterns:
        n = len(rhythm)
        if n not in counts["by_length"]:
            pitch_seqs = enumerate_pitch_sequences(length=n)
            counts["by_length"][n] = {
                "rhythm_patterns": 0,
                "pitch_sequences": len(pitch_seqs),
            }
            counts["total_pitch_sequences"] += len(pitch_seqs)
        counts["by_length"][n]["rhythm_patterns"] += 1

    for n, data in counts["by_length"].items():
        data["candidates"] = data["rhythm_patterns"] * data["pitch_sequences"]
        counts["total_candidates"] += data["candidates"]

    return counts


if __name__ == "__main__":
    print("Enumerating valid candidates...")
    counts = count_candidates()

    print(f"\nRhythm patterns: {counts['rhythm_patterns']}")
    print(f"\nBy note count:")
    for n in sorted(counts["by_length"].keys()):
        data = counts["by_length"][n]
        print(f"  {n} notes: {data['rhythm_patterns']} rhythms × {data['pitch_sequences']} pitches = {data['candidates']:,}")

    print(f"\nTotal candidates: {counts['total_candidates']:,}")
