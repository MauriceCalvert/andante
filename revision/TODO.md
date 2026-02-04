this file and status.md must be updated after every step.

# Revision TODO

## Completed Phases

### Phase 1: Delete dead wood ✅
- Deleted unused modules per unused_items.txt

### Phase 5: VoicePlan contract ✅
- DiatonicPitch, CompositionPlan, VoicePlan, SectionPlan, GapPlan
- Key.diatonic_to_midi(), midi_to_diatonic()
- 15 property tests pass

### Phase 6: VoiceWriter + Strategies ✅
- compose.py, voice_writer.py, writing_strategy.py
- PillarStrategy, FigurationStrategy, CadentialStrategy, StaggeredStrategy
- voice_checks.py (consonance, parallels, direct motion, range)
- Sequencing: independent, repeating, static
- Anacrusis support

### Phase 7: Voice Planning Layer ✅
- planner/voice_planning.py: build_composition_plan()
- Schema section detection, sequencing assignment
- Affect-driven density/character per GapPlan

### Phase 8: Delete old builder ✅
- Deleted 6,918 lines (bridge, realisation, constraints, costs, solver, etc.)
- Retained: figuration/{loader, types, rhythm_calc, bass}.py

### Phase 9: Integration ✅
- faults.py: actuator_ranges parameter
- figuration_strategy.py: graceful fallback

### Figuration Fixes ✅
- Interval computation: sevenths→sixth, large intervals mod 7
- Figure selection: try all counts (not halving), relaxed character match

## Deferred (optional cleanup)
- Phase 2: Voice entity model per voices.md
- Phase 3: NoteFile → dict[str, tuple[Note, ...]]
- Phase 4: soprano_degree → upper_degree rename
- Sequencing: accelerating, relaxing, dyadic

---

## Current Output Quality
```
Upper: 199 notes (baroque figuration)
Lower: 47 notes (pillar/sustained)
Faults: 5 (2 ugly leaps, 2 dissonances, 1 direct fifth)
No parallel fifths/octaves, no grotesque leaps
```

## Test Summary
- 37 tests pass
- revision/test_pitch.py: 15
- revision/test_smoke_pillar.py: 5
- revision/test_counterpoint.py: 7
- revision/test_sequencing.py: 4
- revision/test_integration.py: 6
