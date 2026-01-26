"""Junction filter for bar-to-bar connection validation.

Validates that the final note of bar N connects idiomatically
to anchor N+1.
"""
from builder.figuration.types import Figure


def check_junction(figure: Figure, next_anchor_degree: int) -> bool:
    """Check if figure connects idiomatically to next anchor.

    The penultimate note of the figure must:
    - Approach next anchor by step (±1), OR
    - Share a common tone (same degree), OR
    - Be part of an acceptable leap pattern

    Args:
        figure: Figure to check
        next_anchor_degree: Scale degree of next anchor (1-7)

    Returns:
        True if junction is valid.
    """
    # Note: Figure type guarantees at least 2 degrees

    # Get the penultimate and final degrees of the figure
    # Note: degrees are relative offsets, need to compute absolute
    penultimate_relative = figure.degrees[-2]
    final_relative = figure.degrees[-1]

    # The final degree should equal or approach the next anchor
    # Since degrees are relative, we check the approach pattern

    # Check stepwise approach
    if is_stepwise_approach(final_relative, next_anchor_degree):
        return True

    # Check common tone
    if is_common_tone(final_relative, next_anchor_degree):
        return True

    # Check acceptable leap
    if is_acceptable_leap(penultimate_relative, final_relative, next_anchor_degree):
        return True

    return False


def is_stepwise_approach(final_degree: int, next_degree: int) -> bool:
    """Check if final degree approaches next by step.

    Args:
        final_degree: Final degree of figure (relative)
        next_degree: Next anchor degree

    Returns:
        True if stepwise (±1).
    """
    # For relative degrees approaching an absolute degree,
    # we check if the motion would be stepwise
    # This is a simplification; actual check needs context

    # If final_degree is 0 (returns to start), check against next
    interval = abs(next_degree - final_degree)
    return interval <= 1 or interval >= 6  # Step or near-octave


def is_common_tone(final_degree: int, next_degree: int) -> bool:
    """Check if final degree shares common tone with next.

    Args:
        final_degree: Final degree of figure
        next_degree: Next anchor degree

    Returns:
        True if same degree (modulo octave).
    """
    # Same degree = common tone
    return (final_degree % 7) == (next_degree % 7) or final_degree == next_degree


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
        penultimate: Second-to-last degree
        final: Final degree
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

    # Acceptable if:
    # 1. Step back (contrary motion)
    if interval_to_next == 1:
        return True

    # 2. Third leap within arpeggio
    if interval_to_next == 2:
        return True

    # 3. Fifth leap (chord outline)
    if interval_to_next == 4:
        return True

    # 4. Octave (common in baroque)
    if interval_to_next == 7:
        return True

    return False


def find_valid_figure(
    candidates: list[Figure],
    next_anchor_degree: int,
) -> Figure | None:
    """Find first figure that passes junction check.

    Args:
        candidates: List of candidate figures (should be sorted by preference)
        next_anchor_degree: Degree of next anchor

    Returns:
        First valid figure, or None if all fail.
    """
    for figure in candidates:
        if check_junction(figure, next_anchor_degree):
            return figure
    return None


def compute_junction_penalty(
    figure: Figure,
    next_anchor_degree: int,
) -> float:
    """Compute penalty score for junction quality.

    Lower penalty = better junction.

    Args:
        figure: Figure to evaluate
        next_anchor_degree: Next anchor degree

    Returns:
        Penalty score (0.0 = perfect, higher = worse).
    """
    if len(figure.degrees) < 2:
        return 0.0

    final = figure.degrees[-1]
    interval = abs(next_anchor_degree - final)

    # Step = no penalty
    if interval <= 1:
        return 0.0

    # Common tone = no penalty
    if is_common_tone(final, next_anchor_degree):
        return 0.0

    # Third = small penalty
    if interval == 2:
        return 0.1

    # Fourth = medium penalty
    if interval == 3:
        return 0.3

    # Fifth = medium penalty (acceptable in arpeggios)
    if interval == 4:
        return 0.2

    # Larger leaps = higher penalty
    return 0.5 + (interval - 5) * 0.1


def validate_figure_sequence(
    figures: list[Figure],
    anchor_degrees: list[int],
) -> list[tuple[int, str]]:
    """Validate junction points in a sequence of figures.

    Args:
        figures: List of figures for consecutive bars
        anchor_degrees: List of anchor degrees (one more than figures)

    Returns:
        List of (bar_index, error_message) for failed junctions.
    """
    errors: list[tuple[int, str]] = []

    assert len(anchor_degrees) >= len(figures), \
        "Need at least as many anchor degrees as figures"

    for i, figure in enumerate(figures):
        next_degree = anchor_degrees[i + 1] if i + 1 < len(anchor_degrees) else anchor_degrees[-1]

        if not check_junction(figure, next_degree):
            errors.append((
                i,
                f"Bar {i + 1}: figure '{figure.name}' doesn't connect to degree {next_degree}",
            ))

    return errors


def suggest_alternative(
    figure: Figure,
    next_anchor_degree: int,
    candidates: list[Figure],
) -> Figure | None:
    """Suggest alternative figure with better junction.

    Args:
        figure: Current figure that failed junction
        next_anchor_degree: Next anchor degree
        candidates: Other candidate figures

    Returns:
        Alternative figure, or None if no better option.
    """
    # Find candidates that pass junction
    valid = [f for f in candidates if check_junction(f, next_anchor_degree)]

    if not valid:
        return None

    # Prefer figures with similar character
    same_character = [f for f in valid if f.character == figure.character]
    if same_character:
        return same_character[0]

    # Otherwise return first valid
    return valid[0]
