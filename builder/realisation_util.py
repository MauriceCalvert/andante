"""Utility functions for realisation."""
from fractions import Fraction
from typing import Sequence

from builder.types import Anchor, PassageAssignment


def get_function_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
) -> str | None:
    """Look up passage function for a given bar number."""
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.function
    return None


def get_lead_voice_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
) -> int | None:
    """Look up lead voice for a given bar number.

    Returns:
        0 if soprano leads, 1 if bass leads, None if equal.
    """
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.lead_voice
    return None


def get_passage_end_offset(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
    beats_per_bar: int,
) -> Fraction | None:
    """Return offset where current passage ends (start of next bar after end_bar).

    Used to truncate bass notes at passage boundaries to avoid overlap.
    """
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            # End of this passage = start of next bar after end_bar
            end_offset = Fraction(assignment.end_bar * beats_per_bar, 4)
            return end_offset
    return None


def build_stacked_lyric(
    section: str | None,
    schema: str | None,
    function: str | None,
    figure: str | None,
) -> str:
    """Build stacked lyric from section, schema, passage function, and figure name."""
    parts: list[str] = []
    if section:
        parts.append(section)
    if schema:
        parts.append(schema)
    if function:
        parts.append(function)
    if figure:
        parts.append(figure)
    return "/".join(parts)


def get_bass_articulation(
    duration: Fraction,
    is_run: bool,
) -> str:
    """Determine articulation marking for bass note.

    Short notes in running passages get staccato/non-legato articulation
    to lighten the texture and create rhythmic contrast with soprano.
    """
    # removed, ugly
    # if duration <= STACCATO_DURATION_THRESHOLD and is_run:
    #     return "stacc"
    return ""


def anchor_sort_key(anchor: Anchor) -> tuple[float, int]:
    """Sort key for anchors: by time, then by upper degree."""
    parts: list[str] = anchor.bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar + beat / 10.0, anchor.upper_degree)


def get_beats_per_bar(metre: str) -> int:
    """Extract beats per bar from metre string."""
    num_str: str = metre.split("/")[0]
    return int(num_str)


def bar_beat_to_offset(bar_beat: str, beats_per_bar: int) -> Fraction:
    """Convert bar.beat string to Fraction offset in whole notes."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    offset_in_beats: Fraction = Fraction(bar - 1) * beats_per_bar + Fraction(beat) - 1
    return offset_in_beats / 4
