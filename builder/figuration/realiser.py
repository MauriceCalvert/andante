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
    """Generate scalar excursion from base, bounded within ±7.

    Goes up then returns to base. Reverses if hitting bounds.
    """
    if count == 1:
        return [base]
    if count == 2:
        return [base, base + 1]
    low_bound = base - 7
    high_bound = base + 7
    result = [base]
    current = base
    direction = 1
    for _ in range(count - 2):
        next_val = current + direction
        if next_val > high_bound or next_val < low_bound:
            direction = -direction
            next_val = current + direction
        current = next_val
        result.append(current)
    result.append(base)
    return result


def _fill_segment_extended(
    start: int,
    end: int,
    count: int,
    must_end: bool,
    prev: int | None,
) -> list[int]:
    """Fill segment with scalar motion. No consecutive duplicates.

    Produces exactly `count` notes, bounded within ±7 of start.
    If must_end, last note is `end` (clamped to bounds).
    """
    if count <= 0:
        return []
    low_bound = start - 7
    high_bound = start + 7
    target = max(low_bound, min(high_bound, end))
    if count == 1:
        return [target if must_end else start]
    # Build path
    result: list[int] = []
    current = start
    if prev is not None and current == prev:
        current = current + 1 if current + 1 <= high_bound else current - 1
    result.append(current)
    direction = 1 if target >= current else -1
    for i in range(count - 1):
        adding_last = (i == count - 2)
        adding_second_to_last = (i == count - 3)
        if adding_last and must_end:
            current = target
        else:
            next_val = current + direction
            if next_val > high_bound or next_val < low_bound:
                direction = -direction
                next_val = current + direction
            # If adding second-to-last and must_end, avoid landing on target
            if adding_second_to_last and must_end and next_val == target:
                alt = target + direction
                if low_bound <= alt <= high_bound:
                    next_val = alt
                else:
                    next_val = target - direction
            current = next_val
        result.append(current)
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
