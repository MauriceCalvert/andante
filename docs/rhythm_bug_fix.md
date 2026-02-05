# Rhythm Bug Fix

## Symptom

All three test pieces (gavotte, invention, minuet) exhibit a repeating 5/8 + 1/8 + 1/4 rhythmic cell in almost every bar. Melodies are sparse (2–3 notes per bar) where the originals have 4–8+. The pieces sound mechanical and unrecognisable.

## Root Causes

### Bug 1: Default affect forces `density: high` globally

**Location:** `data/rhetoric/affects.yaml`, `default` block, line ~150

The `default` affect sets `density: high`. Every named affect inherits from `default` via `_deep_merge`, and none overrides `density`. Therefore every `AffectConfig` has `density == "high"`.

**Consequence:** In `planner/voice_planning.py:538`:

```python
overdotted=affect_config.density == "high",
```

Every `GapPlan` gets `overdotted=True`.

In `FigurationStrategy._get_rhythm`, template lookup key `(3, "4/4", True)` resolves to the single overdotted template `[5/2, 1/2, 1]`. Scaled to a 1-whole-note gap (div sum 4): **5/8, 1/8, 1/4**. This is the repeating pattern.

**Fix:** Change `default` density from `high` to `medium`. Each named affect should declare its own density explicitly.

---

### Bug 2: Only one rhythm template per (note_count, metre, variant)

**Location:** `data/figuration/rhythm_templates.yaml`

Each (note_count, metre) pair has exactly one `standard` and one `overdotted` entry. Once Bug 1 selects overdotted, every 3-note bar in 4/4 gets the same durations. Even with Bug 1 fixed, every 3-note bar uses `[2, 1, 1]` -> `[1/2, 1/4, 1/4]`. Zero rhythmic variety.

Real Baroque writing mixes dotted rhythms, scotch snaps, Lombardic rhythms, even subdivisions, and running passages within a single piece. The template system needs multiple patterns per note count, selected by gap context (character, phrase position, affect).

**Fix:** Expand each (note_count, metre) entry to a list of named patterns with metadata (character, phrase_position, weight). `_get_rhythm` selects from the list using the GapPlan's character and phrase position. Overdotted becomes one pattern variant among many, not a binary switch.

---

### Bug 3: Note counts collapse to 2-3 via cascading reductions

Three forces crush note counts below what the music requires.

#### 3a: Non-lead voices unconditionally get density="low"

**Location:** `planner/voice_planning.py:_get_density`

```python
if not is_lead:
    return "low"
```

Low density -> rhythmic unit 1/4 -> base count 4 for a whole-note gap. After `SMALL_INTERVAL_NOTE_REDUCTION` (unison: -4, step: -3, third: -2), the result clamps to `MIN_FIGURATION_NOTES = 2`.

In contrapuntal genres (invention, gavotte), the bass is equally active. Hard-coding it to low density is wrong.

**Fix:** Non-lead density should respect `bass_treatment`. Contrapuntal bass gets the function-based density (same as lead). Only patterned/pillar bass defaults to low.

#### 3b: Small-interval reduction is inverted

**Location:** `shared/constants.py:318`

```python
SMALL_INTERVAL_NOTE_REDUCTION: dict[int, int] = {
    0: 4,  # unison
    1: 3,  # step
    2: 2,  # third
}
```

This assumes small intervals need fewer notes. Baroque practice is the opposite: a step or unison gap is typically filled with running scales or neighbour-tone figurations that need *more* notes, not fewer. A unison gap losing 4 notes from a base of 4 collapses to the minimum of 2.

**Fix:** Remove `SMALL_INTERVAL_NOTE_REDUCTION` entirely, or reverse it so small intervals add notes (more pitch space to decorate within a narrow span).

#### 3c: Downward iteration in fill_gap

**Location:** `builder/figuration_strategy.py:FigurationStrategy.fill_gap`

The loop iterates `range(max_count, MIN_FIGURATION_NOTES - 1, -1)`. If higher note counts fail the candidate filter (range, parallels, consonance), it falls to lower counts. Combined with the already-reduced max_count, this frequently bottoms out at 2-3 notes.

**Fix:** Once Bugs 3a and 3b are fixed, the starting count will be realistic and the downward iteration becomes a genuine fallback rather than the normal path.

---

## Why the Melodies Are Wrong

The sparsity follows directly from the note-count collapse. Bach's Invention No. 1 opens with a 16-note semiquaver subject. The system produces 3 notes per bar -- it cannot represent the subject. The gavotte's characteristic running quavers are similarly impossible at 3 notes per 4/4 bar. The melodic content is a consequence of the rhythmic bug, not a separate issue.

---

## Fix Summary

| # | Root cause | Location | Nature | Priority |
|---|-----------|----------|--------|----------|
| 1 | `density: high` always | `data/rhetoric/affects.yaml` default block | Data error | Immediate |
| 2 | `overdotted` as blunt toggle | `voice_planning.py:538` | Should be context-dependent | Immediate |
| 3a | Non-lead always "low" | `voice_planning.py:_get_density` | Ignores bass_treatment | Immediate |
| 3b | Small-interval reduction inverted | `shared/constants.py:318` | Remove or reverse | Immediate |
| 3c | fill_gap downward iteration | `figuration_strategy.py` | Becomes benign after 3a+3b | Deferred |
| 2+ | Single template per count | `rhythm_templates.yaml` | Needs vocabulary expansion | Phase 2 |

## Proposed Fix Order

1. ~~**Bug 1:** Change default density to `medium` in affects.yaml. Add explicit density to each named affect.~~ **DONE**
2. ~~**Bug 3b:** Remove or zero out `SMALL_INTERVAL_NOTE_REDUCTION`.~~ **DONE**
3. ~~**Bug 3a:** Make `_get_density` respect `bass_treatment` for non-lead voices.~~ **DONE**
4. ~~**Bug 2 (partial):** Make `overdotted` probabilistic or character-driven rather than density-driven.~~ **DONE**
5. **Bug 2 (full):** Expand rhythm templates to a vocabulary. This is the largest change and can be a separate phase. **DEFERRED TO PHASE 2**

After steps 1-4, the system should produce 4-8 notes per bar with even rhythms. Step 5 adds variety.

## Validation

Re-generate gavotte, invention, and minuet. Check:

- No repeating 5/8 + 1/8 + 1/4 pattern
- Note counts per bar match genre expectations (4-8 for gavotte/invention in 4/4, 3-6 for minuet in 3/4)
- Bass density matches soprano in contrapuntal genres
- Rhythmic variety across bars within a piece
