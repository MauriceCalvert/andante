"""Voice and instrument entity model per voices.md.

Canonical types for voices, instruments, actuators, scoring, and tracks.
All types are frozen dataclasses.  Role is an enum.
"""
from dataclasses import dataclass
from enum import Enum


class Role(Enum):
    """How a voice's pitches are determined."""
    SCHEMA_UPPER = "schema_upper"
    SCHEMA_LOWER = "schema_lower"
    IMITATIVE = "imitative"
    HARMONY_FILL = "harmony_fill"


@dataclass(frozen=True)
class Range:
    """Pitch limits for an actuator (MIDI pitch values)."""
    low: int
    high: int


@dataclass(frozen=True)
class Actuator:
    """Mechanism that produces notes on an instrument."""
    id: str
    range: Range


@dataclass(frozen=True)
class InstrumentDef:
    """Instrument definition from library."""
    id: str
    actuators: tuple[Actuator, ...]


@dataclass(frozen=True)
class Voice:
    """Single monophonic melodic line with continuity."""
    id: str
    role: Role
    follows: str | None = None
    delay_bars: int | None = None
    interval: int | None = None


@dataclass(frozen=True)
class Instrument:
    """Physical instrument instance in a piece."""
    id: str
    type: str


@dataclass(frozen=True)
class ScoringAssignment:
    """Single voice-to-actuator assignment."""
    voice_id: str
    instrument_id: str
    actuator_id: str


@dataclass(frozen=True)
class TrackAssignment:
    """MIDI track assignment for a voice."""
    voice_id: str
    channel: int
    program: int
