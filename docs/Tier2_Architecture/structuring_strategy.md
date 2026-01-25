# Structuring Strategy

## Goal

Code is easy to find, easy to read, and easy to test. Small modules and small functions enable 100% coverage with minimal cognitive load.

## Size Limits

| Unit | Limit | Escape Hatch |
|------|-------|--------------|
| Function | 25 lines | Comment justification above function |
| Module | 100 lines | Comment justification at module top |
| Folder depth | 3 levels | None — redesign if deeper needed |

**Line counting:** Executable lines + docstrings. Imports and blank lines between functions do not count.

### Justification Format

When exceeding limits, add a comment explaining why splitting would harm cohesion:

```python
"""Transform system for note sequences.

SIZE: 115 lines — state machine with 8 tightly-coupled transitions.
Splitting would scatter related logic across files.
"""
```

```python
# SIZE: 32 lines — parser with inherent branching, extraction would obscure flow
def parse_transform_spec(spec: str) -> TransformSpec:
    ...
```

## Folder Structure

### Rules

1. **Unique filenames across entire project** — No two files share the same name, regardless of folder. Use suffixes: `transform_ops.py`, `transform_handler.py`.

2. **Maximum 3 folder levels** — `package/core/transform/` is the deepest allowed. If you need a fourth level, redesign.

3. **Single types.py** — All data classes for the package live in one `types.py` at package root. Split only if it exceeds 100 lines, then by domain: `types_music.py`, `types_tree.py`.

4. **Tests mirror source** — `package/core/music_math.py` → `package/tests/core/test_music_math.py`

5. **README.md per folder** — Brief description of folder's purpose and contents.

### Generic Layout

```
package/
├── README.md
├── types.py                    # All data classes
├── core/
│   ├── README.md
│   ├── <concept>_ops.py        # Pure functions for concept
│   └── _<concept>_helpers.py   # Private helpers
├── handlers/
│   ├── README.md
│   └── <concept>_handler.py    # Orchestrators
└── tests/
    ├── test_types.py
    ├── core/
    │   └── test_<concept>_ops.py
    └── handlers/
        └── test_<concept>_handler.py
```

### Andante Reference Structure

The actual andante module structure:

```
andante/
├── planner/               # P1-P7: Brief → YAML
│   ├── planner_types.py   # Brief, Frame, Material, Structure, Plan
│   ├── planner.py         # build_plan orchestrator
│   ├── frame.py           # P1: resolve_frame
│   ├── dramaturgy.py      # P2: rhetorical structure
│   ├── material.py        # P3: subject acquisition
│   ├── subject.py         # Subject class
│   ├── cs_generator.py    # Counter-subject solver
│   ├── structure.py       # P4: build SectionSchema from chain
│   ├── cadence_planner.py # Plan cadence points
│   ├── schema_generator.py # Generate schema chain
│   ├── schema_loader.py   # Load schema definitions
│   ├── subject_validator.py # Validate subject against schema
│   ├── subject_deriver.py # Derive subject from schema
│   ├── harmony.py         # P5: harmonic architecture
│   ├── devices.py         # P6: Figurenlehre
│   ├── coherence.py       # P7: callbacks, surprises
│   ├── validator.py       # Plan validation
│   └── serializer.py      # Plan → YAML
│
├── engine/                # E1-E5: YAML → MIDI
│   ├── engine_types.py    # PieceAST, ExpandedPhrase, RealisedPhrase
│   ├── pipeline.py        # E1-E5 orchestrator
│   ├── plan_parser.py     # E1: YAML → PieceAST
│   ├── texture.py         # E2: voice arrangement
│   ├── expander.py        # E3: piece-level expansion
│   ├── expand_phrase.py   # E3: single phrase
│   ├── voice_expander.py  # N-voice expansion
│   ├── inner_voice.py     # Inner voice solving
│   ├── cpsat_slice_solver.py
│   ├── realiser.py        # E4: degrees → MIDI
│   ├── formatter.py       # E5: output formatting
│   ├── output.py          # Export to MIDI/MusicXML
│   ├── cadence.py
│   ├── schema.py
│   ├── pedal.py
│   └── guards/
│       ├── registry.py
│       └── spacing.py
│
├── shared/                # Cross-cutting (Level 1 in trust hierarchy)
│   ├── types.py           # FloatingNote, MidiPitch, Rest
│   ├── errors.py          # Exception hierarchy
│   ├── validate.py        # Validation functions
│   ├── key.py
│   ├── pitch.py
│   ├── music_math.py
│   ├── constants.py
│   └── tracer.py
│
├── data/                  # YAML configuration
│   ├── affects.yaml
│   ├── treatments.yaml
│   ├── textures.yaml
│   ├── episodes.yaml
│   ├── cadences.yaml
│   └── schemas.yaml
│
└── tests/                 # Mirrors source structure
    ├── planner/
    ├── engine/
    └── shared/
```

## Module Organisation

### Structure Within a Module

```python
"""Module docstring — one line summary.

Longer description if needed.

SIZE: 105 lines — justification if over limit.
"""
# === Imports ===
from fractions import Fraction
from typing import Any

from shared.typedefs import Key, Note
from shared.constants import VALID_DURATIONS

# === Constants ===
DEFAULT_STYLE: str = "uniform"
MAX_ITERATIONS: int = 100


# === Public Functions (alphabetical) ===
def build_offsets(...) -> ...:
    ...


def fill_slot(...) -> ...:
    ...


# === Private Functions (alphabetical) ===
def _fill_uniform(...) -> ...:
    ...


def _fill_varied(...) -> ...:
    ...
```

### When to Split a Module

| Signal | Action |
|--------|--------|
| Exceeds 100 lines | Extract helpers to `_<module>_helpers.py` |
| Contains 2+ unrelated concepts | Split by concept with descriptive names |
| Has public + private functions | Keep together if cohesive; split if private section exceeds 50 lines |
| Single class exceeds 100 lines | Extract methods to mixin or helper module |

### The `_helpers` Convention

Private helper modules are prefixed with underscore:

```
package/core/
├── transform_ops.py        # Public API
└── _transform_helpers.py   # Private, imported only by transform_ops.py
```

Rules for `_helpers` modules:
- Never imported by tests directly
- Never imported by other modules (only by their parent)
- Contain functions too small for their own module but cluttering the parent

## Function Organisation

### Size Guidelines

| Lines | Status |
|-------|--------|
| 1–15 | Ideal |
| 16–25 | Acceptable |
| 26–35 | Requires comment justification |
| 36+ | Must split or provide strong justification |

### Extraction Patterns

**Before (35 lines):**
```python
def process_phrase(phrase: Phrase) -> Result:
    # validation
    if not phrase.notes:
        raise EmptyPhraseError()
    if phrase.duration <= 0:
        raise InvalidDurationError()
    # transformation
    transformed = []
    for note in phrase.notes:
        new_pitch = note.pitch + phrase.transposition
        new_duration = note.duration * phrase.tempo_factor
        transformed.append(Note(new_pitch, new_duration))
    # post-processing
    total = sum(n.duration for n in transformed)
    if total != phrase.target_duration:
        scale = phrase.target_duration / total
        transformed = [Note(n.pitch, n.duration * scale) for n in transformed]
    return Result(transformed)
```

**After (4 × 8 lines):**
```python
def process_phrase(phrase: Phrase) -> Result:
    _validate_phrase(phrase)
    transformed = _transform_notes(phrase)
    adjusted = _adjust_durations(transformed, phrase.target_duration)
    return Result(adjusted)

def _validate_phrase(phrase: Phrase) -> None:
    if not phrase.notes:
        raise EmptyPhraseError()
    if phrase.duration <= 0:
        raise InvalidDurationError()

def _transform_notes(phrase: Phrase) -> list[Note]:
    result: list[Note] = []
    for note in phrase.notes:
        new_pitch = note.pitch + phrase.transposition
        new_duration = note.duration * phrase.tempo_factor
        result.append(Note(new_pitch, new_duration))
    return result

def _adjust_durations(notes: list[Note], target: Fraction) -> list[Note]:
    total = sum(n.duration for n in notes)
    if total == target:
        return notes
    scale = target / total
    return [Note(n.pitch, n.duration * scale) for n in notes]
```

### When Not to Split

Keep a function intact when:
- Splitting would require passing 5+ parameters between fragments
- Logic is a linear pipeline that reads top-to-bottom
- It's a state machine where transitions must be visible together
- Extraction would create single-use functions that obscure flow

Always add justification comment when exceeding 25 lines.

## Naming Conventions

### Files

| Type | Pattern | Example |
|------|---------|---------|
| Pure functions | `<noun>_ops.py` or `<noun>.py` | `transform_ops.py`, `music_math.py` |
| Orchestrators | `<noun>_handler.py` or `<noun>.py` | `material_handler.py`, `expander.py` |
| Types | `types.py` or `<package>_types.py` | `types.py`, `planner_types.py` |
| Private helpers | `_<parent>_helpers.py` | `_transform_helpers.py` |
| Tests | `test_<module>.py` | `test_transform_ops.py` |
| Constants | `constants.py` | `constants.py` |

### Functions

| Purpose | Pattern | Example |
|---------|---------|---------|
| Pure computation | `compute_<noun>` | `compute_offset` |
| Build/create | `build_<noun>` | `build_phrase` |
| Transform | `<verb>_<noun>` | `invert_melody`, `augment_duration` |
| Validate (raises) | `require_<condition>` | `require_positive_duration` |
| Predicate (returns bool) | `is_<condition>` | `is_valid_duration` |
| Check (returns bool) | `has_<condition>` | `has_parallel_fifths` |
| Convert | `<source>_to_<target>` | `notes_to_dicts`, `node_to_notes` |
| Extract | `extract_<noun>` | `extract_pitches` |
| Parse | `parse_<noun>` | `parse_transform_spec` |
| Private helper | `_<descriptive_name>` | `_fill_uniform`, `_validate_phrase` |

### Classes

| Type | Pattern | Example |
|------|---------|---------|
| Data class | Noun, singular | `Note`, `Phrase`, `Transform` |
| Collection wrapper | Noun, plural or collective | `Notes`, `PhraseGroup` |
| Handler/orchestrator | `<Noun>Handler` | `MaterialHandler` |
| Error | `<Noun>Error` | `InvalidDurationError` |

### Constants

```python
# Module-level, UPPER_SNAKE_CASE
MAX_VOICES: int = 4
DEFAULT_TIME_SIGNATURE: tuple[int, int] = (4, 4)
VALID_STYLES: frozenset[str] = frozenset({"uniform", "varied", "long_short"})
```

## Discoverability

### README.md Template

Each folder gets a README:

```markdown
# core/

Pure functions for musical computation. No I/O, no validation, no side effects.

## Modules

| Module | Purpose |
|--------|---------|
| music_math.py | Duration arithmetic, offset computation |
| tree_ops.py | Tree traversal, node extraction |
| transform_ops.py | Pitch/duration transformations |

## Dependencies

Imports only from `shared/` and stdlib.
```

### Module Docstring Template

```python
"""One-line summary of module purpose.

Extended description if needed. Explain the domain concept
this module handles and any important constraints.

Functions:
    build_offsets    — Compute note onset times from durations
    fill_slot        — Generate durations to fill a time slot
    repeat_to_fill   — Repeat motif to exactly fill target duration

SIZE: 105 lines — justification if over limit.
"""
```

### Finding Code

| I want to... | Look in... |
|--------------|------------|
| Find a data class | `types.py` or `<package>_types.py` |
| Find pure computation | `<concept>.py` or `<concept>_ops.py` |
| Find orchestration logic | `<concept>_handler.py` or pipeline module |
| Find validation functions | `shared/validate.py` |
| Find constants | `shared/constants.py` or module-level |
| Find tests for X | `tests/<mirror_path>/test_X.py` |

## Integration with Test Strategy

This document complements `test_strategy.md`:

| Test Strategy Concept | Structuring Implication |
|-----------------------|------------------------|
| Level 1 (shared) | Lives in `shared/` folder |
| Category A (pure functions) | Live in domain folders, no validation |
| Category B (orchestrators) | Live in domain folders, validate then delegate |
| Category C (needs decomposition) | Split until each piece fits Category A |
| Zero coupling | Unique filenames prevent accidental cross-imports |

## Checklist for New Modules

Before adding a new module:

- [ ] Filename is unique across entire project
- [ ] Filename follows naming convention
- [ ] Module has docstring with function index
- [ ] Module is ≤100 lines (or has justification)
- [ ] All functions are ≤25 lines (or have justification)
- [ ] Functions are alphabetically ordered
- [ ] Test file created at mirror location
- [ ] Folder README updated with new module

## Checklist for New Functions

Before adding a new function:

- [ ] Name follows convention (`compute_`, `build_`, `is_`, etc.)
- [ ] Function is ≤25 lines (or has justification)
- [ ] Placed in alphabetical order within module
- [ ] Type hints on all parameters and return
- [ ] Single-line docstring present
- [ ] Test cases added
