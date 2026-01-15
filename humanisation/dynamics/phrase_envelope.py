"""Phrase envelope dynamics model for humanisation.

Bell curve shaping: mf at start, f at peak, p at end.
"""
import math

from humanisation.context.types import DynamicsProfile, NoteContext


def compute_phrase_envelope(
    contexts: list[NoteContext],
    profile: DynamicsProfile,
) -> list[float]:
    """Compute phrase envelope velocity multiplier for each note.

    Creates a bell curve across each phrase:
    - Start: ~0.85 multiplier (mf)
    - Peak: ~1.15 multiplier (f)
    - End: ~0.75 multiplier (p)

    The strength parameter controls how pronounced this curve is.

    Args:
        contexts: Analysis contexts for each note
        profile: Dynamics parameters

    Returns:
        List of velocity multipliers (0.5 to 1.5 range)
    """
    if not contexts:
        return []

    multipliers: list[float] = []
    peak_pos = profile.phrase_peak_position
    strength = profile.phrase_envelope_strength

    for ctx in contexts:
        pos = ctx.phrase.position_in_phrase

        if pos < peak_pos:
            # Rising phase: 0.85 -> 1.15
            t = pos / peak_pos
            # Smooth sine curve
            base_mult = 0.85 + 0.30 * math.sin(t * math.pi / 2)
        else:
            # Falling phase: 1.15 -> 0.75
            t = (pos - peak_pos) / (1.0 - peak_pos)
            base_mult = 1.15 - 0.40 * math.sin(t * math.pi / 2)

        # Apply strength scaling (blend toward 1.0)
        multiplier = 1.0 + (base_mult - 1.0) * strength

        multipliers.append(multiplier)

    return multipliers
