"""Subject-to-Notes conversion for imitative counterpoint."""
import math
from fractions import Fraction

from builder.types import Note
from motifs.fugue_loader import LoadedFugue
from shared.key import Key
from shared.voice_types import Range

DURATION_DENOMINATOR_LIMIT: int = 64


def _fit_shift(
    midi_pitches: tuple[int, ...],
    target_range: Range,
    label: str,
) -> int:
    """Find the best shift to place midi_pitches within target_range."""
    lo: int = min(midi_pitches)
    hi: int = max(midi_pitches)
    span: int = hi - lo
    range_span: int = target_range.high - target_range.low
    assert span <= range_span, (
        f"{label} span {span} semitones exceeds range [{target_range.low}, {target_range.high}] "
        f"({range_span} semitones)"
    )
    # Valid shift range: [target_range.low - lo, target_range.high - hi]
    shift_lo: int = target_range.low - lo
    shift_hi: int = target_range.high - hi
    # Try octave-multiple shifts first (preserves tonal anchoring)
    k_lo: int = math.ceil(shift_lo / 12)
    k_hi: int = math.floor(shift_hi / 12)
    best: int | None = None
    best_dist: int = 9999
    for k in range(k_lo, k_hi + 1):
        candidate: int = k * 12
        dist: int = abs(candidate)
        if dist < best_dist:
            best = candidate
            best_dist = dist
    if best is not None:
        return best
    # No octave multiple fits — use the shift closest to zero
    if shift_lo <= 0 <= shift_hi:
        return 0
    return shift_lo if abs(shift_lo) <= abs(shift_hi) else shift_hi


def answer_to_voice_notes(
    fugue: LoadedFugue,
    start_offset: Fraction,
    target_track: int,
    target_range: Range,
) -> tuple[Note, ...]:
    """Place answer in any voice, octave-shifted into range."""
    midi_pitches: tuple[int, ...] = fugue.answer_midi()
    durations: tuple[float, ...] = fugue.answer.durations
    assert len(midi_pitches) == len(durations), (
        f"Answer pitch count {len(midi_pitches)} != duration count {len(durations)}"
    )
    shift: int = _fit_shift(
        midi_pitches=midi_pitches,
        target_range=target_range,
        label="Answer",
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


def countersubject_to_voice_notes(
    fugue: LoadedFugue,
    start_offset: Fraction,
    target_key: Key,
    target_track: int,
    target_range: Range,
) -> tuple[Note, ...]:
    """Place countersubject in any voice at any key, octave-shifted into range."""
    tonic_midi: int = 60 + target_key.tonic_pc
    target_mode: str = target_key.mode
    midi_pitches: tuple[int, ...] = fugue.countersubject_midi(tonic_midi=tonic_midi, mode=target_mode)
    durations: tuple[float, ...] = fugue.countersubject.durations
    assert len(midi_pitches) == len(durations), (
        f"CS pitch count {len(midi_pitches)} != duration count {len(durations)}"
    )
    shift: int = _fit_shift(
        midi_pitches=midi_pitches,
        target_range=target_range,
        label="CS",
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
    target_mode: str = target_key.mode
    midi_pitches: tuple[int, ...] = fugue.subject_midi(tonic_midi=tonic_midi, mode=target_mode)
    durations: tuple[float, ...] = fugue.subject.durations
    assert len(midi_pitches) == len(durations), (
        f"Subject pitch count {len(midi_pitches)} != duration count {len(durations)}"
    )
    shift: int = _fit_shift(
        midi_pitches=midi_pitches,
        target_range=target_range,
        label="Subject",
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
