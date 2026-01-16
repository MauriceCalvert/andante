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


def check_cadence_fifth(
    soprano: list[tuple[Fraction, int]],
    tonic_pitch_class: int,
    cadence_type: str | None,
) -> list[Violation]:
    """Check that fifth scale degree doesn't appear in soprano at final cadence.

    CPE Bach §36: "In a final cadence the fifth must never appear in the upper voice."

    Args:
        soprano: Soprano notes as (offset, pitch) tuples
        tonic_pitch_class: MIDI pitch class of tonic (0-11, where C=0)
        cadence_type: Type of cadence ("authentic", "half", etc.) or None

    Returns:
        List of violations if soprano ends on fifth at authentic cadence
    """
    violations: list[Violation] = []

    # Only check authentic (final) cadences
    if cadence_type != "authentic" or not soprano:
        return violations

    # Fifth scale degree is 7 semitones above tonic
    fifth_pitch_class: int = (tonic_pitch_class + 7) % 12

    # Check final soprano note
    final_offset, final_pitch = soprano[-1]
    if final_pitch % 12 == fifth_pitch_class:
        violations.append(
            Violation(
                type="cadence_fifth",
                offset=final_offset,
                soprano_pitch=final_pitch,
                bass_pitch=0,
            )
        )

    return violations


def check_metrical_stress(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
    bar_duration: Fraction,
    max_tied_subdivisions: int = 2,
) -> list[Violation]:
    """Check that accompaniment maintains metrical stress when melody rests.

    Koch sections 13-14: When melody has tied notes or rests, the accompanying
    voice must maintain metrical motion. Maximum 2 consecutive subdivisions
    can be tied before accompaniment is required.

    Args:
        soprano: Soprano notes as (offset, pitch) tuples
        bass: Bass notes as (offset, pitch) tuples
        bar_duration: Duration of one bar
        max_tied_subdivisions: Maximum silent span before bass required

    Returns:
        List of violations where bass fails to provide metrical support
    """
    violations: list[Violation] = []

    if not soprano or not bass:
        return violations

    # Sort by offset
    soprano_sorted = sorted(soprano, key=lambda x: x[0])
    bass_sorted = sorted(bass, key=lambda x: x[0])

    # Build bass attack times for quick lookup
    bass_attacks: set[Fraction] = {off for off, _ in bass_sorted}

    # Subdivision is typically 1/8 or 1/4 of a beat (use 1/8 of bar as proxy)
    subdivision: Fraction = bar_duration / Fraction(8)
    max_gap: Fraction = subdivision * max_tied_subdivisions

    # Find gaps in soprano attacks and check if bass fills them
    for i in range(len(soprano_sorted) - 1):
        curr_off: Fraction = soprano_sorted[i][0]
        next_off: Fraction = soprano_sorted[i + 1][0]
        gap: Fraction = next_off - curr_off

        if gap > max_gap:
            # Check if bass has any attack in this span
            bass_in_span: bool = any(
                curr_off < off < next_off for off in bass_attacks
            )
            if not bass_in_span:
                violations.append(
                    Violation(
                        type="metrical_stress",
                        offset=curr_off,
                        soprano_pitch=soprano_sorted[i][1],
                        bass_pitch=0,
                    )
                )

    return violations


# =============================================================================
# Phase 1: Voice-Leading Hard Constraints (baroque_plan.md)
# =============================================================================

# Consonance definitions (semitones mod 12)
CONSONANT_INTERVALS: frozenset[int] = frozenset({0, 3, 4, 7, 8, 9, 12})
DISSONANT_INTERVALS: frozenset[int] = frozenset({1, 2, 5, 6, 10, 11})


def is_similar_motion(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
) -> bool:
    """Check if both voices move in the same direction (similar motion)."""
    upper_motion: int = curr_upper - prev_upper
    lower_motion: int = curr_lower - prev_lower
    if upper_motion == 0 or lower_motion == 0:
        return False  # Oblique motion, not similar
    return (upper_motion > 0) == (lower_motion > 0)


def detect_direct_perfect(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Detect direct (hidden) fifths and octaves between outer voices.

    Fux I.15: When outer voices arrive at a perfect consonance (fifth, octave, unison)
    by similar motion and the soprano leaps (moves more than 2 semitones), it is a
    violation. Exception: soprano moving by step is allowed.

    Args:
        soprano: Soprano notes as (offset, pitch) tuples
        bass: Bass notes as (offset, pitch) tuples

    Returns:
        List of violations for direct fifths/octaves
    """
    violations: list[Violation] = []
    sop_by_off: dict[Fraction, int] = {off: pitch for off, pitch in soprano}
    bass_by_off: dict[Fraction, int] = {off: pitch for off, pitch in bass}
    common: list[Fraction] = sorted(set(sop_by_off.keys()) & set(bass_by_off.keys()))

    for i in range(1, len(common)):
        prev_off: Fraction = common[i - 1]
        curr_off: Fraction = common[i]
        prev_sop: int = sop_by_off[prev_off]
        prev_bass: int = bass_by_off[prev_off]
        curr_sop: int = sop_by_off[curr_off]
        curr_bass: int = bass_by_off[curr_off]

        # Check if arriving at perfect consonance (unison, fifth, octave)
        arriving_interval: int = abs(curr_sop - curr_bass) % 12
        if arriving_interval not in (0, 7):  # 0=unison/octave, 7=fifth
            continue

        # Check for similar motion
        if not is_similar_motion(prev_sop, prev_bass, curr_sop, curr_bass):
            continue

        # Check if soprano leaps (> 2 semitones)
        soprano_motion: int = abs(curr_sop - prev_sop)
        if soprano_motion <= 2:
            continue  # Stepwise motion is allowed (Fux exception)

        # Determine violation type
        violation_type: str = "direct_fifth" if arriving_interval == 7 else "direct_octave"
        violations.append(Violation(
            type=violation_type,
            offset=curr_off,
            soprano_pitch=curr_sop,
            bass_pitch=curr_bass,
        ))

    return violations


def detect_direct_perfect_pair(
    upper: list[tuple[Fraction, int]],
    lower: list[tuple[Fraction, int]],
    upper_index: int,
    lower_index: int,
) -> list[VoiceViolation]:
    """Detect direct fifths/octaves between any voice pair (N-voice version)."""
    violations: list[VoiceViolation] = []
    upper_by_off: dict[Fraction, int] = {off: pitch for off, pitch in upper}
    lower_by_off: dict[Fraction, int] = {off: pitch for off, pitch in lower}
    common: list[Fraction] = sorted(set(upper_by_off.keys()) & set(lower_by_off.keys()))

    for i in range(1, len(common)):
        prev_off: Fraction = common[i - 1]
        curr_off: Fraction = common[i]
        prev_upper: int = upper_by_off[prev_off]
        prev_lower: int = lower_by_off[prev_off]
        curr_upper: int = upper_by_off[curr_off]
        curr_lower: int = lower_by_off[curr_off]

        arriving_interval: int = abs(curr_upper - curr_lower) % 12
        if arriving_interval not in (0, 7):
            continue

        if not is_similar_motion(prev_upper, prev_lower, curr_upper, curr_lower):
            continue

        upper_motion: int = abs(curr_upper - prev_upper)
        if upper_motion <= 2:
            continue

        violation_type: str = "direct_fifth" if arriving_interval == 7 else "direct_octave"
        violations.append(VoiceViolation(
            type=violation_type,
            offset=curr_off,
            upper_index=upper_index,
            lower_index=lower_index,
            upper_pitch=curr_upper,
            lower_pitch=curr_lower,
        ))

    return violations


def is_strong_beat(offset: Fraction, bar_duration: Fraction) -> bool:
    """Check if offset falls on a strong beat (downbeat or mid-bar)."""
    beat_in_bar: Fraction = offset % bar_duration
    # Strong beats: 0 (downbeat) and half of bar
    return beat_in_bar == 0 or beat_in_bar == bar_duration / 2


def validate_dissonance(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
    bar_duration: Fraction,
) -> list[Violation]:
    """Validate that all dissonances are properly prepared and resolved.

    Fux II.1-3: Dissonances on strong beats must be:
    1. Prepared: same pitch present on previous weak beat
    2. Resolved: step down to consonance (exception: leading tone may resolve up)

    Weak-beat dissonances must be:
    - Passing tones (stepwise approach AND departure)
    - Neighbor tones (step away and return)
    - Anticipations (same pitch follows)

    Args:
        soprano: Soprano notes as (offset, pitch) tuples
        bass: Bass notes as (offset, pitch) tuples
        bar_duration: Duration of one bar

    Returns:
        List of violations for unprepared/unresolved dissonances
    """
    violations: list[Violation] = []
    sop_by_off: dict[Fraction, int] = {off: pitch for off, pitch in soprano}
    bass_by_off: dict[Fraction, int] = {off: pitch for off, pitch in bass}
    common: list[Fraction] = sorted(set(sop_by_off.keys()) & set(bass_by_off.keys()))

    for i, curr_off in enumerate(common):
        curr_sop: int = sop_by_off[curr_off]
        curr_bass: int = bass_by_off[curr_off]
        interval: int = abs(curr_sop - curr_bass) % 12

        if interval not in DISSONANT_INTERVALS:
            continue  # Consonant, no check needed

        strong: bool = is_strong_beat(curr_off, bar_duration)

        if strong:
            # Strong-beat dissonance: must be prepared
            if i > 0:
                prev_off: Fraction = common[i - 1]
                prev_sop: int = sop_by_off[prev_off]
                # Preparation: soprano pitch must be same as previous
                if prev_sop != curr_sop:
                    violations.append(Violation(
                        type="dissonance_unprepared",
                        offset=curr_off,
                        soprano_pitch=curr_sop,
                        bass_pitch=curr_bass,
                    ))
            else:
                # No previous beat to prepare from
                violations.append(Violation(
                    type="dissonance_unprepared",
                    offset=curr_off,
                    soprano_pitch=curr_sop,
                    bass_pitch=curr_bass,
                ))

            # Must also resolve (check next note)
            if i < len(common) - 1:
                next_off: Fraction = common[i + 1]
                next_sop: int = sop_by_off[next_off]
                next_bass: int = bass_by_off[next_off]
                resolution_interval: int = abs(next_sop - next_bass) % 12
                soprano_motion: int = next_sop - curr_sop

                # Resolution must be to consonance by step
                if resolution_interval in DISSONANT_INTERVALS:
                    violations.append(Violation(
                        type="dissonance_unresolved",
                        offset=curr_off,
                        soprano_pitch=curr_sop,
                        bass_pitch=curr_bass,
                    ))
                elif abs(soprano_motion) > 2:
                    # Not stepwise resolution
                    violations.append(Violation(
                        type="dissonance_unresolved",
                        offset=curr_off,
                        soprano_pitch=curr_sop,
                        bass_pitch=curr_bass,
                    ))
                elif soprano_motion > 0 and interval != 11:
                    # Resolved upward but not a leading tone (major 7th = 11 semitones)
                    # Leading tone (11 semitones above bass) may resolve up
                    violations.append(Violation(
                        type="dissonance_resolved_up",
                        offset=curr_off,
                        soprano_pitch=curr_sop,
                        bass_pitch=curr_bass,
                    ))

        else:
            # Weak-beat dissonance: must be passing, neighbor, or anticipation
            is_valid: bool = False

            if i > 0 and i < len(common) - 1:
                prev_off: Fraction = common[i - 1]
                next_off: Fraction = common[i + 1]
                prev_sop: int = sop_by_off[prev_off]
                next_sop: int = sop_by_off[next_off]
                motion_in: int = curr_sop - prev_sop
                motion_out: int = next_sop - curr_sop

                # Passing tone: stepwise in same direction
                if abs(motion_in) <= 2 and abs(motion_out) <= 2:
                    if (motion_in > 0) == (motion_out > 0) and motion_in != 0 and motion_out != 0:
                        is_valid = True  # Passing tone

                # Neighbor tone: step away and return
                if abs(motion_in) <= 2 and abs(motion_out) <= 2:
                    if curr_sop != prev_sop and next_sop == prev_sop:
                        is_valid = True  # Neighbor tone

                # Anticipation: same pitch follows
                if next_sop == curr_sop:
                    is_valid = True  # Anticipation

            if not is_valid:
                violations.append(Violation(
                    type="dissonance_by_leap",
                    offset=curr_off,
                    soprano_pitch=curr_sop,
                    bass_pitch=curr_bass,
                ))

    return violations


def detect_voice_overlap(
    voices: list[list[tuple[Fraction, int]]],
) -> list[VoiceViolation]:
    """Detect voice overlap across time slices.

    Kirnberger II.5: A voice should not cross the previous position of an adjacent
    voice. This creates confusing voice leading even when the voices don't
    simultaneously cross.

    Checks: upper[t+1] < lower[t] or lower[t+1] > upper[t] for adjacent pairs.

    Args:
        voices: List of voice note lists, ordered from highest to lowest
                (soprano=0, alto=1, tenor=2, bass=3)

    Returns:
        List of violations for voice overlap
    """
    violations: list[VoiceViolation] = []

    for voice_idx in range(len(voices) - 1):
        upper: list[tuple[Fraction, int]] = voices[voice_idx]
        lower: list[tuple[Fraction, int]] = voices[voice_idx + 1]

        upper_by_off: dict[Fraction, int] = {off: pitch for off, pitch in upper}
        lower_by_off: dict[Fraction, int] = {off: pitch for off, pitch in lower}
        all_offsets: list[Fraction] = sorted(set(upper_by_off.keys()) | set(lower_by_off.keys()))

        prev_upper: int | None = None
        prev_lower: int | None = None

        for off in all_offsets:
            curr_upper: int | None = upper_by_off.get(off)
            curr_lower: int | None = lower_by_off.get(off)

            # Update with current values if present
            if curr_upper is not None and prev_lower is not None:
                # Upper voice at current time vs lower voice at previous time
                if curr_upper < prev_lower:
                    violations.append(VoiceViolation(
                        type="voice_overlap",
                        offset=off,
                        upper_index=voice_idx,
                        lower_index=voice_idx + 1,
                        upper_pitch=curr_upper,
                        lower_pitch=prev_lower,
                    ))

            if curr_lower is not None and prev_upper is not None:
                # Lower voice at current time vs upper voice at previous time
                if curr_lower > prev_upper:
                    violations.append(VoiceViolation(
                        type="voice_overlap",
                        offset=off,
                        upper_index=voice_idx,
                        lower_index=voice_idx + 1,
                        upper_pitch=prev_upper,
                        lower_pitch=curr_lower,
                    ))

            # Update previous values
            if curr_upper is not None:
                prev_upper = curr_upper
            if curr_lower is not None:
                prev_lower = curr_lower

    return violations


# =============================================================================
# Phase 2: Melodic Constraints (baroque_plan.md)
# =============================================================================

@dataclass(frozen=True)
class MelodicPenalty:
    """Melodic constraint penalty (soft constraint)."""
    type: str
    offset: Fraction
    pitch: int
    cost: int


def check_leap_compensation(
    melody: list[tuple[Fraction, int]],
) -> list[MelodicPenalty]:
    """Check that leaps are followed by contrary stepwise motion.

    Fux I.11: After a leap (> 2 semitones), the melody should compensate with
    stepwise motion in the opposite direction.

    Args:
        melody: Notes as (offset, pitch) tuples

    Returns:
        List of penalties for uncompensated leaps (10 points each)
    """
    penalties: list[MelodicPenalty] = []
    if len(melody) < 3:
        return penalties

    sorted_melody: list[tuple[Fraction, int]] = sorted(melody, key=lambda x: x[0])

    for i in range(len(sorted_melody) - 2):
        off1, p1 = sorted_melody[i]
        off2, p2 = sorted_melody[i + 1]
        off3, p3 = sorted_melody[i + 2]

        interval1: int = p2 - p1
        interval2: int = p3 - p2

        # Check if first interval is a leap
        if abs(interval1) <= 2:
            continue  # Not a leap

        # Compensation: following interval should be step in opposite direction
        is_step: bool = abs(interval2) <= 2
        is_contrary: bool = (interval1 > 0) != (interval2 > 0) and interval2 != 0

        if not (is_step and is_contrary):
            penalties.append(MelodicPenalty(
                type="leap_not_compensated",
                offset=off2,
                pitch=p2,
                cost=10,
            ))

    return penalties


def check_consecutive_leaps(
    melody: list[tuple[Fraction, int]],
) -> list[MelodicPenalty]:
    """Check for two consecutive leaps in the same direction.

    Fux I.11: Two leaps in the same direction create awkward melodic lines.

    Args:
        melody: Notes as (offset, pitch) tuples

    Returns:
        List of penalties for consecutive same-direction leaps (15 points each)
    """
    penalties: list[MelodicPenalty] = []
    if len(melody) < 3:
        return penalties

    sorted_melody: list[tuple[Fraction, int]] = sorted(melody, key=lambda x: x[0])

    for i in range(len(sorted_melody) - 2):
        off1, p1 = sorted_melody[i]
        off2, p2 = sorted_melody[i + 1]
        off3, p3 = sorted_melody[i + 2]

        interval1: int = p2 - p1
        interval2: int = p3 - p2

        # Both must be leaps (> 2 semitones)
        if abs(interval1) <= 2 or abs(interval2) <= 2:
            continue

        # Same direction
        if (interval1 > 0) == (interval2 > 0):
            penalties.append(MelodicPenalty(
                type="consecutive_leaps_same_direction",
                offset=off2,
                pitch=p2,
                cost=15,
            ))

    return penalties


def check_tritone_outline(
    melody: list[tuple[Fraction, int]],
) -> list[MelodicPenalty]:
    """Check for tritone outlined within 4 notes.

    Fux I.10: A melodic line should not outline a tritone (6 semitones) within
    a short span, as it creates tonal ambiguity.

    Args:
        melody: Notes as (offset, pitch) tuples

    Returns:
        List of penalties for tritone outlines (20 points each)
    """
    penalties: list[MelodicPenalty] = []
    if len(melody) < 4:
        return penalties

    sorted_melody: list[tuple[Fraction, int]] = sorted(melody, key=lambda x: x[0])

    for i in range(len(sorted_melody) - 3):
        off1, p1 = sorted_melody[i]
        off4, p4 = sorted_melody[i + 3]

        outer_interval: int = abs(p4 - p1) % 12
        if outer_interval == 6:  # Tritone
            penalties.append(MelodicPenalty(
                type="tritone_outline",
                offset=off1,
                pitch=p1,
                cost=20,
            ))

    return penalties


def check_forbidden_intervals(
    melody: list[tuple[Fraction, int]],
) -> list[MelodicPenalty]:
    """Check for forbidden melodic intervals.

    Fux I.10: Certain intervals should be avoided in melodic lines:
    - Augmented intervals (tritone = 6 semitones)
    - Sevenths (10, 11 semitones)
    - Intervals larger than an octave (> 12 semitones)

    Args:
        melody: Notes as (offset, pitch) tuples

    Returns:
        List of penalties for forbidden intervals
    """
    penalties: list[MelodicPenalty] = []
    if len(melody) < 2:
        return penalties

    sorted_melody: list[tuple[Fraction, int]] = sorted(melody, key=lambda x: x[0])

    for i in range(len(sorted_melody) - 1):
        off1, p1 = sorted_melody[i]
        off2, p2 = sorted_melody[i + 1]

        interval: int = abs(p2 - p1)

        # Tritone (augmented fourth)
        if interval == 6:
            penalties.append(MelodicPenalty(
                type="leap_augmented",
                offset=off2,
                pitch=p2,
                cost=30,
            ))
        # Seventh (minor or major)
        elif interval in (10, 11):
            penalties.append(MelodicPenalty(
                type="leap_seventh",
                offset=off2,
                pitch=p2,
                cost=25,
            ))
        # Beyond octave
        elif interval > 12:
            penalties.append(MelodicPenalty(
                type="leap_beyond_octave",
                offset=off2,
                pitch=p2,
                cost=30,
            ))

    return penalties


def calculate_melodic_penalty(
    melody: list[tuple[Fraction, int]],
) -> tuple[int, list[MelodicPenalty]]:
    """Calculate total melodic penalty for a phrase.

    Aggregates all melodic constraint penalties. If total > 50, the phrase
    should be rejected and trigger backtracking.

    Args:
        melody: Notes as (offset, pitch) tuples

    Returns:
        Tuple of (total_penalty, list of individual penalties)
    """
    all_penalties: list[MelodicPenalty] = []
    all_penalties.extend(check_leap_compensation(melody))
    all_penalties.extend(check_consecutive_leaps(melody))
    all_penalties.extend(check_tritone_outline(melody))
    all_penalties.extend(check_forbidden_intervals(melody))

    total: int = sum(p.cost for p in all_penalties)
    return total, all_penalties


# =============================================================================
# Phase 5: Cadence Validation (baroque_plan.md)
# =============================================================================

def validate_leading_tone_resolution(
    soprano: list[tuple[Fraction, int]],
    tonic_pitch_class: int,
) -> list[Violation]:
    """Validate that leading tones resolve upward to tonic.

    Fux III.2: The leading tone (degree 7) must resolve upward by step to
    the tonic. This is a fundamental rule of tonal voice-leading.

    Args:
        soprano: Soprano notes as (offset, pitch) tuples
        tonic_pitch_class: MIDI pitch class of tonic (0-11)

    Returns:
        List of violations for unresolved leading tones
    """
    violations: list[Violation] = []
    if len(soprano) < 2:
        return violations

    # Leading tone is 11 semitones above tonic (or 1 below)
    leading_tone_pc: int = (tonic_pitch_class + 11) % 12

    sorted_soprano: list[tuple[Fraction, int]] = sorted(soprano, key=lambda x: x[0])

    for i in range(len(sorted_soprano) - 1):
        off, pitch = sorted_soprano[i]
        next_off, next_pitch = sorted_soprano[i + 1]

        if pitch % 12 == leading_tone_pc:
            # This is a leading tone - must resolve up to tonic
            expected_resolution: int = (pitch % 12 + 1) % 12
            actual_resolution: int = next_pitch % 12

            # Check if it resolved to tonic (could be octave above)
            if actual_resolution != tonic_pitch_class:
                violations.append(Violation(
                    type="leading_tone_unresolved",
                    offset=off,
                    soprano_pitch=pitch,
                    bass_pitch=0,
                ))
            elif next_pitch < pitch:
                # Resolved down instead of up
                violations.append(Violation(
                    type="leading_tone_resolved_down",
                    offset=off,
                    soprano_pitch=pitch,
                    bass_pitch=0,
                ))

    return violations


def validate_cadence_bass_motion(
    bass: list[tuple[Fraction, int]],
    cadence_type: str,
    tonic_pitch_class: int,
) -> list[Violation]:
    """Validate that bass motion matches the declared cadence type.

    Args:
        bass: Bass notes as (offset, pitch) tuples
        cadence_type: Type of cadence ("authentic", "half", "deceptive", "plagal")
        tonic_pitch_class: MIDI pitch class of tonic (0-11)

    Returns:
        List of violations for incorrect bass motion
    """
    violations: list[Violation] = []
    if len(bass) < 2 or not cadence_type:
        return violations

    sorted_bass: list[tuple[Fraction, int]] = sorted(bass, key=lambda x: x[0])
    penult_off, penult_pitch = sorted_bass[-2]
    final_off, final_pitch = sorted_bass[-1]

    penult_pc: int = penult_pitch % 12
    final_pc: int = final_pitch % 12

    # Expected bass motions for each cadence type
    dominant_pc: int = (tonic_pitch_class + 7) % 12  # V
    subdominant_pc: int = (tonic_pitch_class + 5) % 12  # IV
    submediant_pc: int = (tonic_pitch_class + 9) % 12  # vi

    if cadence_type == "authentic":
        # V -> I
        if penult_pc != dominant_pc or final_pc != tonic_pitch_class:
            violations.append(Violation(
                type="cadence_bass_motion",
                offset=final_off,
                soprano_pitch=0,
                bass_pitch=final_pitch,
            ))

    elif cadence_type == "half":
        # -> V (any approach)
        if final_pc != dominant_pc:
            violations.append(Violation(
                type="cadence_bass_motion",
                offset=final_off,
                soprano_pitch=0,
                bass_pitch=final_pitch,
            ))

    elif cadence_type == "deceptive":
        # V -> vi
        if penult_pc != dominant_pc or final_pc != submediant_pc:
            violations.append(Violation(
                type="cadence_bass_motion",
                offset=final_off,
                soprano_pitch=0,
                bass_pitch=final_pitch,
            ))

    elif cadence_type == "plagal":
        # IV -> I
        if penult_pc != subdominant_pc or final_pc != tonic_pitch_class:
            violations.append(Violation(
                type="cadence_bass_motion",
                offset=final_off,
                soprano_pitch=0,
                bass_pitch=final_pitch,
            ))

    return violations


def validate_cadence_preparation(
    soprano: list[tuple[Fraction, int]],
    bar_duration: Fraction,
) -> list[Violation]:
    """Validate that cadence preparation is on a strong beat.

    The penultimate note of a cadence (the preparation/approach) should
    fall on a strong beat for proper metric emphasis.

    Args:
        soprano: Soprano notes as (offset, pitch) tuples
        bar_duration: Duration of one bar

    Returns:
        List of violations for weak-beat cadence preparation
    """
    violations: list[Violation] = []
    if len(soprano) < 2:
        return violations

    sorted_soprano: list[tuple[Fraction, int]] = sorted(soprano, key=lambda x: x[0])
    penult_off, penult_pitch = sorted_soprano[-2]

    if not is_strong_beat(penult_off, bar_duration):
        violations.append(Violation(
            type="cadence_preparation_weak",
            offset=penult_off,
            soprano_pitch=penult_pitch,
            bass_pitch=0,
        ))

    return violations
