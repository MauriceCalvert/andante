"""Rhythmic realisation for figuration system.

Converts figure degree sequences into timed notes with proper durations.
Handles rhythm templates, augmentation, and hemiola.
"""
from fractions import Fraction

from builder.figuration.loader import get_hemiola_templates, get_rhythm_templates
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
