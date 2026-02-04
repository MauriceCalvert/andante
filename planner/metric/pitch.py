"""Pitch calculation utilities for metric planning."""
from shared.key import Key
from shared.pitch import select_octave


def degree_to_midi(
    key: Key,
    degree: int,
    octave: int,
) -> int:
    """Convert scale degree to MIDI pitch at given octave."""
    return key.degree_to_midi(degree=degree, octave=octave)


def snap_to_key(
    midi: int,
    key: Key,
) -> int:
    """Snap MIDI pitch to nearest pitch in key."""
    pc: int = midi % 12
    key_pcs: set[int] = set()
    for degree in range(1, 8):
        degree_midi: int = key.degree_to_midi(degree=degree, octave=0)
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


__all__ = [
    "degree_to_midi",
    "select_octave",
    "snap_to_key",
    "wrap_degree",
]
