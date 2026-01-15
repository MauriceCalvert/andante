"""Pitch and material transformations for expansion."""
from fractions import Fraction

from shared.pitch import FloatingNote, Pitch, is_rest, wrap_degree
from engine.sequence import build_sequence, build_sequence_break
from shared.timed_material import TimedMaterial


def apply_contrary_motion(pitches: tuple[Pitch, ...], axis: int = 4) -> tuple[Pitch, ...]:
    """Mirror degrees around axis for contrary motion."""
    result: list[Pitch] = []
    for p in pitches:
        if is_rest(p):
            result.append(p)
        else:
            assert isinstance(p, FloatingNote)
            result.append(FloatingNote(wrap_degree(2 * axis - p.degree)))
    return tuple(result)


def apply_imitation(pitches: tuple[Pitch, ...], interval: int = -4) -> tuple[Pitch, ...]:
    """Transpose degrees for imitation (default: at the fifth below)."""
    result: list[Pitch] = []
    for p in pitches:
        if is_rest(p):
            result.append(p)
        else:
            assert isinstance(p, FloatingNote)
            result.append(FloatingNote(wrap_degree(p.degree + interval)))
    return tuple(result)


def apply_transform(material: TimedMaterial, transform: str, params: dict) -> TimedMaterial:
    """Apply a named transform to material."""
    if transform == "none":
        return material
    elif transform == "invert":
        return material.invert()
    elif transform == "retrograde":
        return material.retrograde()
    elif transform == "head":
        size: int = min(params.get("size", 4), len(material.pitches) // 2)
        return material.head(size)
    elif transform == "tail":
        size: int = min(params.get("size", 3), len(material.pitches) // 2)
        return material.tail(size)
    elif transform == "augment":
        return material.augment()
    elif transform == "diminish":
        min_dur_str: str | None = params.get("min_duration")
        min_dur: Fraction | None = Fraction(min_dur_str) if min_dur_str else None
        return material.diminish(min_dur)
    else:
        raise ValueError(f"Unknown transform: {transform}")


def apply_fill(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    budget: Fraction,
    fill: str,
    params: dict,
) -> TimedMaterial:
    """Apply a named fill strategy to material."""
    pattern_dur: Fraction = sum(durations)
    assert pattern_dur > 0, "Pattern duration must be positive"
    if fill == "repeat":
        assert budget <= pattern_dur, (
            f"repeat fill requires budget ({budget}) <= pattern duration ({pattern_dur})"
        )
        return TimedMaterial.repeat_to_budget(pitches, durations, budget)
    elif fill == "cycle":
        phrase_seed: int = params.get("phrase_seed", 0)
        shifts: tuple[int, ...] = (0, -2, 3, -1, 2, -3, 1, -4)
        shift: int = shifts[phrase_seed % len(shifts)]
        return TimedMaterial.repeat_to_budget(pitches, durations, budget, shift)
    elif fill == "sequence":
        p, d = build_sequence(
            pitches, durations, budget,
            reps=params.get("reps", 2),
            step=params.get("step", -1),
            start=params.get("start", 0),
            phrase_seed=params.get("phrase_seed", 0),
            vary=params.get("vary", True),
            avoid_leading_tone=params.get("avoid_leading_tone", False),
        )
        return TimedMaterial(p, d, budget)
    elif fill == "sequence_break":
        p, d = build_sequence_break(
            pitches, durations, budget,
            break_after=params.get("break_after", 2),
            step=params.get("step", -1),
            break_shift=params.get("break_shift", 3),
        )
        return TimedMaterial(p, d, budget)
    else:
        raise ValueError(f"Unknown fill: {fill}")
