# Continue — CP-SAT prototype scaling + documentation (2026-02-23)

## What happened this session

### 1. CP-SAT prototype fixed for scaling

Original prototype used `enumerate_all_solutions` which crashed at 9 notes
(exponential time). Tested three sampling strategies:

**Strategy 1: Random restarts with solution limit.** Each restart uses a
different `random_seed`. Result: severe clustering — nearly all solutions
started `(0, 1, 0, 1, ...)`. Different seeds don't push the solver into
different regions of feasible space. 529 distinct at 8 notes (vs 4,120
from enumerate-all).

**Strategy 2: Random linear objective per restart.** Random weights on each
pitch position, then `maximize`. Result: good diversity but very few
solutions per restart — optimisation mode only fires the callback for
improving solutions. 94 distinct at 8 notes.

**Strategy 3: Two-phase (adopted).** Phase A: random objective finds one
diverse anchor. Phase B: feasibility enumeration from anchor neighbourhood
via `add_hint`. Result: good diversity AND good yield. 903 distinct at
8 notes, 1,369 at 9, 1,559 at 10. All within 35s budget.

### 2. Production integration confirmed working

The CP-SAT generator (`cpsat_generator.py`) was already wired into
`pitch_generator.py` from a previous session. Verified:
- Cache files are fresh (`cpsat_pitch_8n_major_k4.pkl` etc.)
- All 6 generated subjects in `motifs/subjects/` use CP-SAT output
- Old `generate_pitch_sequences` is dead code (defined, never called)
- Stretto filter in `selector.py` still active (real-duration evaluation)

### 3. Documentation updated

- `cpsat_brief.md`: Updated status to "Integrated", added prototype
  comparison table, current output table, architecture diagram, known
  limitations.
- `cpsat_design.md`: Updated status to "Implemented", replaced sampling
  strategy section with two-phase description, updated integration plan
  to "completed", updated risks/mitigations to reflect outcomes, marked
  all acceptance criteria as MET, added two-phase prototype results to
  appendix.

### Files changed
- `motifs/subject_gen/cpsat_prototype.py` — rewritten with two-phase sampling
- `workflow/cpsat_brief.md` — full rewrite reflecting integration
- `workflow/cpsat_design.md` — status, sampling, integration, risks, criteria updated

### What needs attention next
1. **Remove dead code.** `generate_pitch_sequences` in `pitch_generator.py`
   is defined but never called. Safe to delete.
2. **Contour diversity.** All 6 subjects are "arch". The scorer favours arch
   shapes — this is a scoring problem, not a CP-SAT problem. The pool
   contains diverse contours but they score lower.
3. **Even-duration stretto gap.** CP-SAT guarantees stretto at primary offset
   with even durations. Real-duration evaluation is stricter. Joint
   pitch+duration model would close this gap but is complex.
4. **Minor mode.** Consonance table switches automatically via
   `NATURAL_MINOR_SCALE` but not yet exercised in production.
