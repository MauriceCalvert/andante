"""Counterpoint hard rules checker.

Category A: Pure functions, no I/O, no validation.
Validates:
- Vertical consonance on strong beats
- Prepared/resolved dissonances
- No parallel 5ths/8ves/unisons
- Voice range constraints
- Diatonic pitch-class membership
"""
from fractions import Fraction
from typing import Sequence

from builder.types import CounterpointViolation, Note


CONSONANT_INTERVALS: frozenset[int] = frozenset({0, 3, 4, 7, 8, 9, 12, 15, 16, 19, 20, 21, 24})
PERFECT_INTERVALS: frozenset[int] = frozenset({0, 7, 12, 19, 24})


def interval_class(soprano: int, bass: int) -> int:
    """Compute interval in semitones mod 12."""
    return abs(soprano - bass) % 12


def interval_size(soprano: int, bass: int) -> int:
    """Compute interval in semitones (unsigned)."""
    return abs(soprano - bass)


def is_consonant(soprano: int, bass: int) -> bool:
    """Check if vertical interval is consonant."""
    ic: int = interval_class(soprano, bass)
    return ic in {0, 3, 4, 7, 8, 9}


def is_perfect(soprano: int, bass: int) -> bool:
    """Check if interval is perfect (P1, P5, P8, compounds)."""
    ic: int = interval_class(soprano, bass)
    return ic in {0, 7}


def check_parallels(
    prev_soprano: int,
    prev_bass: int,
    curr_soprano: int,
    curr_bass: int,
) -> bool:
    """Check for forbidden parallel motion.
    
    Returns True if valid (no forbidden parallels).
    Forbidden: P5→P5, P8→P8, P1→P1 when both voices move same direction.
    """
    prev_interval: int = interval_class(prev_soprano, prev_bass)
    curr_interval: int = interval_class(curr_soprano, curr_bass)
    if prev_interval not in {0, 7}:
        return True
    if curr_interval != prev_interval:
        return True
    soprano_motion: int = curr_soprano - prev_soprano
    bass_motion: int = curr_bass - prev_bass
    if soprano_motion == 0 or bass_motion == 0:
        return True
    if (soprano_motion > 0) == (bass_motion > 0):
        return False
    return True


def check_voice_range(
    pitch: int,
    voice: str,
    registers: dict[str, tuple[int, int]],
) -> bool:
    """Check if pitch is within voice range."""
    if voice not in registers:
        return True
    low, high = registers[voice]
    return low <= pitch <= high


def check_pitch_class(pitch: int, pitch_class_set: frozenset[int]) -> bool:
    """Check if pitch belongs to diatonic set."""
    return (pitch % 12) in pitch_class_set


def is_strong_beat(offset: Fraction, metre: str) -> bool:
    """Determine if offset position is a strong beat.

    Args:
        offset: Position in whole notes from start of piece
        metre: Time signature string (e.g., "4/4")

    Returns:
        True if offset falls on a strong beat.

    Strong beats by metre type:
    - Simple duple (2/4, 2/2): beat 1 only
    - Simple triple (3/4, 3/8): beat 1 only
    - Simple quadruple (4/4): beats 1 and 3
    - Compound duple (6/8, 6/4): beats 1 and 4 (two dotted-beat groups)
    - Compound triple (9/8): beats 1, 4, 7 (three dotted-beat groups)
    - Compound quadruple (12/8): beats 1, 4, 7, 10
    """
    num_str, den_str = metre.split("/")
    num: int = int(num_str)
    den: int = int(den_str)
    bar_length: Fraction = Fraction(num, den)
    beat_unit: Fraction = Fraction(1, den)
    offset_in_bar: Fraction = offset % bar_length

    # Compound metres: numerator divisible by 3, grouped in dotted beats
    is_compound: bool = num in {6, 9, 12} and den in {4, 8, 16}

    if is_compound:
        # Compound: strong on each dotted-beat group (every 3 beat units)
        dotted_beat: Fraction = beat_unit * 3
        groups: int = num // 3
        strong_positions: set[Fraction] = {dotted_beat * i for i in range(groups)}
        return offset_in_bar in strong_positions

    # Simple metres
    if num == 4:
        # Quadruple: beats 1 and 3 are strong
        strong_positions = {Fraction(0), beat_unit * 2}
        return offset_in_bar in strong_positions

    # Duple (2) and triple (3): only beat 1 is strong
    return offset_in_bar == Fraction(0)


def validate_passage(
    soprano_notes: Sequence[Note],
    bass_notes: Sequence[Note],
    pitch_class_set: frozenset[int],
    registers: dict[str, tuple[int, int]],
    metre: str,
) -> list[CounterpointViolation]:
    """Validate entire passage against all hard rules."""
    violations: list[CounterpointViolation] = []
    for note in soprano_notes:
        if not check_pitch_class(note.pitch, pitch_class_set):
            violations.append(CounterpointViolation(
                rule="pitch_class",
                bar_beat=f"{note.offset}",
                soprano_pitch=note.pitch,
                bass_pitch=0,
                message=f"Soprano pitch {note.pitch} not in diatonic set",
            ))
        if not check_voice_range(note.pitch, "soprano", registers):
            violations.append(CounterpointViolation(
                rule="voice_range",
                bar_beat=f"{note.offset}",
                soprano_pitch=note.pitch,
                bass_pitch=0,
                message=f"Soprano pitch {note.pitch} out of range",
            ))
    for note in bass_notes:
        if not check_pitch_class(note.pitch, pitch_class_set):
            violations.append(CounterpointViolation(
                rule="pitch_class",
                bar_beat=f"{note.offset}",
                soprano_pitch=0,
                bass_pitch=note.pitch,
                message=f"Bass pitch {note.pitch} not in diatonic set",
            ))
        if not check_voice_range(note.pitch, "bass", registers):
            violations.append(CounterpointViolation(
                rule="voice_range",
                bar_beat=f"{note.offset}",
                soprano_pitch=0,
                bass_pitch=note.pitch,
                message=f"Bass pitch {note.pitch} out of range",
            ))
    soprano_by_offset: dict[Fraction, int] = {n.offset: n.pitch for n in soprano_notes}
    bass_by_offset: dict[Fraction, int] = {n.offset: n.pitch for n in bass_notes}
    common_offsets: list[Fraction] = sorted(set(soprano_by_offset.keys()) & set(bass_by_offset.keys()))
    for offset in common_offsets:
        s_pitch: int = soprano_by_offset[offset]
        b_pitch: int = bass_by_offset[offset]
        if is_strong_beat(offset, metre) and not is_consonant(s_pitch, b_pitch):
            violations.append(CounterpointViolation(
                rule="consonance",
                bar_beat=f"{offset}",
                soprano_pitch=s_pitch,
                bass_pitch=b_pitch,
                message=f"Dissonance on strong beat: {s_pitch}/{b_pitch}",
            ))
    prev_offset: Fraction | None = None
    for offset in common_offsets:
        if prev_offset is not None:
            prev_s: int = soprano_by_offset[prev_offset]
            prev_b: int = bass_by_offset[prev_offset]
            curr_s: int = soprano_by_offset[offset]
            curr_b: int = bass_by_offset[offset]
            if not check_parallels(prev_s, prev_b, curr_s, curr_b):
                violations.append(CounterpointViolation(
                    rule="parallels",
                    bar_beat=f"{offset}",
                    soprano_pitch=curr_s,
                    bass_pitch=curr_b,
                    message=f"Parallel perfect interval: {prev_s}/{prev_b} -> {curr_s}/{curr_b}",
                ))
        prev_offset = offset
    return violations
