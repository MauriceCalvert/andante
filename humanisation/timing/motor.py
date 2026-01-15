"""Motor model for humanisation.

Models physical constraints of human performance based on Fitts's Law
and keyboard biomechanics research.
"""
from engine.note import Note
from humanisation.context.types import NoteContext, TimingProfile


def compute_motor_offsets(
    notes: list[Note],
    contexts: list[NoteContext],
    profile: TimingProfile,
) -> list[float]:
    """Compute motor constraint timing offsets.

    Physical limitations affect timing:
    - Large intervals take longer to execute
    - Repeated notes may rush slightly
    - Voice leaps add time

    Args:
        notes: Original Note objects (needed for pitch info)
        contexts: Analysis contexts for each note
        profile: Timing parameters

    Returns:
        List of timing offsets in seconds
    """
    if not notes or not contexts:
        return []

    offsets: list[float] = []

    # Group notes by track for interval computation
    track_prev_pitch: dict[int, int] = {}

    for note, ctx in zip(notes, contexts):
        offset_ms = 0.0

        # Get previous pitch in same voice
        prev_pitch = track_prev_pitch.get(note.track)

        if prev_pitch is not None:
            interval = abs(note.midiNote - prev_pitch)

            # Large intervals (beyond octave) add time
            if interval > 12:
                # ~8ms per semitone beyond octave
                offset_ms += profile.motor_interval_coef * (interval - 12)

            # Very large leaps (beyond two octaves) add more
            if interval > 24:
                offset_ms += 15.0

            # Fast repeated notes: slight rush (drummer's rush effect)
            if interval == 0 and ctx.metric.beat_subdivision >= 8:
                offset_ms -= 5.0

        # Update previous pitch for this track
        track_prev_pitch[note.track] = note.midiNote

        # Convert to seconds
        offset_seconds = offset_ms / 1000.0

        offsets.append(offset_seconds)

    return offsets
