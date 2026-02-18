# Subject Generator V2 — Hybrid Design

## Problem

The SG1–SG9 archetype chain produces dull subjects. Each generator picks
the next note independently from interval constraints. There is no motivic
logic, no structural rhythm variety, and no phrase shape. The output is
scale exercises and random walks.

The previous generator (pre-SG) had concrete musical logic — rhythm
templates with variety, leap-and-fill head rules, named tail cells — but
lacked archetype differentiation and affect sensitivity.

V2 grafts the old generator's concrete musical structures onto the new
system's archetype framework. Everything configurable goes in YAML.
Code reads YAML and assembles; it does not contain musical decisions.

## Principle

A baroque subject is not built note-by-note. It is assembled from
**gestures** — short melodic-rhythmic units that have idiomatic shape.
The generator's job is to select gestures appropriate to the archetype,
connect them, and validate the result.

## Architecture

```
YAML data layer
├── data/archetypes/{name}.yaml    — archetype constraints (keep, extend)
├── data/subject_gestures/         — NEW: gesture libraries
│   ├── head_gestures.yaml         — kopfmotiv gesture templates
│   ├── tail_cells.yaml            — continuation interval cells
│   └── kadenz_formulas.yaml       — cadential close patterns
└── data/rhythm_cells/cells.yaml   — existing rhythm cell library

Code layer (reads YAML, assembles, validates)
├── motifs/gesture_loader.py       — NEW: load + cache gesture YAML
├── motifs/kopfmotiv.py            — REWRITE: gesture-based head generation
├── motifs/fortspinnung.py         — REWRITE: cell-based continuation
├── motifs/kadenz.py               — REWRITE: formula-based close
├── motifs/melodic_validator.py    — KEEP as-is
├── motifs/answer_analyser.py      — KEEP as-is
├── motifs/fragment_analyser.py    — KEEP as-is
├── motifs/subject_scorer.py       — KEEP as-is (may extend criteria)
├── motifs/subject_generator.py    — KEEP chain logic, minimal changes
├── motifs/archetype_selector.py   — KEEP as-is
└── motifs/archetype_types.py      — EXTEND to load new gesture refs
```

## YAML Data Design

### 1. Head Gestures (`data/subject_gestures/head_gestures.yaml`)

Each gesture is a **contour template** — a sequence of interval types
(not specific intervals) paired with a rhythm pattern. The generator
instantiates a gesture by choosing concrete intervals within constraints
and transposing to the start degree.

```yaml
# A gesture defines SHAPE, not specific pitches.
# interval_types:
#   step    = +1 or -1  (direction from gesture direction)
#   leap    = +3 to +5  (always in gesture direction)
#   skip    = +2        (in gesture direction)
#   back    = -1 or -2  (contrary to gesture direction, i.e. gap-fill)
#   hold    = 0         (repeated note)
#   any_up  = +1 to +3
#   any_down = -1 to -3

# --- SCALAR gestures ---

scalar_run_4:
  archetype: scalar
  interval_types: [step, step, step]       # 4 notes, 3 intervals
  rhythm: ["1/8", "1/8", "1/8", "1/8"]
  character: driving
  metre_filter: ["4/4", "2/2"]

scalar_run_held_start:
  archetype: scalar
  interval_types: [hold, step, step, step]  # BWV 846 pattern: held C then run
  rhythm: ["1/4", "1/8", "1/8", "1/8", "1/8"]
  character: solemn
  metre_filter: ["4/4", "2/2"]

scalar_run_dotted_start:
  archetype: scalar
  interval_types: [step, step, step]
  rhythm: ["3/8", "1/8", "1/8", "1/8"]
  character: stately
  metre_filter: ["4/4", "2/2"]

scalar_run_6:
  archetype: scalar
  interval_types: [step, step, step, step, step]
  rhythm: ["1/16", "1/16", "1/16", "1/16", "1/16", "1/16"]
  character: energetic
  metre_filter: ["4/4"]

scalar_run_3_34:
  archetype: scalar
  interval_types: [step, step]
  rhythm: ["1/8", "1/8", "1/8"]
  character: flowing
  metre_filter: ["3/4"]

# --- TRIADIC gestures ---

triadic_ascending_3:
  archetype: triadic
  interval_types: [skip, skip]              # 0-2-4 = triad outline
  rhythm: ["1/4", "1/8", "1/8"]            # long first note
  character: open
  metre_filter: ["4/4", "2/2"]

triadic_ascending_4:
  archetype: triadic
  interval_types: [skip, skip, skip]        # 0-2-4-6 or 0-2-4-7
  rhythm: ["3/8", "1/8", "1/8", "1/8"]
  character: grand
  metre_filter: ["4/4"]

triadic_leap_fill:
  archetype: triadic
  interval_types: [leap, back, back]        # leap up, step back twice
  rhythm: ["1/4", "1/8", "1/8", "1/4"]
  character: graceful
  metre_filter: ["4/4", "3/4"]

triadic_wide_4:
  archetype: triadic
  interval_types: [leap, skip, back]
  rhythm: ["1/4", "1/4", "1/8", "1/8"]
  character: bold
  metre_filter: ["4/4"]

# --- CHROMATIC gestures ---
# These operate in diatonic degrees but the generator will apply
# chromatic_inflections (specified below) at render time.

chromatic_lamento_4:
  archetype: chromatic
  interval_types: [step, step, step]        # descending: 0, -1, -2, -3
  rhythm: ["1/4", "1/4", "1/4", "1/4"]     # equal crotchets, grave
  character: lament
  metre_filter: ["4/4", "3/4"]
  force_direction: descending
  chromatic_inflections: [1, 2]             # indices to chromaticise

chromatic_neighbour:
  archetype: chromatic
  interval_types: [step, back, step]        # e.g. 0, -1, 0, -1 with chromatic -1
  rhythm: ["1/4", "1/8", "1/8", "1/4"]
  character: tense
  metre_filter: ["4/4"]
  chromatic_inflections: [1]

chromatic_descent_6:
  archetype: chromatic
  interval_types: [step, step, step, step, step]
  rhythm: ["1/4", "1/4", "1/4", "1/8", "1/8", "1/4"]
  character: grave
  metre_filter: ["4/4"]
  force_direction: descending
  chromatic_inflections: [1, 3]

# --- RHYTHMIC gestures ---
# Pitch range is narrow; the rhythm IS the identity.

rhythmic_dotted_4:
  archetype: rhythmic
  interval_types: [hold, step, back]        # narrow: e.g. 0, 0, 1, 0
  rhythm: ["3/16", "1/16", "3/16", "1/16"]
  character: martial
  metre_filter: ["4/4", "2/2"]

rhythmic_repeated_accel:
  archetype: rhythmic
  interval_types: [hold, hold, step]        # Handel-like: repeated note then move
  rhythm: ["1/4", "1/8", "1/8", "1/4"]
  character: emphatic
  metre_filter: ["4/4"]

rhythmic_syncopated:
  archetype: rhythmic
  interval_types: [step, back, step]
  rhythm: ["1/8", "1/4", "1/8", "1/4"]     # off-beat weight
  character: restless
  metre_filter: ["4/4"]

rhythmic_lombard:
  archetype: rhythmic
  interval_types: [step, back, step, step]
  rhythm: ["1/16", "3/16", "1/16", "3/16", "1/8"]
  character: lombardic
  metre_filter: ["4/4"]

rhythmic_hammer:
  archetype: rhythmic
  interval_types: [hold, hold, hold, step]
  rhythm: ["1/8", "1/8", "1/8", "1/8", "1/4"]
  character: driving
  metre_filter: ["4/4", "2/2"]

# --- COMPOUND gestures ---
# Two-part: static (held/repeated) then kinetic (fast)

compound_held_run:
  archetype: compound
  interval_types: [hold, step, step, step]  # BWV 578: held note then scale
  rhythm: ["1/2", "1/8", "1/8", "1/8", "1/8"]
  character: dramatic
  metre_filter: ["4/4"]

compound_dotted_run:
  archetype: compound
  interval_types: [hold, step, step]
  rhythm: ["3/4", "1/8", "1/8", "1/8", "1/8"]
  character: majestic
  metre_filter: ["4/4"]

compound_repeated_run:
  archetype: compound
  interval_types: [hold, hold, step, step, step]
  rhythm: ["1/4", "1/4", "1/8", "1/8", "1/8", "1/8"]
  character: building
  metre_filter: ["4/4"]

# --- DANCE gestures ---

dance_gigue_leaps:
  archetype: dance
  interval_types: [leap, back, leap]
  rhythm: ["3/8", "1/8", "1/4"]
  character: leaping
  metre_filter: ["6/8", "3/8"]

dance_minuet_step:
  archetype: dance
  interval_types: [step, step, skip]
  rhythm: ["1/4", "1/4", "1/4", "1/4"]
  character: graceful
  metre_filter: ["3/4"]

dance_bourree_upbeat:
  archetype: dance
  interval_types: [step, leap, back, step]
  rhythm: ["1/8", "1/8", "1/4", "1/8", "1/8"]
  character: sturdy
  metre_filter: ["4/4", "2/2"]
```

### 2. Tail Cells (`data/subject_gestures/tail_cells.yaml`)

Tail cells are short interval patterns with a net direction. They are
combined to build the fortspinnung (continuation). Each cell has a
named character and a net pitch displacement.

```yaml
# Each cell: intervals (degree steps), net displacement, character.
# The generator chains 1–3 cells to fill the continuation budget.

# --- Descending cells ---

step_down:
  intervals: [-1]
  net: -1
  character: resolving

run_down_2:
  intervals: [-1, -1]
  net: -2
  character: flowing

run_down_3:
  intervals: [-1, -1, -1]
  net: -3
  character: running

run_down_4:
  intervals: [-1, -1, -1, -1]
  net: -4
  character: cascading

skip_down:
  intervals: [-2]
  net: -2
  character: gentle

skip_step_down:
  intervals: [-2, -1]
  net: -3
  character: falling

down_turn:
  intervals: [-1, -1, 1]
  net: -1
  character: turning

skip_return_down:
  intervals: [-2, 1]
  net: -1
  character: sighing

step_skip_down:
  intervals: [-1, -2]
  net: -3
  character: accelerating

run_skip_down:
  intervals: [-1, -1, -2]
  net: -4
  character: tumbling

skip_run_down:
  intervals: [-2, -1, -1]
  net: -4
  character: cascading

# --- Ascending cells ---

step_up:
  intervals: [1]
  net: 1
  character: rising

run_up_2:
  intervals: [1, 1]
  net: 2
  character: climbing

run_up_3:
  intervals: [1, 1, 1]
  net: 3
  character: running

run_up_4:
  intervals: [1, 1, 1, 1]
  net: 4
  character: soaring

skip_up:
  intervals: [2]
  net: 2
  character: lifting

skip_step_up:
  intervals: [2, 1]
  net: 3
  character: rising

up_turn:
  intervals: [1, 1, -1]
  net: 1
  character: arching

skip_return_up:
  intervals: [2, -1]
  net: 1
  character: breathing

step_skip_up:
  intervals: [1, 2]
  net: 3
  character: accelerating

run_skip_up:
  intervals: [1, 1, 2]
  net: 4
  character: surging

skip_run_up:
  intervals: [2, 1, 1]
  net: 4
  character: climbing
```

### 3. Kadenz Formulas (`data/subject_gestures/kadenz_formulas.yaml`)

Cadential close patterns. Each has a degree sequence relative to the
landing degree and a rhythm. The generator picks one appropriate to the
archetype and fills the remaining budget.

```yaml
# degrees are relative: 0 = landing degree.
# e.g. landing on degree 0 (tonic): step_above gives [1, 0]

step_above:
  approach_degrees: [1, 0]
  rhythm: ["1/8", "1/4"]
  archetypes: [scalar, triadic, chromatic, compound]
  may_augment: true

step_below:
  approach_degrees: [-1, 0]
  rhythm: ["1/8", "1/4"]
  archetypes: [scalar, triadic, chromatic, compound]
  may_augment: true

turn_above:
  approach_degrees: [1, -1, 0]
  rhythm: ["1/8", "1/8", "1/4"]
  archetypes: [scalar, chromatic]
  may_augment: true

leading_tone:
  approach_degrees: [2, 1, 0]
  rhythm: ["1/8", "1/8", "1/4"]
  archetypes: [scalar, triadic, chromatic, compound]
  may_augment: true

sustained_arrival:
  approach_degrees: [0]
  rhythm: ["1/2"]
  archetypes: [compound, rhythmic]
  may_augment: false

dotted_close:
  approach_degrees: [1, 0]
  rhythm: ["3/16", "1/16", "1/4"]
  archetypes: [rhythmic, dance]
  may_augment: false

dance_close:
  approach_degrees: [1, 0]
  rhythm: ["1/4", "1/4"]
  archetypes: [dance]
  may_augment: false
```

### 4. Archetype YAML Extensions

Each archetype YAML gains new fields that reference the gesture library:

```yaml
# Example: scalar.yaml additions
head:
  # ... existing constraints remain for validation ...
  gestures:                          # NEW: which head gestures to use
    - scalar_run_4
    - scalar_run_held_start
    - scalar_run_dotted_start
    - scalar_run_6
    - scalar_run_3_34
continuation:
  # ... existing constraints remain for validation ...
  preferred_cells:                   # NEW: which tail cells suit this archetype
    - run_down_2
    - run_down_3
    - run_down_4
    - run_up_2
    - run_up_3
    - run_up_4
    - down_turn
    - up_turn
  cell_chain_max: 3                  # max cells to chain
  contrary_motion: true              # continuation reverses head direction
kadenz:
  formulas:                          # NEW: which kadenz formulas to use
    - step_above
    - step_below
    - leading_tone
    - turn_above
```

## Generation Algorithm

### Step 1: Select gesture (replaces old kopfmotiv generators)

```
1. Load head_gestures.yaml
2. Filter by archetype name
3. Filter by metre compatibility
4. Filter by affect character (if affect implies e.g. "solemn", prefer
   gestures with character "solemn" or "stately")
5. Weighted random choice (weights from character-affect match)
6. Instantiate the gesture:
   a. Choose start degree from archetype.head.start_degrees
   b. Choose direction (from archetype_selector)
   c. Resolve interval_types to concrete intervals:
      - step  → +1 or -1 (from direction)
      - leap  → random from {+3, +4, +5} (in direction)
      - skip  → +2 (in direction)
      - back  → -1 or -2 (contrary to direction)
      - hold  → 0
   d. Apply chromatic_inflections if present (shift specified
      indices by one additional semitone — this is a flag for
      the degrees_to_midi function, stored as metadata, not
      a degree change)
   e. Validate: range, start degree, intervals within archetype limits
```

### Step 2: Build continuation (replaces old fortspinnung generators)

```
1. Determine continuation direction:
   - If archetype.continuation.contrary_motion: reverse head direction
   - Otherwise: same direction
2. Calculate continuation budget (same as current)
3. Load tail_cells.yaml
4. Filter by archetype.continuation.preferred_cells
5. Filter by direction (net displacement matches continuation direction)
6. Build a chain of 1–3 cells:
   a. First cell: random from filtered set
   b. Each subsequent cell: must keep cumulative degrees within
      range (head range ± range_extension)
   c. Total intervals must match available duration slots
7. Assign rhythm:
   a. Inherit rhythm vocabulary from head gesture (its unique durations)
   b. Distribute durations across cell intervals using head's duration
      pool, with cadential lengthening on last note
   c. Validate: total duration = continuation budget
```

### Step 3: Close with kadenz (replaces current kadenz)

```
1. Load kadenz_formulas.yaml
2. Filter by archetype.kadenz.formulas
3. Calculate kadenz budget (total bars - head - continuation)
4. For each candidate formula:
   a. Check rhythm fits within budget
   b. If may_augment and budget allows, double final note
   c. Choose landing degree from archetype.kadenz.stable_degrees
   d. Resolve approach_degrees relative to landing
5. Pick best fitting formula
6. Append to body
```

### Steps 4–8: Same as current

Melodic validation, answer analysis, fragment analysis, scoring,
candidate selection. No changes needed.

## Chromatic Handling

The current system cannot produce chromatic subjects because it works
entirely in diatonic degrees. V2 adds a `chromatic_inflections` list
to gestures that specify which notes should be chromatically altered.

Implementation: `degrees_to_midi` gains an optional
`chromatic_offsets: tuple[int, ...]` parameter. Each entry is a
semitone adjustment (+1 or -1) applied after the standard
degree-to-MIDI conversion. Default is all zeros (diatonic).

The `chromatic_inflections` field in a head gesture identifies which
note *indices* get a chromatic offset. The generator resolves these
to concrete offsets based on direction and mode:
- Descending chromatic in minor: lower each inflected note by 1 semitone
  (producing the lamento tetrachord: C-B-Bb-A)
- Ascending chromatic in major: raise each inflected note by 1 semitone
  (producing a chromatic approach: F-F#-G)

This keeps the degree system diatonic while allowing chromatic colour
at the MIDI level.

## What Gets Deleted

- `kopfmotiv.py`: all six `_generate_*` functions and their helpers
  (`_EVEN_VALUES`, `_LONG_SHORT_*`, `_affect_density`, `_dance_note_value`,
  `_select_note_value`). These are replaced by gesture instantiation.
- `fortspinnung.py`: all six continuation functions and their helpers.
  Replaced by cell chaining.
- `kadenz.py`: `_generate_approach_path`, `_fit_kadenz_durations`.
  Replaced by formula lookup.

## What Gets Kept

- `archetype_types.py`: extended with gesture/cell/formula references
- `archetype_selector.py`: unchanged
- `melodic_validator.py`: unchanged
- `answer_analyser.py`: unchanged
- `fragment_analyser.py`: unchanged
- `subject_scorer.py`: unchanged (may later weight gesture character match)
- `subject_generator.py`: chain logic unchanged, calls new generators
- `head_generator.py`: `degrees_to_midi` extended with chromatic_offsets

## Migration Path

1. Create the three gesture YAML files
2. Create `gesture_loader.py` (load + cache)
3. Extend archetype YAMLs with gesture/cell/formula references
4. Rewrite `kopfmotiv.py` (gesture-based)
5. Rewrite `fortspinnung.py` (cell-based)
6. Rewrite `kadenz.py` (formula-based)
7. Extend `degrees_to_midi` with chromatic_offsets
8. Run archetype_sampler, compare with current output
9. Iterate on gesture library (add/tune gestures based on listening)

The gesture YAML files are the tuning surface. Once the code is in
place, improving subjects means adding gestures and adjusting their
character tags — no code changes required.
