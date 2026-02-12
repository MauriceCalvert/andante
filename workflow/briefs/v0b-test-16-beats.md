## Task: V0b — 16-beat test

Read these files first:
- `viterbi/demo.py`
- `viterbi/pipeline.py`
- `viterbi/mtypes.py`

### Goal

Add a 16-beat example to `demo.py` that exercises the solver at phrase
length. This verifies the DP scales and the cost function produces a
shaped line over a realistic span.

### Implementation

Add `example_5_sixteen_beats` to demo.py. The scenario:

**Leader (bass):** 16 beats outlining a I–vi–IV–V–I progression in C major.
Use this bass line (one note per beat):

    C3 C3 E3 E3 | A2 A2 C3 C3 | F3 F3 A3 A3 | G3 G3 G3 C3

That is beats 0–15, MIDI pitches:
48, 48, 52, 52, 45, 45, 48, 48, 53, 53, 57, 57, 55, 55, 55, 48

**Follower knots (soprano):** 5 knots outlining an arch:
- beat 0: E5 (76) — opening
- beat 4: G5 (79) — rising
- beat 8: A5 (81) — peak
- beat 12: G5 (79) — descent
- beat 15: C5 (72) — cadential resolution

Call `solve_phrase` with `verbose=True`, write MIDI to `example_5.mid`.

Register this as example "5" in the `examples` dict and add it to the
default run-all loop.

### Constraints

- Do not modify any other file.
- Use the same `_describe_inputs` and `_write_output` helpers.

### Checkpoint

Run `python -m viterbi.demo 5`. Verify:
1. No crash, path found (cost < INF).
2. All strong-beat intervals consonant.
3. The path is predominantly stepwise (most transitions are seconds).
4. Some contrary motion visible in the motion row.
5. MIDI file plays two recognisable voices.

Report the total cost, the number of steps vs leaps, and the motion
type distribution (contrary/similar/oblique counts).
