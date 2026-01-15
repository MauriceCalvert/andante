"""Touch variation dynamics model for humanisation.

Small random velocity variation for natural feel.
"""
import random

from humanisation.context.types import DynamicsProfile


def compute_touch_variation(
    note_count: int,
    profile: DynamicsProfile,
    seed: int,
) -> list[int]:
    """Compute random touch variation for each note.

    Pure random noise within the touch_variation range.
    This is the only stochastic component in dynamics.

    Args:
        note_count: Number of notes
        profile: Dynamics parameters
        seed: Random seed for reproducibility

    Returns:
        List of velocity offsets (integers)
    """
    if note_count == 0:
        return []

    rng = random.Random(seed)
    variation = profile.touch_variation

    return [rng.randint(-variation, variation) for _ in range(note_count)]
