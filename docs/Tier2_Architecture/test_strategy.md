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

---

## Layer Contract Tests

Every layer must have a **contract test** that takes the layer's output in isolation and verifies all invariants. These run without invoking any other layer — the input is either a fixture or the output of the previous layer captured as test data.

### Test architecture

```
Unit tests          ->  function-level correctness
Layer contract tests ->  each layer's output satisfies its postconditions
Integration tests    ->  adjacent layers compose correctly
System tests         ->  full pipeline produces valid .note output
```

Layer contract tests answer: "assuming this layer received valid input, did it produce valid output?"

### Layer 1: Rhetorical

**Input**: GenreConfig
**Output**: trajectory, rhythm_vocab, tempo
**Invariants**:
- tempo > 0 and within genre's plausible range
- rhythm_vocab is non-empty
- trajectory length == number of sections in genre config
- all trajectory values are valid affect terms

### Layer 2: Tonal

**Input**: AffectConfig, GenreConfig
**Output**: TonalPlan
**Invariants**:
- every section in genre config has a corresponding TonalPlan section
- every key_area is a valid Roman numeral (I, IV, V, vi, etc.)
- every cadence_type is one of: authentic, half, deceptive, plagal
- final section cadence_type == "authentic"
- density and modality are valid enum values

### Layer 3: Schematic

**Input**: TonalPlan, GenreConfig, FormConfig, schemas
**Output**: SchemaChain
**Invariants**:
- every schema name in the chain exists in the schema catalogue
- section_boundaries length == number of genre sections
- boundaries are monotonically increasing
- boundaries tile the chain exactly: boundary[-1] == len(schemas)
- first schema in first section has position == "opening"
- last schema in each section has cadential_state appropriate to the section's cadence type ("closed" for authentic, "half" for half)
- no two adjacent schemas are identical (no immediate repetition)

### Layer 4: Metric

**Input**: SchemaChain, GenreConfig, FormConfig, KeyConfig, schemas, TonalPlan
**Output**: bar_assignments, anchors, total_bars
**Invariants**:
- bar_assignments: every genre section has an entry
- bar_assignments: ranges tile 1..total_bars with no gaps or overlaps
- anchors: sorted by bar_beat
- anchors: no duplicate bar_beat values
- anchors: every degree is 1-7
- anchors: every local_key is a valid Key
- anchors: first anchor has upper_degree==1, lower_degree==1 in home key
- anchors: last anchor has upper_degree==1, lower_degree==1 in home key
- anchors: anchor count >= 2 (at least start and end)
- anchors: for cadential schemas, the final stage has the correct terminal degrees (soprano 1, bass 1)
- anchors: for half_cadence, the final stage has bass degree 5
- anchors: bar numbers in bar_beat are within 0..total_bars
- anchors: beat numbers are valid for the metre

### Phrase Planner

**Input**: anchors, genre_config, schemas
**Output**: tuple[PhrasePlan, ...]
**Invariants**:
- one PhrasePlan per schema in the chain
- PhrasePlan.schema_degrees_upper matches schema definition
- PhrasePlan.schema_degrees_lower matches schema definition
- degree_placements length == number of schema degrees
- every placement falls within the phrase's bar span
- placements are in chronological order
- rhythm_profile exists in the genre's rhythm cell vocabulary
- is_cadential == True iff schema is cadential type
- start_offset of phrase N+1 == start_offset of phrase N + phrase N's total duration (phrases tile exactly, no gaps)
- prev_exit_pitch is None only for the first phrase

### Phrase Writer -- Soprano

**Input**: PhrasePlan
**Output**: tuple[Note, ...]
**Invariants**:
- note count >= 1
- all pitches within actuator_range
- all durations are in VALID_DURATIONS
- durations sum to exactly the phrase's total bar span
- no timing gaps between consecutive notes
- no timing overlaps between consecutive notes
- the note at each degree_placement offset has the correct scale degree (verified by converting MIDI back to degree via local_key)
- no repeated pitch across bar boundaries (D007)
- no melodic interval > octave (12 semitones)
- leaps (> 4 semitones) are followed by step in contrary direction, except at phrase boundaries
- if is_cadential: final note is degree 1 in local_key

### Phrase Writer -- Bass

**Input**: PhrasePlan, completed soprano notes
**Output**: tuple[Note, ...]
**Invariants**:
- all pitches within bass actuator_range
- all durations are in VALID_DURATIONS
- durations sum to exactly the phrase's total bar span
- no timing gaps or overlaps
- bass note at each degree_placement offset has the correct bass degree
- if is_cadential: final bass note is degree 1 in local_key
- no parallel fifths or octaves on strong beats (checked against soprano)
- no voice overlap with soprano at any offset
- strong-beat notes are consonant with soprano (no seconds, tritones)

### Compose (integration)

**Input**: all phrase outputs concatenated
**Output**: Composition
**Invariants**:
- exactly 2 voices present (for current genres)
- total duration == total_bars * bar_length
- no note in either voice exceeds total duration
- no note has negative offset
- notes within each voice are sorted by offset
- no overlapping notes within the same voice
- first note offset == 0 (or -upbeat for upbeat pieces)
- last note offset + duration == total duration

### Fault scan (existing, unchanged)

**Input**: Composition
**Output**: list of faults
**Invariants**:
- zero faults is the target, but faults are advisory
- every fault has: type, bar, beat, voice, description
- fault types are from a known enum

---

## Contract Test Implementation Rules

1. **One test file per layer.** `tests/test_layer1_rhetorical.py`, etc. Not mixed into other test files.

2. **Fixtures are frozen layer outputs.** Each test file includes a fixture (or loads one from `tests/fixtures/`) that provides the layer's input. The fixture is the known-good output of the previous layer for a specific genre.

3. **Tests are exhaustive on invariants.** Every invariant listed above becomes one test function (or one parametrised case). No invariant is tested "implicitly" by another test.

4. **Tests are genre-parametrised.** Each contract test runs for every genre in the `data/genres/` directory. A new genre automatically gets tested.

5. **Contract tests run in CI before system tests.** If a layer contract test fails, system tests are skipped.

6. **Regression fixtures.** When a bug is found via system test, the failing layer's input is captured as a new fixture and a contract test is added for the specific invariant that was violated.
