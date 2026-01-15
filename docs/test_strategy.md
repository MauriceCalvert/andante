# Test Strategy

## Goal

Every tested module is **guaranteed faultless**. Once tested, it never needs retesting unless its source changes. This guarantee requires **zero coupling** between modules under test.

## Core Principle

A test proves correctness **once and forever** when:

1. The module imports only shared types + stdlib
2. All functions are pure (deterministic, no side effects)
3. 100% line and branch coverage achieved
4. All edge cases exercised

If a module imports another module from the same package, its correctness depends on that module. Coupling destroys guarantees.

## Module Categories

### Category A — Pure Functions

Modules that transform `(shared types) → (shared types)`.

**Requirements:**
- Import only from shared types package and stdlib
- All dependencies passed as parameters
- No global state, no I/O, no randomness without seed
- Deterministic: same input always produces same output

**Test approach:**
- One test file per module
- Tests import only shared types + module under test
- No mocks—real inputs, real outputs
- Cover every branch, every boundary

**Example signature:**
```python
def generate_cadence(
    cadence_type: str,
    tonal_target: str,
    key: Key,
    budget: Fraction
) -> tuple[list[FloatingNote], list[Fraction]]:
```

**Example test:**
```python
from shared import Key, FloatingNote
from package.cadence import generate_cadence

def test_authentic_cadence():
    key = Key("C", "major")
    pitches, durations = generate_cadence("authentic", "I", key, Fraction(1))
    assert pitches[-1] == FloatingNote(1)
```

### Category B — Orchestrators

Modules that coordinate Category A modules. Tested via integration after all dependencies proven faultless.

**Examples:** `executor.py`, `expander.py`, `realiser.py`

**Test approach:**
- Integration tests only
- Run after all Category A dependencies pass
- Trust proven components, test orchestration logic only

### Category C — Complex (Requires Decomposition)

Modules too large or coupled for direct testing. Must be split into Category A functions first.

**Examples:** `slice_solver.py`, `inner_voice.py`, `phrase_builder.py`

**Action:** Decompose into smaller pure functions, then test each.

## Zero-Coupling Rule

**Forbidden:**
```python
# test_cadence.py
from package.expander_util import CADENCE_BUDGET  # NO
from package.transform import invert  # NO
```

**Required:**
```python
# test_cadence.py
from shared import Key, FloatingNote  # YES
from package.cadence import generate_cadence  # YES (module under test)
```

If a test needs data from another module in the same package, that data must be:
1. Moved to the shared types package, or
2. Passed as a literal in the test

## Specification-Based Testing

**Critical Principle:** Tests must validate behavior against specifications, not just verify code runs.

A test that passes because it mirrors the implementation proves nothing. Tests must answer: "Does this code implement the specification correctly?"

### What Tests Must Verify

1. **Mathematical Correctness**
   - Scale degree calculations match music theory (degree 1=tonic, 2=supertonic, etc.)
   - Interval arithmetic is correct (4th below = -3 scale degrees)
   - Duration sums equal bar lengths

2. **Domain Invariants**
   - Parallel fifths/octaves never occur
   - Voice ranges stay within bounds
   - Cadences resolve correctly

3. **Integration Contracts**
   - Output of module A matches expected input of module B
   - Data flows correctly through pipeline stages

4. **Edge Cases from Specification**
   - What happens at phrase boundaries?
   - What if treatment list is empty?
   - What if voice count is unusual?

### Anti-Patterns

**Bad:** Test mirrors implementation
```python
def test_degree():
    result = compute_degree(midi=62)
    assert result == ((62 - 60) % 7) + 1  # Just repeating the formula!
```

**Good:** Test against known truth
```python
def test_degree():
    # D4 (MIDI 62) is the 2nd degree in C major
    result = compute_degree(midi=62, key=Key("C", "major"))
    assert result == 2
```

### Bug-Finding Tests

Tests should challenge assumptions, not confirm them:

| Category | Example |
|----------|---------|
| Math | "Is (midi % 7) the right formula for scale degrees?" |
| Music theory | "Does -3 interval really mean 4th below?" |
| Edge cases | "What if treatment tuple is empty?" |
| Integration | "Does VoiceMaterial output match HarmonicContext input?" |

## Coverage Requirements

| Metric | Target |
|--------|--------|
| Line coverage | 100% |
| Branch coverage | 100% |
| Edge cases | Documented and tested |
| Specification conformance | All domain rules verified |

**Enforcement:**
```bash
pytest tests/package/module/ --cov=package.module --cov-fail-under=100 --cov-branch
```

## Test File Structure

```
tests/
  shared/
    test_key.py
    test_pitch.py
    test_types.py
  package/
    test_module_a.py
    test_module_b.py
    ...
  integration/
    test_pipeline_a.py
    test_pipeline_b.py
```

## Faultless Checklist

A module is **faultless** when all boxes checked:

- [ ] Imports only shared types + stdlib
- [ ] All functions pure (no side effects)
- [ ] All dependencies passed as parameters
- [ ] 100% line coverage
- [ ] 100% branch coverage
- [ ] All edge cases documented in tests
- [ ] Type hints on all parameters and returns
- [ ] No mocks used

## Retest Policy

| Change | Action |
|--------|--------|
| Module source changes | Retest module |
| Shared type changes | Retest all modules using that type |
| Test file changes | Rerun affected tests |
| No changes | No retest needed—guarantee holds |

## Hierarchy of Trust

```
Level 0: stdlib (assumed correct)
    ↓
Level 1: shared (tested, frozen)
    ↓
Level 2: Category A pure functions (tested individually)
    ↓
Level 3: Category B orchestrators (integration tested)
```

Each level trusts only the levels above. A Level 2 module never imports from another Level 2 module.

## Randomness

Modules requiring randomness must:
1. Accept a `seed` parameter
2. Use `random.Random(seed)` instance, not global `random`
3. Be deterministic given the same seed

**Example:**
```python
def generate_surprise(phrase: Phrase, seed: int) -> Phrase:
    rng = random.Random(seed)
    ...
```

## Bug Discovery Protocol

When writing tests reveals a bug in the module under test:

1. **Document the bug** — Add to docs/todo.md with clear description
2. **Stop and ask** — Do not fix the bug without explicit approval
3. **Skip affected tests** — Mark tests that expose the bug with `@pytest.mark.skip(reason="Bug: ...")`
4. **Continue coverage** — Write tests for remaining functionality

Bugs discovered during testing are valuable findings—they must be tracked and prioritized.

## Forbidden Patterns

1. **Circular imports** — Architectural failure
2. **Import for constants** — Move constants to shared package
3. **Import for types only** — Types belong in shared package
4. **Mocking sibling modules** — Indicates coupling; refactor instead
5. **Tests with external files** — Use literals or shared fixtures

## Migration Path

1. Extract shared types package
2. Refactor Category A modules to pure functions
3. Write 100% coverage tests for each
4. Decompose Category C into smaller Category A modules
5. Integration test Category B orchestrators
