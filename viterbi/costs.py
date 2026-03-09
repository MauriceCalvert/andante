"""Cost function for viterbi pathfinding.

Every musical preference is an additive cost term. Lower = better.

Dissonance is assessed at departure: when transitioning from pitch A to
pitch B, we evaluate A's dissonance with full knowledge of both approach
(from the predecessor) and departure (to B).
"""
import logging
from dataclasses import dataclass

_log: logging.Logger = logging.getLogger(__name__)

from viterbi.mtypes import AffinityContext
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

# Hard constraint sentinel — transition is forbidden
HARD = float("inf")

# Step size (interval between consecutive follower pitches)
COST_STEP_UNISON = 15.0       # stasis: must exceed third to prevent plateaus
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
COST_CONTRARY_BONUS = -4.0    # reward contrary motion (doubled from -2.0)
COST_OBLIQUE_BONUS = 0.0      # oblique is neutral (was -0.5)
COST_SIMILAR_PENALTY = 2.5    # similar motion penalised (was 1.0)

# Direct / hidden perfects: similar motion into P1/P5/P8
COST_DIRECT_PERFECT = 60.0    # approaching perfect consonance by similar motion

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
COST_SUSPENSION_REWARD = -18.0         # reward: prepared dissonance resolving down by step
COST_ACCENTED_PASSING_TONE = 6.0       # stepwise through-motion on strong beat
COST_UNPREPARED_STRONG_DISS = 120.0    # unprepared strong-beat dissonance

# Compound melody: implied-voice dissonance on wide leaps
COMPOUND_MELODY_LEAP_THRESHOLD: int = 3
# diatonic steps: 4th or larger triggers implied-voice check.
# A 3rd is a routine arpeggio step; the listener does not sustain it.
# This filter also naturally excludes suspensions, which are prepared
# stepwise, not by leaps.

COST_COMPOUND_MELODY_DISSONANCE: float = 18.0
# Comparable to COST_HALF_RESOLVED: a departure pitch that no longer
# fits the chord is roughly as bad as a half-resolved dissonance.
# Tunable by listening.

# Phrase position
COST_CADENCE_BONUS = -2.5     # discount for stepwise approach near end
CADENCE_ONSET = 0.65          # phrase position where cadence shaping begins

# Contour shaping (registral arc)
COST_CONTOUR = 1.5            # per scale-degree distance from contour target

# Cross-relations
COST_CROSS_RELATION = 30.0

# Voice spacing (graduated ramp)
SPACING_CRITICAL = 7            # below this: voices merge (severe)
SPACING_TIGHT = 10              # below this: uncomfortable
IDEAL_SPACING_LOW = 12          # lower edge of comfort zone (a 10th)
IDEAL_SPACING_HIGH = 24         # upper edge of comfort zone (2 octaves)
SPACING_WIDE = 28               # above this: losing connection
COST_SPACING_CRITICAL = 25.0    # per semitone below SPACING_CRITICAL
COST_SPACING_TIGHT = 10.0       # per semitone below SPACING_TIGHT
COST_SPACING_WIDE = 3.0         # per semitone above IDEAL_SPACING_HIGH
COST_SPACING_EXTREME = 6.0      # per semitone above SPACING_WIDE

# Interval quality on strong beats
COST_PERFECT_ON_STRONG = 1.5

# Chord-tone preference (schema-derived)
COST_NON_CHORD_TONE = 5.0     # non-chord-tone on strong beat

# Degree affinity bonus (tunable proxy — adjusted after TB-1b)
COST_DEGREE_AFFINITY_BONUS: float = 3.0   # max discount for most-emphasised degree

# Interval affinity bonus (TB-2a)
COST_INTERVAL_AFFINITY_BONUS: float = 4.0  # max discount for most-common subject interval

# Vertical genome bias (TB-5b)
COST_VERTICAL_GENOME_BONUS: float = 3.0   # max discount for matching genome interval at phrase position

# Tritone surcharge (ic=6 is uniquely harsh in two-part texture)
COST_TRITONE = 80.0

# Voice crossing
COST_VOICE_CROSSING_BASE = 15.0           # flat penalty when follower enters other voice's register
COST_VOICE_CROSSING_PER_SEMITONE = 3.0    # additional cost per semitone of crossing depth

# Local replica of CROSS_RELATION_PAIRS from shared/constants.py
# Pairs of pitch classes that form chromatic cross-relations
_CROSS_RELATION_PAIRS = frozenset({
    (0, 1),   # C / C#
    (2, 3),   # D / D#
    (5, 6),   # F / F#
    (7, 8),   # G / G#
    (9, 10),  # A / A#
})


@dataclass(frozen=True)
class FollowerStep:
    """Per-beat state of the follower voice (M002 bundle for pairwise/transition cost)."""
    prev_pitch: int
    curr_pitch: int
    prev_beat_strength: str
    curr_beat_strength: str
    prev_prev_pitch: int | None
    key: KeyInfo
    prev_prev_beat_strength: str | None = None   # beat strength at t-2, for HC7


@dataclass(frozen=True)
class VoiceData:
    """Pairwise data for all existing voices at one beat transition (M002 bundle)."""
    prev_others: tuple[int, ...]
    curr_others: tuple[int, ...]
    nearby_pcs_per_voice: tuple[frozenset[int], ...]
    is_above_per_voice: tuple[bool, ...]
    prev_prev_others: tuple[int, ...] | None = None  # existing-voice pitches at t-2, for HC7


def _pitch_to_degree_index(
    pitch: int,
    key: KeyInfo,
) -> int:
    """Return 0-based degree index (0-6) for a diatonic pitch, or -1 if non-diatonic."""
    pc: int = pitch % 12
    if pc not in key.pitch_class_set:
        return -1
    pcs: list[int] = sorted(key.pitch_class_set)
    tonic_idx: int = pcs.index(key.tonic_pc)
    pc_idx: int = pcs.index(pc)
    return (pc_idx - tonic_idx) % len(pcs)


def degree_affinity_cost(
    curr_pitch: int,
    degree_affinity: tuple[float, ...],
    key: KeyInfo,
) -> float:
    """Cost bonus (negative) for pitches on subject-emphasised degrees.

    Returns -COST_DEGREE_AFFINITY_BONUS * affinity[degree] for diatonic
    pitches, 0.0 for non-diatonic.
    """
    deg_idx: int = _pitch_to_degree_index(pitch=curr_pitch, key=key)
    if deg_idx < 0:
        return 0.0
    return -COST_DEGREE_AFFINITY_BONUS * degree_affinity[deg_idx]


def interval_affinity_cost(
    prev_pitch: int,
    curr_pitch: int,
    interval_affinity: dict[int, float],
    key: KeyInfo,
) -> float:
    """Cost bonus (negative) for transitions matching subject interval vocabulary.

    Returns -COST_INTERVAL_AFFINITY_BONUS * affinity[signed_interval], or 0.0
    if the interval is absent from the affinity dict.
    """
    if prev_pitch == curr_pitch:
        signed_interval: int = 0
    else:
        step_count: int = scale_degree_distance(prev_pitch, curr_pitch, key)
        direction: int = 1 if curr_pitch > prev_pitch else -1
        signed_interval = direction * step_count
    return -COST_INTERVAL_AFFINITY_BONUS * interval_affinity.get(signed_interval, 0.0)


def vertical_genome_cost(
    follower_pitch: int,
    leader_pitch: int,
    phrase_position: float,
    genome_entries: tuple[tuple[float, int], ...],
    key: KeyInfo,
) -> float:
    """Bonus (negative cost) for matching the genome's vertical interval at phrase_position.

    Looks up the target diatonic interval from genome_entries nearest to
    phrase_position, computes the actual diatonic interval between follower and
    leader, and returns a discount proportional to how closely they match.

    Maximum discount when actual == target; zero when |diff| >= 4 scale degrees.
    """
    if not genome_entries:
        return 0.0
    target_interval: int = min(genome_entries, key=lambda e: abs(e[0] - phrase_position))[1]
    actual_interval: int = scale_degree_distance(follower_pitch, leader_pitch, key)
    diff: int = abs(actual_interval - target_interval)
    match_ratio: float = max(0.0, 1.0 - diff / 4.0)
    return -COST_VERTICAL_GENOME_BONUS * match_ratio


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
    """Cost based on relative motion between voices (contrary/oblique/similar)."""
    f_dir = curr_follower - prev_follower
    l_dir = curr_leader - prev_leader
    if f_dir * l_dir < 0:
        return COST_CONTRARY_BONUS
    if f_dir == 0 or l_dir == 0:
        return COST_OBLIQUE_BONUS
    return COST_SIMILAR_PENALTY


def direct_perfect_cost(
    prev_follower: int,
    curr_follower: int,
    prev_other: int,
    curr_other: int,
) -> float:
    """Penalise approaching a perfect consonance (P1/P5/P8) by similar motion.

    This catches both literal parallels (same interval class → same interval
    class) and hidden/direct perfects (any interval → perfect consonance) by
    similar motion.  Oblique motion into a perfect consonance is fine and
    returns 0.0.
    """
    f_dir = curr_follower - prev_follower
    l_dir = curr_other - prev_other
    # Oblique or contrary: no penalty
    if f_dir == 0 or l_dir == 0:
        return 0.0
    if f_dir * l_dir < 0:
        return 0.0
    # Similar motion: check whether arrival interval is a perfect consonance
    curr_interval = abs(curr_follower - curr_other)
    if is_perfect(curr_interval):
        return COST_DIRECT_PERFECT
    return 0.0


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
    tritone_surcharge: float = COST_TRITONE if (interval % 12) == 6 else 0.0
    if beat_strength == "strong":
        # Suspension: prepared (held from previous beat) + resolved down by step
        is_prepared = (approach_pitch is not None and approach_pitch == pitch)
        resolves_down = (departure_pitch < pitch
                         and scale_degree_distance(pitch, departure_pitch, key) == 1)
        if is_prepared and resolves_down:
            return COST_SUSPENSION_REWARD + tritone_surcharge
        # Accented passing tone: step approach + step departure, same direction
        approached_by_step = (approach_pitch is not None
                              and scale_degree_distance(approach_pitch, pitch, key) == 1)
        left_by_step = scale_degree_distance(pitch, departure_pitch, key) == 1
        if approached_by_step and left_by_step:
            approach_dir = pitch - approach_pitch
            departure_dir = departure_pitch - pitch
            if approach_dir * departure_dir > 0:
                return COST_ACCENTED_PASSING_TONE + tritone_surcharge
        # Anything else: unprepared / unresolved strong-beat dissonance
        return COST_UNPREPARED_STRONG_DISS + tritone_surcharge
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
        return base_cost * 3.0 + tritone_surcharge
    return base_cost + tritone_surcharge


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
    contour_weight: float = 1.0,
) -> float:
    """Cost of deviating from the phrase contour target pitch."""
    if contour_target == 0:
        return 0.0
    dist = scale_degree_distance(curr_pitch, contour_target, key)
    return COST_CONTOUR * contour_weight * dist


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

    Graduated ramp: steep penalty for very close voices, 0 in the ideal
    zone (12–24st), mild penalty for wide spacing.
    """
    interval = abs(follower_pitch - leader_pitch)

    if interval < SPACING_CRITICAL:
        # Steep ramp below 7st stacked on top of moderate ramp below 10st
        return (COST_SPACING_CRITICAL * (SPACING_CRITICAL - interval)
                + COST_SPACING_TIGHT * (SPACING_TIGHT - SPACING_CRITICAL))
    if interval < SPACING_TIGHT:
        # Moderate ramp between 7st and 10st
        return COST_SPACING_TIGHT * (SPACING_TIGHT - interval)
    if interval < IDEAL_SPACING_LOW:
        # Mild cost between 10st and 12st
        return 2.0 * (IDEAL_SPACING_LOW - interval)
    if interval <= IDEAL_SPACING_HIGH:
        # Ideal zone: 12–24st
        return 0.0
    if interval <= SPACING_WIDE:
        # Mild penalty above 2 octaves
        return COST_SPACING_WIDE * (interval - IDEAL_SPACING_HIGH)
    # Steep penalty above 28st
    return (COST_SPACING_WIDE * (SPACING_WIDE - IDEAL_SPACING_HIGH)
            + COST_SPACING_EXTREME * (interval - SPACING_WIDE))


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


def chord_tone_cost(
    curr_pitch: int,
    chord_pcs: frozenset[int],
    beat_strength: str,
) -> float:
    """Penalise non-chord-tones on strong beats."""
    if beat_strength != "strong":
        return 0.0
    if not chord_pcs:
        return 0.0
    if (curr_pitch % 12) in chord_pcs:
        return 0.0
    return COST_NON_CHORD_TONE


def implied_voice_dissonance_cost(
    prev_pitch: int,
    curr_pitch: int,
    chord_pcs: frozenset[int],
    key: KeyInfo,
) -> float:
    """Cost for leaps that leave an implied held pitch outside the current chord.

    On a leap of a 4th or larger, the listener sustains the departed pitch.
    If that pitch no longer fits the current chord, penalise.
    Suspensions are excluded: they are prepared stepwise, not by leaps.
    """
    leap_size: int = scale_degree_distance(prev_pitch, curr_pitch, key)
    if leap_size < COMPOUND_MELODY_LEAP_THRESHOLD:
        return 0.0
    implied_pc: int = prev_pitch % 12
    if chord_pcs:
        dissonant: bool = implied_pc not in chord_pcs
        _log.debug(
            "compound_melody chord-pcs path: prev=%d curr=%d leap=%d implied_pc=%d in_chord=%s",
            prev_pitch, curr_pitch, leap_size, implied_pc, not dissonant,
        )
        return COST_COMPOUND_MELODY_DISSONANCE if dissonant else 0.0
    # Fallback: no harmonic grid data — diatonic consonance between the two pitches.
    consonant: bool = is_consonant(abs(prev_pitch - curr_pitch))
    _log.debug(
        "compound_melody fallback path: prev=%d curr=%d leap=%d consonant=%s",
        prev_pitch, curr_pitch, leap_size, consonant,
    )
    return COST_COMPOUND_MELODY_DISSONANCE if not consonant else 0.0


def voice_crossing_cost(
    follower_pitch: int,
    other_pitch: int,
    is_above: bool,
) -> float:
    """Cost when follower crosses into other voice's register.

    is_above=True means the other voice is above the follower
    (e.g. soprano above bass). Crossing = follower above other.
    Graduated: deeper crossing costs more.
    """
    if is_above and follower_pitch > other_pitch:
        depth = follower_pitch - other_pitch
        return COST_VOICE_CROSSING_BASE + COST_VOICE_CROSSING_PER_SEMITONE * depth
    if not is_above and follower_pitch < other_pitch:
        depth = other_pitch - follower_pitch
        return COST_VOICE_CROSSING_BASE + COST_VOICE_CROSSING_PER_SEMITONE * depth
    return 0.0


def hard_constraint_cost(
    step: FollowerStep,
    voice_data: VoiceData,
) -> tuple[float, str]:
    """Hard constraints: return (HARD, rule_name) if violated, else (0.0, "").

    Five rules enforcing fundamental counterpoint correctness:
    - HC1: Anti-stasis (three consecutive identical pitches)
    - HC2: Spacing ceiling (>36 semitones)
    - HC3: Parallel perfects (5ths/octaves) between adjacent grid steps
    - HC6: Similar-motion leaps (both voices leap >=3rd in same direction)
    - HC7: Parallel perfects on consecutive strong/moderate beats separated by one
            weak-beat note (the passing-tone gap that HC3 misses)
    (HC4 tritone removed — soft COST_TRITONE handles this adequately)
    """
    prev_pitch = step.prev_pitch
    curr_pitch = step.curr_pitch
    prev_prev_pitch = step.prev_prev_pitch
    key = step.key
    curr_beat_strength = step.curr_beat_strength
    curr_others = voice_data.curr_others
    prev_others = voice_data.prev_others
    # HC1 — Anti-stasis: three consecutive identical pitches
    if prev_prev_pitch is not None:
        if prev_prev_pitch == prev_pitch == curr_pitch:
            return HARD, "HC1_stasis"
    # HC2 — Spacing ceiling: >36 semitones (3 octaves)
    # Soft cost (COST_SPACING_TOO_FAR) already penalises >24st;
    # hard limit only blocks truly absurd gaps.
    for i in range(len(curr_others)):
        if abs(curr_pitch - curr_others[i]) > 36:
            return HARD, f"HC2_spacing({abs(curr_pitch - curr_others[i])}st)"
    # HC3 — Parallel perfects: parallel 5ths/octaves
    for i in range(len(curr_others)):
        if prev_pitch != curr_pitch and prev_others[i] != curr_others[i]:
            curr_interval = abs(curr_pitch - curr_others[i])
            prev_interval = abs(prev_pitch - prev_others[i])
            if is_perfect(curr_interval) and is_perfect(prev_interval):
                if (curr_interval % 12) == (prev_interval % 12):
                    return HARD, f"HC3_parallel({curr_interval % 12})"
    # HC4 removed: tritone on strong beat is handled by soft COST_TRITONE=80.0.
    # Dominant-function intervals (degrees 4+7) are musically correct and were
    # being hard-blocked, causing fallback to soft-only for entire phrases.
    # HC6 — Similar-motion leaps into perfect consonance
    # Both voices leap >=3rd in same direction AND arrive at P1/P5/P8
    for i in range(len(curr_others)):
        f_interval = scale_degree_distance(prev_pitch, curr_pitch, key)
        l_interval = scale_degree_distance(prev_others[i], curr_others[i], key)
        f_dir = curr_pitch - prev_pitch
        l_dir = curr_others[i] - prev_others[i]
        if f_interval >= 2 and l_interval >= 2 and f_dir * l_dir > 0:
            arrival_interval = abs(curr_pitch - curr_others[i])
            if is_perfect(arrival_interval):
                return HARD, f"HC6_similar_leap(f={f_interval}d,l={l_interval}d)"
    # HC7 — Parallel perfects on consecutive strong/moderate beats, hidden by
    # one intervening weak-beat note.  HC3 checks t-1→t (adjacent steps);
    # HC7 checks t-2→t when t-1 is weak so both strong beats are t-2 and t.
    # Skip when t-2 does not exist (prev_prev_pitch is None) or the conditions
    # are not met (different beat-strength pattern).
    if (prev_prev_pitch is not None
            and step.prev_prev_beat_strength in ("strong", "moderate")
            and step.prev_beat_strength == "weak"
            and curr_beat_strength in ("strong", "moderate")
            and voice_data.prev_prev_others is not None):
        for i in range(min(len(curr_others), len(voice_data.prev_prev_others))):
            pp_other: int = voice_data.prev_prev_others[i]
            # Both voices must move (oblique from t-2→t is not a parallel)
            if prev_prev_pitch != curr_pitch and pp_other != curr_others[i]:
                pp_interval: int = abs(prev_prev_pitch - pp_other)
                curr_interval_hc7: int = abs(curr_pitch - curr_others[i])
                if is_perfect(pp_interval) and is_perfect(curr_interval_hc7):
                    if (curr_interval_hc7 % 12) == (pp_interval % 12):
                        return HARD, f"HC7_strong_parallel({curr_interval_hc7 % 12})"
    return 0.0, ""


def pairwise_cost(
    step: FollowerStep,
    prev_other: int,
    curr_other: int,
    nearby_other_pcs: frozenset[int],
    is_above: bool,
) -> dict[str, float]:
    """Cost terms between the follower and one existing voice.

    Evaluated once per existing voice, then summed by transition_cost.
    """
    mc = motion_cost(
        prev_follower=step.prev_pitch,
        curr_follower=step.curr_pitch,
        prev_leader=prev_other,
        curr_leader=curr_other,
    )
    dc = dissonance_at_departure(
        pitch=step.prev_pitch,
        leader_pitch=prev_other,
        beat_strength=step.prev_beat_strength,
        approach_pitch=step.prev_prev_pitch,
        departure_pitch=step.curr_pitch,
        key=step.key,
    )
    xrc = cross_relation_cost(
        curr_pitch=step.curr_pitch,
        nearby_leader_pcs=nearby_other_pcs,
    )
    spc = spacing_cost(
        follower_pitch=step.curr_pitch,
        leader_pitch=curr_other,
    )
    iqc = interval_quality_cost(
        follower_pitch=step.curr_pitch,
        leader_pitch=curr_other,
        beat_strength=step.curr_beat_strength,
    )
    vcc = voice_crossing_cost(
        follower_pitch=step.curr_pitch,
        other_pitch=curr_other,
        is_above=is_above,
    )
    dpc = direct_perfect_cost(
        prev_follower=step.prev_pitch,
        curr_follower=step.curr_pitch,
        prev_other=prev_other,
        curr_other=curr_other,
    )
    return {
        "motion": mc,
        "diss": dc,
        "cross_rel": xrc,
        "spacing": spc,
        "iv_qual": iqc,
        "crossing": vcc,
        "direct_perf": dpc,
    }


def transition_cost(
    step: FollowerStep,
    voice_data: VoiceData,
    run_count: int,
    phrase_position: float,
    target_pitch: int,
    contour_target: int,
    chord_pcs: frozenset[int],
    hard_constraints: bool,
    affinity: AffinityContext | None = None,
) -> tuple[float, dict[str, float]]:
    """Total cost of one transition, with itemised breakdown.

    Melodic terms depend on the follower only.  Pairwise terms are
    evaluated once per existing voice and summed.
    """
    key = step.key
    prev_pitch = step.prev_pitch
    curr_pitch = step.curr_pitch
    curr_others = voice_data.curr_others
    prev_others = voice_data.prev_others
    contour_weight: float = (
        affinity.contour.weight if (affinity is not None and affinity.contour is not None) else 1.0
    )
    # Hard constraints check (short-circuits if violated)
    if hard_constraints:
        hc, hc_rule = hard_constraint_cost(step=step, voice_data=voice_data)
        if hc == HARD:
            return HARD, {"hard": HARD, "total": HARD, "rule": hc_rule}

    # Melodic terms (follower only)
    sc = step_cost(prev_pitch, curr_pitch, key)
    lrc = leap_recovery_cost(step.prev_prev_pitch, prev_pitch, curr_pitch, key)
    zc = zigzag_cost(step.prev_prev_pitch, prev_pitch, curr_pitch, key)
    prc = pitch_return_cost(step.prev_prev_pitch, curr_pitch)
    rp = run_penalty(run_count)
    pp = phrase_position_cost(curr_pitch, target_pitch, phrase_position, key)
    cc = contour_cost(curr_pitch, contour_target, key, contour_weight=contour_weight)
    ctc = chord_tone_cost(curr_pitch, chord_pcs, step.curr_beat_strength)
    ivdc: float = implied_voice_dissonance_cost(
        prev_pitch=prev_pitch,
        curr_pitch=curr_pitch,
        chord_pcs=chord_pcs,
        key=key,
    )
    dac: float = 0.0
    if affinity is not None and affinity.degree_affinity is not None:
        dac = degree_affinity_cost(
            curr_pitch=curr_pitch,
            degree_affinity=affinity.degree_affinity,
            key=key,
        )
    iac: float = 0.0
    if affinity is not None and affinity.interval_affinity is not None:
        iac = interval_affinity_cost(
            prev_pitch=prev_pitch,
            curr_pitch=curr_pitch,
            interval_affinity=affinity.interval_affinity,
            key=key,
        )
    vgc: float = 0.0
    if affinity is not None and affinity.genome_entries is not None and curr_others:
        vgc = vertical_genome_cost(
            follower_pitch=curr_pitch,
            leader_pitch=curr_others[0],
            phrase_position=phrase_position,
            genome_entries=affinity.genome_entries,
            key=key,
        )

    # Pairwise terms (sum over all existing voices)
    mc_total = 0.0
    dc_total = 0.0
    xrc_total = 0.0
    spc_total = 0.0
    iqc_total = 0.0
    vcc_total = 0.0
    dpc_total = 0.0
    for i in range(len(prev_others)):
        pw = pairwise_cost(
            step=step,
            prev_other=prev_others[i],
            curr_other=curr_others[i],
            nearby_other_pcs=voice_data.nearby_pcs_per_voice[i],
            is_above=voice_data.is_above_per_voice[i],
        )
        mc_total += pw["motion"]
        dc_total += pw["diss"]
        xrc_total += pw["cross_rel"]
        spc_total += pw["spacing"]
        iqc_total += pw["iv_qual"]
        vcc_total += pw["crossing"]
        dpc_total += pw["direct_perf"]

    total = (sc + mc_total + lrc + zc + prc + rp + dc_total
             + pp + xrc_total + spc_total + iqc_total + vcc_total + cc + ctc
             + ivdc + dpc_total + dac + iac + vgc)
    breakdown = {
        "step": sc,
        "motion": mc_total,
        "leap_rec": lrc,
        "zigzag": zc,
        "pitch_ret": prc,
        "run": rp,
        "diss": dc_total,
        "phrase": pp,
        "cross_rel": xrc_total,
        "spacing": spc_total,
        "iv_qual": iqc_total,
        "crossing": vcc_total,
        "direct_perf": dpc_total,
        "contour": cc,
        "chord": ctc,
        "implied_v": ivdc,
        "deg_aff": dac,
        "iv_aff": iac,
        "vg": vgc,
        "total": total,
    }
    return total, breakdown
