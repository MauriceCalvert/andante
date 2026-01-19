"""Domain types for builder module.
All types are frozen dataclasses. All durations are Fraction.
Types here are builder-specific; shared types live in shared/.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import NamedTuple


class CollectedNote(NamedTuple):
    """A note collected from the elaborated tree.

    Fields are explicitly named to avoid tuple order confusion (L015).
    """

    role: str
    diatonic: int
    duration: Fraction
    offset: Fraction

@dataclass(frozen=True)
class Metre:
    """Time signature."""
    numerator: int
    denominator: int

    @property
    def bar_duration(self) -> Fraction:
        """Duration of one bar as a fraction of a semibreve."""
        return Fraction(self.numerator, self.denominator)

@dataclass(frozen=True)
class Notes:
    """Immutable sequence of notes with pitches and durations."""
    pitches: tuple[int, ...]
    durations: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if len(self.pitches) != len(self.durations):
            raise ValueError(
                f"pitches ({len(self.pitches)}) and durations "
                f"({len(self.durations)}) must have same length"
            )

@dataclass(frozen=True)
class FrameContext:
    """Musical context extracted from frame node."""
    key: str
    mode: str
    metre: Metre

@dataclass(frozen=True)
class BarContext:
    """Context for generating notes in a bar."""
    bar_index: int
    phrase_index: int
    phrase_treatment: str
    role: str
    harmony: tuple[str, ...] | None
    frame: FrameContext
    energy: str = "moderate"
    cadence: str | None = None

@dataclass(frozen=True)
class Subject:
    """Musical subject material."""
    notes: Notes
    source_key: str | None = None
    uses_pitches: bool = False

@dataclass(frozen=True)
class BarTreatment:
    """Treatment specification for a bar."""
    name: str
    transform: str
    shift: int

@dataclass(frozen=True)
class ParsedTreatment:
    """Parsed treatment string with base transform and ornaments."""
    base: str
    ornaments: tuple[str, ...]
