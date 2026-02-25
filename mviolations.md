# M001–M005 Violation Audit

Laws reviewed:
- **M001** Bundle 3+ optional params that travel together through 2+ call layers into a frozen dataclass
- **M002** Function signatures max 10 params; bundle related groups when exceeded
- **M003** Pass the source object, not its extracted fields, when the callee has access to both
- **M004** Frozen dataclasses with >15 fields must decompose into named sub-objects
- **M005** When the same extraction pattern appears at 3+ call sites, promote to a method on the source object

---

## M001 — Optional params bundled in transit

### viterbi/pathfinder.py
`degree_affinity`, `interval_affinity`, `genome_entries`, and `contour` are four optional params
that travel together from `find_path()` through two recursive retry calls (lines ~221–235 and
~292–306). They should be a frozen `AffinityContext` dataclass.

### builder/soprano_viterbi.py — lines 70–82
`density_override`, `contour`, `avoid_onsets_by_bar`, `chord_pcs_per_beat`, `bias` — five optional
params that travel as a group through `generate_soprano_viterbi()` into the viterbi pipeline.
Should become a frozen `SopranoOptions` dataclass.

### builder/bass_viterbi.py — lines 37–44
`harmonic_grid`, `density_override`, `bias` — three optional params that travel together into
`generate_bass_viterbi()` and onwards. Should be bundled with the soprano equivalents or into a
shared `ViterbiOptions` context.

### planner/planner.py — lines 92–101 / 215–237
- `key`, `tempo_override`, `fugue`, `sections_override`, `seed`, `trace_name` all forwarded
  through `generate()` into L1–L4 layer calls across 6+ layers. Should be a frozen
  `GeneratorOptions` dataclass.
- `schema_chain`, `genre_config`, `form_config`, `key_config`, `schemas`, `tonal_plan`,
  `answer_interval` all forwarded together into `layer_4_metric()` and beyond. Should be a
  frozen `MetricContext` dataclass.

### planner/metric/layer.py — lines 161–171
`schema_chain`, `genre_config`, `schemas`, `home_key`, `tonal_plan_dict`, `tonal_plan_obj`,
`answer_interval`, `bar_assignments`, `total_bars` travel together from `_generate_all_anchors()`
into `_generate_piece_anchors()`, `_generate_section_anchors_from_plan()`, and
`_generate_phrase_anchors()`. Should be an `AnchorGenerationContext` frozen dataclass.

### planner/imitative/subject_planner.py — lines 268–275
`thematic_config`, `subject_bars`, `home_key`, `metre`, `sections`, `stretto_offsets` travel
together through `plan_subject()` into many internal helper functions. Should be a frozen
`SubjectPlanContext`.

### planner/schematic.py — lines 157–166
`section_plan`, `bar_budget`, `schema_defs`, `rng`, `is_first_section`, `is_final_section`,
`genre_name`, `genre_section` travel as a group from `_generate_section_schemas()` into
`_select_opening_schema()` and `_select_next_schema()`.

### scripts/run_pipeline.py
`verbose`, `trace`, `seed` are three optional control params passed identically through
`run_from_args()`, `run_from_brief()`, `run_from_fugue()`, `run_from_directory()`, and `main()`.
Should be a frozen `PipelineOptions` dataclass.

### scripts/run_fragen.py
`tonic_midi`, `tonic`, `mode` form a tonic-context triple that travels from `main()` into
`_write_notes()` and `_collect_note_rows()` across 2+ layers.

---

## M002 — Function signature exceeds 10 params

### viterbi/costs.py — `transition_cost()` lines ~621–642
20 parameters. Needs decomposition into at least three context objects (motion context, affinity
context, chord context).

### viterbi/costs.py — `pairwise_cost()` lines ~556–567
11 parameters. Exceeds limit by 1; motion/dissonance params should be extracted.

### viterbi/pathfinder.py — `find_path()` lines ~115–129
13 parameters.

### viterbi/pipeline.py — `solve_phrase()` lines ~18–32
13 parameters.

### viterbi/generate.py — `generate_voice()` lines ~15–29
13 parameters.

### builder/phrase_planner.py — `_build_single_plan()` lines ~118–135
14+ parameters (schema_name, schema_def, anchor_group, schema_index, schema_chain,
genre_config, bar_length, beat_unit, upbeat, section_name, upper_range, lower_range,
upper_median, lower_median, cumulative_bar, home_key).

### builder/cadence_writer.py — `write_thematic_cadence()` lines ~284–297
12 parameters.

### builder/hold_writer.py — `_generate_running_voice_bar()` lines ~39–55
14 parameters.

### builder/soprano_viterbi.py — `generate_soprano_viterbi()` lines ~70–82
11 parameters.

### builder/free_fill.py — `fill_free_bars()` lines ~47–58
11 parameters.

### builder/cs_writer.py — `generate_cs_viterbi()` lines ~71–83
11 parameters.

### builder/entry_renderer.py — `render_entry_voice()` lines ~19–33
13 parameters.

### scripts/run_pipeline.py — `run_from_args()` lines ~93–105
11 parameters.

---

## M003 — Extracted fields passed instead of source object

### builder/phrase_writer.py — `_bass_for_plan()` lines ~47–74
Receives the extracted `harmonic_grid` field; the parent plan object is available at the call
site and should be passed instead.

### planner/schematic.py — `layer_3_schematic()` lines ~85–94
Extracts individual fields from `section_plan` (name, key_area, cadence_type) then passes
decomposed values to `_generate_section_schemas()`. Should pass `section_plan` directly.

### planner/metric/layer.py — `layer_4_metric()` lines ~44–48
Converts `tonal_plan` object into a `tonal_plan_dict` at the call site and passes both;
the callee could receive only the object and perform its own conversion.

### planner/imitative/subject_planner.py — `_place_entry_sequence()` lines ~391–392
Extracts `source_key` and `lead_voice_str` from `episode_entry` dict then passes the
reconstructed fields. Should pass the full entry dict.

### planner/thematic.py — lines ~128–143
Extracts individual parameters from `thematic_config` dict to pass to
`_format_entry_sequence_echo()` and `_place_entry_sequence()` instead of passing
`thematic_config` directly.

### planner/imitative/entry_layout.py — `build_imitative_plans()` lines ~77–82
Parses `bar_length` and `beat_unit` from metre at the call site, then passes them as separate
args to `_build_thematic_roles()`. Should pass the metre object and let the callee extract.

---

## M004 — Frozen dataclass with >15 fields

No violations found.

---

## M005 — Repeated extraction pattern (3+ call sites)

### planner/metric/layer.py — bar_beat float sorting
The lambda `bar_beat_to_float()` is written inline three or more times (lines ~80, ~195, ~460)
as a sorting key. Should be promoted to a method on `Anchor`: `anchor.sort_key()`.

### planner/schematic.py — `_schema_bars()` extraction
`_schema_bars()` called at lines ~191, ~225, ~268 to compute bar counts from schemas.
`schema_defs[schema_name]` is also extracted at every call site. Should be a method on
`Schema`: `schema.bar_count()`.

### motifs/catalogue.py — lines ~111–138
The pattern of extracting `intervals`/`durations`/`source` then calling `_generate_heads()`
and `_generate_tails()` appears at 6+ call sites (standard, inverted, augmented, diminished
variants). Should be promoted to a single parameterised method.

### motifs/countersubject_generator.py
`_get_strong_beats()` is queried 3+ times within the module (lines ~220, ~233, ~251). Should
be promoted to a cached property or method on the surrounding context class.

### builder/note_writer.py — lines ~64–87, ~193–208
The construction of `key_map`, `phrase_map`, `cadence_map` extraction/assembly pattern appears
three or more times. Should be promoted to a method on `PhrasePlan` or a dedicated helper.

### tests/ — pipeline setup duplication
Identical L1–L6 pipeline setup code appears in:
- `tests/builder/test_L6_phrase_writer.py` (`_run_pipeline_for_genre`)
- `tests/builder/test_L7_compose.py` (`_run_full_pipeline`)
- `tests/integration/test_system.py` (`_run_full_pipeline`)
- `tests/integration/test_cross_phrase_counterpoint.py` (`_run_full_pipeline`)

Should be consolidated into a single shared fixture in `tests/conftest.py`.

### tests/ — mode-extraction pattern
The pattern `kc.name.split()[-1].lower()` (extracting mode from a KeyConfig name) appears in
3+ test files. Should be a method on `KeyConfig` or `Key`.

---

## Summary

| Law  | Violation count |
|------|----------------|
| M001 | 9              |
| M002 | 13             |
| M003 | 6              |
| M004 | 0              |
| M005 | 6              |
| **Total** | **34**    |
