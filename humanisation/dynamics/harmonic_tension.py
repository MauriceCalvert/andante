"""Harmonic tension dynamics model for humanisation.

Dissonances are emphasized with higher velocity.
"""
from humanisation.context.types import DynamicsProfile, NoteContext


def compute_harmonic_tension_offset(
    contexts: list[NoteContext],
    profile: DynamicsProfile,
) -> list[int]:
    """Compute velocity offset based on harmonic tension.

    - Dissonances get velocity boost (lean in)
    - Resolutions get velocity reduction (release)

    Args:
        contexts: Analysis contexts for each note
        profile: Dynamics parameters

    Returns:
        List of velocity offsets (integers)
    """
    if not contexts:
        return []

    offsets: list[int] = []
    max_boost = profile.harmonic_tension_boost

    for ctx in contexts:
        offset = 0

        # Dissonances: louder based on tension level
        if ctx.harmonic.tension > 0.3:
            offset += int(ctx.harmonic.tension * max_boost)

        # Resolutions: softer
        if ctx.harmonic.is_resolution:
            offset -= 8

        # Prepared dissonances (suspensions): extra emphasis
        if ctx.harmonic.is_prepared_dissonance:
            offset += 4

        offsets.append(offset)

    return offsets
