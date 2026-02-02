# Continue: Andante Revision — Phase 6 Implementation

Read `claude.md` first, then these files in order:

1. `revision/revision_plan.md` — 9-phase plan, what to touch, what not to touch
2. `revision/phase5_design.md` — DiatonicPitch, VoicePlan contract, fault analysis
3. `revision/phase6_design.md` — VoiceWriter, WritingStrategy, counterpoint checking

## Current state

**Phase 1** (dead wood deletion): COMPLETE, committed (HEAD = f68e984).

**Phases 2–4** (Voice entity model, NoteFile→voice-dict, Anchor rename): DEFERRED. Not blocking Phase 6.

**Phase 5** (VoicePlan contract): CODED, NOT COMMITTED. New files:
- `shared/diatonic_pitch.py` — DiatonicPitch dataclass
- `shared/plan_types.py` — CompositionPlan, VoicePlan, SectionPlan, GapPlan, PlanAnchor, WritingMode
- `shared/voice_types.py` — Role, Range, Actuator, Voice, etc.
- `shared/key.py` — MODIFIED: added diatonic_to_midi(), midi_to_diatonic()
- `revision/test_pitch.py` — property tests for DiatonicPitch + Key round-trips

**Phase 6a** (skeleton + PillarStrategy): CODED, NOT COMMITTED, NOT TESTED. New files:
- `builder/compose.py` — entry point
- `builder/voice_writer.py` — VoiceWriter class
- `builder/writing_strategy.py` — WritingStrategy ABC
- `builder/pillar_strategy.py` — PillarStrategy
- `builder/voice_checks.py` — consonance, parallels, range, strong-beat checks
- `builder/figuration_strategy.py` — FigurationStrategy (filter pipeline)
- `builder/cadential_strategy.py` — CadentialStrategy
- `builder/staggered_strategy.py` — StaggeredStrategy
- `builder/junction.py` — junction checking

## What to do next

1. **Review all Phase 5 + 6a code** against the designs and `laws.md`. Check for:
   - Missing type hints, missing asserts, >100-line modules, blank lines in functions
   - Conformance with phase5_design.md and phase6_design.md contracts
   - Any compositional decisions leaking into builder (must come from plan)

2. **Run the existing test** (`revision/test_pitch.py`). Fix if needed.

3. **Write a smoke test** for Phase 6a: hand-build a CompositionPlan with all-PILLAR gaps, call `compose_voices()`, verify MIDI output matches expected anchors. See `briefs/phase6a_prompt.md` for test spec.

4. **Commit** Phase 5 + 6a together if tests pass.

5. **Then proceed** to Phase 6b (FigurationStrategy core) per phase6_design.md §Implementation Order.

## Other uncommitted changes

Several existing files are modified (see `git status`). These include changes to `builder/types.py`, `planner/planner.py`, `shared/constants.py`, `scripts/run_pipeline.py`, and others. Review before committing — some may be Phase 2–4 prep work mixed in.
