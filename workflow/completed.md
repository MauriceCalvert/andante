### MIDI-1 — Canonical degree-to-MIDI resolution (2026-03-07 12:00)

Added `Key.degree_to_pc`; added `knot_midi_upper/lower` to `PhrasePlan`; added
`resolve_knot_pitches` forward pass in `register_plan.py`; called from `compose_phrases`
after register-target injection; updated `place_structural_tones` and bass Step 1 to use
pre-resolved knots when available; fixed 3 `degree_to_midi(octave=4)` callers in
`harmony.py` to use `degree_to_pc`; replaced two while-loop blocks in `_write_pedal` with
`degree_to_nearest_midi`. Pipeline clean, no assertion errors.

### REG-1 — Register planner (2026-02-28 21:00)

Two-pass register planner delivered in `planner/register_plan.py`. Pass 1 collects
thematic entry anchor pitches using whole-sequence octave placement with CS spacing
correction. Pass 2 computes episode start/end targets: contrary motion default
(soprano descends, bass ascends), ascending override with `_MIN_MEANINGFUL_MOTION=4`
guard, bass descent fallback, `_ENDPOINT_MARGIN=4` to prevent tessitura overshoot.
Phrase_writer.py: soprano target uses delta approach (planned direction+magnitude applied
to actual prior), bass uses absolute target with conditional delta rescue for zero-motion
cases. Voice separation floor (`+16st`) prevents delta from pushing soprano below bass.
Fault count: 82 baseline → 58 (29% improvement). Zero tessitura_excursion, zero
zero-motion episodes, all soprano arcs ≥4st, no monotonic climb.

---

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

