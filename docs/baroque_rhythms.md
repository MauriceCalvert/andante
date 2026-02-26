# Baroque Rhythm Cells

## Purpose

Replace the current bar-fill duration enumerator with a musically principled
rhythm generator.  Rhythms are built by concatenating named cells drawn from
baroque practice, subject to a transition table that encodes which
successions sound right and which don't.

## Cells

Each cell has a name, a pattern of relative durations (S = short, L = long),
a note count, and a metric character.

Duration values are expressed in x2-ticks (semiquaver = 1, quaver = 2,
crotchet = 4).

| Cell      | Pattern | Notes | Ticks         | Metric character                    |
|-----------|---------|-------|---------------|-------------------------------------|
| Iamb      | S-L     | 2     | 1-2 or 2-4   | Short-long. Upbeat when off-beat, lombardic snap when on-beat. |
| Trochee   | L-S     | 2     | 2-1 or 4-2   | Long-short. Settling, declarative.  |
| Dotted    | L.-S    | 2     | 3-1           | Dotted quaver + semiquaver. Ceremonial weight. |
| Dactyl    | L-S-S   | 3     | 2-1-1 or 4-2-2 | Strong opening, tumbling forward.  |
| Anapaest  | S-S-L   | 3     | 1-1-2 or 2-2-4 | Building momentum into arrival.    |
| Tirata    | S-S-S-S | 4     | 1-1-1-1       | Equal-value run. Scalar energy, no internal accent. |

### Design decisions

- **Iamb/lombardic collapsed.**  Both are S-L.  The distinction is metric
  placement: off-beat = iamb (anacrusis), on-beat = lombardic (snap).
  The generator emits a single "iamb" cell; beat position determines
  the musical character.  The transition table entry "iamb → iamb = W"
  covers both the case of two anacrusis gestures (predictable) and the
  implicit lombardic repetition (stutter).

- **Tirata fixed at 4 notes.**  Shorter equal-note runs (2–3 semiquavers)
  are the short components of other cells.  Longer runs (5+) are a
  tirata + another cell.

- **4/4 time only.**  Hemiola is out of scope.

- **Rests are out of scope.**  All cells produce sounding notes.

## Partitions

A rhythm for N notes is a sequence of cells whose note counts sum to N.
The available note counts are 2, 3, and 4.

For 12 notes, the partitions of {2, 3, 4} that sum to 12:

| Partition                            | Cell slots | Arrangements (unweighted) |
|--------------------------------------|------------|---------------------------|
| 6 × 2-note                          | 6          | 3^6 = 729                 |
| 3 × 2-note + 2 × 3-note            | 5          | C(5,2) × 3^3 × 2^2 = 1,080 |
| 2 × 2-note + 1 × 3-note + 1 × 4-note | 4        | 4!/2! × 3^2 × 2 × 1 = 216 |
| 1 × 2-note + 1 × 4-note + 2 × 3-note | 4        | 4!/2! × 3 × 1 × 2^2 = 144 |
| 4 × 3-note                          | 4          | 2^4 = 16                  |
| 3 × 4-note                          | 3          | 1^3 = 1                   |
| 1 × 2-note + 2 × 4-note + 1 × 3-note | 4        | 4!/2! × 3 × 1 × 2 = 72   |
| 3 × 4-note                          | 3          | 1                         |

(3 two-note cells: iamb, trochee, dotted.  2 three-note cells: dactyl,
anapaest.  1 four-note cell: tirata.)

Unconstrained total for 12 notes: approximately 2,200.
After transition filtering: roughly 800–1,200.

## Transition Table

Each entry is one of:

- **Y** — good succession, no penalty
- **W** — acceptable, weight penalty (multiplier 0.5)
- **N** — forbidden

| From ↓ / To → | Iamb | Trochee | Dotted | Dactyl | Anapaest | Tirata |
|----------------|------|---------|--------|--------|----------|--------|
| **Iamb**       | W    | Y       | Y      | Y      | W        | Y      |
| **Trochee**    | Y    | W       | W      | N      | Y        | Y      |
| **Dotted**     | Y    | W       | N      | W      | Y        | Y      |
| **Dactyl**     | Y    | W       | Y      | W      | Y        | Y      |
| **Anapaest**   | Y    | W       | Y      | Y      | N        | W      |
| **Tirata**     | Y    | Y       | Y      | Y      | Y        | N      |

### Rationale

- **Trochee → Dactyl = N**: L-S then L-S-S.  Two long notes one short
  apart; metric weight collision.
- **Dotted → Dotted = N**: ceremonial weight becomes mechanical if
  repeated.
- **Anapaest → Anapaest = N**: S-S-L then S-S-L.  Two longs meet at the
  junction.
- **Tirata → Tirata = N**: 8 consecutive semiquavers is a scale run, not
  a rhythmic figure.
- **Iamb → Iamb = W**: S-L S-L is metrically fine but predictable.
- **Trochee → Trochee = W**: L-S L-S same reasoning.
- **Anapaest → Tirata = W**: the long arrival of the anapaest is
  immediately flattened by equal-value notes.

## Scaling

All cells may be uniformly doubled:

| Scale | Short | Long | Dotted long |
|-------|-------|------|-------------|
| 1×    | 1     | 2    | 3           |
| 2×    | 2     | 4    | 6           |

A subject uses exactly one scale.  The scale is chosen before generation
based on note count and bar count: many notes in few bars → 1× scale;
fewer notes in more bars → 2× scale.

Decision rule: if N notes fit B bars at 1× scale (sum of minimum cell
ticks ≤ B × bar_ticks), use 1×.  Otherwise use 2×.  If neither fits,
fail — the note count is incompatible with the bar count.

## Generation Algorithm

1. **Input**: note count N, bar count B, metre (4/4 only), scale.

2. **Partition**: enumerate all ways to partition N into cells of size
   2, 3, and 4.  For each partition, enumerate all orderings of the
   size slots (e.g. [2,2,3,2,3] is one ordering of the partition
   3×2 + 2×3).

3. **Cell assignment**: for each size in each ordering, enumerate all
   cell types of that size (e.g. size 2 → iamb, trochee, or dotted).

4. **Transition filter**: reject sequences where any adjacent cell pair
   is N in the transition table.

5. **Bar fit**: compute total ticks at the chosen scale.  Reject
   sequences that don't fill exactly B bars.

6. **Score**: product of transition weights (Y=1.0, W=0.5) for all
   adjacent pairs.  Higher is better.

7. **Cap and sort**: sort descending by score.  Cap output at
   MAX_DURS_PER_COUNT (from constants.py).

8. **Output**: list of (cell_names, tick_sequence, score).

## Integration

The output replaces `_cached_scored_durations` in `duration_generator.py`.
The interface is unchanged: given a note count and bar length in ticks,
return a dict mapping note count → list of duration-index tuples.

The cell definitions and transition table live in a new module,
`rhythm_cells.py`, in the `motifs/subject_gen/` directory.

The generation logic lives in a replacement `duration_generator.py`.

## Constants Replaced

| Constant             | Replaced by                              |
|----------------------|------------------------------------------|
| MAX_SAME_DUR_RUN     | Transition table (no self-repeat for N)  |
| MAX_DUR_RATIO        | Cell definitions (ratios are 1:2 or 1:3) |
| MIN_SEMIQUAVER_GROUP | Tirata cell (exactly 4)                  |
| MAX_DURS_PER_COUNT   | Retained as output cap                   |
