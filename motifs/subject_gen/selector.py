"""Diversity selection and subject assembly."""
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
    MIN_DIVERSITY_DISTANCE,
    MIN_HEAD_FINAL_DUR_TICKS,
    MIN_STRETTO_OFFSETS,
    X2_TICKS_PER_WHOLE,
    _bar_x2_ticks, MAX_SUBJECT_NOTES,
)
from motifs.subject_gen.contour import _derive_leap_info, _derive_shape_name
from motifs.subject_gen.duration_generator import _cached_scored_durations
from motifs.subject_gen.models import GeneratedSubject, _ScoredPitch
from motifs.subject_gen.rhythm_cells import Cell
from motifs.subject_gen.pitch_generator import _cached_validated_pitch_for_cells
from motifs.subject_gen.scoring import score_subject, subject_features


def _invert_midi(midi: tuple[int, ...]) -> tuple[int, ...]:
    """Mirror MIDI pitches around the first note (diatonic-agnostic)."""
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


def select_diverse_subjects(
    n: int = 6,
    mode: str = "major",
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    target_bars: int | None = None,
    pitch_contour: str | None = None,
    note_counts: tuple[int, ...] | None = None,
    fixed_midi: tuple[int, ...] | None = None,
    verbose: bool = False,
) -> list[GeneratedSubject]:
    """Select n subjects maximising pairwise feature distance."""
    if target_bars is None:
        target_bars = 2
    bar_ticks = _bar_x2_ticks(metre)
    t_start = time.time()
    if verbose:
        print(f"select_diverse: n={n} mode={mode} metre={metre} bars={target_bars}")
    # ── Durations: all valid patterns per note count ─────────────
    all_durs_by_count: dict[int, list[tuple[tuple[int, ...], tuple[Cell, ...]]]] = _cached_scored_durations(
        n_bars=target_bars,
        bar_ticks=bar_ticks,
        verbose=verbose,
    )
    assert len(all_durs_by_count) > 0, f"No durations for bars={target_bars} metre={metre}"
    total_durs: int = sum(len(v) for v in all_durs_by_count.values())
    print(f"[subject_gen] durations: {total_durs} sequences across note counts {sorted(all_durs_by_count.keys())}")
    # ── Pitch × Duration: pair each pitch with each valid duration ──
    pool: list[tuple[_ScoredPitch, tuple[int, ...]]] = []
    pitch_gen_count: int = 0
    pitch_gen_total: int = total_durs if fixed_midi is not None else sum(
        len(all_durs_by_count.get(nc, []))
        for nc in sorted(all_durs_by_count.keys())
        if note_counts is None or nc in note_counts
    )
    t_pitch_start = time.time()
    if fixed_midi is not None:
        # Fixed pitches: bypass pitch generation, explore durations only
        fixed_degrees: tuple[int, ...] = midi_to_degrees(
            midi_pitches=fixed_midi,
            tonic_midi=tonic_midi,
            mode=mode,
        )
        fixed_ivs: tuple[int, ...] = tuple(
            fixed_degrees[i + 1] - fixed_degrees[i]
            for i in range(len(fixed_degrees) - 1)
        )
        fixed_shape: str = _derive_shape_name(list(fixed_degrees))
        fixed_sp = _ScoredPitch(
            score=0.0,
            ivs=fixed_ivs,
            degrees=fixed_degrees,
            shape=fixed_shape,
        )
        nc: int = len(fixed_midi)
        assert nc in all_durs_by_count, (
            f"No durations for {nc} notes in {target_bars} bars of {metre}"
        )
        dur_options = all_durs_by_count[nc]
        if verbose:
            print(f"  Fixed pitches: {nc}n × {len(dur_options)} durations")
        for d_seq, _cells in dur_options:
            pool.append((fixed_sp, d_seq))
        print(f"[subject_gen] fixed pitches: {len(pool)} pitch×dur pairs in {time.time() - t_pitch_start:.1f}s")
    else:
        for nc in sorted(all_durs_by_count.keys()):
            if note_counts is not None and nc not in note_counts:
                continue
            dur_options = all_durs_by_count[nc]
            nc_before: int = len(pool)
            for d_seq, cells in dur_options:
                pitch_gen_count += 1
                if pitch_gen_count % 200 == 0 or pitch_gen_count == 1:
                    print(f"[subject_gen] pitch gen {pitch_gen_count}/{pitch_gen_total} "
                          f"({nc}n) pool={len(pool)} elapsed={time.time() - t_pitch_start:.1f}s")
                if DURATION_TICKS[d_seq[HEAD_SIZE - 1]] < MIN_HEAD_FINAL_DUR_TICKS:
                    continue
                if len(set(d_seq[:HEAD_SIZE])) < 2:
                    continue
                all_pitch = _cached_validated_pitch_for_cells(
                    cell_sequence=cells,
                    tonic_midi=tonic_midi,
                    mode=mode,
                    n_bars=target_bars,
                    bar_ticks=bar_ticks,
                    verbose=verbose,
                )
                for sp in all_pitch:
                    pool.append((sp, d_seq))
            print(f"[subject_gen] {nc}n complete: +{len(pool) - nc_before} pairs, "
                  f"pool={len(pool)}, {time.time() - t_pitch_start:.1f}s")
    assert len(pool) > 0, (
        f"No valid subjects found for bars={target_bars} metre={metre} "
        f"note_counts={note_counts} (MAX_SUBJECT_NOTES={MAX_SUBJECT_NOTES})"
    )
    # ── Contour hard filter ─────────────────────────────────────
    if pitch_contour is not None:
        available_contours = sorted({sp.shape for sp, _ in pool})
        if verbose:
            contour_dist = Counter(sp.shape for sp, _ in pool)
            print(f"  Contour distribution: {dict(contour_dist)}")
        pool = [(sp, durs) for sp, durs in pool if sp.shape == pitch_contour]
        assert len(pool) > 0, (
            f"No subjects with contour={pitch_contour!r}; "
            f"available: {available_contours}"
        )
    # ── Dedup (key: degrees + dur_pattern) ─────────────────────
    seen: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
    candidates: list[tuple[_ScoredPitch, tuple[int, ...]]] = []
    for sp, d_seq in pool:
        dedup_key = (sp.degrees, d_seq)
        if dedup_key not in seen:
            seen.add(dedup_key)
            candidates.append((sp, d_seq))
    print(f"[subject_gen] dedup: {len(pool)} -> {len(candidates)} candidates")
    # ── Stretto filter + aesthetic scoring ──────────────────────
    cache_name = f"stretto_eval_{mode}_{target_bars}b_{bar_ticks}t.pkl"
    loaded = _load_cache(cache_name)
    stretto_cache: dict[tuple[tuple[int, ...], tuple[int, ...]], tuple[OffsetResult, ...]] = (
        loaded if isinstance(loaded, dict) else {}
    )
    # ── Batch GPU evaluation for uncached candidates ────────────
    uncached_items: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    uncached_keys: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for sp, dur_seq in candidates:
        dur_slots = tuple(DURATION_TICKS[d] for d in dur_seq)
        cache_key = (sp.degrees, dur_seq)
        if cache_key not in stretto_cache:
            midi_pitches = degrees_to_midi(degrees=sp.degrees, tonic_midi=tonic_midi, mode=mode)
            uncached_items.append((midi_pitches, dur_slots))
            uncached_keys.append(cache_key)
    new_entries: int = len(uncached_items)
    if new_entries > 0:
        print(f"[subject_gen] stretto: evaluating {new_entries:,} uncached candidates on GPU...")
        from motifs.subject_gen.stretto_gpu import batch_evaluate_stretto
        t_stretto = time.time()
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
        print(f"[subject_gen] stretto unison: done in {time.time() - t_stretto:.1f}s")
    else:
        print(f"[subject_gen] stretto unison: all {len(candidates)} from cache")
    # ── Inverted stretto: same offsets, follower plays mirror ───
    inv_cache_name = f"stretto_inv_{mode}_{target_bars}b_{bar_ticks}t.pkl"
    loaded_inv = _load_cache(inv_cache_name)
    inv_stretto_cache: dict[tuple[tuple[int, ...], tuple[int, ...]], tuple[OffsetResult, ...]] = (
        loaded_inv if isinstance(loaded_inv, dict) else {}
    )
    inv_uncached_items: list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]] = []
    inv_uncached_keys: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for sp, dur_seq in candidates:
        dur_slots = tuple(DURATION_TICKS[d] for d in dur_seq)
        cache_key = (sp.degrees, dur_seq)
        if cache_key not in inv_stretto_cache:
            midi_pitches = degrees_to_midi(degrees=sp.degrees, tonic_midi=tonic_midi, mode=mode)
            inv_midi = _invert_midi(midi_pitches)
            inv_uncached_items.append((midi_pitches, inv_midi, dur_slots))
            inv_uncached_keys.append(cache_key)
    inv_new: int = len(inv_uncached_items)
    if inv_new > 0:
        print(f"[subject_gen] stretto inv: evaluating {inv_new:,} uncached candidates on GPU...")
        from motifs.subject_gen.stretto_gpu import batch_evaluate_stretto
        t_inv = time.time()
        inv_gpu_results = batch_evaluate_stretto(
            uncached=inv_uncached_items,
            metre=metre,
        )
        for (midi_pitches, inv_midi, dur_slots), cache_key in zip(inv_uncached_items, inv_uncached_keys):
            inv_stretto_cache[cache_key] = inv_gpu_results[(midi_pitches, inv_midi, dur_slots)]
        _save_cache(inv_cache_name, inv_stretto_cache)
        print(f"[subject_gen] stretto inv: done in {time.time() - t_inv:.1f}s")
    else:
        print(f"[subject_gen] stretto inv: all {len(candidates)} from cache")
    # ── Score all candidates ────────────────────────────────────
    # (aesthetic, min_offset, sp, dur_seq, viable_offsets, inv_offsets, features)
    scored: list[tuple[float, int, _ScoredPitch, tuple[int, ...], tuple[OffsetResult, ...], tuple[OffsetResult, ...], tuple[float, ...]]] = []
    for sp, dur_seq in candidates:
        cache_key = (sp.degrees, dur_seq)
        viable_offsets = stretto_cache[cache_key]
        inv_offsets = inv_stretto_cache.get(cache_key, ())
        combined_count: int = len(viable_offsets) + len(inv_offsets)
        if combined_count < MIN_STRETTO_OFFSETS:
            continue
        aesthetic: float = score_subject(
            degrees=sp.degrees,
            ivs=sp.ivs,
            dur_indices=dur_seq,
        )
        all_offsets = viable_offsets + inv_offsets
        min_offset: int = min(r.offset_slots for r in all_offsets)
        features: tuple[float, ...] = subject_features(
            degrees=sp.degrees,
            ivs=sp.ivs,
            dur_indices=dur_seq,
        )
        scored.append((aesthetic, min_offset, sp, dur_seq, viable_offsets, inv_offsets, features))
    # ── Sort: aesthetic descending, then min_offset ascending (tighter stretto) ──
    scored.sort(key=lambda x: (-x[0], x[1]))
    # ── Aesthetic floor: drop weak candidates before diversity selection ──
    pre_floor: int = len(scored)
    scored = [s for s in scored if s[0] >= MIN_AESTHETIC_SCORE]
    print(f"[subject_gen] aesthetic floor: {len(scored)}/{pre_floor} candidates >= {MIN_AESTHETIC_SCORE}")
    assert len(scored) > 0, (
        f"No candidates with aesthetic score >= {MIN_AESTHETIC_SCORE}"
    )
    if verbose:
        print(
            f"  Pool: {len(pool)} total, {len(scored)} with "
            f">= {MIN_STRETTO_OFFSETS} stretto "
            f"(cache_hits={len(candidates) - new_entries})"
        )
    assert len(scored) > 0, (
        f"No candidates with >= {MIN_STRETTO_OFFSETS} stretto offsets"
    )
    # ── Pitch dedup: at most one candidate per degree sequence ──
    # Compare degrees mod 7 so octave transpositions collapse.
    # Skip when pitches are fixed — all candidates share the same degrees.
    if fixed_midi is None:
        pitch_best: dict[tuple[int, ...], int] = {}
        for si, (_, _, sp, _, _, _, _) in enumerate(scored):
            mod_key: tuple[int, ...] = tuple(d % 7 for d in sp.degrees)
            if mod_key not in pitch_best:
                pitch_best[mod_key] = si
        scored = [scored[i] for i in sorted(pitch_best.values())]
        if verbose:
            print(f"  Pitch dedup: {len(pitch_best)} distinct pitches, {len(scored)} candidates")

    print(f"[subject_gen] scored: {len(scored)} candidates passed stretto+aesthetic filter")
    # ── Greedy max-min feature-distance selection ──────────────
    t_diversity = time.time()
    picks: list[int] = [0]  # best aesthetic score
    cap: int = min(n, len(scored))
    for _ in range(cap - 1):
        best_idx: int = -1
        best_min_dist: float = -1.0
        picked_features: list[tuple[float, ...]] = [scored[p][6] for p in picks]
        for ci in range(len(scored)):
            if ci in picks:
                continue
            ci_features: tuple[float, ...] = scored[ci][6]
            min_dist: float = min(
                _feature_distance(ci_features, pf) for pf in picked_features
            )
            if min_dist > best_min_dist:
                best_min_dist = min_dist
                best_idx = ci
        if best_idx < 0 or best_min_dist < MIN_DIVERSITY_DISTANCE:
            break
        picks.append(best_idx)
    print(f"[subject_gen] diversity selection: picked {len(picks)} in {time.time() - t_diversity:.1f}s")
    # ── Build GeneratedSubject for each pick ──────────────────
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
    elapsed = time.time() - t_start
    if verbose:
        for i, subj in enumerate(results):
            dur_str: str = ",".join(str(d) for d in subj.durations)
            print(f"  [{i}] {subj.head_name} {len(subj.scale_indices)}n "
                  f"aesthetic={subj.score:.2f} degrees={subj.scale_indices} "
                  f"durs=({dur_str}) stretto={len(subj.stretto_offsets)} "
                  f"inv={len(subj.inverted_stretto_offsets)}")
        print(f"  Selected {len(results)} in {elapsed:.2f}s")
    return results


def select_subject(
    mode: str = "major",
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    target_bars: int | None = None,
    pitch_contour: str | None = None,
    rhythm_contour: str | None = None,
    note_counts: tuple[int, ...] | None = None,
    fixed_midi: tuple[int, ...] | None = None,
    seed: int = 0,
    verbose: bool = False,
) -> GeneratedSubject:
    """Select a single subject (seed indexes into a diverse set)."""
    subjects = select_diverse_subjects(
        n=6,
        mode=mode,
        metre=metre,
        tonic_midi=tonic_midi,
        target_bars=target_bars,
        pitch_contour=pitch_contour,
        note_counts=note_counts,
        fixed_midi=fixed_midi,
        verbose=verbose,
    )
    return subjects[seed % len(subjects)]
