"""Ornament application for realised notes."""
from fractions import Fraction
from pathlib import Path

import yaml

from engine.key import Key
from shared.tracer import get_tracer
from engine.engine_types import RealisedNote
from engine.vocabulary import ORNAMENTS, Ornament

DATA_DIR: Path = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "predicates.yaml", encoding="utf-8") as _f:
    _P: dict = yaml.safe_load(_f)
_I: dict = _P["intervals"]
_O: dict = _P["ornaments"]


def is_power_of_two(n: int) -> bool:
    """Check if n is a power of 2."""
    return n > 0 and (n & (n - 1)) == 0


def can_ornament(duration: Fraction) -> bool:
    """Only ornament notes with clean binary subdivisions.

    Duration must be >= min and have power-of-2 numerator (1, 2, 4...).
    This ensures 4-way subdivision produces clean durations.
    """
    min_dur: Fraction = Fraction(_O["min_duration"])
    if duration < min_dur:
        return False
    return is_power_of_two(duration.numerator)


def select_ornament(
    note: RealisedNote,
    next_note: RealisedNote | None,
    is_cadence: bool,
    bar_dur: Fraction,
    phrase_index: int = 0,
) -> Ornament | None:
    """Select ornament based on baroque conventions.

    - Trill: cadential note
    - Mordent: downbeat with sufficient duration (varies by phrase)
    - Turn: descending stepwise motion
    """
    if not can_ornament(note.duration):
        return None
    if is_cadence:
        return ORNAMENTS.get("trill")
    is_downbeat: bool = note.offset % bar_dur == 0
    if is_downbeat and note.duration >= Fraction(1, 4):
        ornament_options: list[str | None] = ["mordent", "turn", None, "mordent"]
        choice: str | None = ornament_options[phrase_index % len(ornament_options)]
        if choice is not None:
            return ORNAMENTS.get(choice)
        return None
    if next_note is not None:
        interval: int = next_note.pitch - note.pitch
        if interval < 0 and abs(interval) <= _I["step"]:
            return ORNAMENTS.get("turn")
    return None


def apply_ornament(
    note: RealisedNote,
    ornament: Ornament,
    key: Key,
) -> tuple[RealisedNote, ...]:
    """Expand a note into ornamented notes.

    No range checking (L003). Ornament pitches are diatonic steps from the note,
    which is already correctly placed by the realiser.
    """
    tracer = get_tracer()
    result: list[RealisedNote] = []
    current_offset: Fraction = note.offset
    for step, dur_frac in zip(ornament.steps, ornament.durations, strict=True):
        actual_dur: Fraction = note.duration * dur_frac
        pitch: int = key.diatonic_step(note.pitch, step) if step != 0 else note.pitch
        ornamented: RealisedNote = RealisedNote(
            offset=current_offset,
            pitch=pitch,
            duration=actual_dur,
            voice=note.voice,
        )
        result.append(ornamented)
        current_offset += actual_dur
    pitches: list[int] = [n.pitch for n in result]
    durs: list[Fraction] = [n.duration for n in result]
    tracer.trace("ORNAMENT", f"{note.voice}/{ornament.name}", f"applied at {float(note.offset):.3f}",
                 original_pitch=note.pitch, original_dur=note.duration,
                 result_pitches=pitches, result_durs=durs)
    return tuple(result)


def apply_ornaments(
    notes: tuple[RealisedNote, ...],
    key: Key,
    is_cadence: bool,
    bar_dur: Fraction,
    phrase_index: int = 0,
) -> tuple[RealisedNote, ...]:
    """Apply ornaments sparingly - max per phrase from predicates.yaml."""
    if len(notes) < 2:
        return notes
    max_ornaments: int = _O["max_per_phrase"]
    result: list[RealisedNote] = []
    applied: int = 0
    for i, note in enumerate(notes):
        if applied >= max_ornaments:
            result.append(note)
            continue
        next_note: RealisedNote | None = notes[i + 1] if i < len(notes) - 1 else None
        is_note_cadence: bool = is_cadence and i == len(notes) - 1
        ornament: Ornament | None = select_ornament(note, next_note, is_note_cadence, bar_dur, phrase_index)
        if ornament is not None:
            result.extend(apply_ornament(note, ornament, key))
            applied += 1
        else:
            result.append(note)
    return tuple(result)
