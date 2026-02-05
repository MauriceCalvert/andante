"""Gap-level rhythm derivation from phrase motifs.

Slices the phrase motif to cover each gap, scales to actual
gap duration.
"""
import logging
from fractions import Fraction
from builder.types import GapRhythm, RhythmicMotif, RhythmicProfile
from shared.constants import (
    VALID_DURATIONS,
)

logger = logging.getLogger(__name__)

_VALID_DURATIONS_SET: frozenset[Fraction] = frozenset(VALID_DURATIONS)


# =============================================================================
# Motif Slicing and Scaling
# =============================================================================


def _extract_motif_slice(
    pattern: tuple[Fraction, ...],
    gap_position: float,
    gap_fraction: float,
) -> tuple[tuple[Fraction, ...], tuple[int, int]]:
    """Extract the portion of a motif pattern covering a gap.

    gap_position: 0.0 to 1.0, where this gap sits in the phrase.
    gap_fraction: fraction of the phrase this gap occupies.
    Returns (slice of durations, (start_idx, end_idx)).
    """
    total_dur: Fraction = sum(pattern)
    assert total_dur > 0, "Empty motif pattern"
    target_start: Fraction = Fraction(gap_position).limit_denominator(64) * total_dur
    target_end: Fraction = target_start + Fraction(gap_fraction).limit_denominator(64) * total_dur
    cumulative: Fraction = Fraction(0)
    start_idx: int = 0
    end_idx: int = len(pattern)
    found_start: bool = False
    for i, dur in enumerate(pattern):
        if not found_start and cumulative + dur > target_start:
            start_idx = i
            found_start = True
        cumulative += dur
        if found_start and cumulative >= target_end:
            end_idx = i + 1
            break
    # Ensure at least one element
    if start_idx >= end_idx:
        end_idx = min(start_idx + 1, len(pattern))
    result: tuple[Fraction, ...] = pattern[start_idx:end_idx]
    if len(result) == 0:
        result = (pattern[-1],)
        start_idx = len(pattern) - 1
        end_idx = len(pattern)
    return result, (start_idx, end_idx)


def _scale_to_duration(
    durations: tuple[Fraction, ...],
    target_duration: Fraction,
) -> tuple[Fraction, ...]:
    """Scale a duration sequence to sum to target_duration."""
    current_sum: Fraction = sum(durations)
    assert current_sum > 0, "Cannot scale zero-duration sequence"
    if current_sum == target_duration:
        return durations
    scale_factor: Fraction = target_duration / current_sum
    scaled: list[Fraction] = [d * scale_factor for d in durations]
    # Absorb rounding error into the last duration
    residual: Fraction = target_duration - sum(scaled)
    if residual != 0:
        scaled[-1] += residual
    result: tuple[Fraction, ...] = tuple(scaled)
    assert sum(result) == target_duration, (
        f"Scaling error: sum={sum(result)}, target={target_duration}"
    )
    return result


def _snap_to_valid(dur: Fraction) -> Fraction:
    """Snap a duration to the nearest valid duration if close."""
    if dur in _VALID_DURATIONS_SET:
        return dur
    if dur <= 0:
        return VALID_DURATIONS[-1]
    best: Fraction = VALID_DURATIONS[0]
    best_diff: Fraction = abs(dur - best)
    for vd in VALID_DURATIONS[1:]:
        diff: Fraction = abs(dur - vd)
        if diff < best_diff:
            best = vd
            best_diff = diff
    return best


# =============================================================================
# Gap Rhythm Derivation
# =============================================================================


def derive_gap_rhythm(
    phrase_motif: RhythmicMotif,
    profile: RhythmicProfile,
    gap_position: float,
    gap_fraction: float,
    gap_duration: Fraction,
    is_downbeat: bool,
    near_cadence: bool,
) -> GapRhythm:
    """Derive a GapRhythm for one gap from the phrase motif."""
    assert gap_duration > 0, f"Non-positive gap_duration: {gap_duration}"
    assert 0.0 <= gap_position <= 1.0, f"gap_position out of range: {gap_position}"
    assert gap_fraction > 0, f"Non-positive gap_fraction: {gap_fraction}"
    raw_slice, slice_indices = _extract_motif_slice(
        pattern=phrase_motif.pattern,
        gap_position=gap_position,
        gap_fraction=gap_fraction,
    )
    durations: tuple[Fraction, ...] = _scale_to_duration(
        durations=raw_slice,
        target_duration=gap_duration,
    )
    # Verify total is preserved
    assert sum(durations) == gap_duration, (
        f"Duration sum {sum(durations)} != gap_duration {gap_duration}"
    )
    return GapRhythm(
        durations=durations,
        downbeat_emphasis=is_downbeat,
        pickup_to_next=near_cadence,
        motif_slice=slice_indices,
    )
