"""Figuration patterns for melodic variation on repeats."""
from fractions import Fraction
from pathlib import Path
from typing import Optional

import yaml

from engine.key import Key
from shared.tracer import get_tracer
from engine.engine_types import RealisedNote

DATA_DIR: Path = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "figurations.yaml", encoding="utf-8") as _f:
    FIGURATIONS: dict = yaml.safe_load(_f)
with open(DATA_DIR / "predicates.yaml", encoding="utf-8") as _f:
    _P: dict = yaml.safe_load(_f)
_I: dict = _P["intervals"]


def parse_durations(dur_list: list) -> tuple[Fraction, ...]:
    """Parse duration strings to Fractions."""
    return tuple(Fraction(d) if isinstance(d, str) else Fraction(d) for d in dur_list)


def apply_figuration(
    note: RealisedNote,
    next_note: Optional[RealisedNote],
    pattern_name: str,
    key: Key,
) -> tuple[RealisedNote, ...]:
    """Apply a figuration pattern to a note."""
    tracer = get_tracer()
    pattern: dict = FIGURATIONS[pattern_name]
    steps: list[int] = pattern["steps"]
    durations: tuple[Fraction, ...] = parse_durations(pattern["durations"])
    result: list[RealisedNote] = []
    current_offset: Fraction = note.offset
    for step, dur_frac in zip(steps, durations, strict=True):
        actual_dur: Fraction = note.duration * dur_frac
        pitch: int = key.diatonic_step(note.pitch, step) if step != 0 else note.pitch
        fig_note: RealisedNote = RealisedNote(
            offset=current_offset,
            pitch=pitch,
            duration=actual_dur,
            voice=note.voice,
        )
        result.append(fig_note)
        current_offset += actual_dur
    tracer.trace("FIGURATION", f"{note.voice}/{pattern_name}", f"applied at {float(note.offset):.3f}",
                 original_pitch=note.pitch, result_count=len(result))
    return tuple(result)


def can_figurate(note: RealisedNote, next_note: Optional[RealisedNote], pattern_name: str) -> bool:
    """Check if a note can receive a figuration pattern."""
    pattern: dict = FIGURATIONS[pattern_name]
    condition: str = pattern.get("condition", "any")
    min_dur: Fraction = Fraction(1, 4)
    if note.duration < min_dur:
        return False
    if condition == "any":
        return True
    if condition == "long_note":
        return note.duration >= Fraction(1, 2)
    if condition == "stepwise_down" and next_note is not None:
        interval: int = next_note.pitch - note.pitch
        return interval < 0 and abs(interval) <= _I["step"]
    return False


def select_figuration(
    note: RealisedNote,
    next_note: Optional[RealisedNote],
    bar_dur: Fraction,
) -> Optional[str]:
    """Select a figuration pattern based on context."""
    is_downbeat: bool = note.offset % bar_dur == 0
    if note.duration >= Fraction(1, 2):
        return "arpeggio_up" if is_downbeat else "arpeggio_down"
    if next_note is not None:
        interval: int = next_note.pitch - note.pitch
        if interval < 0 and abs(interval) <= _I["step"]:
            return "passing"
    if is_downbeat and note.duration >= Fraction(1, 4):
        return "neighbor_upper"
    return None
