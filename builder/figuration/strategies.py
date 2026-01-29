"""Schema-aware figuration strategies.

Each schema type has characteristic melodic idioms. This module provides
strategy functions that generate figure sequences appropriate to each schema.

Strategies:
- accelerating: Build energy, fragment near end, momentum toward next section
- relaxing: Release tension, gradual simplification
- static: Repeated/pedal figures for prolongation
- dyadic: Two contrasting gestures

Profiles (from figuration_profiles.yaml):
- Define preferred pattern names per schema type
- Used to weight/filter figure selection
"""
from builder.figuration.types import Figure
from builder.figuration.sequencer import (
    fragment_figure,
    transpose_figure,
)


# Schema to strategy mapping
SCHEMA_STRATEGIES: dict[str, str] = {
    "monte": "accelerating",
    "fonte": "relaxing",
    "ponte": "static",
    "meyer": "dyadic",
    "fenaroli": "accelerating",
    "prinner": "relaxing",
    "romanesca": "relaxing",
    "do_re_mi": "repeating",
    "cadenza_semplice": "static",
    "cadenza_composta": "relaxing",
}

# Schema to figuration profile mapping
# Profiles determine WHAT patterns; strategies determine HOW to sequence them
SCHEMA_PROFILES: dict[str, str] = {
    "monte": "sequence_ascending",
    "fonte": "sequence_descending",
    "ponte": "repeated_tone",
    "meyer": "stepwise_mixed",
    "fenaroli": "galant_general",
    "prinner": "stepwise_descent",
    "romanesca": "stepwise_mixed",
    "do_re_mi": "stepwise_ascent",
    "sol_fa_mi": "stepwise_descent",
    "cadenza_semplice": "galant_general",
    "cadenza_composta": "stepwise_descent",
    "quiescenza": "pedal",
    "indugio": "repeated_tone",
    "passo_indietro": "stepwise_descent",
}

# Default strategy for unknown schemas
DEFAULT_STRATEGY: str = "repeating"
DEFAULT_PROFILE: str = "galant_general"


def get_strategy_for_schema(schema_name: str) -> str:
    """Get the figuration strategy for a schema type."""
    return SCHEMA_STRATEGIES.get(schema_name.lower(), DEFAULT_STRATEGY)


def get_profile_for_schema(schema_name: str) -> str:
    """Get the figuration profile for a schema type."""
    return SCHEMA_PROFILES.get(schema_name.lower(), DEFAULT_PROFILE)


def apply_strategy(
    strategy: str,
    initial_figure: Figure,
    target_degrees: list[int],
    direction: str | None = None,
) -> list[Figure]:
    """Apply a figuration strategy to generate figure sequence.

    Args:
        strategy: Strategy name (accelerating, relaxing, static, dyadic, repeating)
        initial_figure: Base figure to work with
        target_degrees: Target degrees for each bar
        direction: Schema direction (up/down) if known

    Returns:
        List of figures, one per target degree.
    """
    if not target_degrees:
        return []
    if strategy == "accelerating":
        return _apply_accelerating(initial_figure, target_degrees)
    elif strategy == "relaxing":
        return _apply_relaxing(initial_figure, target_degrees)
    elif strategy == "static":
        return _apply_static(initial_figure, target_degrees)
    elif strategy == "dyadic":
        return _apply_dyadic(initial_figure, target_degrees)
    else:
        return _apply_repeating(initial_figure, target_degrees)


def _apply_accelerating(
    initial_figure: Figure,
    target_degrees: list[int],
) -> list[Figure]:
    """Accelerating strategy for monte-like schemas.

    Pattern:
    - Bars 1-2: Full figure, transposed
    - Bar 3+: Fragment, increasing fragmentation
    - Final bar: Minimal fragment (launch pad for next section)
    """
    figures: list[Figure] = []
    n = len(target_degrees)
    base_degree = target_degrees[0]
    current_figure = initial_figure
    # Determine when to start fragmenting (after 2 repetitions, or earlier if short)
    fragment_start = min(2, max(1, n - 2))
    for i, target in enumerate(target_degrees):
        interval = target - base_degree
        if i == 0:
            figures.append(initial_figure)
        elif i < fragment_start:
            # Full figure, transposed
            if interval == 0:
                figures.append(current_figure)
            else:
                figures.append(transpose_figure(initial_figure, interval))
        else:
            # Fragment phase - progressive fragmentation
            if i == fragment_start:
                current_figure = fragment_figure(initial_figure)
            elif i > fragment_start and len(current_figure.degrees) > 2:
                current_figure = fragment_figure(current_figure)
            if interval == 0:
                figures.append(current_figure)
            else:
                figures.append(transpose_figure(current_figure, interval))
    return figures


def _apply_relaxing(
    initial_figure: Figure,
    target_degrees: list[int],
) -> list[Figure]:
    """Relaxing strategy for fonte-like schemas.

    Pattern:
    - Start with full figure
    - Gradual simplification throughout
    - Less aggressive fragmentation than accelerating
    """
    figures: list[Figure] = []
    n = len(target_degrees)
    base_degree = target_degrees[0]
    current_figure = initial_figure
    for i, target in enumerate(target_degrees):
        interval = target - base_degree
        # Fragment only in second half, and gently
        if i > 0 and i >= n // 2 and len(current_figure.degrees) > 3:
            current_figure = _gentle_fragment(current_figure)
        if interval == 0:
            figures.append(current_figure)
        else:
            figures.append(transpose_figure(current_figure, interval))
    return figures


def _apply_static(
    initial_figure: Figure,
    target_degrees: list[int],
) -> list[Figure]:
    """Static strategy for ponte-like schemas (pedal prolongation).

    Pattern:
    - Repeat same figure with minimal variation
    - No fragmentation
    - Suitable for dominant pedals
    """
    figures: list[Figure] = []
    base_degree = target_degrees[0]
    for i, target in enumerate(target_degrees):
        interval = target - base_degree
        if interval == 0:
            figures.append(initial_figure)
        else:
            figures.append(transpose_figure(initial_figure, interval))
    return figures


def _apply_dyadic(
    initial_figure: Figure,
    target_degrees: list[int],
) -> list[Figure]:
    """Dyadic strategy for meyer-like schemas (two contrasting gestures).

    Pattern:
    - Alternates between two figure variants
    - First dyad: initial figure
    - Second dyad: contrasting variant (inverted or fragmented)
    """
    figures: list[Figure] = []
    n = len(target_degrees)
    base_degree = target_degrees[0]
    # Create contrasting variant for second dyad
    contrast_figure = _create_contrast(initial_figure)
    midpoint = n // 2
    for i, target in enumerate(target_degrees):
        interval = target - base_degree
        # Use initial figure for first half, contrast for second half
        if i < midpoint:
            base = initial_figure
        else:
            base = contrast_figure
        if interval == 0:
            figures.append(base)
        else:
            figures.append(transpose_figure(base, interval))
    return figures


def _apply_repeating(
    initial_figure: Figure,
    target_degrees: list[int],
) -> list[Figure]:
    """Default repeating strategy - simple transposition with Rule of Three.

    Pattern:
    - Transpose figure to each target
    - Fragment after 2 repetitions (Rule of Three)
    """
    figures: list[Figure] = []
    base_degree = target_degrees[0]
    current_figure = initial_figure
    repetition_count = 0
    for i, target in enumerate(target_degrees):
        interval = target - base_degree
        if i == 0:
            figures.append(initial_figure)
            repetition_count = 0
        else:
            # Rule of Three
            if repetition_count >= 2:
                current_figure = fragment_figure(current_figure)
                repetition_count = 0
            if interval == 0:
                figures.append(current_figure)
            else:
                figures.append(transpose_figure(current_figure, interval))
            repetition_count += 1
    return figures


def _gentle_fragment(figure: Figure) -> Figure:
    """Create a gentle fragment - removes only the last note or two."""
    degrees = figure.degrees
    if len(degrees) <= 3:
        return figure
    # Remove last note only
    new_length = len(degrees) - 1
    fragmented_degrees = degrees[:new_length]
    return Figure(
        name=f"{figure.name}_trim",
        degrees=fragmented_degrees,
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


def _create_contrast(figure: Figure) -> Figure:
    """Create a contrasting variant of a figure.

    For dyadic schemas, the second gesture should contrast with the first.
    This creates a variant with inverted contour direction.
    """
    degrees = figure.degrees
    if len(degrees) < 2:
        return figure
    # Invert the relative motion around the first note
    first = degrees[0]
    inverted = [first]
    for i in range(1, len(degrees)):
        motion = degrees[i] - degrees[i - 1]
        inverted.append(inverted[-1] - motion)  # Invert the motion
    return Figure(
        name=f"{figure.name}_inv",
        degrees=tuple(inverted),
        contour=f"{figure.contour}_inverted",
        polarity="lower" if figure.polarity == "upper" else "upper" if figure.polarity == "lower" else "balanced",
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
        weight=figure.weight * 0.9,
    )
