"""Harmonic context analyzer for humanisation."""
from engine.note import Note
from humanisation.context.types import HarmonicContext

# Interval class to tension mapping (0-11 semitones mod 12)
# Based on traditional consonance/dissonance classification
INTERVAL_TENSION: dict[int, float] = {
    0: 0.0,    # unison - perfect consonance
    1: 0.9,    # minor second - harsh dissonance
    2: 0.7,    # major second - mild dissonance
    3: 0.2,    # minor third - imperfect consonance
    4: 0.2,    # major third - imperfect consonance
    5: 0.15,   # perfect fourth - context-dependent
    6: 0.85,   # tritone - strong dissonance
    7: 0.0,    # perfect fifth - perfect consonance
    8: 0.2,    # minor sixth - imperfect consonance
    9: 0.2,    # major sixth - imperfect consonance
    10: 0.7,   # minor seventh - mild dissonance
    11: 0.8,   # major seventh - strong dissonance
}


def _get_vertical_slices(notes: list[Note]) -> dict[float, list[tuple[int, Note]]]:
    """Group notes by onset time into vertical slices.

    Returns dict mapping offset -> list of (note_index, Note).
    """
    slices: dict[float, list[tuple[int, Note]]] = {}
    for i, note in enumerate(notes):
        # Round to avoid floating point issues
        offset = round(note.Offset, 6)
        slices.setdefault(offset, []).append((i, note))
    return slices


def _compute_slice_tension(slice_notes: list[tuple[int, Note]]) -> dict[int, tuple[float, int]]:
    """Compute tension for each note in a vertical slice.

    Returns dict mapping note_index -> (tension, interval_class).
    """
    results: dict[int, tuple[float, int]] = {}

    if len(slice_notes) < 2:
        # Single note, no harmonic context
        for idx, note in slice_notes:
            results[idx] = (0.0, 0)
        return results

    # Sort by track (voice) - lower track number = higher voice
    sorted_notes = sorted(slice_notes, key=lambda x: x[1].track)

    # Compute intervals between adjacent voices
    for i, (idx, note) in enumerate(sorted_notes):
        max_tension = 0.0
        most_tense_interval = 0

        for j, (other_idx, other_note) in enumerate(sorted_notes):
            if i == j:
                continue

            interval = abs(note.midiNote - other_note.midiNote) % 12
            tension = INTERVAL_TENSION.get(interval, 0.5)

            if tension > max_tension:
                max_tension = tension
                most_tense_interval = interval

        results[idx] = (max_tension, most_tense_interval)

    return results


def _detect_resolution(
    note_idx: int,
    current_tension: float,
    notes: list[Note],
    all_tensions: dict[int, float],
) -> bool:
    """Detect if this note is a resolution from a previous dissonance.

    A note is a resolution if:
    1. Current tension is low (consonant)
    2. Previous note in same voice had high tension (dissonant)
    """
    if current_tension > 0.3:
        return False  # Not consonant enough to be a resolution

    current_note = notes[note_idx]

    # Find previous note in same voice
    prev_note_idx = None
    prev_offset = -1.0
    for i, note in enumerate(notes):
        if note.track == current_note.track and note.Offset < current_note.Offset:
            if note.Offset > prev_offset:
                prev_offset = note.Offset
                prev_note_idx = i

    if prev_note_idx is None:
        return False

    prev_tension = all_tensions.get(prev_note_idx, 0.0)
    return prev_tension > 0.5  # Previous was dissonant


def _detect_prepared_dissonance(
    note_idx: int,
    current_tension: float,
    notes: list[Note],
) -> bool:
    """Detect if this dissonance was prepared.

    A dissonance is prepared if:
    1. Current note is dissonant
    2. Same pitch was present in previous vertical slice
    """
    if current_tension < 0.5:
        return False  # Not dissonant

    current_note = notes[note_idx]

    # Find notes just before this one
    for note in notes:
        if (note.track != current_note.track and
            note.Offset < current_note.Offset and
            current_note.Offset - note.Offset < 0.5):  # Within half bar
            # Check if same pitch class
            if note.midiNote % 12 == current_note.midiNote % 12:
                return True

    return False


def analyze_harmonic(notes: list[Note]) -> list[HarmonicContext]:
    """Analyze harmonic context for each note.

    Computes vertical intervals between simultaneous notes and determines:
    - Harmonic tension (0.0 = consonant, 1.0 = harsh dissonance)
    - Resolution detection (dissonance resolving to consonance)
    - Prepared dissonance detection (suspension/preparation)

    Args:
        notes: List of Note objects

    Returns:
        List of HarmonicContext, one per note
    """
    if not notes:
        return []

    # Get vertical slices
    slices = _get_vertical_slices(notes)

    # Compute tension for all notes
    all_tensions: dict[int, float] = {}
    all_intervals: dict[int, int] = {}

    for offset, slice_notes in slices.items():
        slice_results = _compute_slice_tension(slice_notes)
        for idx, (tension, interval) in slice_results.items():
            all_tensions[idx] = tension
            all_intervals[idx] = interval

    # Build contexts
    contexts: list[HarmonicContext] = []
    for i, note in enumerate(notes):
        tension = all_tensions.get(i, 0.0)
        interval_class = all_intervals.get(i, 0)

        is_resolution = _detect_resolution(i, tension, notes, all_tensions)
        is_prepared = _detect_prepared_dissonance(i, tension, notes)

        contexts.append(HarmonicContext(
            tension=tension,
            is_resolution=is_resolution,
            is_prepared_dissonance=is_prepared,
            interval_class=interval_class,
        ))

    return contexts
