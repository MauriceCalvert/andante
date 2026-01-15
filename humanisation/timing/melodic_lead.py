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
        if not ctx.voice.is_melody:
            # Non-melody voices don't get lead
            offsets.append(0.0)
            continue

        lead_ms = base_lead_ms

        # More lead at phrase starts (announcing)
        if ctx.phrase.position_in_phrase < 0.1:
            lead_ms += 5.0

        # Less lead in fast passages (short notes)
        # We don't have direct access to duration here, so use metric subdivision
        if ctx.metric.beat_subdivision >= 8:  # Sixteenth notes or faster
            lead_ms *= 0.5

        # Convert to seconds and make negative (early)
        offset_seconds = -lead_ms / 1000.0

        offsets.append(offset_seconds)

    return offsets
