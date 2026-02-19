"""Subject generator — contour-guided exhaustive generation and selection.

Generates pitch sequences by exhaustive walk pruned to a contour band,
pairs with bar-aligned duration sequences, scores, then filters for
stretto potential on the shortlist only.
"""
import math
import time
from collections import Counter
from dataclasses import dataclass
from itertools import product as iter_product
from typing import Tuple

from motifs.head_generator import degrees_to_midi


# ── Duration vocabulary ─────────────────────────────────────────────
DURATION_TICKS: tuple[int, ...] = (2, 4, 8)
DURATION_NAMES: tuple[str, ...] = ('semiquaver', 'quaver', 'crotchet')
NUM_DURATIONS: int = len(DURATION_TICKS)

# ── Tick / bar geometry ─────────────────────────────────────────────
X2_TICKS_PER_WHOLE: int = 16


def _bar_x2_ticks(metre: tuple[int, int]) -> int:
    """X2-ticks per bar for the given metre."""
    return X2_TICKS_PER_WHOLE * metre[0] // metre[1]


# ── Bar-fill constraints ────────────────────────────────────────────
MIN_NOTES_PER_BAR: int = 2
MAX_NOTES_PER_BAR: int = 6
MAX_SAME_DUR_RUN: int = 4
MIN_LAST_DUR_TICKS: int = 8

# ── Pitch constraints ───────────────────────────────────────────────
PITCH_LO: int = -7
PITCH_HI: int = 7
MAX_LARGE_LEAPS: int = 4
MAX_REPEATS: int = 1
MIN_STEP_FRACTION: float = 0.5
RANGE_LO: int = 4
RANGE_HI: int = 11
MAX_SAME_SIGN_RUN: int = 5
ALLOWED_FINALS: set[int] = {0, 2, 3, 4, 5, 7, -2, -3, -4, -5, -7}
MAX_PITCH_FREQ: int = 3
CONTOUR_TOLERANCE: int = 3

# ── Contour definitions ─────────────────────────────────────────────
PITCH_CONTOURS: dict[str, list] = {
    'arch':     [(0.35, 6),  (1.0, -7)],
    'cascade':  [(0.1, 2),   (1.0, -10)],
    'swoop':    [(0.2, 8),   (1.0, -8)],
    'valley':   [(0.2, -8),  (1.0, -2)],
    'dip':      [(0.2, -8),  (1.0, 8)],
    'ascent':   [(0.1, -2),  (1.0, 10)],
}
MIRROR_PAIRS: dict[str, str] = {
    'arch': 'valley', 'valley': 'arch',
    'cascade': 'ascent', 'ascent': 'cascade',
    'swoop': 'dip', 'dip': 'swoop',
}
RHYTHM_CONTOURS: dict[str, list] = {
    'motoric':    [(0.4, 0.0), (1.0, 1.0)],
    'busy_brake': [(0.7, 0.1), (1.0, 0.7)],
}

# ── Scoring parameters ──────────────────────────────────────────────
CONTOUR_SCORE_WIDTH: float = 2.5
RHYTHM_SCORE_WIDTH: float = 0.3
IDEAL_STEP_FRACTION: float = 0.67
IDEAL_RHYTHMIC_ENTROPY: float = 0.75

# ── Selection parameters ────────────────────────────────────────────
TOP_K_PITCH: int = 200
TOP_K_DURATIONS: int = 100
TOP_K_PAIRED: int = 50



# ═══════════════════════════════════════════════════════════════════
#  GeneratedSubject
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GeneratedSubject:
    """A fully scored subject ready for answer/CS generation."""
    scale_indices: Tuple[int, ...]
    durations: Tuple[float, ...]
    midi_pitches: Tuple[int, ...]
    bars: int
    score: float
    seed: int
    mode: str
    head_name: str
    leap_size: int
    leap_direction: str
    tail_direction: str
    affect: str | None = None
    figurae_score: float = 0.0
    satisfied_figurae: Tuple[str, ...] = ()


# ═══════════════════════════════════════════════════════════════════
#  Contour interpolation
# ═══════════════════════════════════════════════════════════════════

def interpolate_contour(waypoints: list, num_points: int) -> list[float]:
    """Linearly interpolate waypoints to target pitch at each position."""
    full = [(0.0, 0.0)] + waypoints
    targets: list[float] = []
    for i in range(num_points):
        x = i / max(num_points - 1, 1)
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


# ═══════════════════════════════════════════════════════════════════
#  Stage 1: Contour-guided exhaustive pitch generation
# ═══════════════════════════════════════════════════════════════════

def generate_pitch_sequences(
    num_notes: int,
    contour_targets: list[float],
) -> list[tuple[int, ...]]:
    """Exhaustive interval enumeration pruned to a contour band."""
    num_intervals = num_notes - 1
    min_steps = math.ceil(MIN_STEP_FRACTION * num_intervals)
    results: list[tuple[int, ...]] = []
    buf: list[int] = [0] * num_intervals
    pitch_counts: list[int] = [0] * (PITCH_HI - PITCH_LO + 1)
    pitch_counts[0 - PITCH_LO] = 1
    def _recurse(
        pos: int,
        pitch: int,
        pitch_lo: int,
        pitch_hi: int,
        large_leaps: int,
        repeats: int,
        step_count: int,
        last_iv: int,
        same_sign_run: int,
    ) -> None:
        if pos == num_intervals:
            if pitch not in ALLOWED_FINALS:
                return
            if buf[num_intervals - 1] == 0:
                return
            span = pitch_hi - pitch_lo
            if span < RANGE_LO or span > RANGE_HI:
                return
            if step_count < min_steps:
                return
            results.append(tuple(buf))
            return
        remaining = num_intervals - pos
        target = contour_targets[pos + 1]
        for iv in range(-5, 6):
            abs_iv = abs(iv)
            if pos == 0 and iv == 0:
                continue
            new_pitch = pitch + iv
            # Contour band pruning
            if abs(new_pitch - target) > CONTOUR_TOLERANCE:
                continue
            if new_pitch < PITCH_LO or new_pitch > PITCH_HI:
                continue
            new_repeats = repeats + (1 if iv == 0 and pos > 0 else 0)
            if new_repeats > MAX_REPEATS:
                continue
            new_large = large_leaps + (1 if abs_iv >= 3 and pos > 0 else 0)
            if new_large > MAX_LARGE_LEAPS:
                continue
            new_lo = min(pitch_lo, new_pitch)
            new_hi = max(pitch_hi, new_pitch)
            if new_hi - new_lo > RANGE_HI:
                continue
            pi = new_pitch - PITCH_LO
            if pitch_counts[pi] >= MAX_PITCH_FREQ:
                continue
            new_step = step_count + (1 if abs_iv <= 1 and pos > 0 else 0)
            if pos > 0 and new_step + (remaining - 1) < min_steps:
                continue
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
                pos + 1, new_pitch, new_lo, new_hi,
                new_large, new_repeats, new_step, iv, new_run,
            )
            pitch_counts[pi] -= 1
    _recurse(0, 0, 0, 0, 0, 0, 0, 0, 0)
    return results


# ═══════════════════════════════════════════════════════════════════
#  Stage 1 scoring: pitch quality
# ═══════════════════════════════════════════════════════════════════

def score_pitch_sequence(
    ivs: tuple[int, ...],
    contour_targets: list[float],
) -> float:
    """Score a pitch sequence for contour fit and melodic quality."""
    num_intervals = len(ivs)
    # Contour fit (RMS distance)
    pitches = [0]
    for iv in ivs:
        pitches.append(pitches[-1] + iv)
    sum_sq = sum((p - t) ** 2 for p, t in zip(pitches, contour_targets))
    rms = math.sqrt(sum_sq / len(pitches))
    w = CONTOUR_SCORE_WIDTH
    s_contour = math.exp(-(rms ** 2) / (2 * w * w))
    # Step fraction
    steps = sum(1 for iv in ivs[1:] if abs(iv) <= 1)
    denom = max(num_intervals - 1, 1)
    step_frac = steps / denom
    s_steps = math.exp(-((step_frac - IDEAL_STEP_FRACTION) ** 2) / (2 * 0.12 * 0.12))
    # Interval variety
    abs_ivs = set(abs(iv) for iv in ivs)
    s_variety = min(len(abs_ivs) / 4.0, 1.0)
    return 0.50 * s_contour + 0.30 * s_steps + 0.20 * s_variety


# ═══════════════════════════════════════════════════════════════════
#  Stage 2: Bar-fill duration enumeration
# ═══════════════════════════════════════════════════════════════════

def enumerate_bar_fills(bar_ticks: int) -> list[tuple[int, ...]]:
    """Enumerate all valid duration-index sequences filling one bar."""
    results: list[tuple[int, ...]] = []
    max_notes: int = min(MAX_NOTES_PER_BAR, bar_ticks // min(DURATION_TICKS))
    buf: list[int] = [0] * max_notes
    def _recurse(
        pos: int,
        remaining: int,
        last_di: int,
        same_run: int,
    ) -> None:
        if remaining == 0:
            if pos >= MIN_NOTES_PER_BAR:
                results.append(tuple(buf[:pos]))
            return
        if pos >= max_notes:
            return
        for di in range(NUM_DURATIONS):
            dt = DURATION_TICKS[di]
            if dt > remaining:
                continue
            if remaining - dt > 0 and remaining - dt < min(DURATION_TICKS):
                continue
            new_run = (same_run + 1) if di == last_di else 1
            if new_run > MAX_SAME_DUR_RUN:
                continue
            buf[pos] = di
            _recurse(pos + 1, remaining - dt, di, new_run)
    _recurse(0, bar_ticks, -1, 0)
    return results


def enumerate_durations(
    n_bars: int,
    bar_ticks: int,
    note_counts: tuple[int, ...] | None = None,
) -> list[tuple[int, ...]]:
    """Combine per-bar fills into full-subject duration sequences."""
    fills = enumerate_bar_fills(bar_ticks)
    if not fills:
        return []
    results: list[tuple[int, ...]] = []
    for combo in iter_product(fills, repeat=n_bars):
        seq: tuple[int, ...] = sum(combo, ())
        n_notes = len(seq)
        if note_counts is not None and n_notes not in note_counts:
            continue
        if len(set(seq)) < 2:
            continue
        if DURATION_TICKS[seq[-1]] < MIN_LAST_DUR_TICKS:
            continue
        head_n = len(combo[0])
        tail_n = n_notes - head_n
        if tail_n > 0:
            head_ticks = sum(DURATION_TICKS[d] for d in combo[0])
            tail_ticks = sum(DURATION_TICKS[d] for d in seq[head_n:])
            if head_ticks / head_n > tail_ticks / tail_n:
                continue
        results.append(seq)
    return results


# ═══════════════════════════════════════════════════════════════════
#  Stage 2 scoring: duration quality
# ═══════════════════════════════════════════════════════════════════

def _shannon_entropy(counts: list[int], total: int) -> float:
    """Normalised Shannon entropy, 0..1."""
    if total == 0 or len(counts) <= 1:
        return 0.0
    max_ent = math.log(len(counts))
    if max_ent == 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log(p)
    return ent / max_ent


def _closeness(value: float, target: float, width: float) -> float:
    """Gaussian closeness score, 1.0 at target."""
    return math.exp(-((value - target) ** 2) / (2 * width * width))


def score_duration_sequence(durs: tuple[int, ...]) -> float:
    """Score a duration sequence for rhythmic quality."""
    n_notes = len(durs)
    head_len = n_notes // 2
    ticks = [DURATION_TICKS[d] for d in durs]
    # Entropy
    counts = list(Counter(durs).values())
    s_entropy = _closeness(_shannon_entropy(counts, n_notes), IDEAL_RHYTHMIC_ENTROPY, 0.2)
    # Head/tail contrast
    head_mean = sum(ticks[:head_len]) / max(head_len, 1)
    tail_mean = sum(ticks[head_len:]) / max(n_notes - head_len, 1)
    ratio = tail_mean / head_mean if head_mean > 0 else 1.0
    s_contrast = _closeness(ratio, 2.5, 0.6)
    # Change rate
    changes = sum(1 for i in range(1, n_notes) if durs[i] != durs[i - 1])
    s_coherence = _closeness(changes / max(n_notes - 1, 1), 0.4, 0.15)
    # Final note longer than penultimate
    s_final = 1.0 if ticks[-1] > ticks[-2] else (0.5 if ticks[-1] == ticks[-2] else 0.0)
    return 0.15 * s_entropy + 0.40 * s_contrast + 0.25 * s_coherence + 0.20 * s_final


# ═══════════════════════════════════════════════════════════════════
#  Stage 3: Pairing score (pitch + duration coupling)
# ═══════════════════════════════════════════════════════════════════

def score_pairing(
    ivs: tuple[int, ...],
    durs: tuple[int, ...],
) -> float:
    """Score how well a pitch sequence pairs with a duration sequence."""
    # Reject consecutive identical (pitch, duration) pairs
    for i in range(len(ivs)):
        if ivs[i] == 0 and durs[i] == durs[i + 1]:
            return -1.0
    ticks = [DURATION_TICKS[d] for d in durs]
    iv_abs = [abs(iv) for iv in ivs]
    # Leaps land on longer notes
    leap_bonus = 0.0
    leap_count = 0
    for i in range(len(ivs)):
        if iv_abs[i] >= 2:
            leap_count += 1
            if ticks[i + 1] >= 4:
                leap_bonus += 1.0
            elif ticks[i + 1] <= 2:
                leap_bonus -= 0.5
    s_leap = max(0.0, min(1.0, 0.5 + leap_bonus / leap_count)) if leap_count > 0 else 0.5
    # Short notes before leaps
    pre_count = 0
    pre_bonus = 0.0
    for i in range(len(ivs)):
        if iv_abs[i] >= 2:
            pre_count += 1
            if ticks[i] <= 3:
                pre_bonus += 1.0
    s_pre = pre_bonus / pre_count if pre_count > 0 else 0.5
    return 0.60 * s_leap + 0.40 * s_pre



# ═══════════════════════════════════════════════════════════════════
#  Stretto counting (delegates to analyser)
# ═══════════════════════════════════════════════════════════════════


def _ivs_durs_to_stretto_count(
    ivs: tuple[int, ...],
    durs: tuple[int, ...],
    metre: tuple[int, int],
) -> int:
    """Convert interval-index representation to degrees/durations and count self-stretto."""
    from motifs.stretto_analyser import count_self_stretto
    degrees = (0,) + tuple(sum(ivs[:i + 1]) for i in range(len(ivs)))
    durations = tuple(DURATION_TICKS[d] / X2_TICKS_PER_WHOLE for d in durs)
    return count_self_stretto(degrees, durations, metre)


# ═══════════════════════════════════════════════════════════════════
#  Melodic validators
# ═══════════════════════════════════════════════════════════════════

def _midi_intervals(midi: tuple[int, ...]) -> list[int]:
    """Semitone intervals between adjacent MIDI pitches."""
    return [midi[i + 1] - midi[i] for i in range(len(midi) - 1)]


def is_melodically_valid(midi: tuple[int, ...]) -> bool:
    """Check MIDI pitch sequence for forbidden intervals."""
    ivs = _midi_intervals(midi)
    for iv in ivs:
        a = abs(iv)
        if a == 6 or a in (10, 11):
            return False
    for i in range(len(ivs) - 1):
        if abs(ivs[i]) > 2 and abs(ivs[i + 1]) > 2:
            if (ivs[i] > 0) == (ivs[i + 1] > 0):
                return False
    if len(midi) >= 4:
        for i in range(len(midi) - 3):
            if abs(midi[i + 3] - midi[i]) == 6:
                return False
    return True


# ═══════════════════════════════════════════════════════════════════
#  Pipeline
# ═══════════════════════════════════════════════════════════════════

def _derive_leap_info(ivs: tuple[int, ...]) -> tuple[int, str, str]:
    """Derive leap_size, leap_direction, tail_direction."""
    max_abs = 0
    max_iv = 0
    for iv in ivs:
        if abs(iv) > max_abs:
            max_abs = abs(iv)
            max_iv = iv
    second_half = ivs[len(ivs) // 2:]
    net = sum(second_half)
    return (
        max_abs,
        "up" if max_iv > 0 else "down",
        "down" if net < 0 else "up",
    )


def select_subject(
    mode: str = "major",
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    target_bars: int | None = None,
    pitch_contour: str | None = None,
    rhythm_contour: str | None = None,
    note_counts: tuple[int, ...] | None = None,
    seed: int = 0,
    verbose: bool = False,
) -> GeneratedSubject:
    """Select best subject: generate, score, pair, stretto-filter."""
    if target_bars is None:
        target_bars = 3
    bar_ticks = _bar_x2_ticks(metre)
    t_start = time.time()
    if verbose:
        print(f"select_subject: mode={mode} metre={metre} bars={target_bars} seed={seed}")
    # ── Stage 2: durations (cheap, do first to know note counts) ─
    all_durs = enumerate_durations(
        n_bars=target_bars,
        bar_ticks=bar_ticks,
        note_counts=note_counts,
    )
    assert len(all_durs) > 0, f"No durations for bars={target_bars} metre={metre}"
    durs_by_count: dict[int, list[tuple[int, ...]]] = {}
    for d in all_durs:
        durs_by_count.setdefault(len(d), []).append(d)
    if verbose:
        print(f"  Durations: {len(all_durs)} sequences, counts={sorted(durs_by_count.keys())}")
    # Score and rank durations per note count
    ranked_durs: dict[int, list[tuple[float, tuple[int, ...]]]] = {}
    for nc, seqs in durs_by_count.items():
        scored = [(score_duration_sequence(d), d) for d in seqs]
        scored.sort(key=lambda x: x[0], reverse=True)
        ranked_durs[nc] = scored[:TOP_K_DURATIONS]
    # ── Determine contours ───────────────────────────────────────
    if pitch_contour is not None:
        assert pitch_contour in PITCH_CONTOURS
        p_names = [pitch_contour]
    else:
        p_names = ['arch']  # TODO: restore list(PITCH_CONTOURS.keys())
    # ── Stage 1: pitch generation per contour per note count ─────
    all_candidates: list[tuple[float, tuple[int, ...], tuple[int, ...], str]] = []
    for nc in sorted(durs_by_count.keys()):
        for pname in p_names:
            targets = interpolate_contour(PITCH_CONTOURS[pname], nc)
            t0 = time.time()
            sequences = generate_pitch_sequences(nc, targets)
            t_gen = time.time() - t0
            if not sequences:
                if verbose:
                    print(f"  {pname} {nc}n: 0 sequences")
                continue
            # Score pitch sequences
            scored_pitch = [(score_pitch_sequence(s, targets), s) for s in sequences]
            scored_pitch.sort(key=lambda x: x[0], reverse=True)
            top_pitch = scored_pitch[:TOP_K_PITCH]
            if verbose:
                print(f"  {pname} {nc}n: {len(sequences):,} sequences in {t_gen:.2f}s, top={top_pitch[0][0]:.3f}")
            # ── Stage 3: pair top pitch with top durations ───────
            pairs: list[tuple[float, tuple[int, ...], tuple[int, ...]]] = []
            for p_sc, ivs in top_pitch:
                for d_sc, durs in ranked_durs[nc]:
                    pair_sc = score_pairing(ivs, durs)
                    if pair_sc < 0:
                        continue
                    combined = 0.40 * p_sc + 0.30 * d_sc + 0.30 * pair_sc
                    pairs.append((combined, ivs, durs))
            pairs.sort(key=lambda x: x[0], reverse=True)
            # ── Stage 4: melodic + stretto filter on shortlist ────
            MIN_STRETTO: int = 2
            for combined, ivs, durs in pairs[:TOP_K_PAIRED]:
                degs = (0,) + tuple(sum(ivs[:i + 1]) for i in range(len(ivs)))
                midi = degrees_to_midi(degrees=degs, tonic_midi=tonic_midi, mode=mode)
                if not is_melodically_valid(midi):
                    continue
                total_stretto = _ivs_durs_to_stretto_count(ivs, durs, metre)
                if total_stretto < MIN_STRETTO:
                    continue
                stretto_bonus = min(total_stretto / 4.0, 1.0)
                final_score = 0.70 * combined + 0.30 * stretto_bonus
                all_candidates.append((final_score, ivs, durs, pname))
    assert len(all_candidates) > 0, "No valid subject found"
    all_candidates.sort(key=lambda x: x[0], reverse=True)
    # Deduplicate: no two picks share the same duration sequence
    seen_durs: set[tuple[int, ...]] = set()
    unique: list[tuple[float, tuple[int, ...], tuple[int, ...], str]] = []
    for entry in all_candidates:
        if entry[2] not in seen_durs:
            seen_durs.add(entry[2])
            unique.append(entry)
    pick = seed % len(unique)
    best_score, best_ivs, best_durs, best_contour = unique[pick]
    if verbose:
        gen_stretto = _ivs_durs_to_stretto_count(best_ivs, best_durs, metre)
        print(f"  Candidates: {len(all_candidates)} total, {len(unique)} unique, pick={pick}")
        print(f"  Generator stretto: {gen_stretto}")
    # ── Convert to GeneratedSubject ──────────────────────────────
    degrees = (0,) + tuple(sum(best_ivs[:i + 1]) for i in range(len(best_ivs)))
    dur_ticks = [DURATION_TICKS[d] for d in best_durs]
    bars = sum(dur_ticks) // bar_ticks
    durations = tuple(t / X2_TICKS_PER_WHOLE for t in dur_ticks)
    midi_pitches = degrees_to_midi(degrees=degrees, tonic_midi=tonic_midi, mode=mode)
    leap_size, leap_direction, tail_direction = _derive_leap_info(best_ivs)
    elapsed = time.time() - t_start
    if verbose:
        print(f"  Selected: {best_contour} {len(degrees)}n score={best_score:.4f} "
              f"bars={bars} in {elapsed:.2f}s")
        print(f"  Degrees: {degrees}")
        print(f"  Durations: {durations}")
    return GeneratedSubject(
        scale_indices=degrees,
        durations=durations,
        midi_pitches=midi_pitches,
        bars=bars,
        score=best_score,
        seed=0,
        mode=mode,
        head_name=best_contour,
        leap_size=leap_size,
        leap_direction=leap_direction,
        tail_direction=tail_direction,
    )


# ═══════════════════════════════════════════════════════════════════
#  Display helpers
# ═══════════════════════════════════════════════════════════════════

def display_subject(rank: int, score: float, ivs: tuple, durs: tuple) -> None:
    """Pretty-print a ranked subject."""
    pitches = [0]
    for iv in ivs:
        pitches.append(pitches[-1] + iv)
    dur_names = [DURATION_NAMES[d] for d in durs]
    dur_ticks = [DURATION_TICKS[d] for d in durs]
    print(f"#{rank + 1}  score={score:.4f}")
    print(f"  Pitches:    {pitches}")
    print(f"  Intervals:  {list(ivs)}")
    print(f"  Rhythm:     {dur_names}")
    print(f"  Ticks:      {dur_ticks}  total={sum(dur_ticks)}")
    print()


def decode_subject(intervals: tuple, durations: tuple) -> None:
    """Print a human-readable subject."""
    pitches = [0]
    for iv in intervals:
        pitches.append(pitches[-1] + iv)
    print(f"  Pitches:   {pitches}")
    print(f"  Intervals: {list(intervals)}")
    print(f"  Durations: {[DURATION_NAMES[d] for d in durations]}")
    print(f"  Ticks:     {[DURATION_TICKS[d] for d in durations]}")
