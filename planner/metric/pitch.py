"""Pitch calculation utilities for metric planning."""
from planner.metric.constants import DRIFT_THRESHOLD
from shared.key import Key


def compute_base_octave(
    key: Key,
    degree: int,
    median: int,
) -> int:
    """Compute octave that places degree closest to median."""
    best_octave: int = 4
    best_dist: int = 999
    for octave in range(2, 7):
        midi: int = key.degree_to_midi(degree, octave=octave)
        dist: int = abs(midi - median)
        if dist < best_dist:
            best_dist = dist
            best_octave = octave
    return best_octave


def degree_to_midi(
    key: Key,
    degree: int,
    octave: int,
) -> int:
    """Convert scale degree to MIDI pitch at given octave."""
    return key.degree_to_midi(degree, octave=octave)


def gravitational_pitch(
    key: Key,
    degree: int,
    prev_pitch: int,
    median: int,
) -> int:
    """Find pitch of given degree using gravitational voice leading.
    
    Default: pure voice leading (nearest to prev_pitch).
    If nearest pitch would exceed DRIFT_THRESHOLD from median,
    select the octave closer to median instead.
    """
    candidates: list[int] = []
    for octave in range(1, 8):
        midi: int = key.degree_to_midi(degree, octave=octave)
        candidates.append(midi)
    candidates.sort(key=lambda m: abs(m - prev_pitch))
    nearest: int = candidates[0]
    nearest_drift: int = abs(nearest - median)
    if nearest_drift <= DRIFT_THRESHOLD:
        return nearest
    # Nearest exceeds threshold — find best alternative
    candidates.sort(key=lambda m: abs(m - median))
    for alt in candidates:
        if alt != nearest:
            return alt
    return nearest


def snap_to_key(
    midi: int,
    key: Key,
) -> int:
    """Snap MIDI pitch to nearest pitch in key."""
    pc: int = midi % 12
    key_pcs: set[int] = set()
    for degree in range(1, 8):
        degree_midi: int = key.degree_to_midi(degree, octave=0)
        key_pcs.add(degree_midi % 12)
    if pc in key_pcs:
        return midi
    for offset in [1, -1, 2, -2]:
        if (pc + offset) % 12 in key_pcs:
            return midi + offset
    return midi


def wrap_degree(degree: int) -> int:
    """Wrap scale degree to 1-7 range."""
    return ((degree - 1) % 7) + 1
