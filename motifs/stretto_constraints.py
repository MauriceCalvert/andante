"""Stretto constraints: per-offset counterpoint evaluation for subject generation.

Derives hard (strong-beat) and soft (weak-beat) consonance constraints
from a rhythm and stretto offset, then evaluates degree sequences
against them. Used by subject_generator to replace the binary
stretto filter with graded per-offset scoring.
"""
from dataclasses import dataclass

from shared.constants import (
    CONSONANT_MOD7,
    SECOND_MOD7,
    SEVENTH_MOD7,
    STRETTO_OFFSET_COUNT_CEILING,
    TRITONE_MOD7,
)

HARD_REJECT_INTERVALS: frozenset[int] = frozenset({TRITONE_MOD7, SECOND_MOD7, SEVENTH_MOD7})


# ── Strong-beat slot sets per metre (bar-relative) ───────────────────
# Key: (numerator, denominator) -> set of bar-relative slot positions
# that are strong beats. Slots are x2-tick units (= real semiquavers).
_STRONG_BEAT_SLOTS: dict[tuple[int, int], frozenset[int]] = {
    (4, 4): frozenset({0, 8}),    # beats 1 and 3
    (3, 4): frozenset({0}),       # beat 1 only
    (2, 4): frozenset({0}),       # beat 1 only
    (6, 8): frozenset({0, 6}),    # dotted-crotchet groups
    (3, 8): frozenset({0}),       # beat 1 only
    (2, 2): frozenset({0}),       # beat 1 only
}

# ── Slots per beat for various denominators ──────────────────────────
_SLOTS_PER_CROTCHET: int = 4  # x2-tick slots per real crotchet
_SLOTS_PER_QUAVER: int = 2    # x2-tick slots per real quaver


# ═════════════════════════════════════════════════════════════════════
#  Dataclasses
# ═════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class HardConstraint:
    """Strong-beat consonance requirement between two note indices."""
    higher_idx: int
    lower_idx: int
    allowed_mod7: frozenset[int]


@dataclass(frozen=True)
class SoftConstraint:
    """Weak-beat dissonance penalty between two note indices."""
    higher_idx: int
    lower_idx: int
    collision_slots: int  # min(leader_remaining, follower_remaining)


@dataclass(frozen=True)
class OffsetResult:
    """Stretto viability at one offset for one subject."""
    offset_slots: int
    viable: bool
    consonant_count: int
    total_count: int
    dissonance_cost: int
    quality: float  # consonant_count / total_count, 1.0 if no check points


# ═════════════════════════════════════════════════════════════════════
#  Slot helpers
# ═════════════════════════════════════════════════════════════════════

def build_slot_to_note(*, dur_slots: tuple[int, ...]) -> tuple[int, ...]:
    """Map each time slot to the note index sounding at that slot."""
    assert len(dur_slots) > 0, "Empty duration sequence"
    slot_map: list[int] = []
    for i, d in enumerate(dur_slots):
        assert d > 0, f"Zero-duration note at index {i}"
        slot_map.extend([i] * d)
    return tuple(slot_map)


def _slots_per_bar(metre: tuple[int, int]) -> int:
    """X2-tick slots per bar for the given metre."""
    if metre[1] == 4:
        return metre[0] * _SLOTS_PER_CROTCHET
    if metre[1] == 8:
        return metre[0] * _SLOTS_PER_QUAVER
    if metre[1] == 2:
        return metre[0] * _SLOTS_PER_CROTCHET * 2
    assert False, f"Unsupported metre denominator: {metre[1]}"


def _note_onsets(dur_slots: tuple[int, ...]) -> tuple[int, ...]:
    """Return the onset slot of each note."""
    onsets: list[int] = []
    t: int = 0
    for d in dur_slots:
        onsets.append(t)
        t += d
    return tuple(onsets)


def _remaining_at_slot(
    note_idx: int,
    slot: int,
    onsets: tuple[int, ...],
    dur_slots: tuple[int, ...],
) -> int:
    """How many slots remain of note_idx from the given slot."""
    note_end: int = onsets[note_idx] + dur_slots[note_idx]
    remaining: int = note_end - slot
    assert remaining > 0, f"Note {note_idx} not sounding at slot {slot}"
    return remaining


# ═════════════════════════════════════════════════════════════════════
#  Constraint derivation
# ═════════════════════════════════════════════════════════════════════

def derive_stretto_constraints(
    *,
    dur_slots: tuple[int, ...],
    offset_slots: int,
    metre: tuple[int, int],
) -> tuple[tuple[HardConstraint, ...], tuple[SoftConstraint, ...]]:
    """Derive hard and soft constraints from rhythm + offset.

    Check points are note onsets in either voice during the overlap.
    For each unique (higher_idx, lower_idx) pair:
    - If it lands on a strong beat -> HardConstraint
    - Otherwise -> SoftConstraint with collision_slots
    """
    assert offset_slots > 0, f"Offset must be positive, got {offset_slots}"
    slot_map: tuple[int, ...] = build_slot_to_note(dur_slots=dur_slots)
    total_slots: int = len(slot_map)
    assert offset_slots < total_slots, f"Offset {offset_slots} >= total {total_slots}"

    onsets: tuple[int, ...] = _note_onsets(dur_slots=dur_slots)
    bar_slots: int = _slots_per_bar(metre)
    strong_set: frozenset[int] = _STRONG_BEAT_SLOTS.get(metre, frozenset({0}))

    # Collect note onsets in either voice during overlap
    leader_onset_set: set[int] = set()
    for onset in onsets:
        if onset >= offset_slots:
            leader_onset_set.add(onset)

    follower_onset_set: set[int] = set()
    for onset in onsets:
        shifted: int = onset + offset_slots
        if shifted < total_slots:
            follower_onset_set.add(shifted)

    check_times: list[int] = sorted(leader_onset_set | follower_onset_set)

    # Build constraints per (higher_idx, lower_idx) pair
    hard_pairs: dict[tuple[int, int], frozenset[int]] = {}
    soft_pairs: dict[tuple[int, int], int] = {}

    for t in check_times:
        if t >= total_slots or t < offset_slots:
            continue
        li: int = slot_map[t]
        fi: int = slot_map[t - offset_slots]
        if li == fi:
            continue  # same note index -> unison -> always OK
        key: tuple[int, int] = (li, fi) if li > fi else (fi, li)
        bar_relative: int = t % bar_slots
        is_strong: bool = bar_relative in strong_set

        if is_strong:
            if key in hard_pairs:
                hard_pairs[key] = hard_pairs[key] & CONSONANT_MOD7
            else:
                hard_pairs[key] = CONSONANT_MOD7
        else:
            leader_rem: int = _remaining_at_slot(
                note_idx=li, slot=t,
                onsets=onsets, dur_slots=dur_slots,
            )
            follower_rem: int = _remaining_at_slot(
                note_idx=fi, slot=t - offset_slots,
                onsets=onsets, dur_slots=dur_slots,
            )
            collision: int = min(leader_rem, follower_rem)
            if key in soft_pairs:
                soft_pairs[key] = max(soft_pairs[key], collision)
            else:
                soft_pairs[key] = collision

    hard_list: tuple[HardConstraint, ...] = tuple(
        HardConstraint(higher_idx=hi, lower_idx=lo, allowed_mod7=allowed)
        for (hi, lo), allowed in hard_pairs.items()
    )
    # Exclude soft pairs that were promoted to hard
    soft_list: tuple[SoftConstraint, ...] = tuple(
        SoftConstraint(higher_idx=hi, lower_idx=lo, collision_slots=dur)
        for (hi, lo), dur in soft_pairs.items()
        if (hi, lo) not in hard_pairs
    )
    return hard_list, soft_list


# ═════════════════════════════════════════════════════════════════════
#  Evaluation
# ═════════════════════════════════════════════════════════════════════

def evaluate_offset(
    *,
    degrees: tuple[int, ...],
    dur_slots: tuple[int, ...],
    offset_slots: int,
    metre: tuple[int, int],
) -> OffsetResult:
    """Check one stretto offset for a completed degree sequence.

    Hard constraints: interval must be in allowed_mod7 and not tritone.
    Soft constraints: tritone is fatal; other dissonance adds collision_slots.
    """
    assert len(degrees) == len(dur_slots), (
        f"degrees ({len(degrees)}) != durations ({len(dur_slots)})"
    )
    hard, soft = derive_stretto_constraints(
        dur_slots=dur_slots,
        offset_slots=offset_slots,
        metre=metre,
    )

    total_count: int = len(hard) + len(soft)
    if total_count == 0:
        return OffsetResult(
            offset_slots=offset_slots,
            viable=True,
            consonant_count=0,
            total_count=0,
            dissonance_cost=0,
            quality=1.0,
        )
    # Check hard constraints (all must pass)
    for hc in hard:
        iv: int = abs(degrees[hc.higher_idx] - degrees[hc.lower_idx]) % 7
        if iv in HARD_REJECT_INTERVALS or iv not in hc.allowed_mod7:
            return OffsetResult(
                offset_slots=offset_slots,
                viable=False,
                consonant_count=0,
                total_count=total_count,
                dissonance_cost=0,
                quality=0.0,
            )
    # Hard constraints all passed — count them as consonant
    consonant_count: int = len(hard)
    total_cost: int = 0
    for sc in soft:
        iv = abs(degrees[sc.higher_idx] - degrees[sc.lower_idx]) % 7
        if iv in HARD_REJECT_INTERVALS:
            return OffsetResult(
                offset_slots=offset_slots,
                viable=False,
                consonant_count=consonant_count,
                total_count=total_count,
                dissonance_cost=0,
                quality=0.0,
            )
        if iv in CONSONANT_MOD7:
            consonant_count += 1
        else:
            total_cost += sc.collision_slots
    qual: float = consonant_count / total_count
    return OffsetResult(
        offset_slots=offset_slots,
        viable=True,
        consonant_count=consonant_count,
        total_count=total_count,
        dissonance_cost=total_cost,
        quality=qual,
    )


# ── Stretto viability filters ────────────────────────────────────────
MAX_OFFSET_FRACTION: float = 0.5  # reject if follower enters after half the subject


def evaluate_all_offsets(
    *,
    degrees: tuple[int, ...],
    dur_slots: tuple[int, ...],
    metre: tuple[int, int],
) -> tuple[OffsetResult, ...]:
    """Evaluate stretto at every offset from 1 to total_slots / 2."""
    total_slots: int = sum(dur_slots)
    max_offset: int = int(total_slots * MAX_OFFSET_FRACTION)
    results: list[OffsetResult] = []
    for offset in range(1, max_offset + 1):
        results.append(evaluate_offset(
            degrees=degrees,
            dur_slots=dur_slots,
            offset_slots=offset,
            metre=metre,
        ))
    return tuple(results)


# ═════════════════════════════════════════════════════════════════════
#  Scoring
# ═════════════════════════════════════════════════════════════════════

def score_stretto(
    *,
    offset_results: tuple[OffsetResult, ...],
    total_slots: int,
) -> float:
    """Combine viable offset count, tightness, and quality into 0..1 score.

    - Count     (50%): min(viable_count / ceiling, 1.0)
    - Tightness (30%): mean of (1.0 - offset / total_slots) for viable
    - Quality   (20%): 1.0 - avg_dissonance / total_slots
    """
    viable: list[OffsetResult] = [r for r in offset_results if r.viable]
    count: int = len(viable)
    if count == 0:
        return 0.0

    s_count: float = min(count / STRETTO_OFFSET_COUNT_CEILING, 1.0)
    s_tightness: float = sum(
        1.0 - r.offset_slots / total_slots for r in viable
    ) / count
    avg_cost: float = sum(r.dissonance_cost for r in viable) / count
    s_quality: float = max(0.0, 1.0 - avg_cost / total_slots)

    return 0.50 * s_count + 0.30 * s_tightness + 0.20 * s_quality
