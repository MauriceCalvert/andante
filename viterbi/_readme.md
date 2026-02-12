# Viterbi: Melodic Line Drawing Through Structural Anchors

## Origin

This document captures an architectural insight that emerged from debugging
Phase 16h (select_best_pitch). The immediate problem was cross-bar pitch
repetition failures. The root cause was deeper: span-local generation
cannot see across span boundaries, and every fix adds complexity without
reducing it. The conclusion: spans are the wrong decomposition.

## The Problem with Spans

A "span" is the gap between two consecutive structural tones. The system
chops the phrase at structural tones, fills each gap as an independent
subproblem (via FillStrategy.fill_span), then stitches the results together.

This creates three checking sites that all evaluate roughly the same
constraints with slightly different inputs and exemption rules:

1. `_check_figure_pitches` in diminution.py — checks within a figure
2. `_score_pitch` in pitch_selection.py — scores candidates in stepwise fallback
3. `audit_voice` in voice_writer.py — post-hoc detection over finished notes

Each time a boundary issue surfaces, someone bolts another check onto one
of these sites. The sites diverge. Parameters accumulate. Context objects
grow. The isolation that spans were supposed to provide is illusory — the
strategy needs nearly all the information it would have in a single-pass
generator, accessed through a more complicated interface.

The trajectory is clear: it only gets worse.

## Why Spans Are Wrong

A baroque musician filling in ornamental notes between structural tones
does not think span-by-span. They draw one continuous line through the
whole phrase. They know the entire skeleton ahead, they know what they
just played, and they generate note by note with the full picture.

A span boundary is an implementation artefact. A phrase boundary is a real
musical event — a cadence, a breath. Cross-phrase continuity is not
mandatory because the end of a phrase is where breathing happens. But
within a phrase, the line is continuous.

The structural tones within a phrase are waypoints in a single melodic
line, not endpoints of separate subproblems.

## The Spline Metaphor

Not literal splines on MIDI pitch (that gives a smooth curve hitting no
scale degrees). But the properties of splines are precisely what the
generator needs:

- **Passes through control points.** Non-negotiable. Structural tones are
  knots.

- **Influenced by points ahead, not just behind.** A cubic spline at any
  position depends on the surrounding knots. The generator at any note
  should feel the pull of the next anchor.

- **Smoothness as default, angularity as choice.** A spline is smooth
  unless you force a discontinuity. The melodic line is stepwise unless
  there's a musical reason to leap.

- **Local control, global shape.** Moving one knot changes the curve
  nearby, not everywhere. Changing one structural tone reshapes the
  approach and departure, not the whole phrase.

- **Momentum.** A line moving upward wants to keep moving upward. Changing
  direction costs energy. This is exactly what step recovery and
  consecutive leap rules express — they're properties of a line with
  momentum.

- **Anticipation.** When drawing a line toward a point, you adjust your
  approach well before arrival. If the next anchor is a fifth below, you
  don't wait until one note before it to start descending — you begin
  curving toward it.

- **Texture as quality of the line.** Smooth (stepwise), angular (leaps),
  ornamental (turns, neighbour notes) — these aren't different strategies
  plugged into different spans. They're qualities of the same line at
  different points. Near phrase start: stable. In the middle: exploratory.
  Approaching cadence: tightening, converging.

## Voice Ordering: Leader and Follower

### The problem

Two voices need surfaces drawn through their skeletons. Each voice's
surface affects what the other voice can do (counterpoint intervals). They
cannot be drawn independently without producing collisions, and drawing
both simultaneously is intractable.

### The solution: sequential generation

One voice is drawn first (the **leader**). Its finished surface becomes
fixed terrain. The other voice (the **follower**) is drawn second, with
the leader's complete surface as read-only context.

The pen function is identical for both. The only difference is the richness
of the counterpoint context: the leader sees the other voice's skeleton;
the follower sees the other voice's finished surface.

### Who leads is determined by style and phrase

- **Galant style:** Bass always leads. It defines the harmony (Principle 4).
  The soprano follows, placing ornaments against the bass's realised line.

- **Counterpoint (inventions, fugues):** The voice carrying the subject
  leads for that phrase. The other voice follows with full visibility of
  the subject's surface. Leadership alternates phrase by phrase as the
  subject moves between voices.

This decision is made by the rhetorical/structural layer, long before the
pen starts. It is metadata attached to the phrase, not a runtime choice.

### The follower advantage

The follower has a harder job (more constraints) but better information
(the leader's actual notes, not just its skeleton). This asymmetry is
musically correct: the follower is the voice writing counterpoint. The
leader draws freely; the follower responds.

## Corridors: The Soprano Constrains the Bass

### The key insight

Once the leader's surface is complete, it generates a **corridor map** for
the follower. At every grid position, the leader's pitch determines which
follower pitches produce acceptable intervals:

- **Strong beats:** consonances only (3rds, 5ths, 6ths, octaves) unless
  a suspension is prepared and resolved.
- **Weak beats:** consonances plus stepwise dissonances (passing tones,
  neighbour tones).

This corridor map is fully known before the follower's pen starts. It is
a precomputed lookup table, not a runtime calculation.

### What corridors buy

The follower's problem becomes: draw a smooth curve through these knots
that stays inside these corridors. This is **pathfinding**, not greedy
note-by-note selection.

- The knots are waypoints the path must hit.
- The corridors are walkable terrain.
- The cost function encodes musical preferences (stepwise motion, contrary
  motion, sixths resolving to octaves, chromatic approach near cadences).
- The solver finds the globally optimal line, not a locally greedy one.

### Unlimited lookahead

Because the leader's surface and the follower's knots are both fully known,
the follower has unlimited lookahead within the phrase. This is free — it's
just data that already exists. The entire phrase is a solvable constraint
satisfaction problem with known geometry.

## Why Pathfinding Dissolves the Original Problems

Every concern raised about the pen model is answered by the corridor +
pathfinding framing:

- **Can the pen reach the next anchor on time?** The solver guarantees it
  or proves it impossible before placing a single note.

- **Close anchors (one beat, large interval)?** Trivial path, possibly a
  forced leap. The solver finds it without special-case logic.

- **Far anchors, small interval?** The corridors supply direction where
  momentum alone couldn't. The walkable terrain narrows the options.

- **Leap recovery painting into a corner?** The solver sees the whole path.
  It never commits to a leap whose forced recovery note falls outside the
  corridor. The three-note obligation (leap → recovery step) is evaluated
  as a unit, not note by note.

- **Gestures with multi-note commitments (suspensions, passing tones)?**
  These are path segments the solver evaluates whole, verifying every note
  in the gesture is corridor-admissible before committing to the first.

- **Too many options between distant anchors?** The cost function
  discriminates. Prefer stepwise, prefer contrary motion to the leader,
  prefer intervals that create forward-driving tension (6ths → octaves).
  The solver picks the best path, not a random walk.

## Musical Content Lives in the Cost Function

The counterpoint rules — what makes the output music rather than legal
notes — are encoded as costs, not as special-case checks:

- Stepwise motion: low cost.
- Contrary motion to the leader: low cost.
- Parallel motion: moderate cost (acceptable, not preferred).
- Sixths resolving outward to octaves: low cost (creates forward motion).
- Chromatic approach to cadential target: low cost at high phrase position,
  high cost at phrase opening (Principle 8: emphasis requires contrast).
- Consecutive same-direction leaps: high cost.
- Leap without step recovery: very high cost (or hard constraint).

Every musical preference becomes a weight. The solver balances them all
simultaneously rather than applying them as sequential filters.

## Two Position Parameters

The pen (or solver) operates with two progress parameters:

1. **Local parameter (0→1):** progress from the current anchor toward the
   next anchor. Governs how strongly the target pulls — ornamental freedom
   near 0, directed approach near 1.

2. **Global parameter (0→1):** progress from phrase start to cadence.
   Governs phrase-arc behaviour — stable opening, exploratory middle,
   cadential tightening. Modulates the cost function (e.g., chromaticism
   costs less as the global parameter approaches 1).

Together they give the solver the same context a musician uses: where am I
going next, and where am I in the larger phrase?

## What This Eliminates

- `SpanBoundary`, `SpanResult`, `SpanMetadata` and all subtypes
- `FillStrategy` protocol
- `_check_figure_pitches` (separate figure-level checking)
- `_score_pitch` as a separate fallback-path scorer
- `audit_voice` as a load-bearing wall (becomes genuinely post-hoc safety net)
- The entire category of cross-span boundary problems
- Three-way constraint checking duplication with diverging exemptions
- The accumulating parameter-threading through successive phases

## What Survives

- `select_best_pitch` / `_score_pitch` logic — absorbed into the cost
  function of the pathfinder
- Shared counterpoint functions in `counterpoint.py` — called from the
  corridor builder and cost function
- Diminution tables as vocabulary of melodic gestures (candidate path
  segments, not span-fillers)
- `validate_voice` — hard invariant checks (range, duration, gaps)
- `audit_voice` — as a safety net, not a load-bearing wall

## What This Costs

Phases 16c through 16h become scaffolding for the wrong building. The
type infrastructure (5 phases), the FillStrategy protocol, the span
iteration — all replaced by a simpler architecture.

## Theoretical Warrant

The idea has deep roots:

**Schenker (1920s-1930s):** His entire analytical framework is built on
this principle in reverse — take a finished piece and reduce it to its
skeleton (the Ursatz), showing how the surface melody is an elaboration
of structural tones through passing notes, neighbour tones, and
diminutions. The generative inverse — surface from skeleton — is what
we're proposing.

**WuYun (Zhang et al., 2023):** A two-stage skeleton-guided melody
generation architecture. First generates structurally important notes to
construct a melodic skeleton, then infills with decorative notes. But
still uses two separate stages — skeleton then fill.

**Small Tunes Transformer (Lv et al., 2025):** Explores macro/micro-level
hierarchies for skeleton-conditioned melody generation. Same two-stage
decomposition.

**ProGress (2025):** Uses Schenkerian prolongation explicitly in a
generative framework, fusing phrases based on sampled Schenkerian
structure.

**The gap:** All existing systems treat skeleton-to-surface as a two-stage
pipeline. None formulates the surface generation as a pathfinding problem
through corridors defined by a leader voice's finished surface, with full
lookahead and a cost function encoding musical preferences. The existing
computational work validates the skeleton-first principle but inherits the
span-filling decomposition.

The architectural insight — that the follower voice's generation is a
constrained shortest-path problem through interval corridors, not a
sequential fill — appears to be novel.

## Open Questions

1. **Which pathfinding algorithm?** The grid is discrete (scale degrees ×
   grid positions). The corridors and knot constraints make it a
   constrained shortest-path problem. Candidates: Dijkstra, A*, dynamic
   programming, beam search. Graph size and cost function complexity will
   determine the right choice.

2. **How do diminution gestures interact with pathfinding?** Gestures are
   multi-note path segments. The solver could enumerate gesture-level
   edges (each gesture is one edge connecting its entry state to its exit
   state) rather than note-level edges. This keeps the vocabulary without
   reimposing span boundaries, but the graph structure changes.

3. **Leader pen: pathfinding or greedy?** The leader has no corridors (only
   a skeleton to see). Is its problem simple enough for a greedy forward
   pass, or does it also benefit from pathfinding through its own knots?

4. **Cost function tuning.** The weights encoding musical preferences will
   need calibration. How to validate them without a trained ear in the
   loop? Bob-style score-reading of the .note output is the current best
   proxy.

5. **Cross-phrase continuity.** Between phrases, continuity is nice but not
   mandatory. Should the solver accept a starting pitch constraint from
   the previous phrase's ending pitch, or treat each phrase as independent?

## Status

Design phase. The concept has survived initial tyre-kicking. The corridor
+ pathfinding framing resolves the problems identified with both the span
architecture and the naive pen-forward-pass approach.

Next steps:

1. Investigate pathfinding algorithms suited to the grid structure
2. Design the corridor data structure
3. Design the cost function (map existing counterpoint rules to weights)
4. Determine gesture-level vs note-level graph edges
5. Prototype on a single phrase
6. Write the CC brief for implementation
7. Retire span infrastructure

## Phases Affected

- 16c (voice writer types) — SpanBoundary, SpanResult, SpanMetadata, FillStrategy retire
- 16d (voice writer pipeline) — write_voice rewritten as corridor + pathfinder
- 16e (DiminutionFill strategy) — replaced by cost-function-guided pathfinder
- 16f (wiring) — soprano_writer simplified
- 16g (figure checks) — _check_figure_pitches eliminated
- 16h (select_best_pitch) — logic absorbed into pathfinder cost function
