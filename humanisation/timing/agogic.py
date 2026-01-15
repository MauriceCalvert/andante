"""Agogic accent timing model for humanisation.

Micro-delays on important beats create emphasis through anticipation.
"""
from humanisation.context.types import NoteContext, TimingProfile


def compute_agogic_offsets(
    contexts: list[NoteContext],
    profile: TimingProfile,
) -> list[float]:
    """Compute agogic accent timing offsets.

    Important notes arrive slightly late (10-40ms), creating emphasis.
    Syncopated notes arrive slightly early (anticipation).

    Args:
        contexts: Analysis contexts for each note
        profile: Timing parameters

    Returns:
        List of timing offsets in seconds (positive = late, negative = early)
    """
    if not contexts:
        return []

    offsets: list[float] = []

    for ctx in contexts:
        offset_ms = 0.0

        # Downbeat emphasis
        if ctx.metric.is_downbeat:
            offset_ms += profile.agogic_downbeat_ms

        # Phrase peak emphasis
        if abs(ctx.phrase.distance_to_peak) < 0.05:  # At or very near peak
            offset_ms += profile.agogic_peak_ms

        # Syncopation: arrive early (anticipation)
        if ctx.metric.is_syncopation:
            offset_ms += profile.agogic_syncopation_ms  # Typically negative

        # Melodic peak/arrival after leap gets slight emphasis
        if ctx.melodic.is_peak or ctx.melodic.is_leap:
            offset_ms += 5.0  # Small additional delay

        # Convert to seconds
        offset_seconds = offset_ms / 1000.0

        offsets.append(offset_seconds)

    return offsets
