"""Fragment catalogue: extract thematic fragments from LoadedFugue.

Provides head/tail fragment extraction for episode rendering (TP-B2).
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from math import ceil

from motifs.fugue_loader import LoadedFugue


@dataclass(frozen=True)
class Fragment:
    """A thematic fragment extracted from a subject.

    Attributes:
        degrees: Scale degrees of the fragment
        durations: Duration of each note as Fraction (whole-note fractions)
        bar_span: Number of bars the fragment occupies
    """
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    bar_span: int


def extract_head(fugue: LoadedFugue, bar_length: Fraction) -> Fragment:
    """Extract the head fragment from the subject.

    The head fragment contains the first N notes of the subject whose cumulative
    duration equals bar_length. If no exact split at bar_length, include notes up
    to the last note that starts before bar_length.

    Args:
        fugue: LoadedFugue containing the subject
        bar_length: Length of one bar as a Fraction (e.g., Fraction(1) for 4/4)

    Returns:
        Fragment containing the head portion of the subject
    """
    degrees: list[int] = []
    durations: list[Fraction] = []
    cumulative: Fraction = Fraction(0)

    for degree, dur_float in zip(fugue.subject.degrees, fugue.subject.durations):
        dur: Fraction = Fraction(dur_float).limit_denominator(64)

        # If adding this note would exceed bar_length, stop
        if cumulative + dur > bar_length:
            break

        degrees.append(degree)
        durations.append(dur)
        cumulative += dur

        # If we've reached exactly bar_length, stop
        if cumulative == bar_length:
            break

    assert len(degrees) > 0, (
        f"Head fragment is empty for bar_length={bar_length}. "
        f"Subject durations: {fugue.subject.durations}"
    )

    # Calculate bar span
    total_duration: Fraction = sum(durations)
    bar_span: int = ceil(total_duration / bar_length)

    return Fragment(
        degrees=tuple(degrees),
        durations=tuple(durations),
        bar_span=bar_span,
    )


def extract_tail(fugue: LoadedFugue, bar_length: Fraction) -> Fragment:
    """Extract the tail fragment from the subject.

    The tail fragment contains all notes after the head fragment.

    Args:
        fugue: LoadedFugue containing the subject
        bar_length: Length of one bar as a Fraction

    Returns:
        Fragment containing the tail portion of the subject
    """
    head: Fragment = extract_head(fugue=fugue, bar_length=bar_length)
    head_note_count: int = len(head.degrees)

    # Remaining notes after head
    tail_degrees: tuple[int, ...] = tuple(fugue.subject.degrees[head_note_count:])
    tail_durations: tuple[Fraction, ...] = tuple(
        Fraction(d).limit_denominator(64)
        for d in fugue.subject.durations[head_note_count:]
    )

    if len(tail_degrees) == 0:
        # Subject is exactly one bar long, no tail
        return Fragment(degrees=(), durations=(), bar_span=0)

    # Calculate bar span
    total_duration: Fraction = sum(tail_durations)
    bar_span: int = ceil(total_duration / bar_length)

    return Fragment(
        degrees=tail_degrees,
        durations=tail_durations,
        bar_span=bar_span,
    )


def extract_sixteenth_cell(fugue: LoadedFugue, bar_length: Fraction) -> Fragment:
    """Extract the initial run of sixteenth-note durations from the subject's tail.

    For subjects with rhythmic unit 1/16, this extracts the ascending cell used
    for hold-exchange sequencing (e.g., degrees 0,1,2,3 with durations 1/16 each).

    Args:
        fugue: LoadedFugue containing the subject
        bar_length: Length of one bar as a Fraction

    Returns:
        Fragment containing the sixteenth-note cell from the tail.
        If the tail has no sixteenths, returns the first 4 notes of the tail.
    """
    tail: Fragment = extract_tail(fugue=fugue, bar_length=bar_length)

    if len(tail.degrees) == 0:
        # Subject is exactly one bar, no tail
        return Fragment(degrees=(), durations=(), bar_span=0)

    # Determine rhythmic unit (assume 1/16 for invention genre)
    rhythmic_unit: Fraction = Fraction(1, 16)

    # Extract initial run of notes with duration == rhythmic_unit
    cell_degrees: list[int] = []
    cell_durations: list[Fraction] = []

    for degree, dur in zip(tail.degrees, tail.durations):
        if dur == rhythmic_unit:
            cell_degrees.append(degree)
            cell_durations.append(dur)
        else:
            # Stop at first note with different duration
            break

    # Fallback: if no sixteenths found, take first 4 notes of tail regardless of duration
    if len(cell_degrees) == 0:
        cell_degrees = list(tail.degrees[:4])
        cell_durations = list(tail.durations[:4])

    assert len(cell_degrees) > 0, (
        f"Sixteenth cell is empty. Tail degrees: {tail.degrees}, durations: {tail.durations}"
    )

    # Calculate bar span
    total_duration: Fraction = sum(cell_durations) if cell_durations else Fraction(0)
    bar_span: int = ceil(total_duration / bar_length) if total_duration > 0 else 0

    return Fragment(
        degrees=tuple(cell_degrees),
        durations=tuple(cell_durations),
        bar_span=bar_span,
    )
