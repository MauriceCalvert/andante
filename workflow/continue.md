# Continue

## Current state

Plan 4 (Rhythm Repair) complete. Plan 5 in progress.

### Plan 4 — complete
- Phase 4.1: Walking bass even quarter notes (removed select_cell)
- Phase 4.2: Soprano-aware cell selection verified (already wired)
- Phase 4.3: Pillar bass energetic cell guard added

### Plan 5 — in progress
- Phase 5.1: Audit complete. Boundaries already smooth. Minuet: zero
  boundaries above a fifth in either voice. Gavotte: one soprano
  (10st, D4→C5) and one bass (10st, A2→G3), not simultaneous.
- Phase 5.2: In progress in CC. The plan specified modifying
  planner/metric/pitch.py but CC found that degree_to_nearest_midi
  already does proximity-based placement and exit pitches already
  thread through compose_phrases. The fix may be a tighter
  tie-breaker, not a new mechanism.
- Phase 5.3: Not started (directional continuity).

### Known test failures (5, all from Plan 4.1)
- parallel_rhythm: gavotte_c_major (bar 15.3), gavotte_a_minor (bar 15.3),
  invention_c_major (bars 5.3, 9.3, 14.3), invention_a_minor (bars 5.3, 9.3, 14.3).
  Cause: walking bass even quarters + soprano quarter-note figuration = lockstep.
  Fix: soprano needs denser sub-beat figuration in walking-bass sections.
  Separate future brief, not part of Plans 4–7.
- parallel_octave: gavotte_c_major (bar 19.1, B4/B3 → G4/G3).
  Cause: rhythm change created different common onsets exposing latent
  pitch alignment. Separate fix needed in walking bass pitch logic.

### Recent change
bob.md updated to v4.0: added Confidence Tiers (high/medium/low) so
Bob flags score-reading inferences vs audible facts. Low-confidence
claims about tension, character, phrase feel are now marked as
hypotheses for the human listener to confirm.

## What to do next

Check workflow/result.md for Phase 5.2 outcome. If complete, evaluate
and proceed to 5.3. If 5.2 was a near-no-op (likely given the audit),
consider folding 5.3 or closing Plan 5 early.

## Plans

- plan4.md — complete
- plan5.md — in progress
- plan6.md — motivic return (next)
- plan7.md — additional genre validation

## Key files

- workflow/plan5.md — current plan
- workflow/bob.md — v4.0 with confidence tiers
- builder/bass_writer.py — Plan 4 rhythm fixes applied
- output/gavotte.note, output/minuet.note — current test output
