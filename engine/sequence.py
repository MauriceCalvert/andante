"""Sequence generation - data-driven pattern repetition with variation.

Replaces the complex nested loops in transform.py with a cleaner architecture:
- Variation strategies as data
- Separate uniqueness checking
"""
from dataclasses import dataclass
from fractions import Fraction

from shared.pitch import FloatingNote, Pitch, Rest, is_rest, wrap_degree


@dataclass(frozen=True)
class Variation:
    """A pitch variation strategy."""
    name: str
    invert: bool = False
    reverse: bool = False


# Available variations in priority order
VARIATIONS: tuple[Variation, ...] = (
    Variation("none"),
    Variation("invert", invert=True),
    Variation("retrograde", reverse=True),
    Variation("inv_retro", invert=True, reverse=True),
)

# Extended variations for fallback
EXTENDED_VARIATIONS: tuple[Variation, ...] = VARIATIONS + (
    Variation("none_shift1"),  # Will use different shift
    Variation("invert_shift", invert=True),
    Variation("retro_shift", reverse=True),
)


def _apply_variation(
    pitches: list[Pitch],
    durations: list[Fraction],
    variation: Variation,
) -> tuple[list[Pitch], list[Fraction]]:
    """Apply a variation to pitches and durations."""
    result_p: list[Pitch] = list(pitches)
    result_d: list[Fraction] = list(durations)
    if variation.invert:
        result_p = [p if is_rest(p) else FloatingNote(wrap_degree(8 - p.degree)) for p in result_p]
    if variation.reverse:
        result_p = list(reversed(result_p))
        result_d = list(reversed(result_d))
    return result_p, result_d


def _shift_pitch(pitch: Pitch, shift: int, avoid_leading_tone: bool) -> Pitch:
    """Shift a pitch by scale degrees."""
    if is_rest(pitch):
        return pitch
    assert isinstance(pitch, FloatingNote)
    shifted: FloatingNote = FloatingNote(wrap_degree(pitch.degree + shift))
    if avoid_leading_tone and shifted.degree == 7:
        return FloatingNote(6)
    return shifted


def _append_material(
    result_p: list[Pitch],
    result_d: list[Fraction],
    source_p: list[Pitch],
    source_d: list[Fraction],
    shift: int,
    remaining: Fraction,
    avoid_leading_tone: bool,
) -> Fraction:
    """Append shifted material to result, respecting budget. Returns new remaining."""
    for pitch, dur in zip(source_p, source_d):
        if remaining <= Fraction(0):
            break
        use_dur: Fraction = min(dur, remaining)
        result_p.append(_shift_pitch(pitch, shift, avoid_leading_tone))
        result_d.append(use_dur)
        remaining -= use_dur
    return remaining


def build_sequence(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    budget: Fraction,
    reps: int = 2,
    step: int = -1,
    start: int = 0,
    phrase_seed: int = 0,
    vary: bool = True,
    avoid_leading_tone: bool = False,
) -> tuple[tuple[Pitch, ...], tuple[Fraction, ...]]:
    """Build sequence: subject repeated at shifted pitch levels with melodic variation.

    Uses phrase_seed to select variation for each repetition and to offset
    the starting position, creating unique sequences across phrases.
    When vary=False, only uses 'none' variation (literal repetition).
    """
    subject_dur: Fraction = sum(durations)
    assert subject_dur > Fraction(0), f"Subject duration must be positive, got {subject_dur}"
    min_reps: int = int(budget / subject_dur) + 1
    actual_reps: int = max(reps, min_reps)
    result_p: list[Pitch] = []
    result_d: list[Fraction] = []
    remaining: Fraction = budget
    variations: tuple[Variation, ...] = VARIATIONS if vary else (VARIATIONS[0],)
    # Use phrase_seed to offset starting position for variety across phrases
    start_offsets: tuple[int, ...] = (0, 2, -1, 3, 1, -2, 4, -3)
    effective_start: int = start + start_offsets[phrase_seed % len(start_offsets)]
    for rep in range(actual_reps):
        if remaining <= Fraction(0):
            break
        base_shift: int = effective_start + rep * step
        var_idx: int = (rep + phrase_seed) % len(variations)
        variation: Variation = variations[var_idx]
        var_p, var_d = _apply_variation(list(pitches), list(durations), variation)
        remaining = _append_material(
            result_p, result_d, var_p, var_d, base_shift, remaining, avoid_leading_tone
        )
    return tuple(result_p), tuple(result_d)


def build_sequence_break(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    budget: Fraction,
    break_after: int = 1,
    step: int = -1,
    break_shift: int = 3,
) -> tuple[tuple[Pitch, ...], tuple[Fraction, ...]]:
    """Sequence that breaks pattern unexpectedly after N repetitions.

    After break_after repetitions at regular step intervals, the next
    material shifts by break_shift instead, creating surprise.
    """
    assert all(d > 0 for d in durations), "Durations must be positive"
    result_p: list[Pitch] = []
    result_d: list[Fraction] = []
    remaining: Fraction = budget
    rep: int = 0
    max_reps: int = 1000
    while remaining > Fraction(0):
        if rep >= max_reps:
            raise ValueError(f"sequence_with_break exceeded {max_reps} repetitions")
        if rep < break_after:
            shift: int = rep * step
        else:
            shift = (break_after - 1) * step + break_shift
        for pitch, dur in zip(pitches, durations):
            if remaining <= Fraction(0):
                break
            use_dur: Fraction = min(dur, remaining)
            result_p.append(_shift_pitch(pitch, shift, avoid_leading_tone=False))
            result_d.append(use_dur)
            remaining -= use_dur
        rep += 1
    return tuple(result_p), tuple(result_d)
