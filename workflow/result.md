# CLR-1 Result

## Code Changes

**`planner/imitative/types.py`**
- Added `cadence_schema: str = "cadenza_composta"` field to `SubjectPlan`. Default preserves backward compatibility.

**`planner/imitative/subject_planner.py`**
- Removed `from shared.constants import CADENCE_BARS`
- Added `from builder.cadence_writer import load_cadence_templates`
- At the top of `plan_subject()`: reads `cadence_schema` from `thematic_config.get("cadence", "cadenza_composta")`, loads templates, asserts the `(schema, metre)` key exists, derives `cadence_bars: int` from `templates[key].bars`
- Replaced `entry_costs.append(CADENCE_BARS)` with `entry_costs.append(cadence_bars)`
- Passes `cadence_schema=cadence_schema` to `SubjectPlan` constructor

**`planner/imitative/entry_layout.py`**
- Added `_CADENCE_TYPE_MAP: dict[str, str]` mapping schema names to cadence types
- Replaced `get_schema(name="cadenza_composta")` with `get_schema(name=subject_plan.cadence_schema)`
- Replaced hardcoded `schema_name="cadenza_composta"` with `schema_name=cadence_schema_name`
- Replaced hardcoded `cadence_type="authentic"` with `cadence_type=_CADENCE_TYPE_MAP[cadence_schema_name]`

**`shared/constants.py`**
- Removed `CADENCE_BARS: int = 2` (dead code)

---

## Bob's Assessment

**Pass 1 — What do I hear?**

No change. The piece sounds exactly as before: the subject enters alone in bar 1, the answer follows in bar 2 with the first countersubject above, the music moves through six related keys, builds through stretto and pedal, and lands on the same two-bar cadential arrival in bars 30–31. The ending has the same approach and resolution it had before. Nothing has shifted in character, weight, or timing.

**Pass 2 — Why does it sound that way?**

This was pure plumbing. The genre YAML already specified `cadenza_composta` and the code was already producing a two-bar `cadenza_composta` ending. The change made the code *read* what it was already producing. No note moved.

---

## Chaz's Diagnosis

**Bob says:** "No change."

**Cause:** CLR-1 was a plumbing-only task. `invention.yaml` already specified `thematic.vocabulary.cadence: cadenza_composta`. The old constant `CADENCE_BARS = 2` happened to agree with the `cadenza_composta` template's `bars: 2`. The new code path reads the same value from the template, producing identical `SubjectPlan.bars` tuples. `entry_layout.py` now reads `subject_plan.cadence_schema` ("cadenza_composta") and looks it up in `_CADENCE_TYPE_MAP` (returns "authentic") — same schema, same type, same `PhrasePlan` output.

**Location:** `planner/imitative/subject_planner.py:plan_subject`, `planner/imitative/entry_layout.py:build_imitative_plans`

**Fix:** Already done. No open issues.

---

## Checkpoint Verification

1. Pipeline runs clean, no errors. ✅
2. Output identical to pre-CLR-1: 200 soprano + 134 bass notes, 31 bars. ✅
3. `CADENCE_BARS` no longer exists in `constants.py`. ✅
4. No hardcoded `"cadenza_composta"` in `subject_planner.py` or `entry_layout.py` (except the `.get()` default in `subject_planner.py` and the type map entry in `entry_layout.py`). ✅

---

Please listen to the MIDI and let me know what you hear.
