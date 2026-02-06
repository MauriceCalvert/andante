# E2: Sequential schema degree expansion

## Steps

- [x] 1. Add `degree_keys: tuple[Key, ...] | None` to PhrasePlan in phrase_types.py
- [x] 2. Add `_expand_sequential_degrees()` to phrase_planner.py
- [x] 3. Call expander in `_build_single_plan` when schema_def.sequential
- [x] 4. Update phrase_writer.py to use degree_keys when resolving degrees
- [x] 5. Update tests P-04/P-05/P-06 to handle sequential schemas
- [x] 6. Run tests — all pass (3492 passed, 209 skipped, 30 xfailed, 39 xpassed)
