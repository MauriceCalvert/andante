# Planner Test Suite: Status & Issues

Test suite completed January 2026.

## Test Coverage Summary

**All 395 tests passing.**

| Module | Tests | Category |
|--------|-------|----------|
| types | 25 | A |
| solver | 38 | A |
| transition | 28 | A |
| serializer | 25 | A |
| episode_generator | 41 | A |
| arc | 30 | B |
| frame | 24 | B |
| macro_form | 25 | B |
| material | 34 | B |
| subject | 26 | B |
| subject_generator | 15 | B |
| section_planner | 18 | B |
| structure | 21 | B |
| validator | 13 | B |
| planner | 32 | B |
| **Total** | **395** | |

## Production Data Bug

### Missing Arc Definition

**File:** `data/genres/invention.yaml`
**Issue:** References `arc: simple` but `data/arcs.yaml` does not define a `simple` arc.
**Impact:** `plan_structure()` raises `KeyError: 'simple'` when genre is `invention`.
**Workaround:** Tests use `minuet` genre which references valid `dance_stately` arc.
**Fix Required:** Either add `simple` arc to `arcs.yaml` or update `invention.yaml` to use existing arc.

## Behavioral Notes (Not Bugs)

### Transition Type Selection Priority

**File:** `planner/transition.py:select_transition_type()`
**Behavior:** Same-key check (`if from_key == to_key: return "linking"`) precedes character-based checks.
**Effect:** Climax/triumphant characters get `linking` transition when key is unchanged.
**Tests accommodate this by using different keys to exercise cadential transition path.

## Running Tests

```bash
cd /d/projects/Barok/barok && source .venv/Scripts/activate && cd source/andante

# Run all planner tests
python -m pytest tests/planner/ -v

# Run with coverage for specific module
python -m pytest tests/planner/test_<module>.py -v --cov=planner.<module> --cov-branch --cov-report=term-missing
```
