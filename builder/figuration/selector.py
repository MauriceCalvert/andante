"""Figure selection pipeline for figuration system.

Implements the 13-step filter pipeline from figuration.md:
1. Compute interval (anchor A to anchor B)
2. Filter by interval
3. Filter by direction (ascending/descending/static)
4. Filter by harmonic tension
5. Filter by character (from phrase position)
6. Filter by density (from affect)
7. Filter by minor safety (if minor key)
8. Filter by compensation need (if previous figure leaped)
9. Apply controlled misbehaviour
10. Sort by weight
11. Select via seeded RNG
12. Check junction to next anchor
13. If junction fails, try next candidate
"""
import random
from fractions import Fraction
from typing import Sequence

from builder.figuration.loader import get_diminutions
from builder.figuration.types import Figure, PhrasePosition, SelectionContext
from builder.types import Anchor
from shared.constants import FIGURATION_INTERVALS, MISBEHAVIOUR_PROBABILITY, ONSET_COVERAGE_BONUS


def compute_interval(degree_a: int, degree_b: int) -> str:
    """Compute interval name from two scale degrees.

    Args:
        degree_a: Starting degree (1-7)
        degree_b: Ending degree (1-7)

    Returns:
        Interval name like "step_up", "third_down", etc.
    """
    diff = degree_b - degree_a

    # Handle octave wrapping
    while diff > 7:
        diff -= 7
    while diff < -7:
        diff += 7

    if diff == 0:
        return "unison"
    elif diff == 1:
        return "step_up"
    elif diff == -1:
        return "step_down"
    elif diff == 2:
        return "third_up"
    elif diff == -2:
        return "third_down"
    elif diff == 3:
        return "fourth_up"
    elif diff == -3:
        return "fourth_down"
    elif diff == 4:
        return "fifth_up"
    elif diff == -4:
        return "fifth_down"
    elif diff == 5:
        return "sixth_up"
    elif diff == -5:
        return "sixth_down"
    elif diff == 6:
        return "octave_up"  # 7th scale degree span = octave in diatonic
    elif diff == -6:
        return "octave_down"
    elif diff == 7:
        return "octave_up"
    elif diff == -7:
        return "octave_down"
    else:
        assert False, f"Unexpected interval diff: {diff}"


def compute_interval_with_direction(
    degree_a: int,
    degree_b: int,
    direction: str | None,
) -> str:
    """Compute interval name using explicit direction.

    When schema specifies direction (up/down/same), use it to resolve
    ambiguity in degree-only computation. E.g., degree 1->7 with direction
    'down' is step_down, not sixth_up.

    Args:
        degree_a: Starting degree (1-7)
        degree_b: Ending degree (1-7)
        direction: Explicit direction (up/down/same) or None

    Returns:
        Interval name like "step_up", "third_down", etc.
    """
    if direction == "same" or degree_a == degree_b:
        return "unison"
    diff = degree_b - degree_a
    # Adjust diff to match explicit direction
    if direction == "down" and diff > 0:
        diff = diff - 7
    elif direction == "up" and diff < 0:
        diff = diff + 7
    # Handle remaining octave wrapping for None direction
    while diff > 7:
        diff -= 7
    while diff < -7:
        diff += 7
    if diff == 0:
        return "unison"
    elif diff == 1:
        return "step_up"
    elif diff == -1:
        return "step_down"
    elif diff == 2:
        return "third_up"
    elif diff == -2:
        return "third_down"
    elif diff == 3:
        return "fourth_up"
    elif diff == -3:
        return "fourth_down"
    elif diff == 4:
        return "fifth_up"
    elif diff == -4:
        return "fifth_down"
    elif diff == 5:
        return "sixth_up"
    elif diff == -5:
        return "sixth_down"
    elif diff in (6, 7):
        return "octave_up"
    elif diff in (-6, -7):
        return "octave_down"
    else:
        assert False, f"Unexpected interval diff: {diff}"


def compute_interval_from_anchors(anchor_a: Anchor, anchor_b: Anchor) -> str:
    """Compute interval name between two anchors (upper voice).

    Uses anchor_b's direction field to resolve ambiguous degree intervals.

    Args:
        anchor_a: Starting anchor
        anchor_b: Ending anchor

    Returns:
        Interval name.
    """
    return compute_interval_with_direction(
        anchor_a.upper_degree,
        anchor_b.upper_degree,
        anchor_b.upper_direction,
    )


def filter_by_interval(figures: list[Figure], interval: str) -> list[Figure]:
    """Filter figures to those matching the given interval.

    This is typically done at load time by selecting from the interval-indexed dict.

    Args:
        figures: List of figures to filter
        interval: Interval name

    Returns:
        Figures that work for this interval.
    """
    assert interval in FIGURATION_INTERVALS, f"Invalid interval: {interval}"
    # For interval-indexed data, this would return the pre-filtered list
    # For flat data, we'd check final degree matches interval
    return figures  # Already filtered by interval at load time


def filter_by_direction(figures: list[Figure], ascending: bool) -> list[Figure]:
    """Filter figures by ascending/descending direction preference.

    Args:
        figures: List of figures to filter
        ascending: True for ascending motion, False for descending

    Returns:
        Figures matching direction preference.
    """
    if not figures:
        return []

    result: list[Figure] = []
    for fig in figures:
        # Check polarity compatibility
        if ascending and fig.polarity == "lower":
            # Lower polarity doesn't fit ascending context well
            continue
        if not ascending and fig.polarity == "upper":
            # Upper polarity doesn't fit descending context well
            continue
        result.append(fig)

    # If all filtered out, return original (soft filter)
    return result if result else figures


def filter_by_tension(figures: list[Figure], tension: str) -> list[Figure]:
    """Filter figures by harmonic tension level.

    Args:
        figures: List of figures to filter
        tension: Target tension level ("low", "medium", "high")

    Returns:
        Figures matching tension level (±1 level allowed).
    """
    if not figures:
        return []

    tension_order = {"low": 0, "medium": 1, "high": 2}
    target_level = tension_order.get(tension, 1)

    result: list[Figure] = []
    for fig in figures:
        fig_level = tension_order.get(fig.harmonic_tension, 1)
        # Allow exact match or adjacent levels
        if abs(fig_level - target_level) <= 1:
            result.append(fig)

    return result if result else figures


def filter_by_character(figures: list[Figure], character: str) -> list[Figure]:
    """Filter figures by character type.

    Args:
        figures: List of figures to filter
        character: Target character ("plain", "expressive", "energetic")

    Returns:
        Figures matching character type.
    """
    if not figures:
        return []

    # Character compatibility mapping
    compatible: dict[str, set[str]] = {
        "plain": {"plain", "expressive"},
        "expressive": {"plain", "expressive", "ornate"},
        "energetic": {"energetic", "bold", "expressive"},
    }

    target_chars = compatible.get(character, {character})

    result: list[Figure] = []
    for fig in figures:
        if fig.character in target_chars:
            result.append(fig)

    return result if result else figures


def filter_by_density(figures: list[Figure], density: str) -> list[Figure]:
    """Filter figures by maximum density level.

    A figure's max_density indicates the maximum density it's appropriate for.
    For a target density, we accept figures whose max_density <= target.
    - Low density target: only simple (low) figures appropriate
    - High density target: all figures acceptable (busy passages allow anything)

    Args:
        figures: List of figures to filter
        density: Target density ("low", "medium", "high")

    Returns:
        Figures compatible with density level.
    """
    if not figures:
        return []

    density_order = {"low": 0, "medium": 1, "high": 2}
    target_level = density_order.get(density, 1)

    result: list[Figure] = []
    for fig in figures:
        fig_level = density_order.get(fig.max_density, 1)
        # Target level must be >= figure's max_density
        # High target (2): accepts all figures (2 >= any level)
        # Low target (0): only accepts low max_density (0 >= 0)
        if target_level >= fig_level:
            result.append(fig)

    return result if result else figures


def filter_by_minor_safety(figures: list[Figure], is_minor: bool) -> list[Figure]:
    """Filter figures for minor key safety.

    Args:
        figures: List of figures to filter
        is_minor: True if in minor key

    Returns:
        Figures safe for minor keys (if applicable).
    """
    if not figures or not is_minor:
        return figures

    result: list[Figure] = []
    for fig in figures:
        if fig.minor_safe:
            result.append(fig)

    return result if result else figures


def filter_by_compensation(
    figures: list[Figure],
    prev_leaped: bool,
    leap_direction: str | None,
) -> list[Figure]:
    """Filter figures based on leap compensation needs.

    After a leap, prefer figures that provide contrary stepwise motion.

    Args:
        figures: List of figures to filter
        prev_leaped: True if previous figure ended with a leap
        leap_direction: Direction of previous leap ("up", "down", or None)

    Returns:
        Figures suitable given compensation context.
    """
    if not figures or not prev_leaped:
        return figures

    result: list[Figure] = []
    for fig in figures:
        # Prefer figures that don't require further compensation
        if not fig.requires_compensation:
            result.append(fig)
        # Or figures that compensate in the opposite direction
        elif fig.compensation_direction is not None:
            if leap_direction == "up" and fig.compensation_direction == "down":
                result.append(fig)
            elif leap_direction == "down" and fig.compensation_direction == "up":
                result.append(fig)

    return result if result else figures


def filter_cadential_safe(figures: list[Figure], near_cadence: bool) -> list[Figure]:
    """Filter figures for cadential safety.

    Args:
        figures: List of figures to filter
        near_cadence: True if approaching cadence

    Returns:
        Figures safe near cadences (if applicable).
    """
    if not figures or not near_cadence:
        return figures

    result: list[Figure] = []
    for fig in figures:
        if fig.cadential_safe:
            result.append(fig)

    return result if result else figures


def apply_misbehaviour(
    figures: list[Figure],
    all_figures_for_interval: list[Figure],
    seed: int,
    probability: float = MISBEHAVIOUR_PROBABILITY,
) -> list[Figure]:
    """Apply controlled misbehaviour by occasionally relaxing filters.

    With small probability, this allows figures that would normally be filtered.
    This prevents over-regular, textbook surfaces.

    Args:
        figures: List of filtered figures
        all_figures_for_interval: Unfiltered figures for this interval
        seed: RNG seed for determinism
        probability: Probability of misbehaviour (default 5%)

    Returns:
        Possibly expanded figure list.
    """
    if not figures:
        return figures
    rng = random.Random(seed)
    if rng.random() < probability and all_figures_for_interval:
        # Misbehaviour: return all figures for this interval, ignoring filters
        return list(all_figures_for_interval)
    return figures


def sort_by_weight(figures: list[Figure]) -> list[Figure]:
    """Sort figures by weight (descending) then name (alphabetical).

    Deterministic ordering ensures reproducible selection.

    Args:
        figures: List of figures to sort

    Returns:
        Sorted figure list.
    """
    return sorted(figures, key=lambda f: (-f.weight, f.name))


def select_figure(figures: list[Figure], seed: int) -> Figure | None:
    """Select a figure using seeded weighted random selection.

    Args:
        figures: List of candidate figures (should be sorted)
        seed: RNG seed for determinism

    Returns:
        Selected figure, or None if no candidates.
    """
    if not figures:
        return None

    rng = random.Random(seed)

    # Weighted selection based on figure weights
    total_weight = sum(f.weight for f in figures)
    if total_weight <= 0:
        return figures[0] if figures else None

    r = rng.random() * total_weight
    cumulative = 0.0

    for fig in figures:
        cumulative += fig.weight
        if r <= cumulative:
            return fig

    return figures[-1]  # Fallback to last


def determine_phrase_position(
    bar: int,
    total_bars: int,
    schema_type: str | None = None,
) -> PhrasePosition:
    """Determine phrase position for a bar within a phrase.

    Standard 8-bar phrase structure:
    - Opening: bars 1-2
    - Continuation: bars 3-6
    - Cadence: bars 7-8

    Args:
        bar: Bar number within phrase (0-indexed for anacrusis, 1-indexed otherwise)
        total_bars: Total bars in phrase
        schema_type: Optional schema type for overrides

    Returns:
        PhrasePosition for the bar.
    """
    assert bar >= 0, f"bar must be >= 0, got {bar}"
    assert total_bars >= 1, f"total_bars must be >= 1, got {total_bars}"
    if bar == 0:
        return PhrasePosition(
            position="opening",
            bars=(0, 0),
            character="plain",
            sequential=False,
        )

    # Schema overrides for sequential schemas
    sequential = schema_type in ("monte", "fonte", "meyer", "ponte")

    # For short phrases (< 4 bars), use simplified position logic
    if total_bars <= 2:
        # 1-2 bar phrases: just opening and cadence
        if bar == total_bars:
            return PhrasePosition(
                position="cadence",
                bars=(total_bars, total_bars),
                character="plain",
                sequential=False,
            )
        else:
            return PhrasePosition(
                position="opening",
                bars=(1, max(1, total_bars - 1)),
                character="plain",
                sequential=False,
            )

    # Standard phrase structure for 3+ bars
    # Normalize bar position relative to phrase length
    position_pct = bar / total_bars

    # Compute bar boundaries
    opening_end = max(1, total_bars // 4)
    cadence_start = max(opening_end + 1, (3 * total_bars) // 4 + 1)
    continuation_end = cadence_start - 1

    if position_pct <= 0.25:
        # First quarter: opening
        return PhrasePosition(
            position="opening",
            bars=(1, opening_end),
            character="plain",
            sequential=False,
        )
    elif bar < cadence_start:
        # Middle: continuation
        return PhrasePosition(
            position="continuation",
            bars=(opening_end + 1, continuation_end),
            character="energetic" if sequential else "expressive",
            sequential=sequential,
        )
    else:
        # Final quarter: cadence
        return PhrasePosition(
            position="cadence",
            bars=(cadence_start, total_bars),
            character="plain",
            sequential=False,
        )


def select_figure_for_bar(
    anchor_a: Anchor,
    anchor_b: Anchor,
    context: SelectionContext,
) -> Figure | None:
    """Main entry point: Select appropriate figure for bar.

    Implements the full 13-step filter pipeline.

    Args:
        anchor_a: Starting anchor
        anchor_b: Ending anchor
        context: Selection context with all filter criteria

    Returns:
        Selected figure, or None if no valid candidates.
    """
    diminutions = get_diminutions()
    # Step 1: Get figures for interval
    interval = context.interval
    if interval not in diminutions:
        return None
    all_figures = list(diminutions[interval])
    candidates = list(all_figures)
    # Step 2: Already filtered by interval
    # Step 3: Filter by direction
    candidates = filter_by_direction(candidates, context.ascending)
    # Step 4: Filter by harmonic tension
    candidates = filter_by_tension(candidates, context.harmonic_tension)
    # Step 5: Filter by character
    candidates = filter_by_character(candidates, context.character)
    # Step 6: Filter by density
    candidates = filter_by_density(candidates, context.density)
    # Step 7: Filter by minor safety
    candidates = filter_by_minor_safety(candidates, context.is_minor)
    # Step 8: Filter by compensation
    candidates = filter_by_compensation(
        candidates,
        context.prev_leaped,
        context.leap_direction,
    )
    # Check if near cadence
    near_cadence = (
        context.bar_in_phrase >= context.total_bars_in_phrase - 1
    )
    candidates = filter_cadential_safe(candidates, near_cadence)
    # Step 9: Apply misbehaviour (pass unfiltered list for relaxation)
    candidates = apply_misbehaviour(candidates, all_figures, context.seed)
    # Step 10: Sort by weight
    candidates = sort_by_weight(candidates)
    # Step 11: Select via seeded RNG
    selected = select_figure(candidates, context.seed)
    # Steps 12-13 (junction check) handled by junction.py
    return selected


def get_figures_for_interval(interval: str) -> list[Figure]:
    """Get all figures for a given interval.

    Args:
        interval: Interval name

    Returns:
        List of figures for that interval.
    """
    assert interval in FIGURATION_INTERVALS, f"Invalid interval: {interval}"
    diminutions = get_diminutions()
    return list(diminutions.get(interval, []))


def score_by_coverage(
    figures: list[Figure],
    covered_onsets: set[Fraction] | None,
    bar_offset: Fraction,
    gap_duration: Fraction,
    metre: str,
) -> list[tuple[Figure, float]]:
    """Score figures by how many new onsets they add.

    Args:
        figures: Candidate figures.
        covered_onsets: Onsets already covered by other voices (or None to skip).
        bar_offset: Start offset of this bar.
        gap_duration: Duration to fill (anchor A to anchor B).
        metre: Metre string like "4/4".

    Returns:
        List of (figure, bonus) tuples. Bonus is added to selection weight.
    """
    if covered_onsets is None or not figures:
        return [(f, 0.0) for f in figures]

    result: list[tuple[Figure, float]] = []

    for fig in figures:
        note_count = len(fig.degrees)
        avg_duration = gap_duration / note_count if note_count > 0 else gap_duration

        candidate_onsets: set[Fraction] = set()
        current = bar_offset
        for _ in range(note_count):
            candidate_onsets.add(current)
            current += avg_duration

        new_count = len(candidate_onsets - covered_onsets)
        bonus = new_count * ONSET_COVERAGE_BONUS
        result.append((fig, bonus))

    return result
