"""Unit tests for builder/voice_checks.py — per-note counterpoint filter."""
import pytest
from fractions import Fraction

from builder.voice_checks import (
    check_consonance,
    check_direct_motion,
    check_melodic_interval,
    check_parallels,
    check_range,
    check_strong_beat_consonance,
    check_voice_overlap,
    format_interval,
)
from shared.voice_types import Range


# =========================================================================
# format_interval
# =========================================================================


@pytest.mark.parametrize("semitones, expected", [
    (0, "unison"),
    (3, "m3"),
    (7, "P5"),
    (12, "P8"),
    (14, "M2+1oct"),
    (19, "P5+1oct"),
    (24, "unison+2oct"),
    (-7, "-P5"),
    (-12, "-P8"),
])
def test_format_interval(semitones: int, expected: str) -> None:
    """Interval formatting produces readable names."""
    assert format_interval(semitones=semitones) == expected


# =========================================================================
# check_consonance
# =========================================================================


@pytest.mark.parametrize("midi_a, midi_b, expected", [
    # unison — consonant
    (60, 60, True),
    # m3 — consonant
    (60, 63, True),
    # M3 — consonant
    (60, 64, True),
    # P4 — dissonant above bass (not in CONSONANT_INTERVALS_ABOVE_BASS)
    (60, 65, False),
    # P5 — consonant
    (60, 67, True),
    # m6 — consonant
    (60, 68, True),
    # M6 — consonant
    (60, 69, True),
    # m2 — dissonant
    (60, 61, False),
    # M2 — dissonant
    (60, 62, False),
    # tritone — dissonant
    (60, 66, False),
    # m7 — dissonant
    (60, 70, False),
    # M7 — dissonant
    (60, 71, False),
    # octave compound: m3 + octave still consonant
    (48, 63, True),
    # order doesn't matter
    (67, 60, True),
])
def test_check_consonance(midi_a: int, midi_b: int, expected: bool) -> None:
    """Vertical interval consonance check."""
    assert check_consonance(midi_a=midi_a, midi_b=midi_b) is expected


# =========================================================================
# check_direct_motion
# =========================================================================


@pytest.mark.parametrize("prev_u, prev_l, curr_u, curr_l, expected", [
    # Similar motion to P5, upper leaps (>2 semitones) — forbidden
    (64, 48, 67, 48 + 12, False),
    # Similar motion to P5, upper steps — allowed
    (66, 48, 67, 48 + 12, True),
    # Contrary motion to P5 — allowed
    (70, 55, 67, 60, True),
    # Upper voice stationary — allowed
    (67, 48, 67, 60, True),
    # Lower voice stationary — allowed
    (64, 60, 67, 60, True),
    # Similar motion to non-perfect interval — allowed
    (64, 48, 67, 64, True),
    # Similar motion to P8 (unison), upper leaps — forbidden
    (57, 45, 60, 48, False),
])
def test_check_direct_motion(
    prev_u: int,
    prev_l: int,
    curr_u: int,
    curr_l: int,
    expected: bool,
) -> None:
    """Direct motion to perfect interval rule."""
    assert check_direct_motion(
        prev_upper=prev_u,
        prev_lower=prev_l,
        curr_upper=curr_u,
        curr_lower=curr_l,
    ) is expected


# =========================================================================
# check_melodic_interval
# =========================================================================


@pytest.mark.parametrize("prev, curr, expected", [
    # step (m2) — allowed
    (60, 61, True),
    # step (M2) — allowed
    (60, 62, True),
    # m3 — allowed
    (60, 63, True),
    # M3 — allowed
    (60, 64, True),
    # P4 — allowed (not in UGLY_INTERVALS)
    (60, 65, True),
    # tritone leap — forbidden (6 in UGLY_INTERVALS, interval > 2)
    (60, 66, False),
    # P5 — allowed
    (60, 67, True),
    # m7 — forbidden (10 in UGLY_INTERVALS)
    (60, 70, False),
    # M7 — forbidden (11 in UGLY_INTERVALS)
    (60, 71, False),
    # octave — allowed (12 % 12 = 0, not ugly)
    (60, 72, True),
    # compound tritone (6 + 12 = 18) — still forbidden (18 % 12 = 6)
    (60, 78, False),
    # m2 step (1 semitone, <= 2) — allowed despite being in UGLY_INTERVALS
    (60, 59, True),
])
def test_check_melodic_interval(prev: int, curr: int, expected: bool) -> None:
    """Melodic interval ugliness filter."""
    assert check_melodic_interval(prev_midi=prev, curr_midi=curr) is expected


# =========================================================================
# check_parallels
# =========================================================================


@pytest.mark.parametrize("prev_u, prev_l, curr_u, curr_l, expected", [
    # parallel P5 → P5, same direction — forbidden
    (67, 60, 69, 62, False),
    # parallel P8 → P8, same direction — forbidden
    (72, 60, 74, 62, False),
    # P5 → P5, contrary motion — allowed
    (67, 60, 65, 62, True),
    # P5 → m3 — different interval, allowed
    (67, 60, 67, 64, True),
    # m3 → P5 — previous not perfect, allowed
    (63, 60, 67, 60, True),
    # one voice stationary, same interval — allowed (oblique motion)
    (67, 60, 67, 60, True),
    # unison → unison, same direction — forbidden
    (60, 60, 62, 62, False),
])
def test_check_parallels(
    prev_u: int,
    prev_l: int,
    curr_u: int,
    curr_l: int,
    expected: bool,
) -> None:
    """Parallel perfect interval detection."""
    assert check_parallels(
        prev_upper=prev_u,
        prev_lower=prev_l,
        curr_upper=curr_u,
        curr_lower=curr_l,
    ) is expected


# =========================================================================
# check_range
# =========================================================================


SOPRANO_RANGE: Range = Range(low=55, high=84)


@pytest.mark.parametrize("midi, expected", [
    (55, True),   # low boundary
    (84, True),   # high boundary
    (70, True),   # middle
    (54, False),  # below
    (85, False),  # above
])
def test_check_range(midi: int, expected: bool) -> None:
    """Pitch within actuator range."""
    assert check_range(midi=midi, actuator_range=SOPRANO_RANGE) is expected


# =========================================================================
# check_strong_beat_consonance
# =========================================================================


@pytest.mark.parametrize("cand, prior, offset, metre, expected", [
    # strong beat (0), consonant (P5) — pass
    (67, 60, Fraction(0), "4/4", True),
    # strong beat (0), dissonant (M2) — fail
    (62, 60, Fraction(0), "4/4", False),
    # weak beat, dissonant — pass (not enforced)
    (62, 60, Fraction(1, 4), "4/4", True),
    # beat 3 in 4/4 (offset 1/2) is strong — consonant check applies
    (67, 60, Fraction(1, 2), "4/4", True),
    # beat 3 in 4/4 (offset 1/2) is strong — dissonant fails
    (62, 60, Fraction(1, 2), "4/4", False),
    # beat 1 in 3/4, consonant — pass
    (64, 60, Fraction(0), "3/4", True),
    # beat 2 in 3/4, dissonant — pass (weak beat)
    (62, 60, Fraction(1, 4), "3/4", True),
])
def test_check_strong_beat_consonance(
    cand: int,
    prior: int,
    offset: Fraction,
    metre: str,
    expected: bool,
) -> None:
    """Strong-beat consonance enforcement."""
    assert check_strong_beat_consonance(
        candidate_midi=cand,
        prior_midi=prior,
        offset=offset,
        metre=metre,
    ) is expected


# =========================================================================
# check_voice_overlap
# =========================================================================


def test_voice_overlap_detected() -> None:
    """Voice moves to pitch just vacated by prior voice."""
    prior: dict[Fraction, list[int]] = {
        Fraction(0): [67],
        Fraction(1, 4): [64],
    }
    assert check_voice_overlap(
        candidate_midi=67,
        candidate_offset=Fraction(1, 4),
        prior_notes_by_offset=prior,
        prev_offset=Fraction(0),
    ) is False


def test_voice_overlap_allowed_when_pitch_still_present() -> None:
    """Pitch still active in prior voice at current offset — no overlap."""
    prior: dict[Fraction, list[int]] = {
        Fraction(0): [67],
        Fraction(1, 4): [67],
    }
    assert check_voice_overlap(
        candidate_midi=67,
        candidate_offset=Fraction(1, 4),
        prior_notes_by_offset=prior,
        prev_offset=Fraction(0),
    ) is True


def test_voice_overlap_no_previous_offset() -> None:
    """First note has no previous offset — always passes."""
    assert check_voice_overlap(
        candidate_midi=67,
        candidate_offset=Fraction(0),
        prior_notes_by_offset={},
        prev_offset=None,
    ) is True
