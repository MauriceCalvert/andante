### EPI-8 — Episode endpoint navigation (2026-02-28 18:00)

Endpoint-driven episode trajectories delivered. Each voice now receives
independent start/target MIDI pitches and navigates via `_compute_step_schedule`
(front-loaded diatonic steps). `ascending` flag removed; `fragment_iteration=0`
for all episode bars. Voice exchange restored with register-preserving transpose:
soprano takes `lower_degrees − lower_degrees[0]`, bass takes `upper_degrees`
directly (no additional shift). Fault count 65 → 41. Perfect arrival at episode 5
→ bar 32 (G5→G5). Minor bass tessitura excursions remain during voice-exchange
second halves (G1/A1/B1). Cross-phrase target missing for episode→subject
transitions (compose.py plumbing gap — future work).

---

### EPI-6 — Paired-kernel episode variety (2026-02-28)

Architecture delivered. PairedKernel extraction (shared-onset slicing),
EpisodeKernelSource chain solver (DFS, fragmentation ordering), and
EpisodeDialogue wiring (consonance check, voice exchange, fallback).
For subject09_2bar, paired-kernel path not activated: CS crotchet start
vs answer semiquaver start means all slices rejected (< 2 notes in both
voices). All 5 episodes use EPI-5b fallback. No regression (10 faults).
Fix: cross-slice windows (all pairs, not just consecutive). See result.md.

