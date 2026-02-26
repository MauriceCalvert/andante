# Continue — Subject Generator: Diversity & Stretto Overhaul

## Status: all changes made, tested, working

## What was done this session

### 1. Aesthetic floor filter (selector.py, constants.py)
MIN_AESTHETIC_SCORE (7.0, now 8.0) was defined but never applied. Added
filter after scoring/sorting, before pitch dedup and diversity selection.
Prevents weak subjects from being pulled in by the max-min distance loop.

### 2. Head interval features (scoring.py, constants.py)
Diversity metric used only aggregate statistics (range, leap fraction,
climax position…). Subjects with identical openings looked distant
because tails differed. Fix: appended first 3 intervals (normalised by
DEGREES_PER_OCTAVE, scaled by HEAD_IV_FEATURE_SCALE=2.0) to the feature
vector. Subjects with similar Kopfmotiv now cluster in feature space.

### 3. Tail interval features (scoring.py, constants.py)
Mirror problem: subjects sharing the last 10 of 12 degrees survived
because heads differed. Added last 3 intervals to feature vector,
same scaling. Replaced 3 redundant aggregate features (f_leap_fraction,
f_max_interval, f_head_character) to keep vector at 13D.

### 4. HEAD_IV_FEATURE_WINDOW decoupled from HEAD_SIZE (constants.py, scoring.py)
HEAD_LENGTHS expanded to (3,4,5) made HEAD_SIZE=5, widening the feature
window to 4 intervals and diluting per-interval weight. Fix: new constant
HEAD_IV_FEATURE_WINDOW=3 controls feature extraction independently of
HEAD_SIZE. Feature vector stays 13D (7 aggregate + 3 head + 3 tail).

### 5. Stretto offset cap: bar-1 only (stretto_constraints.py, stretto_gpu.py)
Replaced MAX_OFFSET_FRACTION=0.5 with `onset >= bar_slots` (strict <).
Offsets at or past bar 2 downbeat no longer count. Musically grounded
limit that generalises across metres. MAX_OFFSET_FRACTION removed entirely.

### 6. Stretto consonance relaxation (stretto_constraints.py, stretto_gpu.py)
Two changes to increase viable stretto offsets:
- **P4 on strong beats**: now consonant. Uses CONSONANT_INTERVALS instead
  of CONSONANT_INTERVALS_ABOVE_BASS. In stretto, leader isn't always bass.
- **Weak-beat semitone/minor-9th**: no longer fatal. Incurs fixed penalty
  (_SEMITONE_COST=4) instead of immediate rejection. Only tritone remains
  fatal on weak beats.
Both CPU and GPU paths updated in parallel.

### 7. Minim duration (constants.py, rhythm_cells.py)
Added 8-tick minim to DURATION_TICKS/DURATION_NAMES. Added scale factor 4
to SCALES (was (1,2), now (1,2,4)). Enables minim via 2-tick cells × 4.
12n duration generation time increased from 6s to 46s due to 3× scale
combinations. Duration cache key unchanged — must delete cache manually.

### 8. Minimum diversity distance (selector.py, constants.py)
Greedy diversity selector previously had early-out bypass when
`len(scored) <= n` — returned entire pool with no filtering. Removed
bypass; loop always runs. Added MIN_DIVERSITY_DISTANCE=1.0: candidates
closer than this in feature space to any already-picked subject are
rejected. Prevents near-duplicates when pool is small.

### 9. Batch output cap (generate_subjects.py)
Script previously wrapped `j % len(subjects)` to fill requested count,
silently duplicating. Now warns "only N candidates found" and outputs
only distinct subjects. Skips unpopulated indices in output loop.

## Current constants state
- MIN_AESTHETIC_SCORE: 8.0
- MIN_STRETTO_OFFSETS: 2
- MIN_DIVERSITY_DISTANCE: 1.0
- HEAD_IV_FEATURE_SCALE: 2.0
- HEAD_IV_FEATURE_WINDOW: 3
- HEAD_LENGTHS: (3, 4, 5)
- SCALES: (1, 2, 4)
- DURATION_TICKS: (1, 2, 3, 4, 6, 8)

## Files modified this session
- `motifs/subject_gen/constants.py` — MIN_AESTHETIC_SCORE, HEAD_IV_FEATURE_SCALE, HEAD_IV_FEATURE_WINDOW, MIN_DIVERSITY_DISTANCE, DURATION_TICKS, DURATION_NAMES, HEAD_IV_FEATURE_SCALE
- `motifs/subject_gen/scoring.py` — subject_features: replaced 3 redundant features with head+tail intervals, decoupled from HEAD_SIZE
- `motifs/subject_gen/selector.py` — aesthetic floor filter, diversity distance threshold, removed early-out bypass
- `motifs/subject_gen/rhythm_cells.py` — SCALES: (1,2,4)
- `motifs/stretto_constraints.py` — bar-1 cap, P4 consonant on strong beats, semitone cost penalty, removed MAX_OFFSET_FRACTION
- `motifs/subject_gen/stretto_gpu.py` — same changes mirrored for GPU path
- `scripts/generate_subjects.py` — batch cap with warning, no modular wrap

## Caches to delete before next run
All stretto and duration caches in `.cache/subject/` are stale after
these changes. Delete `stretto_eval_*` and `cell_dur_v6_*` files.
