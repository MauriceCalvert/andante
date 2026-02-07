## 2026-02-07 (Anacrusis Implementation)

Implemented anacrusis (upbeat) support across the phrase pipeline. Pieces with
an anacrusis (gavotte: half-bar, bourree: quarter-note) now have correct bar
offsets — previously every bar after bar 1 was shifted by `bar_length - anacrusis`.

- **phrase_types.py**: Added `anacrusis: Fraction = Fraction(0)` field to PhrasePlan.
  Added 4 module-level helpers: `phrase_bar_start`, `phrase_bar_duration`,
  `phrase_degree_offset`, `phrase_offset_to_bar`. When anacrusis == 0, all helpers
  collapse to the old formula (zero behavioral change for non-upbeat genres).

- **phrase_planner.py**: `cumulative_bar` starts at 0 when upbeat > 0 (triggers
  existing bar==0 branch in `_compute_start_offset` for negative offset). First
  phrase gets `anacrusis = upbeat`; `phrase_duration` adjusted to
  `anacrusis + (bar_span - 1) * bar_length`. Passed `anacrusis=` to PhrasePlan.

- **phrase_writer.py**: Replaced all ~14 inline offset formulas
  (`start_offset + (bar_num-1) * bar_length`, `offset // bar_length + 1`, etc.)
  with the 4 helpers in both soprano and bass (all 3 texture paths: patterned,
  pillar, walking). Anacrusis bars bypass `select_cell` and use single-note
  `(bar_dur,)` rhythm instead.

- **compose.py**: Replaced structural offset formula with `phrase_degree_offset`.

- **bourree.yaml**: Added `upbeat: "1/4"`.

Modified: builder/phrase_types.py, builder/phrase_planner.py,
builder/phrase_writer.py, builder/compose.py, data/genres/bourree.yaml

## 2026-02-07 (Fix Key Resolution Bugs)

Two key-resolution bugs caused parallel octaves at schema boundaries:

- **Bug 1: Anchor grouping misattribution**: `_group_anchors_by_schema` matched
  anchors by name instance-counting. When deduplication removed a schema anchor
  (replaced by section_cadence/piece_end), the counting shifted, assigning anchors
  from a later instance to an earlier schema — giving it the wrong key. E.g.,
  invention exordium comma (bar 6) got G major from confirmatio comma (bar 16).

- **Bug 2: Sequential expansion used wrong home_key**: `_expand_sequential_degrees`
  used the piece's overall home_key (C major) instead of the per-schema local_key
  (e.g., G major for key_area="V"). This made fonte typical_keys ("ii","I") resolve
  relative to C major instead of G major, producing wrong degree_keys.

Fixes:
- Removed hardcoded `is_exordium and schema_index == 1 → V` override from
  `_get_local_key()` in planner/metric/layer.py. This rule conflicted with the
  per-schema key_areas from `_distribute_section_key_areas()`.
- Added `_resolve_local_key()` in builder/phrase_planner.py: resolves local_key
  from `schema_chain.key_areas` (canonical source of truth) instead of from
  anchor groups (fragile due to deduplication).
- Fixed `_expand_sequential_degrees` to use per-schema `local_key` instead of
  overall `home_key`, so typical_keys resolve relative to the correct key area.

Modified: planner/metric/layer.py, builder/phrase_planner.py
All 101 integration tests pass (zero faults, all genres × keys).

## 2026-02-07 (Activate Tonal System + Fix Short-Circuits)

Five short-circuits rendered core systems inert. All fixed:

- **Fix 1A**: Removed `modality == "diatonic"` short-circuit in `_get_local_key()`
  (planner/metric/layer.py). Removed the entire `modality` parameter chain from
  layer_4_metric -> _generate_all_anchors -> _generate_phrase_anchors ->
  _phrase_anchors_from_chain -> _phrase_anchors_legacy -> _get_local_key.
  Updated planner/planner.py to stop passing modality.

- **Fix 1B**: Binary forms now get mode-aware key_area for Section A:
  V (dominant) for major keys, III (relative major) for minor keys.
  Added `_BINARY_A_DESTINATION_MAJOR`/`_BINARY_A_DESTINATION_MINOR` constants.
  Added `home_mode` parameter to `layer_2_tonal()` and `_assign_key_areas()`.
  Caller in planner.py extracts mode from key_config.name.

- **Fix 1C**: Per-schema key area distribution in planner/schematic.py. Added
  `_distribute_section_key_areas()`. Departure schemas stay in start key;
  cadential + post-cadential schemas (last 2) get destination key. Section B
  starts in the previous section's destination key. Updated metric layer to
  use SchemaChain.key_areas (per-schema) instead of tonal_plan_dict (per-section).

- **Fix 2**: Wired figuration character through the pipeline.
  Added `character` field to PhrasePlan. Added `character` to all 8 genre YAML
  section definitions (minuet, gavotte, invention, bourree, sarabande, chorale,
  fantasia, trio_sonata). Added `_get_section_character()` helper in
  phrase_planner.py. Replaced hardcoded `character="plain"` in phrase_writer.py
  with `plan.character`.

- **Fix 3**: Reverted — negative offsets are illegal. Upbeat handling deferred.

- **Fix 4**: Fixed `tension_to_energy()` in planner/arc.py: the 0.7-0.85 range
  now returns "high" instead of redundantly returning "peak".

Modified: planner/metric/layer.py, planner/planner.py, planner/tonal.py,
planner/schematic.py, planner/arc.py, builder/phrase_planner.py,
builder/phrase_writer.py, builder/phrase_types.py, tests/planner/test_L2_tonal.py,
data/genres/*.yaml (8 files)

All 8 genres generate successfully with tonal contrast.

## 2026-02-07 (Figuration Revision)

- Wired the unused figuration system into the phrase writer (8 phases):
  - **Phase 0**: Added `bass_pattern` field to PhrasePlan, plumbed from GenreConfig
  - **Phase 1**: Created `builder/figuration/selection.py` — deterministic figure
    selection engine (classify_interval, select_figure) with bar_num rotation (V001)
  - **Phase 2**: Created `builder/figuration/soprano.py` — figurate_soprano_span()
    fills gaps between structural tones using diminution figures + rhythm templates
  - **Phase 3**: Hybrid soprano approach in phrase_writer — rhythm cells for timing
    (preserving complementary rhythm), figuration for pitch selection (replacing
    stepwise fill with baroque diminution patterns)
  - **Phase 4**: Patterned bass in phrase_writer — when bass_pattern is declared
    (e.g. arpeggiated_3_4), uses realise_bass_pattern() instead of drone pillar.
    Includes structural-tone override, multi-degree-bar fallback, voice crossing
    and parallel-fifth guards
  - **Phase 5**: End-to-end minuet validation — zero faults for both C major and
    A minor. Fixed: common-onset parallel-fifth detection, cross-phrase consecutive
    leaps (threaded prev_prev_lower_midi through compose_phrases)
  - **Phase 6**: All genres pass zero faults (minuet, gavotte, bourree, invention,
    sarabande, trio_sonata). Fixed: bourree continuo_walking routed to walking
    texture path for complementary rhythm; invention walking bass common-onset
    parallel check
  - **Phase 7**: Trace output includes soprano_figures and bass_pattern_name per
    phrase for debugging
- New files: `builder/figuration/selection.py`, `builder/figuration/soprano.py`,
  `tests/builder/test_figuration_selection.py`, `tests/builder/test_figurate_soprano.py`
- Modified: `builder/phrase_writer.py` (major), `builder/phrase_types.py`,
  `builder/phrase_planner.py`, `builder/compose.py`, `shared/tracer.py`
- All tests: 1451 passed, 0 failed

## 2026-02-07

- Rewrote `scripts/yaml_validator.py` (~1550 lines) with comprehensive YAML validation:
  - Added `ValidationResult` NamedTuple return type (valid, errors, warnings, usages, orphaned)
  - Added timestamp-based caching via `.yaml_last_validated` file (skips re-validation when no YAML changed)
  - Added in-memory YAML load cache to avoid redundant file reads across validators
  - Added 20+ per-domain validators covering genres, schemas, figuration profiles, figurations,
    bass patterns, bass diminutions, cadential figures, rhythm templates, affects, archetypes,
    episodes, treatments, cadences, cadence templates, instruments, rhythm cells, rhythm affect
    profiles, motif vocabulary, humanisation, and rules
  - All legacy validators preserved (required fields, unknown keys, brief files, cross-references)
- Integrated validation into test suite (`tests/conftest.py` session-scoped autouse fixture)
  and pipeline entry (`scripts/run_pipeline.py` gate at top of `main()`)
- Fixed 11 YAML errors found by new validators:
  - Added `"structure"` to valid brief keys (4 briefs used it)
  - Added `half_bar` bass pattern to `data/figuration/bass_patterns.yaml` (gavotte referenced it)
  - Relaxed offset_from_target check for ornament/diminution figurations (6 patterns)

## 2025-02-07

- Fixed bass MIDI track assignment: was PHRASE_VOICE_BASS=1 (Alto), now TRACK_BASS=3 (Bass).
  Changed in phrase_writer.py, cadence_writer.py, test_L6_phrase_writer.py.
  Retired PHRASE_VOICE_BASS constant.
