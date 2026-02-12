## Task: V3 — Enhanced cost function

Read these files first:
- `viterbi/costs.py`
- `viterbi/scale.py`
- `viterbi/pathfinder.py`
- `shared/counterpoint.py`
- `shared/constants.py` (for PERFECT_INTERVALS, CROSS_RELATION_PAIRS, UGLY_INTERVALS)

### Musical Goal

The current cost function handles step size, motion type, leap recovery,
zigzag, run length, dissonance, and phrase position. It produces competent
stepwise lines but lacks three dimensions a baroque player would consider:

1. **Cross-relations** — F# in one voice against F♮ in the other within a
   few beats is a jarring fault. The solver currently has no awareness of
   this.

2. **Voice spacing** — a soprano sitting a 2nd above the bass is muddy; a
   soprano 3+ octaves above is disconnected. There's a sweet spot around
   one to two octaves.

3. **Interval preference by beat strength** — on strong beats, 3rds and
   6ths (imperfect consonances) are warmer and more forward-driving than
   5ths and octaves (perfect consonances). A good continuo player favours
   imperfect consonances on strong beats and reserves perfect consonances
   for openings and cadences.

### Implementation

**costs.py — new cost functions:**

```python
COST_CROSS_RELATION = 30.0

def cross_relation_cost(
    prev_pitch: int,
    curr_pitch: int,
    prev_leader: int,
    curr_leader: int,
) -> float:
```

A cross-relation occurs when a pitch class appears in one voice and its
chromatic alteration appears in the other voice within the same transition.
Specifically: if `prev_leader % 12` and `curr_pitch % 12` differ by 1
semitone while sharing the same letter name (i.e. one is the sharp/flat of
the other), or likewise `curr_leader % 12` vs `prev_pitch % 12`. Since the
prototype works diatonically within a key, cross-relations arise mainly at
key boundaries. For now, detect the simple case: two pitch classes within
the same transition that differ by exactly 1 semitone.

Return `COST_CROSS_RELATION` if detected, else 0.

```python
COST_SPACING_TOO_CLOSE = 8.0    # interval < 5 semitones (< P4)
COST_SPACING_TOO_FAR = 4.0      # interval > 26 semitones (> 2 octaves + M2)
IDEAL_SPACING_LOW = 7            # P5
IDEAL_SPACING_HIGH = 24          # 2 octaves

def spacing_cost(
    follower_pitch: int,
    leader_pitch: int,
) -> float:
```

Returns 0 if the absolute interval is between `IDEAL_SPACING_LOW` and
`IDEAL_SPACING_HIGH`. Below: `COST_SPACING_TOO_CLOSE`. Above:
`COST_SPACING_TOO_FAR`.

```python
COST_PERFECT_ON_STRONG = 1.5

def interval_quality_cost(
    follower_pitch: int,
    leader_pitch: int,
    beat_strength: str,
) -> float:
```

On strong beats, perfect consonances (unison, P5, octave) cost
`COST_PERFECT_ON_STRONG`. Imperfect consonances (3rds, 6ths) cost 0.
On weak/moderate beats, both cost 0. This gently steers the solver toward
warmer intervals on strong beats without forbidding perfects.

**costs.py — integrate into transition_cost:**

Add the three new costs to the `transition_cost` function. Thread the
necessary parameters (current beat_strength for interval_quality_cost).
Add them to the breakdown dict as `"cross_rel"`, `"spacing"`, `"iv_qual"`.

**pathfinder.py:**

Thread the additional parameters through to `transition_cost` calls.
The `_print_path` display gains the new cost components in the breakdown.

### Constraints

- Do not import from `shared/counterpoint.py` directly. The prototype
  stays self-contained. Replicate the specific logic needed (cross-relation
  check) locally in costs.py.
- Do not change existing cost weights. The new costs are additive.
- Keep the cost function pure: no state, no side effects, deterministic.
- `transition_cost` signature grows — keep `key` parameter from V1.

### Checkpoint

1. `python -m viterbi.demo` — all examples run. Costs will be slightly
   different due to new components.
2. `python -m viterbi.test_brute 5 20` — all pass (brute force uses the
   same cost function, so optimality is preserved).
3. For example 4 (realistic bass, I-IV-V-I), report:
   - How many strong-beat intervals are perfect vs imperfect
   - The spacing range (min/max semitones between voices)
   - Whether any cross-relations were detected (none expected in C major)
