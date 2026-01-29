"""Per-bar context computation for figuration."""
from fractions import Fraction
from typing import Sequence

from builder.figuration.types import PhrasePosition
from builder.types import Anchor, PassageAssignment, Role


def compute_harmonic_tension(
    anchor_a: Anchor,
    phrase_pos: PhrasePosition,
    role: Role,
) -> str:
    """Compute harmonic tension from schema type, bass degree, and bar function."""
    if phrase_pos.position == "cadence":
        base_tension = "low"
    elif phrase_pos.position == "continuation":
        base_tension = "medium"
    else:
        base_tension = "low"
    bass = anchor_a.lower_degree
    if bass in (2, 4, 7):
        if base_tension == "low":
            return "medium"
        return "high"
    if bass in (5,):
        return "medium"
    schema = anchor_a.schema.lower() if anchor_a.schema else ""
    if schema in ("monte", "fonte"):
        return "medium"
    return base_tension


def compute_bar_function(phrase_pos: PhrasePosition, bar_num: int, total_bars: int) -> str:
    """Compute bar function for rhythm realisation."""
    if phrase_pos.position == "cadence":
        return "cadential"
    if phrase_pos.sequential:
        return "schema_arrival"
    if bar_num == total_bars - 2:
        return "preparatory"
    return "passing"


def compute_next_anchor_strength(
    idx: int,
    anchors: Sequence[Anchor],
    total_bars: int,
) -> str:
    """Compute strength of next anchor for anacrusis handling."""
    if idx + 2 >= len(anchors):
        return "strong"
    next_bar = _parse_bar_beat(anchors[idx + 1].bar_beat)[0]
    if next_bar == 1 or next_bar == (total_bars // 2) + 1:
        return "strong"
    if next_bar >= total_bars - 1:
        return "strong"
    return "weak"


def should_use_hemiola(bar_num: int, total_bars: int, metre: str, deformation: str | None) -> bool:
    """Determine if hemiola should be used for this bar."""
    if metre != "3/4":
        return False
    if total_bars < 6:
        return False
    hemiola_bar = total_bars - 2
    if bar_num == hemiola_bar or bar_num == hemiola_bar + 1:
        if deformation == "early_cadence":
            return False
        return True
    return False


def should_use_overdotted(affect_character: str, phrase_pos: PhrasePosition) -> bool:
    """Determine if overdotted rhythms should be used."""
    return affect_character == "ornate"


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


def compute_beat_class(
    voice: str,
    bar: int,
    passage_assignments: Sequence[PassageAssignment] | None,
) -> int:
    """Compute which beat this voice starts on for a given bar.

    Args:
        voice: "soprano" or "bass"
        bar: Bar number
        passage_assignments: Passage assignments with lead_voice info

    Returns:
        1 if voice leads or equal, 2 if voice accompanies.
    """
    lead_voice = get_lead_voice_for_bar(bar, passage_assignments)
    voice_index = 0 if voice == "soprano" else 1
    if lead_voice is None:
        return 1  # Equal: both on beat 1
    if lead_voice == voice_index:
        return 1  # This voice leads
    return 2  # This voice accompanies


def compute_effective_gap(
    gap_duration: Fraction,
    start_beat: int,
    metre: str,
) -> Fraction:
    """Compute effective gap duration based on start beat.

    Args:
        gap_duration: Original gap between anchors (whole notes)
        start_beat: 1 or 2
        metre: Time signature string like "4/4"

    Returns:
        Adjusted gap duration. If start_beat is 2, reduces by one beat.
    """
    if start_beat == 1:
        return gap_duration
    # Reduce by one beat
    parts = metre.split("/")
    beat_value = Fraction(1, int(parts[1]))
    reduced = gap_duration - beat_value
    # Ensure minimum duration (one beat)
    if reduced < beat_value:
        reduced = beat_value
    return reduced


def reduce_density(density: str) -> str:
    """Reduce density by one level for accompanying voice.

    Args:
        density: "high", "medium", or "low"

    Returns:
        One level sparser: high->medium, medium->low, low->low
    """
    if density == "high":
        return "medium"
    return "low"


def _parse_bar_beat(bar_beat: str) -> tuple[int, float]:
    """Parse bar.beat string into (bar, beat) tuple."""
    parts = bar_beat.split(".")
    bar = int(parts[0])
    beat = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar, beat)
