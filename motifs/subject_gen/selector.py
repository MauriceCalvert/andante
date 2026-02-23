"""Diversity selection and subject assembly."""
import time
from collections import Counter

from motifs.head_generator import degrees_to_midi
from motifs.stretto_constraints import OffsetResult, evaluate_all_offsets
from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.constants import (
    DURATION_TICKS,
    MIN_STRETTO_OFFSETS,
    X2_TICKS_PER_WHOLE,
    _bar_x2_ticks,
)
from motifs.subject_gen.contour import _derive_leap_info
from motifs.subject_gen.duration_generator import _cached_scored_durations
from motifs.subject_gen.models import GeneratedSubject, _ScoredPitch
from motifs.subject_gen.pitch_generator import _cached_validated_pitch


def _subject_distance(
    a_degs: tuple[int, ...],
    a_durs: tuple[int, ...],
    b_degs: tuple[int, ...],
    b_durs: tuple[int, ...],
) -> int:
    """Hamming distance over degrees + durations (different lengths = max)."""
    a = a_degs + a_durs
    b = b_degs + b_durs
    if len(a) != len(b):
        return max(len(a), len(b))
    return sum(1 for x, y in zip(a, b) if x != y)


def _build_subject(
    sp: _ScoredPitch,
    best_durs: tuple[int, ...],
    tonic_midi: int,
    mode: str,
    metre: tuple[int, int],
    bar_ticks: int,
    final_score: float,
    cached_viable_offsets: tuple[OffsetResult, ...] | None = None,
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
    )


def select_diverse_subjects(
    n: int = 6,
    mode: str = "major",
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    target_bars: int | None = None,
    pitch_contour: str | None = None,
    note_counts: tuple[int, ...] | None = None,
    verbose: bool = False,
) -> list[GeneratedSubject]:
    """Select n subjects maximising pairwise pitch distance."""
    if target_bars is None:
        target_bars = 3
    bar_ticks = _bar_x2_ticks(metre)
    t_start = time.time()
    if verbose:
        print(f"select_diverse: n={n} mode={mode} metre={metre} bars={target_bars}")
    # ── Durations: all patterns per note count ──────────────────
    all_durs = _cached_scored_durations(n_bars=target_bars, bar_ticks=bar_ticks)
    assert len(all_durs) > 0, f"No durations for bars={target_bars} metre={metre}"
    top_durs_by_count: dict[int, list[tuple[int, ...]]] = {}
    for nc, dur_list in all_durs.items():
        if dur_list:
            top_durs_by_count[nc] = dur_list
    # ── Pitch: full validated pool, paired with each duration option ────
    pool: list[tuple[_ScoredPitch, tuple[int, ...]]] = []
    for nc in sorted(top_durs_by_count.keys()):
        if note_counts is not None and nc not in note_counts:
            continue
        dur_options = top_durs_by_count[nc]
        all_pitch = _cached_validated_pitch(
            num_notes=nc,
            tonic_midi=tonic_midi,
            mode=mode,
        )
        if verbose:
            print(f"  {nc}n: {len(all_pitch):,} valid × {len(dur_options)} durations")
        for sp in all_pitch:
            for d_seq in dur_options:
                pool.append((sp, d_seq))
    assert len(pool) > 0, "No valid subjects found"
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
    # ── Stretto filter: cache to disk ──────────────────────────
    cache_name = f"stretto_eval_{mode}_{target_bars}b_{bar_ticks}t.pkl"
    loaded = _load_cache(cache_name)
    stretto_cache: dict[tuple[tuple[int, ...], tuple[int, ...]], tuple[OffsetResult, ...]] = (
        loaded if isinstance(loaded, dict) else {}
    )
    new_entries: int = 0
    # (stretto_score, sp, dur_seq, viable_offsets)
    stretto_filtered: list[tuple[float, _ScoredPitch, tuple[int, ...], tuple[OffsetResult, ...]]] = []
    for sp, dur_seq in candidates:
        cache_key = (sp.degrees, dur_seq)
        if cache_key in stretto_cache:
            viable_offsets = stretto_cache[cache_key]
        else:
            midi_pitches = degrees_to_midi(degrees=sp.degrees, tonic_midi=tonic_midi, mode=mode)
            dur_slots = tuple(DURATION_TICKS[d] for d in dur_seq)
            all_offsets = evaluate_all_offsets(
                midi=midi_pitches,
                dur_slots=dur_slots,
                metre=metre,
            )
            viable_offsets = tuple(r for r in all_offsets if r.viable)
            stretto_cache[cache_key] = viable_offsets
            new_entries += 1
        if len(viable_offsets) >= MIN_STRETTO_OFFSETS:
            stretto_score = sum(r.quality for r in viable_offsets) / len(viable_offsets)
            stretto_filtered.append((stretto_score, sp, dur_seq, viable_offsets))
    if new_entries > 0:
        _save_cache(cache_name, stretto_cache)
    # ── Sort by stretto quality descending ─────────────────────
    stretto_filtered.sort(key=lambda x: x[0], reverse=True)
    if verbose:
        print(
            f"  Pool: {len(pool)} total, {len(stretto_filtered)} with "
            f">= {MIN_STRETTO_OFFSETS} stretto "
            f"(cache_hits={len(candidates) - new_entries})"
        )
    assert len(stretto_filtered) > 0, (
        f"No candidates with >= {MIN_STRETTO_OFFSETS} stretto offsets"
    )
    # ── Greedy max-min distance selection ──────────────────────
    if len(stretto_filtered) <= n:
        picks = list(range(len(stretto_filtered)))
    else:
        picks: list[int] = [0]  # start with best stretto quality
        for _ in range(n - 1):
            best_idx = -1
            best_min_dist = -1
            picked_items = [(stretto_filtered[p][1].degrees, stretto_filtered[p][2]) for p in picks]
            for ci in range(len(stretto_filtered)):
                if ci in picks:
                    continue
                ci_degs = stretto_filtered[ci][1].degrees
                ci_durs = stretto_filtered[ci][2]
                min_dist = min(_subject_distance(ci_degs, ci_durs, pd, pdr)
                               for pd, pdr in picked_items)
                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best_idx = ci
            assert best_idx >= 0
            picks.append(best_idx)
    # ── Build GeneratedSubject for each pick ──────────────────
    results: list[GeneratedSubject] = []
    for pi in picks:
        stretto_sc, sp, best_d_seq, viable_offsets = stretto_filtered[pi]
        subj = _build_subject(
            sp=sp,
            best_durs=best_d_seq,
            tonic_midi=tonic_midi,
            mode=mode,
            metre=metre,
            bar_ticks=bar_ticks,
            final_score=stretto_sc,
            cached_viable_offsets=viable_offsets,
        )
        results.append(subj)
    elapsed = time.time() - t_start
    if verbose:
        for i, subj in enumerate(results):
            print(f"  [{i}] {subj.head_name} {len(subj.scale_indices)}n "
                  f"stretto_score={subj.score:.4f} degrees={subj.scale_indices} "
                  f"stretto={len(subj.stretto_offsets)}")
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
    seed: int = 0,
    verbose: bool = False,
) -> GeneratedSubject:
    """Select a single subject (seed indexes into a diverse set)."""
    subjects = select_diverse_subjects(
        n=max(seed + 1, 6),
        mode=mode,
        metre=metre,
        tonic_midi=tonic_midi,
        target_bars=target_bars,
        pitch_contour=pitch_contour,
        note_counts=note_counts,
        verbose=verbose,
    )
    return subjects[seed % len(subjects)]
