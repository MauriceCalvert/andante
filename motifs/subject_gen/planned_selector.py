"""Plan-driven subject selection.

Replaces the flat enumeration in selector.py with structured generation:
plan -> segment rhythms -> concatenated pitches -> contour filter -> score.
"""
import logging
import math
import time
from collections import Counter

from motifs.head_generator import degrees_to_midi, midi_to_degrees
from motifs.stretto_constraints import OffsetResult, evaluate_all_offsets
from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.constants import (
    DURATION_TICKS,
    HEAD_SIZE,
    MIN_AESTHETIC_SCORE,
    MIN_HEAD_FINAL_DUR_TICKS,
    MIN_STRETTO_OFFSETS,
    X2_TICKS_PER_WHOLE,
    _bar_x2_ticks,
    DEGREES_PER_OCTAVE,
)
from motifs.subject_gen.contour import _derive_leap_info, _derive_shape_name
from motifs.subject_gen.contour_filter import check_plan_contours
from motifs.subject_gen.melody_generator import generate_pitched_subjects
from motifs.subject_gen.models import GeneratedSubject, _ScoredPitch
from motifs.subject_gen.rhythm_cells import Cell
from motifs.subject_gen.pitch_generator import _cached_validated_pitch_for_cells
from motifs.subject_gen.scoring import score_subject, subject_features
from motifs.subject_gen.segment_rhythm import (
    boundary_transition_ok,
    generate_segment_rhythms,
)
from motifs.subject_gen.subject_planner import (
    SubjectPlan,
    SubjectVocabulary,
    _DENSITY_SCALES,
    generate_plans,
)

logger: logging.Logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────

MAX_RHYTHM_PAIRINGS_PER_PLAN: int = 50
MAX_PITCHES_PER_PAIRING: int = 200


# ── Helpers ──────────────────────────────────────────────────────────

def _invert_midi(midi: tuple[int, ...]) -> tuple[int, ...]:
    """Mirror MIDI pitches around the first note."""
    pivot: int = midi[0]
    return tuple(2 * pivot - p for p in midi)


def _feature_distance(
    a: tuple[float, ...],
    b: tuple[float, ...],
) -> float:
    """Euclidean distance between two feature vectors."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _build_subject(
    sp: _ScoredPitch,
    best_durs: tuple[int, ...],
    tonic_midi: int,
    mode: str,
    metre: tuple[int, int],
    bar_ticks: int,
    final_score: float,
    cached_viable_offsets: tuple[OffsetResult, ...] | None = None,
    cached_inverted_offsets: tuple[OffsetResult, ...] | None = None,
) -> GeneratedSubject:
    """Convert a scored pitch + duration pair into a GeneratedSubject."""
    dur_ticks = [DURATION_TICKS[d] for d in best_durs]
    bars = sum(dur_ticks) // bar_ticks
    durations = tuple(t / X2_TICKS_PER_WHOLE for t in dur_ticks)
    midi_pitches = degrees_to_midi(degrees=sp.degrees, tonic_midi=tonic_midi, mode=mode)
    leap_size, leap_direction, tail_direction = _derive_leap_info(sp.ivs)
    dur_slots = tuple(DURATION_TICKS[d] for d in best_durs)
    if cached_viable_offsets is not None:
        viable_offsets = cached_viable_offsets
    else:
        all_offsets = evaluate_all_offsets(
            midi=midi_pitches,
            dur_slots=dur_slots,
            metre=metre,
        )
        viable_offsets = tuple(r for r in all_offsets if r.viable)
    if cached_inverted_offsets is not None:
        inv_offsets = cached_inverted_offsets
    else:
        inv_midi = _invert_midi(midi_pitches)
        all_inv = evaluate_all_offsets(
            midi=midi_pitches,
            dur_slots=dur_slots,
            metre=metre,
            follower_midi=inv_midi,
        )
        inv_offsets = tuple(r for r in all_inv if r.viable)
    return GeneratedSubject(
        scale_indices=sp.degrees,
        durations=durations,
        midi_pitches=midi_pitches,
        bars=bars,
        score=final_score,
        seed=0,
        mode=mode,
        head_name=sp.shape,
        leap_size=leap_size,
        leap_direction=leap_direction,
        tail_direction=tail_direction,
        stretto_offsets=viable_offsets,
        inverted_stretto_offsets=inv_offsets,
    )


# ── Segment rhythm cache ─────────────────────────────────────────────

_seg_rhythm_cache: dict[
    tuple[tuple[str, ...], int, int, tuple[int, ...]],
    list[tuple[tuple[int, ...], tuple[Cell, ...]]]
] = {}


def _cached_segment_rhythms(
    cell_names: tuple[str, ...],
    n_notes: int,
    total_ticks: int,
    allowed_scales: tuple[int, ...],
) -> list[tuple[tuple[int, ...], tuple[Cell, ...]]]:
    """Generate and cache segment rhythms."""
    key = (cell_names, n_notes, total_ticks, allowed_scales)
    if key in _seg_rhythm_cache:
        return _seg_rhythm_cache[key]
    raw = generate_segment_rhythms(
        n_notes=n_notes,
        total_ticks=total_ticks,
        allowed_cell_names=cell_names,
        allowed_scales=allowed_scales,
    )
    # Keep top entries by score, drop score.
    raw.sort(key=lambda x: x[2], reverse=True)
    result: list[tuple[tuple[int, ...], tuple[Cell, ...]]] = [
        (indices, cells) for indices, cells, _ in raw
    ]
    _seg_rhythm_cache[key] = result
    return result


# ── Main entry point ─────────────────────────────────────────────────

def select_planned_subjects(
    n: int = 6,
    mode: str = "major",
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    target_bars: int | None = None,
    note_counts: tuple[int, ...] | None = None,
    verbose: bool = False,
) -> list[GeneratedSubject]:
    """Select n subjects using plan-driven structured generation."""
    if target_bars is None:
        target_bars = 2
    bar_ticks: int = _bar_x2_ticks(metre)
    total_ticks: int = target_bars * bar_ticks
    t_start: float = time.time()
    if verbose:
        print(f"planned_select: n={n} mode={mode} metre={metre} bars={target_bars}")
    # ── Generate plans ──────────────────────────────────────────
    all_plans: list[SubjectPlan] = generate_plans(
        total_notes_range=note_counts,
    )
    if verbose:
        print(f"  {len(all_plans):,} plans generated")
    # ── Group plans by rhythm key ────────────────────────────────
    # Dimensions that affect rhythm/pitch: (cells, density, head_n, tail_n).
    # Dimensions that only affect contour filter: motion, sig_interval,
    # head_contour, tail_contour.  Grouping avoids 48× redundant work.
    _RhythmKey = tuple[tuple[str, ...], str, int, int]
    rhythm_groups: dict[
        _RhythmKey,
        list[SubjectPlan],
    ] = {}
    for plan in all_plans:
        rk: _RhythmKey = (
            plan.vocabulary.cells,
            plan.vocabulary.density,
            plan.head.n_notes,
            plan.tail.n_notes,
        )
        rhythm_groups.setdefault(rk, []).append(plan)
    if verbose:
        print(f"  {len(rhythm_groups):,} rhythm groups")
    # ── Realise groups into candidates ──────────────────────────
    pool: list[tuple[_ScoredPitch, tuple[int, ...]]] = []
    seen_sequences: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
    groups_with_rhythm: int = 0
    groups_with_pitches: int = 0
    head_tick_budget: int = bar_ticks  # head = bar 1
    tail_tick_budget: int = total_ticks - head_tick_budget  # tail = bar 2
    for (cell_names, density, head_n, tail_n), plan_group in rhythm_groups.items():
        scales: tuple[int, ...] = _DENSITY_SCALES[density]
        # Head rhythms.
        head_rhythms = _cached_segment_rhythms(
            cell_names=cell_names,
            n_notes=head_n,
            total_ticks=head_tick_budget,
            allowed_scales=scales,
        )
        if not head_rhythms:
            continue
        # Tail rhythms.
        tail_rhythms = _cached_segment_rhythms(
            cell_names=cell_names,
            n_notes=tail_n,
            total_ticks=tail_tick_budget,
            allowed_scales=scales,
        )
        if not tail_rhythms:
            continue
        groups_with_rhythm += 1
        # Pair head × tail with boundary check, capped.
        pairings: list[tuple[tuple[int, ...], tuple[Cell, ...]]] = []
        for h_indices, h_cells in head_rhythms:
            for t_indices, t_cells in tail_rhythms:
                if not boundary_transition_ok(
                    head_cells=h_cells,
                    tail_cells=t_cells,
                ):
                    continue
                combined_indices: tuple[int, ...] = h_indices + t_indices
                combined_cells: tuple[Cell, ...] = h_cells + t_cells
                pairings.append((combined_indices, combined_cells))
                if len(pairings) >= MAX_RHYTHM_PAIRINGS_PER_PLAN:
                    break
            if len(pairings) >= MAX_RHYTHM_PAIRINGS_PER_PLAN:
                break
        if not pairings:
            continue
        # Collect contour specs for all plans in this group.
        contour_specs: list[
            tuple[int, str, str, int]
        ] = list({(
            p.head.n_notes,
            p.head.contour,
            p.tail.contour,
            p.vocabulary.signature_interval,
        ) for p in plan_group})
        # Generate pitches for each pairing, then scatter contour checks.
        for combined_indices, combined_cells in pairings:
            all_pitched: list[_ScoredPitch] = _cached_validated_pitch_for_cells(
                cell_sequence=combined_cells,
                tonic_midi=tonic_midi,
                mode=mode,
                n_bars=target_bars,
                bar_ticks=bar_ticks,
                verbose=False,
            )
            if not all_pitched:
                continue
            groups_with_pitches += 1
            for sp in all_pitched[:MAX_PITCHES_PER_PAIRING]:
                dedup_key = (sp.degrees, combined_indices)
                if dedup_key in seen_sequences:
                    continue
                for h_n, h_con, t_con, sig_iv in contour_specs:
                    if check_plan_contours(
                        all_pitches=sp.degrees,
                        head_n=h_n,
                        head_contour=h_con,
                        tail_contour=t_con,
                        signature_interval=sig_iv,
                    ):
                        seen_sequences.add(dedup_key)
                        pool.append((sp, combined_indices))
                        break
    if verbose:
        print(f"  Groups with rhythm: {groups_with_rhythm:,}")
        print(f"  Groups with pitches: {groups_with_pitches:,}")
        print(f"  Contour-passing candidates: {len(pool):,}")
    if not pool:
        if verbose:
            print("  WARNING: no candidates survived contour filter")
        return []
    # ── Octave dedup ────────────────────────────────────────────
    pitch_best: dict[tuple[int, ...], int] = {}
    for pi, (sp, _) in enumerate(pool):
        mod_key: tuple[int, ...] = tuple(d % DEGREES_PER_OCTAVE for d in sp.degrees)
        if mod_key not in pitch_best:
            pitch_best[mod_key] = pi
    pool = [pool[i] for i in sorted(pitch_best.values())]
    if verbose:
        print(f"  After octave dedup: {len(pool):,}")
    # ── Stretto evaluation ──────────────────────────────────────
    cache_name: str = f"stretto_planned_{mode}_{target_bars}b_{bar_ticks}t.pkl"
    loaded = _load_cache(cache_name)
    stretto_cache: dict[
        tuple[tuple[int, ...], tuple[int, ...]],
        tuple[OffsetResult, ...]
    ] = loaded if isinstance(loaded, dict) else {}
    uncached_items: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    uncached_keys: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for sp, dur_indices in pool:
        dur_slots = tuple(DURATION_TICKS[d] for d in dur_indices)
        cache_key = (sp.degrees, dur_indices)
        if cache_key not in stretto_cache:
            midi_pitches = degrees_to_midi(
                degrees=sp.degrees, tonic_midi=tonic_midi, mode=mode,
            )
            uncached_items.append((midi_pitches, dur_slots))
            uncached_keys.append(cache_key)
    if uncached_items:
        if verbose:
            print(f"  Evaluating {len(uncached_items):,} unison stretto on GPU...")
        from motifs.subject_gen.stretto_gpu import batch_evaluate_stretto
        gpu_items_unison = [
            (midi, midi, dur_slots) for midi, dur_slots in uncached_items
        ]
        gpu_results = batch_evaluate_stretto(
            uncached=gpu_items_unison,
            metre=metre,
        )
        for (midi_pitches, dur_slots), cache_key in zip(uncached_items, uncached_keys):
            stretto_cache[cache_key] = gpu_results[(midi_pitches, midi_pitches, dur_slots)]
        _save_cache(cache_name, stretto_cache)
    # ── Inverted stretto ────────────────────────────────────────
    inv_cache_name: str = f"stretto_inv_planned_{mode}_{target_bars}b_{bar_ticks}t.pkl"
    loaded_inv = _load_cache(inv_cache_name)
    inv_stretto_cache: dict[
        tuple[tuple[int, ...], tuple[int, ...]],
        tuple[OffsetResult, ...]
    ] = loaded_inv if isinstance(loaded_inv, dict) else {}
    inv_uncached_items: list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]] = []
    inv_uncached_keys: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for sp, dur_indices in pool:
        dur_slots = tuple(DURATION_TICKS[d] for d in dur_indices)
        cache_key = (sp.degrees, dur_indices)
        if cache_key not in inv_stretto_cache:
            midi_pitches = degrees_to_midi(
                degrees=sp.degrees, tonic_midi=tonic_midi, mode=mode,
            )
            inv_midi = _invert_midi(midi_pitches)
            inv_uncached_items.append((midi_pitches, inv_midi, dur_slots))
            inv_uncached_keys.append(cache_key)
    if inv_uncached_items:
        if verbose:
            print(f"  Evaluating {len(inv_uncached_items):,} inverted stretto on GPU...")
        from motifs.subject_gen.stretto_gpu import batch_evaluate_stretto
        inv_gpu_results = batch_evaluate_stretto(
            uncached=inv_uncached_items,
            metre=metre,
        )
        for (midi_pitches, inv_midi, dur_slots), cache_key in zip(inv_uncached_items, inv_uncached_keys):
            inv_stretto_cache[cache_key] = inv_gpu_results[(midi_pitches, inv_midi, dur_slots)]
        _save_cache(inv_cache_name, inv_stretto_cache)
    # ── Score all candidates ────────────────────────────────────
    scored: list[tuple[float, int, _ScoredPitch, tuple[int, ...], tuple[OffsetResult, ...], tuple[OffsetResult, ...], tuple[float, ...]]] = []
    for sp, dur_indices in pool:
        cache_key = (sp.degrees, dur_indices)
        viable_offsets = stretto_cache[cache_key]
        inv_offsets = inv_stretto_cache.get(cache_key, ())
        combined_count: int = len(viable_offsets) + len(inv_offsets)
        if combined_count < MIN_STRETTO_OFFSETS:
            continue
        aesthetic: float = score_subject(
            degrees=sp.degrees,
            ivs=sp.ivs,
            dur_indices=dur_indices,
        )
        if aesthetic < MIN_AESTHETIC_SCORE:
            continue
        all_offsets = viable_offsets + inv_offsets
        min_offset: int = min(r.offset_slots for r in all_offsets)
        features: tuple[float, ...] = subject_features(
            degrees=sp.degrees,
            ivs=sp.ivs,
            dur_indices=dur_indices,
        )
        scored.append((aesthetic, min_offset, sp, dur_indices, viable_offsets, inv_offsets, features))
    scored.sort(key=lambda x: (-x[0], x[1]))
    if verbose:
        print(f"  Stretto-viable above floor: {len(scored):,}")
    if not scored:
        if verbose:
            print("  WARNING: no candidates with stretto")
        return []
    # ── Greedy score-weighted max-min feature-distance selection ──
    # Pure max-min distance pulls in low-quality outliers.  Weighting
    # by aesthetic score / max ensures quality competes with diversity.
    if len(scored) <= n:
        picks = list(range(len(scored)))
    else:
        max_aesthetic: float = scored[0][0]
        picks: list[int] = [0]
        for _ in range(n - 1):
            best_idx: int = -1
            best_effective: float = -1.0
            picked_features: list[tuple[float, ...]] = [scored[p][6] for p in picks]
            for ci in range(len(scored)):
                if ci in picks:
                    continue
                ci_features: tuple[float, ...] = scored[ci][6]
                min_dist: float = min(
                    _feature_distance(ci_features, pf) for pf in picked_features
                )
                score_factor: float = scored[ci][0] / max_aesthetic
                effective: float = min_dist * score_factor
                if effective > best_effective:
                    best_effective = effective
                    best_idx = ci
            assert best_idx >= 0
            picks.append(best_idx)
    # ── Build GeneratedSubject for each pick ────────────────────
    results: list[GeneratedSubject] = []
    for pi in picks:
        aesthetic_sc, _, sp, best_d_seq, viable_offsets, inv_offsets, _ = scored[pi]
        subj = _build_subject(
            sp=sp,
            best_durs=best_d_seq,
            tonic_midi=tonic_midi,
            mode=mode,
            metre=metre,
            bar_ticks=bar_ticks,
            final_score=aesthetic_sc,
            cached_viable_offsets=viable_offsets,
            cached_inverted_offsets=inv_offsets,
        )
        results.append(subj)
    elapsed: float = time.time() - t_start
    if verbose:
        for i, subj in enumerate(results):
            dur_str: str = ",".join(str(d) for d in subj.durations)
            print(f"  [{i}] {subj.head_name} {len(subj.scale_indices)}n "
                  f"aesthetic={subj.score:.2f} degrees={subj.scale_indices} "
                  f"durs=({dur_str}) stretto={len(subj.stretto_offsets)} "
                  f"inv={len(subj.inverted_stretto_offsets)}")
        print(f"  Selected {len(results)} in {elapsed:.2f}s")
    return results
