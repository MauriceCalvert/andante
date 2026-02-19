# Result: INV-STRETTO — Invertible subjects with stretto scoring

## Changes Made

### 1. subject_generator.py — symmetric enumeration

- Removed `if pitch >= 0: return` (global descent constraint)
- Removed `if peak_pos > HEAD_LEN: return` (peak-in-head constraint)
- Expanded `ALLOWED_FINALS` from `{0, -2, -3, -4, -5, -7}` to `{0, 2, 3, 4, 5, 7, -2, -3, -4, -5, -7}`

The generator now enumerates both ascending and descending subjects. Direction
preference moves to contour scoring (arch still favours rise-then-fall).

### 2. subject_contours.py — mirror contours

- Added two mirror pitch contours:
  - `dip`: `[(0.2, -8), (1.0, 8)]` (mirror of swoop)
  - `ascent`: `[(0.1, -2), (1.0, 10)]` (mirror of cascade)
- Added `MIRROR_PAIRS` dict mapping each contour to its mirror
- Added `mirror_waypoints(waypoints)` helper that negates all Y values

### 3. subject_scorer.py — invertibility + stretto

**3a. Invertibility in interval scoring:**
- `score_intervals` gains optional `mirror_waypoints` parameter
- When provided, scores both original pitches against original contour AND
  inverted pitches (`-pitches`) against mirror contour, uses `np.minimum`
- When `mirror_waypoints` is None, behaviour unchanged

**3b. Stretto scoring:**
- New `count_stretto_offsets(ivs, durs, bar_ticks=16)` function
- Builds onset timeline and degree sequences (original + inverted)
- Tests each internal note onset as a candidate stretto offset
- Checks strong-beat consonances ({0,2,5} mod 7), weak-beat ({0,1,2,4,5,6}),
  rejects on strong-beat dissonance, >1 weak-beat dissonance, consecutive
  parallel unisons/5ths, or <3 overlap onset points
- Returns `(self_count, mirror_count)`

**3c. Rebalanced joint weights:**
- `score_joint` now calls `count_stretto_offsets` and computes
  `s_stretto = min(total / 4.0, 1.0)`
- New weights: `0.30 * s_leap_dur + 0.20 * s_pre_leap + 0.50 * s_stretto`
- Stretto is 50% of joint, joint is 30% of combined = 15% of total score

**3d. Display + diagnostic:**
- `display_subject` prints stretto counts (self, mirror, total) per subject
- `run()` prints stretto hit-rate diagnostic: fraction of 10K candidates
  with any stretto offset

### 4. subject_render.py — wiring

- Imports `MIRROR_PAIRS` from `subject_contours`
- Per-contour scoring loop looks up mirror contour via `MIRROR_PAIRS[pname]`,
  passes both `contour_waypoints` and `mirror_waypoints` to `score_intervals`
- Now renders 6 pitch x 2 rhythm = 12 subjects (was 4x2=8)
- Stretto counts appear automatically via updated `display_subject`

## Verification Checklist

Run `python subject_render.py` and verify:

1. Enumeration count roughly doubled (~2M+ interval sequences)
2. Top-ranked subjects per contour have invertibility score > 0.5
3. At least some subjects have stretto offsets > 0
4. Subjects with both self and mirror stretto appear in top ranks
5. Listen to MIDI: subjects sound like viable fugue subjects
6. Stretto hit-rate diagnostic: >= 10% of joint candidates have any offset
