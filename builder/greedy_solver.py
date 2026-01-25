"""Greedy pitch solver with look-ahead.

Fast O(n × d) solver that fills slots sequentially, choosing pitches that:
1. Are in key (pitch class set)
2. Are in tessitura range
3. Navigate toward the next anchor (look-ahead)
4. Prefer stepwise motion
5. Avoid parallel 5ths/8ves
6. Avoid oscillation (A-B-A patterns)

Now supports per-voice active slots for voice independence.
"""
from dataclasses import dataclass
from fractions import Fraction

PERFECT_INTERVALS: frozenset[int] = frozenset({0, 7})  # unison, fifth (mod 12)
SLOTS_PER_BAR: int = 16
DEBUG: bool = False


def _debug(msg: str) -> None:
    if DEBUG:
        print(f"[GREEDY] {msg}")


@dataclass(frozen=True)
class GreedyConfig:
    """Configuration for greedy solver."""
    voice_count: int
    pitch_class_set: frozenset[int]
    tessitura_medians: dict[int, int]
    tessitura_span: int


@dataclass(frozen=True)
class GreedySolution:
    """Greedy solver output."""
    pitches: dict[tuple[Fraction, int], int]
    cost: float


def _build_domain(
    voice: int,
    config: GreedyConfig,
) -> list[int]:
    """Build sorted list of valid pitches for a voice."""
    median: int = config.tessitura_medians[voice]
    span: int = config.tessitura_span
    low: int = median - span
    high: int = median + span
    domain: list[int] = []
    for midi in range(low, high + 1):
        if midi % 12 in config.pitch_class_set:
            domain.append(midi)
    return domain


def _is_parallel(
    prev_interval: int,
    curr_interval: int,
    prev_pitches_moved: bool,
) -> bool:
    """Check if motion creates parallel 5th/8ve."""
    if not prev_pitches_moved:
        return False
    prev_ic: int = abs(prev_interval) % 12
    curr_ic: int = abs(curr_interval) % 12
    if prev_ic in PERFECT_INTERVALS and curr_ic == prev_ic:
        return True
    return False


def _slot_to_offset(slot: int) -> Fraction:
    """Convert slot index to Fraction offset."""
    return Fraction(slot, SLOTS_PER_BAR)


def _find_next_anchor_for_voice(
    anchors: dict[tuple[Fraction, int], int],
    current_slot: int,
    voice: int,
    active_slots: frozenset[int],
) -> tuple[int | None, int]:
    """Find the next anchor for this voice and distance in active slots.

    Args:
        anchors: Anchor constraints (offset, voice) -> pitch
        current_slot: Current slot index
        voice: Voice number
        active_slots: Active slot indices for this voice

    Returns:
        Tuple of (anchor_pitch or None, steps_in_active_slots to reach it)
    """
    # Get sorted active slots after current
    future_slots: list[int] = sorted(s for s in active_slots if s > current_slot)

    for step, slot in enumerate(future_slots, start=1):
        offset: Fraction = _slot_to_offset(slot)
        key: tuple[Fraction, int] = (offset, voice)
        if key in anchors:
            return anchors[key], step

    return None, 0


def _pitch_cost(
    pitch: int,
    prev_pitch: int | None,
    prev_prev_pitch: int | None,
    target_pitch: int | None,
    steps_to_target: int,
    median: int,
) -> float:
    """Cost function with look-ahead toward target."""
    cost: float = 0.0

    # Motion from previous pitch
    if prev_pitch is not None:
        motion: int = abs(pitch - prev_pitch)
        if motion == 0:
            cost += 1.0  # repetition: penalised
        elif motion <= 2:
            cost += 0.1  # step: good
        elif motion <= 4:
            cost += 0.3  # skip: ok
        elif motion <= 7:
            cost += 0.6  # leap: penalised
        else:
            cost += 1.2  # large leap: strongly penalised

        # Reward motion toward target
        if target_pitch is not None and steps_to_target > 0:
            direction_needed: int = 1 if target_pitch > prev_pitch else -1 if target_pitch < prev_pitch else 0
            actual_direction: int = 1 if pitch > prev_pitch else -1 if pitch < prev_pitch else 0
            if direction_needed != 0:
                if actual_direction == direction_needed:
                    cost -= 0.3  # reward moving toward target
                elif actual_direction == -direction_needed:
                    cost += 0.2  # penalise moving away from target

    # Oscillation penalty
    if prev_prev_pitch is not None and pitch == prev_prev_pitch and prev_pitch != pitch:
        cost += 1.5  # oscillation A-B-A

    # Distance to target (should be reachable)
    if target_pitch is not None and steps_to_target > 0:
        distance_to_target: int = abs(pitch - target_pitch)
        # More generous reachability for sparse slots (can move more per active slot)
        max_reachable: int = steps_to_target * 4  # can move 4 semitones per active slot
        if distance_to_target > max_reachable:
            cost += 2.0  # unreachable: strong penalty

    # Tessitura: mild preference for median
    tessitura_dev: int = abs(pitch - median)
    cost += tessitura_dev * 0.02

    return cost


def solve_greedy(
    anchors: dict[tuple[Fraction, int], int],
    active_slots: dict[int, frozenset[int]],
    config: GreedyConfig,
) -> GreedySolution:
    """Fill active slots greedily with look-ahead toward anchors.

    Args:
        anchors: Anchor constraints mapping (offset, voice) -> pitch
        active_slots: Per-voice active slot indices: voice -> frozenset of slot indices
        config: Solver configuration

    Returns:
        GreedySolution with pitches for all active slots
    """
    domains: dict[int, list[int]] = {
        v: _build_domain(v, config) for v in range(config.voice_count)
    }
    _debug(f"Domains: voice 0 has {len(domains[0])} pitches, voice 1 has {len(domains[1])} pitches")

    # Start with anchors
    pitches: dict[tuple[Fraction, int], int] = dict(anchors)
    total_cost: float = 0.0

    # Track previous pitches per voice for continuity
    prev_pitches: dict[int, int] = {}
    prev_prev_pitches: dict[int, int] = {}

    # Get all unique slots across all voices, sorted
    all_slots: set[int] = set()
    for voice_slots in active_slots.values():
        all_slots.update(voice_slots)
    sorted_slots: list[int] = sorted(all_slots)

    _debug(f"Total active slots: {len(sorted_slots)}")

    # Track intervals for parallel detection
    prev_interval: int | None = None
    anchor_hits: int = 0

    for slot in sorted_slots:
        offset: Fraction = _slot_to_offset(slot)
        curr_pitches: dict[int, int] = {}

        for voice in range(config.voice_count):
            # Skip if this slot is not active for this voice
            voice_active: frozenset[int] = active_slots.get(voice, frozenset())
            if slot not in voice_active:
                # Carry forward previous pitch for interval tracking
                if voice in prev_pitches:
                    curr_pitches[voice] = prev_pitches[voice]
                continue

            key: tuple[Fraction, int] = (offset, voice)

            # Check if this is an anchor
            if key in anchors:
                curr_pitches[voice] = anchors[key]
                pitches[key] = anchors[key]
                anchor_hits += 1
                continue

            # Find best pitch for this slot
            domain: list[int] = domains[voice]
            prev_pitch: int | None = prev_pitches.get(voice)
            prev_prev_pitch: int | None = prev_prev_pitches.get(voice)
            median: int = config.tessitura_medians[voice]

            # Look-ahead to next anchor for this voice
            target_pitch, steps_to_target = _find_next_anchor_for_voice(
                anchors, slot, voice, voice_active
            )

            best_pitch: int = domain[len(domain) // 2]
            best_cost: float = float('inf')

            for pitch in domain:
                cost: float = _pitch_cost(
                    pitch, prev_pitch, prev_prev_pitch,
                    target_pitch, steps_to_target, median
                )
                if cost < best_cost:
                    best_cost = cost
                    best_pitch = pitch

            curr_pitches[voice] = best_pitch
            pitches[key] = best_pitch
            total_cost += best_cost

        # Check for parallel motion (only if both voices active at this slot)
        if config.voice_count >= 2 and 0 in curr_pitches and 1 in curr_pitches:
            # Only check if both voices are actually active at this slot
            voice_0_active: bool = slot in active_slots.get(0, frozenset())
            voice_1_active: bool = slot in active_slots.get(1, frozenset())

            if voice_0_active and voice_1_active:
                curr_interval: int = curr_pitches[0] - curr_pitches[1]
                if prev_interval is not None:
                    voices_moved: bool = (
                        prev_pitches.get(0) != curr_pitches.get(0) or
                        prev_pitches.get(1) != curr_pitches.get(1)
                    )
                    if _is_parallel(prev_interval, curr_interval, voices_moved):
                        total_cost += 5.0
                prev_interval = curr_interval

        # Update previous pitch tracking
        for voice, pitch in curr_pitches.items():
            if voice in active_slots and slot in active_slots[voice]:
                prev_prev_pitches[voice] = prev_pitches.get(voice, pitch)
                prev_pitches[voice] = pitch

    _debug(f"Anchor hits: {anchor_hits}")
    return GreedySolution(pitches=pitches, cost=total_cost)


def solve_greedy_legacy(
    anchors: dict[tuple[Fraction, int], int],
    offsets: list[Fraction],
    config: GreedyConfig,
) -> GreedySolution:
    """Legacy interface: fill all offsets for all voices.

    Converts offsets list to active_slots format and calls solve_greedy.
    """
    # Convert offsets to slot indices
    all_slots: frozenset[int] = frozenset(
        int(offset * SLOTS_PER_BAR) for offset in offsets
    )

    # All voices active at all slots
    active_slots: dict[int, frozenset[int]] = {
        v: all_slots for v in range(config.voice_count)
    }

    return solve_greedy(anchors, active_slots, config)
