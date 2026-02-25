"""Voice writer types and protocols.

All types are frozen dataclasses. The FillStrategy protocol defines the
interface for span-filling strategies (diminution, walking, pillar, patterned).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Literal, Protocol

from builder.types import Note
from shared.key import Key

if TYPE_CHECKING:
    from motifs.thematic_transform import VerticalGenome
    from viterbi.mtypes import Knot


# =============================================================================
# Literal Types
# =============================================================================

GENRES = Literal[
    "bourree", "chorale", "fantasia", "gavotte",
    "invention", "minuet", "sarabande", "trio_sonata",
]

CHARACTERS = Literal["plain", "expressive", "energetic", "bold", "ornate"]

PHRASE_ZONE = Literal["opening", "middle", "cadential"]


# =============================================================================
# Structural Data
# =============================================================================

@dataclass(frozen=True)
class StructuralTone:
    """Schema arrival point with resolved pitch."""
    offset: Fraction
    midi: int
    key: Key


@dataclass(frozen=True)
class VoiceBias:
    """Per-voice Viterbi bias parameters bundled together (M001)."""
    degree_affinity: tuple[float, ...] | None = None
    interval_affinity: dict[int, float] | None = None
    structural_knots: list[Knot] | None = None
    vertical_genome: VerticalGenome | None = None


# =============================================================================
# Span Filling
# =============================================================================

@dataclass(frozen=True)
class SpanBoundary:
    """Boundary data for one span between structural tones."""
    start_offset: Fraction
    start_midi: int
    start_key: Key
    end_offset: Fraction
    end_midi: int | None
    end_key: Key | None
    phrase_bar: int
    total_bars: int
    is_final_span: bool


@dataclass(frozen=True)
class VoiceConfig:
    """Static configuration for voice generation."""
    voice_id: int
    range_low: int
    range_high: int
    key: Key
    metre: str
    bar_length: Fraction
    beat_unit: Fraction
    phrase_start: Fraction
    genre: GENRES
    character: CHARACTERS
    is_minor: bool
    guard_tolerance: frozenset[int]
    cadence_type: str | None


@dataclass(frozen=True)
class VoiceContext:
    """Immutable context for strategy span filling."""
    other_voices: dict[int, tuple[Note, ...]]
    own_prior_notes: tuple[Note, ...]
    prior_phrase_tail: Note | None
    structural_offsets: frozenset[Fraction]


# =============================================================================
# Strategy Metadata
# =============================================================================

@dataclass(frozen=True)
class SpanMetadata:
    """Base class for strategy-specific span metadata."""
    strategy_name: str


@dataclass(frozen=True)
class DiminutionMetadata(SpanMetadata):
    """Metadata from DiminutionFill."""
    figure_name: str
    used_stepwise_fallback: bool


@dataclass(frozen=True)
class WalkingMetadata(SpanMetadata):
    """Metadata from WalkingFill."""
    direction: str
    approach_type: str


@dataclass(frozen=True)
class PillarMetadata(SpanMetadata):
    """Metadata from PillarFill."""
    held: bool


@dataclass(frozen=True)
class PatternedMetadata(SpanMetadata):
    """Metadata from PatternedFill."""
    pattern_name: str


@dataclass(frozen=True)
class SpanResult:
    """Output from filling one span."""
    notes: tuple[Note, ...]
    metadata: SpanMetadata


# =============================================================================
# Strategy Protocol
# =============================================================================

class FillStrategy(Protocol):
    """Protocol for span-filling strategies."""

    def fill_span(
        self,
        span: SpanBoundary,
        config: VoiceConfig,
        context: VoiceContext,
    ) -> SpanResult: ...


# =============================================================================
# Audit
# =============================================================================

@dataclass(frozen=True)
class AuditViolation:
    """One detected counterpoint or melodic fault."""
    rule: str
    offset: Fraction
    pitch: int
    detail: str


# =============================================================================
# Pipeline Output
# =============================================================================

@dataclass(frozen=True)
class WriteResult:
    """Complete result from write_voice pipeline."""
    notes: tuple[Note, ...]
    span_metadata: tuple[SpanMetadata, ...]
    structural_offsets: frozenset[Fraction]
    audit_violations: tuple[AuditViolation, ...]
