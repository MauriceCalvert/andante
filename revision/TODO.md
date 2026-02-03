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

## Phase 6a: Skeleton + PillarStrategy
- [x] Design complete (phase6_design.md)
- [x] builder/compose.py — entry point
- [x] builder/voice_writer.py — VoiceWriter class
- [x] builder/writing_strategy.py — WritingStrategy ABC
- [x] builder/pillar_strategy.py — PillarStrategy
- [x] builder/voice_checks.py — consonance, parallels, range, strong-beat checks
- [x] builder/figuration_strategy.py — FigurationStrategy (filter pipeline)
- [x] builder/cadential_strategy.py — CadentialStrategy
- [x] builder/staggered_strategy.py — StaggeredStrategy
- [x] builder/junction.py — junction checking
- [x] Review all Phase 5+6a code against designs and laws.md
- [x] Write smoke test: revision/test_smoke_pillar.py (5/5 pass)
- [x] Commit Phase 5+6a

## Phase 6b: FigurationStrategy core
- [x] Implement filter pipeline in figuration_strategy.py
- [x] Reuse get_diminutions(), compute_rhythmic_distribution(), sort_by_weight()
- [x] Fallback to pillar if all figures rejected

## Phase 6c: Counterpoint checking
- [x] Wire voice_checks.py into candidate_filter callback
- [x] check_consonance, check_parallels, check_direct_motion, check_range, check_strong_beat_consonance
- [x] revision/test_counterpoint.py (7/7 pass)

## Phase 6d: Sequencing strategies
- [x] independent — default, each gap independent
- [x] repeating — transpose figure across gaps
- [x] static — reuse figure unchanged
- [x] revision/test_sequencing.py (2/2 pass)
- [ ] accelerating, relaxing, dyadic (Fortspinnung) — DEFERRED

## Phase 6e: Anacrusis support
- [x] Handle anacrusis in VoiceWriter._compose_anacrusis
- [x] revision/test_sequencing.py (2/2 pass for anacrusis)

## Phase 7: Enrich planner output
- [x] planner/voice_planning.py — build_composition_plan()
- [x] Schema section detection from anchors
- [x] Sequencing assignment (repeating for sequential schemas)
- [x] Affect-driven density/character per GapPlan
- [x] Function-based writing mode selection
- [x] Hemiola near cadences in triple metre
- [x] Anacrusis support from genre upbeat
- [x] planner/planner.py — now calls voice_planning directly
- [x] Tests updated: warn-and-continue behavior

## Phase 8: Delete old builder execution path
- [ ] Delete builder/bridge.py (now superseded by voice_planning.py)
- [ ] Delete builder/realisation.py, realisation_bass.py, realisation_util.py
- [ ] Delete or simplify constraints.py, costs.py, solver.py, greedy_solver.py
- [ ] Delete builder/figuration/ directory (176KB) if no longer needed

## Phase 9: Integration + faults.py updates
- [ ] faults.py: accept actuator ranges, check all voice pairs
- [ ] Compose all YAML pieces, assert zero faults
- [ ] Compare MIDI output with pre-revision for musical plausibility

---

## Current Test Summary
- revision/test_pitch.py: 15 passed
- revision/test_smoke_pillar.py: 5 passed  
- revision/test_counterpoint.py: 7 passed
- revision/test_sequencing.py: 4 passed
- **Total: 31 passed**

## Pipeline Test
```
from planner.planner import generate
result = generate('invention', 'Zaertlichkeit')
# Voices: ['upper', 'lower']
# Upper notes: 49
# Lower notes: 37
# Tempo: 105, Metre: 4/4
```
