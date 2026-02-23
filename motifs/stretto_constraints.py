"""Stretto constraints: per-offset counterpoint evaluation for subject generation.

Derives check points (note-index pairs at strong/weak beats) from a
rhythm and stretto offset, then evaluates MIDI pitch sequences against
them in semitone space.  Used by subject_generator to score stretto
potential at every possible offset.
"""
from dataclasses import dataclass

from shared.constants import (
    CONSONANT_INTERVALS,
    CONSONANT_INTERVALS_ABOVE_BASS,
    STRETTO_MIN_QUALITY,
    STRETTO_OFFSET_COUNT_CEILING,
    TRITONE_SEMITONES,
)


# ── Strong-beat slot sets per metre (bar-relative) ───────────────────
_STRONG_BEAT_SLOTS: dict[tuple[int, int], frozenset[int]] = {
    (4, 4): frozenset({0, 8}),    # beats 1 and 3
    (3, 4): frozenset({0}),       # beat 1 only
    (2, 4): frozenset({0}),       # beat 1 only
    (6, 8): frozenset({0, 6}),    # dotted-crotchet groups
    (3, 8): frozenset({0}),       # beat 1 only
    (2, 2): frozenset({0}),       # beat 1 only
}

_SLOTS_PER_CROTCHET: int = 4
_SLOTS_PER_QUAVER: int = 2


# ═════════════════════════════════════════════════════════════════════
#  Dataclasses
# ═════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StrettoCheck:
    """A note-index pair to check, with beat strength and collision size."""
    leader_idx: int
    follower_idx: int
    is_strong: bool
    collision_slots: int


@dataclass(frozen=True)
class OffsetResult:
    """Stretto viability at one offset for one subject."""
    offset_slots: int
    viable: bool
    consonant_count: int
    total_count: int
    dissonance_cost: int
    quality: float


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
#  Check-point derivation (rhythm only — no pitch knowledge)
# ═════════════════════════════════════════════════════════════════════

def derive_check_points(
    *,
    dur_slots: tuple[int, ...],
    offset_slots: int,
    metre: tuple[int, int],
) -> tuple[StrettoCheck, ...]:
    """Derive check points from rhythm + offset.

    Each check point is a (leader_idx, follower_idx) pair at a note
    onset in either voice during the overlap, tagged with beat strength
    and collision duration.
    """
    assert offset_slots > 0, f"Offset must be positive, got {offset_slots}"
    slot_map: tuple[int, ...] = build_slot_to_note(dur_slots=dur_slots)
    total_slots: int = len(slot_map)
    assert offset_slots < total_slots, f"Offset {offset_slots} >= total {total_slots}"
    onsets: tuple[int, ...] = _note_onsets(dur_slots=dur_slots)
    bar_slots: int = _slots_per_bar(metre)
    strong_set: frozenset[int] = _STRONG_BEAT_SLOTS.get(metre, frozenset({0}))
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
    seen: dict[tuple[int, int], StrettoCheck] = {}
    for t in check_times:
        if t >= total_slots or t < offset_slots:
            continue
        li: int = slot_map[t]
        fi: int = slot_map[t - offset_slots]
        if li == fi:
            continue
        key: tuple[int, int] = (li, fi) if li > fi else (fi, li)
        bar_relative: int = t % bar_slots
        is_strong: bool = bar_relative in strong_set
        leader_rem: int = _remaining_at_slot(
            note_idx=li, slot=t, onsets=onsets, dur_slots=dur_slots,
        )
        follower_rem: int = _remaining_at_slot(
            note_idx=fi, slot=t - offset_slots, onsets=onsets, dur_slots=dur_slots,
        )
        collision: int = min(leader_rem, follower_rem)
        prev = seen.get(key)
        if prev is None:
            seen[key] = StrettoCheck(
                leader_idx=key[0], follower_idx=key[1],
                is_strong=is_strong, collision_slots=collision,
            )
        else:
            seen[key] = StrettoCheck(
                leader_idx=key[0], follower_idx=key[1],
                is_strong=prev.is_strong or is_strong,
                collision_slots=max(prev.collision_slots, collision),
            )
    return tuple(seen.values())


# ═════════════════════════════════════════════════════════════════════
#  Evaluation (semitone space)
# ═════════════════════════════════════════════════════════════════════

def evaluate_offset(
    *,
    midi: tuple[int, ...],
    dur_slots: tuple[int, ...],
    offset_slots: int,
    metre: tuple[int, int],
) -> OffsetResult:
    """Check one stretto offset using MIDI pitches in semitone space.

    Strong beats: interval must be in CONSONANT_INTERVALS_ABOVE_BASS
    (P4 excluded — dissonant when above bass, and in stretto we
    cannot know which voice is lower).
    Weak beats: tritone is fatal; other dissonance adds collision cost;
    P4 is consonant (passing fourths are idiomatic).
    """
    assert len(midi) == len(dur_slots), (
        f"midi ({len(midi)}) != durations ({len(dur_slots)})"
    )
    checks: tuple[StrettoCheck, ...] = derive_check_points(
        dur_slots=dur_slots, offset_slots=offset_slots, metre=metre,
    )
    total_count: int = len(checks)
    if total_count == 0:
        return OffsetResult(
            offset_slots=offset_slots, viable=True,
            consonant_count=0, total_count=0,
            dissonance_cost=0, quality=1.0,
        )
    consonant_count: int = 0
    total_cost: int = 0
    for ck in checks:
        semitones: int = abs(midi[ck.leader_idx] - midi[ck.follower_idx]) % 12
        if ck.is_strong:
            if semitones not in CONSONANT_INTERVALS_ABOVE_BASS:
                return OffsetResult(
                    offset_slots=offset_slots, viable=False,
                    consonant_count=consonant_count, total_count=total_count,
                    dissonance_cost=0, quality=0.0,
                )
            consonant_count += 1
        else:
            if semitones == TRITONE_SEMITONES:
                return OffsetResult(
                    offset_slots=offset_slots, viable=False,
                    consonant_count=consonant_count, total_count=total_count,
                    dissonance_cost=0, quality=0.0,
                )
            if semitones in CONSONANT_INTERVALS:
                consonant_count += 1
            else:
                total_cost += ck.collision_slots
    qual: float = consonant_count / total_count
    if qual < STRETTO_MIN_QUALITY:
        return OffsetResult(
            offset_slots=offset_slots, viable=False,
            consonant_count=consonant_count, total_count=total_count,
            dissonance_cost=total_cost, quality=qual,
        )
    return OffsetResult(
        offset_slots=offset_slots, viable=True,
        consonant_count=consonant_count, total_count=total_count,
        dissonance_cost=total_cost, quality=qual,
    )


# ── Stretto viability filters ────────────────────────────────────────
MAX_OFFSET_FRACTION: float = 0.5


def evaluate_all_offsets(
    *,
    midi: tuple[int, ...],
    dur_slots: tuple[int, ...],
    metre: tuple[int, int],
) -> tuple[OffsetResult, ...]:
    """Evaluate stretto at every leader note onset up to half the subject."""
    total_slots: int = sum(dur_slots)
    max_offset: int = int(total_slots * MAX_OFFSET_FRACTION)
    onsets: tuple[int, ...] = _note_onsets(dur_slots)
    results: list[OffsetResult] = []
    for onset in onsets:
        if onset < 1 or onset > max_offset:
            continue
        results.append(evaluate_offset(
            midi=midi, dur_slots=dur_slots,
            offset_slots=onset, metre=metre,
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
