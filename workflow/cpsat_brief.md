# CP-SAT for Stretto-First Subject Generation

## Status

**Integrated.** CP-SAT generator is live in `motifs/subject_gen/cpsat_generator.py`,
wired into `pitch_generator.py`. Old exhaustive enumerator is dead code.

## Problem (solved)

The old subject generator enumerated all pitch-interval sequences exhaustively,
then filtered for stretto compatibility after the fact. Result: 99.86% of
subjects failed stretto. At 9 notes the enumeration crashed. The six subjects
that survived the diversity selector had 1–3 stretto offsets at best, all "arch"
contour. Musical variety was throttled by stretto acting as a post-hoc sieve.

## Solution

CP-SAT builds subjects where stretto consonance is a construction constraint.
Every candidate the solver produces is stretto-ready at the primary offset
(k = N // 2, even durations) by definition.

Two-phase sampling with random restarts provides diversity:
- Phase A: random linear objective finds one anchor solution per restart
- Phase B: feasibility enumeration from that anchor's neighbourhood

## Prototype Results

| Notes | k (offset) | Distinct solutions | Time   |
|-------|-----------|-------------------|--------|
| 5     | 2         | 85                | 2.7s   |
| 6     | 3         | 202               | 4.1s   |
| 7     | 3         | 643               | 8.4s   |
| 8     | 4         | 903               | 21s    |
| 9     | 4         | 1,369             | 25s    |
| 10    | 5         | 1,559             | 33s    |
| 11    | 5         | 1,863             | 36s    |
| 12    | 6         | 1,936             | 54s    |

5–10 notes all within the 35s budget. Diversity is good — evenly-spaced
samples from the sorted solution set show genuine variety across the
feasible space.

### Comparison with old enumerate-all

| Notes | Old enumerate-all | CP-SAT sampling | Gain |
|-------|-------------------|-----------------|------|
| 5     | 85 (0.06s)       | 85 (2.7s)       | 100% coverage, slower |
| 6     | 228 (0.16s)      | 202 (4.1s)      | 89% coverage |
| 7     | 1,530 (3.9s)     | 643 (8.4s)      | 42% coverage |
| 8     | 4,120 (22s)      | 903 (21s)       | 22% coverage, same time |
| 9     | crash            | 1,369 (25s)     | ∞ |

CP-SAT finds fewer solutions at 7–8 notes than enumerate-all, but this
doesn't matter. The old pipeline found 4,120 at 8 notes, then stretto
killed 99.86%, leaving ~6 survivors for the scorer. CP-SAT gives the
scorer 903 candidates, all stretto-viable. The pool is 150× larger.

## Current Output (2026-02-23)

Six subjects generated from CP-SAT, all pass stretto:

| Subject | Notes | Stretto offsets | Best quality |
|---------|-------|----------------|-------------|
| 00      | 8     | 1              | 0.67        |
| 01      | 9     | 3              | 0.82        |
| 02      | 9     | 2              | 0.80        |
| 03      | 8     | 2              | 1.00        |
| 04      | 8     | 1              | 0.80        |
| 05      | 9     | 2              | 0.64        |

Stretto counts are modest because CP-SAT guarantees consonance at the
primary offset with even durations, but the post-hoc `evaluate_all_offsets`
uses real (uneven) durations where different notes overlap.

## Architecture

```
  ┌────────────────────────┐
  │  cpsat_generator.py    │  Two-phase sampling per restart:
  │  build model, sample   │  A. Random objective → anchor
  │  (40 restarts × 50)    │  B. Enumerate from anchor
  └──────────┬─────────────┘
             │ sorted degree sequences
  ┌──────────▼─────────────┐
  │  pitch_generator.py    │  MIDI validation, scoring,
  │  _cached_validated_pitch│  shape classification
  └──────────┬─────────────┘
             │ _ScoredPitch list
  ┌──────────▼─────────────┐
  │  selector.py           │  Duration pairing, quality floor,
  │  select_diverse_subjects│  stretto re-evaluation (real durs),
  │                        │  greedy max-min diversity
  └──────────┬─────────────┘
             │ GeneratedSubject list
```

## CP-SAT Model Constraints

All constraints use symbolic constants from `constants.py`:

| Constraint | Encoding |
|---|---|
| Tonic start (pitch[0] = 0) | Direct |
| Allowed finals {0, 2, 4} | AllowedAssignments |
| Pitch range [4, 11] | Min/Max equality + bounds |
| Step fraction >= 50% | Boolean sum |
| Large leaps <= 4 | Boolean sum |
| Same-sign run <= 5 | Automaton (11 states, 22 transitions) |
| No repeated pitches | iv[i] != 0 |
| Pitch frequency <= 3 | Per-value Boolean sum |
| Stretto consonance (primary k) | Table constraint per overlap position |

Post-filter in Python:
- Melodic tritone ban, tritone outline, consecutive same-dir leaps
- Pitch scoring (signature leap, recovery, run penalty, variety, climax)
- Shape classification
- Stretto re-evaluation at all offsets with real durations
- Diversity selection (greedy max-min Hamming)

## Files

| File | Role |
|---|---|
| `subject_gen/cpsat_generator.py` | Model builder + two-phase sampler |
| `subject_gen/cpsat_prototype.py` | Prototype (superseded, kept for reference) |
| `subject_gen/pitch_generator.py` | Scoring + validation (calls cpsat_generator) |
| `subject_gen/constants.py` | All constants inc. CPSAT_NUM_RESTARTS etc. |
| `subject_gen/selector.py` | Diversity + real-duration stretto filter |
| `subject_gen/cache.py` | Disk cache (key: `cpsat_pitch_{N}n_{mode}_k{K}.pkl`) |

## Dead Code

`generate_pitch_sequences` in `pitch_generator.py` — the old exhaustive
enumerator. Defined but no longer called. Can be removed.

## Known Limitations

1. **Even-duration stretto only.** CP-SAT assumes all notes have equal
   duration. Real subjects have mixed durations, which changes overlap
   patterns. Joint pitch+duration CP-SAT model deferred.

2. **Single primary offset.** CP-SAT enforces consonance at k = N // 2
   only. Additional offsets are scored in post-filter. Could add a second
   offset as a hard constraint if feasible set is large enough.

3. **All contours are "arch".** The scorer and contour classifier still
   favour arch shapes. This is a scoring problem, not a CP-SAT problem —
   the pool contains diverse contours but they score lower.

4. **Minor mode untested.** `_SCALE_BY_MODE` maps "minor" to
   `NATURAL_MINOR_SCALE`. Consonance table changes accordingly. Not yet
   exercised in production.
