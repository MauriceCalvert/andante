# andante_engine Refactoring Progress

## Goal
Break andante_engine (60+ modules) into smaller parts testable in complete isolation with 100% coverage.

## Test Strategy
See `docs/test_strategy.md` for full methodology.

**Key principles:**
- Zero coupling: tests import only `andante_shared` + module under test + stdlib
- 100% line and branch coverage
- No mocks - real inputs, real outputs
- Tested = guaranteed faultless

## Progress

### Phase 0: Shared Types Extraction ✅ COMPLETE
- Merged duplicate `Key` classes into `andante_shared/key.py`
- Constants in `andante_shared/constants.py`
- Pitch types in `andante_shared/pitch.py`
- `VoiceMaterial`, `ExpandedVoices` in `andante_shared/types.py`
- `tracer.py` moved to `andante_shared/tracer.py` (project-wide debugging utility)
- Re-export shims: `andante_engine/key.py`, `andante_engine/voice_material.py`

### Phase 1: Category A Module Testing (IN PROGRESS)

**Modules with 100% coverage:**

| Module | Tests | Stmts | Branches | Coverage |
|--------|-------|-------|----------|----------|
| `voice_pair.py` | 19 | 19 | 4 | 100% |
| `voice_entry.py` | 35 | 68 | 10 | 100% |
| `harmonic_context.py` | 37 | 58 | 16 | 100% |
| `validate.py` | 73 | 159 | 32 | 100% |
| `surprise.py` | 30 | 28 | 10 | 100% |
| `energy.py` | 30 | 16 | 0 | 100% |
| `arc_loader.py` | 37 | 71 | 18 | 99%** |
| `annotate.py` | 18 | 29 | 14 | 100% |
| `types.py` | 25 | 122 | 4 | 100% |
| `vocabulary.py` | 38 | 113 | 14 | 100% |
| `andante_shared/tracer.py` | 36 | 90 | 24 | 99%* |
| `tests/engine/shared/test_key.py` | 64 | - | - | 100% |
| `tests/engine/shared/test_types.py` | 25 | - | - | 100% |
| `tests/engine/shared/test_voice_config.py` | 32 | - | - | 100% |
| `tests/engine/shared/test_voice_material.py` | 26 | - | - | 100% |

*tracer.py has 99% branch coverage - one branch (`if TRACE_ENABLED`) cannot be tested as constant is True.
**arc_loader.py has 99% branch coverage - one branch unreachable for valid inputs (4-voice inner voice fallthrough).

**Total tests: 599**

### Additional Test Categories

| Test File | Tests | Purpose |
|-----------|-------|---------|
| `test_integration_contracts.py` | 22 | Module interface contracts |
| `test_adversarial.py` | 30 | Bug-finding, edge cases |

### Bugs Found and Fixed

| Module | Bug | Status |
|--------|-----|--------|
| `harmonic_context.py:66-67` | MidiPitch→degree used `(midi-60)%7+1`, treating semitones as degrees | ✅ FIXED |

**Fix Applied:**
- Added `pc_to_degree(pc, key)` function that maps pitch class to scale degree
- Changed MidiPitch handling to: `midi % 12` → lookup in key's scale → degree
- Chromatic notes (not in scale) now default to degree 1 (tonic)

**Category A modules identified (37 total):**
Pure functions with only stdlib + andante_shared imports:
- ✅ `voice_pair.py`
- ✅ `voice_entry.py`
- ✅ `harmonic_context.py`
- ✅ `validate.py`
- ✅ `surprise.py`
- ✅ `energy.py`
- ✅ `arc_loader.py`
- ✅ `annotate.py`
- ✅ `types.py`
- ✅ `vocabulary.py`
- ⬜ `backtrack.py` (has global state - needs refactor)
- ⬜ `episode.py`
- ⬜ `passage.py`
- ⬜ `schema.py`
- ⬜ `variety.py`
- ⬜ `walking_bass.py`
- ⬜ And others...

**Category A- modules (need TimedMaterial moved to shared):**
- `pedal.py`
- `sequence.py`
- `invertible.py`
- `hemiola.py`
- `melodic_bass.py`
- `cadence.py`
- `cadenza.py`

**Category B modules (orchestrators - integration test later):**
- `executor.py`
- `expander.py`
- `parser.py`
- `realiser.py`
- `phrase_expander.py`
- `voice_expander.py`
- `slice_solver.py`
- `n_voice_expander.py`

### Phase 2: Category A- Refactoring (PENDING)
Move `TimedMaterial` from `andante_executor` to `andante_shared` to enable testing of Category A- modules.

### Phase 3: Category C Decomposition (PENDING)
Break complex modules into smaller pure functions.

### Phase 4: Category B Integration Testing (PENDING)
Integration tests for orchestrators after all dependencies proven.

## Files Modified

### Created
- `andante_shared/key.py` - merged Key class
- `tests/engine/test_voice_pair.py`
- `tests/engine/test_voice_entry.py`
- `tests/engine/test_harmonic_context.py`
- `tests/shared/test_tracer.py`
- `tests/engine/shared/test_key.py`
- `tests/engine/shared/test_types.py`
- `tests/engine/shared/test_voice_config.py`
- `tests/engine/shared/test_voice_material.py`
- `tests/engine/test_validate.py`
- `tests/engine/test_surprise.py`
- `tests/engine/test_energy.py`
- `tests/engine/test_arc_loader.py`
- `tests/engine/test_annotate.py`
- `tests/engine/test_types.py`
- `tests/engine/test_vocabulary.py`
- `tests/engine/test_integration_contracts.py`
- `tests/engine/test_adversarial.py`

### Updated
- `andante_shared/__init__.py` - exports Key
- `andante_engine/key.py` - re-exports from andante_shared
- `andante_engine/voice_material.py` - re-exports from andante_shared
- `andante_executor/realiser.py` - imports Key from andante_shared
- `andante_executor/executor.py` - imports Key from andante_shared

### Deleted
- `andante_executor/key.py` (duplicate)
- `andante_engine/shared/` folder (temporary)
- `tests/test_*.py` (8 legacy files with broken imports)
- `andante_executor/guard_loop.py` (redundant, engine.executor handles execution)

## Running Tests

```bash
cd /d/projects/Barok/barok && source .venv/Scripts/activate && cd source/andante

# Run all tests
python -m pytest tests/ -v

# Run with coverage for specific module
python -m pytest tests/engine/test_voice_pair.py -v --cov=engine.voice_pair --cov-branch --cov-report=term-missing
```

## Next Steps
1. Continue testing remaining Category A modules
2. Move `TimedMaterial` to `andante_shared` to unblock Category A- testing
3. Refactor `backtrack.py` to remove global state
