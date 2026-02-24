# Completed

## Code review refactor (2026-02-24)

Ran 5 parallel review agents across all modules then implemented findings.

**Law violations fixed (L001, L016, L002):**
- `shared/key.py`: Removed forbidden try/except in `diatonic_step()`, replaced with direct `min()` call.
- `builder/figuration/selection.py`: Removed `if True:` dead branch and forbidden try/except. Added guard `if note_count >= 2 and interval in INTERVAL_DIATONIC_SIZE:` before calling `generate_degrees()`.
- `planner/planner.py`: Replaced all `print()` calls with `tracer._line()` (pipeline output) or `_log.info()` (pre-tracer fugue loading). Added module-level `_log`. Removed duplicate `from dataclasses import replace` at function scope.
- `viterbi/pipeline.py`: Replaced `print()` calls in `_print_phrase_summary()` with `_log.debug()`.
- `builder/musicxml_writer.py`: Replaced `print()` warning with `_log.warning()`.
- `shared/midi_writer.py`: Replaced `print()` warning with `_log.warning()`. Moved `GATE_TIME = 0.95` local constant to `shared/constants.py` as `MIDI_GATE_TIME`.
- `shared/constants.py`: Added `DURATION_DENOMINATOR_LIMIT: int = 64` and `MIDI_GATE_TIME: float = 0.95`.
- `builder/cs_writer.py`, `builder/imitation.py`: Removed duplicate `DURATION_DENOMINATOR_LIMIT` definitions, import from `shared.constants`.

**Typing modernisation (Tuple/Dict/List/Optional → built-ins):**
- Removed `from typing import Tuple` and updated to `tuple[...]` in: `shared/constants.py`, `shared/key.py`, `planner/dramaturgy.py`, `planner/thematic.py`, `motifs/fugue_loader.py`, `motifs/countersubject_generator.py`, `motifs/catalogue.py`, `motifs/answer_generator.py`, `motifs/stretto_analyser.py`, `motifs/subject_gen/models.py`, `scripts/generate_subjects.py`.
- `LinesOfCode.py`: Removed `Dict` import, updated to `dict[...]`.
- `shared/midi_writer.py`: Replaced `List`, `Optional` with `list`, `str | None`.
- `shared/tracer.py`: Moved `from collections import Counter` from inside function to module-level import.

**Dead code and Pythonic improvements:**
- `shared/phrase_position.py`: Removed unreachable defensive branch (impossible after assert on previous line).
- `shared/counterpoint.py`: Replaced manual for-loops with `next()` generator expressions in `has_parallel_perfect()`.
- `planner/variety.py`: Replaced `assert False, msg` inside if-branch with inline conditional assertion.
- `planner/schematic.py`: Extracted magic `20` as module-level `_MAX_SCHEMA_WALK_ITERATIONS`.
- `planner/thematic.py`: Extracted duplicate material code dict literal to module-level `_MATERIAL_CODE_MAP`.
- `builder/galant/bass_writer.py`: Replaced `dict(list_of_tuples)` with explicit dict comprehensions.
- `motifs/fragen.py`: Moved `MIN_EPISODE_SPACING = 10` from inside function body to module-level `_MIN_EPISODE_SPACING`.
- `motifs/subject_gen/cache.py`: Narrowed `except Exception` to specific pickle failure types.

All 26 modified modules import cleanly.

## F4 — Canonic Episode Texture (2026-02-24)

Replaced cross-pairing episode builder with canonic pairing in `motifs/fragen.py`.

- Deleted `_FOLLOWER_OFFSETS`, `_RHYTHMIC_CONTRAST`, `_avg_duration`, `product` import
- Added `_CANONIC_STAGGERS` (1/4, 1/2) for 1-2 beat canonic stagger
- `build_fragments`: each cell paired with itself (parallel) and its inversion (contrary), looped over staggers
- `_consonance_score`: added `leader_voice` param, fixed model_dur and t-loop for bass-leads case
- `_emit_notes`: fixed timing so leader enters first, follower at stagger offset; fixed `realise` model_dur
- `_fragment_signature` / `dedup_fragments`: added contrary flag and stagger to signature/dedup key
- Pipeline verified: episodes show staggered entries, contrary motion, recognisable motivic cells

## SUBSCORE — Remove pitch/duration scoring, rank by stretto quality (2026-02-23)

Replaced aesthetic scoring with stretto-quality ranking throughout the subject generator.

- `constants.py`: Removed `QUALITY_FLOOR_FRACTION`, `CONTOUR_PREFERENCE_BONUS`, `IDEAL_CLIMAX_LO/HI`, `IDEAL_STEP_FRACTION`, `IDEAL_RHYTHMIC_ENTROPY`, `MIN_SIGNATURE_LEAP`, `MAX_STEPWISE_RUN`, `MIN_DISTINCT_INTERVALS`, `LEAP_RECOVERY_WINDOW`, `MAX_OPENING_TICKS`, `MIN_DURATION_KINDS`
- `pitch_generator.py`: Deleted `score_pitch_sequence` and all helpers (`_direction_changes`, `_tension_arc_score`, `_longest_stepwise_run`, `_leap_recovery_rate`). `_cached_validated_pitch` now sets `score=0.0`, no sorting.
- `duration_generator.py`: Deleted `score_duration_sequence`. `_cached_scored_durations` returns `dict[int, list[tuple[int, ...]]]` (patterns only, no scores).
- `selector.py`: Pool is now `list[tuple[_ScoredPitch, tuple[int, ...]]]` (no score). No quality floor. `pitch_contour` is a hard exclusion filter, not a bonus. After stretto filter, candidates ranked by `mean(r.quality for r in viable_offsets)`. `final_score` passed to `_build_subject` is the stretto quality score.
- `scoring.py`: Deleted.
- Caches: All `.pkl` cache files deleted to force regeneration with new data structures.

## SUBDUR — Multi-duration pairing + stretto cache (2026-02-23)

Introduced rhythmic variety by pairing each pitch with the top-5 duration patterns
per note count, and cached stretto evaluation results to disk.

- `constants.py`: added `DURATIONS_PER_NOTE_COUNT = 5`
- `selector.py`:
  - Imports: added `OffsetResult`, `_load_cache`, `_save_cache`, `DURATIONS_PER_NOTE_COUNT`
  - `top_durs_by_count` replaces `best_dur_by_count` (top-K list, not single best)
  - Pool loop: inner loop over K duration options per pitch
  - Dedup key changed to `(degrees, dur_pattern)` — same pitch+different rhythm no longer collapsed
  - Stretto cache: `stretto_eval_{mode}_{bars}b_{ticks}t.pkl` loaded before filter loop,
    saved after if any new entries; maps `(degrees, dur_pattern)` → `tuple[OffsetResult, ...]`
  - `stretto_filtered` now 4-tuple including `viable_offsets`
  - `_build_subject`: accepts `cached_viable_offsets` param; skips `evaluate_all_offsets` when provided
  - Picks loop: passes cached offsets to `_build_subject`


## SUBPOOL — Widen subject pool for stretto richness (2026-02-23)

Extended subject note range to 16 and raised stretto minimum to 3 viable offsets.

- `constants.py`: `MAX_SUBJECT_NOTES` 10→16; added `MIN_STRETTO_OFFSETS=3`,
  `CONTOUR_PREFERENCE_BONUS=0.05`
- `selector.py`: contour filter replaced with +0.05 scoring bonus; stretto
  threshold raised from >0 to >=3; verbose label updated
- Deleted stale `.cache/subject/` pkl files (8n, 9n pitch; 2-bar duration)
