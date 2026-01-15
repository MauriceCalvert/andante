# Test Coverage Report

**Overall: 97%** (20,013 statements, 541 missed)
**Tests: 2,740 passing**

## Engine (Executor)

| Module | Cover | Missing |
|--------|-------|---------|
| annotate.py | 100% | |
| arc_loader.py | 100% | |
| backtrack.py | 98% | 77 |
| cadence.py | 100% | |
| cadenza.py | 99% | 121 |
| energy.py | 100% | |
| episode.py | 97% | 136, 138 |
| episode_registry.py | 96% | 98, 114 |
| expand_phrase.py | 100% | |
| expander.py | 72% | 78-84, 91-108 |
| expander_util.py | 100% | |
| figuration.py | 33% | 32-51, 56-68, 77-86 |
| figured_bass.py | 97% | 108-109, 206 |
| formatter.py | 100% | |
| guard_backtrack.py | 97% | 88, 129 |
| guards/cross_phrase.py | 0% | 6-100 |
| guards/registry.py | 92% | 31, 154-161, 166-173 |
| guards/spacing.py | 0% | 2-97 |
| guards/voice_leading.py | 100% | |
| harmonic_context.py | 100% | |
| hemiola.py | 100% | |
| inner_voice.py | 77% | 40-57, 63, 66, 93, 96, 99, 119-120, 208, 213-215, 220, 225-227, 238-239, 243, 245, 249, 279, 301-305 |
| invertible.py | 100% | |
| key.py | 100% | |
| melodic_bass.py | 99% | 87 |
| metrics.py | 100% | |
| motif_expander.py | 100% | |
| n_voice_expander.py | 91% | 47, 61, 80, 84, 86, 92, 118 |
| n_voice_guards.py | 94% | 30-33, 96, 98 |
| note.py | 94% | 37 |
| octave.py | 100% | |
| ornament.py | 100% | |
| output.py | 99% | 35 |
| passage.py | 99% | 267, 271 |
| pedal.py | 100% | |
| phrase_builder.py | 95% | 118, 135, 195, 203-205 |
| phrase_expander.py | 94% | 34, 37, 40 |
| pipeline.py | 100% | |
| plan_parser.py | 97% | 128-129 |
| realiser.py | 94% | 81-82, 106, 156-158, 168 |
| realiser_guards.py | 100% | |
| realiser_passes.py | 76% | 34-36, 41-45, 72, 75-99, 147 |
| schema.py | 100% | |
| sequence.py | 99% | 146 |
| serializer.py | 98% | 46 |
| slice_solver.py | 85% | 108, 110, 117-118, 124-125, 207, 229, 262, 267, 336-342, 347-350, 366, 372-375, 382, 393, 398-400, 407, 412-414 |
| subdivision.py | 100% | |
| surprise.py | 100% | |
| transform.py | 100% | |
| types.py | 100% | |
| validate.py | 100% | |
| vocabulary.py | 100% | |
| voice_checks.py | 100% | |
| voice_config.py | 100% | |
| voice_entry.py | 100% | |
| voice_expander.py | 81% | 86-88, 90-98, 106-110 |
| voice_material.py | 100% | |
| voice_pair.py | 100% | |
| voice_pipeline.py | 100% | |
| voice_realiser.py | 97% | 40, 88 |
| walking_bass.py | 99% | 74 |

## Planner

| Module | Cover | Missing |
|--------|-------|---------|
| arc.py | 98% | 70 |
| episode_generator.py | 94% | 46, 124, 190-192, 200-205 |
| frame.py | 100% | |
| macro_form.py | 100% | |
| material.py | 100% | |
| planner.py | 100% | |
| section_planner.py | 100% | |
| serializer.py | 100% | |
| solver.py | 98% | 82, 232, 289, 319, 352, 396 |
| structure.py | 95% | 122, 139-141, 148, 153 |
| subject.py | 90% | 66, 79, 87, 94-97, 101-106, 182, 207, 212, 214 |
| subject_generator.py | 94% | 53, 66, 74 |
| transition.py | 100% | |
| types.py | 100% | |
| validator.py | 97% | 30 |

## Shared

| Module | Cover | Missing |
|--------|-------|---------|
| constants.py | 100% | |
| constraint_validator.py | 80% | 32, 38-39, 44-45, 50-51, 73-76, 105, 163, 173, 178-202 |
| key.py | 96% | 66-67 |
| music_math.py | 93% | 92, 97, 115, 131, 151 |
| parallels.py | 100% | |
| pitch.py | 100% | |
| schema_validator.py | 83% | 19, 30, 45, 49, 64-67, 74, 104, 108, 115, 129-135 |
| timed_material.py | 100% | |
| tracer.py | 100% | |
| types.py | 100% | |

## Uncovered (0%)

| File | Reason |
|------|--------|
| engine/__main__.py | CLI entry point |
| planner/__main__.py | CLI entry point |
| engine/guards/cross_phrase.py | Not integrated |
| engine/guards/spacing.py | Not integrated |
| engine/pitch.py | Deprecated import shim |
| LinesOfCode.py | Utility script |
