# Continue

## Current state

Plans 4–7 complete. No active plan.

### Completed plans
- Plan 4 (Rhythm Repair): walking bass even quarters, soprano-aware
  cell selection verified, pillar bass energetic cell guard.
- Plan 5 (Boundary Smoothing): audit showed boundaries already smooth
  (avg 2.2st soprano, 3.8st bass). degree_to_nearest_midi with
  prev_exit_midi threading already handles proximity. No code changes.
- Plan 6 (Motivic Return): HeadMotif capture, recall_figure_name
  threading, placement at B-section start and pre-final cadence.
- Plan 7 (Genre Validation): 5 genres validated. Bass routing fix
  (continuo_walking). Sarabande 2 cross-relations, invention lacks
  imitation. Minuet/gavotte/bourree have genre character.

### Known test failures (5, all from Plan 4.1)
- parallel_rhythm: gavotte_c_major (bar 15.3), gavotte_a_minor (bar 15.3),
  invention_c_major (bars 5.3, 9.3, 14.3), invention_a_minor (bars 5.3,
  9.3, 14.3). Cause: walking bass even quarters + soprano quarter-note
  figuration = lockstep. Fix: soprano needs denser sub-beat figuration
  in walking-bass sections.
- parallel_octave: gavotte_c_major (bar 19.1, B4/B3 → G4/G3). Cause:
  rhythm change exposed latent pitch alignment.

### Known genre gaps (from Plan 7)
- Sarabande: 2 cross-relations at minor-key boundaries; no beat-2 weight
- Invention: no imitative counterpoint (lead_voice not wired)
- Chorale: needs inner voices (out of scope)
- Fantasia/trio_sonata: not validated

## Key files
- workflow/bob.md — v4.0 with confidence tiers
- workflow/result.md — Plans 5–7 result
- completed.md — full history
