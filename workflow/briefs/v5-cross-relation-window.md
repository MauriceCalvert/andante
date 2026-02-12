## Task: V5 — Widen Viterbi cross-relation detection window

Read these files first:
- `viterbi/costs.py`
- `viterbi/pathfinder.py`
- `viterbi/test_brute.py`
- `viterbi/pipeline.py`

### Musical Goal

Eliminate cross-relations that the Viterbi solver currently misses because
its detection window is too narrow. The solver's `cross_relation_cost`
checks only the immediately adjacent grid step (t−1 vs t). At semiquaver
resolution a crotchet beat spans 4 grid steps. Cross-relations occurring
2–4 grid steps apart are invisible to the solver but audible, and flagged
by the post-hoc audit in `voice_writer.audit_voice`.

Concrete example from V4 output: soprano G#4 at offset 165/16 (bar 10
beat 4.25) against bass G3 at offset 21/2 (bar 11 beat 1.0) — 3
semiquaver steps apart, well within one beat. The solver never saw this
because it only compared adjacent steps.

The solver's cross-relation window must match the audit's window: ±1
crotchet (0.25 whole-note units), so both agree on what constitutes
"nearby".

### Idiomatic Model

**What the listener hears:** A cross-relation is one of the most jarring
faults in baroque counterpoint — G# in one voice against G♮ in the other
within the same beat sounds like a wrong note. It breaks the tonal field
established by the key. The listener hears a contradiction, not a chromatic
enrichment.

**What a competent musician does:** Awareness of the other voice extends
over a beat, not just the immediately adjacent note. If the bass has F# on
beat 3, the soprano avoids F♮ anywhere from beat 2 to beat 4. This is
unconscious but absolute — it is part of what "hearing the other voice"
means (Principle 2). The musician scans the other voice within a beat
window and never places a chromatic alteration of a pitch class they hear
nearby.

**Rhythm:** Unaffected. This is a pitch-selection constraint only.

**Genre character:** Cross-relation avoidance is universal across all
baroque genres. No genre-specific shaping required.

**Phrase arc:** Cross-relation avoidance applies uniformly at all phrase
positions. This is not a Principle 8 violation: avoidance of a
counterpoint fault is not an expressive device. Cross-relations are never
desirable anywhere.

### What Bad Sounds Like

**Cross-relation across grid gap:** Soprano G#4 against bass G♮3 within
the same beat but separated by 2–4 semiquaver grid steps. The solver
doesn't see it, produces it, and the audit flags it. The listener hears a
wrong note — Principle 2 (voices must relate) and Principle 3
(uncontrolled dissonance with no resolution).

### Known Limitations

1. **Window is time-based, not harmony-based.** The code checks within a
   fixed ±0.25 whole-note window (one crotchet). A musician would also
   consider harmonic context — an F# in a D major passage followed by F♮
   in a C major passage with clear cadential separation might be
   acceptable. The code treats all cross-relation pairs within the window
   equally. Acceptable because: (a) the cost is a preference (30.0), not
   a prohibition — the solver can still choose a cross-relation if all
   alternatives are worse; (b) false positives (penalising legitimate
   key-boundary changes) are less harmful than false negatives (allowing
   audible faults).

2. **Only follower-vs-leader direction.** The check examines the candidate
   soprano pitch against nearby bass pitches. It does not check
   bass-vs-future-soprano because the bass is already fixed. Acceptable
   because the bass is the given context — the soprano must adapt to it.

3. **Comparison with old check.** The old `cross_relation_cost` checked
   exactly 2 pairs: prev_follower vs curr_leader, and curr_follower vs
   prev_leader. At coarse grid resolution (integer beats, 1.0 apart), the
   old check was too aggressive — it flagged pairs 4 crotchets apart,
   which are not audible cross-relations. At fine grid resolution
   (semiquavers, 0.0625 apart), the old check was too narrow — it missed
   pairs 2–4 steps apart. The new windowed approach is correct at both
   resolutions because the window is in absolute time, not grid steps.

### Implementation

**File: `viterbi/pathfinder.py`**

1. Add constant at module level:
   ```
   CROSS_RELATION_BEAT_WINDOW = 0.25  # whole-note units = one crotchet
   ```

2. Before the DP loop (after building `leader_map` and `beats`), precompute
   a list of nearby leader pitch-class sets:
   ```
   nearby_ldr_pcs: list[frozenset[int]] = []
   for t in range(n_beats):
       pcs = frozenset(
           leader_map[beats[j]] % 12
           for j in range(n_beats)
           if abs(beats[j] - beats[t]) <= CROSS_RELATION_BEAT_WINDOW
       )
       nearby_ldr_pcs.append(pcs)
   ```

3. Pass `nearby_ldr_pcs[t]` as `nearby_leader_pcs` keyword argument to
   every `transition_cost` call (beat 1 seed and beats 2..n-1 loop).

4. In `_print_path`: the `bd` dict will now show `xr` reflecting the
   windowed cost. No structural change needed.

**File: `viterbi/costs.py`**

1. Replace `cross_relation_cost` function. New signature:
   ```python
   def cross_relation_cost(
       curr_pitch: int,
       nearby_leader_pcs: frozenset[int],
   ) -> float:
   ```
   Implementation: compute `curr_pc = curr_pitch % 12`. For each `lpc` in
   `nearby_leader_pcs`, check if `(min(curr_pc, lpc), max(curr_pc, lpc))`
   is in `_CROSS_RELATION_PAIRS`. Return `COST_CROSS_RELATION` on first
   match, 0.0 otherwise.

   Note: the old function also checked prev_follower vs curr_leader. This
   is no longer needed because prev_follower was already checked against
   its own nearby_leader_pcs at the previous DP step, whose window
   overlaps with the current position's leader. No coverage is lost.

2. Update `transition_cost` signature: add parameter
   `nearby_leader_pcs: frozenset[int] = frozenset()`. Pass through to
   the new `cross_relation_cost`. Remove the `prev_pitch`, `prev_leader`,
   `curr_leader` arguments from the `cross_relation_cost` call — those
   parameters are still received by `transition_cost` for use by
   `motion_cost`, `dissonance_at_departure`, `spacing_cost`, and
   `interval_quality_cost`.

**File: `viterbi/test_brute.py`**

1. In `brute_force_cost`, precompute `nearby_ldr_pcs` from the corridors
   list using the same window logic as `pathfinder.py`. Pass the
   appropriate entry to each `transition_cost` call. Import
   `CROSS_RELATION_BEAT_WINDOW` from `pathfinder`.

### Constraints

- Do not modify any file outside `viterbi/`.
- Do not change `solve_phrase` signature in `pipeline.py`.
- Do not change any dataclass in `mtypes.py`.
- Do not introduce backward-compatible wrappers for the old
  `cross_relation_cost` signature — it is only called from
  `transition_cost`.
- `CROSS_RELATION_BEAT_WINDOW` value must be `0.25` (matching the audit's
  `beat_unit` for 4/4 time).
- Before proposing any new mechanism, grep for existing code first.

### Checkpoint (mandatory)

After implementation, run:

1. `python -m viterbi.test_brute 5 20` — all 20 must pass (optimality
   preserved with new cost function).
2. `python -m viterbi.demo 1` — verify example 1 still runs. Output may
   differ slightly if the widened window changes costs at integer-beat
   resolution.
3. `python -m scripts.run_pipeline gavotte default 2025-01-02 -o tests/output 2>&1 | grep -E "cross-relation|audit"`
   — count cross-relation audit violations. Compare with V4 baseline
   (2 cross-relation violations at offsets 165/16 and 83/8).

Bob:
1. Did the cross-relation violations at bars 10–11 disappear?
2. Did any new faults appear (ugly intervals, parallel perfects, new
   cross-relations elsewhere)?
3. Does the soprano still flow smoothly across the formerly problematic
   region, or did cross-relation avoidance create awkward detours?
4. Is there tension and release in the affected phrases? (Principle 1)

Chaz:
For each remaining cross-relation violation (if any):
- Trace to specific grid positions and leader pitches
- Verify the window was correctly computed at those positions
- Determine whether the solver chose the cross-relation as a cost
  trade-off (acceptable) or the window missed it (bug)

### Acceptance Criteria

- Cross-relation audit violations at offsets 165/16 and 83/8 eliminated
  (the two V4 violations). If they persist, Chaz must explain why the
  solver chose to accept the 30.0 penalty. CC-measurable proxy; Bob's ear
  is the real test.
- `test_brute 5 20`: 20/20 pass.
- No new violation types introduced by the change.
- No files modified outside `viterbi/`.
- The solver and audit now agree on what "nearby" means: both use a
  ±0.25 whole-note window.
