"""Counterpoint and range checks for voice writing.

Pure functions.  Each returns True if the candidate passes.
Used by VoiceWriter._check_candidate to filter notes against
prior voices and range constraints.
"""
from fractions import Fraction

from shared.constants import (
    CONSONANT_INTERVALS_ABOVE_BASS,
    DIRECT_MOTION_STEP_THRESHOLD,
    INTERVAL_NAMES_SHORT,
    PERFECT_INTERVALS,
    UGLY_INTERVALS,
    UGLY_LEAP_SEMITONES,
)
from shared.voice_types import Range

_CONSONANT_IC: frozenset[int] = CONSONANT_INTERVALS_ABOVE_BASS
_PERFECT_IC: frozenset[int] = PERFECT_INTERVALS


def format_interval(semitones: int) -> str:
    """Format interval in semitones as readable name."""
    if semitones < 0:
        return f"-{format_interval(semitones=-semitones)}"
    simple: int = semitones % 12
    octaves: int = semitones // 12
    name: str = INTERVAL_NAMES_SHORT[simple]
    if octaves == 0:
        return name
    if octaves == 1 and simple == 0:
        return "P8"
    return f"{name}+{octaves}oct"


def check_consonance(midi_a: int, midi_b: int) -> bool:
    """Return True if vertical interval is consonant."""
    ic: int = abs(midi_a - midi_b) % 12
    return ic in _CONSONANT_IC


def check_direct_motion(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
) -> bool:
    """Return True if no forbidden direct motion to perfect interval.

    Direct (similar) motion to P5 or P8 is forbidden when the upper
    voice leaps (moves by more than a major second = 2 semitones).
    """
    curr_ic: int = abs(curr_upper - curr_lower) % 12
    if curr_ic not in _PERFECT_IC:
        return True
    upper_motion: int = curr_upper - prev_upper
    lower_motion: int = curr_lower - prev_lower
    if upper_motion == 0 or lower_motion == 0:
        return True
    same_direction: bool = (upper_motion > 0) == (lower_motion > 0)
    if not same_direction:
        return True
    upper_leap: bool = abs(upper_motion) > DIRECT_MOTION_STEP_THRESHOLD
    return not upper_leap


def check_melodic_interval(prev_midi: int, curr_midi: int) -> bool:
    """Return True if melodic interval is not ugly (tritone, 7th, etc.).
    
    Ugly intervals: minor 2nd (1), tritone (6), minor 7th (10), major 7th (11).
    Only rejects if interval exceeds a step (> 2 semitones).
    """
    interval: int = abs(curr_midi - prev_midi)
    if interval <= 2:
        return True
    simple: int = interval % 12
    return simple not in UGLY_INTERVALS


def check_parallels(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
) -> bool:
    """Return True if no parallel perfect intervals.

    Parallel P5->P5, P8->P8, P1->P1 with both voices moving
    in the same direction are forbidden.
    """
    prev_ic: int = abs(prev_upper - prev_lower) % 12
    if prev_ic not in _PERFECT_IC:
        return True
    curr_ic: int = abs(curr_upper - curr_lower) % 12
    if curr_ic != prev_ic:
        return True
    upper_motion: int = curr_upper - prev_upper
    lower_motion: int = curr_lower - prev_lower
    if upper_motion == 0 or lower_motion == 0:
        return True
    same_direction: bool = (upper_motion > 0) == (lower_motion > 0)
    return not same_direction


def check_range(midi: int, actuator_range: Range) -> bool:
    """Return True if MIDI pitch is within actuator range."""
    return actuator_range.low <= midi <= actuator_range.high


def check_strong_beat_consonance(
    candidate_midi: int,
    prior_midi: int,
    offset: Fraction,
    metre: str,
) -> bool:
    """Return True if consonant on strong beat, or not a strong beat."""
    if not _is_strong_beat(offset=offset, metre=metre):
        return True
    return check_consonance(midi_a=candidate_midi, midi_b=prior_midi)


def check_voice_overlap(
    candidate_midi: int,
    candidate_offset: Fraction,
    prior_notes_by_offset: dict[Fraction, list[int]],
    prev_offset: Fraction | None,
) -> bool:
    """Return True if candidate doesn't move to pitch just vacated by prior voice.
    
    Voice overlap occurs when one voice moves to a pitch that another voice
    just left at the previous offset.
    """
    if prev_offset is None:
        return True
    prev_pitches: list[int] = prior_notes_by_offset.get(prev_offset, [])
    curr_pitches: list[int] = prior_notes_by_offset.get(candidate_offset, [])
    for prev_pitch in prev_pitches:
        if prev_pitch == candidate_midi and prev_pitch not in curr_pitches:
            return False
    return True


def _is_strong_beat(offset: Fraction, metre: str) -> bool:
    """Return True if offset is a strong beat position."""
    num_str: str
    den_str: str
    num_str, den_str = metre.split("/")
    num: int = int(num_str)
    den: int = int(den_str)
    bar_length: Fraction = Fraction(num, den)
    beat_unit: Fraction = Fraction(1, den)
    offset_in_bar: Fraction = offset % bar_length
    if num == 4:
        return offset_in_bar in (Fraction(0), beat_unit * 2)
    return offset_in_bar == Fraction(0)
