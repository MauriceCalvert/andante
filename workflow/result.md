# Result: SUBDUR — Multi-duration pairing + stretto cache

## Changes

### `motifs/subject_gen/constants.py`
- Added `DURATIONS_PER_NOTE_COUNT: int = 5`

### `motifs/subject_gen/selector.py`
1. **Imports**: `OffsetResult` from `stretto_constraints`; `_load_cache`, `_save_cache` from `cache`; `DURATIONS_PER_NOTE_COUNT` from `constants`
2. **Top-K durations**: `top_durs_by_count` keeps `scored_list[:DURATIONS_PER_NOTE_COUNT]` per note count
3. **Pool loop**: inner loop over K duration options — each pitch × each duration = one pool entry
4. **Dedup key**: `(sp.degrees, dur_seq)` — same pitch + different rhythm no longer collapsed
5. **Stretto cache**: loaded before filter loop as `dict[(degrees, dur_pattern), tuple[OffsetResult, ...]]`. On cache hit: use stored offsets. On miss: evaluate, store. Save if new entries added. Cache file: `stretto_eval_{mode}_{target_bars}b_{bar_ticks}t.pkl`
6. **`stretto_filtered`**: 4-tuple `(score, sp, dur_seq, viable_offsets)`
7. **`_build_subject`**: `cached_viable_offsets: tuple[OffsetResult, ...] | None = None` parameter — when provided, skips `evaluate_all_offsets`
8. **Picks loop**: passes `viable_offsets` from `stretto_filtered` to `_build_subject`

## Chaz Checkpoint

1. ✅ `DURATIONS_PER_NOTE_COUNT = 5` in `constants.py`
2. ✅ Dedup key is `(degrees, dur_pattern)` — line `dedup_key = (entry[1].degrees, entry[2])`
3. ✅ Cache file loaded before loop, saved after if `new_entries > 0`; second run will have all keys cached → no `evaluate_all_offsets` calls → fast
4. ✅ `_build_subject` uses `cached_viable_offsets` when provided, no re-evaluation at pick time

## Notes

- The CP-SAT pitch caches are untouched.
- Delete `stretto_eval_*.pkl` if the stretto logic changes; pitch caches remain valid.
- Verbose output now shows `cache_hits` count alongside pool/stretto stats.
