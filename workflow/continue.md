# Continue: Post-BV1 — Listening Gate Passed

## Current state (2026-02-13)

**BV1 complete and approved by ear.** Walking-bass phrases now use Viterbi
pathfinding against the soprano. Pillar/patterned textures unchanged.
Human verdict: "brilliant, not Bach yet but much closer."

## What to do next

Pick from remaining work. Priorities by likely musical impact:

1. **Dead code cleanup** — remove the walking branch from bass_writer.py.
   Quick housekeeping, no musical effect. Reduces bass_writer by ~300 lines.

2. **Accented neighbour fix** — cost function tweak in viterbi/costs.py.
   Small change, unlocks a class of idiomatic dissonance for soprano Viterbi.

3. **Motivic coherence** — cost function addition to echo leader material.
   Largest musical impact of the deferred items but also the most complex.

4. **BV2: pillar/patterned bass Viterbi** — extend Viterbi to gavotte A
   (half_bar), minuet (arpeggiated_3_4), sarabande (continuo_sustained).
   Requires chord-tone incentive costs or pattern-as-knot constraints.

5. **Subject development** — inversion, augmentation, stretto for invention.

## Recommendation

Dead code cleanup first (quick win), then accented neighbour fix (small,
testable), then decide between motivic coherence and BV2 based on what
sounds weakest after listening.
