"""Unified schema types shared between planner and builder.

Single source of truth (L017) for schema definitions loaded from
data/schemas/schemas.yaml.
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Arrival:
    """Entry or exit point: soprano and bass degree."""
    soprano: int
    bass: int


@dataclass(frozen=True)
class Schema:
    """Schema definition from schemas.yaml.

    Unified type replacing the former duplicate Schema (planner) and
    SchemaConfig (builder).
    """
    name: str
    soprano_degrees: tuple[int, ...]
    soprano_directions: tuple[str | None, ...]  # up/down/same/None per degree
    bass_degrees: tuple[int, ...]
    bass_directions: tuple[str | None, ...]  # up/down/same/None per degree
    entry: Arrival  # derived from first degrees
    exit: Arrival  # derived from last degrees
    min_bars: int
    max_bars: int
    position: str  # opening, riposte, continuation, pre_cadential, cadential, post_cadential
    cadential_state: str  # open, closed, preparing, half
    sequential: bool
    segments: tuple[int, ...]  # segment counts (tuple for consistency)
    direction: str | None  # ascending, descending for sequential schemas
    segment_direction: str | None  # up/down between segments for sequential schemas
    pedal: str | None  # dominant, tonic, subdominant
    chromatic: bool  # has chromatic alterations
    figuration_profile: str  # figuration profile name from figuration_profiles.yaml
    cadence_approach: bool  # whether final connection uses cadential patterns
    typical_keys: tuple[str, ...] | None  # key journey for sequential schemas

    @property
    def stage_count(self) -> int:
        """Number of stages. For sequential, multiply by max segments."""
        base: int = len(self.soprano_degrees)
        if self.sequential:
            return base * max(self.segments)
        return base

    # Backward-compatible aliases for former SchemaConfig field names
    @property
    def bars_min(self) -> int:
        return self.min_bars

    @property
    def bars_max(self) -> int:
        return self.max_bars

    @property
    def entry_soprano(self) -> int:
        return self.entry.soprano

    @property
    def entry_bass(self) -> int:
        return self.entry.bass

    @property
    def exit_soprano(self) -> int:
        return self.exit.soprano

    @property
    def exit_bass(self) -> int:
        return self.exit.bass
