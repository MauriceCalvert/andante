### EPI-6 — Paired-kernel episode variety (2026-02-28)

Architecture delivered. PairedKernel extraction (shared-onset slicing),
EpisodeKernelSource chain solver (DFS, fragmentation ordering), and
EpisodeDialogue wiring (consonance check, voice exchange, fallback).
For subject09_2bar, paired-kernel path not activated: CS crotchet start
vs answer semiquaver start means all slices rejected (< 2 notes in both
voices). All 5 episodes use EPI-5b fallback. No regression (10 faults).
Fix: cross-slice windows (all pairs, not just consecutive). See result.md.

