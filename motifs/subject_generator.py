"""Subject generator using head + tail construction.

Generates Baroque-style fugue subjects by:
1. Selecting a head (opening gesture with leap + gap fill)
2. Generating a tail (contrary motion, derived rhythm, tonic resolution)
3. Combining into subjects that span an integer number of bars
4. Scoring against figurae for affect appropriateness

Usage:
    from motifs.subject_generator import generate_subject, generate_subject_batch
"""
import random
from dataclasses import dataclass
from typing import List, Tuple

from motifs.head_generator import (
    get_rhythm_cells,
    degrees_to_midi,
    Head,
    NOTE_NAMES,
    RHYTHM_CELLS_BY_METRE,
    START_DEGREES,
    MIN_DEGREE,
    MAX_DEGREE,
    MAX_INTERVAL,
    MIN_LEAP,
)
from motifs.tail_generator import (
    generate_tails_for_head,
    tail_to_degrees,
    Tail,
)
from motifs.figurae import get_figurae, score_motif_figurae, Figura
from motifs.affect_loader import get_affect_profile, score_subject_affect

# Supported metres
SUPPORTED_METRES: tuple[tuple[int, int], ...] = tuple(RHYTHM_CELLS_BY_METRE.keys())


def _bar_duration(metre: tuple[int, int]) -> float:
    """Calculate duration of one bar for a given metre."""
    return metre[0] / metre[1]


@dataclass(frozen=True)
class GeneratedSubject:
    """Result of subject generation."""
    scale_indices: Tuple[int, ...]
    durations: Tuple[float, ...]
    midi_pitches: Tuple[int, ...]
    bars: int  # Number of bars the subject spans
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


def _intervals(degrees: tuple[int, ...]) -> list[int]:
    """Compute intervals between adjacent degrees."""
    return [degrees[i + 1] - degrees[i] for i in range(len(degrees) - 1)]


def _largest_leap_position(intervals: list[int]) -> int:
    """Return 0-indexed position of largest leap, or -1 if no leap."""
    if not intervals:
        return -1
    max_size = 0
    max_pos = -1
    for i, iv in enumerate(intervals):
        if abs(iv) > max_size:
            max_size = abs(iv)
            max_pos = i
    return max_pos if max_size >= MIN_LEAP else -1


def _is_filled(intervals: list[int], leap_pos: int) -> bool:
    """Check if leap at position is followed by contrary stepwise motion."""
    if leap_pos < 0 or leap_pos >= len(intervals) - 1:
        return False
    leap_iv = intervals[leap_pos]
    next_iv = intervals[leap_pos + 1]
    if leap_iv > 0 and next_iv >= 0:
        return False
    if leap_iv < 0 and next_iv <= 0:
        return False
    return 1 <= abs(next_iv) <= 2


def _is_valid_pitch(degrees: tuple[int, ...]) -> tuple[bool, int, str]:
    """Check if pitch sequence has leap + fill. Returns (valid, leap_size, direction)."""
    intervals = _intervals(degrees)
    leap_pos = _largest_leap_position(intervals)
    if leap_pos < 0:
        return False, 0, ""
    if not _is_filled(intervals, leap_pos):
        return False, 0, ""
    leap_size = abs(intervals[leap_pos])
    direction = "up" if intervals[leap_pos] > 0 else "down"
    return True, leap_size, direction


def _random_pitch_sequence(n_notes: int, rng: random.Random) -> tuple[int, ...]:
    """Generate a random pitch sequence of given length."""
    start = rng.choice(START_DEGREES)
    degrees = [start]
    for _ in range(n_notes - 1):
        last = degrees[-1]
        # Generate valid intervals
        valid_intervals = [
            iv for iv in range(-MAX_INTERVAL, MAX_INTERVAL + 1)
            if MIN_DEGREE <= last + iv <= MAX_DEGREE
        ]
        iv = rng.choice(valid_intervals)
        degrees.append(last + iv)
    return tuple(degrees)


def _sample_valid_head(metre: tuple[int, int], rng: random.Random, max_attempts: int = 100) -> Head | None:
    """Sample a random valid head for the given metre."""
    rhythm_cells = get_rhythm_cells(metre)
    # Filter cells with rhythm variety
    valid_cells = [(r, n) for r, n in rhythm_cells if len(set(r)) >= 2]
    if not valid_cells:
        return None

    for _ in range(max_attempts):
        rhythm, rhythm_name = rng.choice(valid_cells)
        n_notes = len(rhythm)
        degrees = _random_pitch_sequence(n_notes, rng)
        valid, leap_size, direction = _is_valid_pitch(degrees)
        if valid:
            return Head(
                degrees=degrees,
                rhythm=rhythm,
                rhythm_name=rhythm_name,
                leap_size=leap_size,
                leap_direction=direction,
            )
    return None


def _crosses_barline(rhythm: tuple[float, ...], bar_dur: float) -> bool:
    """Check if any note in the rhythm crosses a barline."""
    offset = 0.0
    for dur in rhythm:
        end = offset + dur
        # Check if note spans across a bar boundary
        start_bar = int(offset / bar_dur)
        end_bar = int(end / bar_dur)
        # If end is exactly on barline, it's OK
        if abs(end % bar_dur) < 0.0001:
            end_bar = start_bar
        if start_bar != end_bar:
            return True
        offset = end
    return False


def _combine_head_tail(
    head: Head,
    tail: Tail,
    bar_dur: float,
) -> tuple[tuple[int, ...], tuple[float, ...], int] | None:
    """Combine head and tail into a single subject.

    Returns (degrees, rhythm, bars) or None if invalid.
    """
    tail_degrees = tail_to_degrees(tail, head.degrees[-1])
    full_degrees = head.degrees + tail_degrees[1:]
    full_rhythm = head.rhythm + tail.rhythm[1:]

    if _crosses_barline(full_rhythm, bar_dur):
        return None

    # Calculate number of bars
    total_dur = sum(full_rhythm)
    bars = total_dur / bar_dur
    # Must be integer number of bars
    if abs(bars - round(bars)) > 0.001:
        return None

    return full_degrees, full_rhythm, int(round(bars))


def generate_subject(
    mode: str = "major",
    metre: Tuple[int, int] = (4, 4),
    seed: int | None = None,
    tonic_midi: int = 60,
    verbose: bool = False,
    affect: str | None = None,
    max_attempts: int = 500,
) -> GeneratedSubject:
    """Generate a single subject using head + tail construction.

    Supports common time signatures: 4/4, 3/4, 2/4, 2/2, 6/8.
    Subject spans an integer number of bars determined by head+tail duration.

    If affect is provided, generates multiple candidates and returns
    the one that best satisfies the affect's figurae.
    """
    if metre not in SUPPORTED_METRES:
        raise ValueError(f"Unsupported metre {metre}. Supported: {SUPPORTED_METRES}")

    rng = random.Random(seed)
    bar_dur = _bar_duration(metre)

    # Get figurae and affect profile for this affect
    figurae_mgr = get_figurae()
    target_figurae: list[Figura] = []
    affect_profile = None
    if affect:
        target_figurae = figurae_mgr.select_for_motif(affect, tension=0.5)
        affect_profile = get_affect_profile(affect)

    if verbose:
        if affect:
            print(f"Affect: {affect}, target figurae: {[f.name for f in target_figurae]}")
            if affect_profile:
                print(f"  Profile: {affect_profile.interval_profile} intervals, {affect_profile.contour} contour")

    # Generate candidates via random sampling
    candidates: list[GeneratedSubject] = []
    target_candidates = 50 if affect else 5

    for _ in range(max_attempts):
        if len(candidates) >= target_candidates:
            break

        # Sample a valid head
        head = _sample_valid_head(metre, rng)
        if head is None:
            continue

        # Calculate remaining duration for various bar counts
        head_dur = sum(head.rhythm)

        # Try different target totals (1, 2, 3, 4 bars)
        for target_bars in [2, 1, 3, 4]:
            target_total = target_bars * bar_dur
            if target_total <= head_dur:
                continue

            tails = generate_tails_for_head(head, target_total=target_total)
            if not tails:
                continue

            tail = rng.choice(tails)
            result = _combine_head_tail(head, tail, bar_dur)
            if result is None:
                continue

            degrees, rhythm, bars = result

            # Require at least 2 distinct durations
            if len(set(rhythm)) < 2:
                continue

            # Score against figurae
            fig_score = 0.0
            satisfied: list[str] = []
            if target_figurae:
                fig_score, satisfied = score_motif_figurae(
                    list(degrees), list(rhythm), target_figurae
                )

            # Score against affect profile (contour, intervals, rhythm density)
            affect_score = 0.0
            if affect_profile:
                affect_score = score_subject_affect(degrees, rhythm, affect_profile)

            midi_pitches = degrees_to_midi(degrees, tonic_midi, mode)

            # Combined score: base + figurae + affect profile
            total_score = 1.0 + fig_score + affect_score

            subject = GeneratedSubject(
                scale_indices=degrees,
                durations=rhythm,
                midi_pitches=midi_pitches,
                bars=bars,
                score=total_score,
                seed=seed or 0,
                mode=mode,
                head_name=head.rhythm_name,
                leap_size=head.leap_size,
                leap_direction=head.leap_direction,
                tail_direction=tail.direction,
                affect=affect,
                figurae_score=fig_score,
                satisfied_figurae=tuple(satisfied),
            )
            candidates.append(subject)
            break  # Found a valid subject for this head

    if not candidates:
        raise RuntimeError(
            f"Failed to generate subject for metre {metre} after {max_attempts} attempts."
        )

    # Return best scoring candidate
    best = max(candidates, key=lambda s: s.score)

    if verbose:
        pitch_str = ' '.join(f"{NOTE_NAMES[m % 12]}{m // 12 - 1}" for m in best.midi_pitches)
        print(f"Subject: {pitch_str}")
        print(f"  Bars: {best.bars}")
        print(f"  Head: {best.head_name}, leap {best.leap_direction} {best.leap_size}")
        print(f"  Tail: {best.tail_direction}")
        if affect:
            print(f"  Figurae score: {best.figurae_score:.2f}, satisfied: {best.satisfied_figurae}")

    return best


def generate_subject_batch(
    mode: str = "major",
    metre: Tuple[int, int] = (4, 4),
    seed: int | None = None,
    tonic_midi: int = 60,
    count: int = 10,
    verbose: bool = False,
) -> List[GeneratedSubject]:
    """Generate multiple subjects with variety."""
    if metre not in SUPPORTED_METRES:
        raise ValueError(f"Unsupported metre {metre}. Supported: {SUPPORTED_METRES}")

    rng = random.Random(seed)
    bar_dur = _bar_duration(metre)

    results: List[GeneratedSubject] = []
    seen_degrees: set[tuple[int, ...]] = set()
    max_attempts = count * 50

    for _ in range(max_attempts):
        if len(results) >= count:
            break

        head = _sample_valid_head(metre, rng)
        if head is None:
            continue

        head_dur = sum(head.rhythm)

        # Try 2-bar subjects first, then others
        for target_bars in [2, 1, 3, 4]:
            target_total = target_bars * bar_dur
            if target_total <= head_dur:
                continue

            tails = generate_tails_for_head(head, target_total=target_total)
            if not tails:
                continue

            tail = rng.choice(tails)
            result = _combine_head_tail(head, tail, bar_dur)
            if result is None:
                continue

            degrees, rhythm, bars = result

            if degrees in seen_degrees:
                continue

            if len(set(rhythm)) < 2:
                continue

            seen_degrees.add(degrees)
            midi_pitches = degrees_to_midi(degrees, tonic_midi, mode)

            subject = GeneratedSubject(
                scale_indices=degrees,
                durations=rhythm,
                midi_pitches=midi_pitches,
                bars=bars,
                score=1.0,
                seed=seed or 0,
                mode=mode,
                head_name=head.rhythm_name,
                leap_size=head.leap_size,
                leap_direction=head.leap_direction,
                tail_direction=tail.direction,
            )
            results.append(subject)

            if verbose:
                pitch_str = ' '.join(f"{NOTE_NAMES[m % 12]}{m // 12 - 1}" for m in midi_pitches)
                print(f"[{len(results):02d}] {pitch_str} | {bars} bars | {head.rhythm_name}")
            break

    return results


def main() -> None:
    """Test subject generation."""
    print("Generating subjects (head + tail)...")
    print()

    subjects = generate_subject_batch(
        mode="major",
        metre=(4, 4),
        seed=42,
        tonic_midi=60,
        count=10,
        verbose=True,
    )

    print(f"\nGenerated {len(subjects)} subjects")


if __name__ == "__main__":
    main()
