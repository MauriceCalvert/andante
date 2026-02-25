# Continue — Post SH-2: Subject Generator Refactored

## What just happened

SH-2 refactored the subject generator from random CP-SAT sampling to
exhaustive head enumeration + tail solving. Also restored dotted
durations and removed mediant from allowed finals.

### Changes made

1. **`constants.py`** — Added `HEAD_LENGTHS = (4,)` (prepared for
   `(3, 4, 5)` later). Restored `DURATION_TICKS` to `(1, 2, 3, 4, 6)`.
   Changed `ALLOWED_FINALS` to `{0, 4}`. Replaced old CP-SAT sampling
   params with `CPSAT_SOLUTIONS_PER_HEAD = 200` and
   `CPSAT_TAIL_TIMEOUT = 2.0`. Old `CPSAT_NUM_RESTARTS`,
   `CPSAT_SOLUTIONS_PER_RESTART`, `CPSAT_SOLVER_TIMEOUT` removed.

2. **`head_enumerator.py`** — New file. Exhaustive enumeration of valid
   heads (leap ≥ 4th + stepwise contrary recovery). For HEAD_LENGTHS=(4,)
   produces 208 heads.

3. **`cpsat_generator.py`** — Rewritten. No longer does random-objective
   sampling. Exports `build_consonant_pairs(mode)` and
   `generate_tails_for_head(head, num_notes, ...)`. The old
   `generate_cpsat_degrees()` function is gone.

4. **`pitch_generator.py`** — Rewritten. Iterates HEAD_LENGTHS, calls
   `enumerate_heads()` per length, then `generate_tails_for_head()` per
   head. The old `_has_valid_head()` post-filter is gone — heads are
   valid by construction. Cache key includes head lengths tag.
   Accepts `verbose` parameter.

5. **`selector.py`** — Pitch dedup (one candidate per degree sequence)
   runs before diversity selection. Rhythm dedup removed — with 3,813
   distinct pitches, the diversity selector handles variety. Passes
   `verbose` through to `_cached_validated_pitch`.

### Pipeline numbers (12n, major, 4/4, 2 bars)

- 208 heads enumerated (len=4)
- 71 fertile heads (have ≥1 valid tail)
- 11,539 raw degree sequences
- 4,767 pass melodic validation
- 2,898,336 pitch × duration pairs
- 90,431 stretto-capable
- 3,813 distinct pitch sequences with stretto
- 20 selected with diversity

### Caches

All `.pkl` files in `.cache/subject/` were deleted. They rebuild on
first run (~230s for stretto GPU eval, then cached).

## What to do next

Discuss with the user which direction to take. Options:

1. **Extend HEAD_LENGTHS to (3, 4, 5)** — change one constant, delete
   pitch cache, run. Should significantly expand the pool. 3-note heads
   give longer tails with more freedom; 5-note heads give more
   distinctive openings.

2. **Add minim (tick 8)** to DURATION_TICKS — enables long-note heads
   and running-tail subjects. Independent of head length change.

3. **Allow other note counts** — drop `--notes 12` restriction and run
   across 8–12 notes. Shorter subjects have more rhythmic slack.

4. **Tune aesthetic scoring** — some selected subjects score below 4.0.
   Review scoring weights or add new criteria now that the pool is large
   enough to be selective.

5. **Listen** — generate MIDI output and evaluate by ear. The numbers
   look good but the only real test is hearing.

6. **Something else** the user has in mind.
