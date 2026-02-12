## Task: V2 — Sub-beat timing and irregular grids

Read these files first:
- `viterbi/mtypes.py`
- `viterbi/corridors.py`
- `viterbi/pathfinder.py`
- `viterbi/pipeline.py`
- `viterbi/costs.py`

### Goal

The prototype places one note per integer beat. Real music has notes at
irregular sub-beat positions (quavers, semiquavers, dotted rhythms). The
solver must accept grid positions at arbitrary offsets.

### Implementation

**mtypes.py:**

Change the `beat` field in `Knot`, `LeaderNote`, and `Corridor` from
`int` to `float`. This is the only type change. The field still
represents a time position in beats (e.g. 0.0, 0.5, 1.0, 1.25).

Add a `BeatStrength` enum or keep the string constants but add a
`MODERATE_BEAT` value for off-beat quavers that are neither strong
(downbeat) nor fully weak (passing semiquaver):

```python
STRONG_BEAT = "strong"
MODERATE_BEAT = "moderate"
WEAK_BEAT = "weak"
```

**corridors.py:**

Replace the `beat_strength(beat: int)` function. It now accepts
`(position: float, beats_per_bar: float)` and classifies:

- Downbeat (position % beats_per_bar == 0): STRONG_BEAT
- Half-bar (position % beats_per_bar == beats_per_bar/2): STRONG_BEAT
- Beat boundary (position % 1.0 == 0): MODERATE_BEAT
- Everything else: WEAK_BEAT

`build_corridors` gains a `beats_per_bar` parameter (default 4.0).
Moderate beats allow all diatonic pitches but with higher dissonance
costs than weak beats (handled in costs.py, not here — corridors stay
binary: consonance-only on strong, all-diatonic otherwise).

Actually, keep corridor logic simple: STRONG_BEAT positions get
consonance-only corridors, MODERATE_BEAT and WEAK_BEAT get all diatonic.
The cost function differentiates moderate from weak.

**costs.py:**

`dissonance_at_departure`: add a moderate case. Strong-beat dissonance
costs 100.0 (unchanged). Moderate-beat dissonance: cost is 3× the
weak-beat cost (so a dissonance on a quaver off-beat is tolerated but
more expensive than on a passing semiquaver).

**pathfinder.py:**

`find_path` already uses `corridors[i].beat` for leader lookup. Since
this is now float, the `leader_map` keys become floats. No algorithm
change needed — just type tolerance.

The `phrase_position` calculation: `t / max(n_beats - 1, 1)` is already
a ratio of position index to length. This stays correct regardless of
whether the underlying beats are integer or fractional.

**pipeline.py:**

`solve_phrase` assertion changes: `follower_knots[i].beat <
follower_knots[i+1].beat` works with floats. The first/last alignment
assertions use float equality — use `abs(a - b) < 1e-6` tolerance.

**demo.py:**

Add `example_6_subbeat` that uses quaver positions (0.0, 0.5, 1.0, 1.5,
...) for 4 bars (positions 0.0 to 7.5, 16 grid positions). Leader on
every quaver, knots at bar boundaries (0.0, 2.0, 4.0, 6.0, 7.5).

### Constraints

- All existing integer-beat examples must still work without change.
  Float 0.0 == int 0, etc.
- Do not change cost weights.
- Do not import Fraction — use plain float. The real system uses Fraction
  but the prototype stays lightweight.
- The `midi_out.py` writer must handle fractional beat times (midiutil
  accepts float time values).

### Checkpoint

1. `python -m viterbi.demo 1` — identical output to before V2.
2. `python -m viterbi.demo 6` — sub-beat example runs, path found.
3. `python -m viterbi.test_brute 5 20` — all pass (integer beats still work).
4. Report the sub-beat example's motion distribution and whether
   quaver-level passages show more stepwise motion (they should, because
   the pitch distance per grid step is smaller).
