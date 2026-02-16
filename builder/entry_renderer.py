"""Entry voice renderer: voice-agnostic role dispatch for thematic entries.

Renders one voice of one entry (SUBJECT, ANSWER, CS, EPISODE, STRETTO, FREE).
Eliminates voice-0/voice-1 duplication from phrase_writer (D011, L017).
"""
from dataclasses import replace
from fractions import Fraction

from builder.imitation import subject_to_voice_notes
from builder.thematic_renderer import render_thematic_beat, _render_episode_fragment
from builder.types import Note
from motifs.fugue_loader import LoadedFugue
from planner.thematic import BeatRole, ThematicRole
from shared.music_math import parse_metre
from shared.tracer import get_tracer, _key_str
from shared.voice_types import Range


def render_entry_voice(
    role: ThematicRole,
    beat_role: BeatRole | None,
    fugue: LoadedFugue,
    start_offset: Fraction,
    end_offset: Fraction,
    entry_first_bar: int,
    entry_bar_count: int,
    target_track: int,
    target_range: Range,
    voice_name: str,
    plan: "PhrasePlan",
    thematic_roles: tuple[BeatRole, ...],
    metre: str,
) -> tuple[Note, ...]:
    """Render one voice of one entry in a voice-agnostic way.

    Args:
        role: ThematicRole for this voice (SUBJECT, ANSWER, CS, EPISODE, STRETTO, FREE)
        beat_role: BeatRole for this voice (None if role is FREE)
        fugue: LoadedFugue containing subject/answer/CS data
        start_offset: Absolute offset where this entry starts
        end_offset: Absolute offset where time window ends (exclusive)
        entry_first_bar: First bar number of this entry (1-based)
        entry_bar_count: Number of bars in this entry
        target_track: Track number for the notes (TRACK_SOPRANO or TRACK_BASS)
        target_range: Voice range for octave selection
        voice_name: "U" or "L" for tracing
        plan: PhrasePlan for context
        thematic_roles: All thematic roles for finding bar-specific BeatRoles
        metre: Metre string for beat calculations

    Returns:
        Tuple of notes for this voice
    """
    tracer = get_tracer()

    # SUBJECT, ANSWER, CS
    if role in (ThematicRole.SUBJECT, ThematicRole.ANSWER, ThematicRole.CS):
        assert beat_role is not None, f"No BeatRole for {role.value} at entry bar {entry_first_bar}"

        voice_notes: tuple[Note, ...] | None = render_thematic_beat(
            role=beat_role,
            fugue=fugue,
            start_offset=start_offset,
            target_range=target_range,
            end_offset=end_offset,
        )
        if voice_notes:
            # Label first note
            lyric: str = {
                ThematicRole.SUBJECT: "subject",
                ThematicRole.ANSWER: "answer",
                ThematicRole.CS: "cs",
            }[role]
            voice_notes = (replace(voice_notes[0], lyric=lyric),) + voice_notes[1:]

            # Trace render
            note_pitches: list[int] = [n.pitch for n in voice_notes]
            tracer.trace_thematic_render(
                bar=entry_first_bar,
                voice_name=voice_name,
                role_name=role.value.upper(),
                key_str=_key_str(key=beat_role.material_key),
                note_count=len(voice_notes),
                low_pitch=min(note_pitches),
                high_pitch=max(note_pitches),
            )
            return voice_notes
        else:
            # No notes rendered for this voice
            tracer.trace_thematic_render(
                bar=entry_first_bar,
                voice_name=voice_name,
                role_name=role.value.upper(),
                key_str=_key_str(key=beat_role.material_key),
                note_count=0,
                low_pitch=0,
                high_pitch=0,
            )
            return ()

    # EPISODE
    elif role == ThematicRole.EPISODE:
        # Render all episode fragments (one per bar with incrementing iteration)
        all_episode_notes: list[Note] = []
        for bar_offset in range(entry_bar_count):
            bar_num: int = entry_first_bar + bar_offset
            bar_start_offset: Fraction = start_offset + Fraction(bar_offset)

            # Find BeatRole for this bar and this voice
            bar_beat_role: BeatRole | None = None
            voice_idx: int = 0 if voice_name == "U" else 1
            for r in thematic_roles:
                if r.bar == bar_num and r.voice == voice_idx and r.beat == Fraction(0):
                    bar_beat_role = r
                    break

            assert bar_beat_role is not None, (
                f"No BeatRole for voice {voice_idx} EPISODE at bar {bar_num}"
            )

            # Render this bar's fragment
            fragment_notes: tuple[Note, ...] = _render_episode_fragment(
                role=bar_beat_role,
                fugue=fugue,
                start_offset=bar_start_offset,
                target_track=target_track,
                target_range=target_range,
            )
            all_episode_notes.extend(fragment_notes)

        # Apply time window
        voice_notes_windowed: list[Note] = []
        for n in all_episode_notes:
            if n.offset >= end_offset:
                break
            note_end: Fraction = n.offset + n.duration
            if note_end > end_offset:
                voice_notes_windowed.append(replace(n, duration=end_offset - n.offset))
            else:
                voice_notes_windowed.append(n)

        # Trace render (only for first bar)
        if voice_notes_windowed:
            note_pitches = [n.pitch for n in voice_notes_windowed]
            tracer.trace_thematic_render(
                bar=entry_first_bar,
                voice_name=voice_name,
                role_name="EPISODE",
                key_str=_key_str(key=beat_role.material_key) if beat_role else "",
                note_count=len(voice_notes_windowed),
                low_pitch=min(note_pitches),
                high_pitch=max(note_pitches),
            )
        return tuple(voice_notes_windowed)

    # STRETTO
    elif role == ThematicRole.STRETTO:
        assert beat_role is not None, f"No BeatRole for STRETTO at entry bar {entry_first_bar}"
        assert beat_role.material is not None, "STRETTO BeatRole missing material (delay)"

        # Parse delay from material field (string -> int)
        delay_beats: int = int(beat_role.material)

        # Compute delay_offset: delay in beats × beat_unit
        bar_length: Fraction
        beat_unit: Fraction
        bar_length, beat_unit = parse_metre(metre=metre)
        delay_offset: Fraction = Fraction(delay_beats) * beat_unit

        # Render subject at delayed start
        voice_notes_stretto: tuple[Note, ...] = subject_to_voice_notes(
            fugue=fugue,
            start_offset=start_offset + delay_offset,
            target_key=beat_role.material_key,
            target_track=target_track,
            target_range=target_range,
        )

        # Apply time window: drop/truncate notes outside [start_offset, end_offset)
        voice_notes_windowed: list[Note] = []
        for n in voice_notes_stretto:
            if n.offset >= end_offset:
                break
            note_end: Fraction = n.offset + n.duration
            if note_end > end_offset:
                voice_notes_windowed.append(replace(n, duration=end_offset - n.offset))
            else:
                voice_notes_windowed.append(n)

        # Label first note
        if voice_notes_windowed:
            voice_notes_windowed[0] = replace(voice_notes_windowed[0], lyric="stretto")

            # Trace render
            note_pitches = [n.pitch for n in voice_notes_windowed]
            tracer.trace_thematic_render(
                bar=entry_first_bar,
                voice_name=voice_name,
                role_name="STRETTO",
                key_str=_key_str(key=beat_role.material_key),
                note_count=len(voice_notes_windowed),
                low_pitch=min(note_pitches),
                high_pitch=max(note_pitches),
            )
            return tuple(voice_notes_windowed)
        else:
            # No notes rendered (fully truncated)
            tracer.trace_thematic_render(
                bar=entry_first_bar,
                voice_name=voice_name,
                role_name="STRETTO",
                key_str=_key_str(key=beat_role.material_key),
                note_count=0,
                low_pitch=0,
                high_pitch=0,
            )
            return ()

    # FREE
    elif role == ThematicRole.FREE:
        # FREE voice within material entry
        tracer.trace_thematic_render(
            bar=entry_first_bar,
            voice_name=voice_name,
            role_name="FREE",
            key_str="",
            note_count=0,
            low_pitch=0,
            high_pitch=0,
        )
        return ()

    # PEDAL handled elsewhere (not per-voice)
    else:
        return ()
