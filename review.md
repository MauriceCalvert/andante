# Code Review: Planner & Builder

Reviewed against `laws.md` and project conventions. Sorted by severity.

---

## 1. Dead Modules (Still in Tree)

The current pipeline is: `planner.py` -> layers 1-4 -> `build_phrase_plans` -> `compose_phrases`.

These modules operate on the old `Plan`/`Episode`/`Phrase` hierarchy and are **never called from the active pipeline**:

| Module | Depends on old types |
|--------|---------------------|
| `planner/constraints.py` | `Plan`, `Structure`, `Section`, `Episode`, `Phrase` |
| `planner/coherence.py` | `Structure`, `Material`, `RhetoricalStructure`, `TensionCurve` |
| `planner/harmony.py` | `RhetoricalStructure`, `TensionCurve`, `HarmonicPlan` |
| `planner/structure.py` | `CadencePoint`, `SchemaSlot`, `SectionSchema` |
| `planner/plan_validator.py` | `Plan`, `SchemaPlan` (the latter doesn't exist) |

Likewise, the bulk of `planner/plannertypes.py` defines types (`Brief`, `Frame`, `Material`, `Motif`, `Plan`, `Episode`, `Section`, `Structure`, `MacroForm`, `TensionCurve`, `CoherencePlan`, `GenreTemplate`, etc.) that exist only to serve these dead modules. They inflate the import graph and create false coupling.

**Verdict:** Excise all five modules and trim `plannertypes.py` to only the types still imported by living code.

---

## 2. L017 Violations (Single Source of Truth)

### 2a. `_parse_signed_degree` / `_parse_signed_degrees` duplicated

Identical copy-paste in:
- `builder/config_loader.py:261-313`
- `planner/schema_loader.py:71-106`

### 2b. `_parse_typical_keys` duplicated

Identical regex-based parser in:
- `builder/config_loader.py:53-67`
- `planner/schema_loader.py:125-139`

### 2c. `_parse_metre` duplicated

Two different implementations of the same thing:
- `builder/phrase_planner.py:253-260`
- `builder/phrase_writer.py:80-87`

### 2d. `_degree_to_nearest_midi` duplicated

- `builder/phrase_writer.py:61-77`
- `builder/cadence_writer.py:40-61` (adds `ceiling` param)

The one without `ceiling` is a subset. Should be one function with optional ceiling.

### 2e. `_parse_fraction` duplicated

- `builder/cadence_writer.py:64-69`
- `builder/rhythm_cells.py:37-42`

### 2f. `VALID_DURATIONS_SET` defined three times

- `builder/phrase_writer.py:21`
- `builder/cadence_writer.py:18`
- `builder/rhythm_cells.py:16`

Should be one constant in `shared/constants.py`.

### 2g. `METRE_BAR_LENGTH` defined twice

- `builder/cadence_writer.py:19-22`
- `builder/rhythm_cells.py:17-20`

### 2h. Schema type duality

`planner/schema_loader.py:Schema` and `builder/types.py:SchemaConfig` represent the same YAML data with different field names. Two parallel hierarchies for one concept.

### 2i. `CadenceTemplate` name collision

`builder/cadence_writer.py:CadenceTemplate` and `planner/plannertypes.py:CadenceTemplate` are different types with the same name for different purposes.

---

## 3. D008 Violations (No Downstream Fixes)

### 3a. Bass voice-crossing correction

`builder/phrase_writer.py:505-512`:
```python
if sop_here is not None and pitch > sop_here:
    # Step down from soprano instead of stepping toward target
    pitch = current_key.diatonic_step(midi=sop_here, steps=-1)
```
This is a textbook downstream fix. The generator should choose a pitch below soprano in the first place, not overshoot and patch.

### 3b. `realise_bass_pattern` octave-shifting corrections

`builder/figuration/bass.py:280-327` does three separate post-hoc corrections:

1. **Consecutive same-direction leap fix** (lines 283-298): Detects consecutive leaps and tries octave shift.
2. **Tritone fix** (lines 300-316): Detects tritone and tries octave shifts, falls back to holding previous note.
3. **Leap-too-large fix** (lines 318-326): Detects large leaps and tries octave shifts.

All three violate D008. The pattern or `select_octave` should prevent these at source.

### 3c. `_fix_*` functions in tonal.py

Three functions with "fix" in the name, all mutating lists in-place after generation:

- `_fix_consecutive_non_tonic` (line 105)
- `_fix_consecutive_half_cadences` (line 140)
- `_fix_interior_authentic_overuse` (line 151)

The CLAUDE.md says: "Any function that 'fixes' things is illegal, fix at source." The generator (`_assign_key_areas`, `_assign_cadences`) should produce valid output directly via constrained selection.

---

## 4. L002 Violations (Magic Numbers)

### 4a. Module-level constants not in shared/constants.py

`builder/phrase_writer.py:22-24`:
```python
MAX_MELODIC_INTERVAL: int = 12
LEAP_THRESHOLD: int = 4
STEP_THRESHOLD: int = 2
```
These belong in `shared/constants.py`. `STEP_THRESHOLD` overlaps with `STEP_SEMITONES` already there.

### 4b. `_BASS_TEXTURE` hardcoded dict

`builder/phrase_writer.py:25-31`:
```python
_BASS_TEXTURE: dict[str, str] = {
    "minuet": "pillar",
    "gavotte": "walking",
    ...
}
```
Genre-to-bass-texture mapping is data, not code. Should be in genre YAML (A003 violation too).

### 4c. Sentinel values for durations

`builder/figuration/bass.py:78-82` uses `Fraction(-1)` for "bar" and `Fraction(-2)` for "half" as sentinel values. These are magic constants threaded through parsing and realisation.

### 4d. Hardcoded consonance sets in faults.py

`builder/faults.py:262`: local `consonant = frozenset({0, 3, 4, 7, 8, 9})` duplicates `CONSONANT_INTERVALS_ABOVE_BASS` from constants.

`builder/faults.py:420`: local `ugly = frozenset({1, 6, 10, 11})` duplicates `UGLY_INTERVALS` from constants.

---

## 5. Silent Defaults (Should Throw)

### 5a. `io.py:bar_beat()` assumes 4/4

Line 33-34:
```python
else:
    beats_per_bar = 4
```
CLAUDE.md: "assuming 4:4 time is forbidden." Should assert known metres.

### 5b. `bass.py:_get_beats_per_bar` assumes 4 for "any"

Line 342-345: returns 4 when metre is "any". Same violation.

### 5c. `_choose_modality` always returns "diatonic"

`planner/tonal.py:67-71`:
```python
def _choose_modality(affect_config: AffectConfig) -> str:
    if hasattr(affect_config, "rhythm_states") and affect_config.rhythm_states:
        return "diatonic"
    return "diatonic"
```
Dead if-branch. Both paths return the same value. Either remove the function entirely or implement it.

---

## 6. Type Hygiene

### 6a. `Any` in PhraseResult

`builder/phrase_types.py:49-50`:
```python
upper_notes: tuple[Any, ...]
lower_notes: tuple[Any, ...]
```
Should be `tuple[Note, ...]`. The `Any` suggests an import was avoided to prevent cycles, but that's a design issue.

### 6b. Old-style typing imports

`planner/constraints.py`, `planner/coherence.py`, `planner/harmony.py` use `from typing import Dict, List, Tuple, Optional` instead of `dict`, `list`, `tuple`, `| None`. Minor, but these are dead modules anyway (see section 1).

### 6c. `hasattr` on a dataclass

`builder/phrase_planner.py:25`:
```python
upbeat: Fraction = genre_config.upbeat if hasattr(genre_config, "upbeat") else Fraction(0)
```
`GenreConfig` is a frozen dataclass with `upbeat` field and default `Fraction(0)`. The `hasattr` is cargo code left from before the field was added.

---

## 7. Architectural Smells

### 7a. `planner.py` double tempo modifier

`config_loader.py:214` computes `tempo = genre_config.tempo + affect_config.tempo_modifier`.
`planner.py:86` computes `tempo = tempo + affect_config.tempo_modifier` again (on the raw L1 output).

The modifier is only applied once correctly in the end because L1 returns `genre_config.tempo` (without modifier), but the dead computation in `load_configs` is misleading. The `load_configs` function returns a `tempo` field that nobody uses correctly.

### 7b. Type mismatch on empty anchors

`planner.py:129`:
```python
home_key = anchors[0].local_key if anchors else key_config
```
If `anchors` is empty, `key_config` is a `KeyConfig` (not a `Key`). This would pass the wrong type to `compose_phrases`. Should assert `len(anchors) > 0`.

### 7c. Late import in types.py

`builder/types.py:108`:
```python
from shared.voice_types import ...  # noqa: E402
```
Imports after class definitions indicate circular dependency issues being worked around with ordering.

### 7d. `_schema_bars` in schematic.py accesses `.segments` as int

`planner/schematic.py:261`:
```python
if schema.sequential:
    return schema.segments   # int
```
But in `schema_loader.py`, `segments` is parsed as `int` via `_parse_segments`. However, `cadence_writer.py:184` treats it as `tuple`:
```python
segments = schema_def.segments or (2,)
return max(segments) if isinstance(segments, (list, tuple)) else segments
```
The two bar-counting paths disagree on whether `segments` is `int` or `tuple`. `SchemaConfig.segments` is `tuple[int, ...]` while `Schema.segments` is `int`. Two different types for the same YAML field.

---

## 8. L016 Violation (No Print)

`builder/faults.py:629-639`: `print_faults()` uses `print()` directly. Should use `logging`.

---

## 9. L011 Violation (While Loop Guards)

`planner/tonal.py:157-160`:
```python
while len(interior) > 1:
    idx: int = interior.pop()
    cadences[idx] = rng.choice(["half", "open"])
    interior = [i for i in range(len(cadences) - 1) if cadences[i] == "authentic"]
```
No `max_iterations` guard. If `rng.choice` keeps selecting "authentic" (it won't with the current candidates, but the contract isn't enforced), this loops forever.

---

## 10. Minor Issues

| Location | Issue |
|----------|-------|
| `faults.py:493` | Motion type `"parallel"` is not returned by `_motion_type()` (it returns "similar", "oblique", "contrary", "static"). Dead branch. |
| `schematic.py:37` | `logger = logging.getLogger(__name__)` imported but never used |
| `phrase_planner.py:40` | `anchor_group: list[Anchor] = anchor_groups[i] if i < len(anchor_groups) else []` -- defensive fallback hides bugs; should assert `i < len(anchor_groups)` |
| `phrase_planner.py:104` | `seq_positions` variable used at line 126 but only assigned inside `elif schema_def.sequential:` branch -- if that branch isn't taken, NameError |
| `io.py:36` | `total_beats: Fraction = (offset - upbeat) * 4` -- hardcoded `* 4` assumes quarter-note beats |

---

## Summary

| Category | Count |
|----------|-------|
| Dead modules | 5 files + bulk of plannertypes.py |
| L017 (duplicated code) | 9 instances |
| D008 (downstream fixes) | 6 functions |
| L002 (magic numbers / missing constants) | 4 groups |
| Silent bad defaults | 3 |
| Type issues | 3 |
| Architectural smells | 4 |
| Other law violations | 3 |
