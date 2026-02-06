# xfail Resolution Plan

18 xfails across 3 root causes. Fix each root cause, confirm with affected tests, remove xfail guards.

---

## Root Cause 1: Minor key cadence — wrong local_key fallback (10 xfails)

**Affected tests:**
- `test_final_soprano_tonic` — bourree_a_minor, invention_a_minor, minuet_a_minor
- `test_final_bass_tonic` — bourree_a_minor, invention_a_minor, minuet_a_minor
- `test_correct_final_degree` — bourree_a_minor, invention_a_minor, minuet_a_minor, gavotte_a_minor

**Diagnosis:**
In `builder/phrase_planner.py`, `_group_anchors_by_schema` filters out `piece_end` anchors.
The final schema in the chain (typically a comma) gets an empty anchor_group, so
`_build_single_plan` falls back to `Key(tonic="C", mode="major")` (line 106).
For A minor pieces, degree 1 in C major = C, not A. Hence the wrong final pitch.

**Fix:**
- [x] 1a. Derive `home_key` from `anchors[0].local_key` inside `build_phrase_plans` (no new param needed)
- [x] 1b. Replace the fallback `Key(tonic="C", mode="major")` with `home_key`
- [x] 1c. Threaded `home_key` through to `_build_single_plan`
- [x] 1d. Run affected tests: 13 passed, 2 xfailed (gavotte — root cause 2)
- [x] 1e. Removed xfail guards for "planner cadence bug" in both test files

---

## Root Cause 2: Gavotte voice-crossing — bass allows unison (6 xfails)

**Affected tests:**
- `test_final_bass_tonic` — gavotte_c_major, gavotte_a_minor
- `test_final_unison_or_octave` — gavotte_c_major, gavotte_a_minor
- `test_correct_final_degree` — gavotte_c_major, gavotte_a_minor
- `test_zero_parallel_perfects` — gavotte_c_major, gavotte_a_minor

**Diagnosis:**
In `builder/phrase_writer.py`, `_select_strong_beat_bass` filters with `p <= soprano_pitch`,
allowing unison (p == soprano_pitch). When soprano is low, bass gets clamped to soprano pitch.
This produces parallel unisons (C4/C4 → B3/B3) and wrong final bass degree.
Also `_find_consonant_alternative` uses `m <= soprano_pitch` — same unison problem.

**Fix:**
- [x] 2a. In `_select_strong_beat_bass`: structural map pitches are now authoritative; strong-beat override skipped when pitch came from structural map
- [x] 2b. Fixed in phrase_writer.py with from_structural flag
- [x] 2c. N/A — root cause was structural map override, not separation constant
- [x] 2d. N/A — structural map authority resolves edge case
- [x] 2e. All 49 gavotte tests pass
- [x] 2f. All gavotte xfail guards removed

---

## Root Cause 3: Invention parallel octaves from pillar strategy (2 xfails)

**Affected tests:**
- `test_zero_parallel_perfects` — invention_c_major, invention_a_minor

**Diagnosis:**
`PillarStrategy.fill_gap` emits a single held note for the whole gap. The candidate_filter
only checks parallels at the note's onset. If the soprano moves during the gap creating
parallel octaves/fifths at a subsequent strong beat, this is not caught during composition
but IS detected by `faults.py` post-facto.

The root cause is that `PillarStrategy` does not check for parallels against the prior voice
at ALL strong beats within the gap — only at the single onset offset.

**Fix:**
- [x] 3a. REVISED: Root cause was phrase_writer.py, not pillar strategy. Parallel checks only ran on strong beats (beat 1). Extended `generate_bass_phrase` to track `prev_bass`/`prev_soprano` at every note and check parallels universally.
- [x] 3b. REVISED: Fixed `_check_parallel_perfects` to verify both voices move in the same direction (was missing motion direction check — would false-positive on contrary motion maintaining a perfect interval).
- [x] 3c. Both invention parallel tests pass: 0 faults
- [x] 3d. Removed xfail guard for "pillar strategy" in test_system.py

---

## Final Validation

- [x] 4a. Full suite: 268 passed, 2 skipped, 0 xfailed, 0 failures
- [x] 4b. Confirmed
- [x] 4c. Appended to completed.md
