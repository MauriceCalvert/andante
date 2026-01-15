"""Spacing constraints for N-voice architecture."""
from dataclasses import dataclass
from fractions import Fraction

from engine.voice_checks import VoiceViolation


@dataclass(frozen=True)
class SpacingConstraint:
    """Spacing rules between two voices."""
    min_interval: int
    max_interval: int
    allow_crossing: bool
    max_crossing_beats: Fraction


SPACING_ADJACENT_UPPER = SpacingConstraint(
    min_interval=0,
    max_interval=12,
    allow_crossing=True,
    max_crossing_beats=Fraction(1, 8),
)

SPACING_BASS_GAP = SpacingConstraint(
    min_interval=0,
    max_interval=19,
    allow_crossing=False,
    max_crossing_beats=Fraction(0),
)

SPACING_OUTER = SpacingConstraint(
    min_interval=7,
    max_interval=36,
    allow_crossing=False,
    max_crossing_beats=Fraction(0),
)


def check_spacing(
    upper: list[tuple[Fraction, int]],
    lower: list[tuple[Fraction, int]],
    upper_index: int,
    lower_index: int,
    constraint: SpacingConstraint,
) -> list[VoiceViolation]:
    """Check spacing constraints between two voices."""
    violations: list[VoiceViolation] = []
    upper_by_off: dict[Fraction, int] = {off: pitch for off, pitch in upper}
    lower_by_off: dict[Fraction, int] = {off: pitch for off, pitch in lower}
    common: list[Fraction] = sorted(set(upper_by_off.keys()) & set(lower_by_off.keys()))
    for off in common:
        upper_pitch: int = upper_by_off[off]
        lower_pitch: int = lower_by_off[off]
        interval: int = upper_pitch - lower_pitch
        if interval < constraint.min_interval:
            violations.append(VoiceViolation(
                type="spacing_too_close",
                offset=off,
                upper_index=upper_index,
                lower_index=lower_index,
                upper_pitch=upper_pitch,
                lower_pitch=lower_pitch,
            ))
        elif interval > constraint.max_interval:
            violations.append(VoiceViolation(
                type="spacing_too_wide",
                offset=off,
                upper_index=upper_index,
                lower_index=lower_index,
                upper_pitch=upper_pitch,
                lower_pitch=lower_pitch,
            ))
        if not constraint.allow_crossing and upper_pitch < lower_pitch:
            violations.append(VoiceViolation(
                type="voice_crossing",
                offset=off,
                upper_index=upper_index,
                lower_index=lower_index,
                upper_pitch=upper_pitch,
                lower_pitch=lower_pitch,
            ))
    return violations


def get_spacing_constraint(
    upper_index: int,
    lower_index: int,
    voice_count: int,
) -> SpacingConstraint:
    """Get appropriate spacing constraint for a voice pair."""
    is_outer: bool = upper_index == 0 and lower_index == voice_count - 1
    if is_outer:
        return SPACING_OUTER
    is_bass_adjacent: bool = lower_index == voice_count - 1
    if is_bass_adjacent:
        return SPACING_BASS_GAP
    return SPACING_ADJACENT_UPPER
