# Plan 3: Polish and Variety

## Root Cause

Plan 2 wired the planner's dormant systems — genre preferences, tension arc,
character-driven figuration. The pipeline produces structurally coherent music
with zero faults. But three sources of rigidity remain:

1. **Static bass in gavotte Section B**: The genre declares
   `accompany_texture: walking` for Section B, and the phrase writer does
   route to the walking path. But the walking path steps toward the next
   structural tone and holds pitch when there is none nearby. With only
   2–3 structural bass degrees spread across 6+ bars, most beats repeat
   the current pitch. The half_bar pattern (Section A) at least alternates
   root and fifth — the walking path does less.

2. **Deterministic schema chains**: `layer_3_schematic()` takes a seed
   (default 42). The CLI never passes a seed. Every run of the same genre
   produces identical chains regardless of key. Law A005 says "RNG in
   planner" — the RNG exists but is never varied.

3. **Per-section schema_sequence ignored**: Phase 1A wired
   `genre_preferences` from `transitions.yaml` — a global preference per
   genre per position category. But each genre section also declares its own
   `schema_sequence` (e.g., minuet A: do_re_mi→fenaroli→prinner). These
   per-section sequences are never read by the walk. They're the strongest
   statement of what the genre wants, and they're discarded.

4. **Post-peak registral plunge**: The tension-to-bias mapping drops from
   +7 (peak) to 0 (low) in one phrase. The result is a 24-semitone soprano
   descent over 2–3 phrases (C6→C4 in the E minor gavotte). A proper arch
   settles gradually.

---

## Strategy

Four independent phases. Any can be done in any order. Phase 5 validates all.

---

## Phase 1: Walking Bass Motion

### Problem

The walking bass path in `generate_bass_phrase()` handles non-structural
beats by stepping toward the next structural tone:

```
if next_struct_midi > current_midi: step up
elif next_struct_midi < current_midi: step down
else: hold current_midi
```

When the current and next structural tones are the same pitch (common in
schemas with repeated degrees like ponte), or when the next structural tone
is many bars away, the bass flatlines.

### Fix

Between structural tones, the walking bass should move by step in a
directional arc — not target-seek. The arc should:

- Depart from the current structural tone by step
- Change direction at bar boundaries (creating a wave)
- Arrive at the next structural tone by step on the beat it falls

This is how baroque walking bass works: stepwise motion with local direction
changes, landing on chord tones at strong beats. The strong-beat consonance
check (`_select_strong_beat_bass`) already exists and stays.

### Implementation

In the walking bass branch of `generate_bass_phrase()`, replace the
target-seeking logic for non-structural notes with an arc generator:

1. At each structural tone, compute direction: if the next structural tone
   is higher, start ascending; if lower, descending; if equal, alternate
   direction per bar.
2. Between structural tones, step diatonically in the current direction.
3. At each bar boundary (non-structural), consider reversing direction
   if the current pitch is approaching a range limit or has moved more
   than a fourth from the structural tone.
4. At the beat before a structural tone, step toward it (existing logic).

The `_select_strong_beat_bass` call remains for accented beats. The
parallel-perfect and leap guards remain unchanged.

### Change site

`builder/phrase_writer.py`, walking bass branch only (the `else` block
starting around line 688).

### Constraint

Do not touch the patterned bass path or the pillar path. Do not change
the structural tone placement logic. Do not add new files.

---

## Phase 2: Seed-Driven Variation

### Problem

The CLI defaults seed to 42. Every run of `gavotte default g_major` produces
the same piece. This violates A005 ("RNG in planner") in spirit — the RNG
exists but is never varied.

### Fix

Two changes:

**2A — CLI seed parameter**

Add an optional `-seed N` flag to `run_pipeline.py`. If omitted, derive
a seed from a hash of (genre, affect, key, current time) so that each run
produces a different piece. If provided, the run is reproducible.

Pass the seed to `planner.generate()`.

**2B — Seed propagation**

`planner.generate()` already accepts `seed` and passes `seed+1` to
`layer_3_schematic()`. Verify that no other planner layer uses `Random`
with a hardcoded seed. If any do, thread the seed through.

### Change sites

- `scripts/run_pipeline.py` — add `-seed` argument
- `planner/planner.py` — verify seed flows to all RNG users

### Constraint

Reproducibility must be preserved: same seed + same inputs = same output.
The default should vary, not be fixed.

---

## Phase 3: Per-Section Schema Sequences

### Problem

The minuet genre declares Section A should use `[do_re_mi, fenaroli, prinner]`.
The walk ignores this and picks from the global `genre_preferences` pool.
The per-section sequence is the composer's intent — the order and choice of
schemas that define the genre's character for each section.

### Fix

Use the per-section `schema_sequence` as the primary source for schema
selection. The transition graph validates that each consecutive pair is
connected; if not, insert a bridge schema.

**3A — Read per-section sequences**

In `_generate_section_schemas()`, before the random walk, check whether the
current section has a `schema_sequence` in the genre config. If it does,
use it directly instead of walking. Validate connectivity: for each pair
(schema[i], schema[i+1]), confirm that schema[i+1] is in the transition
graph's `allowed_next` for schema[i]. If not, insert a connecting schema
from the transition graph (smallest possible bridge).

**3B — Budget reconciliation**

The per-section sequence may not fill the bar budget exactly. Two cases:

- **Too few bars**: The declared sequence sums to fewer bars than the section
  budget. Extend by repeating the continuation-position schemas in the
  sequence (not cadential ones). If no continuation schemas exist, append
  one from the genre_preferences pool.

- **Too many bars**: The declared sequence sums to more bars than the section
  budget. Truncate from the middle (never remove the opening or closing
  schema). Prefer removing continuation schemas.

After adjustment, the cadential filter from Phase 1B still applies: the
section's final schema must be cadential if the section demands a cadence.

### Change site

`planner/schematic.py` — `_generate_section_schemas()` and helpers.

### Constraint

The random walk remains as fallback for sections without a declared
`schema_sequence`. Genres that don't declare per-section sequences (or
declare empty ones) behave exactly as today.

---

## Phase 4: Gentle Registral Descent

### Problem

`ENERGY_TO_REGISTRAL_BIAS` maps energy directly to semitone offset:
peak=+7, high=+6, moderate=+2, low=0. When the tension curve drops from
peak to low over 2–3 phrases, the soprano plunges 7 semitones of bias
instantly. The ascent works (gradual energy rise → gradual bias rise)
but the descent is a cliff.

### Fix

Cap the per-phrase bias change. The bias for phrase N should be at most
`DESCENT_BIAS_STEP` semitones below the bias for phrase N−1. The ascent
is uncapped (the tension curve already provides gradual rise).

Proposed value: `DESCENT_BIAS_STEP = 2` (one whole tone per phrase).

A peak phrase at +7 would descend: +7 → +5 → +3 → +1 → 0 over four
phrases — a gentle settling rather than a plunge.

### Implementation

In `build_phrase_plans()`, after computing `bias` from the energy level,
apply:

```
if i > 0 and plans[i-1].registral_bias - bias > DESCENT_BIAS_STEP:
    bias = plans[i-1].registral_bias - DESCENT_BIAS_STEP
```

Cadential phrases still get bias=0 (they're formulaic and register-locked).
The cap only applies to non-cadential phrases.

### Change sites

- `shared/constants.py` — add `DESCENT_BIAS_STEP = 2`
- `builder/phrase_planner.py` — apply descent cap in `build_phrase_plans()`

### Constraint

Do not change `ENERGY_TO_REGISTRAL_BIAS` itself. The raw mapping is correct
for the ascent; only the descent rate needs limiting.

---

## Phase 5: Validation

No code changes. Measurement and listening.

1. Generate gavotte E minor with default seed and with seed=99.
   Verify schema chains differ.
2. Verify gavotte Section B bass has stepwise motion between structural
   tones (no 3+ consecutive same-pitch notes outside structural repeats).
3. Verify minuet Section A contains do_re_mi, fenaroli, or prinner.
4. Verify post-peak soprano descent: max 3-semitone bias drop per phrase.
5. Zero faults across minuet × 3 keys, gavotte × 3 keys.
6. Listen. Bob judges.

**Success criterion**: Bob hears a gavotte with a walking bass in Section B,
a minuet with genre-idiomatic schemas, and both pieces with a gentle
soprano arch.

---

## Dependency Order

```
Phase 1 (walking bass)      ──┐
Phase 2 (seed variation)    ──┤
Phase 3 (section sequences) ──┼── Phase 5 (validation)
Phase 4 (gentle descent)   ──┘
```

All four phases are independent. Phase 5 validates everything.

---

## Out of Scope

- Motivic return between sections
- Cadential figuration (ornamenting cadence templates)
- Dynamic shaping (velocity arc)
- Additional genres beyond minuet and gavotte for validation
- ML pipeline (Phase 15)
