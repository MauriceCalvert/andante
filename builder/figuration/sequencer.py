"""Fortspinnung sequencer for figuration system.

Handles motivic coherence across bars through:
- Sequential transposition of figures
- Rule of Three (maximum 2 repetitions before break)
- Fragmentation for breaking sequences
- Melodic rhyme detection
"""
from dataclasses import dataclass

from builder.figuration.types import Figure
from shared.constants import MAX_SEQUENCE_REPETITIONS


@dataclass
class SequencerState:
    """State for tracking sequential repetitions.

    Tracks how many times a figure has been repeated in sequence
    and the transposition interval.
    """
    current_figure: Figure | None = None
    repetition_count: int = 0
    transposition_interval: int = 0
    last_start_degree: int = 1

    def reset(self) -> None:
        """Reset sequencer state."""
        self.current_figure = None
        self.repetition_count = 0
        self.transposition_interval = 0
        self.last_start_degree = 1


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


def should_break_sequence(repetition_count: int) -> bool:
    """Check if sequence should be broken (Rule of Three).

    Sequences should repeat at most MAX_SEQUENCE_REPETITIONS times
    before being broken via fragmentation or new material.

    Args:
        repetition_count: Current repetition count (0-indexed)

    Returns:
        True if sequence should be broken.
    """
    return repetition_count >= MAX_SEQUENCE_REPETITIONS


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


def compute_transposition_interval(
    from_degree: int,
    to_degree: int,
) -> int:
    """Compute transposition interval between two target degrees.

    Args:
        from_degree: Starting degree
        to_degree: Target degree

    Returns:
        Interval in scale degrees.
    """
    return to_degree - from_degree


def apply_fortspinnung(
    initial_figure: Figure,
    target_degrees: list[int],
    state: SequencerState,
) -> list[Figure]:
    """Apply Fortspinnung (spinning out) to generate sequential figures.

    Takes an initial figure and spins it out across multiple bars,
    transposing to target degrees and applying Rule of Three.

    Args:
        initial_figure: Figure to spin out
        target_degrees: List of target degrees for each bar
        state: Sequencer state for tracking

    Returns:
        List of figures for each bar.
    """
    if not target_degrees:
        return []

    figures: list[Figure] = []
    current_figure = initial_figure
    state.current_figure = initial_figure
    state.last_start_degree = target_degrees[0]

    for i, target in enumerate(target_degrees):
        if i == 0:
            # First bar: use initial figure
            figures.append(current_figure)
            state.repetition_count = 0
        else:
            # Compute transposition from previous bar
            prev_target = target_degrees[i - 1]
            interval = compute_transposition_interval(prev_target, target)

            # Check Rule of Three
            if should_break_sequence(state.repetition_count):
                # Break with fragmentation
                current_figure = fragment_figure(current_figure)
                state.repetition_count = 0

            # Transpose figure and update current for next iteration
            transposed = transpose_figure(current_figure, interval)
            figures.append(transposed)
            current_figure = transposed  # Accumulate transpositions
            state.repetition_count += 1

        state.last_start_degree = target

    return figures


def detect_melodic_rhyme(
    bar_5_figure: Figure,
    bar_1_figure: Figure,
    transposition: int = 4,
) -> bool:
    """Detect if bar 5 is a melodic rhyme of bar 1.

    In Ponte schema, bar 5 often restates bar 1 figure transposed
    to the dominant (up a 4th/5th).

    Args:
        bar_5_figure: Figure in bar 5
        bar_1_figure: Figure in bar 1
        transposition: Expected transposition (default 4 = dominant)

    Returns:
        True if melodic rhyme detected.
    """
    # Check if figures have same shape (ignoring transposition)
    if len(bar_5_figure.degrees) != len(bar_1_figure.degrees):
        return False

    # Check if relative motion is the same
    bar_1_relative = _compute_relative_motion(bar_1_figure.degrees)
    bar_5_relative = _compute_relative_motion(bar_5_figure.degrees)

    if bar_1_relative != bar_5_relative:
        return False

    # Check if transposition matches expected
    first_1 = bar_1_figure.degrees[0]
    first_5 = bar_5_figure.degrees[0]

    return (first_5 - first_1) == transposition


def _compute_relative_motion(degrees: tuple[int, ...]) -> tuple[int, ...]:
    """Compute relative motion between consecutive degrees.

    Args:
        degrees: Sequence of degrees

    Returns:
        Tuple of intervals between consecutive degrees.
    """
    if len(degrees) < 2:
        return ()

    return tuple(degrees[i + 1] - degrees[i] for i in range(len(degrees) - 1))


def create_sequence_figures(
    base_figure: Figure,
    sequence_count: int,
    direction: str,
    step_size: int = 1,
) -> list[Figure]:
    """Create a series of sequenced figures.

    Generates figures for a rising or falling sequence pattern.

    Args:
        base_figure: Starting figure
        sequence_count: Number of figures in sequence
        direction: "ascending" or "descending"
        step_size: Scale degree step between sequence members

    Returns:
        List of transposed figures.
    """
    assert sequence_count >= 1, "sequence_count must be >= 1"
    assert direction in ("ascending", "descending"), f"Invalid direction: {direction}"

    figures: list[Figure] = [base_figure]
    interval_step = step_size if direction == "ascending" else -step_size
    cumulative_interval = 0

    for i in range(1, sequence_count):
        cumulative_interval += interval_step
        transposed = transpose_figure(base_figure, cumulative_interval)
        figures.append(transposed)

    return figures


def accelerate_to_cadence(
    figure: Figure,
    remaining_bars: int,
) -> list[Figure]:
    """Generate accelerating fragments toward cadence.

    Takes a figure and creates increasingly fragmented versions
    to build momentum toward a cadential point.

    Args:
        figure: Starting figure
        remaining_bars: Bars remaining until cadence

    Returns:
        List of increasingly fragmented figures.
    """
    if remaining_bars <= 0:
        return []

    figures: list[Figure] = []
    current = figure

    for i in range(remaining_bars):
        # Progressive fragmentation
        if i > 0 and len(current.degrees) > 2:
            current = fragment_figure(current)
        figures.append(current)

    return figures
