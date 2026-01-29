"""Type definitions for the figuration system.

All types are frozen dataclasses for immutability.
Durations are Fraction (whole notes). Degrees are integers (1-7).
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Figure:
    """Single melodic figure from diminution table.

    Represents a baroque melodic pattern that connects two structural tones.
    Degrees are relative to the starting pitch; final degree equals the interval.
    """
    name: str
    degrees: tuple[int, ...]
    contour: str
    polarity: str  # upper | lower | balanced
    arrival: str  # direct | stepwise | accented
    placement: str  # start | end | span
    character: str  # plain | expressive | energetic | ornate | bold
    harmonic_tension: str  # low | medium | high
    max_density: str  # low | medium | high
    cadential_safe: bool
    repeatable: bool
    requires_compensation: bool
    compensation_direction: str | None  # up | down | None
    is_compound: bool
    minor_safe: bool
    requires_leading_tone: bool
    weight: float  # historical frequency / selection probability

    def __post_init__(self) -> None:
        assert self.name, "Figure name cannot be empty"
        assert len(self.degrees) >= 2, f"Figure '{self.name}' must have at least 2 degrees"
        assert self.polarity in ("upper", "lower", "balanced"), f"Invalid polarity: {self.polarity}"
        assert self.arrival in ("direct", "stepwise", "accented"), f"Invalid arrival: {self.arrival}"
        assert self.placement in ("start", "end", "span"), f"Invalid placement: {self.placement}"
        assert self.character in ("plain", "expressive", "energetic", "ornate", "bold"), \
            f"Invalid character: {self.character}"
        assert self.harmonic_tension in ("low", "medium", "high"), \
            f"Invalid harmonic_tension: {self.harmonic_tension}"
        assert self.max_density in ("low", "medium", "high"), f"Invalid max_density: {self.max_density}"
        assert self.compensation_direction in (None, "up", "down"), \
            f"Invalid compensation_direction: {self.compensation_direction}"
        assert self.weight > 0, f"Weight must be positive, got {self.weight}"


@dataclass(frozen=True)
class CadentialFigure:
    """Cadential figure for phrase endings.

    Special figures used at cadences, indexed by target degree (1 or 5)
    and approach interval.
    """
    name: str
    degrees: tuple[int, ...]
    contour: str
    trill_position: int | None  # which degree gets trill (0-indexed), or None
    hemiola: bool

    def __post_init__(self) -> None:
        assert self.name, "CadentialFigure name cannot be empty"
        assert len(self.degrees) >= 2, f"CadentialFigure '{self.name}' must have at least 2 degrees"
        if self.trill_position is not None:
            assert 0 <= self.trill_position < len(self.degrees), \
                f"trill_position {self.trill_position} out of range for {len(self.degrees)} degrees"


@dataclass(frozen=True)
class PhrasePosition:
    """Bar position classification within phrase.

    Determines selection mode based on bar position and schema type.
    """
    position: str  # opening | continuation | cadence
    bars: tuple[int, int]  # e.g., (1, 2) for bars 1-2
    character: str  # plain | expressive | energetic
    sequential: bool  # Fortspinnung active

    def __post_init__(self) -> None:
        assert self.position in ("opening", "continuation", "cadence"), \
            f"Invalid position: {self.position}"
        assert len(self.bars) == 2, "bars must be a 2-tuple (start, end)"
        assert self.bars[0] <= self.bars[1], f"Invalid bar range: {self.bars}"
        assert self.character in ("plain", "expressive", "energetic"), \
            f"Invalid character: {self.character}"


@dataclass(frozen=True)
class RhythmTemplate:
    """Duration template for figure realisation.

    Maps note count and metre to specific duration patterns.
    Durations are in beats (not whole notes).
    """
    note_count: int
    metre: str  # "3/4", "4/4"
    durations: tuple[Fraction, ...]  # In beats
    overdotted: bool = False

    def __post_init__(self) -> None:
        assert self.note_count >= 2, f"note_count must be >= 2, got {self.note_count}"
        assert self.metre, "metre cannot be empty"
        assert len(self.durations) == self.note_count, \
            f"durations length {len(self.durations)} != note_count {self.note_count}"
        assert all(d > 0 for d in self.durations), "All durations must be positive"


@dataclass(frozen=True)
class FiguredBar:
    """Output of figuration for one bar.

    Contains the complete melodic content for a single bar after figuration.
    Bar 0 is used for anacrusis (upbeat).
    """
    bar: int
    degrees: tuple[int, ...]  # Scale degrees (absolute, 1-7)
    durations: tuple[Fraction, ...]  # Note durations in whole notes
    figure_name: str  # For tracing
    start_beat: int = 1  # Beat on which this voice enters (1=lead, 2=accompany)

    def __post_init__(self) -> None:
        assert self.bar >= 0, f"bar must be >= 0, got {self.bar}"
        assert len(self.degrees) == len(self.durations), \
            f"degrees length {len(self.degrees)} != durations length {len(self.durations)}"
        assert all(1 <= d <= 7 for d in self.degrees), \
            f"All degrees must be in range 1-7, got {self.degrees}"
        assert all(d > 0 for d in self.durations), "All durations must be positive"
        assert self.start_beat in (1, 2), f"start_beat must be 1 or 2, got {self.start_beat}"

    def get_onsets(self, bar_offset: Fraction) -> set[Fraction]:
        """Return onset positions (absolute offsets) for this bar's notes."""
        onsets: set[Fraction] = set()
        current: Fraction = bar_offset
        for dur in self.durations:
            onsets.add(current)
            current += dur
        return onsets


@dataclass(frozen=True)
class SelectionContext:
    """Context for figure selection decisions.

    Aggregates all information needed to select appropriate figures.
    """
    interval: str  # unison, step_up, step_down, third_up, etc.
    ascending: bool
    harmonic_tension: str  # low | medium | high
    character: str  # plain | expressive | energetic
    density: str  # low | medium | high
    is_minor: bool
    prev_leaped: bool
    leap_direction: str | None  # up | down | None
    bar_in_phrase: int
    total_bars_in_phrase: int
    schema_type: str | None
    phrase_deformation: str | None  # early_cadence | extended_continuation | None
    seed: int

    def __post_init__(self) -> None:
        from shared.constants import FIGURATION_INTERVALS
        assert self.interval in FIGURATION_INTERVALS, f"Invalid interval: {self.interval}"
        assert self.harmonic_tension in ("low", "medium", "high"), \
            f"Invalid harmonic_tension: {self.harmonic_tension}"
        assert self.character in ("plain", "expressive", "energetic"), \
            f"Invalid character: {self.character}"
        assert self.density in ("low", "medium", "high"), f"Invalid density: {self.density}"
        assert self.leap_direction in (None, "up", "down"), \
            f"Invalid leap_direction: {self.leap_direction}"
        assert self.phrase_deformation in (None, "early_cadence", "extended_continuation"), \
            f"Invalid phrase_deformation: {self.phrase_deformation}"
