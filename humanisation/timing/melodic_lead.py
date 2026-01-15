"""Melodic lead timing model for humanisation.

Melody voice arrives slightly before accompaniment, a natural performance
practice documented in 18th-century performance treatises.
"""
from humanisation.context.types import NoteContext, TimingProfile


def compute_melodic_lead_offsets(
    contexts: list[NoteContext],
    profile: TimingProfile,
) -> list[float]:
    """Compute melodic lead timing offsets.

    Melody notes arrive early relative to accompaniment. The lead is
    reduced for fast passages (would sound sloppy) and increased at
    phrase starts (announcing the melody).

    Args:
        contexts: Analysis contexts for each note
        profile: Timing parameters

    Returns:
        List of timing offsets in seconds (negative = early)
    """
    if not contexts:
        return []

    offsets: list[float] = []
    base_lead_ms = profile.melodic_lead_ms

    for ctx in contexts:
        lead_ms = base_lead_ms

        # More lead at phrase starts (announcing)
        if ctx.phrase.position_in_phrase < 0.1:
            lead_ms += 5.0

        # Less lead in fast passages (short notes)
        if ctx.metric.beat_subdivision >= 8:  # Sixteenth notes or faster
            lead_ms *= 0.5

        if ctx.voice.is_melody:
            # Melody arrives early (negative offset)
            offset_seconds = -lead_ms / 1000.0
        else:
            # Non-melody arrives late (positive offset)
            # This ensures melody leads regardless of other timing adjustments
            offset_seconds = lead_ms / 1000.0

        offsets.append(offset_seconds)

    return offsets
