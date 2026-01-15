"""Constraint checking for diatonic inner voice solver.

All constraints operate in degree space (1-7). This module provides:
- Parallel fifth/octave detection (degree intervals 4 and 0)
- Spacing constraints between voices
- Voice crossing detection
- Chord tone preference scoring
"""
from dataclasses import dataclass
from fractions import Fraction

from shared.parallels import is_parallel_fifth_diatonic, is_parallel_octave_diatonic
from engine.diatonic_solver.core import DiatonicSlice


# =============================================================================
# Cost weights for soft constraints
# =============================================================================

# Hard constraint costs (make solutions infeasible)
PARALLEL_FIFTH_COST: int = 1000
PARALLEL_OCTAVE_COST: int = 1000
VOICE_CROSSING_COST: int = 500

# Soft constraint costs
NON_CHORD_TONE_COST: int = 20
UNISON_COST: int = 1000  # Same degree - as bad as parallel fifths
OCTAVE_DOUBLING_COST: int = 10  # Same degree but different register

# Voice leading costs
STATIC_VOICE_COST: int = 25  # No motion - discourages drone behavior
STEP_REWARD: int = -5  # 1 degree (ideal) - reward with negative cost
SMALL_LEAP_COST: int = 0  # 2 degrees
MEDIUM_LEAP_COST: int = 3  # 3 degrees
LARGE_LEAP_COST: int = 8  # 4+ degrees

# Thematic fidelity
THEMATIC_MATCH_REWARD: int = 15


# =============================================================================
# Diatonic interval constants
# =============================================================================

# Consonant intervals in degree space
CONSONANT_INTERVALS: frozenset[int] = frozenset({0, 2, 4, 5})  # unison, 3rd, 5th, 6th

# Chord tone degrees relative to bass
def get_chord_tones(bass_degree: int) -> frozenset[int]:
    """Get chord tones (root, third, fifth) given bass degree.

    In diatonic space, the triad built on degree N has:
    - Root: N
    - Third: N+2 (mod 7, wrapped to 1-7)
    - Fifth: N+4 (mod 7, wrapped to 1-7)
    """
    root = bass_degree
    third = ((bass_degree - 1 + 2) % 7) + 1
    fifth = ((bass_degree - 1 + 4) % 7) + 1
    return frozenset({root, third, fifth})


# =============================================================================
# Parallel motion detection
# =============================================================================

def check_parallel_fifths(
    prev_slice: DiatonicSlice,
    curr_slice: DiatonicSlice,
) -> list[tuple[int, int]]:
    """Check for parallel fifths between all voice pairs.

    Returns list of (upper_voice_idx, lower_voice_idx) pairs with violations.
    """
    violations: list[tuple[int, int]] = []
    voice_count = prev_slice.voice_count

    for upper in range(voice_count):
        for lower in range(upper + 1, voice_count):
            prev_upper = prev_slice.get_degree(upper)
            prev_lower = prev_slice.get_degree(lower)
            curr_upper = curr_slice.get_degree(upper)
            curr_lower = curr_slice.get_degree(lower)

            # Skip if any voice is resting
            if any(d is None for d in [prev_upper, prev_lower, curr_upper, curr_lower]):
                continue

            if is_parallel_fifth_diatonic(prev_upper, prev_lower, curr_upper, curr_lower):
                violations.append((upper, lower))

    return violations


def check_parallel_octaves(
    prev_slice: DiatonicSlice,
    curr_slice: DiatonicSlice,
) -> list[tuple[int, int]]:
    """Check for parallel octaves/unisons between all voice pairs.

    Returns list of (upper_voice_idx, lower_voice_idx) pairs with violations.
    """
    violations: list[tuple[int, int]] = []
    voice_count = prev_slice.voice_count

    for upper in range(voice_count):
        for lower in range(upper + 1, voice_count):
            prev_upper = prev_slice.get_degree(upper)
            prev_lower = prev_slice.get_degree(lower)
            curr_upper = curr_slice.get_degree(upper)
            curr_lower = curr_slice.get_degree(lower)

            # Skip if any voice is resting
            if any(d is None for d in [prev_upper, prev_lower, curr_upper, curr_lower]):
                continue

            if is_parallel_octave_diatonic(prev_upper, prev_lower, curr_upper, curr_lower):
                violations.append((upper, lower))

    return violations


def has_parallel_violation(
    prev_degrees: tuple[int | None, ...],
    curr_degrees: tuple[int | None, ...],
) -> bool:
    """Quick check for any parallel fifth or octave violation."""
    voice_count = len(prev_degrees)

    for upper in range(voice_count):
        for lower in range(upper + 1, voice_count):
            prev_upper = prev_degrees[upper]
            prev_lower = prev_degrees[lower]
            curr_upper = curr_degrees[upper]
            curr_lower = curr_degrees[lower]

            if any(d is None for d in [prev_upper, prev_lower, curr_upper, curr_lower]):
                continue

            if is_parallel_fifth_diatonic(prev_upper, prev_lower, curr_upper, curr_lower):
                return True
            if is_parallel_octave_diatonic(prev_upper, prev_lower, curr_upper, curr_lower):
                return True

    return False


# =============================================================================
# Spacing and unison detection
# =============================================================================

def check_unisons(degrees: tuple[int | None, ...]) -> list[tuple[int, int]]:
    """Check for unisons (same degree) between any voice pair.

    Returns list of (voice1_idx, voice2_idx) pairs with unisons.
    """
    unisons: list[tuple[int, int]] = []
    voice_count = len(degrees)

    for i in range(voice_count):
        for j in range(i + 1, voice_count):
            if degrees[i] is not None and degrees[j] is not None:
                if degrees[i] == degrees[j]:
                    unisons.append((i, j))

    return unisons


def has_unison(degrees: tuple[int | None, ...]) -> bool:
    """Quick check for any unison."""
    voice_count = len(degrees)
    for i in range(voice_count):
        for j in range(i + 1, voice_count):
            if degrees[i] is not None and degrees[j] is not None:
                if degrees[i] == degrees[j]:
                    return True
    return False


# =============================================================================
# Voice leading scoring
# =============================================================================

def voice_leading_cost(prev_degree: int, curr_degree: int) -> int:
    """Calculate voice-leading cost for single voice motion."""
    motion = abs(curr_degree - prev_degree)
    if motion == 0:
        return STATIC_VOICE_COST
    elif motion == 1:
        return STEP_REWARD  # Negative = reward
    elif motion == 2:
        return SMALL_LEAP_COST
    elif motion == 3:
        return MEDIUM_LEAP_COST
    else:
        return LARGE_LEAP_COST


def total_voice_leading_cost(
    prev_degrees: tuple[int | None, ...],
    curr_degrees: tuple[int | None, ...],
) -> int:
    """Calculate total voice-leading cost across all voices."""
    total = 0
    for prev, curr in zip(prev_degrees, curr_degrees):
        if prev is not None and curr is not None:
            total += voice_leading_cost(prev, curr)
    return total


# =============================================================================
# Chord tone scoring
# =============================================================================

def chord_tone_cost(
    degrees: tuple[int | None, ...],
    bass_degree: int,
    is_strong_beat: bool = False,
) -> int:
    """Calculate cost for non-chord-tone inner voices.

    Args:
        degrees: All voice degrees (soprano to bass)
        bass_degree: Bass degree (determines chord)
        is_strong_beat: If True, penalties are doubled

    Returns:
        Total cost for non-chord-tone usage.
    """
    chord_tones = get_chord_tones(bass_degree)
    multiplier = 2 if is_strong_beat else 1
    total = 0

    # Only penalize inner voices (indices 1 to len-2)
    for i in range(1, len(degrees) - 1):
        deg = degrees[i]
        if deg is not None and deg not in chord_tones:
            total += NON_CHORD_TONE_COST * multiplier

    return total


# =============================================================================
# Combined scoring
# =============================================================================

@dataclass
class SliceScore:
    """Score breakdown for a slice configuration."""
    parallel_cost: int = 0
    unison_cost: int = 0
    voice_leading_cost: int = 0
    chord_tone_cost: int = 0
    thematic_bonus: int = 0

    @property
    def total(self) -> int:
        return (
            self.parallel_cost
            + self.unison_cost
            + self.voice_leading_cost
            + self.chord_tone_cost
            - self.thematic_bonus  # Bonus reduces cost
        )


def score_slice_transition(
    prev_degrees: tuple[int | None, ...],
    curr_degrees: tuple[int | None, ...],
    bass_degree: int,
    is_strong_beat: bool = False,
    thematic_targets: dict[int, int] | None = None,
) -> SliceScore:
    """Score a transition from prev slice to curr slice.

    Args:
        prev_degrees: Previous slice degrees (None for rests)
        curr_degrees: Current slice degrees
        bass_degree: Current bass degree (for chord inference)
        is_strong_beat: If True, non-chord-tone penalties are doubled
        thematic_targets: Optional dict mapping voice_idx to target degree

    Returns:
        SliceScore with breakdown of costs.
    """
    score = SliceScore()

    # Parallel violations
    if has_parallel_violation(prev_degrees, curr_degrees):
        # Count violations
        voice_count = len(prev_degrees)
        for upper in range(voice_count):
            for lower in range(upper + 1, voice_count):
                prev_upper = prev_degrees[upper]
                prev_lower = prev_degrees[lower]
                curr_upper = curr_degrees[upper]
                curr_lower = curr_degrees[lower]

                if any(d is None for d in [prev_upper, prev_lower, curr_upper, curr_lower]):
                    continue

                if is_parallel_fifth_diatonic(prev_upper, prev_lower, curr_upper, curr_lower):
                    score.parallel_cost += PARALLEL_FIFTH_COST
                if is_parallel_octave_diatonic(prev_upper, prev_lower, curr_upper, curr_lower):
                    score.parallel_cost += PARALLEL_OCTAVE_COST

    # Unison violations
    unison_pairs = check_unisons(curr_degrees)
    score.unison_cost = len(unison_pairs) * UNISON_COST

    # Voice leading
    score.voice_leading_cost = total_voice_leading_cost(prev_degrees, curr_degrees)

    # Chord tone preference
    score.chord_tone_cost = chord_tone_cost(curr_degrees, bass_degree, is_strong_beat)

    # Thematic matching
    if thematic_targets:
        for voice_idx, target_deg in thematic_targets.items():
            if voice_idx < len(curr_degrees):
                curr_deg = curr_degrees[voice_idx]
                if curr_deg == target_deg:
                    score.thematic_bonus += THEMATIC_MATCH_REWARD

    return score
