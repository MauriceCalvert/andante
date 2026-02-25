# Result: SH-2 — Head Enumeration + Dotted Durations + Mediant Removal

## Status: Complete

## Summary

Refactored subject generator from random CP-SAT sampling (40 restarts ×
50 solutions) to exhaustive head enumeration + per-head tail solving.
Pool expanded from 98 to 4,767 valid pitch sequences, stretto-capable
pool from 9 to 3,813 distinct pitches.

Also restored dotted durations (1,2,3,4,6) and removed mediant (degree 2)
from allowed finals.

## Files changed

- `motifs/subject_gen/constants.py` — HEAD_LENGTHS, durations, finals, solver params
- `motifs/subject_gen/head_enumerator.py` — new file
- `motifs/subject_gen/cpsat_generator.py` — rewritten (head-prefix solver)
- `motifs/subject_gen/pitch_generator.py` — rewritten (head iteration)
- `motifs/subject_gen/selector.py` — pitch dedup first, rhythm dedup removed, verbose passthrough
