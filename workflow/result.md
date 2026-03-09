# EPI-7 Result: Planner episode-type selection

## Code Changes

Three files modified, no new files.

**1. builder/phrase_types.py** — Added `episode_type: str | None = None` field to
PhrasePlan after `register_target`. Default None preserves paired-kernel path for
non-episode phrases and for episodes where no type is explicitly assigned.

**2. planner/imitative/entry_layout.py** — Added:
- `CIRCLE_OF_FIFTHS_MIN_BARS = 4` constant
- `_EPISODE_TYPE_POOL` tuple: `("sequential_episode", "parallel_sixths", "circle_of_fifths")`
- `_select_episode_type(bar_count, prev_type)` function: iterates pool, skips
  circle_of_fifths when bar_count < 4, skips any type matching prev_type, falls
  back to "sequential_episode"
- In `build_imitative_plans`: `prev_episode_type` tracker, episode_type selection
  for `function == "episode"` groups, passed to PhrasePlan constructor

**3. builder/phrase_writer.py** — In the EPISODE case of `_write_thematic`, changed
`demo_technique=demo_technique` to
`demo_technique=demo_technique if demo_technique is not None else plan.episode_type`.
Demo mode takes priority; production uses plan.episode_type; both None falls through
to paired-kernel path.

---

## Bob's Assessment

### Pass 1: What do I hear?

Five episodes in this invention. They alternate between two clearly different
textures, and that alternation is the most audible structural change this phase
introduces.

**Bars 4-10 (episode 1):** Voices chase each other. The soprano descends in
semiquaver groups — D5 C5 B4 A4 — and the bass follows with its own figures
offset by a beat. The ear tracks two independent lines, one pursuing the other.
Direction is clear: downward through A minor. Motion is lively.

**Bars 11-16 (episode 2):** Both voices move together in lockstep. Every attack
is simultaneous. The soprano descends from E5 to F3 over six bars — a large
sweeping descent — and the bass mirrors it a sixth below. No chase, no delay.
The texture is fuller, blended, and the sense of two independent voices vanishes.
It is unmistakably different from the preceding episode.

**Bars 19-25 (episode 3):** Back to chasing. Soprano descends from B5, bass
follows with offset figuration. The call-and-response returns. After the blended
lockstep of bars 11-16, the return to independent motion is refreshing.

**Bars 26-31 (episode 4):** Lockstep again. Both voices are simultaneous. But
here the contrast collapses: the exact same 7-note melodic pattern (D5 C5 Bb4 A4
Bb4 G4 E4) repeats identically in every bar for six bars. There is no
transposition, no development, no direction. The soprano is trapped. The ear
gives up tracking after bar 27 — it is a static loop, not a sequence. This is
the weakest moment in the piece. Where bars 11-16 descended continuously and
maintained momentum, bars 26-31 simply circle.

**Bars 34-40 (episode 5):** Chasing returns. Soprano F#5 descending through E
minor, bass trailing. The relief after the static loop is palpable.

### Pass 2: Why does it sound that way?

The alternation between "chasing" (sequential_episode) and "blended"
(parallel_sixths) is doing what the task intended: adjacent episodes are
texturally distinct. The chasing episodes use staggered attacks and independent
rhythms; the blended episodes use simultaneous attacks throughout. The ear
distinguishes these instantly.

The failure at bars 26-31 is not an episode-type problem — the type assignment
is correct (parallel_sixths, distinct from the preceding sequential). The problem
is that parallel_sixths in D minor at this pitch level produces no transposition
across iterations. Each bar is identical. This is a pre-existing limitation of
the parallel_sixths technique function, not of the selection logic.

Bars 11-16 (also parallel_sixths) avoid this because the soprano range is wider
(E5 to F3), giving the technique room to descend. Bars 26-31 start at D5 and
the pattern simply repeats.

The cross-relation faults (A natural vs Bb) at bars 11, 12, 13, 26-31 are a
consequence of the parallel_sixths technique moving through keys that include Bb
while adjacent material uses A natural.

1. **Do adjacent episodes sound texturally distinct?** Yes. Every adjacent pair
   differs: bars 4-10 (chasing) vs 11-16 (blended), bars 11-16 (blended) vs
   19-25 (chasing), bars 19-25 (chasing) vs 26-31 (blended), bars 26-31
   (blended) vs 34-40 (chasing).

2. **Is any episode indistinguishable from its neighbour?** No. Every adjacent
   pair has a different texture.

3. **Tension and release across the episode sequence?** The alternation
   contributes to variety. The chasing episodes create forward motion; the
   blended episodes provide contrast. However, bars 26-31 undermine the arc —
   a static loop six bars long drains momentum from the confirmatio section.
   The return to chasing at bar 34 rescues the forward motion, but the damage
   is done: the most structurally important part of the piece (confirmatio)
   has its longest episode stuck in a repetitive loop.

---

## Chaz's Diagnosis

### Episode type assignments

| Phrase | Bars   | bar_count | episode_type        | prev_episode_type (before) |
|--------|--------|-----------|---------------------|----------------------------|
| [2]    | 4-10   | 7         | sequential_episode  | None                       |
| [3]    | 11-16  | 6         | parallel_sixths     | sequential_episode         |
| [5]    | 19-25  | 7         | sequential_episode  | parallel_sixths            |
| [6]    | 26-31  | 6         | parallel_sixths     | sequential_episode         |
| [8]    | 34-40  | 7         | sequential_episode  | parallel_sixths            |

**Verification:** `prev_episode_type` advances correctly. No two adjacent
episode PhrasePlans share the same type. Two distinct values appear
(sequential_episode and parallel_sixths).

**Circle-of-fifths never selected.** The `_select_episode_type` function iterates
`_EPISODE_TYPE_POOL` in order. When `prev_type` is "parallel_sixths", the first
candidate "sequential_episode" passes both gates (not circle_of_fifths, not
prev_type) and is returned immediately. Circle-of-fifths is third in the pool
and is only reachable when both preceding candidates are skipped. This happens
only if `prev_type` is "sequential_episode" AND "parallel_sixths" is also
skipped — which never occurs because parallel_sixths has no bar-count gate.
Known Limitation #2 in the task brief acknowledges this as a fixed-cycle proxy.

### Bob's complaints traced

**Bob says:** "the exact same 7-note melodic pattern repeats identically in
every bar for six bars [at bars 26-31]"

**Cause:** The `technique_2` (parallel_sixths) function in `builder/techniques.py`
generates the pattern. When the register_target start and end pitches are close
together, the step_schedule produces zero transposition per iteration. Each
iteration of the parallel_sixths kernel is identical. The `_select_episode_type`
function in `entry_layout.py` correctly assigned "parallel_sixths" — the problem
is in the technique function's handling of narrow pitch trajectories, which is
outside EPI-7 scope.

**Location:** `builder/techniques.py` (technique_2 / parallel_sixths generator)

**Fix:** Not in scope for EPI-7. The technique function would need to enforce a
minimum transposition step or fall back to a different voicing when the trajectory
is near-zero.

---

## Acceptance Criteria

- [x] At least two distinct episode_type values appear: sequential_episode and parallel_sixths
- [x] No two consecutive episode PhrasePlans share the same episode_type
- [x] Bob hears textural contrast between adjacent episodes (chasing vs blended)
- [x] Pipeline runs clean, no new assertions or regressions

---

Please listen to the MIDI and let me know what you hear.
