# Test Remediation — Remaining TODO

Updated: 2026-02-06

Baseline: 1530 passed, 1 failed, 254 skipped, 14 xfailed, 20 xpassed

## Phase D — Extend parametrisation
- [x] 3.1 Dynamic GENRES from filesystem
- [x] 3.2 Dynamic PHRASE_GENRES from cell availability
- [x] 4.1 Minor key testing (KEYS in conftest, L5/L7/system parametrised)
- [ ] 4.2 Multi-affect L5 testing (L5 hardcodes "Zierlich")

## Phase E — Structural improvements
- [ ] 1.3 RhythmCell accent_pattern
- [ ] 1.4 Sequential schema degree expansion

## Additional issues found
- [x] Fix test_phrase_join_intervals[invention]: soprano leap of 14 at offset 18
- [ ] Review 20 xpassed tests — tighten xfail marks where bugs are fixed
- [ ] Replace all range clamps (max/min) in generators with asserts — L003 violation
- [ ] Remove dead PhrasePlan.prev_exit_upper / prev_exit_lower fields
