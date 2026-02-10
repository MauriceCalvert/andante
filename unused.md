# Unused Code Report

## Planner — Completely Unused Modules (0% coverage)

| File | Statements | Key contents |
|------|-----------|-------------|
| `planner/__main__.py` | 24 | `main()` |
| `planner/cs_generator.py` | 598 | `CounterSubject`, `SubjectSpec`, CP-SAT solver |
| `planner/devices.py` | 95 | `load_figurae`, `get_eligible_figures`, `select_figures_for_phrase`, `assign_devices` |
| `planner/dramaturgy.py` | 183 | `CompositionParams`, `load_archetypes`, `compute_rhetorical_structure`, `compute_tension_curve`, `select_parameters`, etc. |
| `planner/frame.py` | 30 | `parse_upbeat`, `resolve_frame` |
| `planner/koch_rules.py` | 125 | `KochViolation`, `validate_koch`, baroque phrase validation |
| `planner/material.py` | 133 | `generate_motif`, `acquire_material`, `extend_by_repetition/sequence/appendix/parenthesis` |
| `planner/motif_loader.py` | 105 | `parse_note_name`, `midi_to_degree`, `load_motif` |
| `planner/phrase_harmony.py` | 39 | `generate_phrase_harmony` |
| `planner/serializer.py` | 55 | `InlineList`, `plan_to_dict`, `serialize_plan` |
| `planner/subject.py` | 131 | `Subject` class |
| `planner/subject_deriver.py` | 78 | `derive_subject`, `get_subject_rhythm` |
| `planner/subject_validator.py` | 78 | `validate_subject` |

**~1,400 lines total across 13 dead modules.**

## Planner — Partially Used Modules (low coverage)

| File | Coverage | Unused functions |
|------|----------|-----------------|
| `planner/arc.py` | 21% | `get_tension_at_position`, `select_tension_curve` |
| `planner/metric/distribution.py` | 24% | `distribute_arrivals`, `get_beats_per_bar`, `get_final_strong_beat`, `get_strong_beats` |
| `planner/metric/pitch.py` | 0% | `snap_to_key` (but `degree_to_midi`, `wrap_degree` may be used) |

## Builder — Unused Public Functions

| Function | File | Line |
|----------|------|------|
| `check_junction()` | `builder/junction.py` | 11 |
| `load_genre_raw()` | `builder/config_loader.py` | 30 |
| `clear_genre_cache()` | `builder/config_loader.py` | 47 |
| `get_patterns_by_texture()` | `builder/figuration/bass.py` | 200 |
| `get_patterns_for_metre()` | `builder/figuration/bass.py` | 207 |
