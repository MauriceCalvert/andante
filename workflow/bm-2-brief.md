# BM-2 — Melody generator

Read these files first:
- `docs/baroque_melody.md` (the full spec — sections 3, 5, 6, 7)
- `motifs/subject_gen/harmonic_grid.py` (created in BM-1)
- `motifs/subject_gen/rhythm_cells.py` (Cell dataclass)
- `motifs/subject_gen/constants.py` (ranges, limits)
- `motifs/subject_gen/models.py` (_ScoredPitch dataclass)
- `motifs/subject_gen/contour.py` (_derive_shape_name)
- `shared/pitch.py` (degrees_to_intervals)

## Goal

Create `motifs/subject_gen/melody_generator.py` — the pitch generation
engine that replaces head_enumerator + cpsat_generator + validator.
It produces `list[_ScoredPitch]` matching the existing interface.

## Interface contract

The module must export:

```python
def generate_pitched_subjects(
    cell_sequence: tuple[Cell, ...],
    mode: str,
    tonic_midi: int,
    n_bars: int,
    bar_ticks: int,
) -> list[_ScoredPitch]:
```

This is the new generation path.  `pitch_generator.py` will call it
in BM-3.  For now, just create the module with this entry point.

## Algorithm (§7 of baroque_melody.md)

Implement steps 1–7 as described in the spec.  Summary of the flow:

### Step 1: Harmonic rhythm level

Call `select_harmonic_level` from harmonic_grid with the flat tick
sequence from the cell chain.

### Step 2: Iterate harmonic patterns

Call `get_progressions(level)`.  For minor mode, the progressions
already use minor chord names.

### Step 3: Build C/P grid

For each note position in the cell sequence, assign C or P from the
cell pattern table (§3 of the spec):

| Cell     | Pattern       |
|----------|---------------|
| iamb     | P, C          |
| trochee  | C, P          |
| dotted   | C, P          |
| dactyl   | C, P, P       |
| anapaest | P, P, C       |
| tirata   | P, P, P, P    |

Apply boundary rule (§3.1): first note and last note forced to C.

For each note, compute its tick offset from bar 0 (cumulative sum of
preceding ticks).  Call `chord_at_tick` to determine the active chord.

Store as a list of `(slot_type, chord_name, tick_offset)` per note.

### Step 4: Enumerate C-slot skeletons

Identify the indices of all C-slots.  For each C-slot, enumerate
valid chord tones from `chord_tones(mode, chord)`, mapped to actual
pitch values within range [PITCH_LO, PITCH_HI].

A chord tone set gives degrees mod 7.  Expand each to all octave
positions within range:
```
for base_deg in chord_tone_set:
    for octave in range(-2, 3):  # enough to cover PITCH_LO..PITCH_HI
        pitch = octave * 7 + base_deg
        if PITCH_LO <= pitch <= PITCH_HI:
            yield pitch
```

Generate all combinations of C-slot pitches subject to (§5.1):
- Adjacent C-slots: `abs(c[i+1] - c[i]) <= 4` (max 5th)
- No same-pitch on adjacent C-slots (unless a neighbour figure exists
  between them — i.e. at least one P-slot separates them)
- First C-slot degree: `pitch % 7 in {0, 4}` (tonic or dominant)
- Last C-slot degree: `pitch % 7 in {0, 4}`
- Range: `RANGE_LO <= max(all_c) - min(all_c) <= RANGE_HI`

Use recursive enumeration with early pruning on interval and range
constraints.

### Step 5: Fill P-slots

Between each pair of adjacent C-slot anchors, compute the stepwise
path for the intervening P-slots.

Let `anchor_lo` and `anchor_hi` be the two C-slot pitches.  Let
`gap = anchor_hi - anchor_lo` (signed).  Let `m` = number of P-slots.

- If `abs(gap)` == m: one step per P-slot, straight line.
- If `abs(gap)` < m: insert neighbour-tone detour (§5.2).
  Step past target by 1, then step back.  Prefer upper neighbour
  for notes falling on even tick offsets, lower on odd.
- If `abs(gap)` > m: reject this skeleton (gap too large for
  stepwise fill).
- If m == 0 and `abs(gap)` > 2: reject (too large for direct leap
  between adjacent C-slots).

**Tirata handling (§3.2):** a tirata with no internal C-slot is
anchored by the last C-slot of the preceding cell and the first
C-slot of the following cell.  The fill rules above handle this
naturally — the P-slots fill stepwise between the two anchors.

**Melodic minor (§2):** when filling P-slots in minor mode, determine
fill direction from the two anchor C-slots.  If ascending and a
P-slot pitch has degree mod 7 in {5, 6}, use the raised form (call
`should_raise` and `degree_to_semitone` from harmonic_grid).

The fill is deterministic: given two anchors and a count, there is
exactly one stepwise path (or one with a single neighbour detour).

### Step 6: Validate

Apply all checks from §6 of the spec to the complete pitch sequence:

1. **Range**: RANGE_LO <= max - min <= RANGE_HI
2. **Forbidden intervals**: no tritone (abs interval producing 6
   semitones) between adjacent notes.  Use `degree_to_semitone` for
   accurate semitone computation including raised degrees.
3. **Cross-relations** (§4): at every chord boundary (where two
   adjacent notes have different active chords), check via
   `is_cross_relation` from harmonic_grid.
4. **Terminal degrees**: first note degree % 7 in {0, 4}, last note
   degree % 7 in {0, 4}.
5. **Repeated pitches**: no degree appearing > MAX_PITCH_FREQ times.
6. **Monotonic runs**: no more than MAX_SAME_SIGN_RUN consecutive
   same-direction steps.

### Step 7: Classify and return

For each valid sequence:
- Compute intervals via `degrees_to_intervals` from shared.pitch
- Classify shape via `_derive_shape_name` from contour.py
- Return as `_ScoredPitch(score=0.0, ivs=ivs, degrees=degrees, shape=shape)`

Score is left at 0.0 — aesthetic scoring happens in selector.py.

## Data structures

Use a frozen dataclass for the per-note grid entry:

```python
@dataclass(frozen=True)
class NoteSlot:
    index: int          # position in note sequence
    slot_type: str      # "C" or "P"
    chord: str          # active chord name (e.g. "I", "V", "iv")
    tick_offset: int    # ticks from bar 0
```

## Constraints

- Do not modify any existing file.  This brief creates one new file only.
- Do not import from head_enumerator, cpsat_generator, pitch_generator,
  or validator.
- May import from: harmonic_grid, rhythm_cells, constants, models,
  contour, shared.pitch, shared.constants.
- Functions sorted alphabetically.
- One parameter per line.  Type-hint everything.
- Assert preconditions and shapes.
- L002: name all thresholds.  The C-slot max interval (4 steps) should
  be a constant `MAX_CSLOT_INTERVAL = 4`.
- L016: logging only.
- L019: ASCII only.
- L020: keyword args only.
- The C/P pattern table must be data (dict keyed by cell name), not
  if-chains (A001).

## Checkpoint

Verify the module imports cleanly:

```
python -c "from motifs.subject_gen.melody_generator import generate_pitched_subjects; print('OK')"
```

Then run a smoke test:

```python
from motifs.subject_gen.rhythm_cells import IAMB, TROCHEE, DACTYL
from motifs.subject_gen.melody_generator import generate_pitched_subjects

results = generate_pitched_subjects(
    cell_sequence=(TROCHEE, IAMB, DACTYL, TROCHEE, IAMB),
    mode="major",
    tonic_midi=60,
    n_bars=2,
    bar_ticks=8,
)
print(f"Generated {len(results)} pitched subjects")
assert len(results) > 0, "No subjects generated"
for sp in results[:5]:
    print(f"  degrees={sp.degrees} shape={sp.shape}")

# Minor mode
results_minor = generate_pitched_subjects(
    cell_sequence=(TROCHEE, IAMB, DACTYL, TROCHEE, IAMB),
    mode="minor",
    tonic_midi=57,
    n_bars=2,
    bar_ticks=8,
)
print(f"Minor mode: {len(results_minor)} pitched subjects")
assert len(results_minor) > 0, "No minor subjects generated"
```

Report: number of subjects generated for each mode, any cell sequences
that produce zero results, and any design decisions not in the spec.
