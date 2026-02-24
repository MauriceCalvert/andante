"""Subject-to-Notes conversion for imitative counterpoint."""
import logging
import math
from dataclasses import replace
from fractions import Fraction

from builder.types import Note
from motifs.fugue_loader import LoadedFugue
from shared.constants import DURATION_DENOMINATOR_LIMIT
from shared.key import Key
from shared.voice_types import Range

logger = logging.getLogger(__name__)


def _fit_shift(
    midi_pitches: tuple[int, ...],
    target_range: Range,
    label: str,
) -> int:
    """Find the best shift to place midi_pitches within target_range."""
    print(f'DEBUG _fit_shift: {label} pitches_lo={min(midi_pitches)} pitches_hi={max(midi_pitches)} range=[{target_range.low},{target_range.high}]', flush=True)
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
    # No octave multiple fits within range — use nearest octave multiple
    # anyway, accepting minor range overflow (L003: soft hints, not hard limits)
    mid: float = (shift_lo + shift_hi) / 2
    k_near: int = round(mid / 12)
    # Also check neighbours in case round() picked poorly
    candidates: list[int] = [k_near - 1, k_near, k_near + 1]
    best = None
    best_dist: float = 9999.0
    for k in candidates:
        candidate: int = k * 12
        dist: float = abs(candidate - mid)
        if dist < best_dist or (dist == best_dist and abs(candidate) < abs(best)):
            best = candidate
            best_dist = dist
    assert best is not None
    logger.warning(
        "%s: no octave-multiple shift in [%d, %d]; using %d (range may overflow by %d semitones)",
        label, shift_lo, shift_hi, best,
        max(0, shift_lo - best, best - shift_hi),
    )
    return best


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
    return tuple(replace(n, generated_by="answer") for n in notes)


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
    return tuple(replace(n, generated_by="cs") for n in notes)


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
    return tuple(replace(n, generated_by="subject") for n in notes)
