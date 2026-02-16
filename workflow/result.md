# CP1 Result -- Fix thematic plumbing

## Changes Made

### `planner/imitative/subject_planner.py`
- Bug 1: `texture="plain"` -> `texture="silent"` for `slot=="none"` (line 434)
- Bug 2: `prev_is_special`/`curr_is_special` simplified to cadence-only check (lines 140-147)
- Bug 3: Episode iteration `bar_offset` -> `bar_offset + 1` (lines 248-251)
- Extended `_extract_lead_voice_and_key` to handle hold_exchange, stretto, pedal entries

### `builder/free_fill.py`
- Bug 1: Added silent-voice guard after `voice_material_map` construction (lines 84-89)

## Acceptance Criteria

1. Bar 1 bass: no notes -- PASS
2. Auto-inserted episodes: 3 (bars 7-8, 15-16, 21-22) -- PASS (exceeds minimum of 2)
3. No consecutive bars with identical soprano pitch sequences in episodes -- PASS
4. Pipeline seed 42: no assertion errors -- PASS
5. Pipeline seeds 1-10: no assertion errors -- PASS
6. Full test suite (8 genres, seed 42): all pass -- PASS

## Open Complaints (pre-existing, not CP1 scope)

- Hold-exchange bars 11-14: identical bar pairs (11=13, 12=14), mechanical oscillation
- Pedal bars 23-24: identical soprano pattern both bars
- 11 counterpoint faults (unprepared dissonances, cross-relations) -- CP2/CP3 scope
