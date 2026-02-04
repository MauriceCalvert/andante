"""Junction validation between consecutive gaps.

Checks that the transition from the last note of one gap to the
first note of the next gap is melodically acceptable.
"""
from shared.constants import GROTESQUE_LEAP_SEMITONES
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key

_MAX_LEAP_SEMITONES: int = 12
_UGLY_INTERVALS: frozenset[int] = frozenset({1, 6, 10, 11})


def check_junction(
    exit_pitch: DiatonicPitch,
    entry_pitch: DiatonicPitch,
    prev_leap_direction: int,
    home_key: Key,
) -> bool:
    """Return True if junction between gaps is acceptable.

    prev_leap_direction: +1 if previous gap ended with upward leap,
    -1 if downward leap, 0 if step or no previous gap.

    Checks:
    1. No grotesque leap (> octave + fifth)
    2. No consecutive leaps in same direction
    3. No augmented/diminished interval
    """
    exit_midi: int = home_key.diatonic_to_midi(dp=exit_pitch)
    entry_midi: int = home_key.diatonic_to_midi(dp=entry_pitch)
    semitones: int = abs(exit_midi - entry_midi)
    if semitones >= GROTESQUE_LEAP_SEMITONES:
        return False
    is_leap: bool = semitones > 4
    if is_leap and prev_leap_direction != 0:
        junction_direction: int = 1 if entry_midi > exit_midi else -1
        if junction_direction == prev_leap_direction:
            return False
    ic: int = semitones % 12
    if ic in _UGLY_INTERVALS and semitones > 2:
        return False
    return True
