# Continue — Enable semiquavers in subject_generator (2026-02-19)

## What happened this session

Diagnosed why subject_generator never produces stretti: semiquavers didn't
exist in the duration vocabulary. The `DURATION_TICKS = (2, 4, 8)` with
`X2_TICKS_PER_WHOLE = 16` meant the smallest note was a quaver (tick=2),
not a semiquaver (tick=1). The names were also shifted — 'semiquaver'
labelled what was actually a quaver.

### Changes made to `motifs/subject_generator.py`

1. **Duration vocabulary fixed:**
   - `DURATION_TICKS = (1, 2, 4, 8)` — semiquaver, quaver, crotchet, minim
   - `DURATION_NAMES` corrected to match
   - Added `SEMIQUAVER_DI = 0`

2. **Bar-fill constraints updated:**
   - `MAX_NOTES_PER_BAR`: 6 → 8
   - `MIN_LAST_DUR_TICKS`: 8 → 4 (crotchet ending, was forcing minim)
   - Added `MAX_SUBJECT_NOTES = 11` (caps pitch enumeration; 12n takes 16s,
     11n takes 8s — acceptable)
   - Added `MIN_SEMIQUAVER_GROUP = 2` (no isolated semiquavers)

3. **Isolated semiquaver filter:** New `_has_isolated_semiquaver()` function.
   Applied as post-filter on bar fills inside `enumerate_durations`. Reduces
   bar fills from 1224 to 372.

4. **Note count cap:** `MAX_SUBJECT_NOTES` enforced in `enumerate_durations`.

5. **Head/tail acceleration direction fixed:**
   - Enumeration filter was `head_mean > tail_mean` (rejected acceleration).
     Changed to `head_mean < tail_mean` (rejects deceleration — baroque
     subjects accelerate, head notes longer than tail).
   - `score_duration_sequence` contrast scorer: ratio flipped to
     `head_mean / tail_mean`, target changed from 2.5 to 2.0 with
     width 0.8. Now rewards head being ~2x slower than tail.

### Current state

Duration enumeration produces 3398 sequences (up from 251), of which 2884
contain semiquavers. Semiquaver durations score competitively (top ~0.96).
Thousands of semiquaver candidates survive pairing and melodic validation.

However, seed 0 still selects a 6-note non-semiquaver subject — the combined
pitch+pairing+stretto scoring favours short subjects with excellent contour
fit. A multi-seed test (`test_sq_seeds.py`) was written but not yet run.

### Test scripts left in andante root (delete after use)

- `test_pitch_timing.py` — times pitch enumeration by note count
- `test_dur_timing.py` — tests duration enumeration with semiquavers
- `test_sq_diag.py` — checks semiquaver duration generation and scoring
- `test_sq_candidates.py` — checks semiquaver candidates through pipeline
- `test_sq_seeds.py` — multi-seed test, not yet run

### What needs attention next

1. **Run `python test_sq_seeds.py`** to see if any seeds produce semiquaver
   subjects. If none do, the scoring weights need adjustment — likely the
   pitch contour score (50% of pitch scoring) dominates and short subjects
   win on contour fit alone.

2. **Possible fixes if no seeds produce semiquavers:**
   - Add a note-count bonus to the combined score (longer subjects with
     more rhythmic variety score higher)
   - Reduce pitch contour weight relative to duration contrast
   - Add a direct semiquaver bonus in `score_duration_sequence`
   - Tighten the contour band for short sequences so fewer trivial 5-6n
     subjects survive

3. **Stretto yield** remains low from the previous session (strict interval
   rejection). With semiquavers in the vocabulary, subjects now have more
   note onsets and finer-grained offsets, which should improve stretto
   viability. But this hasn't been verified yet.

4. **Downstream impact:** once subjects contain semiquavers, check that
   `thematic_renderer.py`, `imitation.py`, and the answer/CS generators
   handle the finer durations correctly. The duration system uses Fractions
   internally and 1/16 is in VALID_DURATIONS, so this should be safe.
