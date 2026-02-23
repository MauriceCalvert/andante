"""Generic scoring utilities."""
import math


def _shannon_entropy(counts: list[int], total: int) -> float:
    """Normalised Shannon entropy, 0..1."""
    if total == 0 or len(counts) <= 1:
        return 0.0
    max_ent = math.log(len(counts))
    if max_ent == 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log(p)
    return ent / max_ent


def _closeness(value: float, target: float, width: float) -> float:
    """Gaussian closeness score, 1.0 at target."""
    return math.exp(-((value - target) ** 2) / (2 * width * width))
