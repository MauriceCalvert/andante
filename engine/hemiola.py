"""Hemiola: metric displacement for rhythmic tension."""
from dataclasses import dataclass
from fractions import Fraction

from shared.pitch import Pitch
from shared.timed_material import TimedMaterial


@dataclass(frozen=True)
class HemiolaPattern:
    """Hemiola pattern configuration."""
    name: str
    input_metre: str       # Must be triple metre (3/4, 6/8, etc.)
    regrouping: str        # "3_to_2" (standard), "2_to_3" (reverse)
    duration_bars: int     # How many bars affected
    trigger: str           # "pre_cadence", "climax", "manual"


HEMIOLA_PATTERNS: dict[str, HemiolaPattern] = {
    "cadential": HemiolaPattern(
        name="cadential",
        input_metre="3/4",
        regrouping="3_to_2",
        duration_bars=2,
        trigger="pre_cadence",
    ),
    "climax": HemiolaPattern(
        name="climax",
        input_metre="3/4",
        regrouping="3_to_2",
        duration_bars=2,
        trigger="climax",
    ),
}


def can_apply_hemiola(metre: str) -> bool:
    """Check if metre supports hemiola (must be triple)."""
    parts: list[str] = metre.split("/")
    assert len(parts) == 2, f"Invalid metre format: {metre}"
    numerator: int = int(parts[0])
    return numerator % 3 == 0


def apply_hemiola(
    material: TimedMaterial,
    pattern_name: str,
    metre: str,
) -> TimedMaterial:
    """Apply hemiola regrouping to material.

    Hemiola regroups beats: in 3/4, two bars of 3 quarter-notes become
    three groups of 2 quarter-notes. This preserves melodic arc by
    selecting structurally important pitches (first, middle, last of
    each original beat group) and assigning them to new groupings.

    Args:
        material: TimedMaterial to transform
        pattern_name: Name of hemiola pattern
        metre: Current metre (must be triple)

    Returns:
        New TimedMaterial with regrouped durations
    """
    assert can_apply_hemiola(metre), f"Hemiola requires triple metre, got {metre}"
    assert pattern_name in HEMIOLA_PATTERNS, f"Unknown hemiola pattern: {pattern_name}"
    pattern: HemiolaPattern = HEMIOLA_PATTERNS[pattern_name]
    parts: list[str] = metre.split("/")
    beat_value: Fraction = Fraction(1, int(parts[1]))
    if pattern.regrouping == "3_to_2":
        new_group_dur: Fraction = beat_value * 2
    else:
        new_group_dur = beat_value * Fraction(3, 2)
    num_groups: int = int(material.budget / new_group_dur)
    if num_groups < 1:
        return material
    selected_pitches: list[Pitch] = _select_structural_pitches(
        material.pitches, material.durations, num_groups
    )
    new_durations: list[Fraction] = []
    remaining: Fraction = material.budget
    for _ in range(num_groups):
        dur: Fraction = min(new_group_dur, remaining)
        new_durations.append(dur)
        remaining -= dur
    if remaining > Fraction(0):
        new_durations[-1] += remaining
    return TimedMaterial(
        pitches=tuple(selected_pitches),
        durations=tuple(new_durations),
        budget=material.budget,
    )


def _select_structural_pitches(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    num_groups: int,
) -> list[Pitch]:
    """Select structurally important pitches for hemiola regrouping.

    Preserves melodic arc by sampling at evenly-spaced points through
    the material, always including first and last pitches.
    """
    if len(pitches) <= num_groups:
        result: list[Pitch] = list(pitches)
        while len(result) < num_groups:
            result.append(pitches[-1])
        return result
    selected: list[Pitch] = []
    step: float = (len(pitches) - 1) / (num_groups - 1) if num_groups > 1 else 0
    for i in range(num_groups):
        idx: int = round(i * step) if num_groups > 1 else 0
        selected.append(pitches[idx])
    return selected


def detect_hemiola_trigger(
    phrase_index: int,
    total_phrases: int,
    is_climax: bool,
    cadence: str | None,
) -> str | None:
    """Detect if phrase should trigger hemiola.

    Args:
        phrase_index: Current phrase index
        total_phrases: Total number of phrases
        is_climax: Whether phrase is marked as climax
        cadence: Cadence type if any

    Returns:
        Hemiola pattern name to apply, or None
    """
    if is_climax:
        return "climax"
    if cadence in ("authentic", "half") and phrase_index >= total_phrases - 2:
        return "cadential"
    return None
