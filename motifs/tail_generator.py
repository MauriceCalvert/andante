"""Tail generator: generate tail from a given head.

A tail continues from the head with:
- Net contrary motion to the head's leap (mandatory)
- Rhythm drawn from head's duration vocabulary
- Melodic cells for interest (runs, neighbors, turns)
- Final note longer than previous
"""
from dataclasses import dataclass
from itertools import product
from motifs.head_generator import Head


# Interval cells for tails - each has a net direction
# (intervals, name, net_direction)
# Avoid 4ths/5ths - too dissonant for tail motion
TAIL_CELLS: tuple[tuple[tuple[int, ...], str, int], ...] = (
    # Downward cells (net < 0)
    ((-1,), "step-down", -1),
    ((-1, -1), "run-down-2", -2),
    ((-1, -1, -1), "run-down-3", -3),
    ((-1, -1, -1, -1), "run-down-4", -4),
    ((-2,), "skip-down-3rd", -2),
    ((-2, -1), "skip-step-down-3", -3),
    ((-2, -2), "skip-skip-down", -4),
    ((-1, -1, 1), "down-turn", -1),
    ((-2, 1), "skip-step-down", -1),
    ((-1, -2), "step-skip-down", -3),
    ((-1, -1, -2), "run-skip-down", -4),
    ((-2, -1, -1), "skip-run-down", -4),
    # Upward cells (net > 0)
    ((1,), "step-up", 1),
    ((1, 1), "run-up-2", 2),
    ((1, 1, 1), "run-up-3", 3),
    ((1, 1, 1, 1), "run-up-4", 4),
    ((2,), "skip-up-3rd", 2),
    ((2, 1), "skip-step-up-3", 3),
    ((2, 2), "skip-skip-up", 4),
    ((1, 1, -1), "up-turn", 1),
    ((2, -1), "skip-step-up", 1),
    ((1, 2), "step-skip-up", 3),
    ((1, 1, 2), "run-skip-up", 4),
    ((2, 1, 1), "skip-run-up", 4),
)

# Stable degrees for resolution (tonic triad across octaves)
STABLE_DEGREES = frozenset({0, 2, 4, 7, 9, 11, 14})


@dataclass(frozen=True)
class Tail:
    """A valid tail candidate."""
    intervals: tuple[int, ...]
    rhythm: tuple[float, ...]
    direction: str  # "up" or "down" (net)
    cell_names: tuple[str, ...]

    @property
    def n_notes(self) -> int:
        return len(self.intervals) + 1

    @property
    def total_duration(self) -> float:
        return sum(self.rhythm)


def _find_rhythm_combinations(
    pool: tuple[float, ...],
    target: float,
    min_notes: int,
    max_notes: int,
) -> list[tuple[float, ...]]:
    """Find rhythm combinations from pool that sum to target.

    Returns rhythms ending with: ..., smallest, largest (cadential feel).
    Must use at least 2 distinct durations.
    """
    durations = sorted(set(pool))
    if len(durations) < 2:
        return []

    results = []
    smallest, largest = durations[0], durations[-1]

    # We reserve smallest + largest for the ending
    # Body must sum to: target - smallest - largest
    body_target = target - smallest - largest
    if body_target < -0.001:
        return []

    # Solve for body: sum of counts * durations = body_target
    if len(durations) == 2:
        a, b = durations
        for n_a in range(max_notes + 1):
            remainder = body_target - n_a * a
            if remainder < -0.001:
                break
            if abs(remainder % b) < 0.001:
                n_b = int(round(remainder / b))
                if n_b < 0:
                    continue
                body_notes = n_a + n_b
                total = body_notes + 2  # +2 for smallest, largest ending
                if min_notes <= total <= max_notes:
                    body = [a] * n_a + [b] * n_b
                    rhythm = tuple(body + [smallest, largest])
                    results.append(rhythm)

    elif len(durations) == 3:
        a, b, c = durations
        for n_a in range(max_notes + 1):
            for n_b in range(max_notes + 1 - n_a):
                remainder = body_target - n_a * a - n_b * b
                if remainder < -0.001:
                    break
                if abs(remainder % c) < 0.001:
                    n_c = int(round(remainder / c))
                    if n_c < 0:
                        continue
                    body_notes = n_a + n_b + n_c
                    total = body_notes + 2
                    # Count distinct: body uses some, ending adds smallest and largest
                    body_distinct = (n_a > 0) + (n_b > 0) + (n_c > 0)
                    if min_notes <= total <= max_notes and body_distinct >= 0:
                        body = [a] * n_a + [b] * n_b + [c] * n_c
                        rhythm = tuple(body + [smallest, largest])
                        results.append(rhythm)

    return results


def _build_interval_sequences(
    target_direction: str,
    min_intervals: int,
    max_intervals: int,
) -> list[tuple[tuple[int, ...], tuple[str, ...]]]:
    """Build interval sequences from cells with net motion in target direction."""
    # Filter cells by direction
    if target_direction == "down":
        cells = [(ivs, name) for ivs, name, net in TAIL_CELLS if net < 0]
    else:
        cells = [(ivs, name) for ivs, name, net in TAIL_CELLS if net > 0]

    sequences: list[tuple[tuple[int, ...], tuple[str, ...]]] = []

    # 1-cell
    for ivs, name in cells:
        if min_intervals <= len(ivs) <= max_intervals:
            sequences.append((ivs, (name,)))

    # 2-cell combinations
    for (iv1, n1), (iv2, n2) in product(cells, repeat=2):
        ivs = iv1 + iv2
        if min_intervals <= len(ivs) <= max_intervals:
            sequences.append((ivs, (n1, n2)))

    # 3-cell combinations
    for (iv1, n1), (iv2, n2), (iv3, n3) in product(cells, repeat=3):
        ivs = iv1 + iv2 + iv3
        if min_intervals <= len(ivs) <= max_intervals:
            sequences.append((ivs, (n1, n2, n3)))

    return sequences


def get_target_duration(metre: tuple[int, int], duration_bars: int = 2) -> float:
    """Calculate total subject duration for a given metre and bar count."""
    bar_duration = metre[0] / metre[1]
    return bar_duration * duration_bars


def generate_tails_for_head(
    head: Head,
    target_total: float = 2.0,
    min_tail_notes: int = 3,
    max_tail_notes: int = 12,
    min_degree: int = -4,  # F3, prevents notes going too low
    max_degree: int = 11,  # G5, prevents notes going too high
) -> list[Tail]:
    """Generate valid tails for a given head."""
    # Tail direction is contrary to head's leap
    direction = "down" if head.leap_direction == "up" else "up"

    # Remaining duration for tail (excluding shared first note)
    head_dur = sum(head.rhythm)
    remaining = round(target_total - head_dur, 4)
    if remaining <= 0:
        return []

    # Rhythm pool from head
    rhythm_pool = tuple(sorted(set(head.rhythm)))
    if len(rhythm_pool) < 2:
        return []

    # Find rhythm combinations (these are for notes after the shared one)
    rhythm_combos = _find_rhythm_combinations(
        pool=rhythm_pool,
        target=remaining,
        min_notes=min_tail_notes - 1,
        max_notes=max_tail_notes - 1,
    )

    # Build interval sequences
    # n_intervals = n_notes - 1, so for tail contribution of k notes, we need k intervals
    interval_seqs_by_len: dict[int, list[tuple[tuple[int, ...], tuple[str, ...]]]] = {}
    for n in range(min_tail_notes - 1, max_tail_notes):
        seqs = _build_interval_sequences(target_direction=direction, min_intervals=n, max_intervals=n)
        if seqs:
            interval_seqs_by_len[n] = seqs

    # Combine rhythms with matching interval sequences
    tails = []
    for rhythm in rhythm_combos:
        n_tail_contrib = len(rhythm)  # Notes contributed by tail (after shared)
        n_intervals_needed = n_tail_contrib  # One interval per contributed note

        if n_intervals_needed not in interval_seqs_by_len:
            continue

        for intervals, cell_names in interval_seqs_by_len[n_intervals_needed]:
            # Reject mostly stepwise (more than half are ±1)
            step_count = sum(1 for iv in intervals if abs(iv) == 1)
            if step_count > len(intervals) // 2:
                continue

            # Reject oscillating patterns (repeated back-and-forth)
            if _is_oscillating(intervals=intervals):
                continue

            # Check final degree resolves to stable tone
            final_degree = head.degrees[-1] + sum(intervals)
            if final_degree % 7 not in (0, 2, 4):  # Tonic triad within octave
                continue

            # Require minimum pitch range (at least a 4th = 3 degrees)
            cumulative = [0]
            for iv in intervals:
                cumulative.append(cumulative[-1] + iv)
            pitch_range = max(cumulative) - min(cumulative)
            if pitch_range < 3:
                continue

            # Check all notes stay within allowed pitch range
            start_degree = head.degrees[-1]
            absolute_degrees = [start_degree + c for c in cumulative]
            if max(absolute_degrees) > max_degree or min(absolute_degrees) < min_degree:
                continue

            # Full rhythm includes shared first note
            full_rhythm = (head.rhythm[-1],) + rhythm

            tail = Tail(
                intervals=intervals,
                rhythm=full_rhythm,
                direction=direction,
                cell_names=cell_names,
            )
            tails.append(tail)

    return tails


def _is_oscillating(intervals: tuple[int, ...]) -> bool:
    """Check if intervals create boring oscillation (e.g., +1,-1,+1,-1)."""
    if len(intervals) < 4:
        return False
    # Check for repeated 2-interval pattern
    for i in range(len(intervals) - 3):
        a, b, c, d = intervals[i:i+4]
        if a == c and b == d and a == -b:
            return True
    return False


def tail_to_degrees(tail: Tail, start_degree: int) -> tuple[int, ...]:
    """Convert tail intervals to absolute degrees starting from given degree."""
    degrees = [start_degree]
    for iv in tail.intervals:
        degrees.append(degrees[-1] + iv)
    return tuple(degrees)


def tail_to_str(tail: Tail) -> str:
    """Format tail as readable string."""
    cells = " + ".join(tail.cell_names)
    return f"{tail.direction} | {cells} | {tail.n_notes} notes | dur={tail.total_duration:.2f}"


if __name__ == "__main__":
    from motifs.head_generator import generate_heads

    heads = generate_heads()
    print(f"Total heads: {len(heads)}")

    # Test tail generation
    total_tails = 0
    heads_with_tails = 0

    for head in heads[:100]:
        tails = generate_tails_for_head(head=head)
        if tails:
            heads_with_tails += 1
            total_tails += len(tails)

    print(f"\nFirst 100 heads:")
    print(f"  Heads with valid tails: {heads_with_tails}")
    print(f"  Total tails generated: {total_tails}")

    # Show examples
    print("\n" + "=" * 60)
    shown = 0
    for head in heads:
        tails = generate_tails_for_head(head=head)
        if tails and shown < 5:
            print(f"\nHead: {head.degrees} | {head.rhythm} | leap {head.leap_direction}")
            for tail in tails[:3]:
                print(f"  Tail: {tail_to_str(tail=tail)}")
                print(f"    intervals: {tail.intervals}")
            shown += 1
