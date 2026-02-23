"""Diversity selection and subject assembly."""
import time
from collections import Counter

from motifs.head_generator import degrees_to_midi
from motifs.stretto_constraints import OffsetResult, evaluate_all_offsets
from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.constants import (
    CONTOUR_PREFERENCE_BONUS,
    DIVERSITY_POOL_CAP,
    DURATION_TICKS,
    DURATIONS_PER_NOTE_COUNT,
    MIN_STRETTO_OFFSETS,
    QUALITY_FLOOR_FRACTION,
    X2_TICKS_PER_WHOLE,
    _bar_x2_ticks,
)
from motifs.subject_gen.contour import _derive_leap_info
from motifs.subject_gen.duration_generator import _cached_scored_durations
from motifs.subject_gen.models import GeneratedSubject, _ScoredPitch
from motifs.subject_gen.pitch_generator import _cached_validated_pitch


def _degree_distance(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    """Hamming distance between two degree sequences (different lengths = max)."""
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
    # ── Durations: top-K per note count ────────────────────────
    all_scored_durs = _cached_scored_durations(n_bars=target_bars, bar_ticks=bar_ticks)
    assert len(all_scored_durs) > 0, f"No durations for bars={target_bars} metre={metre}"
    top_durs_by_count: dict[int, list[tuple[float, tuple[int, ...]]]] = {}
    for nc, scored_list in all_scored_durs.items():
        if scored_list:
            top_durs_by_count[nc] = scored_list[:DURATIONS_PER_NOTE_COUNT]
    # ── Pitch: full validated pool, paired with each duration option ────
    pool: list[tuple[float, _ScoredPitch, tuple[int, ...]]] = []
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
            for d_sc, d_seq in dur_options:
                combined = 0.50 * sp.score + 0.50 * d_sc
                pool.append((combined, sp, d_seq))
    assert len(pool) > 0, "No valid subjects found"
    pool.sort(key=lambda x: x[0], reverse=True)
    # ── Contour filter ─────────────────────────────────────────
    if pitch_contour is not None:
        if verbose:
            contour_dist = Counter(sp.shape for _, sp, _ in pool)
            print(f"  Contour distribution: {dict(contour_dist)}")
        pool = [
            (sc + CONTOUR_PREFERENCE_BONUS, sp, durs) if sp.shape == pitch_contour
            else (sc, sp, durs)
            for sc, sp, durs in pool
        ]
        pool.sort(key=lambda x: x[0], reverse=True)
    # ── Quality floor + dedup (key: degrees + dur_pattern) ─────
    best_score = pool[0][0]
    floor = best_score * QUALITY_FLOOR_FRACTION
    seen: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
    candidates: list[tuple[float, _ScoredPitch, tuple[int, ...]]] = []
    for entry in pool:
        if entry[0] < floor:
            break
        dedup_key = (entry[1].degrees, entry[2])
        if dedup_key not in seen:
            seen.add(dedup_key)
            candidates.append(entry)
            if len(candidates) >= DIVERSITY_POOL_CAP:
                break
    # ── Stretto filter: cache to disk ──────────────────────────
    cache_name = f"stretto_eval_{mode}_{target_bars}b_{bar_ticks}t.pkl"
    loaded = _load_cache(cache_name)
    stretto_cache: dict[tuple[tuple[int, ...], tuple[int, ...]], tuple[OffsetResult, ...]] = (
        loaded if isinstance(loaded, dict) else {}
    )
    new_entries: int = 0
    stretto_filtered: list[tuple[float, _ScoredPitch, tuple[int, ...], tuple[OffsetResult, ...]]] = []
    for entry in candidates:
        sp = entry[1]
        dur_seq = entry[2]
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
            stretto_filtered.append((entry[0], sp, dur_seq, viable_offsets))
    if new_entries > 0:
        _save_cache(cache_name, stretto_cache)
    if verbose:
        print(f"  Pool: {len(pool)} total, {len(stretto_filtered)} with >= {MIN_STRETTO_OFFSETS} stretto "
              f"(best={best_score:.4f}, floor={floor:.4f}, cache_hits={len(candidates)-new_entries})")
    assert len(stretto_filtered) > 0, f"No candidates with >= {MIN_STRETTO_OFFSETS} stretto offsets"
    # ── Greedy max-min distance selection ──────────────────────
    if len(stretto_filtered) <= n:
        picks = list(range(len(stretto_filtered)))
    else:
        picks: list[int] = [0]  # start with best-scoring
        for _ in range(n - 1):
            best_idx = -1
            best_min_dist = -1
            picked_degs = [stretto_filtered[p][1].degrees for p in picks]
            for ci in range(len(stretto_filtered)):
                if ci in picks:
                    continue
                min_dist = min(_degree_distance(stretto_filtered[ci][1].degrees, pd)
                               for pd in picked_degs)
                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best_idx = ci
            assert best_idx >= 0
            picks.append(best_idx)
    # ── Build GeneratedSubject for each pick ──────────────────
    results: list[GeneratedSubject] = []
    for pi in picks:
        combined_sc, sp, best_d_seq, viable_offsets = stretto_filtered[pi]
        subj = _build_subject(
            sp=sp,
            best_durs=best_d_seq,
            tonic_midi=tonic_midi,
            mode=mode,
            metre=metre,
            bar_ticks=bar_ticks,
            final_score=combined_sc,
            cached_viable_offsets=viable_offsets,
        )
        results.append(subj)
    elapsed = time.time() - t_start
    if verbose:
        for i, subj in enumerate(results):
            print(f"  [{i}] {subj.head_name} {len(subj.scale_indices)}n "
                  f"score={subj.score:.4f} degrees={subj.scale_indices} "
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
