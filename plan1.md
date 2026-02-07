# Plan 1: Activate the Tonal System

## Problem Summary

Five short-circuits render core systems inert:
1. `modality == "diatonic"` makes all modulation dead
2. Binary forms get I→I (no tonal contrast)
3. `character="plain"` hardcoded (figuration always sparse)
4. Upbeat offset logic dead (anacrusis impossible)
5. `tension_to_energy` has redundant condition

## Guiding Laws

- **L008/L009**: Tonal targets = harmonic functions. Schemas operate relative to a local key — the planner picks which key, the builder writes in it.
- **A005**: RNG in planner only. Key selection is a planning decision (L2/L3).
- **D008**: No downstream fixes. Each layer must produce correct output.
- **L002**: No magic numbers. Key area rules go in constants.

## Execution Order

Fix 1 (tonal system) is the foundation — everything else is subordinate. We do these in dependency order.

---

## Fix 1: Activate Modulation (Critical)

### 1A. Remove the `modality == "diatonic"` short-circuit

**File**: `planner/metric/layer.py`
**Line 447**: Delete `if modality == "diatonic": return home_key`

The `_get_local_key()` function already has correct logic for resolving key areas to keys (lines 449-459). It just needs to execute.

**Also**: Remove the `modality` parameter from `_get_local_key()` entirely. It serves no purpose once the guard is gone. Update all call sites.

Remove `modality` parameter from:
- `layer_4_metric()` signature
- `_generate_all_anchors()` signature
- `_generate_phrase_anchors()` signature
- `_phrase_anchors_from_chain()` signature
- `_phrase_anchors_legacy()` signature

Update the caller in `planner/planner.py` to stop passing `modality`.

### 1B. Fix binary-form key areas in L2

**File**: `planner/tonal.py`, `_assign_key_areas()`

Current logic for `count == 2`: first="I", last="I". No intermediate section gets a contrasting key.

**Fix**: Add a binary-form branch. For 2-section forms:
- Section A (first): "V" for major home keys, "III" for minor home keys
  - This represents the *destination* key area — section A's schemas should modulate *toward* V by the cadence
- Section B (last): "I" (return home)

This requires knowing the home mode. Add `home_mode: str` parameter to `_assign_key_areas()`. Pass from `layer_2_tonal()` via `affect_config`.

**New constants** in `planner/tonal.py`:
```python
_BINARY_A_KEY_MAJOR: str = "V"
_BINARY_A_KEY_MINOR: str = "III"
```

### 1C. Distribute key areas per-schema within sections

**File**: `planner/schematic.py`, `layer_3_schematic()`

Currently every schema in a section gets the same key_area (line 90). For a section whose key_area is "V", only the final schema(s) should be in V — the interior should transition.

**Change**: Instead of `all_key_areas.append(section_plan.key_area)` for every schema, use a distribution strategy:
- First schema(s): "I" (home key)
- Last schema in section: `section_plan.key_area` (the target)
- Middle schemas: transitional (use home "I" — the modulation happens naturally through the schema's sequential transposition)

Implementation: new function `_distribute_key_areas(section_schemas, section_key_area, is_first_section)` that returns a list of key_areas per schema.

For Section A of a binary (key_area="V"):
```
[do_re_mi → "I", fenaroli → "I", prinner → "V"]
```

For Section B (key_area="I"):
```
[monte → "V", fenaroli → "I", passo_indietro → "I", cadenza_semplice → "I"]
```

Section B *starts* in the key that Section A ended in (V), then returns to I.

### 1D. Thread key areas through phrase planner

**File**: `builder/phrase_planner.py`

Currently `local_key` comes from anchors (line 123). The anchors already carry `local_key` from `_get_local_key()` — once Fix 1A removes the guard, this will propagate automatically.

Verify: `build_phrase_plans()` → `anchor_group[0].local_key` → `PhrasePlan.local_key`. No change needed here if anchors are correct.

### 1E. Verify `Key.modulate_to()` handles all L2 targets

**File**: `shared/key.py` + `shared/constants.py`

Already confirmed: `MODULATION_TARGETS` supports I, IV, V, ii, iii, vi for major and I, III, IV, V, VI for minor. All L2 candidates (`_ODD_KEY_CANDIDATES`, `_EVEN_KEY_CANDIDATES`, `_PENULTIMATE_KEY`) are in this set. No change needed.

---

## Fix 2: Wire Figuration Character

### 2A. Add `character` field to PhrasePlan

**File**: `builder/phrase_types.py`

Add field with default:
```python
character: str = "plain"
```

### 2B. Add `character` to genre YAML sections

**Files**: `data/genres/minuet.yaml`, `gavotte.yaml`, `invention.yaml`, `bourree.yaml`, `sarabande.yaml`, `chorale.yaml`, `fantasia.yaml`, `trio_sonata.yaml`

Add `character` field per section. Sensible defaults:
- Opening/exordium sections: `"plain"` or `"expressive"`
- Continuation/development: `"energetic"` or `"bold"`
- Cadential/closing: `"ornate"`
- Chorale: always `"plain"`

Example for minuet:
```yaml
sections:
  - name: A
    character: expressive
    ...
  - name: B
    character: energetic
    ...
```

### 2C. Wire phrase planner to extract character

**File**: `builder/phrase_planner.py`

In the phrase plan building loop, extract `character` from the genre section dict:
```python
character: str = genre_section.get("character", "plain")
```

Pass to `PhrasePlan(character=character, ...)`.

Need a helper or inline lookup to get the genre section for the current schema's section_name.

### 2D. Replace hardcoded `character="plain"` in phrase writer

**File**: `builder/phrase_writer.py`, line 392

Change:
```python
character="plain",
```
To:
```python
character=plan.character,
```

---

## Fix 3: Fix Upbeat Offset

### 3A. Make first phrase start at bar 0 for upbeat genres

**File**: `builder/phrase_planner.py`

Change initialization logic around line 38:
```python
# Current:
cumulative_bar: int = 1

# New:
has_upbeat: bool = upbeat > Fraction(0)
cumulative_bar: int = 0 if has_upbeat else 1
```

This allows the first schema to get `first_bar = 0`, which triggers the upbeat branch in `_compute_start_offset()`.

### 3B. Adjust bar span accounting for upbeat phrase

The first phrase with upbeat starts at bar 0 but bar 0 is a partial bar. The bar_span calculation may need adjustment. Currently `bar_span` comes from `get_schema_bars()`. If the first schema spans 3 bars and starts at bar 0, bars are 0, 1, 2 → span should be 3 but bar numbering is 0-2 not 1-3.

Verify that `cumulative_bar` increments correctly after the first phrase:
```python
cumulative_bar += bar_span  # 0 + 3 = 3... should be bar 3 for next phrase
```

This needs careful checking. The anchor system uses bar 0 for upbeat, bar 1 for first full bar. After a 3-bar schema starting at bar 0: bars 0, 1, 2 → next starts at bar 3. That's correct (bar 3 is the 3rd full bar).

Wait — if the piece has upbeat, bar 0 is partial. A 3-stage schema starting at bar 0 occupies bars 0, 1, 2. But bar 0 is partial, so the schema's *effective* content spans 2 full bars + partial. This is already handled in `_build_bar_assignments` (layer.py:128-129) where `end_bar -= 1` for upbeat first section.

After the first phrase: `cumulative_bar = 0 + bar_span = 3`. But the next phrase should start at bar 3 (the actual 3rd full bar). Need to verify alignment with Layer 4 anchors.

### 3C. Update test P-13

**File**: relevant test file

The test currently passes incorrectly. After fix, verify:
- Upbeat genres: `start_bar == 0`, `start_offset == -upbeat`
- Non-upbeat genres: `start_bar == 1`, `start_offset == 0`

---

## Fix 4: Clean Up Minor Issues

### 4A. Fix `tension_to_energy` redundant condition

**File**: `planner/arc.py`, lines 81-83

Current:
```python
if level < 0.85:
    return "peak"
return "peak"
```

Change to:
```python
if level < 0.85:
    return "high"
return "peak"
```

Or clarify the intended semantics. "high" makes more sense as the level below "peak". Check if "high" is a valid energy name in consumers.

Actually — look at the full function:
```
< 0.25 → "low"
< 0.45 → "moderate"
< 0.7  → "rising"
< 0.85 → "peak"  ← should probably be "high"
else   → "peak"
```

Need to check what energy names are used downstream before changing. This might need a new constant/enum.

### 4B. Remove dead code (optional, low priority)

- `planner/motif_loader.py`: `load_motif`, `load_motif_from_file` — never called
- `planner/schema_loader.py:218`: `get_arrival_beats` — never called
- `planner/dramaturgy.py:567`: `get_tempo_bpm` — never called

These are harmless. Remove only if explicitly asked.

---

## Testing Strategy

After all fixes are made (per CLAUDE.md — don't test after each change):

1. **Unit tests**: Run tests for changed modules:
   - `tests/planner/test_tonal.py` — key areas for binary forms
   - `tests/planner/test_metric_layer.py` — anchors carry correct local keys
   - `tests/builder/test_L5_phrase_planner.py` — upbeat offset, character field
   - `tests/builder/test_phrase_writer.py` — character propagation

2. **Integration**: Generate a minuet and an invention, check traces:
   - Anchors show different keys for different sections
   - Phrase plans carry `character` from genre config
   - Upbeat genres start at negative offset

3. **Fault check**: Run faults on generated pieces to ensure modulation doesn't introduce voice-leading errors.

---

## Dependency Graph

```
Fix 1A (remove modality guard)
  └─ Fix 1B (binary key areas)
       └─ Fix 1C (per-schema key distribution)
            └─ Fix 1D (verify propagation)

Fix 2A (PhrasePlan.character)
  └─ Fix 2B (genre YAML)
       └─ Fix 2C (phrase planner wiring)
            └─ Fix 2D (phrase writer wiring)

Fix 3A (cumulative_bar init)
  └─ Fix 3B (bar span accounting)
       └─ Fix 3C (test update)

Fix 4A (tension_to_energy) — independent
Fix 4B (dead code) — independent
```

Fixes 1, 2, 3, 4 are independent of each other and can be implemented in any order. Within each fix, steps are sequential.

---

## Risk Assessment

**Fix 1 (tonal)**: Highest impact, moderate risk. Modulation changes which MIDI pitches are generated — could introduce new voice-leading faults. Must verify with fault checker.

**Fix 2 (character)**: Low risk. Changes figuration density, not pitch content. Purely additive.

**Fix 3 (upbeat)**: Moderate risk. Changes timing offsets — could break note alignment. Need careful bar-numbering verification.

**Fix 4**: Zero risk. Cosmetic.
