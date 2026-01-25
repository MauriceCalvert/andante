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

# =============================================================================
# Corpus-Derived Melodic Cost Ratios
# =============================================================================
# Source: analyse_intervals.py run on 9 baroque pieces (source/andante/motifs/frequencies/)
#   Brandenburg Concerto No.3, Pachelbel Canon, Dido's Lament, Hallelujah,
#   La Folia, Little Fugue in G minor, Primavera, Tambourin, Toccata in D minor
#
# Method: Extract highest-pitch track (soprano/melody line) from each piece,
#   compute successive melodic intervals, aggregate across corpus (n=7426).
#
# Frequency distribution:
#   unison:     331 ( 4.5%)
#   step:      3677 (49.5%)  -- semitones 1-2
#   skip:      1547 (20.8%)  -- semitones 3-4
#   leap:      1021 (13.7%)  -- semitones 5-7
#   large_leap: 850 (11.4%)  -- semitones 8+
#
# Cost ratios derived as inverse frequency (rarer = higher cost):
#   If step cost = 1.0, then:
#     unison     = 3677 / 331  = 11.11x
#     skip       = 3677 / 1547 =  2.38x
#     leap       = 3677 / 1021 =  3.60x
#     large_leap = 3677 / 850  =  4.33x
#
# Normalised to step=1.0 base cost:
CORPUS_RATIO_UNISON: float = 11.1
CORPUS_RATIO_STEP: float = 1.0
CORPUS_RATIO_SKIP: float = 2.4
CORPUS_RATIO_LEAP: float = 3.6
CORPUS_RATIO_LARGE_LEAP: float = 4.3


def default_motive_weights(base_cost: float = 100.0) -> dict[str, float]:
    """
    Return corpus-derived melodic motion weights.

    Args:
        base_cost: Cost for a step (default 100). Other costs scale from this.

    Returns:
        Dict with keys: "unison", "step", "skip", "leap", "large_leap"
    """
    return {
        "unison": base_cost * CORPUS_RATIO_UNISON,
        "step": base_cost * CORPUS_RATIO_STEP,
        "skip": base_cost * CORPUS_RATIO_SKIP,
        "leap": base_cost * CORPUS_RATIO_LEAP,
        "large_leap": base_cost * CORPUS_RATIO_LARGE_LEAP,
    }


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
        One of: "unison", "step", "skip", "leap", "large_leap"
    """
    if semitones == 0:
        return "unison"
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
# S06: Tessitura Deviation (Two-Tier Model)
# =============================================================================
# Corpus analysis (analyse_intervals.py) shows:
#   81% of baroque melody notes fall within 7 semitones of median
#   Only 19% venture beyond, with gradual drop-off
#
# Two-tier model:
#   Within span (<=7 from median): no penalty (no gravity well)
#   Beyond span: 100 per semitone past boundary (soft fence)
#
# This allows natural melodic exploration within tessitura while
# discouraging stepwise drift outside the intended range.

TESSITURA_SPAN: int = 7  # Semitones from median (9th = 14 semitones total)
TESSITURA_BEYOND_COST: float = 100.0  # Per semitone beyond span


def cost_tessitura_deviation(
    slices: list[Slice],
    voice: int,
    median: int,
    span: int = TESSITURA_SPAN,
) -> float:
    """
    S06: Two-tier penalty for pitches outside tessitura span.

    Args:
        slices: All slices in phrase
        voice: Voice index
        median: MIDI pitch of tessitura centre
        span: Semitones from median before penalty applies (default 7)

    Returns:
        Sum of penalties for notes beyond span.
        Within span: 0 cost (no gravity toward median).
        Beyond span: 100 per semitone past boundary.
    """
    cost: float = 0.0
    for slice_ in slices:
        pitch = slice_.pitches[voice]
        if pitch is None:
            continue
        deviation: int = abs(pitch - median)
        if deviation > span:
            beyond: int = deviation - span
            cost += beyond * TESSITURA_BEYOND_COST
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
# S11: Directional Constraint (Escalating Penalty)
# =============================================================================
# Baroque melody changes direction frequently. After 4 consecutive steps
# in the same direction, penalty escalates to encourage direction change.
#
# Consecutive steps same direction | Cost
# --------------------------------|------
# 1-4                              | 0
# 5                                | 100
# 6                                | 200
# 7                                | 300
# n (where n>4)                    | (n-4) * 100

DIRECTION_THRESHOLD: int = 4  # Steps allowed before penalty starts
DIRECTION_COST_PER_STEP: float = 100.0  # Escalation rate


def cost_directional(
    slices: list[Slice],
    voice: int,
) -> float:
    """
    S11: Escalating penalty for prolonged motion in same direction.

    Args:
        slices: All slices in phrase
        voice: Voice index

    Returns:
        Sum of escalating penalties for consecutive steps in same direction.
        First 4 consecutive steps: 0 cost.
        5th consecutive step: 100.
        6th: 200, 7th: 300, etc.
    """
    pitches: list[int] = [s.pitches[voice] for s in slices if s.pitches[voice] is not None]
    if len(pitches) < 2:
        return 0.0
    cost: float = 0.0
    consecutive: int = 1
    prev_direction: int = 0  # -1 = down, 0 = none, +1 = up
    for i in range(1, len(pitches)):
        interval: int = pitches[i] - pitches[i - 1]
        if interval == 0:
            # Unison: doesn't count as continuing or breaking direction
            continue
        direction: int = 1 if interval > 0 else -1
        if direction == prev_direction:
            consecutive += 1
            if consecutive > DIRECTION_THRESHOLD:
                # Penalty escalates: 5th step = 100, 6th = 200, etc.
                cost += (consecutive - DIRECTION_THRESHOLD) * DIRECTION_COST_PER_STEP
        else:
            consecutive = 1
            prev_direction = direction
    return cost


# =============================================================================
# S10: Bass Motion Cost
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

    # S01-S04, S05, S06, S11: Per voice
    for voice in range(voice_count):
        cost += cost_melodic_motion(slices, voice, motive_weights)
        cost += cost_leap_recovery(slices, voice)
        cost += cost_tessitura_deviation(
            slices, voice, tessitura_medians[voice]
        )
        cost += cost_directional(slices, voice)

    # S07-S08, S09: Per voice pair
    for voice_a in range(voice_count):
        for voice_b in range(voice_a + 1, voice_count):
            cost += cost_voice_motion(slices, voice_a, voice_b)
            cost += cost_voice_crossing(slices, voice_a, voice_b, voice_mode)

    # S10: Bass motion (bass is the last voice)
    bass_voice: int = voice_count - 1
    cost += cost_bass_motion(slices, bass_voice)

    return cost
