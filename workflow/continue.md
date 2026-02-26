# Continue — CLR-1: Dynamic Cadence Type

## Status: CLR-1 brief issued. Awaiting CC execution.

## Context

ICP-2 complete (CS2 alternation, labels). Invention passes listening gate.

## Current task: CLR-1 — Dynamic cadence type

Read cadence schema name from genre YAML `thematic.cadence` instead of
hardcoding `cadenza_composta`. Look up bar count from templates. Remove
`CADENCE_BARS` constant.

Four files: subject_planner.py, types.py, entry_layout.py, constants.py.
No audible change to invention (it already specifies cadenza_composta).

## Next

CLR-2: Internal section cadences (half cadences at section boundaries).
Or new templates (hemiola, grand cadence). Depends on listening priorities.
