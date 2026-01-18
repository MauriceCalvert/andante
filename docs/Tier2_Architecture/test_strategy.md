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

## Hierarchy of Trust

```
Level 0: stdlib (assumed correct)
    ↓
Level 1: shared (tested, frozen — includes types, constants, validators, errors)
    ↓
Level 2: Pure functions (tested individually, assume valid input)
    ↓
Level 3: Orchestrators (integration tested, responsible for validation)
```

Each level trusts only the levels above. A Level 2 module never imports from another Level 2 module.

## Module Categories

### Category A — Pure Functions

Modules that transform `(shared types) → (shared types)`.

**Requirements:**
- Import only from shared package and stdlib
- All dependencies passed as parameters
- No global state, no I/O, no randomness without seed
- Deterministic: same input always produces same output
- **No input validation** — assume all inputs valid

**Test approach:**
- One test file per module
- Tests import only shared types + module under test
- No mocks — real inputs, real outputs
- Cover every branch, every boundary

**Example:**
```python
def generate_cadence(
    cadence_type: str,
    tonal_target: str,
    key: Key,
    budget: Fraction
) -> tuple[list[FloatingNote], list[Fraction]]:
```

```python
from shared import Key, FloatingNote
from engine.cadence import generate_cadence

def test_authentic_cadence():
    key = Key("C", "major")
    pitches, durations = generate_cadence("authentic", "I", key, Fraction(1))
    assert pitches[-1] == FloatingNote(1)
```

### Category B — Orchestrators

Modules that coordinate Category A modules. Responsible for validating inputs before calling pure functions.

**Examples:** `pipeline.py`, `expander.py`, `realiser.py`

**Requirements:**
- Validate all external inputs using shared validators
- Raise typed exceptions from shared.errors on invalid input
- Call Category A functions only with known-valid data

**Test approach:**
- Integration tests only
- Run after all Category A dependencies pass
- Trust proven components, test orchestration logic only
- Test validation paths raise correct exceptions

### Category C — Complex (Requires Decomposition)

Modules too large or coupled for direct testing. Must be split into Category A functions first.

**Action:** Decompose into smaller pure functions, then test each.

## Validation Strategy

### Where Validation Lives

| Location | Purpose | Raises |
|----------|---------|--------|
| `shared/validate.py` | Reusable validation functions | `shared.errors.*` |
| Category B orchestrators | Input validation before calling Category A | `shared.errors.*` |
| Category A pure functions | **None** | **Nothing** |

### Validation Functions

Validation functions live in `shared/validate.py` and raise typed exceptions:

```python
# shared/validate.py
from fractions import Fraction
from shared.errors import InvalidDurationError, InvalidCountError

def require_positive_duration(duration: Fraction, name: str = "duration") -> None:
    """Raise if duration is not positive."""
    if duration <= 0:
        raise InvalidDurationError(f"{name} must be positive: {duration}")

def require_positive_int(value: int, name: str = "value") -> None:
    """Raise if value is not a positive integer."""
    if value <= 0:
        raise InvalidCountError(f"{name} must be positive: {value}")
```

### Exception Hierarchy

All domain exceptions live in `shared/errors.py`:

```python
# shared/errors.py
class BarokError(Exception):
    """Base exception for all Barok errors."""

class ValidationError(BarokError):
    """Base for input validation errors."""

class InvalidDurationError(ValidationError):
    """Duration is invalid or out of range."""

class InvalidCountError(ValidationError):
    """Count or quantity is invalid."""
```

### Orchestrator Pattern

Category B orchestrators validate, then delegate:

```python
from shared.validate import require_positive_duration, require_positive_int
from engine.music_math import fill_uniform

def fill_slot(target: Fraction, note_count: int, style: str) -> list[Fraction]:
    """Fill target duration with notes. Validates inputs."""
    require_positive_duration(target, "target")
    require_positive_int(note_count, "note_count")
    if style not in VALID_STYLES:
        raise InvalidStyleError(f"Unknown style: {style}")
    return fill_uniform(target, note_count)  # Pure function, no validation
```

## Asserts: When and Where

### Forbidden

Asserts for **input validation** in Category A modules. Tests prove correctness; validation happens in Category B.

**Bad:**
```python
# Category A module
def fill_uniform(target: Fraction, note_count: int) -> list[Fraction]:
    assert target > 0, f"target must be positive: {target}"  # NO
    assert note_count > 0, f"note_count must be positive"    # NO
    ...
```

### Permitted

Asserts for **internal invariants** — impossible states that indicate bugs in the algorithm itself, not bad input. These are rare.

**Acceptable:**
```python
def _internal_step(state: State) -> State:
    # Algorithm invariant: state.phase is always A or B here
    # If not, the algorithm has a bug
    assert state.phase in {Phase.A, Phase.B}, f"Corrupt state: {state.phase}"
    ...
```

### Summary

| Assert Type | Category A | Category B | Tests |
|-------------|------------|------------|-------|
| Input validation | ✗ Forbidden | ✗ Use exceptions | ✓ Use pytest.raises |
| Internal invariants | ✓ Rare, permitted | ✓ Rare, permitted | N/A |
| Test assertions | N/A | N/A | ✓ Required |

## Zero-Coupling Rule

**Forbidden:**
```python
# test_cadence.py
from engine.expander_util import CADENCE_BUDGET  # NO — sibling import
from engine.transform import invert              # NO — sibling import
```

**Required:**
```python
# test_cadence.py
from shared import Key, FloatingNote  # YES — Level 1
from engine.cadence import generate_cadence  # YES — module under test
```

If a test needs data from another module in the same package, that data must be:
1. Moved to the shared package, or
2. Passed as a literal in the test

## Specification-Based Testing

**Critical Principle:** Tests must validate behaviour against specifications, not just verify code runs.

A test that passes because it mirrors the implementation proves nothing. Tests must answer: "Does this code implement the specification correctly?"

### What Tests Must Verify

1. **Mathematical Correctness**
   - Scale degree calculations match music theory
   - Interval arithmetic is correct
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

## Coverage Requirements

| Metric | Target |
|--------|--------|
| Line coverage | 100% |
| Branch coverage | 100% |
| Edge cases | Documented and tested |
| Specification conformance | All domain rules verified |

**Enforcement:**
```bash
pytest tests/engine/cadence/ --cov=engine.cadence --cov-fail-under=100 --cov-branch
```

## Test File Structure

Tests mirror source structure:

```
tests/
  shared/
    test_errors.py
    test_validate.py
    test_key.py
    test_pitch.py
    test_types.py
  planner/
    test_frame.py
    test_structure.py
  engine/
    test_cadence.py
    test_expander.py
  integration/
    test_pipeline.py
```

## Faultless Checklist

A module is **faultless** when all boxes checked:

- [ ] Imports only shared types + stdlib
- [ ] All functions pure (no side effects)
- [ ] All dependencies passed as parameters
- [ ] No input validation asserts (validation in caller)
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
| No changes | No retest needed — guarantee holds |

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

## Forbidden Patterns

1. **Circular imports** — Architectural failure
2. **Import for constants** — Move constants to shared package
3. **Import for types only** — Types belong in shared package
4. **Mocking sibling modules** — Indicates coupling; refactor instead
5. **Tests with external files** — Use literals or shared fixtures
6. **Asserts for input validation** — Use typed exceptions in orchestrators
7. **Validation in pure functions** — Validation belongs in callers

## Migration Path

For existing modules with asserts:

1. Create `shared/errors.py` with exception hierarchy
2. Create `shared/validate.py` with validation functions
3. Extract shared types to shared package
4. Refactor Category A modules to pure functions (remove validation asserts)
5. Write 100% coverage tests for each Category A module
6. Add validation calls to Category B orchestrators
7. Decompose Category C into smaller Category A modules
8. Integration test Category B orchestrators
