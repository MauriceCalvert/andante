"""Pitch and material transformations for expansion."""
from fractions import Fraction

from shared.pitch import FloatingNote, Pitch, is_rest, wrap_degree
from engine.sequence import build_sequence, build_sequence_break
from shared.timed_material import TimedMaterial


def apply_tonal_answer(material: TimedMaterial) -> TimedMaterial:
    """Apply tonal answer transformation for dominant entry.

    In baroque fugue/invention, when the subject enters on the dominant,
    intervals are adjusted to maintain key coherence:

    1. If subject starts on 1 and leaps to 5, answer starts on 5 and goes to 1
       (the 4th up becomes a 4th down, or equivalently 5th→4th contraction)
    2. Remaining intervals are transposed to dominant level (+4 degrees)

    This creates the characteristic "tonal answer" vs "real answer" distinction.

    Example (C major):
      Subject: C-G-A-G (degrees 1-5-6-5)
      Answer:  G-C-D-C (degrees 5-1-2-1) - first interval inverted, rest transposed
    """
    pitches = list(material.pitches)
    if len(pitches) < 2:
        # Too short to need adjustment, just transpose
        return TimedMaterial(
            tuple(apply_imitation(tuple(pitches), 4)),
            material.durations,
            material.budget,
        )

    result: list[Pitch] = []
    first_deg: int | None = None
    second_deg: int | None = None

    # Find first two non-rest pitches to analyze the opening interval
    for p in pitches:
        if not is_rest(p) and isinstance(p, FloatingNote):
            if first_deg is None:
                first_deg = p.degree
            elif second_deg is None:
                second_deg = p.degree
                break

    # Determine if we need tonal adjustment
    # Classic case: subject starts 1→5 (or 5→1), answer should be 5→1 (or 1→5)
    needs_adjustment = False
    if first_deg is not None and second_deg is not None:
        interval = (second_deg - first_deg) % 7
        # Interval of 4 (a 5th up in 1-indexed) needs tonal adjustment
        if interval == 4 or interval == -3 or interval == 3:
            needs_adjustment = True

    # Process pitches
    processed_first = False
    processed_second = False
    for p in pitches:
        if is_rest(p):
            result.append(p)
            continue

        assert isinstance(p, FloatingNote)

        if not processed_first:
            # First note: transpose to dominant (degree 5)
            result.append(FloatingNote(wrap_degree(p.degree + 4)))
            processed_first = True
        elif not processed_second and needs_adjustment:
            # Second note with tonal adjustment: contract 5th to 4th
            # If subject went 1→5, answer goes 5→1 (not 5→2)
            if first_deg == 1 and second_deg == 5:
                result.append(FloatingNote(1))  # Answer: 5→1
            elif first_deg == 5 and second_deg == 1:
                result.append(FloatingNote(5))  # Answer: 1→5
            else:
                # Other intervals: just transpose
                result.append(FloatingNote(wrap_degree(p.degree + 4)))
            processed_second = True
        else:
            # Remaining notes: straight transposition to dominant
            result.append(FloatingNote(wrap_degree(p.degree + 4)))

    return TimedMaterial(tuple(result), material.durations, material.budget)


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
