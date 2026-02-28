# Continue

## Status: EPI-5b — Episode parallel fix + Viterbi strong-beat parallel check

New chat starts here. EPI-5 (imitative dialogue episodes) is done but has
structural faults. EPI-5b brief is in `workflow/task.md`, ready for Claude Code.

Read this file, then `workflow/todo.md`, then `docs/Tier1_Normative/laws.md`,
then `docs/knowledge.md`, then `completed.md`.

---

## Context: what the invention looks like now

45 bars, C major. 3 subject appearances (subject, answer, stretto), 5 episodes
(Am 7 bars, F 6 bars, G 7 bars, Dm 6 bars, Em 7 bars), one answer+CS
restatement at bar 24 (Dm), half-cadence bar 39, cadenza grande bars 43–45.

Episodes now use imitative dialogue (`motifs/episode_dialogue.py`): both voices
state a 1-bar fragment from the subject in close imitation (1-beat offset,
lower 10th), sequencing stepwise, with progressive fragmentation in the last
iterations and voice exchange at midpoint for 6+ bar episodes. This replaced
the rejected kernel system.

## What EPI-5 achieved

1. Real imitative dialogue — both voices trade recognisable fragments
2. Sequential stepwise transposition through the key journey
3. Progressive fragmentation (half-fragment in last 2 iterations)
4. Voice exchange at midpoint for long episodes
5. Thematic coherence — fragment derived from subject

## What EPI-5b must fix

53 faults in the trace. 49 attributable to episode_dialogue or Viterbi gap.

### A. Episode crotchet-tail parallels (42 faults)

Both voices use the identical fragment at a fixed diatonic 10th. On beats 3–4
(crotchet tail), both descend in lockstep. Where the 10th collapses to an
octave (same pitch class), parallel octaves result. Every full-fragment
iteration produces this on beats 3–4.

**Fix:** Follower voice plays only the semiquaver portion (half-fragment) then
sustains its last pitch. Leader plays full fragment unchanged. Oblique motion
breaks the lockstep.

### B. Viterbi strong-beat parallels (bars 24–25)

CS against answer in D minor: C5/C3 → D5/D3 on consecutive downbeats. HC3
only checks adjacent grid steps — the weak-beat E5 between them hides the
parallel. The ear hears octaves on every strong beat.

**Fix:** New HC7 in `viterbi/costs.py` — check back to previous strong-beat
pitch, not just adjacent step. Uses existing beat_strength classification.

### C. Bass register excursion (1 fault)

A#1 in F major episode, 2 below C2 floor. Global octave shift too coarse.

**Fix:** Per-iteration octave shift instead of global.

### D. Ugly leaps at episode entry (2 faults)

D4→C5 (bar 11), C4→F#4 (bar 22). Octave shift applied after note generation.

**Fix:** Anchor first note within a 5th of prior pitch.

### E. Known issues NOT in EPI-5b scope

- 4 cross-relation faults (bars 11, 14, 28, 29) — key-planning interaction
- 4 pre-existing faults (unprepared dissonance bar 24 beat 1, ugly leap bar 40,
  2 parallel rhythms, consecutive leaps bar 39)

---

## Files involved in EPI-5b

- `motifs/episode_dialogue.py` — oblique tail, per-iteration shift, entry anchor
- `viterbi/costs.py` — HC7 strong-beat parallel check
- `viterbi/pipeline.py` — maintain prev_strong state for HC7
