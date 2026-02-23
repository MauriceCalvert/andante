# Continue — Subject pool expansion + scoring removal (2026-02-23)

## What happened this session

### 1. SUBPOOL — Widened subject pool for stretto richness

- `MAX_SUBJECT_NOTES` raised from 10 to 16 (was limiting to 8–10 notes)
- Hard contour filter (arch only, discarding 87%) replaced with soft bonus
- Stretto filter raised from `viable_count > 0` to `>= 3`
- CP-SAT generates ~2000 sequences per note count (8–16), total ~6 min one-off
- Result: pool grew from 2,735 to 5,256; stretto-passing candidates from 1/20 to 28

### 2. SUBDUR — Multi-duration pairing + stretto cache

- Each pitch now pairs with top-5 duration patterns (was: single best per note count)
- Fixed dedup key to `(degrees, dur_pattern)` so rhythm variants survive
- Stretto evaluation cached to disk — second run 0.03s (was 542s)
- `DIVERSITY_POOL_CAP` raised from 500 to 2500 to accommodate 5× pool growth
- Result: pool 25,833; stretto-passing 128; minim lock broken (5/6 end on crotchets)

### 3. SUBSCORE — Removed pitch/duration scoring (CC done, not yet tested)

- Deleted `scoring.py` entirely
- Deleted `score_pitch_sequence` and all helpers from `pitch_generator.py`
- Deleted `score_duration_sequence` from `duration_generator.py`
- Removed quality floor from selector
- Ranking signal is now stretto quality: `mean(offset.quality for viable offsets)`
- Contour parameter restored as hard filter (CLI convenience), not bonus
- Removed ~15 scoring constants from `constants.py`

**Status: code changes committed by CC, caches need deletion, needs first run + evaluation.**

### Files changed (cumulative)
- `motifs/subject_gen/constants.py` — MAX_SUBJECT_NOTES=16, MIN_STRETTO_OFFSETS=3, DURATIONS_PER_NOTE_COUNT=5, removed scoring constants
- `motifs/subject_gen/selector.py` — top-K durations, stretto cache, stretto quality ranking, no quality floor
- `motifs/subject_gen/pitch_generator.py` — scoring removed, _ScoredPitch.score=0.0
- `motifs/subject_gen/duration_generator.py` — scoring removed, returns patterns only
- `motifs/subject_gen/scoring.py` — deleted
- `motifs/subject_gen/models.py` — score fields retained (0.0 / stretto quality)

### What needs attention next

1. **Test SUBSCORE.** Delete all `.cache/subject/` files. Run:
   ```
   python -m motifs.subject_generator --bars 2 --verbose
   ```
   First run ~6–10 min (regen caches + stretto eval). Second run < 5s.
   Check: ≥3 contour shapes in top 6, ≥200 stretto-passing candidates,
   stepwise subjects present, all 6 have ≥3 stretto offsets.

2. **Commit SUBSCORE** after successful test.

3. **Listen.** Generate MIDI for the top subjects and listen. The numbers
   look right but the human ear is the real test.

4. **Duration scorer bias** is gone but the duration *enumerator* still
   has hard constraints: last note ≥ crotchet, no isolated semiquavers,
   bar1 density ≥ bar2. These may still exclude valid patterns. Review
   after listening.

5. **Cross-bar rhythmic variety**: bar1 and bar2 can still be identical
   rhythm. Not yet addressed.
