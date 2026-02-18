"""
subject_contours.py — Spline-based contour definitions for subject generation.

Two contour families, same architecture:

PITCH CONTOURS — waypoints (X, Y) where:
    X = normalised position along the subject, 0.0 = first note, 1.0 = last note
    Y = target cumulative pitch displacement in diatonic steps
    Waypoint (0, 0) is implicit — the interpolator prepends it automatically.

RHYTHM CONTOURS — waypoints (X, Y) where:
    X = normalised position along the subject, 0.0 = first note, 1.0 = last note
    Y = target speed level, 0.0 = fastest (semiquaver), 1.0 = slowest (crotchet)
    Waypoint (0, 0) is implicit — subjects start fast by default.

Both are linearly interpolated. Subjects are scored by RMS fit to the curve.
"""

import math

from subject_generator import NUM_DURATIONS, NUM_NOTES

# ── Pitch contour definitions ───────────────────────────────────────
# (0, 0) is always prepended — do not include it here.
PITCH_CONTOURS = {
    'arch':     [(0.35, 6),  (1.0, -7)],    # rise to peak, descend past origin
    'cascade':  [(0.1, 2),   (1.0, -10)],   # brief rise then long plunge
    'swoop':    [(0.2, 8),   (1.0, -8)],    # fast climb, long descent
    'valley':   [(0.2, -8),  (1.0, -2)],    # deep dip then recover
}

# ── Rhythm contour definitions ──────────────────────────────────────
# (0, 0) is always prepended — subjects start fast by default.
# Y: 0.0 = semiquaver, 0.5 = quaver, 1.0 = crotchet
RHYTHM_CONTOURS = {
    'motoric':    [(0.4, 0.0), (1.0, 1.0)],   # fast head, broadening tail
    'busy_brake': [(0.7, 0.1), (1.0, 0.7)],   # stays fast, late brake
}

# ── Scoring parameters ──────────────────────────────────────────────
PITCH_SCORE_WIDTH = 2.5     # RMS tolerance in diatonic steps
RHYTHM_SCORE_WIDTH = 0.3    # RMS tolerance in speed units (0..1)


def interpolate_contour(
    waypoints: list,
    num_points: int,
) -> list:
    """Linearly interpolate waypoints to get target Y at each position."""
    full = [(0.0, 0.0)] + waypoints
    targets = []
    for i in range(num_points):
        x = i / (num_points - 1)
        for j in range(len(full) - 1):
            x0, y0 = full[j]
            x1, y1 = full[j + 1]
            if x0 <= x <= x1:
                t = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
                targets.append(y0 + t * (y1 - y0))
                break
        else:
            targets.append(full[-1][1])
    return targets


def score_pitch_fit(
    ivs: tuple,
    waypoints: list,
) -> float:
    """Score how well an interval sequence tracks a pitch contour. Returns 0..1."""
    pitches = [0]
    for iv in ivs:
        pitches.append(pitches[-1] + iv)
    targets = interpolate_contour(waypoints, NUM_NOTES)
    assert len(pitches) == len(targets)
    sum_sq = sum((a - t) ** 2 for a, t in zip(pitches, targets))
    rms = math.sqrt(sum_sq / len(pitches))
    return math.exp(-(rms ** 2) / (2 * PITCH_SCORE_WIDTH ** 2))


def score_rhythm_fit(
    durs: tuple,
    waypoints: list,
) -> float:
    """Score how well a duration sequence tracks a rhythm contour. Returns 0..1."""
    scale = NUM_DURATIONS - 1
    levels = [d / scale for d in durs]
    targets = interpolate_contour(waypoints, NUM_NOTES)
    assert len(levels) == len(targets)
    sum_sq = sum((a - t) ** 2 for a, t in zip(levels, targets))
    rms = math.sqrt(sum_sq / len(levels))
    return math.exp(-(rms ** 2) / (2 * RHYTHM_SCORE_WIDTH ** 2))


# ── Legacy aliases ──────────────────────────────────────────────────
CONTOURS = PITCH_CONTOURS
CONTOUR_SCORE_WIDTH = PITCH_SCORE_WIDTH


def score_contour_fit(ivs: tuple, waypoints: list) -> float:
    """Legacy wrapper."""
    return score_pitch_fit(ivs, waypoints)
