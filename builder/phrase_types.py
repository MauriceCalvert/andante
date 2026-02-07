"""Phrase-level types for phrase planner and writer.

Pure data containers for phrase planning and generation.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING
from shared.key import Key
from shared.voice_types import Range

if TYPE_CHECKING:
    from builder.types import Note


@dataclass(frozen=True)
class BeatPosition:
    """Position of a schema degree within a phrase."""
    bar: int
    beat: int


@dataclass(frozen=True)
class PhrasePlan:
    """Complete specification for writing one phrase (one schema)."""
    schema_name: str
    degrees_upper: tuple[int, ...]
    degrees_lower: tuple[int, ...]
    degree_positions: tuple[BeatPosition, ...]
    local_key: Key
    bar_span: int
    start_bar: int
    start_offset: Fraction
    phrase_duration: Fraction
    metre: str
    rhythm_profile: str
    is_cadential: bool
    cadence_type: str | None
    prev_exit_upper: int | None
    prev_exit_lower: int | None
    section_name: str
    upper_range: Range
    lower_range: Range
    upper_median: int
    lower_median: int
    bass_texture: str = "pillar"
    bass_pattern: str | None = None
    degree_keys: tuple[Key, ...] | None = None


@dataclass(frozen=True)
class PhraseResult:
    """Output of phrase writer for one phrase."""
    upper_notes: tuple[Note, ...]
    lower_notes: tuple[Note, ...]
    exit_upper: int
    exit_lower: int
    schema_name: str
    faults: tuple[str, ...] = ()
    soprano_figures: tuple[str, ...] = ()
    bass_pattern_name: str | None = None
