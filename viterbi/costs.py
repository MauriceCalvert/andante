"""Cost function for viterbi pathfinding.

Every musical preference is an additive cost term. Lower = better.

Dissonance is assessed at departure: when transitioning from pitch A to
pitch B, we evaluate A's dissonance with full knowledge of both approach
(from the predecessor) and departure (to B).
"""
from viterbi.scale import (
    is_consonant,
    is_perfect,
    scale_degree_distance,
    KeyInfo,
    CMAJ,
)

# ---------------------------------------------------------------------------
# Cost weights
# ---------------------------------------------------------------------------

# Step size (interval between consecutive follower pitches)
COST_STEP_UNISON = 8.0        # stasis: must exceed third to prevent plateaus
COST_STEP_SECOND = 0.0        # stepwise: the ideal motion
COST_STEP_THIRD = 1.5         # small leap: routine arpeggio interval
COST_STEP_FOURTH = 5.0        # normal working leap
COST_STEP_FIFTH = 8.0         # expressive but common
COST_STEP_SIXTH = 12.0        # emphatic registral expansion
COST_STEP_SEVENTH = 20.0      # rare in stepwise counterpoint
COST_STEP_OCTAVE = 25.0       # registral shift, not melodic gesture
COST_STEP_BEYOND_OCTAVE_BASE = 25.0  # 9th+: virtually unheard of
COST_STEP_BEYOND_OCTAVE_PER = 5.0    # per additional degree beyond octave

# Relative motion between voices
COST_CONTRARY_BONUS = -2.0    # reward contrary motion
COST_OBLIQUE_BONUS = -0.5     # slight reward for oblique
COST_SIMILAR_PENALTY = 1.0    # slight cost for similar motion
COST_PARALLEL_PERFECT = 25.0  # parallel 5ths/octaves: severe

# Melodic shape
COST_LEAP_NO_RECOVERY = 20.0  # leap not followed by step in opposite direction
COST_ZIGZAG = 1.0             # step reversal: mild pressure, allows neighbour tones
COST_PITCH_RETURN = 4.0       # return to pitch two steps back (anti-oscillation)
COST_RUN_PENALTY = 5.0        # per step beyond 4 consecutive same-direction

# Dissonance (assessed with full approach + departure knowledge)
COST_PASSING_TONE = 1.0       # approached AND left by step
COST_HALF_RESOLVED = 15.0     # only one of approach/departure is stepwise
COST_UNRESOLVED_DISS = 50.0   # neither approach nor departure by step

# Strong-beat dissonance classification
COST_SUSPENSION = 2.0                  # prepared dissonance resolving down by step
COST_ACCENTED_PASSING_TONE = 6.0       # stepwise through-motion on strong beat
COST_UNPREPARED_STRONG_DISS = 50.0     # unprepared strong-beat dissonance

# Phrase position
COST_CADENCE_BONUS = -2.5     # discount for stepwise approach near end
CADENCE_ONSET = 0.65          # phrase position where cadence shaping begins

# Contour shaping (registral arc)
COST_CONTOUR = 1.5            # per scale-degree distance from contour target
ARC_PEAK_POSITION = 0.65      # phrase fraction where arc peaks
ARC_SIGMA = 0.25              # width of the bell curve
ARC_REACH = 0.5               # how far toward the range extreme (0=midpoint, 1=extreme)

# Cross-relations
COST_CROSS_RELATION = 30.0

# Voice spacing
COST_SPACING_TOO_CLOSE = 8.0    # interval < 5 semitones (< P4)
COST_SPACING_TOO_FAR = 4.0      # interval > 26 semitones (> 2 octaves + M2)
IDEAL_SPACING_LOW = 7            # P5
IDEAL_SPACING_HIGH = 24          # 2 octaves

# Interval quality on strong beats
COST_PERFECT_ON_STRONG = 1.5

# Local replica of CROSS_RELATION_PAIRS from shared/constants.py
# Pairs of pitch classes that form chromatic cross-relations
_CROSS_RELATION_PAIRS = frozenset({
    (0, 1),   # C / C#
    (2, 3),   # D / D#
    (5, 6),   # F / F#
    (7, 8),   # G / G#
    (9, 10),  # A / A#
})


def step_cost(
    prev_pitch: int,
    curr_pitch: int,
    key: KeyInfo = CMAJ,
) -> float:
    """Cost of the melodic interval between consecutive follower pitches."""
    dist = scale_degree_distance(prev_pitch, curr_pitch, key)
    if dist == 0:
        return COST_STEP_UNISON
    if dist == 1:
        return COST_STEP_SECOND
    if dist == 2:
        return COST_STEP_THIRD
    if dist == 3:
        return COST_STEP_FOURTH
    if dist == 4:
        return COST_STEP_FIFTH
    if dist == 5:
        return COST_STEP_SIXTH
    if dist == 6:
        return COST_STEP_SEVENTH
    if dist == 7:
        return COST_STEP_OCTAVE
    return COST_STEP_BEYOND_OCTAVE_BASE + COST_STEP_BEYOND_OCTAVE_PER * (dist - 7)


def motion_cost(
    prev_follower: int,
    curr_follower: int,
    prev_leader: int,
    curr_leader: int,
) -> float:
    """Cost based on relative motion between voices."""
    f_dir = curr_follower - prev_follower
    l_dir = curr_leader - prev_leader
    if f_dir != 0 and l_dir != 0:
        interval = abs(curr_follower - curr_leader)
        if is_perfect(interval):
            prev_interval = abs(prev_follower - prev_leader)
            if is_perfect(prev_interval) and (interval % 12) == (prev_interval % 12):
                return COST_PARALLEL_PERFECT
    if f_dir * l_dir < 0:
        return COST_CONTRARY_BONUS
    if f_dir == 0 or l_dir == 0:
        return COST_OBLIQUE_BONUS
    return COST_SIMILAR_PENALTY


def leap_recovery_cost(
    prev_prev_pitch: int | None,
    prev_pitch: int,
    curr_pitch: int,
    key: KeyInfo = CMAJ,
) -> float:
    """Penalise if the previous move was a leap and this move doesn't recover."""
    if prev_prev_pitch is None:
        return 0.0
    prev_dist = scale_degree_distance(prev_prev_pitch, prev_pitch, key)
    if prev_dist < 2:
        return 0.0
    prev_dir = prev_pitch - prev_prev_pitch
    curr_dir = curr_pitch - prev_pitch
    curr_dist = scale_degree_distance(prev_pitch, curr_pitch, key)
    if curr_dist == 1 and (curr_dir * prev_dir < 0):
        return 0.0
    return COST_LEAP_NO_RECOVERY


def zigzag_cost(
    prev_prev_pitch: int | None,
    prev_pitch: int,
    curr_pitch: int,
    key: KeyInfo = CMAJ,
) -> float:
    """Penalise step-step direction reversals (oscillation)."""
    if prev_prev_pitch is None:
        return 0.0
    prev_dist = scale_degree_distance(prev_prev_pitch, prev_pitch, key)
    curr_dist = scale_degree_distance(prev_pitch, curr_pitch, key)
    if prev_dist != 1 or curr_dist != 1:
        return 0.0
    prev_dir = prev_pitch - prev_prev_pitch
    curr_dir = curr_pitch - prev_pitch
    if prev_dir * curr_dir < 0:
        return COST_ZIGZAG
    return 0.0


def pitch_return_cost(
    prev_prev_pitch: int | None,
    curr_pitch: int,
) -> float:
    """Penalise returning to the pitch two steps back (oscillation suppression).

    A single neighbour tone (C-D-C then onward) pays once. Sustained
    oscillation (C-D-C-D-C) pays at every step, accumulating cost.
    """
    if prev_prev_pitch is None:
        return 0.0
    if curr_pitch == prev_prev_pitch:
        return COST_PITCH_RETURN
    return 0.0


def run_penalty(
    run_count: int,
) -> float:
    """Penalise runs of >4 consecutive steps in the same direction."""
    if run_count > 4:
        return COST_RUN_PENALTY * (run_count - 4)
    return 0.0


def dissonance_at_departure(
    pitch: int,
    leader_pitch: int,
    beat_strength: str,
    approach_pitch: int | None,
    departure_pitch: int,
    key: KeyInfo = CMAJ,
) -> float:
    """Dissonance cost of pitch, assessed when departure is known."""
    interval = abs(pitch - leader_pitch)
    if is_consonant(interval):
        return 0.0
    if beat_strength == "strong":
        # Suspension: prepared (held from previous beat) + resolved down by step
        is_prepared = (approach_pitch is not None and approach_pitch == pitch)
        resolves_down = (departure_pitch < pitch
                         and scale_degree_distance(pitch, departure_pitch, key) == 1)
        if is_prepared and resolves_down:
            return COST_SUSPENSION
        # Accented passing tone: step approach + step departure, same direction
        approached_by_step = (approach_pitch is not None
                              and scale_degree_distance(approach_pitch, pitch, key) == 1)
        left_by_step = scale_degree_distance(pitch, departure_pitch, key) == 1
        if approached_by_step and left_by_step:
            approach_dir = pitch - approach_pitch
            departure_dir = departure_pitch - pitch
            if approach_dir * departure_dir > 0:
                return COST_ACCENTED_PASSING_TONE
        # Anything else: unprepared / unresolved strong-beat dissonance
        return COST_UNPREPARED_STRONG_DISS
    approached_by_step = (approach_pitch is not None
                          and scale_degree_distance(approach_pitch, pitch, key) == 1)
    left_by_step = scale_degree_distance(pitch, departure_pitch, key) == 1
    if approached_by_step and left_by_step:
        base_cost = COST_PASSING_TONE
    elif approached_by_step or left_by_step:
        base_cost = COST_HALF_RESOLVED
    else:
        base_cost = COST_UNRESOLVED_DISS
    # Moderate beats: 3× the weak-beat cost
    if beat_strength == "moderate":
        return base_cost * 3.0
    return base_cost


def phrase_position_cost(
    curr_pitch: int,
    target_pitch: int,
    phrase_position: float,
    key: KeyInfo = CMAJ,
) -> float:
    """Reward stepwise convergence toward the final target near cadence."""
    if phrase_position < CADENCE_ONSET:
        return 0.0
    dist = scale_degree_distance(curr_pitch, target_pitch, key)
    if dist <= 2:
        return COST_CADENCE_BONUS * phrase_position
    return 0.0


def contour_cost(
    curr_pitch: int,
    contour_target: int,
    key: KeyInfo = CMAJ,
) -> float:
    """Cost of deviating from the phrase contour target pitch."""
    if contour_target == 0:
        return 0.0
    dist = scale_degree_distance(curr_pitch, contour_target, key)
    return COST_CONTOUR * dist


def cross_relation_cost(
    curr_pitch: int,
    nearby_leader_pcs: frozenset[int],
) -> float:
    """Cost of cross-relation between voices within a beat window.

    A cross-relation occurs when a pitch class in the follower voice and its
    chromatic alteration appear in the leader voice within ±1 crotchet.
    """
    curr_pc = curr_pitch % 12
    for lpc in nearby_leader_pcs:
        pair = (min(curr_pc, lpc), max(curr_pc, lpc))
        if pair in _CROSS_RELATION_PAIRS:
            return COST_CROSS_RELATION
    return 0.0


def spacing_cost(
    follower_pitch: int,
    leader_pitch: int,
) -> float:
    """Cost of voice spacing (interval between follower and leader).

    Returns 0 if spacing is ideal (between P5 and 2 octaves).
    Penalizes voices that are too close or too far apart.
    """
    interval = abs(follower_pitch - leader_pitch)

    if interval < IDEAL_SPACING_LOW:
        return COST_SPACING_TOO_CLOSE
    if interval > IDEAL_SPACING_HIGH:
        return COST_SPACING_TOO_FAR

    return 0.0


def interval_quality_cost(
    follower_pitch: int,
    leader_pitch: int,
    beat_strength: str,
) -> float:
    """Cost of interval quality on strong beats.

    On strong beats, perfect consonances (unison, P5, octave) are slightly
    penalized to favor warmer imperfect consonances (3rds, 6ths).
    """
    if beat_strength != "strong":
        return 0.0

    interval = abs(follower_pitch - leader_pitch)
    if is_perfect(interval):
        return COST_PERFECT_ON_STRONG

    return 0.0


def transition_cost(
    prev_pitch: int,
    curr_pitch: int,
    prev_leader: int,
    curr_leader: int,
    prev_beat_strength: str,
    curr_beat_strength: str,
    prev_prev_pitch: int | None = None,
    phrase_position: float = 0.0,
    target_pitch: int = 0,
    run_count: int = 1,
    key: KeyInfo = CMAJ,
    nearby_leader_pcs: frozenset[int] = frozenset(),
    contour_target: int = 0,
) -> tuple[float, dict[str, float]]:
    """Total cost of one transition, with itemised breakdown."""
    sc = step_cost(prev_pitch, curr_pitch, key)
    mc = motion_cost(prev_pitch, curr_pitch, prev_leader, curr_leader)
    lrc = leap_recovery_cost(prev_prev_pitch, prev_pitch, curr_pitch, key)
    zc = zigzag_cost(prev_prev_pitch, prev_pitch, curr_pitch, key)
    prc = pitch_return_cost(prev_prev_pitch, curr_pitch)
    rp = run_penalty(run_count)
    dc = dissonance_at_departure(
        prev_pitch, prev_leader, prev_beat_strength,
        prev_prev_pitch, curr_pitch, key,
    )
    pp = phrase_position_cost(curr_pitch, target_pitch, phrase_position, key)
    xrc = cross_relation_cost(curr_pitch, nearby_leader_pcs)
    spc = spacing_cost(curr_pitch, curr_leader)
    iqc = interval_quality_cost(curr_pitch, curr_leader, curr_beat_strength)
    cc = contour_cost(curr_pitch, contour_target, key)
    total = sc + mc + lrc + zc + prc + rp + dc + pp + xrc + spc + iqc + cc
    breakdown = {
        "step": sc,
        "motion": mc,
        "leap_rec": lrc,
        "zigzag": zc,
        "pitch_ret": prc,
        "run": rp,
        "diss": dc,
        "phrase": pp,
        "cross_rel": xrc,
        "spacing": spc,
        "iv_qual": iqc,
        "contour": cc,
        "total": total,
    }
    return total, breakdown
