# Design Document: CP-SAT Subject Generation

## Status

Implemented and live. CP-SAT generator wired into pitch_generator.py
as of 2026-02-23. Old exhaustive enumerator is dead code.

## Problem Statement

The current subject generator uses exhaustive enumeration: it generates
every possible pitch-interval sequence of length N, applies hard
constraints as pruning predicates during recursion, scores the survivors,
then filters post-hoc for stretto compatibility. The stretto filter
rejects 99.86% of candidates. At 9 notes the enumeration crashes.

This is architecturally backwards. Stretto compatibility — the property
that a subject sounds consonant against a delayed copy of itself — is
the most restrictive constraint and should govern construction, not act
as a sieve on an ocean of candidates that mostly fail.

## Goal

Replace the enumerate-then-filter pipeline with a constraint-satisfaction
approach using Google OR-Tools CP-SAT. Stretto consonance becomes a
built-in construction constraint. Every candidate the solver produces is
stretto-ready by definition. Soft scoring criteria (climax position,
leap placement, tension arc) are applied as a Python post-filter on the
feasible set.

The external interface (`select_subject`, `select_diverse_subjects`)
does not change. The reform is internal to the generation pipeline.


## Background

### What a fugue subject needs

A fugue subject is a short melody (5–10 notes, typically 2–3 bars) that
must work in *stretto*: two voices play the same subject overlapping in
time, offset by k notes. At every simultaneous sounding, the vertical
interval must be consonant. This is a hard combinatorial constraint
because the semitone value of a degree-space interval depends on the
mode and on the starting position within the scale.

### Current pipeline

1. **Pitch generation** (`pitch_generator.py`): Exhaustive enumeration
   of interval sequences `iv[0..N-2]` in [-5, +5]\{0}. Cumulative
   pitches from degree 0. Hard constraints prune during recursion:
   final in {0, 2, 4}; range in [4, 11]; step fraction >= 50%;
   large leaps <= 4; same-sign run <= 5; pitch frequency <= 3;
   pitches in [-7, +7].

   Scored on: signature leap placement (25%), leap recovery (20%),
   stepwise run penalty (20%), interval variety (15%), climax
   position (20%), direction-change bonus (5%).

2. **Duration generation** (`duration_generator.py`): Independent
   bar-fill enumeration, scored for rhythmic character. Best duration
   per note-count paired with each pitch sequence.

3. **Selection** (`selector.py`): Combined score (50% pitch + 50%
   duration), quality floor (85% of best), stretto evaluation at all
   offsets via `stretto_constraints.py`, zero-viable rejection,
   greedy max-min Hamming diversity selection.

4. **Melodic validation** (`validator.py`): MIDI-space checks: no
   melodic tritones, no consecutive same-direction leaps, no tritone
   outlines over 4-note spans.

### Stretto evaluation

`stretto_constraints.py` works in MIDI semitone space with real rhythms.
Per offset: builds slot-level note map, identifies check points at note
onsets, classifies beats as strong/weak from metre tables.

- **Strong beats**: interval (mod 12) in {0, 3, 4, 7, 8, 9} (P4
  excluded — dissonant above bass in two-voice texture).
- **Weak beats**: tritone (6) fatal; other dissonance costs
  proportional to collision duration; P4 permitted.
- Viable if no strong-beat dissonance, no weak-beat tritone,
  consonance ratio > 0.6.

Score combines viable count (50%), tightness (30%), cost (20%).

### Why enumeration fails at scale

Interval alphabet |{-5..+5}\{0}| = 10. For 9 notes: 10^8 = 100M raw
candidates. Stretto filtering is the bottleneck. Prototype confirms:
7 notes / k=3 → 1,530 solutions in 4s; 8 / k=4 → 4,120 in 22s;
9 / k=4 → crash.

The key insight: we don't need all solutions. We need a few hundred
good ones, stretto-ready by construction.


## Proposed Architecture

```
  ┌────────────────────┐
  │  CP-SAT Model      │
  │  Hard constraints:  │
  │   melodic + stretto │
  │  Automaton: runs,   │
  │   leap recovery     │
  └─────────┬──────────┘
            │ solve (N solutions, random restarts)
  ┌─────────▼──────────┐
  │  Feasible set      │
  │  (stretto-ready,   │
  │   melodically       │
  │   valid)            │
  └─────────┬──────────┘
            │ MIDI validation post-filter
            │ Python scoring (existing)
  ┌─────────▼──────────┐
  │  Ranked pool       │
  └─────────┬──────────┘
            │ diversity selection (existing selector.py)
  ┌─────────▼──────────┐
  │  Final subjects    │
  └────────────────────┘
```

### Phase 1: Even durations

All notes have equal duration. Stretto offset k notes means positions i
and i+k always overlap. Duration assignment happens after pitch
selection; existing duration generator unchanged.

### Phase 2: Joint pitch-duration (future, deferred)


## CP-SAT Model Specification

### Variables

```
pitch[i]  : IntVar in [-7, +7]     i = 0..N-1    (degrees from tonic)
iv[i]     : IntVar in [-5, +5]     i = 0..N-2    (intervals)
abs_iv[i] : IntVar in [0, 5]       i = 0..N-2    (absolute intervals)
```

### Linking constraints

```
pitch[0] == 0
pitch[i+1] == pitch[i] + iv[i]     for all i
iv[i] != 0                          for all i
AddAbsEquality(abs_iv[i], iv[i])   for all i
```

### Melodic hard constraints

**Allowed finals** — parameterised, not hardcoded:
```
pitch[N-1] in allowed_finals       default {0, 2, 4}
```
Encoded via `AddAllowedAssignments`. The set is a parameter to the model
builder, allowing degree 4 (dominant) for minor-key open subjects.

**Pitch range:**
```
pitch_max - pitch_min in [4, 11]
```
Via `AddMinEquality`, `AddMaxEquality` over the pitch array.

**Step fraction:**
```
sum(is_step[i]) >= ceil(0.5 * (N-1))
```
Where `is_step[i]` ↔ `abs_iv[i] <= 1`.

**Large leaps:**
```
sum(is_large[i]) <= 4
```
Where `is_large[i]` ↔ `abs_iv[i] >= 3`.

**Same-sign run** — via `AddAutomaton`:

The same-sign constraint and leap recovery are encoded as a finite state
machine over the interval sign sequence. This moves melodic logic into
the solver's propagation engine rather than post-filtering.

States: `S` (start), `U1`–`U5` (consecutive up), `D1`–`D5` (consecutive
down). A 6th consecutive same-sign interval transitions to no state
(dead). The automaton input alphabet maps each `iv[i]` to a sign token:

```
sign[i] = 0 if iv[i] < 0, 1 if iv[i] > 0
```

Transition table (11 states, 2 inputs):

| State | Input 0 (down) | Input 1 (up) |
|-------|----------------|--------------|
| S     | D1             | U1           |
| U1    | D1             | U2           |
| U2    | D1             | U3           |
| U3    | D1             | U4           |
| U4    | D1             | U5           |
| U5    | D1             | (dead)       |
| D1    | D2             | U1           |
| D2    | D3             | U1           |
| D3    | D4             | U1           |
| D4    | D5             | U1           |
| D5    | (dead)         | U1           |

All states except dead are accepting. This is compact (11 states, 22
transitions) and propagates early in the search.

To encode the sign extraction, define `sign[i]` as a BoolVar constrained
by `iv[i] > 0` (since `iv[i] != 0`, positive ↔ up, non-positive ↔ down).

**Pitch frequency:**
```
count(pitch[i] == d) <= 3    for each d in [-7, +7]
```
Encoded via per-value Boolean sums. Small domain (15 values) makes this
cheap.

### Mod-7 lookup table

The domain [-7, +7] maps to exactly 15 pitch values. Rather than using
`AddModuloEquality` (which has overhead for negative dividends), use a
precomputed constant array and `AddElement`:

```python
MOD7_TABLE = [0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0]
# Index: pitch[i] + 7  (shifts [-7,+7] to [0,14])

idx[i] = model.NewIntVar(0, 14, ...)
model.Add(idx[i] == pitch[i] + 7)
model.AddElement(idx[i], MOD7_TABLE, start_mod7[i])
```

This replaces all modular arithmetic with a single table lookup per
pitch variable.

### Stretto consonance constraint

For primary offset k notes (even durations):

```
For each overlap position i = 0..N-1-k:
    (start_mod7[i], pitch[i+k] - pitch[i]) must be in consonant_pairs
```

**Table construction** — precomputed per mode:

```python
def build_consonant_pairs(
    scale_semitones: tuple[int, ...],
    consonance_set: frozenset[int],
) -> list[tuple[int, int]]:
    pairs = []
    for start in range(7):
        for span in range(-14, 15):
            oct, step = divmod(start + span, 7)
            st = abs(oct * 12 + scale_semitones[step]
                     - scale_semitones[start]) % 12
            if st in consonance_set:
                pairs.append((start, span))
    return pairs
```

Per overlap position, post:
```
AddAllowedAssignments([start_mod7[i], degree_span[i]], pairs)
```

The consonance set varies by beat strength. With even durations, beat
positions are fixed. Each overlap position uses the appropriate table:

| Beat type | Consonance set (mod 12) | P4 |
|-----------|------------------------|----|
| Strong    | {0, 3, 4, 7, 8, 9}    | excluded |
| Weak      | {0, 3, 4, 5, 7, 8, 9} | included |

Tritone (6) is excluded from both sets, so it is automatically fatal.

### Allowed finals

The default set {0, 2, 4} (tonic triad) is a parameter to the model
builder. For minor-key fugues, {0, 2, 4, 4} can be extended to include
degree 4 (dominant, the 5th scale degree in 0-indexed terms). The caller
controls this via the `allowed_finals` argument.

### Multiple stretto offsets

Require one primary offset (default k = N // 2). Additional offsets are
scored in the Python post-filter via the existing `evaluate_all_offsets`
machinery. This keeps the model as a feasibility problem (faster than
optimisation in CP-SAT) and preserves the existing stretto scoring
weights.

If the feasible set at the primary offset exceeds 500 solutions, a
follow-up solve can add a second offset as a hard constraint to find
the intersection. This is a refinement, not part of Phase 1.

### Minor mode

Pass `MINOR_SEMITONES = (0, 2, 3, 5, 7, 8, 10)` to
`build_consonant_pairs`. No other model changes.

### Melodic validation (MIDI-space)

Post-filter: convert each solution to MIDI via `degrees_to_midi`, apply
`is_melodically_valid`. The feasible set is small (hundreds, not
millions), so this is cheap. If the rejection rate exceeds 20%, promote
the melodic tritone check to the CP-SAT model via a table constraint on
`(start_mod7, iv)` pairs.


## Sampling Strategy

### Two-phase sampling with random restarts (implemented)

Simple random restarts with `random_seed` produced severe clustering
(all solutions started `(0,1,0,1,...)`). Random objectives alone produced
diversity but very few solutions per restart (optimisation mode only fires
the callback for improving solutions).

Solution: two phases per restart.

**Phase A** — Random linear objective with random per-position weights
finds one anchor solution in a different region of the feasible space.

**Phase B** — Feasibility enumeration from the anchor's neighbourhood
(via `add_hint`) collects up to `SOLUTIONS_PER_RESTART` solutions.

```python
for restart in range(CPSAT_NUM_RESTARTS):  # 40
    # Phase A: random objective → anchor
    weights = [rng.randint(-10, 10) for _ in range(num_notes)]
    model_a.maximize(sum(w * p for w, p in zip(weights, pitches)))
    anchor = solve(model_a)  # one solution

    # Phase B: enumerate from anchor neighbourhood
    model_b.add_hint(pitches, anchor)
    enumerate(model_b, limit=CPSAT_SOLUTIONS_PER_RESTART)  # 50
```

Default: 40 restarts × 50 solutions = up to 2,000 candidates.
Duplicates removed via set of degree tuples. Typical yield: 900–1,900
distinct sequences depending on note count.

### Performance (measured)

| Notes | CP-SAT sampling | Scoring + selection | Total |
|---|---|---|---|
| 8 | 21s | <1s | ~22s |
| 9 | 25s | <1s | ~26s |
| 10 | 33s | <1s | ~34s |

All within the 35s budget for 5–10 notes.


## Scoring

The existing `score_pitch_sequence` function applies unchanged to CP-SAT
solutions. Combined score (50% pitch + 50% duration), quality floor
(85% of best), and stretto scoring all remain as-is. The difference:
every candidate entering stretto evaluation is already viable at the
primary offset, so the zero-viable rejection rate drops from 99.86%
to 0%.


## Integration (completed)

### Files created

- `motifs/subject_gen/cpsat_generator.py`: CP-SAT model builder,
  consonance table precomputation, automaton construction, two-phase
  sampling driver. Replaces `generate_pitch_sequences` as the pitch source.

### Files modified

- `motifs/subject_gen/pitch_generator.py`: `_cached_validated_pitch`
  calls `generate_cpsat_degrees` instead of `generate_pitch_sequences`.
  Old enumerator is dead code (can be removed).

- `motifs/subject_gen/constants.py`: Added:
  ```
  CPSAT_NUM_RESTARTS: int = 40
  CPSAT_SOLUTIONS_PER_RESTART: int = 50
  CPSAT_SOLVER_TIMEOUT: float = 3.0
  ```

### Files unchanged

`selector.py`, `duration_generator.py`, `contour.py`, `models.py`,
`validator.py`, `scoring.py`, `stretto_constraints.py`,
`head_generator.py`, `shared/constants.py`.

### Dead code

`generate_pitch_sequences` in `pitch_generator.py` — old exhaustive
enumerator. Defined but never called. Safe to remove.

### Cache key format

`cpsat_pitch_{N}n_{mode}_k{K}.pkl`. Includes primary offset k since
different offsets produce different feasible sets. Delete `.cache/subject/`
to force regeneration after any constraint or scoring change.


## Constraints by Enforcement Layer

| Constraint | Layer | Encoding |
|---|---|---|
| Tonic start, allowed finals | CP-SAT | Direct / AllowedAssignments |
| Pitch range [4, 11] | CP-SAT | Min/Max equality + bounds |
| Step fraction >= 50% | CP-SAT | Boolean sum |
| Large leaps <= 4 | CP-SAT | Boolean sum |
| Same-sign run <= 5 | CP-SAT | Automaton |
| No repeated pitches | CP-SAT | iv[i] != 0 |
| Pitch frequency <= 3 | CP-SAT | Per-value Boolean sum |
| Stretto consonance (primary k) | CP-SAT | Table constraint per overlap |
| Melodic tritone ban | Post-filter | `is_melodically_valid` (MIDI) |
| Tritone outline / 4 notes | Post-filter | `is_melodically_valid` (MIDI) |
| Consecutive same-dir leaps | Post-filter | `is_melodically_valid` (MIDI) |
| Stretto at secondary offsets | Post-filter | `evaluate_all_offsets` (scoring) |
| Pitch scoring (multi-criteria) | Post-filter | `score_pitch_sequence` |
| Diversity | Post-filter | Greedy max-min Hamming |

If any post-filter rejects >20% of candidates, promote to CP-SAT.


## Risks and Mitigations

| Risk | Status |
|---|---|
| Feasible set < 50 | Not observed. 85–1,936 distinct at 5–12 notes |
| Solver clustering (low diversity) | Solved by two-phase anchor+enumerate strategy |
| Mod-7 performance | Using AddModuloEquality, adequate performance |
| Cache coherence across k values | k included in cache key |
| Automaton complexity | 11 states, 22 transitions — trivial for CP-SAT |
| Even-duration stretto gap | Known: CP-SAT guarantees at even durations, real-duration evaluation in post-filter is stricter |


## Acceptance Criteria

1. [MET] Produces subjects for 5–10 notes without crashing.
2. [MET] Every output subject has >= 1 viable stretto offset.
3. [MET] Uncached generation <= 35 seconds for 5–10 notes.
4. [MET] `select_subject` / `select_diverse_subjects` interface unchanged.
5. [MET] All subjects pass `is_melodically_valid`.
6. [MET] Pitch scores comparable (scorer unchanged, pool is larger).
7. [MET] Stretto: all 6 subjects have >= 1 viable offset (was ~14% survival rate).


## Appendix A: Prototype Results

### Original enumerate-all (crashed at 9 notes)

| Notes | Offset k | Solutions | Time |
|---|---|---|---|
| 5 | 2 | 85 | 0.06s |
| 6 | 3 | 228 | 0.16s |
| 7 | 3 | 1,530 | 3.95s |
| 8 | 4 | 4,120 | 22s |
| 9 | 4 | crash | — |

### Two-phase sampling (production strategy)

| Notes | Offset k | Distinct | Time |
|---|---|---|---|
| 5 | 2 | 85 | 2.7s |
| 6 | 3 | 202 | 4.1s |
| 7 | 3 | 643 | 8.4s |
| 8 | 4 | 903 | 21s |
| 9 | 4 | 1,369 | 25s |
| 10 | 5 | 1,559 | 33s |
| 11 | 5 | 1,863 | 36s |
| 12 | 6 | 1,936 | 54s |


## Appendix B: Consonance Sets

| Set | Mod 12 | Usage |
|---|---|---|
| `CONSONANT_INTERVALS` | {0,3,4,5,7,8,9} | Weak-beat stretto |
| `CONSONANT_INTERVALS_ABOVE_BASS` | {0,3,4,7,8,9} | Strong-beat stretto |
| `PERFECT_INTERVALS` | {0,7} | Parallel motion ban |
| `STRONG_BEAT_DISSONANT` | {1,2,6,10,11} | Downbeat prohibition |


## Appendix C: File Inventory

| File | Role | Status |
|---|---|---|
| `subject_gen/cpsat_generator.py` | Model + two-phase sampler | Created |
| `subject_gen/cpsat_prototype.py` | Prototype (reference only) | Superseded |
| `subject_gen/pitch_generator.py` | Scoring + validation | Calls cpsat_generator |
| `subject_gen/duration_generator.py` | Duration pipeline | Unchanged |
| `subject_gen/selector.py` | Diversity + stretto filter | Stretto filter still active (real durations) |
| `subject_gen/constants.py` | Constants | CP-SAT params added |
| `subject_gen/contour.py` | Shape classification | Unchanged |
| `subject_gen/models.py` | Data classes | Unchanged |
| `subject_gen/validator.py` | MIDI melodic checks | Post-filter |
| `subject_gen/scoring.py` | Scoring utilities | Unchanged |
| `subject_gen/cache.py` | Disk cache | New key format |
| `stretto_constraints.py` | Offset evaluation | Real-duration scoring |
| `head_generator.py` | MIDI conversion | Unchanged |
| `shared/constants.py` | Scales, consonances | Read-only |
