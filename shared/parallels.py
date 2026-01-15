"""Parallel motion detection: fifths and octaves.

This is the canonical implementation. All parallel detection code should use
these functions rather than duplicating the algorithm.

The core algorithm:
1. Both consecutive intervals must equal the target (7 for fifth, 0 for octave)
2. Both voices must move in the same direction (both ascending or both descending)
3. If either voice is stationary (motion == 0), it's NOT parallel motion
"""


def is_parallel_motion(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
    interval: int,
) -> bool:
    """Check if motion between two slices creates parallel motion at interval.

    Args:
        prev_upper: Previous upper voice MIDI pitch
        prev_lower: Previous lower voice MIDI pitch
        curr_upper: Current upper voice MIDI pitch
        curr_lower: Current lower voice MIDI pitch
        interval: Target interval in semitones mod 12 (7=fifth, 0=octave)

    Returns:
        True if parallel motion at the specified interval is detected.
    """
    prev_interval: int = (prev_upper - prev_lower) % 12
    curr_interval: int = (curr_upper - curr_lower) % 12
    if prev_interval != interval or curr_interval != interval:
        return False
    upper_motion: int = curr_upper - prev_upper
    lower_motion: int = curr_lower - prev_lower
    if upper_motion == 0 or lower_motion == 0:
        return False
    return (upper_motion > 0) == (lower_motion > 0)


def is_parallel_fifth(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
) -> bool:
    """Check for parallel fifths between two consecutive slices."""
    return is_parallel_motion(prev_upper, prev_lower, curr_upper, curr_lower, 7)


def is_parallel_octave(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
) -> bool:
    """Check for parallel octaves/unisons between two consecutive slices."""
    return is_parallel_motion(prev_upper, prev_lower, curr_upper, curr_lower, 0)


# =============================================================================
# Diatonic parallel detection (degree space)
# =============================================================================

def is_parallel_motion_diatonic(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
    interval: int,
) -> bool:
    """Check for parallel motion at interval in degree space.

    Args:
        prev_upper: Previous upper voice degree (1-7)
        prev_lower: Previous lower voice degree (1-7)
        curr_upper: Current upper voice degree (1-7)
        curr_lower: Current lower voice degree (1-7)
        interval: Target interval in degrees mod 7 (4=fifth, 0=octave/unison)

    Returns:
        True if parallel motion at the specified interval is detected.
    """
    prev_interval: int = (prev_upper - prev_lower) % 7
    curr_interval: int = (curr_upper - curr_lower) % 7
    if prev_interval != interval or curr_interval != interval:
        return False
    upper_motion: int = curr_upper - prev_upper
    lower_motion: int = curr_lower - prev_lower
    if upper_motion == 0 or lower_motion == 0:
        return False
    return (upper_motion > 0) == (lower_motion > 0)


def is_parallel_fifth_diatonic(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
) -> bool:
    """Check for parallel fifths in degree space (interval of 4 degrees)."""
    return is_parallel_motion_diatonic(prev_upper, prev_lower, curr_upper, curr_lower, 4)


def is_parallel_octave_diatonic(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
) -> bool:
    """Check for parallel octaves/unisons in degree space (interval of 0 mod 7)."""
    return is_parallel_motion_diatonic(prev_upper, prev_lower, curr_upper, curr_lower, 0)
