## Subject Generation — Current State

### Architecture

Two parallel contour systems, same machinery:

**Pitch contours** — waypoints `(X, Y)` where X is position 0..1, Y is scale degree
displacement. Origin `(0, 0)` implicit. Linear interpolation. Scored by RMS fit (σ=2.5).

Six contours in three mirror pairs:

```
'arch':     [(0.35, 6),  (1.0, -7)]   ↔  'valley':  [(0.2, -8),  (1.0, -2)]
'swoop':    [(0.2, 8),   (1.0, -8)]   ↔  'dip':     [(0.2, -8),  (1.0, 8)]
'cascade':  [(0.1, 2),   (1.0, -10)]  ↔  'ascent':  [(0.1, -2),  (1.0, 10)]
```

**Rhythm contours** — waypoints `(X, Y)` where Y is speed level 0.0=fast, 1.0=slow.
Same origin convention. Scored by RMS fit (σ=0.3). Only 2 viable with 3-value vocabulary:

```
'motoric':    [(0.4, 0.0), (1.0, 1.0)]   # fast head, broadening tail
'busy_brake': [(0.7, 0.1), (1.0, 0.7)]   # stays fast, late brake
```

Duration vocabulary: semiquaver(2), quaver(4), crotchet(8) in x2 ticks.

### Invertibility

Generator is now symmetric — no directional bias. Three former hard constraints
removed:
- Global descent (`pitch >= 0` rejection) — removed
- Peak in head (`peak_pos > HEAD_LEN`) — removed
- Negative-only finals — `ALLOWED_FINALS` expanded to `{0, ±2, ±3, ±4, ±5, ±7}`

Direction comes from contour scoring. Each interval sequence is scored against
both its original contour and the mirror contour (negated pitches vs negated
waypoints). Invertibility score = `min(original_fit, mirror_fit)`. Subjects
that work well both ways up rank highest.

Enumeration: ~3.2M interval sequences (was ~1.2M), 10.5s. Acceptable.

### Stretto

`count_stretto_offsets(ivs, durs, bar_ticks=16)` in `subject_scorer.py` tests
two configurations at each internal note onset:
- **Self-vs-self**: subject overlapping a time-shifted copy of itself
- **Self-vs-inversion**: subject overlapping its negated form

Consonance rules (degree intervals mod 7):
- Strong beats (tick % bar_ticks in {0, half_bar}): {0, 2, 5} — unison, 3rd, 6th.
  Perfect 5th excluded (inverts to dissonant 4th in two-voice texture).
- Weak beats: {0, 1, 2, 4, 5, 6} — all but tritone. Max 1 weak dissonance.
- No consecutive parallel unisons or 5ths at onset points.
- Minimum 3 overlap onset points.

Stretto score = `min((self_count + mirror_count) / 4, 1.0)`. Weighted 50% in
joint scoring (effectively 15% of total combined score).

Results from render pipeline (12 subjects, 6 contours × 2 rhythms):
- 10/12 have stretto offsets
- 4/12 have both self AND mirror stretto
- Best: cascade[2] and ascent[2] with self=2, mirror=1 (total=3)

### Pipeline

1. Enumerate intervals (recursive, ~3.2M sequences, 10.5s)
2. Enumerate durations (~3.9K sequences, instant)
3. Score intervals per pitch contour with invertibility (NumPy vectorised, ~3s each)
4. Score durations per rhythm contour (Python loop, instant)
5. Pair best melody × best rhythm per combo
6. Joint-score with stretto evaluation
7. Render to MIDI

### Constraints

- 9 notes, 8 intervals, scale degrees ±5
- Pitch range: span 4–11 degrees, cumulative −7..+7
- Allowed finals: {0, ±2, ±3, ±4, ±5, ±7}
- ≥50% steps, ≤4 large leaps, ≤1 repeat, ≤5 same-direction run
- ≤3 same pitch frequency
- Head (4 notes) faster than tail (5 notes) on average
- Last note ≥ crotchet
- ≥2 distinct durations

### Files

- `subject_generator.py` — enumeration constants, contour definitions, mirror pairs,
  interpolation, pitch/rhythm scoring helpers, exhaustive enumeration (symmetric)
- `subject_pipeline.py` — interval/duration/joint scoring incl. invertibility + stretto,
  rendering, MIDI output. Single entry point: `python subject_pipeline.py`

### Next

Listen to `subjects_by_contour.mid`. Evaluate whether:
1. Subjects with high stretto counts sound like viable fugue material
2. Mirror-pair subjects (arch/valley, swoop/dip, cascade/ascent) are
   recognisably related when heard back-to-back
3. Rhythmic variety is sufficient with only 2 rhythm contours
4. Any subjects sound like scale exercises or random walks

Then: integrate into the main Andante pipeline (`motifs/subject_generator.py`),
replacing the head+tail construction with contour-ranked subjects.
