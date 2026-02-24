"""Thematic renderer: converts BeatRole assignments to Note objects.

Layer 6 component. Takes thematic plan roles and renders them into notes
using pre-composed material from the fugue triple.

TD-1: Handles SUBJECT, ANSWER, CS, and FREE roles. EPISODE falls through to
FREE (rendering deferred to TD-2).
"""
from fractions import Fraction

from builder.imitation import (
    answer_to_voice_notes,
    countersubject_to_voice_notes,
    subject_to_voice_notes,
)
from builder.types import Note
from motifs.fugue_loader import LoadedFugue
from planner.thematic import BeatRole, ThematicRole
from shared.voice_types import Range


def render_thematic_beat(
    role: BeatRole,
    fugue: LoadedFugue,
    start_offset: Fraction,
    target_range: Range,
    end_offset: Fraction,
) -> tuple[Note, ...] | None:
    """Render one beat's thematic material to notes within a time window.

    Args:
        role: BeatRole specifying what to render
        fugue: LoadedFugue containing subject/answer/CS data
        start_offset: Absolute offset where this beat starts
        target_range: Voice range for octave selection
        end_offset: Absolute offset where time window ends (exclusive)

    Returns:
        Tuple of notes for this beat, or None if role is FREE.
        All returned notes satisfy: onset < end_offset.
        Notes that overshoot are truncated to end at end_offset.
    """
    from dataclasses import replace
    from shared.constants import TRACK_BASS, TRACK_SOPRANO

    if role.role == ThematicRole.FREE:
        return None

    # Map voice index (0 or 1) to track number (0 for soprano, 3 for bass)
    target_track: int = TRACK_SOPRANO if role.voice == 0 else TRACK_BASS

    raw_notes: tuple[Note, ...] | None = None

    if role.role == ThematicRole.SUBJECT:
        # Render subject in material_key
        raw_notes = subject_to_voice_notes(
            fugue=fugue,
            start_offset=start_offset,
            target_key=role.material_key,
            target_track=target_track,
            target_range=target_range,
        )

    elif role.role == ThematicRole.ANSWER:
        # Render answer using answer-specific rendering
        # fugue.answer_midi() internally transposes to dominant (+7)
        # render_offset shifts start backwards for mid-bar answer entries
        raw_notes = answer_to_voice_notes(
            fugue=fugue,
            start_offset=start_offset + role.render_offset,
            target_track=target_track,
            target_range=target_range,
        )

    elif role.role == ThematicRole.CS:
        # Render countersubject in material_key
        raw_notes = countersubject_to_voice_notes(
            fugue=fugue,
            start_offset=start_offset,
            target_key=role.material_key,
            target_track=target_track,
            target_range=target_range,
        )

    elif role.role == ThematicRole.EPISODE:
        # Episode rendering handled by _render_episode_fragment, not here
        return None

    else:
        # Other roles not yet implemented (STRETTO, CADENCE, etc.)
        # CADENCE is handled by cadence_writer, not thematic renderer
        return None

    if raw_notes is None:
        return None

    # Apply time-window contract: drop/truncate notes outside [start_offset, end_offset)
    windowed: list[Note] = []
    for n in raw_notes:
        if n.offset >= end_offset:
            break
        note_end: Fraction = n.offset + n.duration
        if note_end > end_offset:
            windowed.append(replace(n, duration=end_offset - n.offset))
        else:
            windowed.append(n)

    result: tuple[Note, ...] = tuple(windowed)

    # Postcondition: no note starts at or past end_offset
    for n in result:
        assert n.offset < end_offset, (
            f"render_thematic_beat emitted note at {n.offset} >= end_offset {end_offset}"
        )

    return result


def _render_episode_fragment(
    role: BeatRole,
    fugue: LoadedFugue,
    start_offset: Fraction,
    target_track: int,
    target_range: Range,
) -> tuple[Note, ...]:
    """Render an episode fragment transposed down by fragment_iteration steps.

    Args:
        role: BeatRole with role=EPISODE, material="head" or "tail", fragment_iteration=N
        fugue: LoadedFugue containing the subject
        start_offset: Absolute offset where this beat starts
        target_track: Track number for the notes
        target_range: Voice range for octave selection

    Returns:
        Tuple of notes for this episode fragment
    """
    from motifs.fragment_catalogue import extract_head, extract_tail
    from motifs.head_generator import degrees_to_midi
    from shared.music_math import parse_metre

    # Extract fragment based on material
    bar_length: Fraction = parse_metre(metre=f"{fugue.metre[0]}/{fugue.metre[1]}")[0]
    if role.material == "head":
        fragment = extract_head(fugue=fugue, bar_length=bar_length)
    elif role.material == "tail":
        fragment = extract_tail(fugue=fugue, bar_length=bar_length)
    else:
        assert False, f"Episode role must have material 'head' or 'tail', got '{role.material}'"

    # If fragment is empty (tail of 1-bar subject), return no notes
    if len(fragment.degrees) == 0:
        return ()

    # Transpose fragment degrees down by fragment_iteration diatonic steps
    transposed_degrees: tuple[int, ...] = tuple(
        deg - role.fragment_iteration
        for deg in fragment.degrees
    )

    # Convert to MIDI in material_key
    tonic_midi: int = 60 + role.material_key.tonic_pc
    midi_pitches: tuple[int, ...] = degrees_to_midi(
        degrees=transposed_degrees,
        tonic_midi=tonic_midi,
        mode=fugue.subject.mode,
    )

    # Octave-shift into target_range
    highest: int = max(midi_pitches)
    lowest: int = min(midi_pitches)
    shift: int = 0

    # Shift down until highest fits
    while highest + shift > target_range.high:
        shift -= 12

    # Shift up until lowest fits
    while lowest + shift < target_range.low:
        shift += 12

    assert lowest + shift >= target_range.low, (
        f"Episode fragment cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, lowest pitch {lowest + shift} < {target_range.low}"
    )
    assert highest + shift <= target_range.high, (
        f"Episode fragment cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, highest pitch {highest + shift} > {target_range.high}"
    )

    # Build notes
    notes: list[Note] = []
    offset: Fraction = start_offset
    for pitch, duration in zip(midi_pitches, fragment.durations):
        notes.append(Note(
            offset=offset,
            pitch=pitch + shift,
            duration=duration,
            voice=target_track,
            generated_by="episode_fragment",
        ))
        offset += duration

    # Mark first note with lyric="episode"
    if notes:
        from dataclasses import replace
        notes[0] = replace(notes[0], lyric="episode")

    return tuple(notes)
