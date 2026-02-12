# Phase 16b TODO

## Implementation Tasks
- [x] 1. Add detection functions to shared/counterpoint.py
  - [x] has_parallel_perfect
  - [x] would_cross_voice
  - [x] is_ugly_melodic_interval
  - [x] needs_step_recovery
  - [x] is_cross_bar_repetition
  - [x] has_consecutive_leaps
- [x] 2. Add prevention helper to shared/counterpoint.py
  - [x] find_non_parallel_pitch
- [x] 3. Create shared/phrase_position.py with phrase_zone
- [x] 4. Create shared/pitch_selection.py with select_best_pitch placeholder
- [x] 5. Create tests/shared/test_counterpoint_extended.py
- [x] 6. Create tests/shared/test_phrase_position.py
- [x] 7. Run pytest tests/ (full suite) — expect identical results

## Checkpoint
- [x] Bob: Confirm zero change in musical output (same test results)
- [x] Chaz: Verify each function matches faults.py logic
- [x] Chaz: List all new files and functions
- [x] Chaz: Confirm all new tests pass
- [x] Chaz: Confirm no new imports in bass_writer/soprano_writer
