### [SUSP-1] Suspension reward constant (2026-03-08 16:45)

**Code**: `viterbi/costs.py` — `COST_SUSPENSION = 2.0` renamed to
`COST_SUSPENSION_REWARD = -18.0`. Reference updated in `dissonance_at_departure`.

**Bob**: No suspensions present in this output. Every strong beat settles
immediately — no lean-and-release. The invention.brief (seed 42) generates no
galant Viterbi sections, so the mechanism has no opportunity to fire.

**Chaz**: The constant is correct. Net suspension chain cost is now −3.0 (was
+17.0), making the pattern 3 units cheaper than alternatives. No Viterbi galant
voices are scheduled in this invention plan; verification requires a galant-schema
brief. No unprepared strong-beat dissonances in the fault log.

**Open**: Acceptance criterion (audible 7-6 suspension) deferred — invention
brief has no galant Viterbi sections. Fix is architectural; will manifest in a
galant or suite movement.

---

### EPI-6 fixes + kernel range solver (2026-03-08)

Three spec deviations in the paired-kernel system corrected:
- `extract_kernels.py`: min-notes rule tightened to ≥2 per voice in both
  `_extract_slices` and `_truncate_pk`.
- `extract_kernels.py`: third source pairing corrected to `cs_subj`
  (CS as upper, subject as bass).
- `episode_kernel.py`: pool register filter added (`lower_degrees[0] >= 0`
  → reject); fixes episode bass resolving to soprano register.

Range warnings added to `_emit_paired_voice_notes` and `_emit_voice_notes`
in `episode_dialogue.py` — no clamping, warnings only.

`KernelRangeContext` dataclass added to `episode_kernel.py`. DFS solver
(`_dfs`) now calls `_kernel_in_range` before accepting each candidate atom:
computes all absolute MIDI degrees for all notes across all repetitions at
the current chain position, rejects if any falls outside the assigned voice
range. `episode_dialogue.py` constructs and passes the context from
per-episode data already in scope. Canonical solution: range policy owned
by planner, builder executes, solver prunes without compensating.

---

### BUG-1 — Fix ep_label AttributeError (2026-03-07)

One-line fix in `builder/phrase_writer.py`: replaced `get_tracer()._episode_count`
with `entry_first_bar` for episode lyric label. Pipeline clean, no AttributeError.

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

