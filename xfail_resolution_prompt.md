# Resolve 18 xfailed tests

Read `claude.md`, then `docs/Tier1_Normative/laws.md` and `docs/knowledge.md`.

Write a todo to `xfail_todo.md` before starting, tick items off as you go.

## Context

The test suite has 18 `pytest.xfail()` calls guarding known generator bugs. All are inline conditional xfails (not decorator-level). The goal is to fix the root causes so the xfails can be removed. Run `python -m pytest tests/test_L7_compose.py tests/test_system.py -v --tb=no 2>&1 | grep XFAIL` to see them.

## Three root causes

### 1. Minor key cadence bug (10 xfails)

Tests: `test_final_soprano_tonic`, `test_final_bass_tonic` (L7), `test_correct_final_degree` (system) for bourree_a_minor, invention_a_minor, minuet_a_minor, gavotte_a_minor.

The planner's cadential schema degrees don't resolve to tonic in minor keys. The final soprano and/or bass degree ends up on the wrong scale degree. The fix is in the planner cadence logic — the cadenza_semplice and cadenza_composta schemas must resolve correctly in minor mode. Check `planner/metric/pitch.py` and `planner/metric/schema_anchors.py` for how final anchor degrees are assigned.

### 2. Gavotte voice-crossing workaround (6 xfails)

Tests: `test_final_bass_tonic`, `test_final_unison_or_octave` (L7), `test_correct_final_degree`, `test_zero_parallel_perfects` (system) for gavotte_c_major and gavotte_a_minor.

`_select_strong_beat_bass` in the builder picks pitch ≤ soprano_pitch, which allows unison. When soprano is low, bass gets clamped to soprano pitch, causing parallel unisons (C4/C4 → B3/B3) and wrong final bass degree. The fix must ensure bass stays below soprano with proper separation. Check `builder/voice_writer.py` or `builder/figuration/bass.py` for `_select_strong_beat_bass`.

### 3. Invention parallel octaves from pillar strategy (2 xfails)

Tests: `test_zero_parallel_perfects` (system) for invention_c_major and invention_a_minor.

The pillar strategy sustains/repeats anchor notes without checking for parallel perfect intervals against the other voice. Check `builder/pillar_strategy.py` and `builder/voice_checks.py` — the candidate_filter should catch parallels but may not be called during pillar note selection.

## Rules

- Fix at source (D008). No downstream fixes.
- Guards detect, generators prevent (D010).
- Natural minor for melody; raised 6/7 cadential only (L007).
- No try/except (L001). Assert preconditions.
- Deterministic builder (A005).
- After fixing each root cause, run only the affected tests to confirm, then remove the corresponding xfail guards.
- Final validation: `python -m pytest tests/test_L7_compose.py tests/test_system.py tests/test_cross_phrase_counterpoint.py --tb=short` — target: 0 xfailed, 0 failures.
