# Phase 1 Brief: Delete Dead Wood

## For: Claude Code
## Context: Andante baroque composition system
## Working directory: D:\projects\Barok\barok\source\andante
## Python: D:\projects\Barok\barok\.venv\Scripts\python.exe
## Pytest: python -m pytest (from working directory, with PYTHONPATH=.)

---

## Task

Delete all unused modules, functions, classes, constants, and imports
listed below.  After EACH group of deletions, run the existing tests
to verify nothing breaks:

```
cd /d D:\projects\Barok\barok\source\andante
set PYTHONPATH=.
D:\projects\Barok\barok\.venv\Scripts\python.exe -m pytest test_pitch.py test_breathing.py test_schema_load.py -v
```

Also run:
```
D:\projects\Barok\barok\.venv\Scripts\python.exe -c "from shared.key import Key; k=Key(tonic='C',mode='major'); print(k.degree_to_midi(1,5))"
```

If any test fails after a deletion, undo that deletion and note it.

Git-commit after each successful group with message format:
`Phase 1: delete <description>`

---

## Rules

1. **Delete only what is listed.** Do not delete anything else.
2. **Do not modify function bodies** of surviving functions.
3. **Do not reformat or reorder** surviving code.
4. **Remove orphaned imports** — if deleting function X means an import
   is no longer needed, remove that import too.
5. **Empty modules after deletion:** If deleting functions leaves a
   module with only imports and no definitions, delete the entire module.
6. **__init__.py files:** If a deleted module was re-exported from an
   __init__.py, remove the re-export line.
7. **Test after each group**, not after each individual deletion.

---

## Group 1: Delete entire unused modules

Delete these files entirely:

| File | Notes |
|------|-------|
| shared\dissonance.py | Never imported by any live code |
| shared\timed_material.py | Never imported |
| shared\constraint_validator.py | Never imported |
| shared\validate.py | Never imported |
| shared\voice_role.py | Never imported |
| shared\parallels.py | Never imported (3 diatonic functions listed as unused; checked — no file imports this module at all) |
| builder\figuration\melodic_minor.py | Never imported |

After deleting, check shared\__init__.py and builder\figuration\__init__.py
for any re-exports of these modules.  Remove those lines.

**Test, then commit:** `Phase 1: delete 7 unused modules`

---

## Group 2: Delete dead functions from shared\pitch.py

Delete these functions from shared\pitch.py:

- `cycle_pitch_with_variety` (line ~96)
- `degree_interval` (line ~85)
- `is_degree_consonant` (line ~90)
- `is_floating` (line ~72)
- `is_midi_pitch` (line ~77)
- `is_rest` (line ~67)
- `place_degree` (line ~107)

Delete this constant from shared\pitch.py:

- `CONSONANT_DEGREE_INTERVALS` (line ~82)

Also delete the entire `select_octave` function and the entire
`place_anchor_pitch` function and `place_anchors_in_tessitura` function
— but ONLY IF they appear in unused_items.txt or are confirmed to have
zero importers outside shared\pitch.py.  If unsure, leave them.

After deleting, remove any imports in shared\pitch.py that are now
orphaned (no longer used by surviving code).

**Test, then commit:** `Phase 1: delete dead functions from shared/pitch.py`

---

## Group 3: Delete dead functions from shared\music_math.py

Delete these functions from shared\music_math.py:

- `bar_duration` (line ~42)
- `beat_duration` (line ~47)
- `build_offsets` (line ~160)
- `repeat_to_fill` (line ~137)

Delete this class from shared\music_math.py:

- `MusicMathError` (line ~11)

If the module is empty after deletion (only imports remain), delete
the entire file and remove any re-exports from shared\__init__.py.

If the module still has live functions, remove orphaned imports only.

**Test, then commit:** `Phase 1: delete dead functions from shared/music_math.py`

---

## Group 4: Delete dead classes from shared\errors.py

Delete these classes from shared\errors.py:

- `HarmonyGenerationError` (line ~36)
- `MissingContextError` (line ~24)
- `SubjectValidationError` (line ~40)
- `VoiceGenerationError` (line ~32)

Keep all other classes (AndanteError, ValidationError,
InvalidDurationError, InvalidPitchError, InvalidRomanNumeralError,
SolverTimeoutError, SolverInfeasibleError).

**Test, then commit:** `Phase 1: delete dead classes from shared/errors.py`

---

## Group 5: Delete dead constants from shared\constants.py

Delete these constants (variable assignments) from shared\constants.py:

```
AUGMENTATION
CADENCE_DENSITY
DEGREE_TO_CHORD
DENSITY_LEVELS
DIATONIC_DEFAULTS
DIMINUTION
DOMINANT_TARGETS
FIGURE_ARRIVALS
FIGURE_CHARACTERS
FIGURE_PLACEMENTS
FIGURE_POLARITIES
HARMONIC_MINOR_SCALE
KEY_AREA_OFFSETS
LARGE_LEAP_SEMITONES
LEAP_SEMITONES
MELODIC_MINOR_SCALE
MIN_TONAL_SECTION_BARS
PHRASE_DEFORMATIONS
PHRASE_POSITIONS
TENSION_LEVELS
TESSITURA_DRIFT_THRESHOLD
TONAL_PROPORTION_TOLERANCE
TONAL_ROOTS
VALID_DURATION_OPS
VALID_PITCH_OPS
VOICE_TRACKS
```

Also delete:

- `normalise_key_area` function (line ~154) — confirmed unused
- `DIRECT_MOTION_STEP_THRESHOLD` (line ~58) — listed as unused import in figurate.py; check if constants.py itself defines it AND if any other file imports it. If only figurate.py imports it and figurate.py's import is unused, delete the constant.

**Do NOT delete** any constant that is imported by faults.py, key.py,
or any file outside builder\figuration\.  When in doubt, leave it.

**Test, then commit:** `Phase 1: delete 27+ unused constants from shared/constants.py`

---

## Group 6: Delete dead functions from builder\figuration\ modules

### sequencer.py

Delete these functions and classes:

- `SequencerState` class (line ~16)
- `should_break_sequence` (line ~69)
- `compute_transposition_interval` (line ~121)
- `apply_fortspinnung` (line ~137)
- `detect_melodic_rhyme` (line ~188)
- `create_sequence_figures` (line ~239)
- `accelerate_to_cadence` (line ~273)

### realiser.py

Delete these functions:

- `apply_augmentation` (line ~58)
- `apply_diminution` (line ~80)
- `compute_bar_duration` (line ~102)
- `generate_default_durations` (line ~137)
- `realise_rhythm` (line ~384)
- `compute_gap_duration` (line ~500)
- `is_anacrusis_beat` (line ~518)

### junction.py

Delete these functions:

- `compute_junction_penalty` (line ~168)
- `suggest_alternative` (line ~236)
- `validate_figure_sequence` (line ~209)

If any module is empty after deletion, delete the entire file.
Remove orphaned imports from surviving code.

**Test, then commit:** `Phase 1: delete dead functions from builder/figuration/`

---

## Group 7: Clean up unused imports in builder\figuration\figurate.py

The following imports in figurate.py are listed as unused:

- `CADENTIAL_UNDERSTATEMENT_PROBABILITY` (line ~21)
- `DEFORMATION_PROBABILITY` (line ~26)
- `DIRECT_MOTION_STEP_THRESHOLD` (line ~64)
- `MAX_SCHEMA_SECTION_ANCHORS` (line ~27)
- `MIN_SCHEMA_SECTION_ANCHORS` (line ~28)
- `PERFECT_INTERVALS` (line ~64)
- `would_create_parallel_or_direct` (line ~50)

Delete ONLY the import lines.  Do not modify any function bodies.

### selector.py

- `Fraction` import (line ~19) — delete if unused
- `random` import (line ~18) — delete if unused
- `Sequence` import (line ~20) — delete if unused

### realisation_util.py

- `GenreConfig` import (line ~5) — delete if unused
- `STACCATO_DURATION_THRESHOLD` import (line ~6) — delete if unused

For each: verify the import is genuinely unused in that file (not used
in any surviving function).  If used, leave it.

**Test, then commit:** `Phase 1: clean up unused imports`

---

## Verification

After all groups are committed, run the full test suite one final time:

```
cd /d D:\projects\Barok\barok\source\andante
set PYTHONPATH=.
D:\projects\Barok\barok\.venv\Scripts\python.exe -m pytest test_pitch.py test_breathing.py test_schema_load.py -v
```

Also do a quick smoke check that the pipeline still runs:

```
D:\projects\Barok\barok\.venv\Scripts\python.exe scripts\run_pipeline.py
```

(If run_pipeline.py requires arguments, just verify it imports
successfully with `python -c "import scripts.run_pipeline"` or similar.)

Report: which groups succeeded, which items were skipped (if any), and
the final test results.

---

## Do NOT do any of the following

- Do not delete builder\figuration\figurate.py itself (it's still live)
- Do not delete builder\figuration\selector.py itself (still live)
- Do not delete builder\faults.py (critical guard)
- Do not delete shared\key.py, shared\constants.py, shared\pitch.py (live modules; only delete listed items within them)
- Do not refactor, rename, or restructure anything
- Do not add any new code
- Do not modify any test files
- Do not touch any YAML files
- Do not touch any file in planner/ or motifs/
