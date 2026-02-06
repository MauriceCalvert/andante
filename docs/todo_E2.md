# E2: Sequential schema degree expansion

## Steps

- [ ] 1. Add `degree_keys: tuple[Key, ...] | None` to PhrasePlan in phrase_types.py
- [ ] 2. Add `_expand_sequential_degrees()` to phrase_planner.py
- [ ] 3. Call expander in `_build_single_plan` when schema_def.sequential
- [ ] 4. Update phrase_writer.py to use degree_keys when resolving degrees
- [ ] 5. Update tests P-04/P-05/P-06 to remove sequential skips
- [ ] 6. Run tests
