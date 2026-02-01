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
from builder.figuration.loader import get_diminutions
from builder.figuration.selection import apply_misbehaviour, select_figure, sort_by_weight
from builder.figuration.types import Figure, PhrasePosition, SelectionContext
from builder.types import Anchor
from shared.constants import (
    DIRECT_MOTION_STEP_THRESHOLD,
    FIGURATION_INTERVALS,
    PERFECT_INTERVALS,
    UGLY_LEAP_SEMITONES,
)


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


MAX_EXPANSION_RATIO: float = 3.0  # Maximum allowed expansion of figure degrees


def filter_by_note_count(
    figures: list[Figure],
    required_count: int,
    max_expansion: float = MAX_EXPANSION_RATIO,
) -> list[Figure]:
    """Filter figures that can produce required note count without extreme expansion.

    Non-chainable figures: must have enough degrees that expansion ratio stays
    within bounds. A 4-degree figure expanded to 12 (3×) is acceptable.
    A 2-degree figure expanded to 16 (8×) is not.

    Chainable figures: can tile their chain_unit to reach any count, so always
    acceptable if they have max_density=high.

    Args:
        figures: List of figures to filter
        required_count: Number of notes needed
        max_expansion: Maximum allowed expansion ratio (default 3.0)

    Returns:
        Figures that can produce required count acceptably.
    """
    if not figures or required_count <= 0:
        return figures

    min_degrees = max(2, int(required_count / max_expansion))

    result: list[Figure] = []
    for fig in figures:
        if fig.chainable:
            # Chainable figures can tile to any count
            result.append(fig)
        elif fig.note_count >= min_degrees:
            # Non-chainable must have enough degrees
            result.append(fig)

    return result if result else figures


def _compute_max_internal_leap(degrees: tuple[int, ...]) -> int:
    """Compute largest interval between adjacent degrees in semitones.

    Approximates semitones from scale degrees:
    - Each scale degree step averages ~2 semitones
    - This is a heuristic; actual intervals depend on mode
    """
    if len(degrees) < 2:
        return 0
    max_leap: int = 0
    for i in range(len(degrees) - 1):
        # Approximate: each scale degree difference ≈ 2 semitones average
        # This is conservative; minor 2nds (1 semitone) are treated as 2
        leap = abs(degrees[i + 1] - degrees[i]) * 2
        max_leap = max(max_leap, leap)
    return max_leap


def filter_by_max_leap(
    figures: list[Figure],
    max_leap_semitones: int = UGLY_LEAP_SEMITONES,
) -> list[Figure]:
    """Remove figures with internal leaps exceeding threshold.

    This prevents ugly melodic intervals like minor 7ths within figures.

    Args:
        figures: List of figures to filter
        max_leap_semitones: Maximum allowed internal leap (default: minor 7th - 1)

    Returns:
        Figures with acceptable internal leaps. Soft filter: returns original
        if all would be filtered.
    """
    if not figures:
        return []

    result: list[Figure] = []
    for fig in figures:
        max_leap = _compute_max_internal_leap(fig.degrees)
        if max_leap <= max_leap_semitones:
            result.append(fig)

    # Soft filter: return original if all filtered out
    return result if result else figures


def _degree_to_semitone_approx(degree: int, start_midi: int) -> int:
    """Approximate MIDI pitch from scale degree offset.

    Uses major scale intervals for approximation:
    degree 0 = 0, 1 = 2, 2 = 4, 3 = 5, 4 = 7, 5 = 9, 6 = 11, 7 = 12
    """
    # Major scale semitone offsets for degrees 0-7
    major_offsets = [0, 2, 4, 5, 7, 9, 11, 12]
    octaves = degree // 7
    remainder = degree % 7
    if remainder < 0:
        octaves -= 1
        remainder += 7
    semitones = octaves * 12 + major_offsets[remainder]
    return start_midi + semitones


CROSS_RELATION_INTERVALS: frozenset[int] = frozenset({1, 11, 13, 23})


def would_create_cross_relation(
    soprano_degrees: tuple[int, ...],
    bass_degrees: tuple[int, ...],
    soprano_start_midi: int,
    bass_start_midi: int,
) -> bool:
    """Check if bass figure would create cross-relation with soprano.

    A cross-relation occurs when one voice has a pitch that is a minor 2nd
    (1 semitone) or minor 9th (13 semitones) from a concurrent pitch in
    the other voice. E.g., A natural in bass against Bb in soprano.

    Checks all pairs of pitches since figures may have different rhythmic
    densities and concurrent notes may not align by index.

    Args:
        soprano_degrees: Soprano figure degrees (relative to start)
        bass_degrees: Bass candidate degrees (relative to start)
        soprano_start_midi: Soprano starting MIDI pitch
        bass_start_midi: Bass starting MIDI pitch

    Returns:
        True if bass candidate would create cross-relation.
    """
    if not soprano_degrees or not bass_degrees:
        return False
    soprano_pitches: set[int] = set()
    for d in soprano_degrees:
        pitch = _degree_to_semitone_approx(d, soprano_start_midi)
        soprano_pitches.add(pitch)
    for d in bass_degrees:
        b_pitch = _degree_to_semitone_approx(d, bass_start_midi)
        for s_pitch in soprano_pitches:
            interval = abs(b_pitch - s_pitch)
            if interval in CROSS_RELATION_INTERVALS:
                return True
    return False


def filter_cross_relation(
    figures: list[Figure],
    soprano_degrees: tuple[int, ...] | None,
    soprano_start_midi: int,
    bass_start_midi: int,
) -> list[Figure]:
    """Filter bass figures that would create cross-relations with soprano.

    Args:
        figures: Bass figure candidates
        soprano_degrees: Soprano figure degrees (None if not available)
        soprano_start_midi: Soprano starting MIDI pitch
        bass_start_midi: Bass starting MIDI pitch

    Returns:
        Filtered figures. Soft filter: returns original if all filtered.
    """
    if not figures or soprano_degrees is None:
        return figures
    result: list[Figure] = []
    for fig in figures:
        if not would_create_cross_relation(
            soprano_degrees, fig.degrees, soprano_start_midi, bass_start_midi
        ):
            result.append(fig)
    return result if result else figures


def would_create_parallel_or_direct(
    soprano_degrees: tuple[int, ...],
    bass_degrees: tuple[int, ...],
    soprano_start_midi: int,
    bass_start_midi: int,
) -> bool:
    """Check if bass figure would create parallel or direct fifths/octaves.

    Parallel: Both voices move in similar motion maintaining the same perfect
    interval (unison, fifth, or octave).

    Direct: Similar motion arrives at a perfect interval where soprano leaps
    (> 2 semitones).

    Args:
        soprano_degrees: Soprano figure degrees (relative to start)
        bass_degrees: Bass candidate degrees (relative to start)
        soprano_start_midi: Soprano starting MIDI pitch
        bass_start_midi: Bass starting MIDI pitch

    Returns:
        True if bass candidate would create forbidden motion.
    """
    min_len = min(len(soprano_degrees), len(bass_degrees))
    if min_len < 2:
        return False

    for i in range(min_len - 1):
        # Convert degrees to approximate MIDI pitches
        s1 = _degree_to_semitone_approx(soprano_degrees[i], soprano_start_midi)
        s2 = _degree_to_semitone_approx(soprano_degrees[i + 1], soprano_start_midi)
        b1 = _degree_to_semitone_approx(bass_degrees[i], bass_start_midi)
        b2 = _degree_to_semitone_approx(bass_degrees[i + 1], bass_start_midi)

        interval1 = abs(s1 - b1) % 12
        interval2 = abs(s2 - b2) % 12

        s_delta = s2 - s1
        b_delta = b2 - b1

        # Skip if not similar motion (one stationary or contrary motion)
        if s_delta == 0 or b_delta == 0:
            continue
        if (s_delta > 0) != (b_delta > 0):
            continue

        # Check parallel: same perfect interval maintained
        if interval1 in PERFECT_INTERVALS and interval1 == interval2:
            return True

        # Check direct: arrive at perfect interval with soprano leap
        if interval2 in PERFECT_INTERVALS:
            if abs(s_delta) > DIRECT_MOTION_STEP_THRESHOLD:
                return True

    return False


def filter_parallel_direct(
    figures: list[Figure],
    soprano_degrees: tuple[int, ...] | None,
    soprano_start_midi: int,
    bass_start_midi: int,
) -> list[Figure]:
    """Filter bass figures that would create parallel/direct fifths or octaves.

    Args:
        figures: Bass figure candidates
        soprano_degrees: Soprano figure degrees (None if not available)
        soprano_start_midi: Soprano starting MIDI pitch
        bass_start_midi: Bass starting MIDI pitch

    Returns:
        Filtered figures. Soft filter: returns original if all filtered.
    """
    if not figures or soprano_degrees is None:
        return figures

    result: list[Figure] = []
    for fig in figures:
        if not would_create_parallel_or_direct(
            soprano_degrees, fig.degrees, soprano_start_midi, bass_start_midi
        ):
            result.append(fig)

    return result if result else figures


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
