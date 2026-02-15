"""Subject-to-Notes conversion for imitative counterpoint."""
from fractions import Fraction

from builder.types import Note
from motifs.fugue_loader import LoadedFugue
from shared.key import Key
from shared.voice_types import Range

DURATION_DENOMINATOR_LIMIT: int = 64



def countersubject_to_voice_notes(
    fugue: LoadedFugue,
    start_offset: Fraction,
    target_key: Key,
    target_track: int,
    target_range: Range,
) -> tuple[Note, ...]:
    """Place countersubject in any voice at any key, octave-shifted into range."""
    tonic_midi: int = 60 + target_key.tonic_pc
    midi_pitches: tuple[int, ...] = fugue.countersubject_midi(tonic_midi=tonic_midi)
    durations: tuple[float, ...] = fugue.countersubject.durations
    assert len(midi_pitches) == len(durations), (
        f"CS pitch count {len(midi_pitches)} != duration count {len(durations)}"
    )
    # Octave-shift all pitches so they fit within target_range
    highest: int = max(midi_pitches)
    shift: int = 0
    while highest + shift > target_range.high:
        shift -= 12
    while min(midi_pitches) + shift < target_range.low:
        shift += 12
    assert min(midi_pitches) + shift >= target_range.low, (
        f"CS cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, lowest pitch {min(midi_pitches) + shift} < {target_range.low}"
    )
    assert max(midi_pitches) + shift <= target_range.high, (
        f"CS cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, highest pitch {max(midi_pitches) + shift} > {target_range.high}"
    )
    notes: list[Note] = []
    offset: Fraction = start_offset
    for pitch, dur_float in zip(midi_pitches, durations):
        dur: Fraction = Fraction(dur_float).limit_denominator(DURATION_DENOMINATOR_LIMIT)
        assert dur > 0, f"CS duration must be positive, got {dur_float}"
        notes.append(Note(
            offset=offset,
            pitch=pitch + shift,
            duration=dur,
            voice=target_track,
        ))
        offset += dur
    return tuple(notes)


def subject_to_voice_notes(
    fugue: LoadedFugue,
    start_offset: Fraction,
    target_key: Key,
    target_track: int,
    target_range: Range,
) -> tuple[Note, ...]:
    """Place subject in any voice at any key, octave-shifted into range."""
    tonic_midi: int = 60 + target_key.tonic_pc
    midi_pitches: tuple[int, ...] = fugue.subject_midi(tonic_midi=tonic_midi)
    durations: tuple[float, ...] = fugue.subject.durations
    assert len(midi_pitches) == len(durations), (
        f"Subject pitch count {len(midi_pitches)} != duration count {len(durations)}"
    )
    # Octave-shift all pitches so they fit within target_range
    highest: int = max(midi_pitches)
    shift: int = 0
    while highest + shift > target_range.high:
        shift -= 12
    while min(midi_pitches) + shift < target_range.low:
        shift += 12
    assert min(midi_pitches) + shift >= target_range.low, (
        f"Subject cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, lowest pitch {min(midi_pitches) + shift} < {target_range.low}"
    )
    assert max(midi_pitches) + shift <= target_range.high, (
        f"Subject cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, highest pitch {max(midi_pitches) + shift} > {target_range.high}"
    )
    notes: list[Note] = []
    offset: Fraction = start_offset
    for pitch, dur_float in zip(midi_pitches, durations):
        dur: Fraction = Fraction(dur_float).limit_denominator(DURATION_DENOMINATOR_LIMIT)
        assert dur > 0, f"Subject duration must be positive, got {dur_float}"
        notes.append(Note(
            offset=offset,
            pitch=pitch + shift,
            duration=dur,
            voice=target_track,
        ))
        offset += dur
    return tuple(notes)


def answer_to_voice_notes(
    fugue: LoadedFugue,
    start_offset: Fraction,
    target_track: int,
    target_range: Range,
) -> tuple[Note, ...]:
    """Place answer in any voice, octave-shifted into range.

    Uses fugue.answer_midi() which internally transposes to dominant (+7).
    Pass no tonic_midi override so it uses fugue.tonic_midi by default.
    """
    midi_pitches: tuple[int, ...] = fugue.answer_midi()
    durations: tuple[float, ...] = fugue.answer.durations
    assert len(midi_pitches) == len(durations), (
        f"Answer pitch count {len(midi_pitches)} != duration count {len(durations)}"
    )
    # Octave-shift all pitches so they fit within target_range
    highest: int = max(midi_pitches)
    shift: int = 0
    while highest + shift > target_range.high:
        shift -= 12
    while min(midi_pitches) + shift < target_range.low:
        shift += 12
    assert min(midi_pitches) + shift >= target_range.low, (
        f"Answer cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, lowest pitch {min(midi_pitches) + shift} < {target_range.low}"
    )
    assert max(midi_pitches) + shift <= target_range.high, (
        f"Answer cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, highest pitch {max(midi_pitches) + shift} > {target_range.high}"
    )
    notes: list[Note] = []
    offset: Fraction = start_offset
    for pitch, dur_float in zip(midi_pitches, durations):
        dur: Fraction = Fraction(dur_float).limit_denominator(DURATION_DENOMINATOR_LIMIT)
        assert dur > 0, f"Answer duration must be positive, got {dur_float}"
        notes.append(Note(
            offset=offset,
            pitch=pitch + shift,
            duration=dur,
            voice=target_track,
        ))
        offset += dur
    return tuple(notes)

