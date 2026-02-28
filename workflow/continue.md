# Continue

## Status: EPI-6 paired-kernel episodes active but producing 105 faults

New chat starts here. Read this file, then `workflow/todo.md`, then
`docs/Tier1_Normative/laws.md`, then `docs/knowledge.md`, then `completed.md`.

---

## What was done this session

### 1. Confirmed paired-kernel path is live
EPI-6 cross-slice fix (all-pairs windows) was already applied in a previous
session. Diagnostic prints added to `episode_kernel.py` confirm:
- 354 raw kernels extracted (147 slices + dedup/inversion/sub-pairs)
- 126 survive pool filtering (durations: 44×3/8, 68×1/2, 6×5/8, 8×1/4)
- DFS chains solve successfully for all 5 episodes (bar_counts 7,6,7,6,7)
- No fallback warnings — every episode uses the paired-kernel path

### 2. Removed stale debug logging
- `PLACE-NEAR` prints removed from `_place_near()` in `episode_dialogue.py`
- `Consonance fix` debug removed from `_apply_consonance_check()` in `episode_dialogue.py`
- `EPISODE-CALL` / `EPISODE-EXIT` debug removed from `phrase_writer.py`
- `-v` DEBUG enablement for episode_dialogue/phrase_writer removed from `run_pipeline.py`

### 3. Diagnosed 105 faults (up from 68 with fallback)

Two independent root causes:

#### Problem A — Register drift (37 tessitura + 5 grotesque_leap = 42 new faults)

`_place_near` (introduced to fix octave leaps) shifts each iteration to the
nearest octave of the previous exit pitch, with NO range consultation. In a
descending sequence (step = -1), each iteration is one diatonic step lower.
After 4-5 iterations the soprano drifts below its range floor and the bass
follows. By bar 11 the soprano is at A#2 (range floor is G3). By bar 26
it's at C2. The bass hits C1, D1, E1.

Trace evidence — soprano ranges per episode:
- bars 4-10:  F3..E5  (marginally low)
- bars 11-16: A#2..A3 (9 semitones below floor)
- bars 19-25: B2..D5  (drifting)
- bars 26-31: C2..A3  (19 semitones below floor)
- bars 34-40: D2..B4  (17 semitones below floor)

**Root cause of root cause:** The `ascending` flag is set by `subject_planner.py`
based on semitone distance between episode from_key and to_key
(`dist > 0` → ascending). This is wrong — direction should be determined by
where the voice currently IS relative to its range, not by the key journey.
If episode 1 finishes low (e.g. C4), episode 2 should ascend regardless of
what key it's heading toward. Octave-shifting is a band-aid; the sequence
direction must adapt to register.

**Location:** `ascending` originates in `subject_planner.py` episode block
(around line 676), flows through `BeatRole.fragment_iteration` sign convention,
is read in `phrase_writer.py` line 289 (`ascending = beat_role_v0.fragment_iteration < 0`),
and passed to `episode_dialogue.py:generate()` which converts it to `step = 1 if ascending else -1`.

#### Problem B — Oscillating parallels (66 faults, unchanged from fallback)

The fixed `IMITATION_DEGREE_OFFSET = -9` (lower 10th) means both voices
walk through the same diatonic interval pattern. At each iteration both voices
are transposed by the same `step`, so the vertical interval between them
is determined entirely by the kernel's original intervals. When the kernel
has upper/lower notes at octave or fifth intervals, every iteration
reproduces those parallels.

Independent kernel rhythms (the whole point of EPI-6) should break lockstep,
but the parallels occur at shared-attack points where both voices happen to
have onsets. The consonance check (`_apply_consonance_check`) only adjusts
±1 degree and only at shared attacks — it doesn't prevent parallel motion
between consecutive shared attacks.

This is a deeper design problem. Possible approaches (not yet evaluated):
- Vary the degree offset per iteration (e.g. alternate 10th/6th)
- Apply different transposition rates to upper vs lower voice
- Post-hoc parallel detection + correction pass
- Viterbi-based episode generation (major architectural change)

## Files modified this session

- `motifs/episode_kernel.py` — diagnostic prints in `_build_pool` and `generate()`
- `motifs/episode_dialogue.py` — removed PLACE-NEAR and Consonance fix debug logging
- `builder/phrase_writer.py` — removed EPISODE-CALL/EXIT debug, dead `_prior_up`/`_prior_lo` vars
- `scripts/run_pipeline.py` — removed `-v` DEBUG enablement for episode/phrase_writer loggers

## Current fault census (105 total, seed 1053109245)

| Type               | Count | Source        |
|--------------------|-------|---------------|
| tessitura_excursion| 37    | Problem A     |
| parallel_octave    | 23    | Problem B     |
| parallel_fifth     | 16    | Problem B     |
| direct_octave      | 6     | Problem B     |
| ugly_leap (tritone)| 6     | Problem B     |
| grotesque_leap     | 5     | Problem A     |
| consecutive_leaps  | 5     | Problem A + B |
| direct_fifth       | 3     | Problem B     |
| cross_relation     | 3     | Problem B     |
| parallel_rhythm    | 2     | Stretto/cad   |

## Next steps

1. **Fix Problem A first** — register-aware episode direction. The `ascending`
   flag should be computed at render time from the prior exit pitch relative
   to voice range midpoint, not from the planner's key distance. This is a
   small change in `phrase_writer.py` (override the planner's ascending with
   a register-based decision) or in `episode_dialogue.py:generate()`.

2. **Then tackle Problem B** — parallel motion in paired-kernel episodes.
   This requires a design decision on approach before coding.
