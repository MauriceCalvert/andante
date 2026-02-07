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
