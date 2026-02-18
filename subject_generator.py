"""
subject_generator.py — Exhaustive enumeration of baroque subjects.

A subject is NUM_NOTES notes. Between consecutive notes are NUM_INTERVALS
intervals in scale degrees. Pitch 0 is the starting note; subsequent pitches
are the cumulative sum of intervals.

Interval and duration constraints are separable: enumerate independently,
total valid subjects = |interval_sequences| x |duration_sequences|.

Durations in ticks (1 tick = semiquaver):
    semiquaver=1  dotted_semiquaver=1.5  quaver=2  dotted_quaver=3  crotchet=4
"""

import math
import time

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# ── Duration vocabulary ─────────────────────────────────────────────
# Ticks stored as x2 to avoid floats: semiquaver=2, dotted=3, quaver=4, etc.
DURATION_TICKS = (2, 4, 8)
DURATION_NAMES = (
    'semiquaver',
    'quaver',
    'crotchet',
)
NUM_DURATIONS = len(DURATION_TICKS)

# ── Structural parameters ───────────────────────────────────────────
NUM_NOTES = 9
NUM_INTERVALS = NUM_NOTES - 1
HEAD_LEN = NUM_NOTES // 2

# ── Interval constraints ────────────────────────────────────────────
PITCH_LO = -7
PITCH_HI = 7
MAX_LARGE_LEAPS = 4        # |interval| >= 3
MAX_REPEATS = 1             # interval == 0
MIN_STEP_COUNT = math.ceil(0.5 * NUM_INTERVALS)
RANGE_LO = 4               # min span (max_pitch - min_pitch)
RANGE_HI = 11              # max span (12th in scale degrees)
MAX_SAME_SIGN_RUN = 5      # consecutive same-direction intervals (scalar runs)
ALLOWED_FINALS = {0, -2, -3, -4, -5, -7}  # 1st, 7th, 5th, 4th, 3rd, octave below

# ── Duration constraints ────────────────────────────────────────────
TICK_LO = 28                # ~1.75 bars of 4/4 (x2 ticks)
TICK_HI = 56                # 3.5 bars of 4/4 (x2 ticks)
MAX_SAME_DUR_RUN = 4        # consecutive identical durations (scalar runs)
MAX_HEAD_DUR_TICKS = 8      # head notes: up to crotchet (mordent-then-hold)
MIN_TAIL_DUR_TICKS = 2      # tail notes: semiquaver or longer (scalar runs)
MIN_LAST_DUR_TICKS = 8      # last note: crotchet


def enumerate_intervals() -> list:
    """Enumerate all valid interval sequences. Returns list of tuples."""
    results = []
    buf = [0] * NUM_INTERVALS
    pitch_counts = [0] * (PITCH_HI - PITCH_LO + 1)  # frequency of each pitch
    pitch_counts[0 - PITCH_LO] = 1  # starting pitch 0
    MAX_PITCH_FREQ = 3
    def _recurse(
        pos: int,
        pitch: int,
        pitch_lo: int,
        pitch_hi: int,
        peak_pos: int,
        large_leaps: int,
        repeats: int,
        step_count: int,
        last_iv: int,
        same_sign_run: int,
    ) -> None:
        if pos == NUM_INTERVALS:
            if pitch not in ALLOWED_FINALS:
                return
            # Last two notes must differ in pitch
            if buf[NUM_INTERVALS - 1] == 0:
                return
            # Global descent: final pitch below start
            if pitch >= 0:
                return
            span = pitch_hi - pitch_lo
            if span < RANGE_LO or span > RANGE_HI:
                return
            if step_count < MIN_STEP_COUNT:
                return
            # Peak in head (note indices 0..HEAD_LEN-1, pitch indices 0..HEAD_LEN)
            if peak_pos > HEAD_LEN:
                return
            results.append(tuple(buf))
            return
        remaining = NUM_INTERVALS - pos
        # Leap recovery disabled — was forcing monotonous sawtooth patterns
        leap_recovery = False
        for iv in range(-5, 6):
            abs_iv = abs(iv)
            # First interval must be non-zero
            if pos == 0 and iv == 0:
                continue
            # After a leap, must step back opposite direction
            if leap_recovery:
                if abs_iv != 1:
                    continue
                if (last_iv > 0) == (iv > 0):
                    continue
            # Budget checks (first interval exempt from repeat/large-leap budgets)
            new_repeats = repeats + (1 if iv == 0 and pos > 0 else 0)
            if new_repeats > MAX_REPEATS:
                continue
            new_large = large_leaps + (1 if abs_iv >= 3 and pos > 0 else 0)
            if new_large > MAX_LARGE_LEAPS:
                continue
            # Pitch range
            new_pitch = pitch + iv
            if new_pitch < PITCH_LO or new_pitch > PITCH_HI:
                continue
            new_lo = min(pitch_lo, new_pitch)
            new_hi = max(pitch_hi, new_pitch)
            if new_hi - new_lo > RANGE_HI:
                continue
            # Pitch frequency limit
            pi = new_pitch - PITCH_LO
            if pitch_counts[pi] >= MAX_PITCH_FREQ:
                continue
            # Step dominance (first interval exempt): can we still reach MIN_STEP_COUNT?
            new_step = step_count + (1 if abs_iv <= 1 and pos > 0 else 0)
            if pos > 0 and new_step + (remaining - 1) < MIN_STEP_COUNT:
                continue
            # Track peak position (pitch index = pos+1 for note after interval)
            new_peak = peak_pos
            if new_pitch > pitch_hi:
                new_peak = pos + 1
            # Same-direction run
            if iv > 0:
                new_run = (same_sign_run + 1) if same_sign_run > 0 else 1
            elif iv < 0:
                new_run = (same_sign_run - 1) if same_sign_run < 0 else -1
            else:
                new_run = 0
            if abs(new_run) > MAX_SAME_SIGN_RUN:
                continue
            buf[pos] = iv
            pitch_counts[pi] += 1
            _recurse(
                pos + 1, new_pitch, new_lo, new_hi, new_peak,
                new_large, new_repeats, new_step, iv, new_run,
            )
            pitch_counts[pi] -= 1
    t0 = time.time()
    _recurse(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    elapsed = time.time() - t0
    print(f"Interval sequences: {len(results):,} in {elapsed:.1f}s")
    return results


def enumerate_durations() -> list:
    """Enumerate all valid duration sequences. Returns list of tuples."""
    results = []
    buf = [0] * NUM_NOTES
    min_dur = min(DURATION_TICKS)
    max_dur = max(DURATION_TICKS)
    def _recurse(
        pos: int,
        ticks: int,
        same_run: int,
        last_di: int,
    ) -> None:
        if pos == NUM_NOTES:
            if ticks < TICK_LO or ticks > TICK_HI:
                return
            # Last note must be long
            if DURATION_TICKS[last_di] < MIN_LAST_DUR_TICKS:
                return
            # Head faster than tail (mean duration)
            head_t = sum(DURATION_TICKS[buf[i]] for i in range(HEAD_LEN))
            tail_t = ticks - head_t
            tail_len = NUM_NOTES - HEAD_LEN
            # head_mean < tail_mean  =>  head_t / HEAD_LEN < tail_t / tail_len
            if head_t * tail_len >= tail_t * HEAD_LEN:
                return
            # At least 2 distinct durations
            if len(set(buf)) < 2:
                return
            results.append(tuple(buf))
            return
        remaining = NUM_NOTES - pos
        for di in range(NUM_DURATIONS):
            dt = DURATION_TICKS[di]
            # Head: no dotted quavers or crotchets
            if pos < HEAD_LEN and dt > MAX_HEAD_DUR_TICKS:
                continue
            # Tail: no semiquavers
            if pos >= HEAD_LEN and dt < MIN_TAIL_DUR_TICKS:
                continue
            # Tick bounds: can we still finish in range?
            new_ticks = ticks + dt
            if new_ticks + (remaining - 1) * min_dur > TICK_HI:
                continue
            if new_ticks + (remaining - 1) * max_dur < TICK_LO:
                continue
            # No 3+ identical consecutive durations
            new_run = (same_run + 1) if di == last_di else 1
            if new_run > MAX_SAME_DUR_RUN:
                continue
            buf[pos] = di
            _recurse(pos + 1, new_ticks, new_run, di)
    t0 = time.time()
    _recurse(0, 0, 0, -1)
    elapsed = time.time() - t0
    print(f"Duration sequences: {len(results):,} in {elapsed:.1f}s")
    return results


def decode_subject(
    intervals: tuple,
    durations: tuple,
) -> None:
    """Print a human-readable subject."""
    pitches = [0]
    for iv in intervals:
        pitches.append(pitches[-1] + iv)
    dur_names = [DURATION_NAMES[d] for d in durations]
    dur_ticks = [DURATION_TICKS[d] for d in durations]
    total = sum(dur_ticks)
    print(f"  Pitches:   {pitches}")
    print(f"  Intervals: {list(intervals)}")
    print(f"  Durations: {dur_names}")
    print(f"  Ticks:     {dur_ticks}  total={total} ({total / 2:.1f} semiquavers)")


if __name__ == '__main__':
    ivs = enumerate_intervals()
    durs = enumerate_durations()
    total = len(ivs) * len(durs)
    print(f"\nTotal valid subjects: {len(ivs):,} x {len(durs):,} = {total:,}")
    if HAS_TORCH and ivs:
        iv_tensor = torch.tensor(ivs, dtype=torch.int8)
        print(f"Interval tensor: {iv_tensor.shape}, dtype={iv_tensor.dtype}")
    if HAS_TORCH and durs:
        dur_tensor = torch.tensor(durs, dtype=torch.uint8)
        print(f"Duration tensor: {dur_tensor.shape}, dtype={dur_tensor.dtype}")
    if ivs and durs:
        print(f"\nFirst:")
        decode_subject(ivs[0], durs[0])
        print(f"\nMiddle:")
        decode_subject(ivs[len(ivs) // 2], durs[len(durs) // 2])
        print(f"\nLast:")
        decode_subject(ivs[-1], durs[-1])
