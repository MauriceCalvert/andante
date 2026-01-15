"""Expander utilities: constants and helper functions."""
from fractions import Fraction
from pathlib import Path

import yaml

from shared.pitch import FloatingNote, Pitch, cycle_pitch_with_variety
from engine.engine_types import MotifAST
from engine.vocabulary import DEVICES, RHYTHMS
from planner.subject import Subject

DATA_DIR = Path(__file__).parent.parent / "data"
CADENCE_BUDGET: Fraction = Fraction(1, 2)
TREATMENTS: dict = yaml.safe_load(open(DATA_DIR / "treatments.yaml", encoding="utf-8"))

TONAL_ROOTS: dict[str, int] = {
    "I": 1, "i": 1, "V": 5, "v": 5, "IV": 4, "iv": 4,
    "vi": 6, "VI": 6, "ii": 2, "iii": 3, "III": 3, "VII": 7, "vii": 7,
}


def bar_duration(metre: str) -> Fraction:
    """Calculate duration of one bar."""
    num_str, den_str = metre.split("/")
    return Fraction(int(num_str), int(den_str))


def subject_to_motif_ast(subj: Subject) -> MotifAST:
    """Convert Subject's subject Motif to MotifAST for legacy pipeline."""
    m = subj.subject
    pitches: tuple[Pitch, ...] = tuple(FloatingNote(d) for d in m.degrees)
    return MotifAST(pitches=pitches, durations=m.durations, bars=m.bars)


def cs_to_motif_ast(subj: Subject) -> MotifAST:
    """Convert Subject's counter_subject Motif to MotifAST for legacy pipeline."""
    m = subj.counter_subject
    pitches: tuple[Pitch, ...] = tuple(FloatingNote(d) for d in m.degrees)
    return MotifAST(pitches=pitches, durations=m.durations, bars=m.bars)


def apply_rhythm(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    rhythm_name: str,
    budget: Fraction,
) -> tuple[tuple[Pitch, ...], tuple[Fraction, ...]]:
    """Apply rhythm pattern to pitches with variety on cycling."""
    assert rhythm_name in RHYTHMS, f"Unknown rhythm: {rhythm_name}"
    rhythm = RHYTHMS[rhythm_name]
    pattern: tuple[Fraction, ...] = rhythm.durations
    result_pitches: list[Pitch] = []
    result_durs: list[Fraction] = []
    pitch_idx: int = 0
    pattern_idx: int = 0
    remaining: Fraction = budget
    while remaining > Fraction(0):
        dur: Fraction = pattern[pattern_idx % len(pattern)]
        use_dur: Fraction = min(dur, remaining)
        result_pitches.append(cycle_pitch_with_variety(pitches, pitch_idx))
        result_durs.append(use_dur)
        pitch_idx += 1
        pattern_idx += 1
        remaining -= use_dur
    return tuple(result_pitches), tuple(result_durs)


def apply_device(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    device_name: str,
    budget: Fraction,
) -> tuple[tuple[Pitch, ...], tuple[Fraction, ...]]:
    """Apply contrapuntal device, cycling transformed material to fill budget.

    Device transforms rhythmic character (e.g. diminution halves note values),
    then material is cycled to fill the phrase budget.
    """
    assert device_name in DEVICES, f"Unknown device: {device_name}"
    device = DEVICES[device_name]
    transformed_durs: list[Fraction] = list(durations)
    if device.duration_factor is not None:
        transformed_durs = [d * device.duration_factor for d in transformed_durs]
    result_pitches: list[Pitch] = []
    result_durs: list[Fraction] = []
    pitch_idx: int = 0
    dur_idx: int = 0
    remaining: Fraction = budget
    n_pitches: int = len(pitches)
    n_durs: int = len(transformed_durs)
    while remaining > Fraction(0):
        dur: Fraction = transformed_durs[dur_idx % n_durs]
        use_dur: Fraction = min(dur, remaining)
        result_pitches.append(cycle_pitch_with_variety(pitches, pitch_idx))
        result_durs.append(use_dur)
        pitch_idx += 1
        dur_idx += 1
        remaining -= use_dur
    return tuple(result_pitches), tuple(result_durs)
