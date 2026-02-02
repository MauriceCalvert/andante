# Revision Findings

IMPORTANT: Only add to the end of this file, it's a historical trace.

Updated: 2026-02-02 17:00

## Current task
Review all Phase 5+6a code against designs and laws.md, fix bugs, then run tests.

## Files read so far
- claude.md ✓
- revision/STATUS.md, TODO.md, revision_plan.md ✓
- revision/phase5_design.md ✓
- revision/phase6_design.md ✓
- shared/diatonic_pitch.py ✓
- shared/plan_types.py ✓
- shared/voice_types.py ✓
- shared/key.py ✓
- builder/compose.py ✓
- builder/voice_writer.py ✓
- builder/writing_strategy.py ✓
- builder/pillar_strategy.py ✓
- builder/voice_checks.py ✓
- builder/figuration_strategy.py ✓
- builder/cadential_strategy.py ✓
- builder/staggered_strategy.py ✓
- builder/junction.py ✓
- builder/types.py ✓ (Composition now uses dict[str, tuple[Note, ...]])
- builder/figuration/types.py ✓
- shared/constants.py (partial, key constants confirmed)
- revision/test_pitch.py ✓

## Files still to read
- docs/Tier1_Normative/laws.md (for review against)
- builder/figuration/loader.py (confirm get_diminutions, get_cadential signatures)
- builder/figuration/rhythm_calc.py (confirm compute_rhythmic_distribution)
- builder/figuration/selection.py (confirm sort_by_weight)
- revision/test_phase6a.py, test_plan_contract.py

## Bugs found and fixed

### BUG-001: junction.py consecutive leap check is broken
**File:** builder/junction.py
**Line:** `if (entry_step - exit_step > 0) == (exit_step > 0):`
**Problem:** The "same direction" check compares entry_step-exit_step against exit_step > 0 (absolute position). Should compare the current leap direction against the previous leap direction. But we don't have the previous leap direction — we only have `prev_ended_with_leap: bool`, not the direction. The check is meaningless as written.
**Status:** NEEDS FIX — need to pass prev_leap_direction or rethink.

### BUG-002: staggered_strategy.py doesn't offset returned notes
**File:** builder/staggered_strategy.py
**Problem:** Returns `((source_pitch, sounding),)` but the delay offset isn't communicated back. The phase6_design.md says "The caller (VoiceWriter._compose_gap) adds the delay to all offsets in the returned notes." But VoiceWriter._compose_gap doesn't know about the delay — it just uses elapsed time from pair durations. The gap_offset is already the anchor start, and elapsed starts at 0. So the staggered note will be placed at the gap start, not after the delay.
**Status:** NEEDS FIX — either return a rest tuple or have the caller handle delay.

### BUG-003: figuration_strategy.py uses sort_by_weight then rng.shuffle then re-sorts
**File:** builder/figuration_strategy.py  
**Lines:** `ranked = sort_by_weight(filtered)` then `rng.shuffle(ranked)` then `ranked.sort(key=lambda f: -f.weight)`
**Problem:** The first sort_by_weight is wasted — immediately shuffled, then re-sorted. The shuffle+stable-sort gives random order within same weight, which is correct behaviour, but the initial sort_by_weight call is dead code.
**Status:** MINOR — remove first sort_by_weight call.

### BUG-004: voice_writer.py _compose_gap lambda captures wrong offset
**File:** builder/voice_writer.py
**Problem:** `candidate_filter=lambda dp, offset: self._check_candidate(dp, gap_offset + offset, Fraction(0))`
The lambda parameter `offset` shadows the meaning — strategy passes elapsed-within-gap as the second arg, and VoiceWriter adds gap_offset. This is actually correct. But the third arg to _check_candidate is `duration=Fraction(0)` which is unused in 6a but will be needed in 6c. Fine for now.
**Status:** OK for 6a.

### BUG-005: Composition type in compose.py vs builder/types.py
**File:** builder/compose.py, builder/types.py
**Problem:** compose.py creates `Composition(voices=prior_voices, metre=..., tempo=..., upbeat=...)`. builder/types.py defines Composition with `voices: dict[str, tuple[Note, ...]]` — matches. Good.
**Status:** OK.

## Review checklist

### Phase 5 types
- [x] DiatonicPitch — clean, matches design
- [x] plan_types.py — all types match phase5_design.md
- [x] voice_types.py — Role enum correct, Range correct
- [x] key.py — diatonic_to_midi and midi_to_diatonic implemented correctly
- [x] validate_plan — comprehensive, all 8 checks present
- [ ] test_pitch.py — need to run

### Phase 6a code
- [x] compose.py — clean, matches design
- [x] writing_strategy.py — ABC correct
- [x] pillar_strategy.py — correct
- [x] voice_writer.py — review in progress
- [x] voice_checks.py — all 5 check functions present
- [x] figuration_strategy.py — review in progress
- [x] cadential_strategy.py — review in progress  
- [x] staggered_strategy.py — BUG-002 found
- [x] junction.py — BUG-001 found

## Next steps
1. Read laws.md for cross-check
2. Fix BUG-001 (junction consecutive leap)
3. Fix BUG-002 (staggered delay offset)
4. Fix BUG-003 (dead sort_by_weight)
5. Run test_pitch.py
6. Write smoke test for Phase 6a
7. Commit Phase 5+6a
8. Proceed to Phase 6b
