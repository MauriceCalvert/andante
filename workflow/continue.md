# Continue: Post-Viterbi — Harmonic Rhythm Layer

## Current state (2026-02-12)

**V9 complete (V9a–V9d).** Cost function now has: graduated leap costs,
contour shaping (registral arc), strong-beat dissonance classification
(suspension/APT/unprepared), pitch return penalty (anti-oscillation).

Bach comparison after V9d:
```
              grid   exact  pc     iv     dir    mot    MAE   cons
Baseline      3175   22.3%  23.1%  23.1%  34.9%  42.8%  3.4   71.8%
V9d           3175   21.8%  24.1%  24.1%  33.3%  41.8%  4.0   76.7%
```

Consonance improved +5pp. Direction agreement dropped ~1.5pp (contour arc
pulls in fixed directions that don't always match Bach). Exact match stable.
Musical quality improved: lines have registral shape, accented passing tones
appear, 2-note oscillation suppressed.

**Known open issues:**
- 3-note cycles (period-3 oscillation) evade the 2-step lookback. Visible
  in invention bar 19, gavotte bars 18–19. Expect the harmonic layer to
  suppress these as a side effect (chord tones become attractive, cycling
  between non-chord tones becomes expensive).
- Zero suspensions. COST_STEP_UNISON = 8.0 makes preparation too expensive.
  A preparation discount could fix this but is lower priority than harmonic
  awareness.
- Motivic coherence (echoing leader material) not addressed. Deferred
  indefinitely — needs harmonic context first.

## What exists

### Viterbi solver (`\viterbi`)

Proven by brute-force test. Wired into soprano generation for galant phrases
(V4) and invention follower phrases where bass leads (V6). Cost function is
additive with 12 components: step, motion, leap recovery, zigzag, run,
dissonance (3-way strong-beat classification), phrase position, contour,
cross-relation, spacing, interval quality, pitch return.

### Generation order (galant phrases)

Structural soprano skeleton → bass against skeleton → Viterbi soprano against
finished bass. Cadential and imitation phrases unchanged.

## Next: Harmonic Rhythm Layer

The solver's biggest gap is harmonic ignorance. It knows which pitches are
diatonic and which intervals are consonant with the leader, but it doesn't
know what chord is in effect at any given beat. This means:
- It can't distinguish chord tones from passing tones (except by consonance
  with the leader, which is a subset of harmonic awareness)
- It can't prefer chord-tone arrivals on strong beats
- It can't shape passing motion between chord tones
- Aimless cycling persists because all diatonic pitches cost the same

The harmonic rhythm layer sits between L4 (metric planning) and surface
generation. It provides a per-beat chord grid that the solver can use as
additional cost context.

See `workflow/todo.md` for the deferred item description.
