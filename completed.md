# Completed

## CP1 -- Fix thematic plumbing (2026-02-16)

Three bugs fixed in `planner/imitative/subject_planner.py` and `builder/free_fill.py`:

1. **Phantom bass in solo entries.** Changed `texture="plain"` to `texture="silent"` for
   `slot=="none"` voice assignments. Added silent-voice guard in `free_fill.py` to mark
   silent bars as occupied, preventing Viterbi companion generation.

2. **Missing episodes at section boundaries.** Relaxed `prev_is_special`/`curr_is_special`
   guard to only block cadences (not pedal/stretto/hold_exchange). Extended
   `_extract_lead_voice_and_key` to extract keys from hold_exchange, stretto, and pedal
   entries so episodes can bridge from these to the next subject entry.

3. **Episode bar duplication.** Changed episode iteration from `bar_offset` to
   `bar_offset + 1`, so the first episode bar starts at iteration +/-1 (already transposed)
   instead of iteration 0 (verbatim copy of preceding bar).

Verified: bar 1 bass silent, 3 episodes auto-inserted, no verbatim episode duplication,
seeds 1-10 clean, full 8-genre test suite passes.
