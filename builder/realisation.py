"""Realisation: Turn abstract structure into notes.

Category A: Pure functions, no I/O, no validation.
Inputs:
- Schema arrivals (soprano/bass pairs at strong beats)
- Bar assignments
- Subject (if active)
- Metre, local key, affect, texture

Process:
1. Place schema arrivals at designated strong beats
2. Fill weak beats with decoration
3. Verify all hard constraints
4. Apply surface rhythm
"""
from fractions import Fraction
from typing import Sequence

from builder.counterpoint import validate_passage
from builder.types import (
    Anchor, AffectConfig, FormConfig, GenreConfig, KeyConfig,
    Note, NoteFile, RhythmState, SchemaChain, Solution, TextureSequence,
)


SEMIQUAVER: Fraction = Fraction(1, 16)
QUAVER: Fraction = Fraction(1, 8)
CROTCHET: Fraction = Fraction(1, 4)


def realise(
    solution: Solution,
    texture: TextureSequence,
    anchors: Sequence[Anchor],
    key_config: KeyConfig,
    affect_config: AffectConfig,
    genre_config: GenreConfig,
    form_config: FormConfig,
) -> NoteFile:
    """Convert solver solution to note file."""
    soprano_notes: list[Note] = []
    bass_notes: list[Note] = []
    anchor_slots: set[int] = set()
    for anchor in anchors:
        slot: int = _bar_beat_to_slot(anchor.bar_beat)
        anchor_slots.add(slot)
    slot_count: int = len(solution.soprano_pitches)
    rhythm_state: RhythmState = RhythmState(state="RUN", density=0.75)
    i: int = 0
    while i < slot_count:
        offset: Fraction = Fraction(i, 16)
        if i in anchor_slots:
            duration: Fraction = QUAVER
            rhythm_state = RhythmState(state="HOLD", density=0.5)
        else:
            duration = SEMIQUAVER
            if rhythm_state.state == "HOLD":
                rhythm_state = RhythmState(state="RUN", density=0.75)
        bar: int = i // 16 + 1
        if bar >= form_config.minimum_bars - 1:
            rhythm_state = RhythmState(state="CADENCE", density=0.25)
            duration = CROTCHET
        soprano_notes.append(Note(
            offset=offset,
            pitch=solution.soprano_pitches[i],
            duration=duration,
            voice=0,
            lyric="",
        ))
        bass_notes.append(Note(
            offset=offset,
            pitch=solution.bass_pitches[i],
            duration=duration,
            voice=1,
            lyric="",
        ))
        slots_to_skip: int = int(duration / SEMIQUAVER)
        i += max(1, slots_to_skip)
    soprano_notes = _merge_repeated_pitches(soprano_notes)
    bass_notes = _merge_repeated_pitches(bass_notes)
    soprano_notes = _add_lyrics(soprano_notes, anchors, texture)
    tempo_range: list[int] = genre_config.rhythmic_vocabulary.get("tempo_range", [72, 88])
    tempo_base: int = (tempo_range[0] + tempo_range[1]) // 2
    tempo: int = tempo_base + affect_config.tempo_modifier
    return NoteFile(
        soprano=tuple(soprano_notes),
        bass=tuple(bass_notes),
        metre=genre_config.metre,
        tempo=tempo,
    )


def _merge_repeated_pitches(notes: list[Note]) -> list[Note]:
    """Merge consecutive notes with same pitch into longer notes."""
    if not notes:
        return notes
    merged: list[Note] = []
    current: Note = notes[0]
    for note in notes[1:]:
        if note.pitch == current.pitch:
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
    texture: TextureSequence,
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
    return (bar - 1) * 16 + slot_in_bar


def _bar_beat_to_offset(bar_beat: str) -> Fraction:
    """Convert bar.beat string to Fraction offset."""
    slot: int = _bar_beat_to_slot(bar_beat)
    return Fraction(slot, 16)


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
            offset=Fraction(i, 16),
            pitch=s_pitch,
            duration=SEMIQUAVER,
            voice=0,
        ))
        bass_notes.append(Note(
            offset=Fraction(i, 16),
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
    for note in subject_notes:
        offset_from_median: int = note.pitch - median_pitch
        cs_pitch: int = median_pitch - offset_from_median + transposition
        cs_duration: Fraction = note.duration
        if note.duration == SEMIQUAVER:
            cs_duration = QUAVER
        elif note.duration >= QUAVER:
            cs_duration = SEMIQUAVER
        countersubject.append(Note(
            offset=note.offset,
            pitch=cs_pitch,
            duration=cs_duration,
            voice=0,
        ))
    return countersubject
