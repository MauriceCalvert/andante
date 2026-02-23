# Continue — Subject generator refinement (2026-02-23)

## What happened this session

### 1. Removed low note counts for 2-bar subjects
- Added `MIN_SUBJECT_NOTES = 8` to constants.py
- Duration enumerator now skips sequences below this floor
- Rationale: 5–7 notes in 2 bars of 4/4 produces hymn-tune subjects, not baroque keyboard

### 2. Removed DIVERSITY_POOL_CAP
- The 2500-entry cap was starving diversity — first pitch sequences hogged all slots
- With stretto caching to disk, the cap served no purpose (first run pays once)
- Pool now unlimited; 10.6M candidates evaluated, 1.96M stretto-viable for 8–16n
- Result: genuine diversity across note counts and contour shapes

### 3. Challenged BachStretto.md claims
- Document claimed BWV 846 fugue opens with a half-note C enabling stretto
- Actually that's the prelude; the fugue subject is pure quavers from beat 2
- "Sustained opening enables stretto" is not a general rule — BWV 846 disproves it
- The document is unreliable on this point

### 4. Removed minims from duration vocabulary
- `DURATION_TICKS` reduced to `(1, 2, 4)` — semiquaver, quaver, crotchet
- Subjects now use mixed quaver/semiquaver rhythms naturally

### 5. Lowered RANGE_LO from 4 to 3
- Admits BWV 846-style subjects spanning only a 4th
- Still prevents aimless noodling (minimum span = 3 degrees = a 4th)

### 6. Fixed MIN_STEP_FRACTION enforcement
- Was hardcoded to 50% via `ceil(n_iv / 2)` in cpsat_generator.py
- Constant `MIN_STEP_FRACTION = 0.65` existed but was never read
- Now uses `math.ceil(n_iv * MIN_STEP_FRACTION)` — 6 of 9 intervals must be steps for 10n

### 7. Improved diversity selection metric
- Was: Hamming distance on pitch degrees only (rhythm invisible)
- Now: Hamming distance on `(degrees + durations)` concatenated
- Result: 6 picks show genuinely different rhythmic profiles

### 8. Added rhythm display to writers output
- Each subject now prints `Rhythm:` line with standard shorthand (16/8/4/2/1)

### 9. Forbid semitone clashes in stretto
- Minor 2nd (1 semitone) and major 7th (11 semitones) now fatal on any beat
- Previously only tritones were fatal on weak beats; semitone clashes just added cost
- A semitone clash at the end of overlap sounds terrible regardless of beat strength

### 10. Stretto follower onset alignment rules
- Bug: follower notes could attack between leader onsets and sustain across them
- New rules in `evaluate_offset`:
  1. First follower onset must land on a leader onset
  2. Later follower onsets may fall between leader onsets but must finish on/before the next leader onset
- Stretto caches cleared; next run rebuilds with stricter evaluation

### Files changed
- `motifs/subject_gen/constants.py` — MIN_SUBJECT_NOTES=8, DURATION_TICKS=(1,2,4), DURATION_NAMES trimmed, RANGE_LO=3, MIN_STEP_FRACTION=0.65, DIVERSITY_POOL_CAP removed
- `motifs/subject_gen/cpsat_generator.py` — math.ceil(n_iv * MIN_STEP_FRACTION)
- `motifs/subject_gen/selector.py` — cap removed, _subject_distance replaces _degree_distance (pitch+rhythm Hamming)
- `motifs/subject_gen/duration_generator.py` — MIN_SUBJECT_NOTES import and floor check
- `motifs/stretto_constraints.py` — follower onset alignment rules, semitone clashes fatal
- `motifs/subject_generator.py` — added --notes CLI parameter
- `motifs/writers.py` — rhythm display line

### Cache state
- All `.cache/subject/*.pkl` deleted — stretto caches must rebuild
- First run will be slow (stretto eval for full pool); subsequent runs instant

### What needs attention next

1. **Test stretto onset rules.** Run `writers.py -v --bars 2 --notes 12` and verify .note files — no follower notes should straddle leader onsets.

2. **Listen.** Generate MIDI and listen. Numbers look right but the ear is the real test.

3. **Full note-count run.** After verifying 12n, run without --notes restriction. First run will be very slow (rebuilding stretto cache for all note counts). Expect significantly fewer stretto-viable candidates due to stricter onset alignment.

4. **Selection caching.** If full-pool dedup/selection is still slow (~58s) after stretto cache is warm, cache the `select_diverse_subjects` output itself.

5. **Cross-bar rhythmic variety**: bar1 and bar2 can still have identical rhythm. Not yet addressed.
