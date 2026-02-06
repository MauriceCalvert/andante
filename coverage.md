# Andante Test Coverage Report

**Date**: 2026-02-06
**Test results**: 1973 passed, 254 skipped, 3 xfailed, 0 failures
**Overall coverage**: 28% (2893 / 10321 statements)

---

## Summary by Package

| Package | Stmts | Miss | Cover |
|---------|------:|-----:|------:|
| builder | 2927 | 1932 | 34% |
| planner | 3350 | 2551 | 24% |
| shared | 578 | 320 | 45% |
| motifs | 1669 | 1669 | 0% |
| scripts | 968 | 968 | 0% |

---

## Well-Tested (≥80%)

| Module | Stmts | Cover |
|--------|------:|------:|
| builder/cadence_writer.py | 106 | 99% |
| builder/phrase_planner.py | 116 | 98% |
| planner/rhythmic_profile.py | 62 | 98% |
| builder/phrase_writer.py | 245 | 96% |
| planner/schematic.py | 113 | 95% |
| planner/variety.py | 21 | 95% |
| planner/metric/schema_anchors.py | 62 | 94% |
| builder/config_loader.py | 200 | 88% |
| planner/rhythmic.py | 122 | 88% |
| planner/tonal.py | 82 | 88% |
| planner/voice_planning.py | 343 | 83% |
| builder/faults.py | 344 | 81% |
| builder/phrase_types.py | 40 | 100% |
| builder/rhythm_cells.py | 56 | 100% |
| builder/writing_strategy.py | 10 | 100% |
| shared/constants.py | 96 | 100% |
| shared/voice_types.py | 24 | 100% |

---

## Partially Tested (20–79%)

| Module | Stmts | Cover |
|--------|------:|------:|
| builder/staggered_strategy.py | 13 | 77% |
| planner/textural.py | 25 | 76% |
| planner/rhythmic_gap.py | 65 | 74% |
| planner/schema_loader.py | 164 | 71% |
| planner/rhythmic_motif.py | 125 | 71% |
| shared/diatonic_pitch.py | 13 | 69% |
| planner/metric/layer.py | 214 | 66% |
| builder/types.py | 128 | 59% |
| builder/pillar_strategy.py | 24 | 54% |
| shared/key.py | 98 | 54% |
| builder/figuration/bass.py | 193 | 52% |
| builder/compose.py | 73 | 44% |
| shared/tracer.py | 130 | 42% |
| builder/figuration/types.py | 84 | 38% |
| shared/plan_types.py | 113 | 38% |
| shared/pitch.py | 67 | 33% |
| builder/cadential_strategy.py | 70 | 27% |
| planner/metric/distribution.py | 37 | 24% |
| builder/junction.py | 18 | 22% |
| builder/figuration_strategy.py | 145 | 21% |
| builder/arpeggiated_strategy.py | 90 | 19% |
| builder/voice_checks.py | 76 | 18% |
| builder/figuration/loader.py | 184 | 14% |
| builder/voice_writer.py | 686 | 10% |

---

## Untested (0%)

| Module | Stmts | Notes |
|--------|------:|-------|
| **motifs/** (all 14 files) | 1669 | Entire package |
| **scripts/** (all 9 files) | 968 | CLI/utility scripts |
| planner/cs_generator.py | 598 | Counter-subject generator |
| planner/dramaturgy.py | 179 | Key suggestion from affect |
| planner/constraints.py | 149 | Planning constraints |
| planner/schema_generator.py | 139 | Schema sequence generation |
| planner/material.py | 135 | Material assignments |
| planner/subject.py | 131 | Subject handling |
| planner/koch_rules.py | 125 | Koch's phrase rules |
| planner/plannertypes.py | 110 | Planner-internal types |
| planner/motif_loader.py | 101 | Load motifs |
| planner/plan_validator.py | 95 | Plan validation |
| planner/devices.py | 95 | Compositional devices |
| planner/planner.py | 88 | Orchestrator |
| planner/coherence.py | 79 | Coherence checks |
| planner/subject_deriver.py | 79 | Subject derivation |
| planner/subject_validator.py | 78 | Subject validation |
| planner/harmony.py | 70 | Harmonic analysis helpers |
| planner/rhythmic_variety.py | 59 | Rhythmic variety |
| planner/serializer.py | 55 | Plan serialisation |
| planner/arc.py | 52 | Trajectory arc |
| planner/phrase_harmony.py | 39 | Phrase-level harmony |
| planner/structure.py | 36 | Form structure helpers |
| planner/frame.py | 30 | Frame-level planning |
| planner/__main__.py | 24 | Entry point |
| planner/metric/pitch.py | 19 | Anchor pitch assignment |
| shared/midi_writer.py | 90 | Low-level MIDI writing |
| shared/music_math.py | 53 | Duration arithmetic |
| shared/errors.py | 7 | Custom exceptions |
| builder/musicxml_writer.py | 79 | MusicXML output |
| builder/io.py | 49 | MIDI/MusicXML/note file output |
| builder/figuration/rhythm_calc.py | 37 | Rhythm calculation |
