# Phase 6 Implementation Prompt

Read CLAUDE.md first, then phase6_design.md.

## Task

Implement Phase 6a (skeleton + PillarStrategy) as defined in phase6_design.md §Implementation Order.

## Key files to read before coding

1. `CLAUDE.md` — project conventions, tooling, file paths
2. `phase6_design.md` — full design with module shapes, data flow, resolved questions
3. `shared/plan_types.py` — CompositionPlan, VoicePlan, SectionPlan, GapPlan, PlanAnchor
4. `shared/diatonic_pitch.py` — DiatonicPitch class
5. `shared/key.py` — Key class, diatonic_to_midi()
6. `shared/voice_types.py` — Role, Range
7. `builder/types.py` — Note, Composition, Anchor dataclasses
8. `test_plan_contract.py` — existing test helpers (_plan, _voice, _section, _gap, _anchor)

## What to build (6a only)

Create these new files in `builder/`:

1. **writing_strategy.py** (~20 lines) — WritingStrategy ABC with fill_gap()
2. **pillar_strategy.py** (~15 lines) — PillarStrategy: returns source_pitch held for gap_duration
3. **voice_checks.py** (~15 lines initially) — check_range() only for 6a
4. **voice_writer.py** (~100 lines) — VoiceWriter class:
   - __init__ takes VoicePlan, home_key, anchors, prior_voices
   - compose() iterates sections, returns tuple[Note, ...]
   - _compose_section() handles independent sequencing only (others assert-fail)
   - _compose_gap() dispatches to strategy, converts results to Notes
   - _pitch_for_role() reads upper_pitch or lower_pitch from anchor by Role
   - _check_candidate() — for 6a just checks range
   - _to_note() converts DiatonicPitch + offset + duration to Note
5. **compose.py** (~30 lines) — compose_voices(plan) loops voice_plans, builds Composition

## Test

Write `test_voice_writer.py` in the andante root. Build a CompositionPlan by hand using the test helpers from test_plan_contract.py. Use all-PILLAR gaps. Verify:
- compose_voices returns a Composition with correct voice count
- Each voice has one Note per gap
- MIDI pitches match expected anchor pitches
- Note offsets are sequential and correct
- Actuator range violations are caught

## Constraints

- Do not modify any existing files (except adding imports if absolutely necessary)
- Reuse _plan(), _voice(), _section(), _gap(), _anchor() patterns from test_plan_contract.py
- All code conventions per CLAUDE.md (one class per file, methods alphabetical, type hints, asserts, no blank lines inside functions, ≤100 lines)
- IMITATIVE and HARMONY_FILL sections: assert-fail in voice_writer
- WALKING and ARPEGGIATED writing modes: assert-fail in voice_writer
- Non-independent sequencing: assert-fail in _compose_section (deferred to 6d)
- Anacrusis: skip if None (deferred to 6e)
- No counterpoint checking yet (deferred to 6c) — candidate_filter passes everything

## After coding

Run tests. Fix any failures. Then stop and report what was built.
