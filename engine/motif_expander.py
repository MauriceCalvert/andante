"""Motif expander: cycle/trim motifs to budget (moved from Subject)."""
from fractions import Fraction

from shared.types import Motif


def cycle_motif(motif: Motif, budget: Fraction) -> Motif:
    """Cycle motif to fill budget exactly."""
    degrees: list[int] = []
    durations: list[Fraction] = []
    remaining: Fraction = budget
    n: int = len(motif.degrees)
    idx: int = 0
    max_iterations: int = 10000
    while remaining > Fraction(0) and idx < max_iterations:
        deg: int = motif.degrees[idx % n]
        dur: Fraction = motif.durations[idx % n]
        use_dur: Fraction = min(dur, remaining)
        degrees.append(deg)
        durations.append(use_dur)
        remaining -= use_dur
        idx += 1
    return Motif(degrees=tuple(degrees), durations=tuple(durations), bars=motif.bars)


def trim_motif(motif: Motif, budget: Fraction) -> Motif:
    """Trim motif to budget."""
    degrees: list[int] = []
    durations: list[Fraction] = []
    remaining: Fraction = budget
    for deg, dur in zip(motif.degrees, motif.durations):
        if remaining <= Fraction(0):
            break
        degrees.append(deg)
        durations.append(min(dur, remaining))
        remaining -= dur
    return Motif(degrees=tuple(degrees), durations=tuple(durations), bars=motif.bars)


def extend_motif(motif: Motif, budget: Fraction) -> Motif:
    """Extend or trim motif to fill budget exactly."""
    motif_dur: Fraction = sum(motif.durations, Fraction(0))
    if budget <= motif_dur:
        return trim_motif(motif, budget)
    return cycle_motif(motif, budget)


def extend_pair(subject: Motif, counter_subject: Motif, budget: Fraction) -> tuple[Motif, Motif]:
    """Extend both subject and counter-subject to fill budget."""
    return extend_motif(subject, budget), extend_motif(counter_subject, budget)
