"""Articulation engine for humanisation.

Modifies note durations for expressive articulation.
"""
from engine.note import Note
from humanisation.context.types import HumanisationProfile, NoteContext
from humanisation.articulation.duration import compute_duration_factor


def apply_articulation(
    notes: list[Note],
    contexts: list[NoteContext],
    profile: HumanisationProfile,
) -> list[Note]:
    """Apply articulation model to adjust note durations.

    Note: This applies AFTER the existing 95% gate time from L013.
    The factors here multiply the already-shortened duration.

    Args:
        notes: Note objects
        contexts: Analysis contexts for each note
        profile: Humanisation profile

    Returns:
        New list of Note objects with adjusted Duration
    """
    if not notes:
        return []

    articulation = profile.articulation

    result: list[Note] = []
    for note, ctx in zip(notes, contexts):
        factor = compute_duration_factor(note, ctx, articulation)

        # Apply factor
        new_duration = note.Duration * factor

        # Ensure minimum duration (avoid zero-length notes)
        new_duration = max(0.01, new_duration)

        # Create new note with adjusted duration
        new_note = Note(
            midiNote=note.midiNote,
            Offset=note.Offset,
            Duration=new_duration,
            track=note.track,
            Length=note.Length,
            bar=note.bar,
            beat=note.beat,
            lyric=note.lyric,
            velocity=note.velocity,
        )
        result.append(new_note)

    return result
