## Task: V7 — Bach sample comparison

Read these files first:
- `viterbi/pipeline.py`
- `viterbi/mtypes.py`
- `viterbi/scale.py`
- `viterbi/costs.py`

### Goal

Test the viterbi solver against real Bach keyboard pieces. Extract the
soprano from Bach's .note files, use it as the leader voice, run the
solver to generate a bass, and compare the solver's bass against Bach's
actual bass. This validates whether the cost function produces musically
reasonable lines.

### Data

The .note files in `viterbi/bachsamples/` are CSV with columns:
`offset, midinote, duration, track, length, bar, beat, notename, lyric`

Each file has 2 tracks. Track numbering varies across files (4/5, 1/2,
3/4, 12/13). Identify soprano vs bass by median pitch: the track with
the higher median is soprano; the lower median is bass.

### Polyphony stripping

Both tracks may contain polyphonic passages (multiple notes sounding
simultaneously). Reduce to monophonic:

- **Soprano:** at each grid position, keep only the HIGHEST sounding pitch.
- **Bass:** at each grid position, keep only the LOWEST sounding pitch.

A note is "sounding" at grid position P if its onset <= P and
onset + duration > P (duration parsed from the fraction string in column 3).

### Grid resolution

Use quaver resolution (0.5 beats). For each piece:

1. Find the first and last note onsets across both tracks.
2. Build a grid from the first onset to the last, stepping by 0.5.
3. At each grid position, sample soprano (highest pitch) and bass
   (lowest pitch).
4. If no note is sounding at a grid position in either voice, carry
   forward the previous pitch (sustain).

### Key detection

Detect the key from the pitch class distribution of ALL notes in the file.
Use the Krumhansl-Schmuckler key-finding algorithm:

Major profile: [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
Minor profile: [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

For each of 24 possible keys (12 major + 12 minor), rotate the
appropriate profile to align with the candidate tonic, then correlate
with the observed pitch-class histogram. The key with the highest
correlation wins. Build a `KeyInfo` from the result.

### Knot placement

Place knots at bar downbeats using Bach's actual bass pitch at each
downbeat. Specifically:

1. Identify every bar boundary (offset where beat == 1.0, or offset is
   an integer corresponding to a bar start — use the `bar` column).
2. At each bar downbeat, take the lowest bass pitch sounding there.
3. These become knots: `Knot(beat=downbeat_offset, midi_pitch=bass_pitch)`.
4. First and last grid positions are always knots.

If a downbeat has no bass note sounding, skip it (no knot there).

### Solver run

For each piece:

1. Parse the .note file.
2. Detect key → `KeyInfo`.
3. Build quaver grid, extract monophonic soprano and bass.
4. Build `LeaderNote` list from soprano grid.
5. Build `Knot` list from bass at bar downbeats.
6. Determine bass range from the actual bass track: `(min_pitch - 2, max_pitch + 2)`.
7. Call `solve_phrase(leader_notes, knots, follower_low, follower_high, key, verbose=False)`.
8. If the piece is longer than ~64 grid positions, split into segments
   of 32 positions (overlapping by 1 at knot boundaries) and solve each
   separately. Concatenate results.

### Comparison metrics

For each grid position where both solver and Bach have a bass pitch,
compute:

1. **Exact match rate** — solver pitch == Bach pitch.
2. **Octave-equivalent match rate** — same pitch class (mod 12).
3. **Interval match rate** — solver-to-soprano interval == Bach-to-soprano
   interval (mod 12).
4. **Step direction agreement** — both move in the same direction from the
   previous position (ascending, descending, or static).
5. **Motion type agreement** — relative motion between voices is the same
   type (contrary, similar, oblique).
6. **Mean absolute error** — average |solver_pitch - bach_pitch| in
   semitones.
7. **Consonance rate** — fraction of strong-beat positions where the
   solver's interval with soprano is consonant.

Report per-piece and aggregate (mean across all pieces).

### Output

Create `viterbi/bach_compare.py` as the main script:
`python -m viterbi.bach_compare`

Output a summary table to stdout:

```
BWV        Key     Grid  Exact%  PC%   Iv%   Dir%  Mot%  MAE   Cons%
--------------------------------------------------------------------
bwv0772    C maj   186   12.3    34.5  45.2  67.8  72.1  3.4   89.2
bwv0832_01 ...
...
--------------------------------------------------------------------
AGGREGATE                 ...
```

Also write the full results to `viterbi/output/bach_results.txt`.

For each piece, additionally write a side-by-side .note-style comparison
to `viterbi/output/compare_<bwv>.txt` showing at each grid position:

```
pos   soprano  bach_bass  vit_bass  match  interval_bach  interval_vit  motion
0.0   C5       C3         C3        =      P8             P8            -
0.5   D5       B2         D3        .      m10            m10           contr
...
```

### Constraints

- Do not modify any existing viterbi module. All new code goes in
  `bach_compare.py`.
- Import from `viterbi.pipeline`, `viterbi.mtypes`, `viterbi.scale`.
- Use only standard library for CSV parsing (csv module).
- Handle missing data gracefully (pieces that fail to solve get a row
  with "FAIL" and continue).
- Print progress: one line per piece as it processes.

### Checkpoint

1. Script runs on all .note files without crashing.
2. Aggregate table printed.
3. Consonance rate on strong beats > 80% (the solver should at minimum
   produce consonant counterpoint).
4. Review 2-3 of the per-piece comparison files. Do the solver's choices
   look like plausible bass lines, or like random walks? Where does the
   solver diverge most from Bach? What musical dimension is responsible?
