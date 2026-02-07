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
