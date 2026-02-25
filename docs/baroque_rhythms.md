# Baroque Rhythm Cells

## Purpose

Replace the current bar-fill duration enumerator with a musically principled
rhythm generator.  Rhythms are built by concatenating named cells drawn from
baroque practice, subject to a transition table that encodes which
successions sound right and which don't.

## Cells

Each cell has a name, a pattern of relative durations (S = short, L = long),
a note count, a metric weight profile, and a preferred beat alignment.

Duration values are expressed in x2-ticks (semiquaver = 1, quaver = 2,
crotchet = 4).  The table below gives the default realisation; cells may
be doubled (e.g. quaver-crotchet iamb in slower passages) provided all
cells in a subject use the same scaling.

| Cell      | Pattern | Notes | Ticks        | Metric character                   |
|-----------|---------|-------|--------------|------------------------------------|
| Iamb      | S-L     | 2     | 1-2 or 2-4   | Upbeat → downbeat. Forward motion. |
| Trochee   | L-S     | 2     | 2-1 or 4-2   | Downbeat → upbeat. Settling.       |
| Lombardic | S-L     | 2     | 1-2           | Short ON the beat, against expectation. Energetic. |
| Dotted    | L.-S    | 2     | 3-1           | Dotted quaver + semiquaver. Ceremonial weight. |
| Dactyl    | L-S-S   | 3     | 2-1-1 or 4-2-2 | Strong opening, tumbling forward.  |
| Anapaest  | S-S-L   | 3     | 1-1-2 or 2-2-4 | Building momentum into arrival.    |
| Tirata    | S-S-S-S | 4     | 1-1-1-1       | Equal-value run. Scalar energy, no internal accent. |

### Notes

- **Iamb vs lombardic**: identical durations, different metric placement.
  An iamb starts off the beat (anacrusis); a lombardic starts on the beat.
  The distinction matters for beat alignment (see below) but not for
  duration enumeration.  If beat alignment is not enforced, treat them as
  one cell.

- **Dotted**: always semiquaver resolution (3-1 ticks).  A dotted
  crotchet + quaver (6-2 ticks) is a doubled dotted, not a separate cell.

- **Tirata**: must be exactly 4 notes.  Shorter runs (2–3 semiquavers)
  are the short components of other cells.  Longer runs (5+) are two
  tiratas or a tirata + anapaest.

## Partitions

A rhythm for N notes is a sequence of cells whose note counts sum to N.
The available note counts are 2, 3, and 4.

For 12 notes, the partitions are:

| Partition          | Cells | Arrangements (unweighted) |
|--------------------|-------|---------------------------|
| 6 × 2-note        | 6     | 4^6 = 4,096              |
| 3 × 2-note + 2 × 3-note | 5 | C(5,2) × 4^3 × 2^2 = 2,560 |
| 2 × 2-note + 1 × 3-note + 1 × 4-note | 4 | 4!/2! × 4^2 × 2 × 1 = 384 |
| 3 × 4-note        | 3     | 1^3 = 1                  |
| 1 × 2-note + 1 × 3-note + 2 × 4-note | 4 | 4!/2! × 4 × 2 × 1 = 96 |
| 2 × 3-note + 1 × 2-note + 1 × 4-note | 4 | (same as above, included) |
| 4 × 3-note         | 4     | 2^4 = 16                 |

(Partitions involving tirata are rare because 4 semiquavers is a strong
commitment.  The generator should allow them but not favour them.)

Unconstrained total for 12 notes: approximately 7,000.
After transition filtering: roughly 2,500–3,500.

## Transition Table

The transition table governs which cell may follow which.  Each entry is
one of:

- **Y** — good succession, no penalty
- **W** — acceptable with a weight penalty (0.5)
- **N** — forbidden

The governing principles:

1. **Weight collision**: two consecutive accented onsets create a stop.
   L-ending cell → L-starting cell is penalised unless a bar boundary
   intervenes.

2. **Surprise cancellation**: a disruptive cell (lombardic, dotted) loses
   its effect if immediately repeated.

3. **Run monotony**: equal-value cells (tirata → tirata) flatten the
   rhythm.  One tirata is energy; two is a scale exercise.

4. **Flow**: S-ending → S-starting is always smooth.

| From ↓ / To → | Iamb | Trochee | Lombardic | Dotted | Dactyl | Anapaest | Tirata |
|----------------|------|---------|-----------|--------|--------|----------|--------|
| **Iamb**       | W    | Y       | Y         | Y      | Y      | W        | Y      |
| **Trochee**    | Y    | W       | Y         | W      | N      | Y        | Y      |
| **Lombardic**  | Y    | Y       | N         | W      | Y      | W        | Y      |
| **Dotted**     | Y    | W       | Y         | N      | W      | Y        | Y      |
| **Dactyl**     | Y    | W       | Y         | Y      | W      | Y        | Y      |
| **Anapaest**   | Y    | W       | W         | Y      | Y      | N        | W      |
| **Tirata**     | Y    | Y       | Y         | Y      | Y      | Y        | N      |

### Rationale for key entries

- **Trochee → Dactyl = N**: L-S followed by L-S-S places two long notes
  one short apart.  The metric weight collides.

- **Lombardic → Lombardic = N**: the snap is a surprise.  Two in a row
  is a stutter, not a surprise.

- **Dotted → Dotted = N**: same reasoning.  The ceremonial weight becomes
  mechanical if repeated.

- **Anapaest → Anapaest = N**: S-S-L followed by S-S-L places two longs
  meeting at the junction.  Heavy and static.

- **Tirata → Tirata = N**: eight consecutive semiquavers is a scale run,
  not a rhythmic figure.

- **Iamb → Iamb = W**: S-L S-L is metrically fine but rhythmically
  predictable.  Penalise, don't forbid.

- **Trochee → Trochee = W**: same reasoning.  L-S L-S is acceptable
  but uniform.

- **Anapaest → Lombardic = W**: the long note of the anapaest is
  immediately followed by the beat-accented short of the lombardic.
  Not wrong, but the stress pattern is unusual.

## Beat Alignment

Each cell has a preferred starting position relative to the beat:

| Cell      | Preferred start         |
|-----------|-------------------------|
| Iamb      | Off-beat (anacrusis)    |
| Trochee   | On-beat                 |
| Lombardic | On-beat                 |
| Dotted    | On-beat                 |
| Dactyl    | On-beat                 |
| Anapaest  | Off-beat                |
| Tirata    | On-beat or off-beat     |

Beat alignment is a soft preference, not a hard constraint.  Cells placed
against their preferred alignment are penalised but not rejected.

A cell's tick length determines its metric span:
- 2-tick cells: one quaver
- 3-tick cells: dotted quaver
- 4-tick cells: one crotchet

Alignment is evaluated by accumulating tick offsets from bar start and
checking whether each cell begins on or off the beat grid.

## Scaling

The default tick values assume semiquaver = 1 (the x2-tick system).
For slower subjects, all cells may be uniformly doubled:

| Scale | Short | Long | Dotted long |
|-------|-------|------|-------------|
| 1×    | 1     | 2    | 3           |
| 2×    | 2     | 4    | 6           |

A subject uses exactly one scale.  Mixed scales within a subject are not
permitted — they would imply a tempo change.

Scaling is chosen before generation based on note count and bar count:
many notes in few bars → 1× scale; fewer notes in more bars → 2× scale.

## Generation Algorithm

1. **Input**: note count N, bar count B, metre, scale.

2. **Partition**: enumerate all ways to partition N into cells of size
   2, 3, and 4.

3. **Permute**: for each partition, enumerate all orderings of cell types.
   For each ordering, enumerate all cell choices (e.g. for a 2-note slot:
   iamb, trochee, lombardic, or dotted).

4. **Transition filter**: reject sequences where any adjacent cell pair
   is marked N in the transition table.  Apply weight penalties for W
   transitions.

5. **Bar fit**: compute total ticks.  Reject sequences that don't fill
   exactly B bars.

6. **Beat alignment**: score each sequence for how well cells land on
   their preferred metric positions.

7. **Output**: ranked list of (cell sequence, tick sequence, score).

## Integration

The output of this generator replaces `_cached_scored_durations` in
`duration_generator.py`.  The interface is the same: given a note count
and bar length, return a list of tick sequences ranked by score.

The transition table and cell definitions live in a new module,
`rhythm_cells.py`, alongside `duration_generator.py`.

## Constraints Replaced

The following ad-hoc constants in `constants.py` become unnecessary:

| Constant            | Replaced by                          |
|---------------------|--------------------------------------|
| MAX_SAME_DUR_RUN    | Transition table (no self-repeat)    |
| MAX_DUR_RATIO       | Cell definitions (ratios are 1:2 or 1:3 only) |
| MIN_SEMIQUAVER_GROUP| Tirata cell (minimum 4) + anapaest/dactyl (minimum 2) |
| MAX_DURS_PER_COUNT  | Retained as output cap               |

## Open Questions

1. **Iamb/lombardic distinction**: worth tracking separately, or collapse
   into one cell and let beat alignment handle it?

2. **Tirata length**: fixed at 4, or allow 3-note short tiratas?  Three
   equal semiquavers occur in practice but blur the line with anapaest
   (S-S-L where L happens to equal S).

3. **Hemiola**: not a cell but a bar-level regrouping.  Only relevant in
   triple/compound time.  Out of scope for now; note as future extension.

4. **Rest cells**: baroque subjects occasionally begin with a rest (e.g.
   crotchet rest + anapaest).  Not covered here.  Add if needed.
