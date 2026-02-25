"""GPU-accelerated batch stretto evaluation.

Groups candidates by duration pattern, precomputes check-point
structures on CPU, then evaluates all pitch sequences per group
in a single GPU tensor pass.
"""
import torch

from motifs.stretto_constraints import (
    OffsetResult,
    derive_check_points,
    MAX_OFFSET_FRACTION,
    StrettoCheck,
)
from motifs.subject_gen.constants import DURATION_TICKS
from shared.constants import (
    CONSONANT_INTERVALS,
    CONSONANT_INTERVALS_ABOVE_BASS,
    STRETTO_MIN_QUALITY,
)

# ── Lookup tables (built once, moved to device on first call) ────────

_CONSONANT_STRONG: list[bool] = [i in CONSONANT_INTERVALS_ABOVE_BASS for i in range(12)]
_CONSONANT_WEAK: list[bool] = [i in CONSONANT_INTERVALS for i in range(12)]
_WEAK_FATAL: list[bool] = [(i in (1, 6, 11)) for i in range(12)]

_device_luts: dict[torch.device, tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}


def _get_luts(device: torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Return (consonant_strong, consonant_weak, weak_fatal) lookup tensors."""
    if device not in _device_luts:
        _device_luts[device] = (
            torch.tensor(_CONSONANT_STRONG, dtype=torch.bool, device=device),
            torch.tensor(_CONSONANT_WEAK, dtype=torch.bool, device=device),
            torch.tensor(_WEAK_FATAL, dtype=torch.bool, device=device),
        )
    return _device_luts[device]


# ── Check-point precomputation (CPU, per duration pattern) ──────────

def _note_onsets(dur_slots: tuple[int, ...]) -> tuple[int, ...]:
    """Onset slot of each note."""
    onsets: list[int] = []
    t: int = 0
    for d in dur_slots:
        onsets.append(t)
        t += d
    return tuple(onsets)


def _passes_alignment(
    dur_slots: tuple[int, ...],
    offset_slots: int,
) -> bool:
    """Check follower-onset alignment (rhythm only, no pitch)."""
    onsets = _note_onsets(dur_slots)
    total = sum(dur_slots)
    leader_onset_set = frozenset(onsets)
    sorted_leader = sorted(leader_onset_set)
    for fi, f_onset in enumerate(onsets):
        f_abs = f_onset + offset_slots
        if f_abs >= total:
            break
        if fi == 0:
            if f_abs not in leader_onset_set:
                return False
        else:
            if f_abs not in leader_onset_set:
                f_end = f_abs + dur_slots[fi]
                next_leader = None
                for lo in sorted_leader:
                    if lo > f_abs:
                        next_leader = lo
                        break
                if next_leader is None or f_end > next_leader:
                    return False
    return True


def _precompute_checks_for_dur(
    dur_slots: tuple[int, ...],
    metre: tuple[int, int],
) -> list[tuple[int, list[StrettoCheck]]]:
    """Return [(offset_slots, checks), ...] for all valid offsets of this dur pattern."""
    total = sum(dur_slots)
    max_offset = int(total * MAX_OFFSET_FRACTION)
    onsets = _note_onsets(dur_slots)
    result: list[tuple[int, list[StrettoCheck]]] = []
    for onset in onsets:
        if onset < 1 or onset > max_offset:
            continue
        if not _passes_alignment(dur_slots, onset):
            continue
        checks = derive_check_points(
            dur_slots=dur_slots,
            offset_slots=onset,
            metre=metre,
        )
        result.append((onset, list(checks)))
    return result


# ── GPU batch evaluation ────────────────────────────────────────────

def batch_evaluate_stretto(
    uncached: list[tuple[tuple[int, ...], tuple[int, ...]]],
    metre: tuple[int, int],
    device: torch.device | None = None,
) -> dict[tuple[tuple[int, ...], tuple[int, ...]], tuple[OffsetResult, ...]]:
    """Evaluate stretto for many (midi_pitches, dur_slots) pairs on GPU.

    Returns dict mapping (midi, dur_slots) -> tuple of viable OffsetResults.
    """
    if not uncached:
        return {}
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    lut_strong, lut_weak, lut_fatal = _get_luts(device)
    # ── Group by dur_slots ──────────────────────────────────────
    groups: dict[tuple[int, ...], list[tuple[int, tuple[int, ...]]]] = {}
    for idx, (midi, dur_slots) in enumerate(uncached):
        groups.setdefault(dur_slots, []).append((idx, midi))
    results: dict[tuple[tuple[int, ...], tuple[int, ...]], tuple[OffsetResult, ...]] = {}
    for dur_slots, members in groups.items():
        offset_checks = _precompute_checks_for_dur(dur_slots, metre)
        n_offsets = len(offset_checks)
        if n_offsets == 0:
            empty: tuple[OffsetResult, ...] = ()
            for _, midi in members:
                results[(midi, dur_slots)] = empty
            continue
        # ── Pack check points into tensors ──────────────────────
        max_checks = max(len(cks) for _, cks in offset_checks)
        if max_checks == 0:
            # All offsets have zero checks → all viable with quality 1.0
            all_viable: tuple[OffsetResult, ...] = tuple(
                OffsetResult(
                    offset_slots=off,
                    viable=True,
                    consonant_count=0,
                    total_count=0,
                    dissonance_cost=0,
                    quality=1.0,
                )
                for off, _ in offset_checks
            )
            for _, midi in members:
                results[(midi, dur_slots)] = all_viable
            continue
        offset_slots_list = [off for off, _ in offset_checks]
        t_leaders = torch.zeros(n_offsets, max_checks, dtype=torch.long, device=device)
        t_followers = torch.zeros(n_offsets, max_checks, dtype=torch.long, device=device)
        t_strong = torch.zeros(n_offsets, max_checks, dtype=torch.bool, device=device)
        t_collision = torch.zeros(n_offsets, max_checks, dtype=torch.int32, device=device)
        t_valid = torch.zeros(n_offsets, max_checks, dtype=torch.bool, device=device)
        t_count = torch.zeros(n_offsets, dtype=torch.int32, device=device)
        for oi, (_, checks) in enumerate(offset_checks):
            nc = len(checks)
            t_count[oi] = nc
            for ci, ck in enumerate(checks):
                t_leaders[oi, ci] = ck.leader_idx
                t_followers[oi, ci] = ck.follower_idx
                t_strong[oi, ci] = ck.is_strong
                t_collision[oi, ci] = ck.collision_slots
                t_valid[oi, ci] = True
        # ── Stack MIDI pitches ──────────────────────────────────
        n_members = len(members)
        num_notes = len(members[0][1])
        midi_tensor = torch.zeros(n_members, num_notes, dtype=torch.long, device=device)
        for mi, (_, midi) in enumerate(members):
            for ni, p in enumerate(midi):
                midi_tensor[mi, ni] = p
        # ── Evaluate: (N, O, max_C) ────────────────────────────
        # Gather pitches at check-point indices
        # t_leaders/t_followers: (O, max_C) -> expand to (N, O, max_C)
        leaders_exp = t_leaders.unsqueeze(0).expand(n_members, -1, -1)
        followers_exp = t_followers.unsqueeze(0).expand(n_members, -1, -1)
        leader_pitch = midi_tensor.unsqueeze(1).expand(-1, n_offsets, -1).gather(2, leaders_exp)
        follower_pitch = midi_tensor.unsqueeze(1).expand(-1, n_offsets, -1).gather(2, followers_exp)
        intervals = (leader_pitch - follower_pitch).abs() % 12
        # Strong-beat consonance
        strong_consonant = lut_strong[intervals]
        strong_fail = t_strong.unsqueeze(0) & t_valid.unsqueeze(0) & ~strong_consonant
        any_strong_fail = strong_fail.any(dim=2)
        # Weak-beat fatal intervals
        is_fatal = lut_fatal[intervals] & ~t_strong.unsqueeze(0) & t_valid.unsqueeze(0)
        any_fatal = is_fatal.any(dim=2)
        # Consonance count and quality
        is_consonant = lut_weak[intervals] & t_valid.unsqueeze(0)
        consonant_count = is_consonant.sum(dim=2)
        total_count_exp = t_count.unsqueeze(0).expand(n_members, -1)
        quality = torch.where(
            total_count_exp > 0,
            consonant_count.float() / total_count_exp.float(),
            torch.ones(1, device=device),
        )
        # Dissonance cost: collision slots at non-consonant weak-beat checks
        is_dissonant_weak = t_valid.unsqueeze(0) & ~t_strong.unsqueeze(0) & ~lut_weak[intervals]
        cost = (is_dissonant_weak.int() * t_collision.unsqueeze(0)).sum(dim=2)
        # Viable: no strong fail, no weak fatal, quality >= threshold
        viable = ~any_strong_fail & ~any_fatal & (quality >= STRETTO_MIN_QUALITY)
        viable = viable | (total_count_exp == 0)
        # ── Transfer to CPU and build OffsetResult tuples ───────
        viable_cpu = viable.cpu()
        consonant_cpu = consonant_count.cpu()
        total_cpu = total_count_exp.cpu()
        cost_cpu = cost.cpu()
        quality_cpu = quality.cpu()
        for mi, (_, midi) in enumerate(members):
            offsets: list[OffsetResult] = []
            for oi in range(n_offsets):
                v = viable_cpu[mi, oi].item()
                offsets.append(OffsetResult(
                    offset_slots=offset_slots_list[oi],
                    viable=bool(v),
                    consonant_count=int(consonant_cpu[mi, oi].item()),
                    total_count=int(total_cpu[mi, oi].item()),
                    dissonance_cost=int(cost_cpu[mi, oi].item()),
                    quality=float(quality_cpu[mi, oi].item()),
                ))
            results[(midi, dur_slots)] = tuple(r for r in offsets if r.viable)
    return results
