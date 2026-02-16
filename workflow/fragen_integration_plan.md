# Plan: Fragen Integration — Episodes and Holds

## Diagnosis (from invention.note)

Two specific failures, both caused by voices rendered independently
without cross-voice awareness.

### Problem 1: Episodes (bars 7–8, 13–14, 19–20)

Both voices stamped independently by `_render_episode_fragment`.
Soprano gets the tail (ascending sixteenth run), bass gets the head
(descending quarter-note walk). No consonance check between them.
Result: unprepared dissonances, cross-relations. Two monologues.

### Problem 2: Holds (bars 11–12)

`hold_writer` generates running voice via Viterbi against held note.
CP3 added subject-cell knots but fill between knots is Viterbi
stepwise — the "sewing machine". 3-note oscillation for 16 sixteenths.

### What is NOT broken

CS entries (cs_writer with Viterbi): leave alone.
Free fill: not the acute problem.
Pedal: parked. Subject/answer stamping: works.

---

## Pre-requisite: Fix Fragen's Cell Vocabulary

**This comes before any integration work.**

The current `extract_cells()` is crippled by three constraints:

1. `_bar_aligned_cells()` only extracts cells at bar boundaries
2. Final filter `c.total_duration % bar_length == 0` kills sub-bar cells
3. Result: ~6 bar-filling cells from a 2-bar subject

This is why the POC produced only 4 soprano-led episodes. The musically
interesting fragments — the 4-sixteenth ascending run, the mordent
figure, the tail truncated to a beat — are all discarded.

**Fix:** Replace bar-aligned extraction with contiguous sub-sequence
extraction (the original fragen.md spec, steps 1b–1d). Every
contiguous sub-sequence of 2+ notes from head, tail, answer, and CS.
No bar-alignment requirement. Cells carry their natural duration
(1/4 bar, 1/2 bar, 1 bar, etc.).

**Chain building** then assembles these sub-bar cells into bar-filling
chains (spec step 2a). A bar could be `tail[0:4]` + `tail[0:4]` +
`head[0:2]` (1/4 + 1/4 + 1/2 = 1 bar). This is where the variety
comes from.

Expected yield: 30–40 cells after sub-cells + inversions + dedup
(matching the original spec), up from ~6 today. Many more valid
Fragments, including bass-led ones.

---

## What Fragen Needs

### Consonance (W1 — must be much stronger)

Current fragen checks only at half-bar positions (beat 1, beat 3 in
4/4). This is far too coarse.

**Required:**
- Check at every quarter-beat position (semiquaver grid in 4/4)
- Parallel perfect 5ths/8ves detection on consecutive strong beats
- Cross-relation detection (chromatic pitch in one voice, natural
  form in the other within 2 beats)
- Weak-beat dissonance tolerance: only if approached AND left by step
- Voice-crossing check at every note onset, not just strong beats

This brings fragen's consonance checking close to the Viterbi solver's
coverage. Without it, we swap one set of dissonances for another.

### Cell boundary scoring (W4)

When one cell ends and the next begins in a chain, the interval at
the join can be awkward. Score chains by boundary smoothness: penalty
for leaps > 3 scale steps at cell joins. Already in the fragen.md
spec (scoring item 4) but not implemented.

### Pipeline adapter (E1–E4)

- Convert degree-space output to `builder.types.Note` (MIDI, absolute
  offset, track)
- Accept `start_offset: Fraction` for absolute time placement
- Accept `prior_upper_pitch` / `prior_lower_pitch` for smooth
  connection to preceding material
- Accept `Key` object from phrase plan

### Fragment diversity (W3, E5)

Planner must specify leader voice per episode. No automatic alternation
— the planner knows the section structure and can distribute.

To prevent motivic saturation: allow Viterbi to have a turn
occasionally. Not every non-thematic bar needs fragen. If an episode
follows a hold-exchange, use Viterbi for variety. Or: if the cell
vocabulary is small (< 15 cells), fall back to Viterbi for some bars.
The planner decides, not fragen.

### Hold exchange (H1–H3)

For holds, fragen generates only the running voice. The held note
stays in hold_writer (simple, works). Fragen replaces only the
`_generate_running_voice_bar()` Viterbi call.

Generate both bars of the exchange in one call (`n_bars=2`, `step=-1`)
so the sequence continues across the swap rather than restarting.
hold_writer calls fragen once for the pair, not bar-by-bar.

U1 from previous plan: a held note isn't a cell, so
`build_hold_fragments()` with its synthetic Cell wrapper is forced.
Simpler: a dedicated `realise_cell_chain_against_held()` that takes
a cell chain, a held pitch, and returns running-voice notes. Skip
the full Fragment pairing machinery.

---

## Phasing

| Phase | Scope | Risk |
|-------|-------|------|
| F0 | Fix cell vocabulary: sub-sequence extraction + chain building. Run POC, verify yield ≥25 cells, ≥10 diverse Fragments including bass-led. | Low — self-contained in fragen.py |
| F1 | Strengthen consonance: quarter-beat checks, parallel motion, cross-relation, weak-beat tolerance. Pipeline adapter (Notes, offset, Key). | Medium — algorithmic |
| F2 | Episode integration: replace per-voice episode dispatch in phrase_writer with fragen paired rendering. Planner specifies leader voice. | Medium — changes dispatch |
| F3 | Hold integration: replace Viterbi running-voice call with fragen cell-chain realisation. Both bars generated as one call. | Medium — simpler than F2 |

Each phase has a listening gate.

---

## Critique — What Could Go Wrong

**W1. Consonance regression.** Addressed: F1 strengthens checking to
quarter-beat grid with parallel motion and cross-relation detection.
Should be strictly better than current independent episode rendering
(which has no cross-voice checks at all).

**W2. Vocabulary still too small.** F0 fixes this. If a particular
subject yields < 15 cells even after sub-sequence extraction, the
planner should know and can allocate some bars to Viterbi instead.

**W3. Motivic saturation.** Mitigated by: (a) larger cell vocabulary
including inversions and sub-cells gives more variety, (b) planner
can assign some bars to Viterbi for contrast, (c) episodes and holds
are only 6/24 bars in this invention — most bars are thematic entries.

**W4. Cell boundary leaps.** Addressed in F1: chain scoring penalises
boundary leaps > 3 steps.

**W5. Hold exchange continuity.** Addressed: single 2-bar call.

**W6. Leader voice assignment.** Addressed: planner specifies per
episode. No automatic alternation.

**W7. Two-voice episodes break free_fill.** The dispatch change in F2:
add an EPISODE branch in `_write_thematic` (like HOLD and CS branches).
When both voices are EPISODE, call fragen for both. free_fill's
`voice_material_map` already marks both voices as having material for
EPISODE entries, so it won't try to fill them. Verified in the code:
the per-voice loop in `_write_thematic` renders each EPISODE voice
independently; replacing that with a single fragen call that returns
both is the same structural pattern as the HOLD branch.

**W8. Sequence truncation.** Partial final iterations are normal in
Bach. Prefer truncation at rhythmically strong positions.

---

## Recommendation

F0 first — without more cells, everything downstream starves.
Then F1 (consonance + adapter), F2 (episodes), F3 (holds).

Total scope: `motifs/fragen.py` (vocabulary + consonance + adapter),
`builder/phrase_writer.py` (episode dispatch), `builder/hold_writer.py`
(running voice replacement). No new modules.
