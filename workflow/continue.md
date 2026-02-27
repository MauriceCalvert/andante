# Continue — HRL-7: Note writer figured bass enrichment

## Status: task.md issued. Awaiting "go" in Claude Code.

## Context

HRL block: HRL-3 through HRL-6 done. EPI-1 done (variable-length episodes,
42 bars, 50% entries / 31% episodes / 14% cadences / 5% pedal).
HRL-7 is the last HRL item — figured bass numerals in .note CSV output.
Diagnostic only, no audible change.

## What HRL-7 does

1. Adds `harmony: str = ""` field to `Note` dataclass in `builder/types.py`.
2. Adds `chord_display_label()` to `builder/galant/harmony.py` — converts
   ChordLabel to figured bass string (e.g. "I", "ii6", "V/V").
3. After Viterbi generation in `bass_viterbi.py` and `soprano_viterbi.py`,
   stamps each note's `harmony` field from the HarmonicGrid when present.
4. Rewrites `_build_harmony_map` in `note_writer.py` to prefer grid-derived
   labels over bass-pitch inference. Iterates union of all offsets so
   grid-only onsets are not dropped.

## What to do next

1. Read `workflow/result.md` (written by Claude Code after "go")
2. Evaluate: FREE-fill bars should show figured bass (I, IV, V, V/V, I6, iv6).
   Subject/CS/stretto bars should still show bass-inferred harmony.
3. If pass: update completed.md, todo.md, continue.md
4. No listening needed — diagnostic only.

## EPI-1 listening notes

Episodes are structurally present and lengths scale correctly by key distance.
But most episodes sound like the subject — fragen draws from same head/tail
cells. Bars 28–30 used Viterbi fallback (fragen returned None in E minor),
producing static half-notes. Logged as known limitations; EPI-2 added to
roadmap for episode variety.

## After HRL-7

HRL block complete. Next priorities:
- SUB (subject generator reform) — tonal answers, rhythmic drama
- MEL (melodic quality) — Viterbi motivic coherence, figuration
- EPI-2 (episode variety) — if listening confirms need
