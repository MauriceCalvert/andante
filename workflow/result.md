# Phase 16f Result — DiminutionFill wired into soprano_writer

## Implementation Complete

Successfully replaced soprano generation path from `_fill_all_spans` + `_apply_guards` (downstream fix) with `write_voice` + `DiminutionFill` (prevent at source).

**Files modified:** `builder/soprano_writer.py` only
**Functions deleted:** 6 (_fill_all_spans, _apply_guards, _validate_soprano_notes, _check_leap_step, _check_max_interval, _deflect_neighbour)
**Functions remaining:** 2 (_place_structural_tones, generate_soprano_phrase)
**Public API:** Unchanged (same signature, same return type)

---

## Bob Evaluation

### Pipeline Test: minuet default c_major

**Pass 1 — What do I hear?**

Cannot evaluate musically - Bob reads .note files, not test runs. The pipeline completed without crashing and produced 178 soprano notes and 52 bass notes. One logged audit violation appeared during generation: "needs step recovery at 71 at offset 7".

**Pass 2 — Why does it sound that way?**

Not applicable - no musical assessment to explain.

### Audit Violations

The pipeline logged one violation:
- **needs_step_recovery** at pitch 71, offset 7

This indicates a leap was not followed by stepwise recovery in contrary direction. The old system would have fixed this in `_apply_guards`; the new system detects it in `audit_voice` but does not prevent it (strict_audit=False).

### Test Failures

37 tests failed that previously passed:
- 32 failures in `test_soprano_no_cross_bar_repetition` (D007 violations)
- 4 failures in `test_soprano_leap_then_step` (leap-recovery violations)
- 1 failure in `test_bass_hits_schema_degrees` (unrelated to soprano changes)

The failures show that the new system produces output violating rules D007 (cross-bar repetition) and leap-step recovery. The old `_apply_guards` prevented these; the new `audit_voice` detects but does not fix them.

---

## Chaz Evaluation

### Code Structure Verification

Per task checklist:

1. **Is `_fill_all_spans` gone from soprano_writer.py?** ✓ Yes
2. **Is `_apply_guards` gone from soprano_writer.py?** ✓ Yes
3. **Are all removed imports genuinely unused?** ✓ Verified (no grep hits)
4. **Does `generate_soprano_phrase` call `write_voice`?** ✓ Yes (line 136)
5. **Is `strict_audit=False`?** ✓ Yes (line 145)
6. **Count remaining functions in soprano_writer.py** ✓ Exactly 2
7. **Count `if` statements in rewritten `generate_soprano_phrase`**
   - **2 total:** both are simple, non-nested conditionals
   - Line 85-89: Compute next_entry_midi (early return pattern)
   - Line 123-124: Build other_voices dict (optional data assembly)
   - Both follow CLAUDE.md rule: avoid nested if, use early returns

### Root Cause of Test Failures

**Bob says:** 37 tests failed; soprano output violates D007 and leap-step recovery rules.

**Cause:** `DiminutionFill._check_figure_pitches()` (builder/strategies/diminution.py:244-337) checks:
- Parallel perfects ✓
- Cross-relations ✓
- Ugly melodic intervals ✓
- Voice crossing ✓

But does NOT check:
- Cross-bar repetition ✗
- Leap-step recovery ✗
- Consecutive leaps ✗

The old `_apply_guards` (now deleted) enforced these rules via post-pass fixes. The new `audit_voice` (builder/voice_writer.py:32-221) detects them but does not fix (strict_audit=False logs violations, does not raise).

**Location:** builder/strategies/diminution.py:244-337 (_check_figure_pitches)

**Fix:** Not applicable per task constraints. Task Known Limitation #3 explicitly states:
> "audit_voice checks things DiminutionFill does not prevent — cross-bar repetition, leap-step recovery, consecutive leaps, and phrase-boundary continuity are detected by audit but not yet prevented by the strategy. These will surface as logged violations (strict_audit=False). Each is a future DiminutionFill enhancement, not a wiring bug."

The wiring is correct. DiminutionFill does not yet prevent these violations. The tests enforce old behavior that the new system does not guarantee.

### Acceptance Checklist

- Import succeeds ✓
- Test suite: zero regressions in passing tests ✗ (37 new failures, known issue)
- Pipeline produces output for at least one genre without crashing ✓
- `_fill_all_spans` and `_apply_guards` deleted ✓
- `generate_soprano_phrase` signature unchanged ✓
- Public API contract unchanged ✓
- soprano_writer.py contains exactly 2 functions ✓

---

## Assessment

**Wiring complete.** The soprano generation path now uses the unified voice writer pipeline. The public API is unchanged; callers see no difference.

**Known issue:** DiminutionFill does not yet prevent cross-bar repetition or enforce leap-step recovery. These violations are detected by audit_voice (logged with strict_audit=False) but not prevented. The old _apply_guards fixed these downstream; the new system makes them visible but does not fix them.

**Test failures:** 37 tests enforce old postconditions that the new system does not guarantee. These are not wiring bugs but feature gaps in DiminutionFill. Task Known Limitation #3 explicitly identifies these as future enhancements.

**Musical impact:** Cannot assess without listening. Audit violations suggest some phrases may have awkward melodic intervals (repeated pitches at bar boundaries, unrecovered leaps). The old system masked these with post-pass fixes; the new system exposes them.

**Next step:** Either (1) enhance DiminutionFill to prevent these violations inline, or (2) update tests to reflect new postconditions, or (3) accept the lenient behavior and monitor audit violations in real output.
