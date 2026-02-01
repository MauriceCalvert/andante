"""Rhythmic realisation for figuration system.

Converts figure degree sequences into timed notes with proper durations.
Handles rhythm templates, augmentation, and hemiola.
"""
from fractions import Fraction

from builder.figuration.loader import get_hemiola_templates, get_rhythm_templates
from builder.figuration.rhythm_calc import compute_rhythmic_distribution
from builder.figuration.types import Figure, FiguredBar, RhythmTemplate


def get_rhythm_template(
    note_count: int,
    metre: str,
    overdotted: bool = False,
) -> RhythmTemplate | None:
    """Get rhythm template for given parameters.

    Args:
        note_count: Number of notes in figure
        metre: Time signature string (e.g., "3/4", "4/4")
        overdotted: Whether to use overdotted variant

    Returns:
        RhythmTemplate if found, None otherwise.
    """
    templates = get_rhythm_templates()
    key = (note_count, metre, overdotted)

    if key in templates:
        return templates[key]

    # Try standard if overdotted not available
    if overdotted:
        standard_key = (note_count, metre, False)
        if standard_key in templates:
            return templates[standard_key]

    return None


def get_hemiola_template(note_count: int, metre: str) -> RhythmTemplate | None:
    """Get hemiola-specific rhythm template.

    Args:
        note_count: Number of notes
        metre: Time signature

    Returns:
        RhythmTemplate for hemiola context, or None.
    """
    templates = get_hemiola_templates()
    key = (note_count, metre)
    return templates.get(key)


def beats_to_whole_notes(beats: Fraction, metre: str) -> Fraction:
    """Convert beat-based duration to whole note duration.

    Args:
        beats: Duration in beats
        metre: Time signature

    Returns:
        Duration in whole notes.
    """
    parts = metre.split("/")
    denom = int(parts[1])

    # One beat = 1/denom of a whole note
    return beats * Fraction(1, denom)


def generate_default_durations(note_count: int, bar_duration: Fraction) -> tuple[Fraction, ...]:
    """Generate evenly distributed durations when no template available.

    Args:
        note_count: Number of notes
        bar_duration: Total duration of bar

    Returns:
        Tuple of equal durations summing to bar_duration.
    """
    single_duration = bar_duration / note_count
    return tuple(single_duration for _ in range(note_count))


def realise_rhythm_baroque(
    gap_duration: Fraction,
    density: str,
) -> tuple[Fraction, ...]:
    """Realise rhythm using Bach's approach: density->unit, gap->count.

    Args:
        gap_duration: Available duration for the figure (in whole notes)
        density: Density level ("low", "medium", "high")

    Returns:
        Tuple of equal durations that sum to gap_duration.
        All durations are valid baroque values (1/4, 1/8, 1/16, 1/32).
    """
    note_count, unit = compute_rhythmic_distribution(gap_duration, density)
    return tuple(unit for _ in range(note_count))


def _adjust_degrees_to_count(degrees: list[int], target_count: int) -> list[int]:
    """Adjust degree list to match target count with no repeated notes.

    Bach's rule: at fast subdivisions, every note is different.
    Uses scalar excursions (go somewhere, return) not oscillation (trill).
    Preserves extended degree range (no wrapping to 1-7).

    Args:
        degrees: Extended degrees (can be <1 or >7)
        target_count: Desired number of degrees

    Returns:
        New list of extended degrees with target_count elements, no adjacent repeats.
    """
    if target_count <= 0:
        return [degrees[0]] if degrees else [1]
    if target_count == 1:
        return [degrees[0]] if degrees else [1]
    if len(degrees) == 0:
        return _scalar_run_extended(1, target_count, 1)
    if len(degrees) == 1:
        return _scalar_excursion_extended(degrees[0], target_count)
    result: list[int] = []
    segments = len(degrees) - 1
    notes_per_segment = target_count // segments
    extra = target_count % segments
    for seg in range(segments):
        start_deg = degrees[seg]
        end_deg = degrees[seg + 1]
        seg_count = notes_per_segment + (1 if seg < extra else 0)
        if seg_count == 0:
            continue
        is_last = (seg == segments - 1)
        prev = result[-1] if result else None
        seg_notes = _fill_segment_extended(start_deg, end_deg, seg_count, is_last, prev)
        result.extend(seg_notes)
    while len(result) < target_count:
        result.append(result[-1] + 1)
    return result[:target_count]


def _scalar_run_extended(start: int, count: int, direction: int) -> list[int]:
    """Generate a scalar run, bounded within ±7 of start."""
    low_bound = start - 7
    high_bound = start + 7
    result = [start]
    current = start
    for _ in range(count - 1):
        next_val = current + direction
        if next_val > high_bound or next_val < low_bound:
            direction = -direction
            next_val = current + direction
        current = next_val
        result.append(current)
    return result


def _scalar_excursion_extended(base: int, count: int) -> list[int]:
    """Generate symmetric scalar excursion from base returning to base.

    Climbs half the distance, then descends back. No leaps > 2 degrees.
    """
    if count == 1:
        return [base]
    if count == 2:
        return [base, base + 1]
    if count == 3:
        return [base, base + 1, base]
    half = (count - 1) // 2
    result = [base]
    for i in range(1, half + 1):
        result.append(base + i)
    peak = result[-1]
    remaining = count - len(result)
    for i in range(remaining):
        step_down = peak - 1 - i
        if step_down < base:
            step_down = base
        result.append(step_down)
    while len(result) < count:
        result.append(base)
    return result[:count]


def _fill_segment_extended(
    start: int,
    end: int,
    count: int,
    must_end: bool,
    prev: int | None,
) -> list[int]:
    """Fill segment with scalar motion ensuring stepwise landing.

    Produces exactly `count` notes. If must_end, last note is `end`.
    Maximum leap is 2 degrees (a third). Reserves final notes for stepwise approach.
    """
    MAX_LEAP = 2
    if count <= 0:
        return []
    low_bound = start - 7
    high_bound = start + 7
    target = max(low_bound, min(high_bound, end))
    if count == 1:
        return [target if must_end else start]
    current = start
    if prev is not None and current == prev:
        current = current + 1 if current + 1 <= high_bound else current - 1
    if count == 2:
        if must_end:
            if abs(target - current) <= MAX_LEAP:
                return [current, target]
            approach = current + (1 if target > current else -1)
            return [approach, target]
        return [current, current + 1]
    if start == end:
        return _symmetric_excursion(current, count, low_bound, high_bound)
    distance = target - current
    direction = 1 if distance > 0 else -1
    steps_needed = abs(distance)
    if steps_needed <= count - 1:
        return _direct_stepwise_path(current, target, count, direction, low_bound, high_bound)
    return _excursion_then_approach(current, target, count, direction, low_bound, high_bound)


def _symmetric_excursion(start: int, count: int, low: int, high: int) -> list[int]:
    """Generate symmetric excursion returning to start."""
    half = (count - 1) // 2
    result = [start]
    direction = 1 if start + half <= high else -1
    current = start
    for _ in range(half):
        next_val = current + direction
        if next_val > high or next_val < low:
            direction = -direction
            next_val = current + direction
        current = next_val
        result.append(current)
    while len(result) < count - 1:
        next_val = current - direction
        if next_val > high or next_val < low:
            direction = -direction
            next_val = current - direction
        current = next_val
        result.append(current)
    if abs(current - start) > 2:
        while abs(current - start) > 1 and len(result) < count - 1:
            current = current + (1 if start > current else -1)
            result.append(current)
    result.append(start)
    return result[:count]


def _direct_stepwise_path(
    start: int,
    target: int,
    count: int,
    direction: int,
    low: int,
    high: int,
) -> list[int]:
    """Fill with stepwise motion when we have enough notes."""
    result = [start]
    current = start
    notes_to_target = abs(target - current)
    spare_notes = count - 1 - notes_to_target
    excursion_budget = spare_notes // 2
    opp_direction = -direction
    for _ in range(excursion_budget):
        next_val = current + opp_direction
        if low <= next_val <= high:
            current = next_val
            result.append(current)
    while len(result) < count - 1:
        next_val = current + direction
        if next_val > high or next_val < low:
            break
        current = next_val
        result.append(current)
    while len(result) < count - 1:
        current = current + (1 if target > current else -1)
        result.append(current)
    result.append(target)
    return result[:count]


def _excursion_then_approach(
    start: int,
    target: int,
    count: int,
    direction: int,
    low: int,
    high: int,
) -> list[int]:
    """When target is far, excurse then approach stepwise."""
    APPROACH_RESERVE = 3
    result = [start]
    current = start
    excursion_notes = count - APPROACH_RESERVE
    opp_direction = -direction
    for _ in range(excursion_notes - 1):
        next_val = current + opp_direction
        if next_val > high or next_val < low:
            opp_direction = -opp_direction
            next_val = current + opp_direction
        current = next_val
        result.append(current)
    while len(result) < count - 1:
        step = 1 if target > current else -1
        current = current + step
        result.append(current)
    result.append(target)
    return result[:count]



def realise_rhythm(
    figure: Figure,
    gap_duration: Fraction,
    metre: str,
    bar_function: str,
    rhythmic_unit: Fraction,
    next_anchor_strength: str,
    use_hemiola: bool = False,
    overdotted: bool = False,
) -> tuple[Fraction, ...]:
    """Realise rhythm for a figure.

    Args:
        figure: Figure to realise
        gap_duration: Available duration for the figure (in whole notes)
        metre: Time signature
        bar_function: Bar function (passing, preparatory, cadential, schema_arrival)
        rhythmic_unit: Genre's characteristic note value
        next_anchor_strength: Strength of next anchor (weak, strong)
        use_hemiola: Whether to use hemiola rhythms
        overdotted: Whether to use overdotted rhythms

    Returns:
        Tuple of durations in whole notes.
    """
    note_count = len(figure.degrees)

    # Try hemiola template first if requested
    if use_hemiola:
        hemiola_template = get_hemiola_template(note_count, metre)
        if hemiola_template:
            durations = tuple(
                beats_to_whole_notes(d, metre) for d in hemiola_template.durations
            )
            return _scale_to_gap(durations, gap_duration)

    # Try standard template
    template = get_rhythm_template(note_count, metre, overdotted)

    if template:
        durations = tuple(
            beats_to_whole_notes(d, metre) for d in template.durations
        )
        return _scale_to_gap(durations, gap_duration)

    # Fallback: even distribution
    return generate_default_durations(note_count, gap_duration)


def _scale_to_gap(durations: tuple[Fraction, ...], gap_duration: Fraction) -> tuple[Fraction, ...]:
    """Scale durations to fit exactly within gap duration.

    Args:
        durations: Original durations
        gap_duration: Target total duration

    Returns:
        Scaled durations summing to gap_duration.
    """
    total = sum(durations)
    if total == 0:
        return durations

    scale_factor = gap_duration / total
    return tuple(d * scale_factor for d in durations)


def realise_figure_to_bar(
    figure: Figure,
    bar: int,
    start_degree: int,
    gap_duration: Fraction,
    metre: str,
    bar_function: str = "passing",
    rhythmic_unit: Fraction = Fraction(1, 4),
    next_anchor_strength: str = "strong",
    use_hemiola: bool = False,
    overdotted: bool = False,
    start_beat: int = 1,
    density: str = "medium",
    use_baroque_rhythm: bool = False,
) -> FiguredBar:
    """Realise a figure into a FiguredBar with extended degrees and durations."""
    # Convert relative degrees to extended degrees (NO WRAPPING)
    extended_degrees: list[int] = []
    for relative_degree in figure.degrees:
        extended = start_degree + relative_degree
        extended_degrees.append(extended)
    # Get rhythm durations
    if use_baroque_rhythm:
        durations = realise_rhythm_baroque(gap_duration, density)
        # Adjust degrees to match duration count
        if len(durations) != len(extended_degrees):
            extended_degrees = _adjust_degrees_to_count(
                extended_degrees, len(durations)
            )
    else:
        durations = realise_rhythm(
            figure=figure,
            gap_duration=gap_duration,
            metre=metre,
            bar_function=bar_function,
            rhythmic_unit=rhythmic_unit,
            next_anchor_strength=next_anchor_strength,
            use_hemiola=use_hemiola,
            overdotted=overdotted,
        )
    return FiguredBar(
        bar=bar,
        degrees=tuple(extended_degrees),
        durations=durations,
        figure_name=figure.name,
        start_beat=start_beat,
    )


