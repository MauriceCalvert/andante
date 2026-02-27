# Continue — EPI-2a: Cell vocabulary expansion

## Status: task.md issued. Awaiting "go" in Claude Code.

## Context

HRL block complete (HRL-3 through HRL-7). EPI-1 done (variable-length
episodes, 42 bars, 5 episodes). All episodes sound alike because the cell
vocabulary is too narrow — all drawn from same subject head/tail cells.

EPI-2 split into three sub-phases:
- **EPI-2a** (now): Widen vocabulary with diminution + cross-source pairing
- **EPI-2b** (next): Fix fragen fallback (retry + minimal sequential)
- **EPI-2c** (stretch): Episode character arc (position-aware selection)

## What EPI-2a does

1. Adds `_diminish(cell)` — halves all durations, discards if any < 1/16
2. Expands `extract_cells` to include diminished variants of all cells
3. Adds cross-source pairing in `build_fragments` — head×tail, answer×cs
4. Caps cross-source pairs at 200 to prevent combinatorial explosion

All changes in `motifs/fragen.py` only. No pipeline integration changes.

## What to do next

1. Read `workflow/result.md`
2. Evaluate: catalogue should be at least 2× larger. At least 10 diminished
   and 10 cross-source fragments should survive consonance checking.
3. Run pipeline — fault count should be unchanged.
4. If pass: update completed.md, todo.md, continue.md
5. Listen to MIDI — episodes may already sound more varied (provider has
   more diverse material to choose from).

## After EPI-2a

EPI-2b: fragen fallback retry. When `realise_to_notes` returns None, try
up to 3 alternative fragments before falling through to static half-notes.
If all fail, generate a minimal stepwise sequential fallback.
