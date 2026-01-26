"""Figuration system for baroque melodic patterns.

Layer 6.5: Transforms anchors into idiomatic melodic motion using
authentic baroque figure vocabulary (Quantz, CPE Bach).

Pipeline: Anchors → Phrase Structure → Figure Selection → Rhythmic Realisation → Pitch Mapping → Notes
"""
from fractions import Fraction
from typing import Sequence

from builder.figuration.junction import check_junction, find_valid_figure
from builder.figuration.loader import get_cadential, get_diminutions
from builder.figuration.melodic_minor import MelodicMinorMapper, determine_direction
from builder.figuration.realiser import (
    compute_bar_duration,
    compute_gap_duration,
    realise_figure_to_bar,
)
from builder.figuration.selector import (
    compute_interval,
    determine_phrase_position,
    filter_by_character,
    filter_by_compensation,
    filter_by_density,
    filter_by_direction,
    filter_by_minor_safety,
    filter_by_tension,
    filter_cadential_safe,
    get_figures_for_interval,
    select_figure,
    sort_by_weight,
)
from builder.figuration.sequencer import SequencerState, apply_fortspinnung
from builder.figuration.types import (
    CadentialFigure,
    Figure,
    FiguredBar,
    PhrasePosition,
    RhythmTemplate,
    SelectionContext,
)
from builder.types import Anchor
from shared.key import Key

__all__ = [
    "CadentialFigure",
    "Figure",
    "FiguredBar",
    "PhrasePosition",
    "RhythmTemplate",
    "SelectionContext",
    "figurate",
    "figurate_single_bar",
]


def figurate(
    anchors: Sequence[Anchor],
    key: Key,
    metre: str,
    seed: int,
    density: str = "medium",
    affect_character: str = "plain",
) -> list[FiguredBar]:
    """Main entry point: Convert anchors to figured bars.

    Implements the full figuration pipeline:
    1. Compute intervals between consecutive anchors
    2. Determine phrase positions
    3. Select figures using filter pipeline
    4. Apply Fortspinnung for sequential sections
    5. Validate junctions
    6. Realise rhythms

    Args:
        anchors: Sequence of anchors (schema arrivals)
        key: Musical key
        metre: Time signature (e.g., "3/4", "4/4")
        seed: RNG seed for determinism
        density: Rhythmic density ("low", "medium", "high")
        affect_character: Character from affect ("plain", "expressive", "energetic")

    Returns:
        List of FiguredBar objects, one per anchor-to-anchor gap.
    """
    if len(anchors) < 2:
        return []

    sorted_anchors = sorted(anchors, key=lambda a: _parse_bar_beat(a.bar_beat))
    bar_duration = compute_bar_duration(metre)
    is_minor = key.mode == "minor"
    total_bars = _count_bars(sorted_anchors)

    figured_bars: list[FiguredBar] = []
    sequencer_state = SequencerState()
    prev_leaped = False
    leap_direction: str | None = None

    for i in range(len(sorted_anchors) - 1):
        anchor_a = sorted_anchors[i]
        anchor_b = sorted_anchors[i + 1]

        # Compute bar number
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]

        # Compute interval
        interval = compute_interval(anchor_a.soprano_degree, anchor_b.soprano_degree)
        ascending = anchor_b.soprano_degree > anchor_a.soprano_degree

        # Determine phrase position
        phrase_pos = determine_phrase_position(
            bar=bar_num,
            total_bars=total_bars,
            schema_type=anchor_a.schema,
        )

        # Select figure
        figure = _select_figure_with_filters(
            interval=interval,
            ascending=ascending,
            harmonic_tension="low",  # Default; could be derived from schema
            character=phrase_pos.character,
            density=density,
            is_minor=is_minor,
            prev_leaped=prev_leaped,
            leap_direction=leap_direction,
            bar_in_phrase=bar_num,
            total_bars_in_phrase=total_bars,
            near_cadence=phrase_pos.position == "cadence",
            seed=seed + i,
        )

        if figure is None:
            # Fallback to direct figure
            figure = _create_direct_figure(interval, anchor_a.soprano_degree, anchor_b.soprano_degree)

        # Validate junction
        if i + 2 < len(sorted_anchors):
            next_anchor = sorted_anchors[i + 2]
            if not check_junction(figure, next_anchor.soprano_degree):
                # Try to find alternative
                candidates = get_figures_for_interval(interval)
                alt_figure = find_valid_figure(candidates, next_anchor.soprano_degree)
                if alt_figure:
                    figure = alt_figure

        # Compute gap duration
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        gap = offset_b - offset_a

        # Realise figure
        figured_bar = realise_figure_to_bar(
            figure=figure,
            bar=bar_num,
            start_degree=anchor_a.soprano_degree,
            gap_duration=gap,
            metre=metre,
        )

        figured_bars.append(figured_bar)

        # Update state for next iteration
        prev_leaped = _is_leap(figure)
        leap_direction = "up" if ascending else "down" if not ascending else None

    return figured_bars


def figurate_single_bar(
    anchor_a: Anchor,
    anchor_b: Anchor,
    key: Key,
    metre: str,
    seed: int,
    bar_num: int,
    total_bars: int,
    density: str = "medium",
    character: str = "plain",
    prev_leaped: bool = False,
    leap_direction: str | None = None,
) -> FiguredBar | None:
    """Figurate a single bar between two anchors.

    Args:
        anchor_a: Starting anchor
        anchor_b: Ending anchor
        key: Musical key
        metre: Time signature
        seed: RNG seed
        bar_num: Current bar number
        total_bars: Total bars in phrase
        density: Rhythmic density
        character: Figure character
        prev_leaped: Whether previous bar ended with a leap
        leap_direction: Direction of previous leap

    Returns:
        FiguredBar, or None if no valid figure found.
    """
    interval = compute_interval(anchor_a.soprano_degree, anchor_b.soprano_degree)
    ascending = anchor_b.soprano_degree > anchor_a.soprano_degree
    is_minor = key.mode == "minor"

    phrase_pos = determine_phrase_position(bar_num, total_bars, anchor_a.schema)

    figure = _select_figure_with_filters(
        interval=interval,
        ascending=ascending,
        harmonic_tension="low",
        character=character,
        density=density,
        is_minor=is_minor,
        prev_leaped=prev_leaped,
        leap_direction=leap_direction,
        bar_in_phrase=bar_num,
        total_bars_in_phrase=total_bars,
        near_cadence=phrase_pos.position == "cadence",
        seed=seed,
    )

    if figure is None:
        return None

    offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
    offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
    gap = offset_b - offset_a

    return realise_figure_to_bar(
        figure=figure,
        bar=bar_num,
        start_degree=anchor_a.soprano_degree,
        gap_duration=gap,
        metre=metre,
    )


def _select_figure_with_filters(
    interval: str,
    ascending: bool,
    harmonic_tension: str,
    character: str,
    density: str,
    is_minor: bool,
    prev_leaped: bool,
    leap_direction: str | None,
    bar_in_phrase: int,
    total_bars_in_phrase: int,
    near_cadence: bool,
    seed: int,
) -> Figure | None:
    """Apply full filter pipeline and select figure."""
    candidates = get_figures_for_interval(interval)

    if not candidates:
        return None

    # Apply filters in order
    candidates = filter_by_direction(candidates, ascending)
    candidates = filter_by_tension(candidates, harmonic_tension)
    candidates = filter_by_character(candidates, character)
    candidates = filter_by_density(candidates, density)
    candidates = filter_by_minor_safety(candidates, is_minor)
    candidates = filter_by_compensation(candidates, prev_leaped, leap_direction)
    candidates = filter_cadential_safe(candidates, near_cadence)

    # Sort and select
    candidates = sort_by_weight(candidates)
    return select_figure(candidates, seed)


def _create_direct_figure(interval: str, from_degree: int, to_degree: int) -> Figure:
    """Create a simple direct figure when no candidates match."""
    return Figure(
        name=f"direct_{interval}",
        degrees=(0, to_degree - from_degree),
        contour="direct",
        polarity="balanced",
        arrival="direct",
        placement="span",
        character="plain",
        harmonic_tension="low",
        max_density="low",
        cadential_safe=True,
        repeatable=True,
        requires_compensation=False,
        compensation_direction=None,
        is_compound=False,
        minor_safe=True,
        requires_leading_tone=False,
        weight=0.5,
    )


def _is_leap(figure: Figure) -> bool:
    """Check if figure contains a leap (interval > 2)."""
    degrees = figure.degrees
    for i in range(len(degrees) - 1):
        if abs(degrees[i + 1] - degrees[i]) > 2:
            return True
    return False


def _parse_bar_beat(bar_beat: str) -> tuple[int, float]:
    """Parse bar.beat string into (bar, beat) tuple."""
    parts = bar_beat.split(".")
    bar = int(parts[0])
    beat = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar, beat)


def _bar_beat_to_offset(bar_beat: str, metre: str) -> Fraction:
    """Convert bar.beat string to offset in whole notes."""
    bar, beat = _parse_bar_beat(bar_beat)
    parts = metre.split("/")
    beats_per_bar = int(parts[0])
    beat_value = Fraction(1, int(parts[1]))

    offset = Fraction(bar - 1) * beats_per_bar * beat_value
    offset += Fraction(int(beat) - 1) * beat_value
    return offset


def _count_bars(anchors: Sequence[Anchor]) -> int:
    """Count total bars from anchor sequence."""
    if not anchors:
        return 0
    max_bar = max(_parse_bar_beat(a.bar_beat)[0] for a in anchors)
    return max_bar
