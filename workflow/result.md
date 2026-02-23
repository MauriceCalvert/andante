## SUBSCORE — Result

### Chaz checkpoint

1. **`scoring.py` deleted** — confirmed, file is gone.

2. **`score_pitch_sequence` and `score_duration_sequence` gone** — confirmed.
   - `pitch_generator.py` contains no scoring functions; only `_degrees_to_ivs` and `_cached_validated_pitch`.
   - `duration_generator.py` contains no `score_duration_sequence`; `_cached_scored_durations` returns `dict[int, list[tuple[int, ...]]]` (patterns only).

3. **No quality floor in selector** — confirmed.
   - The `QUALITY_FLOOR_FRACTION` constant is deleted from `constants.py`.
   - `selector.py` has no floor logic; all deduped candidates proceed to stretto evaluation, bounded only by `DIVERSITY_POOL_CAP=2500`.

4. **Stretto quality is the ranking signal** — confirmed.
   - After stretto filter, `stretto_score = sum(r.quality for r in viable_offsets) / len(viable_offsets)`.
   - `stretto_filtered` is sorted descending by `stretto_score`.
   - Greedy diversity selection starts at index 0 (best stretto quality).
   - `final_score=stretto_sc` is passed to `_build_subject`, so `GeneratedSubject.score` carries stretto quality.

5. **Cache files deleted** — no `.pkl` files found in `.cache/`; regeneration will happen on first run.

6. **`pitch_contour` as hard filter** — confirmed. When provided, `pool` is filtered to matching shape only; no bonus, just exclusion.

7. **Unchanged per constraints** — `_build_subject` signature unchanged (beyond `final_score` semantics); `select_subject`, `_degree_distance`, `GeneratedSubject.score`, `_ScoredPitch.score` all retained.

---

### Bob checkpoint

User must run:
```
python -m motifs.subject_generator --bars 2 --verbose
```

Bob should report:
1. How many candidates pass ≥3 stretto? (expect >128)
2. What contour shapes appear in the 6 selected? (expect variety)
3. What note counts appear? Any even-quaver subjects?
4. Do any subjects have the stepwise, running character of a Bach invention?
