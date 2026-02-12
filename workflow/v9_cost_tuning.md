# V9 — Cost Function Tuning

Status: **COMPLETE** (V9a–V9d). Four iterations performed.

## Purpose

The Viterbi solver produces correct but bland counterpoint. The Bach
comparison (V7) quantifies the gap:

| Metric | Current | Bach baseline |
|--------|---------|---------------|
| Exact pitch match | 22.3% | 100% |
| Direction agreement | 34.9% | 100% |
| Strong-beat consonance | 71.8% | ~85% (Bach uses dissonance deliberately) |
| Mean absolute error | 3.4 semitones | 0 |

The solver is defensive — it avoids penalties rather than pursuing
musical goals. Bach's lines are shaped by rhetoric, harmonic function,
and motivic logic. The solver's lines are shaped by local optimisation
of a penalty function. Closing this gap requires changing what the
solver values, not how it searches.

## Root Cause Analysis

Six identified deficiencies in the current cost function, ordered by
likely musical impact:

### 1. Strong-beat dissonance is effectively forbidden

`dissonance_at_departure` returns 100.0 for strong-beat dissonance.
This blocks suspensions (the defining baroque dissonance) and accented
passing tones. Bach uses strong-beat dissonance freely — the 71.8%
consonance rate shows he's dissonant ~28% of the time on strong beats.

**What a musician does:** Plays a suspension (strong-beat dissonance
prepared by the same pitch on the preceding weak beat, resolved down by
step). Plays accented passing tones (strong-beat dissonance approached
and left by step in the same direction). Both are standard baroque
practice. The current cost makes them impossible.

**Fix direction:** Distinguish suspension (prepared + resolved by step
down) and accented passing tone (approached + left by step, same
direction) from unprepared dissonance. Suspensions should have near-zero
cost. Accented passing tones should cost less than the current 100.0.

### 2. No contour shaping (registral arc)

The cost function has no preference for overall melodic shape. It
optimises locally — each transition considers only the immediate
predecessor. A line that rises to a registral climax and then descends
(an arch) costs the same as one that meanders at a fixed pitch level.

**What a musician does:** Shapes each phrase as an arc — rising tension
toward a climax point (typically 60-75% through the phrase), then
descent. The climax is the registral high point in the soprano, the
low point in the bass.

**Fix direction:** Add a contour cost that rewards approaching a target
registral extreme at the appropriate phrase position. The target could
be derived from the corridor's available range (e.g., prefer higher
pitches mid-phrase, lower pitches near cadence for soprano).

### 3. Leaps are over-penalised

COST_STEP_FOURTH = 10.0, COST_STEP_FIFTH_PLUS = 18.0. These are high
relative to COST_STEP_SECOND = 0.0. Bach leaps deliberately for
emphasis — a leap followed by stepwise recovery is a fundamental
baroque gesture. The solver's cost structure makes any leap expensive,
producing lines that creep by step.

**What a musician does:** Leaps to a registral peak or to establish a
new register, then fills stepwise. A 4th leap is unremarkable; a 5th is
common; a 6th is expressive. Only 7ths and octaves are unusual in
stepwise counterpoint.

**Fix direction:** Reduce 4th and 5th costs. The leap_recovery_cost
already penalises un-recovered leaps — the step_cost shouldn't also
penalise the leap itself so heavily. Consider making leap cost
phrase-position-dependent (leaps cheaper mid-phrase, more expensive
near cadence where convergence is wanted).

### 4. Zigzag penalty discourages neighbour tones

COST_ZIGZAG = 4.0 penalises step-step reversals. But neighbour tones
(step up, step down, or vice versa) are idiomatic baroque ornamentation.
The penalty makes them as expensive as a small leap.

**What a musician does:** Uses upper and lower neighbour tones freely,
especially on weak beats. A semiquaver figure C-D-C-B-C is standard
diminution. The zigzag penalty discourages this.

**Fix direction:** Reduce or eliminate zigzag cost. The run_penalty
already prevents monotonous scales. Neighbour tones should be free.

### 5. No motivic coherence

The solver has no mechanism to echo or respond to the leader's melodic
material. It treats each transition independently. A line that
accidentally mirrors the leader's contour costs the same as one that
ignores it entirely.

**What a musician does:** Incorporates fragments of the subject (in
counterpoint), echoes intervallic patterns, or inverts the leader's
contour. This creates dialogue, not just counterpoint.

**Fix direction:** Add a contour-following or contour-inverting cost
component. Compare the follower's interval direction/size with the
leader's. Reward inversion (contrary contour) or exact echo (parallel
contour) depending on phrase position. This is the most complex
addition and should come last.

### 6. Conservative register usage

The spacing cost (IDEAL_SPACING_LOW=7, IDEAL_SPACING_HIGH=24) combined
with the step preference keeps the solver in a comfortable middle
register. Bach exploits the full range, using registral extremes for
rhetorical effect.

**What a musician does:** Uses registral height as expression. The
soprano's highest note is saved for the phrase's emotional peak. The
bass's lowest note grounds the cadence. Between these extremes, the
voices breathe — opening and closing their registral distance.

**Fix direction:** This is partially addressed by contour shaping (#2).
The spacing bounds may also need loosening. IDEAL_SPACING_HIGH=24 (two
octaves) could be 26-28 (two octaves + M2/M3).

## Methodology

V9 is iterative, not a single implementation task. Each cycle:

1. **Choose one deficiency** from the list above
2. **Draft a cost change** (new cost component or weight adjustment)
3. **Implement** (modify `viterbi/costs.py` only; possibly `pathfinder.py`
   if new state is needed)
4. **Run bach_compare** — check aggregate metrics. Expect exact match and
   direction agreement to rise. Consonance may fall (desired: Bach-like
   dissonance is better than sterile avoidance).
5. **Run pipeline** — generate gavotte and invention, listen to MIDI
6. **Bob evaluation** — does it sound more musical?
7. **Log results** — which weights changed, what metrics moved, what
   the ear says

If a change improves bach_compare but sounds worse to the ear, revert.
The ear overrides metrics.

## Suggested Order

1. **Zigzag reduction** (smallest change, most likely to help immediately)
2. **Leap cost rebalancing** (3rds and 4ths should be cheaper)
3. **Strong-beat dissonance: suspensions** (requires detecting preparation)
4. **Contour shaping** (new cost component)
5. **Motivic coherence** (most complex, largest architectural change)

Items 1-2 are weight adjustments only. Item 3 requires new logic in
`dissonance_at_departure`. Item 4 requires a new cost function. Item 5
may require new DP state (leader contour tracking), which changes
`pathfinder.py`.

## Constraints

- All changes in `viterbi/` only
- `test_brute` must pass after each change (optimality preserved)
- No changes to `soprano_writer.py`, `phrase_writer.py`, or
  `bass_writer.py`
- Each iteration is one brief to Claude Code
- Keep cost function additive (no multiplicative interactions)

## Success Criteria (end of V9)

No fixed numerical targets — this is iterative. Directional goals:

- Bach exact match rises from 22% toward 30%+
- Direction agreement rises from 35% toward 45%+
- Strong-beat consonance may fall to 65-70% (if the solver is using
  dissonance deliberately, this is an improvement)
- Generated MIDI sounds less mechanical and more directed to the ear
- Soprano lines have audible arch contours rather than meandering

## Baseline Snapshot

```
AGGREGATE  3175   22.3%  23.1%  23.1%  34.9%  42.8%  3.4   71.8%
           grid   exact  pc     iv     dir    mot    MAE   cons
```

Current cost weights (for rollback reference):
```
COST_STEP_UNISON      =  8.0
COST_STEP_SECOND      =  0.0
COST_STEP_THIRD       =  4.0
COST_STEP_FOURTH      = 10.0
COST_STEP_FIFTH_PLUS  = 18.0
COST_CONTRARY_BONUS   = -2.0
COST_OBLIQUE_BONUS    = -0.5
COST_SIMILAR_PENALTY  =  1.0
COST_PARALLEL_PERFECT = 25.0
COST_LEAP_NO_RECOVERY = 20.0
COST_ZIGZAG           =  4.0
COST_RUN_PENALTY      =  5.0
COST_PASSING_TONE     =  1.0
COST_HALF_RESOLVED    = 15.0
COST_UNRESOLVED_DISS  = 50.0
COST_CADENCE_BONUS    = -2.5
COST_CROSS_RELATION   = 30.0
COST_SPACING_TOO_CLOSE=  8.0
COST_SPACING_TOO_FAR  =  4.0
COST_PERFECT_ON_STRONG=  1.5
strong-beat dissonance = 100.0  (hardcoded in dissonance_at_departure)
```

## V9a Results — Zigzag Reduction and Leap Cost Graduation

### Changes Made

| Constant | Before | After |
|----------|--------|-------|
| COST_STEP_THIRD | 4.0 | 1.5 |
| COST_STEP_FOURTH | 10.0 | 5.0 |
| COST_STEP_FIFTH_PLUS | 18.0 (flat) | *replaced with graduated* |
| COST_STEP_FIFTH | — | 8.0 |
| COST_STEP_SIXTH | — | 12.0 |
| COST_STEP_SEVENTH | — | 20.0 |
| COST_STEP_OCTAVE | — | 25.0 |
| COST_STEP_BEYOND_OCTAVE_BASE | — | 25.0 |
| COST_STEP_BEYOND_OCTAVE_PER | — | 5.0 |
| COST_ZIGZAG | 4.0 | 1.0 |

### Bach Compare (V9a vs baseline)

```
              grid   exact  pc     iv     dir    mot    MAE   cons
Baseline      3175   22.3%  23.1%  23.1%  34.9%  42.8%  3.4   71.8%
V9a           3175   22.9%  24.0%  24.0%  34.3%  42.7%  3.4   74.4%
Delta                +0.6   +0.9   +0.9   -0.6   -0.1   0.0   +2.6
```

### test_brute

20/20 passed (5 beats, 20 trials). Optimality preserved.

### Bob's Observations

**Positive:**
- Neighbour-tone figures appear (gavotte bar 4 G#4 upper neighbour, invention bars 8-9 G#5 ornaments)
- Wider registral reach (invention soprano to B5, gavotte to G#5)
- Leaps used purposefully (invention bar 5: 4th leap to registral peak)
- No new jaggedness — leaps are followed by stepwise recovery

**Negative:**
- Gavotte bars 5-7: soprano trapped oscillating between C#4-D4-E4 for ~3 bars
- Invention bar 18: locked B4-A4 oscillation for full bar (8 notes)
- Oscillation worse than baseline — directly caused by COST_ZIGZAG reduction

### Chaz's Diagnosis

Oscillation is the predicted consequence of reducing COST_ZIGZAG from 4.0
to 1.0 without adding contour shaping. In sparse-knot regions (many grid
positions between knots), the solver finds oscillation optimal because no
cost component provides directional preference. The fix is contour shaping
(V9 item #4, deferred). The task anticipated this as Known Limitation #2.

### Acceptance Criteria

| Criterion | Result |
|-----------|--------|
| test_brute 5 20: 20/20 | **PASS** |
| Bach exact >= 20% | **PASS** (22.9%) |
| Bach direction: should rise | **MARGINAL FAIL** (34.3%, was 34.9%) |
| No new parallels | **PASS** |
| More variety, no jaggedness | **PASS** |

Direction agreement regression is -0.6pp, within noise. The oscillation
tendency likely contributes: alternating direction disagrees with Bach's
more directional lines. Contour shaping (V9b or later) should address both
oscillation and direction agreement.

## V9b Results — Contour Shaping (Registral Arc)

### Changes Made

| Constant | Value | Purpose |
|----------|-------|---------|
| COST_CONTOUR | 1.5 | Per scale-degree distance from contour target |
| ARC_PEAK_POSITION | 0.65 | Phrase fraction where arc peaks |
| ARC_SIGMA | 0.25 | Width of bell curve |
| ARC_REACH | 0.5 | How far toward range extreme (0=midpoint, 1=extreme) |

New function `contour_cost(curr_pitch, contour_target, key)` added to costs.py.
New function `compute_contour_targets(corridors, legal)` in pathfinder.py
precomputes one target pitch per beat using a Gaussian bell curve. Soprano-like
followers (avg legal pitch >= avg leader pitch) arc upward; bass-like arc downward.

### Bach Compare (V9b vs V9a vs baseline)

```
              grid   exact  pc     iv     dir    mot    MAE   cons
Baseline      3175   22.3%  23.1%  23.1%  34.9%  42.8%  3.4   71.8%
V9a           3175   22.9%  24.0%  24.0%  34.3%  42.7%  3.4   74.4%
V9b           3175   21.5%  23.3%  23.3%  33.5%  41.4%  4.0   73.0%
V9b delta            -1.4   -0.7   -0.7   -0.8   -1.3   +0.6  -1.4
(vs V9a)
```

All metrics regressed mildly vs V9a. The contour cost pulls pitches toward
range extremes at mid-phrase, diverging from where Bach places notes. The
MAE increase (+0.6 semitones) confirms the solver chooses pitches further
from Bach's. Direction agreement dropped 0.8pp — the fixed arc shape doesn't
match Bach's per-phrase variation (Known Limitation #1).

### test_brute

20/20 passed (5 beats, 20 trials). Updated test_brute.py to pass contour
targets through brute_force_cost for optimality consistency.

### Current cost weights (V9b)

```
COST_STEP_UNISON      =  8.0
COST_STEP_SECOND      =  0.0
COST_STEP_THIRD       =  1.5
COST_STEP_FOURTH      =  5.0
COST_STEP_FIFTH       =  8.0
COST_STEP_SIXTH       = 12.0
COST_STEP_SEVENTH     = 20.0
COST_STEP_OCTAVE      = 25.0
COST_BEYOND_OCT_BASE  = 25.0
COST_BEYOND_OCT_PER   =  5.0
COST_CONTRARY_BONUS   = -2.0
COST_OBLIQUE_BONUS    = -0.5
COST_SIMILAR_PENALTY  =  1.0
COST_PARALLEL_PERFECT = 25.0
COST_LEAP_NO_RECOVERY = 20.0
COST_ZIGZAG           =  1.0
COST_RUN_PENALTY      =  5.0
COST_PASSING_TONE     =  1.0
COST_HALF_RESOLVED    = 15.0
COST_UNRESOLVED_DISS  = 50.0
COST_CADENCE_BONUS    = -2.5
COST_CROSS_RELATION   = 30.0
COST_SPACING_TOO_CLOSE=  8.0
COST_SPACING_TOO_FAR  =  4.0
COST_PERFECT_ON_STRONG=  1.5
COST_CONTOUR          =  1.5  (NEW)
ARC_PEAK_POSITION     =  0.65 (NEW)
ARC_SIGMA             =  0.25 (NEW)
ARC_REACH             =  0.5  (NEW)
strong-beat dissonance = 100.0  (hardcoded)
```

### Bob's Observations

**Gavotte:**
- Bars 5-7: V9a oscillation (C#4-D4-E4 tight band) replaced by wide registral
  sweeps within each bar (D5→D4 drop, then rise). The tight oscillation is gone;
  each bar now has internal directional motion. Not a perfect arc across the
  whole phrase, but clearly better than meandering.
- Bar 12 monte peak at F#5 — the B section's registral high point. The line
  has a destination. The ascending monte sequence B4→D5→E5→F#5 creates audible
  rising shape.
- Bars 15-16: the soprano descends from F#5 through E5 → D5 → A4 after the
  peak. A settling gesture.
- Bars 18-19: late flourish C#5→E5→F#5 before the cadence.
- Bar 19→20 junction: tritone leap C#5→G4. Ugly. Not caused by contour.
- Bar 20: G4→F#4→E4→D4 stepwise descent. Clean final cadence on D4.

**Invention:**
- Bar 1: ascending arc D5→F#5 within the opening bar. Directional from beat 1.
- Bars 5, 12: A5 peaks (knot pitches) give the narratio and confirmatio their
  registral climaxes. The solver's path benefits from contour pull near these
  peaks.
- Bar 18: oscillation shifted from B4-A4 (V9a) to F#5-G5 (V9b). Same pattern
  but at the registral peak — reads as ornamentation around a climax rather
  than aimless wandering. Range D5-G5 (5 semitones) vs B4-A4 (2 semitones).
- Bar 19: G5→F#5→E5→D5 clean cadential descent. Conclusive.

### Chaz's Diagnosis

Bob's observation "wide registral sweeps within each bar" traces to the contour
target varying smoothly across the phrase while the solver must reconcile it
with step-preference and leap-recovery costs. The solver reaches toward the
contour target via short runs, then is pulled back by other costs, creating
per-bar arcs. A longer-range smoothing (phrase-level contour momentum) would
improve this but requires additional state.

Bob's "bar 18 oscillation at the peak" persists because COST_ZIGZAG=1.0 is
too weak to suppress step-step reversals. The contour cost (1.5/degree) shifts
the oscillation register upward but does not eliminate the oscillation pattern
itself. Anti-oscillation requires either raising COST_ZIGZAG (which suppresses
neighbour tones) or adding motivic coherence (V9 item #5).

Bach metric regression is consistent with Known Limitation #1: the fixed arc
shape (peak at 0.65, Gaussian bell) does not match Bach's per-phrase contour
variation. Bach's contour decisions depend on harmonic function, text, and
schema — information the solver doesn't have. The arc is a reasonable default
that improves directionality at the cost of some Bach agreement.

### Acceptance Criteria

| Criterion | Result |
|-----------|--------|
| test_brute 5 20: 20/20 | **PASS** |
| Bach direction: should rise from 34.3% | **FAIL** (33.5%, dropped 0.8pp) |
| Gavotte bars 5-6 oscillation reduced | **PASS** (tight oscillation → wide sweeps) |
| Soprano has audible phrase shape | **PASS** (monte peak F#5, invention A5 peaks) |
| No new faults from contour | **PASS** (faults are pre-existing) |

Direction agreement failed to rise. The fixed arc shape pulls in a consistent
direction that doesn't always agree with Bach's actual phrase-specific contour.
This was anticipated in Known Limitation #1. The musical improvement (wider
register, peak placement, oscillation at peak rather than mid-range) is audible
despite the metric regression.

## V9c Results — Strong-Beat Dissonance: Suspensions and Accented Passing Tones

### Changes Made

| Constant | Value | Purpose |
|----------|-------|---------|
| COST_SUSPENSION | 2.0 | Prepared dissonance resolving down by step |
| COST_ACCENTED_PASSING_TONE | 6.0 | Stepwise through-motion on strong beat |
| COST_UNPREPARED_STRONG_DISS | 50.0 | Unprepared strong-beat dissonance |
| (removed) hardcoded 100.0 | — | Replaced by classification above |

The strong-beat branch in `dissonance_at_departure` now classifies dissonance
into three categories instead of returning a flat 100.0:

1. **Suspension:** approach_pitch == pitch (prepared) AND departure is one
   scale step down (resolves down). Cost 2.0.
2. **Accented passing tone:** approached by step AND left by step, same
   direction. Cost 6.0.
3. **Unprepared:** everything else. Cost 50.0 (down from 100.0).

### Bach Compare (V9c vs V9b vs baseline)

```
              grid   exact  pc     iv     dir    mot    MAE   cons
Baseline      3175   22.3%  23.1%  23.1%  34.9%  42.8%  3.4   71.8%
V9a           3175   22.9%  24.0%  24.0%  34.3%  42.7%  3.4   74.4%
V9b           3175   21.5%  23.3%  23.3%  33.5%  41.4%  4.0   73.0%
V9c           3175   21.5%  23.2%  23.2%  33.2%  41.2%  3.9   73.2%
V9c delta            0.0    -0.1   -0.1   -0.3   -0.2   -0.1  +0.2
(vs V9b)
```

All metrics within noise of V9b. No regression beyond 2pp. Consonance barely
changed (+0.2pp) — the solver rarely exercises the new suspension/APT capability
because consonance (cost 0.0) remains cheaper than suspension (cost 2.0).

### test_brute

20/20 passed (5 beats, 20 trials). Optimality preserved.

### Current cost weights (V9c)

```
COST_STEP_UNISON      =  8.0
COST_STEP_SECOND      =  0.0
COST_STEP_THIRD       =  1.5
COST_STEP_FOURTH      =  5.0
COST_STEP_FIFTH       =  8.0
COST_STEP_SIXTH       = 12.0
COST_STEP_SEVENTH     = 20.0
COST_STEP_OCTAVE      = 25.0
COST_BEYOND_OCT_BASE  = 25.0
COST_BEYOND_OCT_PER   =  5.0
COST_CONTRARY_BONUS   = -2.0
COST_OBLIQUE_BONUS    = -0.5
COST_SIMILAR_PENALTY  =  1.0
COST_PARALLEL_PERFECT = 25.0
COST_LEAP_NO_RECOVERY = 20.0
COST_ZIGZAG           =  1.0
COST_RUN_PENALTY      =  5.0
COST_PASSING_TONE     =  1.0
COST_HALF_RESOLVED    = 15.0
COST_UNRESOLVED_DISS  = 50.0
COST_CADENCE_BONUS    = -2.5
COST_CROSS_RELATION   = 30.0
COST_SPACING_TOO_CLOSE=  8.0
COST_SPACING_TOO_FAR  =  4.0
COST_PERFECT_ON_STRONG=  1.5
COST_CONTOUR          =  1.5
ARC_PEAK_POSITION     =  0.65
ARC_SIGMA             =  0.25
ARC_REACH             =  0.5
COST_SUSPENSION       =  2.0  (NEW)
COST_ACCENTED_PASSING_TONE = 6.0  (NEW)
COST_UNPREPARED_STRONG_DISS = 50.0  (NEW, replaces hardcoded 100.0)
```

### Dissonance Classification Counts

| Type | Gavotte (viterbi) | Gavotte (knots) | Invention (viterbi) | Invention (knots) |
|------|------------------|-----------------|--------------------|--------------------|
| Suspension | 0 | 0 | 0 | 0 |
| Accented PT | 3 | 2 | 0 | 1 |
| Unprepared | 3 | 1 | 1 | 3 |

The solver generates 3 viterbi-chosen accented passing tones in the gavotte
(bars 11, 12, 14 beat 3). Zero suspensions in either piece.

### Bob's Observations

**Gavotte:**
- B section (bars 11-14) has audible accented passing tones — the soprano steps
  through dissonance on strong beats rather than dodging around it. These give the
  monte/fenaroli sequence a bit of harmonic grit absent from the A section.
- Bar 12 peak at F#5 retained from V9b (contour shaping).
- Bar 20 beat 3: ugly tritone leap C#5→G4, pre-existing cadence writer fault.
- No suspensions. No moment of held friction resolving by step. The defining
  baroque dissonance device is still absent.

**Invention:**
- One accented passing tone (bar 9 beat 1: D5 over G#3). Fleeting.
- Confirmatio (bars 10-16) entirely consonant on strong beats — safe and sterile.
- Bar 18 oscillation persists from V9a/V9b.
- No suspensions.

### Chaz's Diagnosis

The accented passing tone classification is correct and the solver exercises it:
3 viterbi-generated APTs in the gavotte where the old flat 100.0 would have
blocked stepwise through-motion on strong beats.

Suspensions do not appear because the combined cost of preparation + suspension
exceeds the cost of any consonant alternative:

- Preparation requires approach_pitch == pitch → COST_STEP_UNISON = 8.0
- Suspension dissonance → COST_SUSPENSION = 2.0
- Total: ~10.0 for the suspension path
- Consonant alternative: step to nearby consonant pitch → 0.0 + 0.0 = 0.0

The 10.0 gap means the solver only places suspensions when ALL consonant pitches
within reach cost >10.0 from other dimensions. In diatonic scales with 7 pitch
classes per octave, there are usually consonant options within a step.

The bottleneck is COST_STEP_UNISON = 8.0, not COST_SUSPENSION = 2.0. A future
V9d could add a preparation discount (negative cost when unison specifically
sets up a suspension) to bridge this gap without encouraging general stasis.

Unprepared strong-beat dissonance is now 50.0 (was 100.0). This slightly relaxes
the solver's path choices around dissonant knots (anchor pitches set by the metric
layer), but the effect is small since knot pitches are fixed constraints.

### Acceptance Criteria

| Criterion | Result |
|-----------|--------|
| test_brute 5 20: 20/20 | **PASS** |
| Bach consonance: should fall from 74.4% toward 72% | **NOT MET** (73.2%, +0.2pp vs V9b) |
| Bob hears at least one convincing suspension | **NOT MET** (zero suspensions; 3 APTs instead) |
| No false suspensions | **PASS** (no unprepared dissonance classified as suspension) |
| No regression beyond 2pp in bach_compare | **PASS** (all metrics within 0.3pp of V9b) |

Two acceptance criteria not met. Root cause identified: COST_STEP_UNISON = 8.0
makes the preparation stage of a suspension prohibitively expensive. The
classification logic is correct (test_brute confirms optimality) but the cost
landscape does not incentivise the solver to hold pitches across strong beats.

The accented passing tone capability IS exercised (3 instances in gavotte). The
code change is correct and enables the right distinctions; the solver needs
a follow-up cost adjustment (preparation discount or unison cost reduction in
suspension context) to actually produce suspensions.

## V9d Results — Anti-oscillation: Pitch Return Penalty

### Changes Made

| Constant | Value | Purpose |
|----------|-------|--------|
| COST_PITCH_RETURN | 4.0 | Penalise return to pitch two steps back |

New function `pitch_return_cost(prev_prev_pitch, curr_pitch)` added to costs.py.
Wired into `transition_cost` as additive term with breakdown key `"pitch_ret"`.

### Bach Compare (V9d vs V9c)

```
              grid   exact  pc     iv     dir    mot    MAE   cons
V9c           3175   21.5%  23.2%  23.2%  33.2%  41.2%  3.9   73.2%
V9d           3175   21.8%  24.1%  24.1%  33.3%  41.8%  4.0   76.7%
V9d delta            +0.3   +0.9   +0.9   +0.1   +0.6   +0.1  +3.5
```

Consonance rose 3.5pp. All other metrics stable or mildly improved.

### test_brute

20/20 passed.

### Bob's Observations

2-note oscillation in invention bars 6 and 9 suppressed. Single neighbour
tones survive. 3-note cycles (period-3) remain in invention bar 19, gavotte
bars 18–19. These sound mechanical but are less severe than the 2-note case.

### Acceptance Criteria

| Criterion | Result |
|-----------|--------|
| test_brute 5 20: 20/20 | **PASS** |
| Bach compare: no regression >2pp | **PASS** |
| Bars 6, 9: <5 consecutive reversals | **PASS** |
| No new fault types | **PASS** |
| 3-note oscillation | **OPEN** (deferred to harmonic layer) |

## V9 Final Summary

### Aggregate Progress

```
              grid   exact  pc     iv     dir    mot    MAE   cons
Pre-V9        3175   22.3%  23.1%  23.1%  34.9%  42.8%  3.4   71.8%
Post-V9       3175   21.8%  24.1%  24.1%  33.3%  41.8%  4.0   76.7%
```

Consonance improved +5pp. Pitch class match +1pp. Direction agreement
dropped 1.6pp (fixed contour arc diverges from Bach's per-phrase variation).
MAE rose 0.6 (contour pulls toward range extremes).

### Final Cost Weights (V9d)

```
COST_STEP_UNISON      =  8.0
COST_STEP_SECOND      =  0.0
COST_STEP_THIRD       =  1.5
COST_STEP_FOURTH      =  5.0
COST_STEP_FIFTH       =  8.0
COST_STEP_SIXTH       = 12.0
COST_STEP_SEVENTH     = 20.0
COST_STEP_OCTAVE      = 25.0
COST_BEYOND_OCT_BASE  = 25.0
COST_BEYOND_OCT_PER   =  5.0
COST_CONTRARY_BONUS   = -2.0
COST_OBLIQUE_BONUS    = -0.5
COST_SIMILAR_PENALTY  =  1.0
COST_PARALLEL_PERFECT = 25.0
COST_LEAP_NO_RECOVERY = 20.0
COST_ZIGZAG           =  1.0
COST_RUN_PENALTY      =  5.0
COST_PASSING_TONE     =  1.0
COST_HALF_RESOLVED    = 15.0
COST_UNRESOLVED_DISS  = 50.0
COST_CADENCE_BONUS    = -2.5
COST_CROSS_RELATION   = 30.0
COST_SPACING_TOO_CLOSE=  8.0
COST_SPACING_TOO_FAR  =  4.0
COST_PERFECT_ON_STRONG=  1.5
COST_CONTOUR          =  1.5
ARC_PEAK_POSITION     =  0.65
ARC_SIGMA             =  0.25
ARC_REACH             =  0.5
COST_SUSPENSION       =  2.0
COST_ACCENTED_PASSING_TONE = 6.0
COST_UNPREPARED_STRONG_DISS = 50.0
COST_PITCH_RETURN     =  4.0
```

### What V9 Achieved

1. **V9a** — Freed neighbour tones (zigzag 4.0→1.0) and graduated leap costs
2. **V9b** — Registral arc (contour shaping, phrase-level melodic direction)
3. **V9c** — Strong-beat dissonance classification (suspensions/APTs enabled)
4. **V9d** — Anti-oscillation (pitch return penalty)

### What V9 Did Not Achieve

1. **Suspensions** — classification works but cost landscape doesn't incentivise
   preparation (COST_STEP_UNISON too high). Needs preparation discount.
2. **Motivic coherence** — not attempted. Needs harmonic context first.
3. **Period-3 oscillation** — 3-note cycles evade 2-step lookback. Expect
   harmonic layer to suppress as side effect.
4. **Bach direction agreement** — regressed 1.6pp. Fixed arc shape doesn't
   match Bach's per-phrase contour variation.
