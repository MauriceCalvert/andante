"""Fortspinnung sequencer for figuration system.

Handles motivic coherence across bars through:
- Sequential transposition of figures
- Rule of Three (maximum 2 repetitions before break)
- Fragmentation for breaking sequences
- Melodic rhyme detection
"""
from builder.figuration.types import Figure


def transpose_figure(figure: Figure, interval: int) -> Figure:
    """Transpose a figure by a scale degree interval.

    Creates a new figure with degrees offset by the interval.
    The figure shape is preserved; only the starting point changes.

    Args:
        figure: Original figure
        interval: Transposition interval in scale degrees (positive = up)

    Returns:
        New Figure with transposed degrees.
    """
    # Transpose all degrees by the interval
    transposed_degrees = tuple(d + interval for d in figure.degrees)

    return Figure(
        name=f"{figure.name}_t{interval:+d}",
        degrees=transposed_degrees,
        contour=figure.contour,
        polarity=figure.polarity,
        arrival=figure.arrival,
        placement=figure.placement,
        character=figure.character,
        harmonic_tension=figure.harmonic_tension,
        max_density=figure.max_density,
        cadential_safe=figure.cadential_safe,
        repeatable=figure.repeatable,
        requires_compensation=figure.requires_compensation,
        compensation_direction=figure.compensation_direction,
        is_compound=figure.is_compound,
        minor_safe=figure.minor_safe,
        requires_leading_tone=figure.requires_leading_tone,
        weight=figure.weight,
    )


def fragment_figure(figure: Figure) -> Figure:
    """Fragment a figure by taking only the first motif.

    Fragmentation takes approximately the first half of the figure's
    degrees, preserving the opening gesture while shortening.

    Args:
        figure: Original figure

    Returns:
        Fragmented figure with fewer notes.
    """
    degrees = figure.degrees
    fragment_length = max(2, len(degrees) // 2)
    fragmented_degrees = degrees[:fragment_length]

    return Figure(
        name=f"{figure.name}_frag",
        degrees=fragmented_degrees,
        contour=f"{figure.contour}_fragment",
        polarity=figure.polarity,
        arrival=figure.arrival,
        placement="start",  # Fragments typically start phrases
        character=figure.character,
        harmonic_tension=figure.harmonic_tension,
        max_density=figure.max_density,
        cadential_safe=False,  # Fragments shouldn't end cadences
        repeatable=True,
        requires_compensation=figure.requires_compensation,
        compensation_direction=figure.compensation_direction,
        is_compound=figure.is_compound,
        minor_safe=figure.minor_safe,
        requires_leading_tone=figure.requires_leading_tone,
        weight=figure.weight * 0.8,  # Slightly lower weight for fragments
    )


