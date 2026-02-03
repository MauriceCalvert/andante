this file and status.md must be updated after every step.

# Revision TODO

## Phase 1: Delete dead wood
- [x] Delete unused modules and functions per unused_items.txt

## Phase 2: Voice entity model (DEFERRED)
- [ ] Implement voices.md entity model in shared/

## Phase 3: NoteFile → voice-dict (DEFERRED)
- [ ] Replace NoteFile with dict[str, tuple[Note, ...]]

## Phase 4: Anchor field rename (DEFERRED)
- [ ] soprano_degree → upper_degree etc.

## Phase 5: VoicePlan contract
- [x] Design complete (phase5_design.md v0.3.0)
- [x] shared/diatonic_pitch.py — DiatonicPitch dataclass
- [x] shared/plan_types.py — CompositionPlan, VoicePlan, SectionPlan, GapPlan, PlanAnchor, WritingMode
- [x] shared/voice_types.py — Role, Range, Actuator, Voice, etc.
- [x] shared/key.py — diatonic_to_midi(), midi_to_diatonic()
- [x] revision/test_pitch.py — property tests (15/15 pass)
- [x] Commit Phase 5

## Phase 6: VoiceWriter + Strategies
- [x] builder/compose.py — entry point
- [x] builder/voice_writer.py — VoiceWriter class
- [x] builder/writing_strategy.py — WritingStrategy ABC
- [x] builder/pillar_strategy.py — PillarStrategy
- [x] builder/figuration_strategy.py — FigurationStrategy (filter pipeline)
- [x] builder/cadential_strategy.py — CadentialStrategy
- [x] builder/staggered_strategy.py — StaggeredStrategy
- [x] builder/voice_checks.py — consonance, parallels, range, strong-beat checks
- [x] builder/junction.py — junction checking
- [x] Sequencing: independent, repeating, static
- [x] Anacrusis support
- [x] revision/test_smoke_pillar.py, test_counterpoint.py, test_sequencing.py

## Phase 7: Enrich planner output
- [x] planner/voice_planning.py — build_composition_plan()
- [x] Schema section detection from anchors
- [x] Sequencing assignment (repeating for sequential schemas)
- [x] Affect-driven density/character per GapPlan
- [x] Function-based writing mode selection
- [x] planner/planner.py — now calls voice_planning directly

## Phase 8: Delete old builder execution path
- [x] Delete builder/bridge.py
- [x] Delete builder/realisation.py, realisation_bass.py, realisation_util.py
- [x] Delete builder/constraints.py, costs.py, solver.py, greedy_solver.py
- [x] Delete builder/slice.py, counterpoint.py, instrument_loader.py
- [x] Delete builder/figuration/{11 dead files}
- [x] Delete planner/melodic.py
- [x] Retain: figuration/{loader, types, rhythm_calc, bass}.py

## Phase 9: Integration + faults.py updates
- [x] faults.py: added actuator_ranges parameter
- [x] faults.py: added find_faults_from_composition() helper
- [x] figuration_strategy.py: graceful fallback for missing intervals
- [x] revision/test_integration.py — 6 tests (all pass)

---

## Current Test Summary
- revision/test_pitch.py: 15 passed
- revision/test_smoke_pillar.py: 5 passed  
- revision/test_counterpoint.py: 7 passed
- revision/test_sequencing.py: 4 passed
- revision/test_integration.py: 6 passed
- **Total: 37 passed**

## Code Deleted
- **6,918 lines removed** (dead builder code)

## Pipeline Status
```
from planner.planner import generate
result = generate('invention', 'Zaertlichkeit')
# Upper: 49 notes, Lower: 37 notes
# Faults: 10 (cross_relation:4, parallel_rhythm:2, ugly_leap:2, dissonance:2)
# No parallel fifths/octaves, no grotesque leaps
```

## Remaining builder/figuration files (kept for loader/types)
- __init__.py
- bass.py (validation)
- loader.py (diminutions, templates)
- rhythm_calc.py (rhythmic distribution)
- types.py (Figure, RhythmTemplate, etc.)
