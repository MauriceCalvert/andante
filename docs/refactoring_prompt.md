# Andante Refactoring Plan Request

> **⚠️ PARTIALLY OUTDATED:** This prompt predates the following architectural changes:
> - Keys are computed from (tonic, mode), no config/keys/ directory
> - Voice ranges replaced by tessituras (medians) per L003
> See architecture.md for current specification.

## Objective

Write a complete, unambiguous, detailed implementation plan to update the Andante baroque music composition system to achieve 100% conformance with `architecture.md` (v1.3.2).

## Context

Andante is a grammar-driven baroque music composition system located at:
```
D:\projects\Barok\barok\source\andante\
```

The architecture specification is the single source of truth:
```
D:\projects\Barok\barok\source\andante\docs\Tier2_Architecture\architecture.md
```

## Current State

The existing codebase has:
- `\engine\` — **OUTDATED, TO BE REPLACED** — contains legacy generation logic that does not conform to architecture
- `\planner\` — **STAYS, TO BE UPDATED** — contains planning logic that needs updating to match architecture
- Various other modules that may or may not conform

## Target State

After implementing this plan:
1. `\engine\` folder is **deleted entirely**
2. `\builder\` folder is **created** with new modules conforming to architecture
3. `\planner\` is **updated in place** to conform to architecture
4. `\config\` folder contains all YAML configurations as specified in architecture
5. The system produces **deterministic, note-for-note identical output** for 2-voice Invention in C Major with Confident affect

## Architecture Summary

Read `architecture.md` in full. Key structural elements:

### Directory Structure (from Implementation Guide)
```
andante/
├── engine/                    # REPLACE WITH builder/
│   ├── counterpoint.py        # Hard rules checker
│   ├── solver.py              # CP-SAT wrapper
│   ├── cost.py                # Weight evaluator
│   ├── realisation.py         # Fills decoration
│   └── io.py                  # MIDI/note output
│
├── config/                    # YAML (changes per genre)
│   ├── genres/
│   ├── schemas/
│   ├── keys/
│   ├── affects/
│   └── forms/
```

### Six Layers
1. **Rhetorical** — Genre → Trajectory + rhythm + tempo (fixed per genre)
2. **Tonal** — Affect → Tonal plan + density + modality (lookup)
3. **Schematic** — Tonal plan → Schema chain (enumerate from rules)
4. **Thematic** — Schema + rhythm → Subject (CP-SAT)
5. **Metric** — Schema chain → Bar assignments + arrival beats (enumerate)
6. **Textural** — Genre + chain + subject → Treatment sequence (lookup)

### Layer 4.5: Motive Constraints
- Motive weighting (stepwise=0.2, skip=0.4, leap=0.8, large=1.5)
- Rhythmic state machine (RUN/HOLD/CADENCE/TRANSITION)
- Counter-decoration rules
- Directional constraints

### Key Specifications
- Global pitch-class set for diatonic mode
- Schema-specific pitch-pair constraints with exact MIDI numbers and bar.beat positions
- Voice registers: soprano C4–G5 (60–79), bass C2–C4 (36–60)
- Solver determinism: lexicographic tie-breaking, no randomisation
- Free passage rules: pentatonic bridge pitch-set, lead-in motion, texture swap

## Deliverables Required

### 1. File-by-File Plan
For each file to be created/modified/deleted, specify:
- Full path
- Action: CREATE / MODIFY / DELETE
- Purpose (one line)
- Dependencies (what it imports/requires)
- Key classes/functions with signatures

### 2. Module Specifications
For each new module in `\builder\`:
- Public interface (all public functions with full type hints)
- Internal structure (private helpers)
- YAML config it reads
- Other modules it depends on

### 3. YAML Schema Definitions
For each YAML file in `\config\`:
- Full path
- Complete schema (all fields, types, required/optional)
- Example content matching architecture

### 4. Planner Updates
For `\planner\`:
- What stays unchanged
- What gets modified (with before/after signatures)
- What gets deleted
- New integration points with `\builder\`

### 5. Implementation Order
Numbered list of implementation steps with:
- Step number
- File(s) to create/modify
- Prerequisites (which steps must complete first)
- Validation criteria (how to verify step is complete)

### 6. Test Specification
For each module:
- Unit test file path
- Key test cases (input → expected output)
- Integration test for full pipeline

## Constraints

1. **PyTorch only** — no TensorFlow, no JAX
2. **One class per file** — methods sorted alphabetically
3. **Type hints on everything** — except loop variables
4. **Assert preconditions** — especially tensor shapes
5. **No blank lines inside functions**
6. **Modules under 100 lines** — unless splitting harms cohesion
7. **Forward slashes** — for all paths
8. **No Greek symbols in code**

## Process

1. First, read the entire `architecture.md` file
2. Then, explore the current `\engine\` and `\planner\` folders to understand existing structure
3. Identify gaps between current state and architecture
4. Write the plan in the order specified above
5. For any ambiguity, ask one clarifying question before proceeding

## Output Format

The plan should be written to:
```
D:\projects\Barok\barok\source\andante\docs\refactoring_plan.md
```

Use markdown with clear headers, tables, and code blocks. The plan must be detailed enough that an implementer can execute each step without additional clarification.

## Success Criteria

The plan is complete when:
- [ ] Every module in architecture.md has a corresponding file specification
- [ ] Every YAML config has a complete schema
- [ ] Every public function has a full signature with types
- [ ] Implementation order has no circular dependencies
- [ ] Test cases cover all hard constraints from architecture
- [ ] Running the implementation produces identical output to `freude_sonata.note`

## Reference Files

Read these files to understand current state:
- `D:\projects\Barok\barok\source\andante\docs\Tier2_Architecture\architecture.md` — THE SPEC
- `D:\projects\Barok\barok\source\andante\engine\` — current (outdated) implementation
- `D:\projects\Barok\barok\source\andante\planner\` — planning logic (to update)
- `D:\projects\Barok\barok\source\andante\output\freude_sonata.note` — target output example
- `D:\projects\Barok\barok\source\andante\output\sonata1.note` — another reference output

Begin by reading architecture.md, then exploring the current codebase, then writing the plan.
