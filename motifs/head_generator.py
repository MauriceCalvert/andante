"""Head generator: enumerate valid 3-5 note heads.

A "head" is the memorable opening gesture of a subject.

Validity rules (based on music cognition research):
1. Must have a leap (interval >= 3)
2. Must have contrary stepwise motion after the leap (gap fill)
3. Must have at least 2 distinct durations

All valid heads are equal candidates - no scoring.
"""
from dataclasses import dataclass
from typing import Iterator

from shared.constants import MAJOR_SCALE, MINOR_SCALE, NOTE_NAMES

# Pitch constraints
MIN_LEAP = 3  # Minimum interval to count as a leap
MAX_INTERVAL = 7  # Octave
MIN_DEGREE = 0
MAX_DEGREE = 14  # Two octaves
START_DEGREES = (0, 2, 4)  # Tonic triad

# Rhythm cells indexed by metre - only those with 2+ distinct durations are valid
# Minimum 4 notes per head
# Head duration should be ~0.5-0.67 of total subject for each metre
# Key: (numerator, denominator) -> list of (durations, name)

RHYTHM_CELLS_BY_METRE: dict[tuple[int, int], tuple[tuple[tuple[float, ...], str], ...]] = {
    # 4/4 time: head 0.75-1.0 bar (total subject 2 bars = 2.0)
    (4, 4): (
        # 4-note cells (0.75 bar)
        ((0.25, 0.125, 0.125, 0.25), "long-short-short-long"),
        ((0.125, 0.25, 0.125, 0.25), "short-long-short-long"),
        ((0.375, 0.125, 0.125, 0.125), "dotted-run"),
        # 5-note cells (0.75 bar)
        ((0.25, 0.125, 0.0625, 0.0625, 0.25), "long-short-ornament"),
        ((0.125, 0.125, 0.125, 0.25, 0.125), "run-accent"),
        # 4-note cells (1.0 bar)
        ((0.25, 0.25, 0.25, 0.25), "quarters"),
        ((0.375, 0.125, 0.25, 0.25), "dotted-quarters"),
        ((0.25, 0.125, 0.125, 0.5), "short-to-long"),
        ((0.5, 0.125, 0.125, 0.25), "long-to-short"),
        # 5-note cells (1.0 bar)
        ((0.25, 0.25, 0.125, 0.125, 0.25), "quarters-run"),
        ((0.25, 0.125, 0.125, 0.25, 0.25), "run-quarters"),
        ((0.375, 0.125, 0.125, 0.125, 0.25), "dotted-run-quarter"),
        ((0.25, 0.125, 0.25, 0.125, 0.25), "alternating"),
        # 6-note cells (1.0 bar)
        ((0.25, 0.125, 0.125, 0.125, 0.125, 0.25), "long-run-long"),
        ((0.125, 0.125, 0.25, 0.125, 0.125, 0.25), "run-accent-run"),
    ),
    # 3/4 time: head ~0.375-0.5 bar (total subject 2 bars = 1.5)
    (3, 4): (
        # 3-note cells (0.375 bar)
        ((0.125, 0.125, 0.125), "triplet-run"),
        ((0.1875, 0.0625, 0.125), "dotted-short"),
        # 4-note cells (0.375 bar)
        ((0.125, 0.0625, 0.0625, 0.125), "long-ornament-long"),
        ((0.0625, 0.125, 0.0625, 0.125), "short-long-alt"),
        # 4-note cells (0.5 bar)
        ((0.125, 0.125, 0.125, 0.125), "even-eighths-3"),
        ((0.1875, 0.0625, 0.125, 0.125), "dotted-eighths-3"),
        # 5-note cells (0.5 bar)
        ((0.125, 0.0625, 0.0625, 0.125, 0.125), "ornament-eighths-3"),
        ((0.0625, 0.0625, 0.125, 0.125, 0.125), "sixteenths-eighths-3"),
    ),
    # 2/4 time: head ~0.375-0.5 bar (total subject 2 bars = 1.0)
    (2, 4): (
        # 3-note cells (0.375 bar)
        ((0.125, 0.125, 0.125), "triplet-2"),
        ((0.1875, 0.0625, 0.125), "dotted-short-2"),
        # 4-note cells (0.5 bar)
        ((0.125, 0.125, 0.125, 0.125), "even-eighths"),
        ((0.1875, 0.0625, 0.125, 0.125), "dotted-run-2"),
        ((0.125, 0.0625, 0.0625, 0.25), "run-long-2"),
        ((0.25, 0.0625, 0.0625, 0.125), "long-ornament-2"),
        # 5-note cells (0.5 bar)
        ((0.125, 0.0625, 0.0625, 0.125, 0.125), "run-eighths-2"),
        ((0.0625, 0.0625, 0.125, 0.125, 0.125), "sixteenths-eighths-2"),
    ),
    # 2/2 (cut time): head 0.75-1.0 bar (total subject 2 bars = 2.0, same as 4/4)
    (2, 2): (
        # Same patterns as 4/4 work well for cut time
        ((0.25, 0.125, 0.125, 0.25), "long-short-short-long"),
        ((0.125, 0.25, 0.125, 0.25), "short-long-short-long"),
        ((0.375, 0.125, 0.125, 0.125), "dotted-run"),
        ((0.25, 0.25, 0.25, 0.25), "quarters"),
        ((0.375, 0.125, 0.25, 0.25), "dotted-quarters"),
        ((0.25, 0.125, 0.125, 0.5), "short-to-long"),
        ((0.5, 0.125, 0.125, 0.25), "long-to-short"),
        ((0.25, 0.25, 0.125, 0.125, 0.25), "quarters-run"),
        ((0.25, 0.125, 0.125, 0.25, 0.25), "run-quarters"),
    ),
    # 6/8 time: head ~0.375-0.5 bar (total subject 2 bars = 1.5)
    (6, 8): (
        # Compound metre - group in dotted quarters
        # 3-note cells (0.375 bar = dotted quarter)
        ((0.125, 0.125, 0.125), "compound-triplet"),
        ((0.1875, 0.0625, 0.125), "compound-dotted"),
        # 4-note cells (0.5 bar)
        ((0.125, 0.125, 0.125, 0.125), "compound-run"),
        ((0.1875, 0.0625, 0.125, 0.125), "compound-dotted-run"),
        ((0.25, 0.0625, 0.0625, 0.125), "compound-long-ornament"),
        # 5-note cells (0.5-0.625 bar)
        ((0.1875, 0.0625, 0.125, 0.125, 0.125), "compound-dotted-eighths"),
        ((0.125, 0.125, 0.125, 0.1875, 0.0625), "compound-run-dotted"),
        ((0.125, 0.125, 0.125, 0.125, 0.125), "compound-even-eighths"),
    ),
}

# Default to 4/4 for backwards compatibility
RHYTHM_CELLS: tuple[tuple[tuple[float, ...], str], ...] = RHYTHM_CELLS_BY_METRE[(4, 4)]


def get_rhythm_cells(metre: tuple[int, int] = (4, 4)) -> tuple[tuple[tuple[float, ...], str], ...]:
    """Get rhythm cells for a specific metre."""
    if metre in RHYTHM_CELLS_BY_METRE:
        return RHYTHM_CELLS_BY_METRE[metre]
    # Fallback to 4/4 if metre not found
    return RHYTHM_CELLS_BY_METRE[(4, 4)]


@dataclass(frozen=True)
class Head:
    """A valid head candidate."""
    degrees: tuple[int, ...]
    rhythm: tuple[float, ...]
    rhythm_name: str
    leap_size: int
    leap_direction: str  # "up" or "down"


def _intervals(degrees: tuple[int, ...]) -> list[int]:
    """Compute intervals between adjacent degrees."""
    return [degrees[i + 1] - degrees[i] for i in range(len(degrees) - 1)]


def _largest_leap_position(intervals: list[int]) -> int:
    """Return 0-indexed position of largest leap, or -1 if no leap."""
    if not intervals:
        return -1
    max_size = 0
    max_pos = -1
    for i, iv in enumerate(intervals):
        if abs(iv) > max_size:
            max_size = abs(iv)
            max_pos = i
    return max_pos if max_size >= MIN_LEAP else -1


def _is_filled(intervals: list[int], leap_pos: int) -> bool:
    """Check if leap at position is followed by contrary stepwise motion."""
    if leap_pos < 0 or leap_pos >= len(intervals) - 1:
        return False
    leap_iv = intervals[leap_pos]
    next_iv = intervals[leap_pos + 1]
    # Must be contrary direction
    if leap_iv > 0 and next_iv >= 0:
        return False
    if leap_iv < 0 and next_iv <= 0:
        return False
    # Must be stepwise (1 or 2)
    return 1 <= abs(next_iv) <= 2


def _is_valid_pitch(degrees: tuple[int, ...]) -> tuple[bool, int, str]:
    """Check if pitch sequence has leap + fill. Returns (valid, leap_size, direction)."""
    intervals = _intervals(degrees)
    leap_pos = _largest_leap_position(intervals)

    if leap_pos < 0:
        return False, 0, ""

    if not _is_filled(intervals, leap_pos):
        return False, 0, ""

    leap_size = abs(intervals[leap_pos])
    direction = "up" if intervals[leap_pos] > 0 else "down"
    return True, leap_size, direction


def _has_rhythm_variety(rhythm: tuple[float, ...]) -> bool:
    """Check if rhythm has at least 2 distinct durations."""
    return len(set(rhythm)) >= 2


def enumerate_pitch_sequences(n_notes: int) -> Iterator[tuple[int, ...]]:
    """Enumerate all pitch sequences of given length."""
    def recurse(current: list[int]):
        if len(current) == n_notes:
            yield tuple(current)
            return

        last = current[-1]
        for interval in range(-MAX_INTERVAL, MAX_INTERVAL + 1):
            new_degree = last + interval
            if MIN_DEGREE <= new_degree <= MAX_DEGREE:
                current.append(new_degree)
                yield from recurse(current)
                current.pop()

    for start in START_DEGREES:
        yield from recurse([start])


def generate_heads(metre: tuple[int, int] = (4, 4)) -> list[Head]:
    """Generate all valid heads for a given metre (no scoring, just filtering)."""
    heads = []
    rhythm_cells = get_rhythm_cells(metre)

    for rhythm, rhythm_name in rhythm_cells:
        if not _has_rhythm_variety(rhythm):
            continue

        n_notes = len(rhythm)

        for degrees in enumerate_pitch_sequences(n_notes):
            valid, leap_size, direction = _is_valid_pitch(degrees)
            if not valid:
                continue

            head = Head(
                degrees=degrees,
                rhythm=rhythm,
                rhythm_name=rhythm_name,
                leap_size=leap_size,
                leap_direction=direction,
            )
            heads.append(head)

    return heads


def degrees_to_midi(degrees: tuple[int, ...], tonic_midi: int = 60, mode: str = "major") -> tuple[int, ...]:
    """Convert scale degrees to MIDI pitches."""
    scale = MINOR_SCALE if mode == "minor" else MAJOR_SCALE
    result = []
    for deg in degrees:
        octave = deg // 7
        scale_idx = deg % 7
        midi = tonic_midi + octave * 12 + scale[scale_idx]
        result.append(midi)
    return tuple(result)


def head_to_str(head: Head, tonic_midi: int = 60, mode: str = "major") -> str:
    """Format head as readable string."""
    midi = degrees_to_midi(head.degrees, tonic_midi, mode)
    pitch_str = ' '.join(f"{NOTE_NAMES[m % 12]}{m // 12 - 1}" for m in midi)
    return f"{pitch_str} | {head.rhythm_name} | leap {head.leap_direction} {head.leap_size}"


if __name__ == "__main__":
    heads = generate_heads()

    # Group by note count
    by_length = {}
    for h in heads:
        n = len(h.degrees)
        by_length.setdefault(n, []).append(h)

    print(f"Total valid heads: {len(heads)}")
    for n in sorted(by_length.keys()):
        print(f"  {n}-note: {len(by_length[n])}")

    print("\n" + "=" * 60)
    print("Sample heads (first 5 of each length):")
    print("=" * 60)

    for n in sorted(by_length.keys()):
        print(f"\n{n}-NOTE HEADS:")
        for head in by_length[n][:5]:
            print(f"  {head_to_str(head)}")
