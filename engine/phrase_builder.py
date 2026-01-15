"""Phrase builder: budget-aware concatenation of distinct treatments.

Key principle: Bass derives from soprano using counterpoint rules, not independent cycles.
Soprano leads, bass follows with complementary treatment.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import yaml

from shared.pitch import FloatingNote, Pitch, wrap_degree, cycle_pitch_with_variety
from engine.engine_types import MotifAST
from shared.timed_material import TimedMaterial

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class BarTreatment:
    """Treatment for a single bar within a phrase."""
    name: str
    transform: str  # none, invert, retrograde, head, tail
    shift: int  # transposition in scale degrees


def _load_bar_treatments() -> tuple[BarTreatment, ...]:
    """Load bar treatments from YAML."""
    with open(DATA_DIR / "bar_treatments.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return tuple(
        BarTreatment(t["name"], t["transform"], t["shift"])
        for t in data["treatments"]
    )


BAR_TREATMENTS: tuple[BarTreatment, ...] = _load_bar_treatments()


# Counterpoint rules: for each soprano treatment, which bass treatment complements it
# Key principle: bass uses contrasting motion/rhythm
COUNTERPOINT_MAP: dict[str, str] = {
    "statement": "continuation",      # Soprano states, bass continues
    "response": "statement",          # Soprano responds, bass states
    "sequence_down": "inversion_seq", # Contrary motion
    "development": "retrograde",      # Contrasting development
    "continuation": "fragmentation",  # Bass fragments while soprano continues
    "inversion_seq": "sequence_down", # Contrary motion
    "retrograde": "development",      # Contrasting development
    "fragmentation": "continuation",  # Bass continues while soprano fragments
}


def apply_transform(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    transform: str,
    shift: int = 0,
) -> tuple[tuple[Pitch, ...], tuple[Fraction, ...]]:
    """Apply transform to pitches and durations.

    Transforms:
        none: no change
        invert: mirror pitches around axis
        retrograde: reverse order
        head: take first 4 notes
        tail: take last 3 notes
        augment: double durations
        diminish: halve durations
    """
    p: tuple[Pitch, ...] = pitches
    d: tuple[Fraction, ...] = durations
    if transform == "invert":
        axis: int = 4
        p = tuple(
            FloatingNote(wrap_degree(2 * axis - x.degree)) if isinstance(x, FloatingNote) else x
            for x in p
        )
    elif transform == "retrograde":
        p = tuple(reversed(p))
        d = tuple(reversed(d))
    elif transform == "head":
        size: int = min(4, len(p))
        p = p[:size]
        d = d[:size]
    elif transform == "tail":
        size: int = min(3, len(p))
        p = p[-size:]
        d = d[-size:]
    elif transform == "augment":
        d = tuple(x * 2 for x in d)
    elif transform == "diminish":
        d = tuple(max(x // 2, Fraction(1, 16)) for x in d)
    if shift != 0:
        p = tuple(
            FloatingNote(wrap_degree(x.degree + shift)) if isinstance(x, FloatingNote) else x
            for x in p
        )
    return p, d


def _fit_durations(
    durations: tuple[Fraction, ...],
    target_budget: Fraction
) -> tuple[Fraction, ...]:
    """Fit durations to target budget by cycling through source material.

    Musical durations are preserved exactly. If material is shorter than budget,
    cycle through durations again. Final note may be truncated to fit exactly.
    """
    assert all(d > 0 for d in durations), "Durations must be positive"
    result: list[Fraction] = []
    remaining: Fraction = target_budget
    idx: int = 0
    max_iterations: int = 1000
    while remaining > Fraction(0):
        if idx >= max_iterations:
            raise ValueError(f"_fit_durations exceeded {max_iterations} iterations")
        d: Fraction = durations[idx % len(durations)]
        if d <= remaining:
            result.append(d)
            remaining -= d
        else:
            result.append(remaining)
            remaining = Fraction(0)
        idx += 1
    return tuple(result)


def _get_treatment_by_name(name: str) -> BarTreatment:
    """Find treatment by name."""
    for t in BAR_TREATMENTS:
        if t.name == name:
            return t
    return BAR_TREATMENTS[0]


def _build_bar(
    source_pitches: tuple[Pitch, ...],
    source_durs: tuple[Fraction, ...],
    treatment: BarTreatment,
    primary_transform: str,
    bar_budget: Fraction,
    pitch_shift: int = 0,
) -> tuple[list[Pitch], list[Fraction]]:
    """Build a single bar of material."""
    # Apply bar treatment transform (pitch only: invert, retrograde, head, tail)
    pitches, durations = apply_transform(
        source_pitches, source_durs, treatment.transform, treatment.shift + pitch_shift
    )
    # Apply primary transform (includes augment/diminish for duration)
    if primary_transform != "none":
        pitches, durations = apply_transform(pitches, durations, primary_transform)
    # Fit to bar budget
    fitted_durs: tuple[Fraction, ...] = _fit_durations(durations, bar_budget)
    if len(pitches) > len(fitted_durs):
        pitches = pitches[:len(fitted_durs)]
    elif len(pitches) < len(fitted_durs):
        # Cycle pitches with variety to avoid exact repetition
        extended: list[Pitch] = [
            cycle_pitch_with_variety(pitches, i) for i in range(len(fitted_durs))
        ]
        pitches = tuple(extended)
    return list(pitches), list(fitted_durs)


def build_voice(
    source_pitches: tuple[Pitch, ...],
    source_durs: tuple[Fraction, ...],
    budget: Fraction,
    phrase_seed: int,
    pitch_shift: int = 0,
    primary_transform: str = "none",
    soprano_treatments: list[str] | None = None,
) -> tuple[TimedMaterial, list[str]]:
    """Build a voice phrase by concatenating distinct treatments.

    If soprano_treatments is None, this is the leading voice (soprano).
    If soprano_treatments is provided, this is bass - derive from soprano using counterpoint.

    Returns:
        (TimedMaterial, treatments_used): The built phrase and treatment names used
    """
    bar_dur: Fraction = Fraction(1)
    assert bar_dur > 0, "Bar duration must be positive"
    result_pitches: list[Pitch] = []
    result_durations: list[Fraction] = []
    remaining: Fraction = budget
    bar_idx: int = 0
    max_bars: int = 1000
    treatments_used: list[str] = []
    used_names: set[str] = set()
    while remaining > Fraction(0):
        if bar_idx >= max_bars:
            raise ValueError(f"build_voice exceeded {max_bars} bars")
        if soprano_treatments is None:
            # Leading voice: pick next treatment, avoiding recent repeats
            base_idx: int = (phrase_seed + bar_idx) % len(BAR_TREATMENTS)
            treatment: BarTreatment = BAR_TREATMENTS[base_idx]
            # Skip if we just used this one
            attempts: int = 0
            while treatment.name in used_names and attempts < len(BAR_TREATMENTS):
                base_idx = (base_idx + 1) % len(BAR_TREATMENTS)
                treatment = BAR_TREATMENTS[base_idx]
                attempts += 1
            used_names.add(treatment.name)
            # Clear used set periodically to allow reuse after gap
            if len(used_names) >= len(BAR_TREATMENTS) // 2:
                used_names.clear()
                used_names.add(treatment.name)
        else:
            # Following voice: derive from soprano using counterpoint rules
            sop_treatment_name: str = soprano_treatments[bar_idx] if bar_idx < len(soprano_treatments) else "statement"
            bass_treatment_name: str = COUNTERPOINT_MAP.get(sop_treatment_name, "continuation")
            treatment = _get_treatment_by_name(bass_treatment_name)
        treatments_used.append(treatment.name)
        bar_budget: Fraction = min(bar_dur, remaining)
        pitches, durations = _build_bar(
            source_pitches, source_durs, treatment, primary_transform, bar_budget, pitch_shift
        )
        result_pitches.extend(pitches)
        result_durations.extend(durations)
        remaining -= bar_budget
        bar_idx += 1
    return TimedMaterial(tuple(result_pitches), tuple(result_durations), budget), treatments_used


def build_phrase_soprano(
    subject: MotifAST,
    counter_subject: MotifAST | None,
    budget: Fraction,
    phrase_seed: int,
    primary_transform: str = "none",
) -> TimedMaterial:
    """Build soprano - wrapper for backward compatibility."""
    material, _ = build_voice(
        subject.pitches, subject.durations, budget, phrase_seed,
        pitch_shift=0, primary_transform=primary_transform
    )
    return material


def build_phrase_bass(
    subject: MotifAST,
    counter_subject: MotifAST | None,
    budget: Fraction,
    phrase_seed: int,
    primary_transform: str = "none",
    use_counter_subject: bool = False,
) -> TimedMaterial:
    """Build bass - wrapper for backward compatibility."""
    if use_counter_subject and counter_subject is not None:
        source_p: tuple[Pitch, ...] = counter_subject.pitches
        source_d: tuple[Fraction, ...] = counter_subject.durations
    else:
        source_p = subject.pitches
        source_d = subject.durations
    material, _ = build_voice(
        source_p, source_d, budget, phrase_seed,
        pitch_shift=-7, primary_transform=primary_transform
    )
    return material


def build_voices(
    subject: MotifAST,
    counter_subject: MotifAST | None,
    budget: Fraction,
    phrase_seed: int,
    soprano_transform: str = "none",
    bass_transform: str = "none",
    use_counter_subject_for_bass: bool = False,
) -> tuple[TimedMaterial, TimedMaterial]:
    """Build both voices with bass derived from soprano via counterpoint.

    This is the proper API - builds soprano first, then derives bass.
    """
    # Build soprano (leading voice)
    soprano, soprano_treatments = build_voice(
        subject.pitches, subject.durations, budget, phrase_seed,
        pitch_shift=0, primary_transform=soprano_transform
    )
    # Build bass (following voice - derives from soprano)
    if use_counter_subject_for_bass and counter_subject is not None:
        bass_source_p: tuple[Pitch, ...] = counter_subject.pitches
        bass_source_d: tuple[Fraction, ...] = counter_subject.durations
    else:
        bass_source_p = subject.pitches
        bass_source_d = subject.durations
    bass, _ = build_voice(
        bass_source_p, bass_source_d, budget, phrase_seed,
        pitch_shift=-7, primary_transform=bass_transform,
        soprano_treatments=soprano_treatments
    )
    return soprano, bass
