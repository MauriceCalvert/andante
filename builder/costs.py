"""Soft constraint cost functions for counterpoint solver."""

from enum import Enum

from builder.slice import (
    Slice,
    melodic_interval,
    motion_type,
    extract_slice_pairs,
)

# Melodic interval thresholds (semitones)
STEP_MAX: int = 2       # Up to major second
SKIP_MAX: int = 4       # Up to major third
LEAP_MAX: int = 7       # Up to perfect fifth
# > 7 = large leap


class VoiceMode(Enum):
    """Voice interaction mode affecting crossing costs."""
    STANDARD = "standard"        # Crossing penalised (S09 positive cost)
    INTERLEAVED = "interleaved"  # Crossing encouraged (S09 negative cost)


# =============================================================================
# S01-S04: Melodic Motion Costs
# =============================================================================


def melodic_motion_category(semitones: int) -> str:
    """
    Categorise melodic interval by size.

    Args:
        semitones: Absolute melodic interval

    Returns:
        One of: "step", "skip", "leap", "large_leap"
    """
    if semitones <= STEP_MAX:
        return "step"
    if semitones <= SKIP_MAX:
        return "skip"
    if semitones <= LEAP_MAX:
        return "leap"
    return "large_leap"


def cost_melodic_motion(
    slices: list[Slice],
    voice: int,
    motive_weights: dict[str, float],
) -> float:
    """
    S01-S04: Total melodic motion cost for one voice.

    Args:
        slices: All slices in phrase
        voice: Voice index
        motive_weights: {"step": w1, "skip": w2, "leap": w3, "large_leap": w4}

    Returns:
        Sum of weights for each melodic interval in voice.
    """
    total: float = 0.0
    prev_pitch: int | None = None
    for slice_ in slices:
        pitch = slice_.pitches[voice]
        if pitch is None:
            continue
        if prev_pitch is not None:
            interval: int = abs(melodic_interval(prev_pitch, pitch))
            category: str = melodic_motion_category(interval)
            total += motive_weights[category]
        prev_pitch = pitch
    return total


# =============================================================================
# S05: Leap Recovery
# =============================================================================


def cost_leap_recovery(
    slices: list[Slice],
    voice: int,
) -> float:
    """
    S05: Penalty for leaps not followed by contrary step.

    Args:
        slices: All slices in phrase
        voice: Voice index

    Returns:
        0.5 for each leap (> 4 semitones) not followed by step in opposite direction.
    """
    cost: float = 0.0
    pitches: list[int] = [s.pitches[voice] for s in slices if s.pitches[voice] is not None]
    for i in range(len(pitches) - 2):
        interval_1: int = melodic_interval(pitches[i], pitches[i + 1])
        if abs(interval_1) <= SKIP_MAX:
            continue  # Not a leap
        interval_2: int = melodic_interval(pitches[i + 1], pitches[i + 2])
        # Check contrary motion
        contrary: bool = (interval_1 > 0) != (interval_2 > 0)
        # Check step
        is_step: bool = abs(interval_2) <= STEP_MAX
        if not (contrary and is_step):
            cost += 0.5
    return cost


# =============================================================================
# S06: Tessitura Deviation
# =============================================================================


def cost_tessitura_deviation(
    slices: list[Slice],
    voice: int,
    median: int,
) -> float:
    """
    S06: Penalty for pitches far from tessitura median.

    Args:
        slices: All slices in phrase
        voice: Voice index
        median: MIDI pitch of tessitura centre

    Returns:
        Sum of 0.1 * abs(pitch - median) for each pitch.
    """
    cost: float = 0.0
    for slice_ in slices:
        pitch = slice_.pitches[voice]
        if pitch is None:
            continue
        cost += 0.1 * abs(pitch - median)
    return cost


# =============================================================================
# S07-S08: Voice Motion Interaction
# =============================================================================


def cost_voice_motion(
    slices: list[Slice],
    voice_a: int,
    voice_b: int,
) -> float:
    """
    S07-S08: Cost for similar motion, reward for contrary.

    Args:
        slices: All slices in phrase
        voice_a: First voice index
        voice_b: Second voice index

    Returns:
        Sum of:
        - +0.3 for each "similar" or "parallel" motion
        - -0.2 for each "contrary" motion
        - 0.0 for "oblique" motion
    """
    pairs = extract_slice_pairs(slices, voice_a, voice_b)
    cost: float = 0.0
    for pair in pairs:
        pitch_a_first = pair.first.pitches[voice_a]
        pitch_a_second = pair.second.pitches[voice_a]
        pitch_b_first = pair.first.pitches[voice_b]
        pitch_b_second = pair.second.pitches[voice_b]

        # These should not be None since extract_slice_pairs filters
        assert pitch_a_first is not None
        assert pitch_a_second is not None
        assert pitch_b_first is not None
        assert pitch_b_second is not None

        motion = motion_type(
            pitch_a_first,
            pitch_a_second,
            pitch_b_first,
            pitch_b_second,
        )
        if motion in {"similar", "parallel"}:
            cost += 0.3
        elif motion == "contrary":
            cost -= 0.2
    return cost


# =============================================================================
# S09: Voice Crossing Depth
# =============================================================================


def cost_voice_crossing(
    slices: list[Slice],
    voice_upper: int,
    voice_lower: int,
    voice_mode: VoiceMode,
) -> float:
    """
    S09: Cost for voice crossing depth (mode-dependent).

    Args:
        slices: All slices in phrase
        voice_upper: Index of nominally higher voice (lower index)
        voice_lower: Index of nominally lower voice (higher index)
        voice_mode: STANDARD (penalise crossing) or INTERLEAVED (reward crossing)

    Returns:
        STANDARD mode: +0.05 * crossing_depth (penalty)
        INTERLEAVED mode: -0.05 * crossing_depth (reward)

        Crossing depth = how many semitones the lower voice exceeds the upper.

    Interleaved texture:
        Used in Goldberg-style variations where two voices weave around
        each other, creating a single composite melody. Crossings are
        not merely tolerated but actively sought to create the
        characteristic interlocking texture.
    """
    multiplier: float = 0.05 if voice_mode == VoiceMode.STANDARD else -0.05
    cost: float = 0.0
    for slice_ in slices:
        upper_pitch = slice_.pitches[voice_upper]
        lower_pitch = slice_.pitches[voice_lower]
        if upper_pitch is None or lower_pitch is None:
            continue
        if lower_pitch > upper_pitch:
            crossing_depth: int = lower_pitch - upper_pitch
            cost += multiplier * crossing_depth
    return cost


# =============================================================================
# S10: Bass Motion Cost (from test_cost.py)
# =============================================================================


def cost_bass_motion(
    slices: list[Slice],
    bass_voice: int,
) -> float:
    """
    S10: Penalty for bass motion by leap.

    Bass should move primarily by step and small skip. Leaps are penalised
    more heavily than in upper voices.

    Args:
        slices: All slices in phrase
        bass_voice: Index of bass voice

    Returns:
        Sum of costs for bass melodic motion (leaps cost more).
    """
    cost: float = 0.0
    prev_pitch: int | None = None
    for slice_ in slices:
        pitch = slice_.pitches[bass_voice]
        if pitch is None:
            continue
        if prev_pitch is not None:
            interval: int = abs(melodic_interval(prev_pitch, pitch))
            # Bass motion costs (heavier on leaps than melodic_motion)
            if interval <= STEP_MAX:
                cost += 0.1  # Steps are preferred
            elif interval <= SKIP_MAX:
                cost += 0.3  # Thirds are acceptable
            elif interval <= LEAP_MAX:
                cost += 0.6  # Fourths/fifths penalised
            else:
                cost += 1.0  # Large leaps heavily penalised
        prev_pitch = pitch
    return cost


# =============================================================================
# Aggregate Cost
# =============================================================================


def compute_total_cost(
    slices: list[Slice],
    voice_count: int,
    tessitura_medians: dict[int, int],
    motive_weights: dict[str, float],
    voice_mode: VoiceMode,
) -> float:
    """
    Compute total soft constraint cost.

    Args:
        slices: All slices in phrase
        voice_count: Number of voices
        tessitura_medians: {voice_index: median_midi_pitch}
        motive_weights: {"step": w1, "skip": w2, "leap": w3, "large_leap": w4}
        voice_mode: STANDARD or INTERLEAVED

    Returns:
        Sum of all soft constraint costs.
    """
    cost: float = 0.0

    # S01-S04, S05, S06: Per voice
    for voice in range(voice_count):
        cost += cost_melodic_motion(slices, voice, motive_weights)
        cost += cost_leap_recovery(slices, voice)
        cost += cost_tessitura_deviation(
            slices, voice, tessitura_medians[voice]
        )

    # S07-S08, S09: Per voice pair
    for voice_a in range(voice_count):
        for voice_b in range(voice_a + 1, voice_count):
            cost += cost_voice_motion(slices, voice_a, voice_b)
            cost += cost_voice_crossing(slices, voice_a, voice_b, voice_mode)

    # S10: Bass motion (bass is the last voice)
    bass_voice: int = voice_count - 1
    cost += cost_bass_motion(slices, bass_voice)

    return cost
