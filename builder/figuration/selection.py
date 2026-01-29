"""Figure selection logic."""
import random

from builder.figuration.types import Figure
from shared.constants import MISBEHAVIOUR_PROBABILITY


def apply_misbehaviour(
    figures: list[Figure],
    all_figures_for_interval: list[Figure],
    seed: int,
    probability: float = MISBEHAVIOUR_PROBABILITY,
) -> list[Figure]:
    """Apply controlled misbehaviour by occasionally relaxing filters.

    With small probability, this allows figures that would normally be filtered.
    This prevents over-regular, textbook surfaces.

    Args:
        figures: List of filtered figures
        all_figures_for_interval: Unfiltered figures for this interval
        seed: RNG seed for determinism
        probability: Probability of misbehaviour (default 5%)

    Returns:
        Possibly expanded figure list.
    """
    if not figures:
        return figures
    rng = random.Random(seed)
    if rng.random() < probability and all_figures_for_interval:
        # Misbehaviour: return all figures for this interval, ignoring filters
        return list(all_figures_for_interval)
    return figures


def sort_by_weight(figures: list[Figure]) -> list[Figure]:
    """Sort figures by weight (descending) then name (alphabetical).

    Deterministic ordering ensures reproducible selection.

    Args:
        figures: List of figures to sort

    Returns:
        Sorted figure list.
    """
    return sorted(figures, key=lambda f: (-f.weight, f.name))


def select_figure(
    figures: list[Figure],
    seed: int,
    weight_overrides: list[float] | None = None,
) -> Figure | None:
    """Select a figure using seeded weighted random selection.

    Args:
        figures: List of candidate figures (should be sorted)
        seed: RNG seed for determinism
        weight_overrides: Optional list of weights to use instead of f.weight.
                          Must be same length as figures if provided.

    Returns:
        Selected figure, or None if no candidates.
    """
    if not figures:
        return None
    if weight_overrides is not None:
        assert len(weight_overrides) == len(figures), "weight_overrides length mismatch"
        weights = weight_overrides
    else:
        weights = [f.weight for f in figures]
    rng = random.Random(seed)
    total_weight = sum(weights)
    if total_weight <= 0:
        return figures[0] if figures else None
    r = rng.random() * total_weight
    cumulative = 0.0
    for fig, w in zip(figures, weights):
        cumulative += w
        if r <= cumulative:
            return fig
    return figures[-1]
