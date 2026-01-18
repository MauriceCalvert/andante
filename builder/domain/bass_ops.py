"""Bass generation operations.

Category A: Pure functions, no validation, no I/O.
Assumes all inputs are valid — validation happens in orchestrators.

Functions:
    compute_degree        — Convert Roman numeral to scale degree
    compute_harmonic_bass — Generate bass pattern for a chord
    compute_diatonic_bass — Convert degrees to diatonic bass pitches
"""
from fractions import Fraction

from builder.types import Notes


def compute_degree(roman: str, tonal_roots: dict[str, int]) -> int:
    """Convert Roman numeral to scale degree (1-7).

    Args:
        roman: Roman numeral like "I", "V", "vi"
        tonal_roots: Mapping from Roman to degree

    Returns:
        Scale degree 1-7
    """
    return tonal_roots[roman]


def compute_harmonic_bass(
    root: int,
    intervals: tuple[int, ...],
    durations: tuple[Fraction, ...],
) -> Notes:
    """Generate harmonic bass pattern for a chord.

    Args:
        root: Root scale degree (1-7)
        intervals: Interval offsets from root (e.g., (0, 4) for root and fifth)
        durations: Duration for each note

    Returns:
        Notes with degrees and durations
    """
    pitches: tuple[int, ...] = tuple(
        ((root - 1 + interval) % 7) + 1 for interval in intervals
    )
    return Notes(pitches, durations)


def compute_diatonic_bass(notes: Notes, base_octave: int) -> Notes:
    """Convert scale degrees to diatonic pitch values.

    Args:
        notes: Notes with scale degrees (1-7) as pitches
        base_octave: Base octave (4 for bass = diatonic 21)

    Returns:
        Notes with diatonic pitch values
    """
    diatonic: tuple[int, ...] = tuple(
        base_octave * 7 + ((d - 1) % 7) for d in notes.pitches
    )
    return Notes(diatonic, notes.durations)
