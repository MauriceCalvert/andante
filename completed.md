# Completed

## SUBDUR — Multi-duration pairing + stretto cache (2026-02-23)

Introduced rhythmic variety by pairing each pitch with the top-5 duration patterns
per note count, and cached stretto evaluation results to disk.

- `constants.py`: added `DURATIONS_PER_NOTE_COUNT = 5`
- `selector.py`:
  - Imports: added `OffsetResult`, `_load_cache`, `_save_cache`, `DURATIONS_PER_NOTE_COUNT`
  - `top_durs_by_count` replaces `best_dur_by_count` (top-K list, not single best)
  - Pool loop: inner loop over K duration options per pitch
  - Dedup key changed to `(degrees, dur_pattern)` — same pitch+different rhythm no longer collapsed
  - Stretto cache: `stretto_eval_{mode}_{bars}b_{ticks}t.pkl` loaded before filter loop,
    saved after if any new entries; maps `(degrees, dur_pattern)` → `tuple[OffsetResult, ...]`
  - `stretto_filtered` now 4-tuple including `viable_offsets`
  - `_build_subject`: accepts `cached_viable_offsets` param; skips `evaluate_all_offsets` when provided
  - Picks loop: passes cached offsets to `_build_subject`


## SUBPOOL — Widen subject pool for stretto richness (2026-02-23)

Extended subject note range to 16 and raised stretto minimum to 3 viable offsets.

- `constants.py`: `MAX_SUBJECT_NOTES` 10→16; added `MIN_STRETTO_OFFSETS=3`,
  `CONTOUR_PREFERENCE_BONUS=0.05`
- `selector.py`: contour filter replaced with +0.05 scoring bonus; stretto
  threshold raised from >0 to >=3; verbose label updated
- Deleted stale `.cache/subject/` pkl files (8n, 9n pitch; 2-bar duration)
