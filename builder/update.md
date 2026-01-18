# Builder Enhancement: Wire Plan to Execution

## Context

You are working on `D:\projects\Barok\barok\source\andante\builder`, a system that transforms YAML plans into baroque music. The pipeline works: brief → planner → YAML plan → tree elaboration → .note/.midi output.

**Problem:** The planner generates rich musical plans with treatments, harmony, tonal targets, and energy curves, but the builder ignores almost all of it. The soprano repeats the same 12-note subject identically for 24 bars. The bass plays simple root+fifth patterns.

## Current Architecture

```
scripts/run_builder.py      — Entry point, loads brief, calls planner, runs builder
builder/
  tree.py                   — Immutable tree structure for YAML traversal
  handlers/
    core.py                 — Handler dispatch: register(), elaborate(), include()
    structure.py            — Creates bars/voices from phrases
    material_handler.py     — Generates soprano notes (currently ignores plan)
    bass_handler.py         — Generates bass notes (primitive patterns)
  domain/
    material_ops.py         — Pure functions: fit_to_duration, convert_midi_to_diatonic
    transform_ops.py        — Transform class (mostly stubs)
    bass_ops.py             — compute_harmonic_bass, compute_diatonic_bass
  adapters/
    tree_reader.py          — extract_bar_context, extract_subject
    tree_writer.py          — build_notes_tree
  data/
    transforms.yaml         — Transform specifications
    bass_patterns.yaml      — Bass rhythm patterns per metre
  types.py                  — BarContext, Notes, Subject, etc.
data/
  bar_treatments.yaml       — Treatment definitions (name, transform, shift)
```

## Key Data Structures

**BarContext** (from tree_reader.py):
- `bar_index: int` — position within phrase (0, 1, 2...)
- `phrase_index: int` — phrase number in piece
- `phrase_treatment: str` — e.g. "statement", "imitation[exclamatio]"
- `harmony: tuple[str, ...]` — e.g. ("I", "V") for 2-bar phrase
- `tonal_target: str` — e.g. "V", "vi"
- `energy: str` — "moderate", "rising", "peak"
- `role: str` — "soprano" or "bass"
- `frame: FrameContext` — key, mode, metre

**Notes** (namedtuple):
- `pitches: tuple[int, ...]` — diatonic pitch numbers (0=C0, 7=C1, 28=C4)
- `durations: tuple[Fraction, ...]`

**Plan YAML structure** (see freude_invention.plan.yaml):
```yaml
structure:
  sections:
  - episodes:
    - phrases:
      - treatment: "inversion[circulatio+groppo]"
        harmony: [IV, IV]
        tonal_target: IV
        energy: rising
        bars: 2
```

## Tasks

### 1. Wire Plan Treatments to material_handler

**File:** `builder/handlers/material_handler.py`

Currently `_get_treatment_name()` uses hardcoded `BAR_TREATMENT_CYCLE`. Change it to:
- Bar 0: use `context.phrase_treatment` (already partially done)
- Bar 1+: derive continuation from phrase_treatment, not arbitrary cycle

Parse treatment strings like `"inversion[circulatio+groppo]"`:
- Base transform: `inversion`
- Ornaments: `circulatio`, `groppo` (store for later, not implemented yet)

### 2. Implement Real Transforms

**File:** `builder/domain/transform_ops.py`

The Transform class needs working implementations for:

| Transform | Description |
|-----------|-------------|
| `inversion` | Mirror around pivot: `new_pitch = 2*pivot - old_pitch` |
| `retrograde` | Reverse note order (pitches and durations) |
| `sequence` | Shift all pitches by N steps (use shift from treatment) |
| `augmentation` | Double all durations |
| `diminution` | Halve all durations |
| `fragmentation` | Take first N notes (e.g., first 4 of 12) |
| `stretto` | Compress: take every 2nd note or halve durations |

Each transform receives `Notes` and returns `Notes`. Keep them pure functions.

### 3. Add Melodic Variation Per Bar

**File:** `builder/handlers/material_handler.py`

Within a phrase, bars after the first should vary:
- Bar 0: statement (or phrase treatment)
- Bar 1: continuation — sequence down 1 step
- Bar 2+: development — combine sequence + fragmentation

Create a function `_derive_bar_treatment(phrase_treatment: str, bar_index: int) -> tuple[str, int]` returning (transform_name, shift_amount).

### 4. Connect Harmony to Melody

**Files:** `builder/domain/material_ops.py`, `builder/handlers/material_handler.py`

After generating notes, adjust them to fit the current chord:
- Get chord from `context.harmony[context.bar_index]`
- Chord tones for "V" in C major are G-B-D (diatonic 4, 6, 1)
- On strong beats (beat 1, 3), prefer chord tones
- Non-chord tones OK on weak beats

Create `harmonize_melody(notes: Notes, chord: str, key: str, mode: str) -> Notes` in material_ops.py. This nudges pitches toward chord tones without destroying the melody contour.

### 5. Improve Bass Patterns

**File:** `builder/handlers/bass_handler.py`, `builder/data/bass_patterns.yaml`

Current bass: root on beat 1, fifth on beat 3.

Enhance to:
- Walking bass for `energy: rising/peak`
- Sustained notes for `energy: moderate`
- Cadential patterns when `context.cadence` is set

Add to bass_patterns.yaml:
```yaml
walking:
  metres:
    4/4:
      pattern: [root, third, fifth, sixth]
      durations: [1/4, 1/4, 1/4, 1/4]
cadential:
  authentic:
    pattern: [fifth, root]
    durations: [1/2, 1/2]
```

Update `generate_bass_for_bar()` to select pattern based on context.energy and context.cadence.

## Coding Standards

- PyTorch not needed here (pure Python)
- One class per file, methods alphabetical
- Type hints on all parameters and returns
- Assert preconditions at function entry
- No blank lines inside functions
- ≤100 lines per module unless splitting harms cohesion
- Use `Fraction` for all durations
- Pure functions in `domain/`, orchestration in `handlers/`

## Test

After changes, run:
```
cd D:\projects\Barok\barok\source\andante
python -m scripts.run_builder freude_invention.brief -v
```

Verify:
1. Soprano varies across bars (not identical 48 times)
2. Transforms actually modify pitches (check .note output)
3. Bass has variety based on energy/cadence
4. No crashes or assertion failures

## Files to Read First

1. `builder/handlers/material_handler.py` — main target
2. `builder/domain/transform_ops.py` — needs implementations
3. `builder/adapters/tree_reader.py` — see what context is available
4. `builder/types.py` — data structures
5. `data/bar_treatments.yaml` — existing treatment definitions
6. `output/builder/freude_invention.plan.yaml` — see what planner produces

## Deliverables

1. Updated `transform_ops.py` with working transforms
2. Updated `material_handler.py` wiring plan treatments
3. New `harmonize_melody()` in `material_ops.py`
4. Updated `bass_handler.py` with pattern selection
5. Updated `bass_patterns.yaml` with walking/cadential patterns

Do not create new files unless necessary. Modify existing architecture.
