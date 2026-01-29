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


def apply_augmentation(template: RhythmTemplate, factor: int) -> RhythmTemplate:
    """Apply augmentation to rhythm template.

    Args:
        template: Original rhythm template
        factor: Augmentation factor (2 for double, etc.)

    Returns:
        New RhythmTemplate with scaled durations.
    """
    assert factor > 0, f"Augmentation factor must be positive, got {factor}"

    scaled_durations = tuple(d * factor for d in template.durations)

    return RhythmTemplate(
        note_count=template.note_count,
        metre=template.metre,
        durations=scaled_durations,
        overdotted=template.overdotted,
    )


def apply_diminution(template: RhythmTemplate, factor: int) -> RhythmTemplate:
    """Apply diminution to rhythm template.

    Args:
        template: Original rhythm template
        factor: Diminution factor (2 for half, etc.)

    Returns:
        New RhythmTemplate with scaled durations.
    """
    assert factor > 0, f"Diminution factor must be positive, got {factor}"

    scaled_durations = tuple(d / factor for d in template.durations)

    return RhythmTemplate(
        note_count=template.note_count,
        metre=template.metre,
        durations=scaled_durations,
        overdotted=template.overdotted,
    )


def compute_bar_duration(metre: str) -> Fraction:
    """Compute duration of one bar in whole notes.

    Args:
        metre: Time signature string (e.g., "3/4", "4/4")

    Returns:
        Bar duration as Fraction.
    """
    parts = metre.split("/")
    assert len(parts) == 2, f"Invalid metre format: {metre}"

    num = int(parts[0])
    denom = int(parts[1])

    return Fraction(num, denom)


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

    Args:
        degrees: Original absolute degrees (1-7)
        target_count: Desired number of degrees

    Returns:
        New list of degrees with target_count elements, no adjacent repeats.
    """
    if target_count <= 0:
        return [degrees[0]] if degrees else [1]
    if target_count == 1:
        return [_wrap(degrees[0])]
    if len(degrees) == 0:
        return _scalar_run(1, target_count, 1)
    if len(degrees) == 1:
        return _scalar_excursion(degrees[0], target_count)
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
        seg_notes = _fill_segment(start_deg, end_deg, seg_count, is_last, prev)
        result.extend(seg_notes)
    while len(result) < target_count:
        result.append(_step_from(result[-1], 1))
    return result[:target_count]


def _wrap(d: int) -> int:
    """Wrap degree to 1-7 range."""
    return ((d - 1) % 7) + 1


def _step_from(current: int, direction: int) -> int:
    """Step from current in direction, guaranteed different from current."""
    return _wrap(current + direction)


def _scalar_run(start: int, count: int, direction: int) -> list[int]:
    """Generate a scalar run in one direction."""
    result = [_wrap(start)]
    current = start
    for _ in range(count - 1):
        current = current + direction
        result.append(_wrap(current))
    return result


def _scalar_excursion(base: int, count: int) -> list[int]:
    """Generate scalar excursion from base: go up, return to base.

    For unison fills - NOT a trill, but an excursion.
    Example: base=3, count=4 -> [3, 4, 5, 3] (up, up, skip back)
    """
    base = _wrap(base)
    if count == 1:
        return [base]
    if count == 2:
        return [base, _wrap(base + 1)]
    # Go up for count-1 notes, then skip back to base
    result = [base]
    current = base
    for i in range(count - 2):
        current = current + 1
        result.append(_wrap(current))
    # Final note: return to base (skip back)
    result.append(base)
    return result


def _fill_segment(
    start: int,
    end: int,
    count: int,
    must_end: bool,
    prev: int | None,
) -> list[int]:
    """Fill segment with scalar motion. No repeats, no trills.

    Strategy:
    - Walk toward end
    - If more notes needed than distance allows, overshoot PAST end, then land on end
    - Never oscillate (that's a trill)
    """
    if count <= 0:
        return []
    start = _wrap(start)
    end = _wrap(end)
    first = start if (prev is None or start != prev) else _step_from(start, 1)
    if count == 1:
        return [first]
    result = [first]
    current = first
    if start == end:
        direction = 1
        distance = 0
    else:
        direction = 1 if end > start else -1
        distance = abs(end - start)
    notes_to_place = count - 1  # Already placed first
    if must_end:
        notes_to_place -= 1  # Reserve last slot for end
    # How many notes do we have vs how many steps to reach end?
    # If notes_to_place > distance: we must overshoot
    # If notes_to_place == distance: walk exactly to end (but then can't place end again if must_end)
    # If notes_to_place < distance: take big steps (rare)
    if must_end and notes_to_place == distance:
        # Edge case: would arrive exactly at end, but we reserved a slot for end
        # Solution: walk to one-before-end, overshoot past end, land on end
        # Walk distance-1 steps
        for _ in range(distance - 1):
            current = current + direction
            result.append(_wrap(current))
        # Overshoot (past end)
        current = current + direction + direction  # Skip over end
        result.append(_wrap(current))
        # Land on end
        result.append(end)
    else:
        # Normal case: walk toward end, overshoot if needed
        steps_taken = 0
        while notes_to_place > 0 and steps_taken < distance:
            current = current + direction
            result.append(_wrap(current))
            notes_to_place -= 1
            steps_taken += 1
        # Overshoot if more notes needed
        while notes_to_place > 0:
            current = current + direction
            result.append(_wrap(current))
            notes_to_place -= 1
        # Land on end if required
        if must_end:
            result.append(end)
    return result


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
    """Realise a figure into a FiguredBar with absolute degrees and durations.

    Args:
        figure: Figure to realise
        bar: Bar number
        start_degree: Starting scale degree (1-7)
        gap_duration: Duration to fill
        metre: Time signature
        bar_function: Function of this bar
        rhythmic_unit: Characteristic note value
        next_anchor_strength: Strength of following anchor
        use_hemiola: Use hemiola rhythms
        overdotted: Use overdotted rhythms
        start_beat: Beat on which this voice enters (1=lead, 2=accompany)
        density: Density level for baroque rhythm ("low", "medium", "high")
        use_baroque_rhythm: Use Bach-style power-of-2 durations

    Returns:
        FiguredBar with absolute degrees and durations.
    """
    # Convert relative degrees to absolute degrees
    absolute_degrees: list[int] = []
    for relative_degree in figure.degrees:
        # Degrees are 1-7, relative offsets are added
        absolute = start_degree + relative_degree
        # Wrap to 1-7 range
        while absolute < 1:
            absolute += 7
        while absolute > 7:
            absolute -= 7
        absolute_degrees.append(absolute)

    # Get rhythm durations
    if use_baroque_rhythm:
        durations = realise_rhythm_baroque(gap_duration, density)
        # Adjust degrees to match duration count
        if len(durations) != len(absolute_degrees):
            absolute_degrees = _adjust_degrees_to_count(
                absolute_degrees, len(durations)
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
        degrees=tuple(absolute_degrees),
        durations=durations,
        figure_name=figure.name,
        start_beat=start_beat,
    )


def compute_gap_duration(
    anchor_offset_a: Fraction,
    anchor_offset_b: Fraction,
) -> Fraction:
    """Compute gap duration between two anchors.

    Args:
        anchor_offset_a: Offset of first anchor (whole notes)
        anchor_offset_b: Offset of second anchor (whole notes)

    Returns:
        Duration of gap between anchors.
    """
    gap = anchor_offset_b - anchor_offset_a
    assert gap > 0, f"Gap must be positive: {anchor_offset_a} to {anchor_offset_b}"
    return gap


def is_anacrusis_beat(
    beat_position: Fraction,
    metre: str,
    next_anchor_strength: str,
) -> bool:
    """Check if current beat is an anacrusis to next bar.

    In 3/4, beat 3 can be anacrusis when next anchor is strong.

    Args:
        beat_position: Position within bar (0 = beat 1)
        metre: Time signature
        next_anchor_strength: Strength of next anchor

    Returns:
        True if this is an anacrusis position.
    """
    if next_anchor_strength != "strong":
        return False

    if metre == "3/4":
        # Beat 3 in 3/4 is anacrusis when next is strong
        return beat_position >= Fraction(1, 2)
    elif metre == "4/4":
        # Beat 4 in 4/4 can be anacrusis
        return beat_position >= Fraction(3, 4)

    return False
