"""Voice relationships - contrary motion, parallel detection.

Ported from executor/voice.py with voice-leading checks.
"""
from dataclasses import dataclass
from fractions import Fraction

from shared.parallels import is_parallel_motion
from shared.pitch import wrap_degree


@dataclass(frozen=True)
class Violation:
    """Voice-leading violation (legacy two-voice format)."""
    type: str           # 'parallel_fifth' | 'parallel_octave'
    offset: Fraction
    soprano_pitch: int
    bass_pitch: int


@dataclass(frozen=True)
class VoiceViolation:
    """Voice-leading violation for N voices."""
    type: str           # 'parallel_fifth' | 'parallel_octave' | 'voice_crossing'
    offset: Fraction
    upper_index: int
    lower_index: int
    upper_pitch: int
    lower_pitch: int


def apply_contrary_motion(
    leader_degrees: list[int],
    axis: int = 5,
) -> list[int]:
    """Generate contrary motion degrees mirrored around axis."""
    return [wrap_degree(2 * axis - d) for d in leader_degrees]


def apply_parallel_motion(
    leader_degrees: list[int],
    interval: int = 2,
) -> list[int]:
    """Generate parallel motion at fixed interval below leader."""
    return [wrap_degree(d - interval) for d in leader_degrees]


def apply_imitation(
    degrees: list[int],
    interval: int = 0,
) -> list[int]:
    """Transpose degrees by diatonic interval."""
    return [wrap_degree(d - interval) for d in degrees]


def _check_parallel_interval(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
    interval: int,
    violation_type: str,
) -> list[Violation]:
    """Check for parallel motion at a specific interval."""
    violations: list[Violation] = []
    sop_by_off: dict[Fraction, int] = {off: pitch for off, pitch in soprano}
    bass_by_off: dict[Fraction, int] = {off: pitch for off, pitch in bass}
    common: list[Fraction] = sorted(set(sop_by_off.keys()) & set(bass_by_off.keys()))
    for i in range(1, len(common)):
        prev_off: Fraction = common[i - 1]
        curr_off: Fraction = common[i]
        prev_sop: int | None = sop_by_off.get(prev_off)
        prev_bass: int | None = bass_by_off.get(prev_off)
        curr_sop: int | None = sop_by_off.get(curr_off)
        curr_bass: int | None = bass_by_off.get(curr_off)
        if all([prev_sop, prev_bass, curr_sop, curr_bass]):
            if is_parallel_motion(prev_sop, prev_bass, curr_sop, curr_bass, interval):
                violations.append(Violation(
                    type=violation_type,
                    offset=curr_off,
                    soprano_pitch=curr_sop,
                    bass_pitch=curr_bass,
                ))
    return violations


def check_parallel_fifths(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Check for parallel fifths between voices."""
    return _check_parallel_interval(soprano, bass, 7, "parallel_fifth")


def check_parallel_octaves(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Check for parallel octaves between voices."""
    return _check_parallel_interval(soprano, bass, 0, "parallel_octave")


def check_voice_leading(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Check all voice-leading rules.

    Returns:
        List of all violations (empty if clean)
    """
    violations: list[Violation] = []
    violations.extend(check_parallel_fifths(soprano, bass))
    violations.extend(check_parallel_octaves(soprano, bass))
    return violations


def check_bar_duplication(
    notes: list[tuple[Fraction, int]],
    bar_duration: Fraction,
) -> list[Violation]:
    """Check for consecutive bars with identical pitch content."""
    violations: list[Violation] = []
    bars: dict[int, tuple[int, ...]] = {}
    for offset, pitch in notes:
        bar_num: int = int(offset // bar_duration)
        if bar_num not in bars:
            bars[bar_num] = ()
        bars[bar_num] = bars[bar_num] + (pitch,)
    sorted_bars: list[int] = sorted(bars.keys())
    for i in range(1, len(sorted_bars)):
        prev_bar: int = sorted_bars[i - 1]
        curr_bar: int = sorted_bars[i]
        if curr_bar == prev_bar + 1 and bars[prev_bar] == bars[curr_bar]:
            violations.append(Violation(
                type="bar_duplication",
                offset=Fraction(curr_bar) * bar_duration,
                soprano_pitch=0,
                bass_pitch=0,
            ))
    return violations


def check_parallel_rhythm(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
    bar_duration: Fraction,
) -> list[Violation]:
    """Check for bars where soprano and bass have identical rhythm."""
    violations: list[Violation] = []
    sop_by_bar: dict[int, tuple[Fraction, ...]] = {}
    bass_by_bar: dict[int, tuple[Fraction, ...]] = {}
    for offset, _ in soprano:
        bar_num: int = int(offset // bar_duration)
        rel_offset: Fraction = offset - bar_num * bar_duration
        if bar_num not in sop_by_bar:
            sop_by_bar[bar_num] = ()
        sop_by_bar[bar_num] = sop_by_bar[bar_num] + (rel_offset,)
    for offset, _ in bass:
        bar_num: int = int(offset // bar_duration)
        rel_offset: Fraction = offset - bar_num * bar_duration
        if bar_num not in bass_by_bar:
            bass_by_bar[bar_num] = ()
        bass_by_bar[bar_num] = bass_by_bar[bar_num] + (rel_offset,)
    common_bars: set[int] = set(sop_by_bar.keys()) & set(bass_by_bar.keys())
    for bar_num in sorted(common_bars):
        if sop_by_bar[bar_num] == bass_by_bar[bar_num]:
            if len(sop_by_bar[bar_num]) >= 4:
                violations.append(Violation(
                    type="parallel_rhythm",
                    offset=Fraction(bar_num) * bar_duration,
                    soprano_pitch=0,
                    bass_pitch=0,
                ))
    return violations


def check_sequence_duplication(
    notes: list[tuple[Fraction, int]],
    window_size: int = 16,
) -> list[Violation]:
    """Check for repeated pitch sequences regardless of bar alignment.

    Reports one violation per duplicated region, not per overlapping window.
    """
    violations: list[Violation] = []
    if len(notes) < window_size * 2:
        return violations
    pitches: list[int] = [p for _, p in notes]
    offsets: list[Fraction] = [o for o, _ in notes]
    seen: dict[tuple[int, ...], int] = {}
    flagged_end: int = -1
    for i in range(len(pitches) - window_size + 1):
        if i < flagged_end:
            continue
        seq: tuple[int, ...] = tuple(pitches[i:i + window_size])
        if seq in seen:
            violations.append(Violation(
                type="sequence_duplication",
                offset=offsets[i],
                soprano_pitch=0,
                bass_pitch=0,
            ))
            flagged_end = i + window_size
        else:
            seen[seq] = i
    return violations


def check_endless_trill(
    notes: list[tuple[Fraction, int]],
    max_alternations: int = 8,
) -> list[Violation]:
    """Check for trills that alternate too many times without resolution."""
    violations: list[Violation] = []
    if len(notes) < 4:
        return violations
    pitches: list[int] = [p for _, p in notes]
    offsets: list[Fraction] = [o for o, _ in notes]
    i: int = 0
    while i < len(pitches) - 3:
        p1: int = pitches[i]
        p2: int = pitches[i + 1]
        if abs(p2 - p1) <= 2 and p2 != p1:
            count: int = 2
            j: int = i + 2
            while j < len(pitches):
                expected: int = p1 if count % 2 == 0 else p2
                if pitches[j] == expected:
                    count += 1
                    j += 1
                else:
                    break
            if count > max_alternations:
                violations.append(Violation(
                    type="endless_trill",
                    offset=offsets[i],
                    soprano_pitch=p1,
                    bass_pitch=p2,
                ))
            i = j
        else:
            i += 1
    return violations


def check_parallel_interval_pair(
    upper: list[tuple[Fraction, int]],
    lower: list[tuple[Fraction, int]],
    upper_index: int,
    lower_index: int,
    interval: int,
    violation_type: str,
) -> list[VoiceViolation]:
    """Check for parallel motion at a specific interval between two voices."""
    violations: list[VoiceViolation] = []
    upper_by_off: dict[Fraction, int] = {off: pitch for off, pitch in upper}
    lower_by_off: dict[Fraction, int] = {off: pitch for off, pitch in lower}
    common: list[Fraction] = sorted(set(upper_by_off.keys()) & set(lower_by_off.keys()))
    for i in range(1, len(common)):
        prev_off: Fraction = common[i - 1]
        curr_off: Fraction = common[i]
        prev_upper: int | None = upper_by_off.get(prev_off)
        prev_lower: int | None = lower_by_off.get(prev_off)
        curr_upper: int | None = upper_by_off.get(curr_off)
        curr_lower: int | None = lower_by_off.get(curr_off)
        if all([prev_upper, prev_lower, curr_upper, curr_lower]):
            if is_parallel_motion(prev_upper, prev_lower, curr_upper, curr_lower, interval):
                violations.append(VoiceViolation(
                    type=violation_type,
                    offset=curr_off,
                    upper_index=upper_index,
                    lower_index=lower_index,
                    upper_pitch=curr_upper,
                    lower_pitch=curr_lower,
                ))
    return violations


def check_parallel_fifths_pair(
    upper: list[tuple[Fraction, int]],
    lower: list[tuple[Fraction, int]],
    upper_index: int,
    lower_index: int,
) -> list[VoiceViolation]:
    """Check for parallel fifths between two voices."""
    return check_parallel_interval_pair(upper, lower, upper_index, lower_index, 7, "parallel_fifth")


def check_parallel_octaves_pair(
    upper: list[tuple[Fraction, int]],
    lower: list[tuple[Fraction, int]],
    upper_index: int,
    lower_index: int,
) -> list[VoiceViolation]:
    """Check for parallel octaves between two voices."""
    return check_parallel_interval_pair(upper, lower, upper_index, lower_index, 0, "parallel_octave")


def check_voice_pair(
    upper: list[tuple[Fraction, int]],
    lower: list[tuple[Fraction, int]],
    upper_index: int,
    lower_index: int,
) -> list[VoiceViolation]:
    """Check voice-leading rules for a pair of voices.

    Voice crossing allowed (L004). Only checks parallel fifths and octaves.
    """
    violations: list[VoiceViolation] = []
    violations.extend(check_parallel_fifths_pair(upper, lower, upper_index, lower_index))
    violations.extend(check_parallel_octaves_pair(upper, lower, upper_index, lower_index))
    return violations
