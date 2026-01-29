"""Rhythmic calculation for baroque durations.

Bach's approach: density determines rhythmic unit, gap determines note count.
Only power-of-2 durations are valid: 1/4, 1/8, 1/16, 1/32.
"""
from fractions import Fraction

# Valid baroque durations in descending order
VALID_UNITS: tuple[Fraction, ...] = (
    Fraction(1, 4),   # quarter
    Fraction(1, 8),   # eighth
    Fraction(1, 16),  # sixteenth
    Fraction(1, 32),  # thirty-second (rare)
)

# Density to preferred rhythmic unit
DENSITY_TO_UNIT: dict[str, Fraction] = {
    "low": Fraction(1, 4),
    "medium": Fraction(1, 8),
    "high": Fraction(1, 16),
}


def compute_rhythmic_distribution(
    gap: Fraction,
    density: str,
) -> tuple[int, Fraction]:
    """Compute note count and duration for a gap.

    Args:
        gap: Duration to fill (in whole notes)
        density: "low", "medium", or "high"

    Returns:
        (note_count, duration_each) where duration_each is a valid baroque value.
        All notes get the same duration. note_count * duration_each == gap.
    """
    preferred_unit = DENSITY_TO_UNIT.get(density, Fraction(1, 8))
    # Try preferred unit first
    count = gap / preferred_unit
    if count == int(count) and count >= 1:
        return (int(count), preferred_unit)
    # Preferred doesn't divide evenly - try LARGER units first (sparser is better than denser)
    for unit in VALID_UNITS:
        if unit <= preferred_unit:
            continue  # Already tried preferred, skip smaller/equal
        count = gap / unit
        if count == int(count) and count >= 1:
            return (int(count), unit)
    # Still no match - try smaller units (denser)
    for unit in VALID_UNITS:
        if unit >= preferred_unit:
            continue  # Already tried preferred and larger
        count = gap / unit
        if count == int(count) and count >= 1:
            return (int(count), unit)
    # Last resort: single note for entire gap
    return (1, gap)


def is_valid_duration(d: Fraction) -> bool:
    """Check if duration is a valid baroque value (power of 2)."""
    # Valid if denominator is power of 2 and numerator is 1
    if d.numerator != 1:
        return False
    denom = d.denominator
    return denom > 0 and (denom & (denom - 1)) == 0


def quantize_duration(d: Fraction) -> Fraction:
    """Quantize a duration to nearest valid baroque value.

    Used as fallback when other methods produce invalid durations.
    """
    if is_valid_duration(d):
        return d
    # Find nearest valid unit
    best = VALID_UNITS[0]
    best_diff = abs(d - best)
    for unit in VALID_UNITS[1:]:
        diff = abs(d - unit)
        if diff < best_diff:
            best = unit
            best_diff = diff
    return best
