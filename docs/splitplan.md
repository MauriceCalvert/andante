# Andante Split Plan

## Goal

Split monolithic andante (7818 SLOC) into four packages with pure YAML/dataclass interfaces:

- **andante-planner**: Brief → Plan YAML
- **andante-engine**: Plan YAML → Expanded YAML
- **andante-executor**: Expanded YAML → MIDI/MusicXML
- **andante-shared**: Types, constants, utilities

## Package Boundaries

### andante-shared

Types and constants used across packages. No logic, no dependencies except stdlib.

```
Fraction (from stdlib)
Motif(degrees, durations, bars)
FloatingNote(degree)  # 1-7 scale degree
Rest
VoiceMaterial(voice_index, pitches: list[FloatingNote|Rest], durations)
ExpandedPhrase(index, voices: list[VoiceMaterial], cadence, tonal_target, ...)
```

Constants:
- Scale degree mappings
- Valid durations
- Tonal target mappings (I, V, vi, etc.)

### andante-planner

**Input**: Brief YAML
```yaml
brief:
  affect: dolore
  genre: trio_sonata
  forces: keyboard
  bars: 32
```

**Output**: Plan YAML (current `_full.yaml` format)
```yaml
brief: ...
frame: ...
material:
  subject: {degrees, durations, bars}
  counter_subject: {degrees, durations, bars}
  derived_motifs: [...]
structure:
  arc: dialogue
  sections:
    - label: A
      episodes:
        - type: statement
          bars: 4
          phrases: [...]
```

**Dependencies**: andante-shared, pyyaml, ortools (for CSP solver)

**Current files**:
- planner/*.py (all)
- data/affects.yaml, arcs.yaml, genres/*.yaml, etc.

### andante-engine

**Input**: Plan YAML (from planner)

**Output**: Expanded YAML
```yaml
frame: {key, mode, metre, tempo, voices}
phrases:
  - index: 0
    bars: 4
    voices:
      - voice_index: 0
        degrees: [1, 5, 4, 3, 2, 1, 7, 1, ...]
        durations: [1/4, 1/8, 1/8, ...]
      - voice_index: 1
        degrees: [3, 3, 4, 1, ...]
        durations: [1/8, 3/16, ...]
      - voice_index: 2
        degrees: [1, 5, 1, 4, ...]
        durations: [1, 1, 1, 1, ...]
    cadence: half
    tonal_target: I
```

Note: Output is still in FloatingNote degrees, not MIDI. Key/mode in frame allows executor to resolve.

**Dependencies**: andante-shared, pyyaml

**Current files** (to extract from engine/):
- expander.py (expansion logic only, not realization)
- voice_pipeline.py
- episode_registry.py
- cadence.py (degree-level cadence patterns)
- treatments.yaml, episodes.yaml
- Motif transforms (invert, retrograde, augment, etc.)

**NOT in engine**:
- realiser.py (MIDI conversion)
- guard_backtrack.py (needs MIDI for parallel fifths)
- slice_solver.py (needs MIDI)
- output.py (music21)

### andante-executor

**Input**: Expanded YAML (from engine)

**Output**: MIDI, MusicXML, .note files

**Dependencies**: andante-shared, pyyaml, music21

**Current files**:
- executor/*.py
- engine/realiser.py
- engine/guard_backtrack.py
- engine/slice_solver.py
- engine/output.py
- engine/key.py (MIDI conversion)

## Interface Files

Each package boundary has a YAML schema:

1. `schemas/brief.yaml` - Input to planner
2. `schemas/plan.yaml` - Planner output, engine input
3. `schemas/expanded.yaml` - Engine output, executor input

## The Guard Problem

Guards (parallel fifths, octaves) need MIDI pitches to detect. But the retry loop is currently in expander.

**Options**:

A. **Guards in executor**: Engine produces candidates, executor validates and requests retry via return value. Requires engine to be stateless/deterministic given seed.

B. **Guards in engine with MIDI preview**: Engine imports minimal pitch resolution from shared. Leaky but practical.

C. **Two-phase executor**: First phase realizes and validates, second phase outputs. Retry loop in executor.

**Recommendation**: Option C. The retry loop moves to executor. Engine is pure expansion. Executor does:
1. Realize phrase to MIDI
2. Check guards
3. If fail, call engine with different seed
4. If pass, accumulate and continue

This requires engine to accept a seed parameter and be deterministic.

## The Subject Problem

Subject class currently:
- Generates counter-subjects (planner concern)
- Extends motifs to budget (engine concern)

**Split**:
- `planner/subject_generator.py`: CSP-based CS generation, outputs Motif
- `engine/motif_expander.py`: Cycles/trims motifs to budget

Material in Plan YAML includes pre-generated subject and counter_subjects. Engine doesn't generate new material, only expands what's in the plan.

## Migration Steps

1. **Create andante-shared**: Extract types to new package, update imports
2. **Define YAML schemas**: Document current Plan YAML format as schema
3. **Extract planner**: Already mostly isolated, just fix imports
4. **Define Expanded YAML**: New interface, doesn't exist yet
5. **Split engine from executor**: The hard part - untangle expander.py
6. **Move guards to executor**: Implement retry loop in executor
7. **Integration tests**: Ensure Brief → MIDI still works across packages

## File Counts (Estimated)

| Package | Files | SLOC |
|---------|-------|------|
| andante-shared | ~5 | ~200 |
| andante-planner | ~15 | ~1500 |
| andante-engine | ~20 | ~2500 |
| andante-executor | ~15 | ~2000 |
| tests | ~10 | ~1000 |
| data/schemas | ~3 | ~100 |

## Risk

The engine/executor split is non-trivial. expander.py is 600+ lines mixing expansion and realization. Will require careful extraction.

## Benefit

- Smaller codebases for Claude to work with
- Clear contracts via YAML schemas
- Planner can run without music21
- Engine can be tested without I/O
- Each package independently versionable
