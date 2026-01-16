# Andante Code Review Prompt for Claude Code

Copy and paste this prompt into Claude Code:

---

## Task: Comprehensive Code Review of Andante

You are reviewing the Andante baroque composition system. Your goal is to assess implementation completeness, code quality, and alignment with documented baroque theory.

### Reference Documents

Read these first:
- `source/andante/docs/Tier4_Reference/baroque_literature.md` — Consolidated baroque theory reference
- `source/andante/docs/Tier4_Reference/baroque_plan.md` — Implementation plan with numbered phases

### Codebase Location

- Main source: `source/andante/`
- Tests: `source/andante/tests/` (if present)
- Data files: `source/andante/data/`

### Review Scope

#### 1. Architecture Review

Examine the module structure and answer:
- Does the separation between planner and engine match baroque theory (planning vs realisation)?
- Are responsibilities clearly divided (one major class per file)?
- Is the data flow logical (Brief → Plan → Realisation → Output)?
- Are there circular dependencies or architectural smells?

#### 2. Implementation Completeness

Cross-reference code against `baroque_plan.md` phases:

| Phase | Key Files | Check |
|-------|-----------|-------|
| 1 | voice_checks.py, parallels.py | Parallel 5th/8ve detection, direct motion, dissonance validation, voice overlap |
| 2 | voice_checks.py | Leap compensation, consecutive leaps, tritone outline, augmented intervals |
| 3 | figured_bass.py, harmonization.py | Rule of octave, bass patterns, suspension handling |
| 4 | planner/*.py | Phrase sequence validation, caesura rules, extension methods, period structure |
| 5 | cadence.py | Cadence types, formula generation, soprano-not-on-5th rule |
| 6 | schema.py, schemas.yaml | Schema definitions, selection logic |
| 7 | ornament.py | Appoggiatura duration, trill from upper, mordent rules |
| 8 | motif.py or equivalent | Counter-subject, head/tail extraction, derived motifs |
| 9 | meter handling | Metrical stress validation, rhythmic complement |
| 10 | affect handling | Affect-driven parameter selection |

For each phase, report:
- **Implemented**: What's working
- **Partial**: What's started but incomplete
- **Missing**: What's not implemented at all
- **Incorrect**: What contradicts the theory

#### 3. Code Quality

Assess against these criteria:
- **Type hints**: All parameters and returns typed (except loop vars)?
- **Assertions**: Preconditions and tensor shapes asserted?
- **Constants**: Symbolic constants used (no magic numbers except 0-10)?
- **Docstrings**: Public APIs have single-line docstrings?
- **Line count**: Modules ≤100 lines unless splitting harms cohesion?
- **Method order**: Methods alphabetically sorted within classes?
- **Blank lines**: No blank lines inside functions?
- **One class per file**: Major classes in separate files?

#### 4. Data File Validation

Check YAML/JSON data files against theory:
- `schemas.yaml` — Do schema definitions match Gjerdingen's specifications in baroque_literature.md?
- `cadences.yaml` — Are cadence formulas complete per baroque_plan.md Phase 5?
- `figures.yaml` — Does figured bass coverage match Rule of Octave tables?
- `affects.yaml` (if present) — Do affect mappings follow Mattheson?

#### 5. Test Coverage

- Are there unit tests for voice-leading constraints?
- Are there integration tests for complete piece generation?
- Do tests cover the edge cases mentioned in baroque_plan.md?

### Output Format

Produce a structured report:

```markdown
# Andante Code Review Report

## Executive Summary
[2-3 sentences: overall assessment, critical gaps, recommendation]

## 1. Architecture Assessment
### Strengths
### Issues
### Recommendations

## 2. Implementation Completeness

### Phase 1: Voice-Leading Hard Constraints
- Status: [Complete/Partial/Missing]
- Implemented: [list]
- Missing: [list with file locations where they should go]
- Issues: [any incorrect implementations]

### Phase 2: Melodic Constraints
[same format]

[... phases 3-10 ...]

## 3. Code Quality Findings

### Compliant
[what follows the standards]

### Non-Compliant
[specific files and issues, with line numbers if possible]

## 4. Data File Issues
[specific discrepancies between YAML and theory]

## 5. Test Coverage Gaps
[what's tested, what's not]

## 6. Priority Actions

### Critical (blocks correct output)
1. [action with file location]
2. ...

### High (affects quality)
1. ...

### Medium (improvements)
1. ...

## 7. Estimated Effort
[rough hours per priority category]
```

### Important Notes

- Do NOT modify any files during review
- Use `find` and `grep` to locate implementations
- Read baroque_literature.md Part I carefully for voice-leading rules
- Check baroque_plan.md "Success Criteria" section for validation targets
- Be specific: cite file paths, function names, line numbers where possible
- If you find undocumented features that work well, note them as strengths

### Start

Begin by reading the two reference documents, then list all Python files in `source/andante/`, then proceed systematically through the review scope.
