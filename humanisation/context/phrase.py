"""Phrase context analyzer for humanisation."""
from engine.note import Note
from humanisation.context.types import PhraseContext


def _extract_treatment(lyric: str) -> str:
    """Extract treatment name from lyric annotation.

    Lyric format: "treatment [texture]" or just "treatment"
    """
    if not lyric:
        return ""
    # Remove texture annotation in brackets
    if "[" in lyric:
        lyric = lyric.split("[")[0].strip()
    return lyric


def _detect_phrase_boundaries(notes: list[Note]) -> list[tuple[int, int, str]]:
    """Detect phrase boundaries from note list.

    Returns list of (start_index, end_index, treatment) tuples.
    Phrase boundaries detected by:
    1. Change in lyric annotation (new treatment)
    2. Gap > 0.5 beats between notes in same voice
    """
    if not notes:
        return []

    phrases: list[tuple[int, int, str]] = []
    phrase_start = 0
    current_treatment = _extract_treatment(notes[0].lyric)

    # Group by track to detect gaps per voice
    track_notes: dict[int, list[tuple[int, Note]]] = {}
    for i, note in enumerate(notes):
        track_notes.setdefault(note.track, []).append((i, note))

    for i, note in enumerate(notes):
        new_treatment = _extract_treatment(note.lyric)

        # Detect phrase change by treatment annotation change
        if new_treatment and new_treatment != current_treatment:
            if i > phrase_start:
                phrases.append((phrase_start, i - 1, current_treatment))
            phrase_start = i
            current_treatment = new_treatment

    # Close final phrase
    if len(notes) > phrase_start:
        phrases.append((phrase_start, len(notes) - 1, current_treatment))

    return phrases


def _find_phrase_peak(notes: list[Note], start: int, end: int) -> int:
    """Find melodic peak within phrase (highest pitch in melody voice)."""
    max_pitch = -1
    peak_idx = start

    for i in range(start, end + 1):
        note = notes[i]
        # Prioritize melody (track 0) for peak detection
        if note.track == 0 and note.midiNote > max_pitch:
            max_pitch = note.midiNote
            peak_idx = i

    # If no melody notes, use any voice
    if max_pitch == -1:
        for i in range(start, end + 1):
            if notes[i].midiNote > max_pitch:
                max_pitch = notes[i].midiNote
                peak_idx = i

    return peak_idx


def analyze_phrases(notes: list[Note]) -> list[PhraseContext]:
    """Analyze phrase context for each note.

    Extracts:
    - Phrase boundaries from lyric annotations
    - Melodic peak within each phrase
    - Position within phrase (0.0 to 1.0)
    - Distance to peak (signed, negative = before peak)

    Args:
        notes: List of Note objects

    Returns:
        List of PhraseContext, one per note
    """
    if not notes:
        return []

    # Detect phrase boundaries
    phrases = _detect_phrase_boundaries(notes)

    # Build mapping from note index to phrase
    note_to_phrase: dict[int, tuple[int, int, int, str]] = {}  # idx -> (phrase_id, start, end, treatment)
    for phrase_id, (start, end, treatment) in enumerate(phrases):
        for i in range(start, end + 1):
            note_to_phrase[i] = (phrase_id, start, end, treatment)

    # Find peaks for each phrase
    phrase_peaks: dict[int, int] = {}  # phrase_id -> peak_idx
    for phrase_id, (start, end, treatment) in enumerate(phrases):
        phrase_peaks[phrase_id] = _find_phrase_peak(notes, start, end)

    # Build contexts
    contexts: list[PhraseContext] = []
    for i, note in enumerate(notes):
        if i not in note_to_phrase:
            # Orphan note, assign to phrase 0
            phrase_id = 0
            start = 0
            end = len(notes) - 1
            treatment = ""
        else:
            phrase_id, start, end, treatment = note_to_phrase[i]

        # Compute position in phrase
        phrase_len = end - start + 1
        position = (i - start) / max(phrase_len - 1, 1) if phrase_len > 1 else 0.5

        # Compute distance to peak
        peak_idx = phrase_peaks.get(phrase_id, start)
        distance_to_peak = (i - peak_idx) / max(phrase_len, 1)

        # Detect boundary type
        is_boundary = (i == end)
        if is_boundary:
            # Check if it's a cadence based on treatment or position
            boundary_type = "cadence" if position > 0.9 else "breath"
        else:
            boundary_type = "none"

        contexts.append(PhraseContext(
            phrase_id=phrase_id,
            position_in_phrase=position,
            distance_to_peak=distance_to_peak,
            is_phrase_boundary=is_boundary,
            boundary_type=boundary_type,
            phrase_treatment=treatment,
        ))

    return contexts
