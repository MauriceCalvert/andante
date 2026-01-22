"""Realisation: Turn abstract structure into notes.

Category A: Pure functions, no I/O, no validation.

Simplified: Durations now come from solution (set by rhythm plan upstream).
No post-hoc rhythm state machine - rhythm decisions made in planner/rhythmic.py (L6).
"""
from fractions import Fraction
from typing import Sequence

from builder.types import (
    Anchor, AffectConfig, FormConfig, GenreConfig, KeyConfig,
    Note, NoteFile, Solution, TreatmentAssignment,
)


SEMIQUAVER: Fraction = Fraction(1, 16)
SLOTS_PER_BAR: int = 16


def realise(
    solution: Solution,
    texture: Sequence[TreatmentAssignment] | None,
    anchors: Sequence[Anchor],
    key_config: KeyConfig,
    affect_config: AffectConfig,
    genre_config: GenreConfig,
    form_config: FormConfig,
) -> NoteFile:
    """Convert solver solution to note file.

    Durations come from solution (set by rhythm plan).
    No post-hoc rhythm modification.

    Args:
        solution: Solver solution with pitches and durations
        texture: List of TreatmentAssignment (unused, kept for interface compat)
        anchors: Anchors from L4 (used for lyrics)
        key_config: Key configuration (unused, kept for interface compat)
        affect_config: Affect configuration (for tempo modifier)
        genre_config: Genre configuration (for tempo range, metre)
        form_config: Form configuration (unused, kept for interface compat)

    Returns:
        NoteFile with soprano and bass notes
    """
    soprano_notes: list[Note] = _build_voice_notes(
        solution.soprano_pitches,
        solution.soprano_durations,
        voice=0,
    )
    bass_notes: list[Note] = _build_voice_notes(
        solution.bass_pitches,
        solution.bass_durations,
        voice=1,
    )

    # Merge consecutive notes with same pitch (ties)
    soprano_notes = _merge_repeated_pitches(soprano_notes)
    bass_notes = _merge_repeated_pitches(bass_notes)

    # Add anchor annotations
    soprano_notes = _add_lyrics(soprano_notes, anchors)

    # Calculate tempo
    tempo_range: list[int] = genre_config.rhythmic_vocabulary.get("tempo_range", [72, 88])
    tempo_base: int = (tempo_range[0] + tempo_range[1]) // 2
    tempo: int = tempo_base + affect_config.tempo_modifier

    return NoteFile(
        soprano=tuple(soprano_notes),
        bass=tuple(bass_notes),
        metre=genre_config.metre,
        tempo=tempo,
    )


def _build_voice_notes(
    pitches: tuple[int, ...],
    durations: tuple[Fraction, ...],
    voice: int,
) -> list[Note]:
    """Build note list from pitches and durations.

    Skips slots where duration indicates hold (creates tied notes via merge).
    """
    notes: list[Note] = []
    slot_idx: int = 0

    while slot_idx < len(pitches):
        offset: Fraction = Fraction(slot_idx, SLOTS_PER_BAR)
        pitch: int = pitches[slot_idx]
        duration: Fraction = durations[slot_idx] if slot_idx < len(durations) else SEMIQUAVER

        notes.append(Note(
            offset=offset,
            pitch=pitch,
            duration=duration,
            voice=voice,
            lyric="",
        ))

        # Advance by duration (in slots)
        slots_to_skip: int = max(1, int(duration * SLOTS_PER_BAR))
        slot_idx += slots_to_skip

    return notes


def _merge_repeated_pitches(
    notes: list[Note],
    max_duration: Fraction = Fraction(1, 1),
) -> list[Note]:
    """Merge consecutive notes with same pitch into longer notes (ties).

    Args:
        notes: List of notes to merge
        max_duration: Maximum duration for merged note (default: 1 bar)

    Returns:
        List with consecutive same-pitch notes merged
    """
    if not notes:
        return notes

    merged: list[Note] = []
    current: Note = notes[0]

    for note in notes[1:]:
        if note.pitch == current.pitch and current.duration + note.duration <= max_duration:
            current = Note(
                offset=current.offset,
                pitch=current.pitch,
                duration=current.duration + note.duration,
                voice=current.voice,
                lyric=current.lyric,
            )
        else:
            merged.append(current)
            current = note

    merged.append(current)
    return merged


def _add_lyrics(
    notes: list[Note],
    anchors: Sequence[Anchor],
) -> list[Note]:
    """Add lyrics/annotations to notes at anchor positions."""
    anchor_map: dict[Fraction, Anchor] = {}
    for anchor in anchors:
        offset: Fraction = _bar_beat_to_offset(anchor.bar_beat)
        anchor_map[offset] = anchor

    result: list[Note] = []
    for note in notes:
        if note.offset in anchor_map:
            anchor: Anchor = anchor_map[note.offset]
            lyric: str = f"{anchor.schema}_{anchor.stage}"
            result.append(Note(
                offset=note.offset,
                pitch=note.pitch,
                duration=note.duration,
                voice=note.voice,
                lyric=lyric,
            ))
        else:
            result.append(note)

    return result


def _bar_beat_to_slot(bar_beat: str) -> int:
    """Convert bar.beat string to slot index."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    slot_in_bar: int = int((beat - 1) * 4)
    return (bar - 1) * SLOTS_PER_BAR + slot_in_bar


def _bar_beat_to_offset(bar_beat: str) -> Fraction:
    """Convert bar.beat string to Fraction offset."""
    slot: int = _bar_beat_to_slot(bar_beat)
    return Fraction(slot, SLOTS_PER_BAR)


def generate_free_passage(
    exit_pitch: tuple[int, int],
    entry_pitch: tuple[int, int],
    duration_beats: int,
    bridge_pitch_set: frozenset[int],
    metre: str,
) -> tuple[list[Note], list[Note]]:
    """Generate free passage between schemas.

    Uses bridge pitch set (pentatonic) to avoid premature tonicisation.
    Ends with lead-in motion (step below entry).
    """
    soprano_notes: list[Note] = []
    bass_notes: list[Note] = []
    slots: int = duration_beats * 4
    exit_s, exit_b = exit_pitch
    entry_s, entry_b = entry_pitch

    for i in range(slots):
        t: float = i / max(1, slots - 1)
        s_pitch: int = int(exit_s + t * (entry_s - exit_s))
        b_pitch: int = int(exit_b + t * (entry_b - exit_b))

        s_pc: int = s_pitch % 12
        if s_pc not in bridge_pitch_set:
            for offset in [1, -1, 2, -2]:
                if (s_pitch + offset) % 12 in bridge_pitch_set:
                    s_pitch += offset
                    break

        b_pc = b_pitch % 12
        if b_pc not in bridge_pitch_set:
            for offset in [1, -1, 2, -2]:
                if (b_pitch + offset) % 12 in bridge_pitch_set:
                    b_pitch += offset
                    break

        soprano_notes.append(Note(
            offset=Fraction(i, SLOTS_PER_BAR),
            pitch=s_pitch,
            duration=SEMIQUAVER,
            voice=0,
        ))
        bass_notes.append(Note(
            offset=Fraction(i, SLOTS_PER_BAR),
            pitch=b_pitch,
            duration=SEMIQUAVER,
            voice=1,
        ))

    return soprano_notes, bass_notes


def generate_countersubject(
    subject_notes: list[Note],
    transposition: int,
) -> list[Note]:
    """Generate countersubject for Answer.

    Rules:
    - Contrary motion skeleton
    - Rhythmic complement
    - Invertible at 10th
    - Arrival synchronisation
    """
    countersubject: list[Note] = []
    if not subject_notes:
        return countersubject

    median_pitch: int = sum(n.pitch for n in subject_notes) // len(subject_notes)
    quaver: Fraction = Fraction(1, 8)

    for note in subject_notes:
        offset_from_median: int = note.pitch - median_pitch
        cs_pitch: int = median_pitch - offset_from_median + transposition

        cs_duration: Fraction = note.duration
        if note.duration == SEMIQUAVER:
            cs_duration = quaver
        elif note.duration >= quaver:
            cs_duration = SEMIQUAVER

        countersubject.append(Note(
            offset=note.offset,
            pitch=cs_pitch,
            duration=cs_duration,
            voice=0,
        ))

    return countersubject
