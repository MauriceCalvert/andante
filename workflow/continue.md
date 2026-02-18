## Subject Generation — Current State

### Architecture

Two parallel contour systems, same machinery:

**Pitch contours** — waypoints `(X, Y)` where X is position 0..1, Y is scale degree
displacement. Origin `(0, 0)` implicit. Linear interpolation. Scored by RMS fit (σ=2.5).

```
'arch':     [(0.35, 6),  (1.0, -7)]
'cascade':  [(0.1, 2),   (1.0, -10)]
'swoop':    [(0.2, 8),   (1.0, -8)]
'valley':   [(0.2, -8),  (1.0, -2)]
```

**Rhythm contours** — waypoints `(X, Y)` where Y is speed level 0.0=fast, 1.0=slow.
Same origin convention. Scored by RMS fit (σ=0.3). Only 2 viable with 3-value vocabulary:

```
'motoric':    [(0.4, 0.0), (1.0, 1.0)]   # fast head, broadening tail
'busy_brake': [(0.7, 0.1), (1.0, 0.7)]   # stays fast, late brake
```

Duration vocabulary: semiquaver(2), quaver(4), crotchet(8) in x2 ticks.
More rhythm contours failed — 3 duration values can't distinguish finer shapes.

### Pipeline

1. Enumerate intervals (recursive, ~1.2M sequences, 10s)
2. Enumerate durations (~3.9K sequences, instant)
3. Score intervals per pitch contour (NumPy vectorised, ~1s each)
4. Score durations per rhythm contour (Python loop, instant)
5. Pair best melody × best rhythm per combo
6. Render to MIDI

### Constraints

- 9 notes, 8 intervals, scale degrees ±5
- Pitch range: span 4–11 degrees, cumulative −7..+7
- Global descent: final pitch < 0
- Allowed finals: {0, −2, −3, −4, −5, −7}
- Peak in first half
- ≥50% steps, ≤4 large leaps, ≤1 repeat, ≤5 same-direction run
- ≤3 same pitch frequency
- Head (4 notes) faster than tail (5 notes) on average
- Last note ≥ crotchet
- ≥2 distinct durations

### Files

- `subject_contours.py` — both contour families, interpolation, scoring
- `subject_generator.py` — exhaustive enumeration with pruning
- `subject_scorer.py` — interval/duration/joint scoring (NumPy vectorised)
- `subject_render.py` — pipeline, pairing, MIDI output

### Next: Invertibility

A baroque subject's value multiplies if it works under inversion (negate all
intervals). Bach uses inversion constantly — it doubles the available thematic
material for free.

**What breaks under inversion now:**

1. **Global descent** — `pitch[-1] < 0` becomes `pitch[-1] > 0`. Inverted subject
   ascends. The generator rejects this.

2. **Peak in head** — becomes trough in head. The constraint `peak_pos ≤ HEAD_LEN`
   is wrong for the inverted form; what matters is `trough_pos ≤ HEAD_LEN`.

3. **Allowed finals** — `{0, −2, −3, −4, −5, −7}` are below the start. Inverted
   finals are `{0, 2, 3, 4, 5, 7}` — above the start. Different set, same logic.

4. **Pitch contours** — arch `[(0.35, 6), (1.0, -7)]` inverts to
   `[(0.35, -6), (1.0, 7)]` which is valley. Contours come in natural pairs:
   arch ↔ valley, swoop ↔ dip, cascade ↔ ascent.

5. **Contour scoring** — a subject that fits arch well will have its inversion
   fit the negated-Y contour. Scoring the inverted form is free — just negate
   the targets.

**Design question: when to check invertibility?**

Option A: **Filter at enumeration.** Generate only subjects whose inversion also
passes all constraints. This halves (or worse) the search space but guarantees
every subject is invertible.

Option B: **Score after enumeration.** Generate normally, then score each subject
twice — original fit to its contour, inverted fit to the mirror contour. Rank by
the minimum of the two scores. Subjects that work well both ways float to the top.

Option B is better. It doesn't discard subjects that are excellent in original
form but mediocre inverted — it just ranks them lower. The contour scoring
machinery already exists; scoring the inverted form is just `score_pitch_fit(
tuple(-iv for iv in ivs), mirror_waypoints)`.

**What "mirror_waypoints" means:** negate all Y values. `arch → [(0.35, -6), (1.0, 7)]`.
The X positions stay the same — the shape flips vertically.

**Constraint relaxation needed:** the generator currently enforces global descent
and peak-in-head as hard constraints. For invertibility, these need to become
soft (scoring dimensions) or the generator needs a mode flag. The cleanest
approach: remove directional asymmetry from the generator entirely. Let
contour scoring handle direction. The generator enforces only:
- Pitch range limits
- Step/leap balance
- Run limits
- Allowed finals (both positive and negative sets)
- No repeated final interval

This makes the generator symmetric. Direction comes from contour selection,
not from enumeration constraints. The search space roughly doubles (ascending
subjects are now legal) but enumeration is already fast (10s).
