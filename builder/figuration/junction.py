"""Junction filter for bar-to-bar connection validation.

Validates that the final note of bar N connects idiomatically
to anchor N+1.
"""
from builder.figuration.types import Figure

# Scale degree interval that constitutes a 7th (ugly leap)
SEVENTH_INTERVAL: int = 6


def check_junction(
    figure: Figure,
    start_degree: int,
    next_anchor_degree: int,
) -> bool:
    """Check if figure connects idiomatically to next anchor.

    The final note of the figure must:
    - Approach next anchor by step (±1), OR
    - Share a common tone (same degree), OR
    - Be part of an acceptable leap pattern
    - NOT create a 7th leap (ugly)

    Args:
        figure: Figure to check
        start_degree: Starting degree of this figure (1-7)
        next_anchor_degree: Scale degree of next anchor (1-7)

    Returns:
        True if junction is valid.
    """
    final_absolute = _compute_absolute_degree(start_degree, figure.degrees[-1])
    penultimate_absolute = _compute_absolute_degree(start_degree, figure.degrees[-2])
    # Reject ugly 7th leaps
    if is_ugly_leap(final_absolute, next_anchor_degree):
        return False
    # Check stepwise approach
    if is_stepwise_approach(final_absolute, next_anchor_degree):
        return True
    # Check common tone
    if is_common_tone(final_absolute, next_anchor_degree):
        return True
    # Check acceptable leap
    if is_acceptable_leap(penultimate_absolute, final_absolute, next_anchor_degree):
        return True
    return False


def _compute_absolute_degree(start_degree: int, relative_offset: int) -> int:
    """Convert relative degree offset to absolute degree (1-7)."""
    absolute = start_degree + relative_offset
    while absolute < 1:
        absolute += 7
    while absolute > 7:
        absolute -= 7
    return absolute


def is_ugly_leap(from_degree: int, to_degree: int) -> bool:
    """Check if interval is an ugly 7th leap.

    Args:
        from_degree: Starting degree (1-7)
        to_degree: Ending degree (1-7)

    Returns:
        True if interval spans a 7th (6 scale steps).
    """
    interval = abs(to_degree - from_degree)
    # Also check wrapped interval (e.g., 1 to 7 = 6, but also 7 to 1 via wrap)
    wrapped = 7 - interval
    return interval == SEVENTH_INTERVAL or wrapped == SEVENTH_INTERVAL


def is_stepwise_approach(final_degree: int, next_degree: int) -> bool:
    """Check if final degree approaches next by step.

    Args:
        final_degree: Final degree of figure (absolute 1-7)
        next_degree: Next anchor degree (1-7)

    Returns:
        True if stepwise (±1 or unison).
    """
    interval = abs(next_degree - final_degree)
    # Stepwise means interval of 0 (unison) or 1 (second)
    # Also handle octave equivalence: 7 maps to unison
    return interval <= 1 or interval == 7


def is_common_tone(final_degree: int, next_degree: int) -> bool:
    """Check if final degree shares common tone with next.

    Args:
        final_degree: Final degree of figure (1-7)
        next_degree: Next anchor degree (1-7)

    Returns:
        True if same degree.
    """
    return final_degree == next_degree


def is_acceptable_leap(
    penultimate: int,
    final: int,
    next_degree: int,
) -> bool:
    """Check if leap pattern is acceptable.

    Acceptable leap patterns:
    - Leap followed by contrary stepwise motion
    - Leap within arpeggiated chord (third, fifth)
    - Octave leap

    Args:
        penultimate: Second-to-last degree (absolute)
        final: Final degree (absolute)
        next_degree: Next anchor degree

    Returns:
        True if leap pattern is acceptable.
    """
    # Check if it's a leap from penultimate to final
    leap_size = abs(final - penultimate)
    if leap_size <= 1:
        return True  # Not a leap, always acceptable
    # Leap from final to next must be compensated or acceptable
    interval_to_next = abs(next_degree - final)
    # Handle wrap-around
    if interval_to_next > 3:
        interval_to_next = 7 - interval_to_next
    # Acceptable if:
    # 1. Step back (contrary motion)
    if interval_to_next == 1:
        return True
    # 2. Third leap within arpeggio
    if interval_to_next == 2:
        return True
    # 3. Unison/octave
    if interval_to_next == 0:
        return True
    return False


def find_valid_figure(
    candidates: list[Figure],
    start_degree: int,
    next_anchor_degree: int,
) -> Figure | None:
    """Find first figure that passes junction check.

    Args:
        candidates: List of candidate figures (should be sorted by preference)
        start_degree: Starting degree for this bar
        next_anchor_degree: Degree of next anchor

    Returns:
        First valid figure, or None if all fail.
    """
    for figure in candidates:
        if check_junction(figure, start_degree, next_anchor_degree):
            return figure
    return None


