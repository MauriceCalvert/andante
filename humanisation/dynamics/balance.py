"""Voice balance dynamics model for humanisation.

Melody and thematic material are emphasized.
"""
from humanisation.context.types import DynamicsProfile, NoteContext


def compute_balance_offset(
    contexts: list[NoteContext],
    profile: DynamicsProfile,
) -> list[int]:
    """Compute velocity offset for voice balance.

    - Melody voice gets boost
    - Thematic material (subject, countersubject) gets boost
    - Both are cumulative

    Args:
        contexts: Analysis contexts for each note
        profile: Dynamics parameters

    Returns:
        List of velocity offsets (integers)
    """
    if not contexts:
        return []

    offsets: list[int] = []
    melody_boost = profile.voice_balance_melody
    thematic_boost = profile.voice_balance_thematic

    for ctx in contexts:
        offset = 0

        if ctx.voice.is_melody:
            offset += melody_boost

        if ctx.voice.is_thematic:
            offset += thematic_boost

        offsets.append(offset)

    return offsets
