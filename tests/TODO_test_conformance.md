# Test Conformance TODO — test_strategy.md audit

## Completed

- [x] V1: Add type hints to all test functions and fixtures
- [x] V2: Replace xfail with skip(reason="Bug: ...") per Bug Discovery Protocol
- [x] V3: Remove zero-coupling violations from test imports
- [x] V4: Remove lenient threshold tests, keep only strict variants (skip if they fail)
- [x] V6: Type conftest fixtures properly

## Outstanding

### ~~Issue 1 — Pre-existing bug: bass.py metre='any' blocks L6 test collection~~ ✅ DONE

`test_L6_phrase_writer.py` fails at collection time because `_build_all_fixtures()` calls
`load_configs()` which eventually reaches `bass.py:_get_beats_per_bar(metre='any')` and asserts.

The root cause: `data/figuration/bass_patterns.yaml` contains entries with `metre: any`.
`_get_beats_per_bar` cannot resolve "any" to a numeric value, and shouldn't need to —
"any" means the pattern applies regardless of metre. The validation path
`load_genre -> validate_bass_treatment -> get_bass_patterns -> load_bass_patterns -> _parse_beat_position`
should not be calling `_get_beats_per_bar` for metre="any" entries.

Fix must follow D001 (validate, don't fix) and the project rule that obvious defaults are
forbidden — "any" is a legitimate wildcard, not an error. The fix belongs in
`_parse_beat_position` or `load_bass_patterns`: skip beat-position parsing for metre="any"
entries, or handle "any" as a distinct case before calling `_get_beats_per_bar`.

Files: `builder/figuration/bass.py`, `data/figuration/bass_patterns.yaml` (read-only reference).

### ~~Issue 2 — V5: Test directory structure doesn't mirror source~~ ✅ DONE

Strategy says: tests/shared/, tests/planner/, tests/builder/, tests/integration/.
Currently all test files are flat in tests/.

Mapping:
- tests/test_key.py -> tests/shared/test_key.py
- tests/test_music_math.py -> tests/shared/test_music_math.py
- tests/test_L1_rhetorical.py -> tests/planner/test_L1_rhetorical.py
- tests/test_L2_tonal.py -> tests/planner/test_L2_tonal.py
- tests/test_L3_schematic.py -> tests/planner/test_L3_schematic.py
- tests/test_L4_metric.py -> tests/planner/test_L4_metric.py
- tests/test_L5_phrase_planner.py -> tests/builder/test_L5_phrase_planner.py
- tests/test_L6_phrase_writer.py -> tests/builder/test_L6_phrase_writer.py
- tests/test_L7_compose.py -> tests/builder/test_L7_compose.py
- tests/test_yaml_integrity.py -> tests/data/test_yaml_integrity.py
- tests/test_system.py -> tests/integration/test_system.py
- tests/test_cross_phrase_counterpoint.py -> tests/integration/test_cross_phrase_counterpoint.py

Each subdirectory needs an empty __init__.py (L018).
conftest.py and helpers.py stay in tests/ root.
Update any relative imports if needed.

### ~~Issue 3 — V7: Weak specification-based tests in L1~~ ✅ DONE

Some test_L1_rhetorical.py tests only check structural properties (isinstance, > 0)
rather than validating against known musical specifications.

Examples of what needs strengthening:
- R-01 (trajectory selection): verify that specific genres produce specific trajectories
  per the rhetoric YAML data, not just that the result is a non-empty string
- R-02 (tempo): verify that specific genres produce tempos within their documented BPM
  ranges from the genre YAML, not just that tempo > 0
- R-03 (rhythm vocabulary): verify that returned rhythm values are valid Fractions from
  VALID_DURATIONS in shared/constants.py, and that genre-specific rhythmic_unit constraints
  are respected

Reference files for ground truth:
- data/rhetoric/archetypes.yaml (trajectory mappings)
- data/genres/*.yaml (tempo ranges, rhythmic_unit)
- shared/constants.py (VALID_DURATIONS)

Tests must remain Category B (integration) — they test the orchestrator, so imports from
builder.config_loader for fixture setup are acceptable. The fix is replacing weak assertions
with specification-derived expected values.
