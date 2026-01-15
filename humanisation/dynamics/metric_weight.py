"""Metric weight dynamics model for humanisation.

Emphasizes strong beats with higher velocity.
"""
from humanisation.context.types import DynamicsProfile, NoteContext


def compute_metric_weight_offset(
    contexts: list[NoteContext],
    profile: DynamicsProfile,
) -> list[int]:
    """Compute velocity offset based on metric weight.

    Maps metric weight (0.0 to 1.0) to velocity offset range.

    Args:
        contexts: Analysis contexts for each note
        profile: Dynamics parameters

    Returns:
        List of velocity offsets (integers, can be negative)
    """
    if not contexts:
        return []

    offsets: list[int] = []
    weight_range = profile.metric_weight_range

    for ctx in contexts:
        # Map metric weight 0-1 to -range to +range
        weight = ctx.metric.metric_weight
        offset = int((weight - 0.5) * 2 * weight_range)
        offsets.append(offset)

    return offsets
