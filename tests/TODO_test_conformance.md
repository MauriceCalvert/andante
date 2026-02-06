# Test Conformance TODO — test_strategy.md audit

## Violations found

### V1 — Missing type hints on test functions
Strategy: "Type hints on all parameters and returns."
Files: test_L1, test_L2, test_L3, test_L4, test_L5, test_cross_phrase_counterpoint
All test functions and fixtures need `-> None` (tests) or correct return types (fixtures).

### V2 — xfail used instead of skip for bugs
Strategy Bug Discovery Protocol: "Mark tests that expose the bug with @pytest.mark.skip(reason='Bug: ...')"
Files: test_L6 (S-11, CP-04), test_yaml_integrity (genre rhythm cells)

### V3 — Zero-coupling violations in tests
Strategy: "If a test needs data from another module in the same package, that data must be
moved to shared or passed as a literal."
- test_L5: imports `builder.cadence_writer.load_cadence_templates` inside P-04/P-05
- test_L6: imports `builder.cadence_writer` inside S-05/B-05
- helpers.py `get_phrase_genres()` imports `builder.config_loader` and `builder.rhythm_cells`

### V4 — Lenient thresholds instead of strict assertions
Strategy: "100% line and branch coverage" and specification conformance.
- test_L7: C-08 allows 3 overlaps, C-09 allows 8 gaps (strict variants exist but lenient ones also run)
- test_system: FAULT_THRESHOLD = 30, duration_integrity allows 8 issues

### V5 — File structure doesn't mirror source
Strategy: "Tests mirror source structure: tests/shared/, tests/planner/, tests/builder/, tests/integration/"
All test files are flat in tests/. This is structural but low-risk.

### V6 — conftest fixtures lack type hints
`genre_config`, `affect_config` etc. return `Any`. Strategy requires typed returns.

### V7 — Specification-based testing gaps
Some L1 tests verify only structural properties (is int, is positive) without testing
against known musical specifications.

---

## Execution plan

- [x] V1: Add type hints to all test functions and fixtures
- [x] V2: Replace xfail with skip(reason="Bug: ...") per Bug Discovery Protocol
- [x] V3: Remove zero-coupling violations from test imports
- [x] V4: Remove lenient threshold tests, keep only strict variants (skip if they fail)
- [ ] V5: Restructure test directories (deferred — requires updating all imports)
- [x] V6: Type conftest fixtures properly
- [ ] V7: Strengthen specification-based tests (deferred — needs domain review)
