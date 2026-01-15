"""Voice role analyzer for humanisation."""
from engine.note import Note
from humanisation.context.types import VoiceContext

# Thematic treatment keywords that indicate subject material
THEMATIC_KEYWORDS = frozenset({
    "statement",
    "answer",
    "subject",
    "countersubject",
    "inversion",
    "augmentation",
    "diminution",
    "stretto",
    "imitation",
    "canon",
})


def _is_thematic(lyric: str) -> bool:
    """Check if lyric indicates thematic material."""
    if not lyric:
        return False
    lyric_lower = lyric.lower()
    return any(keyword in lyric_lower for keyword in THEMATIC_KEYWORDS)


def _compute_activity_ratios(notes: list[Note]) -> dict[int, float]:
    """Compute note density ratio per track.

    Returns dict mapping track -> activity ratio (relative to most active voice).
    """
    if not notes:
        return {}

    # Count notes per track
    track_counts: dict[int, int] = {}
    for note in notes:
        track_counts[note.track] = track_counts.get(note.track, 0) + 1

    if not track_counts:
        return {}

    # Compute ratios relative to most active
    max_count = max(track_counts.values())
    if max_count == 0:
        return {track: 1.0 for track in track_counts}

    return {track: count / max_count for track, count in track_counts.items()}


def analyze_voice(notes: list[Note]) -> list[VoiceContext]:
    """Analyze voice role context for each note.

    Determines:
    - Whether this is the melody voice (track 0 by convention)
    - Whether note is stating thematic material (from lyric)
    - Activity ratio (note density relative to other voices)

    Args:
        notes: List of Note objects

    Returns:
        List of VoiceContext, one per note
    """
    if not notes:
        return []

    # Compute activity ratios
    activity_ratios = _compute_activity_ratios(notes)

    # Build thematic map based on first note lyric in each track/phrase group
    # Notes in same phrase/track inherit thematic status from first annotated note
    phrase_track_thematic: dict[tuple[int, int], bool] = {}

    # First pass: find thematic annotations
    current_phrase = 0
    prev_lyric = ""
    for note in sorted(notes, key=lambda n: n.Offset):
        # Detect phrase change
        if note.lyric and note.lyric != prev_lyric:
            current_phrase += 1
            prev_lyric = note.lyric

        key = (current_phrase, note.track)
        if note.lyric and key not in phrase_track_thematic:
            phrase_track_thematic[key] = _is_thematic(note.lyric)

    # Second pass: build contexts
    contexts: list[VoiceContext] = []
    current_phrase = 0
    prev_lyric = ""

    for note in notes:
        # Track phrase changes
        if note.lyric and note.lyric != prev_lyric:
            current_phrase += 1
            prev_lyric = note.lyric

        key = (current_phrase, note.track)
        is_thematic = phrase_track_thematic.get(key, False)

        # Check this note's own lyric too
        if note.lyric:
            is_thematic = is_thematic or _is_thematic(note.lyric)

        contexts.append(VoiceContext(
            is_melody=note.track == 0,
            is_thematic=is_thematic,
            activity_ratio=activity_ratios.get(note.track, 1.0),
            voice_id=note.track,
        ))

    return contexts
