"""Melodic contour analyzer for humanisation."""
from engine.note import Note
from humanisation.context.types import MelodicContext


def analyze_melodic(notes: list[Note]) -> list[MelodicContext]:
    """Analyze melodic contour context for each note.

    Analyzes horizontal melodic relationships per voice:
    - Interval to previous note (semitones, signed)
    - Leap detection (interval > 2 semitones)
    - Peak/trough detection (local maxima/minima)
    - Contour direction (-1, 0, +1)

    Args:
        notes: List of Note objects

    Returns:
        List of MelodicContext, one per note
    """
    if not notes:
        return []

    # Group notes by track (voice)
    tracks: dict[int, list[tuple[int, Note]]] = {}
    for i, note in enumerate(notes):
        tracks.setdefault(note.track, []).append((i, note))

    # Sort each track by offset
    for track in tracks.values():
        track.sort(key=lambda x: x[1].Offset)

    # Build context for each note
    contexts: list[MelodicContext] = [None] * len(notes)  # type: ignore

    for track_notes in tracks.values():
        for idx, (note_idx, note) in enumerate(track_notes):
            # Get previous and next notes in same voice
            prev_note = track_notes[idx - 1][1] if idx > 0 else None
            next_note = track_notes[idx + 1][1] if idx < len(track_notes) - 1 else None

            # Compute interval from previous
            if prev_note is not None:
                interval_from_previous = note.midiNote - prev_note.midiNote
            else:
                interval_from_previous = 0

            # Detect leap (more than a whole step)
            is_leap = abs(interval_from_previous) > 2

            # Detect peak (higher than both neighbors)
            is_peak = False
            if prev_note is not None and next_note is not None:
                is_peak = (note.midiNote > prev_note.midiNote and
                          note.midiNote > next_note.midiNote)
            elif prev_note is not None and next_note is None:
                # Last note in phrase, could be peak if higher than previous
                is_peak = note.midiNote > prev_note.midiNote

            # Detect trough (lower than both neighbors)
            is_trough = False
            if prev_note is not None and next_note is not None:
                is_trough = (note.midiNote < prev_note.midiNote and
                            note.midiNote < next_note.midiNote)
            elif prev_note is not None and next_note is None:
                # Last note, could be trough if lower than previous
                is_trough = note.midiNote < prev_note.midiNote

            # Determine contour direction
            if interval_from_previous > 0:
                contour_direction = 1  # ascending
            elif interval_from_previous < 0:
                contour_direction = -1  # descending
            else:
                contour_direction = 0  # static

            contexts[note_idx] = MelodicContext(
                interval_from_previous=interval_from_previous,
                is_leap=is_leap,
                is_peak=is_peak,
                is_trough=is_trough,
                contour_direction=contour_direction,
            )

    # Handle any notes that weren't processed (shouldn't happen)
    for i in range(len(contexts)):
        if contexts[i] is None:
            contexts[i] = MelodicContext(
                interval_from_previous=0,
                is_leap=False,
                is_peak=False,
                is_trough=False,
                contour_direction=0,
            )

    return contexts
