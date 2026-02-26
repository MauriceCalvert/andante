## Result: CLR-2 — Internal section cadences

### Code Changes

**`planner/imitative/types.py`**
- Added `cadence_schema: str | None = None` to `BarAssignment` dataclass.

**`planner/thematic.py`**
- Added `cadence_schema: str | None = None` to `BeatRole` dataclass.

**`planner/imitative/subject_planner.py`**
- Loaded `half_cadence` template and bar count at startup (asserted present).
- In step 2b: inserted `_internal_cadence` entry (`schema="half_cadence"`, `key=prev_key`) **before** each auto-episode at section boundaries.
- Added handler in step 3 for `_internal_cadence` entries: stamps `function="cadence"`, `local_key=ic_key`, `cadence_schema=ic_schema` on all BarAssignments.
- Updated the final `entry == "cadence"` branch to stamp `cadence_schema=cadence_schema` (genre's configured schema).

**`planner/imitative/entry_layout.py`**
- `_build_thematic_roles`: passes `cadence_schema=bar_assignment.cadence_schema` to each BeatRole.
- `_group_beat_roles`: tracks `cadence_schema` in `bars_data`; adds it to group dicts.
- `build_imitative_plans` cadence branch: reads `cadence_schema_name = group["cadence_schema"]` (asserted non-None); uses `local_key` (from group) instead of `home_key`.

---

### Bob's Assessment

**1. How many cadences? Bar numbers?**

4 cadences total. Internal half cadences at bars 6, 17, and 28. Final cadenza_composta at bars 33-34.

**2. Half cadences on V in local key?**

Yes, all three hit V correctly:
- Bar 6 (A minor): soprano 3->2 (C5->B4), bass 1->5 (A3->E3). E is degree 5 of Am.
- Bar 17 (D minor): soprano 3->2 (F4->E4), bass 1->5 (D3->A2). A is degree 5 of Dm.
- Bar 28 (C major): soprano 3->2 (E4->D4), bass 1->5 (C3->G2). G is degree 5 of C.

**3. Breath after internal cadences?**

Yes. Arrival notes (both voices) are 3/8 duration in all three HCs — that is 1/2 (half note per template) minus HALF_CADENCE_BREATH (1/8).

**4. Final cadence unchanged?**

Yes — cadenza_composta at bars 33-34, home key C major, two bars, tagged PAC. Unchanged.

**5. More rhetorical shape?**

Yes. The piece now breathes in three places. After each section's material builds, both voices converge on V, then the episode bridges to the next key. The paragraph structure — argument / pause / bridge / new argument — is now audible. 31 bars -> 34 bars with the three 1-bar insertions.

---

### Chaz's Diagnosis

**Which BarAssignments have function="cadence"?**

Bars 6, 17, 28 (internal HCs) and bars 33-34 (final cadenza_composta).

**cadence_schema per group:**

- [3] bar 6: cadence_schema="half_cadence", local_key=A min — outgoing exordium key.
- [8] bar 17: cadence_schema="half_cadence", local_key=D min — outgoing narratio key.
- [13] bar 28: cadence_schema="half_cadence", local_key=C maj — outgoing confirmatio key (final two strettos were in C).
- [16] bars 33-34: cadence_schema="cadenza_composta", local_key=C maj — home key.

**Dispatch path:**

build_imitative_plans reads group["cadence_schema"] and local_key from the group dict. For HCs this is "half_cadence" / local key; for the final cadence it is "cadenza_composta" / home key. write_cadence is dispatched for all four groups (the HCs use the half_cadence template; the final cadence uses cadenza_composta). write_thematic_cadence is not called here — that path is invoked at a separate dispatch site. The half_cadence template is confirmed dispatched.

**The chain is complete:** _internal_cadence entry -> BarAssignment.cadence_schema -> BeatRole.cadence_schema -> group dict -> PhrasePlan.schema_name / local_key -> write_cadence.

---

Please listen to the MIDI and let me know what you hear.
