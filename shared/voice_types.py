"""Voice and instrument types.

Canonical types for voice ranges.
All types are frozen dataclasses.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Range:
    """Pitch limits for an actuator (MIDI pitch values)."""
    low: int
    high: int
