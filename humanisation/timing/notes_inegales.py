"""Notes Inégales timing model for humanisation.

French baroque performance practice where paired notes (typically eighths)
are played unequally: long-short. Only applies to stepwise motion.
"""
from dataclasses import dataclass

from engine.note import Note
from humanisation.context.types import ArticulationProfile, NoteContext


@dataclass
class InegalesAdjustment:
    """Duration and offset adjustment for notes inégales."""

    note_index: int
    offset_delta: float  # Change to onset time
    duration_delta: float  # Change to duration


def _is_stepwise(pitch1: int, pitch2: int) -> bool:
    """Check if interval is stepwise (within 2 semitones)."""
    return abs(pitch1 - pitch2) <= 2


def _find_eligible_pairs(
    notes: list[Note],
    contexts: list[NoteContext],
    threshold: float,
) -> list[tuple[int, int]]:
    """Find pairs of notes eligible for notes inégales.

    Eligibility criteria:
    1. Same voice (track)
    2. Consecutive in time
    3. Both short notes (duration <= threshold)
    4. Stepwise motion between them
    5. On weak-strong beat pattern

    Args:
        notes: Original Note objects
        contexts: Analysis contexts
        threshold: Max duration for eligibility

    Returns:
        List of (first_index, second_index) tuples
    """
    pairs: list[tuple[int, int]] = []

    # Group by track
    track_notes: dict[int, list[tuple[int, Note, NoteContext]]] = {}
    for i, (note, ctx) in enumerate(zip(notes, contexts)):
        track_notes.setdefault(note.track, []).append((i, note, ctx))

    # Sort each track by offset
    for track_list in track_notes.values():
        track_list.sort(key=lambda x: x[1].Offset)

        # Find consecutive pairs
        for j in range(len(track_list) - 1):
            idx1, note1, ctx1 = track_list[j]
            idx2, note2, ctx2 = track_list[j + 1]

            # Check duration threshold
            if note1.Duration > threshold or note2.Duration > threshold:
                continue

            # Check they're consecutive (no gap)
            expected_end = note1.Offset + note1.Duration
            if abs(expected_end - note2.Offset) > 0.01:
                continue

            # Check stepwise motion
            if not _is_stepwise(note1.midiNote, note2.midiNote):
                continue

            # Check same duration (paired notes)
            if abs(note1.Duration - note2.Duration) > 0.01:
                continue

            pairs.append((idx1, idx2))

    return pairs


def compute_notes_inegales(
    notes: list[Note],
    contexts: list[NoteContext],
    profile: ArticulationProfile,
) -> list[InegalesAdjustment]:
    """Compute notes inégales adjustments.

    Transforms pairs of equal short notes into long-short patterns.
    The ratio determines how unequal: 1.5 means 60%-40% split,
    2.0 means 67%-33% split.

    Args:
        notes: Original Note objects
        contexts: Analysis contexts
        profile: Articulation parameters (ratio and threshold)

    Returns:
        List of adjustments for affected notes
    """
    ratio = profile.notes_inegales_ratio
    threshold = profile.notes_inegales_threshold

    if ratio <= 1.0 or ratio > 3.0:
        # Disabled or invalid ratio
        return []

    adjustments: list[InegalesAdjustment] = []

    pairs = _find_eligible_pairs(notes, contexts, threshold)

    for idx1, idx2 in pairs:
        note1 = notes[idx1]
        note2 = notes[idx2]

        # Total duration of the pair
        total_dur = note1.Duration + note2.Duration

        # New durations based on ratio
        # If ratio = 1.5, long gets 1.5/(1.5+1) = 60%
        long_fraction = ratio / (ratio + 1.0)
        short_fraction = 1.0 / (ratio + 1.0)

        new_dur1 = total_dur * long_fraction
        new_dur2 = total_dur * short_fraction

        dur_delta1 = new_dur1 - note1.Duration
        dur_delta2 = new_dur2 - note2.Duration

        # First note: duration changes, offset stays same
        adjustments.append(InegalesAdjustment(
            note_index=idx1,
            offset_delta=0.0,
            duration_delta=dur_delta1,
        ))

        # Second note: offset shifts by first note's duration change
        adjustments.append(InegalesAdjustment(
            note_index=idx2,
            offset_delta=dur_delta1,
            duration_delta=dur_delta2,
        ))

    return adjustments
