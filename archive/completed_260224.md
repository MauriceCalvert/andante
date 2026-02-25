# Completed

## GEL-1: Generative entry layout (2026-02-24)

**`data/genres/invention.yaml`**: Replaced `thematic.entry_sequence` with `thematic.vocabulary` (exposition, development_entries, peroration_entries, key_pools) and `thematic.brief` (scope, dev count, stretto, pedal, key_journey, voice_lead).

**`planner/imitative/subject_planner.py`**: Added `_SCOPE_DEV_COUNT` constant, `_voice_0_leads()` helper, and `generate_entry_sequence()` — the GEL-1 runtime generator. Updated `plan_subject()` to dispatch: uses legacy `entry_sequence` if present (backward compat), otherwise generates via `vocabulary + brief`. Logged generated sequence at INFO level.

**`planner/planner.py`**: Removed stale `entry_count = len(thematic_cfg["entry_sequence"])` from imitative tracer line; L3 log now shows total_bars + section names only.

## TB-5b: Wire vertical genome into Viterbi cost function (2026-02-24)

**`viterbi/costs.py`**: Added `COST_VERTICAL_GENOME_BONUS = 3.0`, `vertical_genome_cost()` function (looks up nearest genome position, compares diatonic intervals, returns linear-decay discount), `genome_entries` parameter to `transition_cost`, `"vg"` in breakdown.

**`viterbi/pathfinder.py`**: Added `genome_entries` parameter to `find_path`; passed to both `transition_cost` call sites and both hard-constraint fallback recursions.

**`viterbi/pipeline.py`** and **`viterbi/generate.py`**: Threaded `genome_entries` through `solve_phrase` → `generate_voice`.

**`builder/voice_types.py`**: Added `VerticalGenome` TYPE_CHECKING import; added `vertical_genome: VerticalGenome | None = None` field to `VoiceBias`.

**`builder/soprano_viterbi.py`** and **`builder/bass_viterbi.py`**: Extract `bias.vertical_genome.entries` and pass as `genome_entries` to `generate_voice`.

**`builder/free_fill.py`**: All four `VoiceBias` instantiations (companion soprano, companion bass, tail bass, tail soprano) now include `vertical_genome=bias.vertical_genome if bias else None`.

## TB-5a: Extract vertical interval genome from exposition (2026-02-24)

**`motifs/thematic_transform.py`**: added `VerticalGenome` frozen dataclass — `entries: tuple[tuple[float, int], ...]` of (normalised_position, abs_diatonic_interval) pairs.

**`motifs/fugue_loader.py`**: added `VerticalGenome` to TYPE_CHECKING import; added `vertical_genome: VerticalGenome | None` field to `ThematicBias`; added `LoadedFugue.vertical_genome()` method that builds onset/pitch step functions for subject and CS, computes overlap duration, samples diatonic intervals at all note onsets, normalises positions to [0.0, 1.0], and returns a `VerticalGenome`. Updated `thematic_bias()` to populate the new field.

## TB-4b: Cell recombination sequencer (2026-02-24)

**`motifs/thematic_transform.py`**: added `_ZONE_TRANSFORMS` constant (zone 0 → identity, zone 1 → invert/retrograde, zone 2 → diminish). Added `sequence_cell_knots(catalogue, span_duration, prefer_family, start_midi, key, start_offset, range_low, range_high, max_offset, seed=0) -> list[Knot]` — greedy cell chain with zone-based phrase arc, soft family alternation, cell-name deduplication, pitch-continuity scoring, and iteration guard at 50.

**`builder/free_fill.py`**: imported `sequence_cell_knots`. At each of the four knot-building sites (companion soprano, companion bass, tail bass, tail soprano), added a primary `if bias.cell_catalogue` branch calling `sequence_cell_knots`; the existing TB-3b whole-pattern code becomes an `elif` fallback for empty/missing catalogues. prefer_family: soprano sites → "cs", bass sites → "subject". Seeds: run_counter for companions, 100/200 for tail bass/soprano.

## TB-4a: Cell-level transformation catalogue (2026-02-24)

**`motifs/thematic_transform.py`**: added `TransformedCell` and `CellCatalogue` frozen dataclasses. Added `cell_to_pattern(cell)` (Cell → IntervalPattern via degree differences). Added `build_cell_catalogue(cells, bar_length)` applying all 5 baroque transforms (identity, invert, retrograde, diminish, augment) per cell, filtering overlong results, partitioning by source family. Added `_pattern_total_duration` and `_source_family` private helpers. Added `TYPE_CHECKING` guard for `Cell` import.

**`motifs/fugue_loader.py`**: added `cell_catalogue: CellCatalogue | None` field to `ThematicBias`. Updated `LoadedFugue.thematic_bias()` to call `extract_cells` + `build_chains` + `build_cell_catalogue` and pass the result. No breaking changes — only one construction site for `ThematicBias`.

## MR-1: ThematicBias + VoiceBias parameter bundle refactor (2026-02-24)

**`motifs/fugue_loader.py`**: added `ThematicBias` frozen dataclass (holds `degree_affinity`, `subject_interval_affinity`, `cs_interval_affinity`, `subject_pattern`, `cs_pattern`). Added `LoadedFugue.thematic_bias()` factory method. Uses `TYPE_CHECKING` guard + `from __future__ import annotations` for `IntervalPattern` reference.

**`builder/voice_types.py`**: added `VoiceBias` frozen dataclass (holds `degree_affinity`, `interval_affinity`, `structural_knots`, all optional). Uses `TYPE_CHECKING` guard for `Knot` reference.

**`builder/soprano_viterbi.py`**: replaced 3 params (`degree_affinity`, `interval_affinity`, `structural_knots_override`) with `bias: VoiceBias | None = None`. Unpacks at Viterbi call site.

**`builder/bass_viterbi.py`**: same — 3 params → `bias: VoiceBias | None = None`. Signature now 8 → 6 params.

**`builder/free_fill.py`**: replaced 4 params (`degree_affinity`, `interval_affinity_soprano`, `interval_affinity_bass`, `fugue`) with `bias: ThematicBias | None = None`. Signature 13 → 10 params. Builds `VoiceBias` at each of 4 Viterbi call sites.

**`builder/phrase_writer.py`**: `_write_thematic` — 3-line extraction replaced with `bias = fugue.thematic_bias()`; PEDAL bass call builds `VoiceBias`; `fill_free_bars` passes `bias=bias`. `_write_pedal` — 4-line extraction replaced with single `bias = fugue.thematic_bias() if fugue else None`; soprano Viterbi call builds `VoiceBias`.

## TB-3b: Wire transformed patterns as structural knots into free Viterbi (2026-02-24)

**`motifs/thematic_transform.py`**: added `nearest_degree_for_midi(target_midi, key) -> tuple[int, int]` (searches octaves 3–6) and `build_thematic_knots(pattern, start_degree, key, octave, start_offset, range_low, range_high) -> list[Knot]` (realises pattern with range correction).

**`builder/soprano_viterbi.py`** + **`builder/bass_viterbi.py`**: added `structural_knots_override: list[Knot] | None = None`. When provided, skips normal knot computation (soprano synthesises `structural_tones` from override for rhythm grid and audit). All other logic unchanged.

**`builder/free_fill.py`**: added `fugue: LoadedFugue | None = None`. Companion soprano uses CS pattern (invert/identity/retrograde by `run_counter % 3`); companion bass uses subject pattern (identity/invert by `run_counter % 2`); tail bass uses subject identity; tail soprano uses diminished subject. Knots passed as `structural_knots_override` only when non-empty.

**`builder/phrase_writer.py`**: added `fugue=fugue` to `fill_free_bars()` call in `_write_thematic`.

## TB-3a: Subject interval pattern extraction + transformation functions (2026-02-24)

New module `motifs/thematic_transform.py`:
- `IntervalPattern` frozen dataclass with `intervals: tuple[tuple[int, Fraction], ...]` and `start_duration: Fraction`
- `extract_interval_pattern(degrees, durations, tonic_midi, mode)`: converts float durations via `exact_fraction`, maps to MIDI via `degrees_to_midi`, computes signed diatonic steps using `build_pitch_class_set` + `diatonic_step_count`
- Five transformation functions (pure, composable): `augment`, `diminish`, `invert`, `retrograde`, `transpose`
- `realise_pattern(pattern, start_degree, key, octave)`: walks `key.diatonic_step` to produce `(midi, duration)` pairs
- `_nearest_valid_duration` helper for aug/dim clamping (L006)

**`shared/pitch.py`**: promoted `_build_pitch_class_set` -> `build_pitch_class_set` and `_diatonic_step_count` -> `diatonic_step_count` as public functions; added `MAJOR_SCALE`, `NATURAL_MINOR_SCALE` imports.

**`motifs/fugue_loader.py`**: removed private function definitions; import `build_pitch_class_set`, `diatonic_step_count` from `shared.pitch`; updated call sites in `subject_interval_affinity` and `cs_interval_affinity`; added `subject_interval_pattern()` and `cs_interval_pattern()` methods to `LoadedFugue` (local import to avoid any future circular-import risk).

## TB-2b: Wire interval_affinity to free Viterbi call sites (2026-02-24)

Threaded `interval_affinity: dict[int, float] | None = None` from `LoadedFugue`
through all layers to the 6 free Viterbi call sites. Follows exact pattern of TB-1b.

**`viterbi/generate.py`**: added `interval_affinity` param; passed to `solve_phrase`.

**`builder/soprano_viterbi.py`**: added `interval_affinity` param; passed to `generate_voice`.

**`builder/bass_viterbi.py`**: added `interval_affinity` param; passed to `generate_voice`.

**`builder/free_fill.py`**: added `interval_affinity_soprano` and `interval_affinity_bass` to
`fill_free_bars`; wired to all 4 free Viterbi call sites:
- Companion soprano → `interval_affinity_soprano` (CS affinity)
- Companion bass → `interval_affinity_bass` (subject affinity)
- Tail bass → `interval_affinity_bass`
- Tail soprano → `interval_affinity_soprano`

**`builder/phrase_writer.py`**:
- `_write_thematic`: extracts `subject_iv_aff = fugue.subject_interval_affinity()` and
  `cs_iv_aff = fugue.cs_interval_affinity()` after the assert; passes `interval_affinity=subject_iv_aff`
  to inline PEDAL `generate_bass_viterbi`; passes both to `fill_free_bars`.
- `_write_pedal`: extracts `pedal_iv_aff` (None when no fugue); passes `interval_affinity=pedal_iv_aff`
  to `generate_soprano_viterbi`.

Context table: soprano free alongside thematic bass → CS affinity; bass free → subject affinity;
tail/pedal → subject affinity. All new params default None — no behavioural change for non-invention genres.

---

## TB-2a: Subject interval affinity extraction + Viterbi cost term (2026-02-24)

Added interval affinity extraction and cost term for subject melodic vocabulary.

**`motifs/fugue_loader.py`**: two inline helpers (`_build_pitch_class_set`,
`_diatonic_step_count`) that replicate `scale_degree_distance` without importing
from viterbi. Two new `LoadedFugue` methods: `subject_interval_affinity()` and
`cs_interval_affinity()` — count signed diatonic intervals across notes, normalise
to sum=1.0, return `dict[int, float]`.

**`viterbi/costs.py`**: added `COST_INTERVAL_AFFINITY_BONUS = 4.0`, added
`interval_affinity_cost()`, added `interval_affinity: dict[int, float] | None = None`
to `transition_cost`; adds `"iv_aff"` to breakdown.

**`viterbi/pathfinder.py`**: added `interval_affinity` to `find_path`; threaded to
both `transition_cost` call sites and both recursive fallback calls.

**`viterbi/pipeline.py`**: added `interval_affinity` to `solve_phrase`; passed to
`find_path`. All parameters default None — no behavioural change for existing callers.

## TB-1b: Wire degree_affinity to free Viterbi call sites (2026-02-24)

Threaded `degree_affinity: tuple[float, ...] | None = None` from `LoadedFugue.degree_affinity()`
through all layers to the 6 free Viterbi call sites.

**`viterbi/generate.py`**: added `degree_affinity` param; passed to `solve_phrase`.

**`builder/soprano_viterbi.py`**: added `degree_affinity` param; passed to `generate_voice`.

**`builder/bass_viterbi.py`**: added `degree_affinity` param; passed to `generate_voice`.

**`builder/free_fill.py`**: added `degree_affinity` param to `fill_free_bars`; passed to all 4
free Viterbi calls (companion soprano, companion bass, tail bass, tail soprano).

**`builder/phrase_writer.py`**:
- `_write_thematic`: extracts `degree_affinity = fugue.degree_affinity()` after the assert;
  passes to inline PEDAL `generate_bass_viterbi` call and to `fill_free_bars`.
- `_write_pedal`: added `fugue: LoadedFugue | None = None` param; extracts
  `pedal_degree_affinity` (None when no fugue); passes to `generate_soprano_viterbi`.
- `write_phrase`: passes `fugue=fugue` to `_write_pedal` call (Path 1.5).

Thematic stamp paths (`hold_writer`, `cs_writer`, `render_entry_voice`) are untouched.
Non-invention genres have `fugue=None` → `degree_affinity=None` at every level.

---

## TB-1a: Subject degree affinity — extraction + Viterbi cost term (2026-02-24)

**`motifs/fugue_loader.py`**: added `degree_affinity() -> tuple[float, ...]` to `LoadedFugue`.
Walks subject degrees+durations, weights by `duration * metric_weight` (2.0 on beat 1 and
half-bar, 1.0 otherwise), normalises to sum=1.0. Uses `Fraction.limit_denominator(1024)` for
exact offset arithmetic over float durations.

**`viterbi/costs.py`**: added `COST_DEGREE_AFFINITY_BONUS = 3.0`; `_pitch_to_degree_index`
helper (0-based degree index or -1 for non-diatonic); `degree_affinity_cost` (returns
`-BONUS * affinity[deg]` for diatonic pitches, 0.0 otherwise); updated `transition_cost`
with `degree_affinity: tuple[float,...] | None = None` param — adds `dac` to total and
`"deg_aff"` to breakdown dict.

**`viterbi/pathfinder.py`**: threaded `degree_affinity` through `find_path` signature;
passed to both `transition_cost` call sites and both soft-only fallback recursive calls.

**`viterbi/pipeline.py`**: threaded `degree_affinity` through `solve_phrase` signature;
passed to `find_path`. All defaults are `None` — no behavioural change for existing callers.

## PED-1: Pedal soprano harmonic direction (2026-02-24)

Added implied harmonic direction to the dominant pedal phrase.

**`builder/soprano_viterbi.py`**: added `chord_pcs_per_beat: list[frozenset[int]] | None = None`
to `generate_soprano_viterbi`. When provided, bypasses HarmonicGrid and H3 fallback. Default None
preserves all existing callers unchanged.

**`builder/phrase_writer.py`**: added module-level constant `_PEDAL_HARMONY_2BAR_4_4`
(bar_offset, beat_offset, chord_root_degree tuples for I → IV → viio → I progression).
In `_write_pedal`, for 2-bar 4/4 pedals:
- 4 structural knots at strong beats: degrees (5, 4, 7, 1) at (bar 1 beat 1, bar 1 beat 3,
  bar 2 beat 1, bar 2 beat 3)
- Chord grid built from triads: bar 1 uses natural PCS, bar 2 uses cadential PCS (for minor
  key leading-tone correctness)
- Grid expanded to semiquaver resolution (33 entries) via `compute_rhythmic_distribution`
- Contour reduced: START=3.0, NADIR=-2.0, WEIGHT=3.0 (knots now do the structural work)
- Non-2-bar-4/4 pedals: warning logged, single-knot fallback preserved

Result: strong-beat soprano pitches are chord tones of I/IV/viio/I above the G pedal. Bar 2
now audibly different from bar 1 (leading tone B5 at beat 1, tonic C6 at beat 3). Cadential
handoff smooth (F5 → G5, a step).

## DUP-1: Consolidate duplicated utility functions (2026-02-24)

Added `midi_to_name(midi, use_flats=False)` and `degrees_to_intervals(degrees)` to
`shared/pitch.py` as canonical implementations. Deleted 8 local `midi_to_name` variants
across `builder/io.py`, `shared/midi_writer.py`, `builder/faults.py`, `viterbi/mtypes.py`,
`scripts/midi_to_note.py`, `motifs/simple_subject.py`, `scripts/generate_subjects.py`,
and converted `scripts/run_fragen.py` to a 2-line wrapper. Deleted 3 local
`degrees_to_intervals` variants in `motifs/catalogue.py`, `motifs/head_generator.py`,
`motifs/subject_gen/pitch_generator.py`, and removed dead code in `motifs/fragen.py`.
Deleted `_parse_time_signature` from `builder/io.py`; call site now uses `parse_metre`
from `shared/music_math`. No musical behaviour changes.

## BUG-1: Fix _fit_shift key destruction (2026-02-24)

Replaced the fallback branch in `_fit_shift` (`builder/imitation.py`).

Old fallback: returned the non-octave shift closest to zero (e.g. +1 semitone),
destroying tonal identity of subject/CS/answer entries in non-home keys.

New fallback: finds the octave multiple (k×12) nearest to the midpoint of
`[shift_lo, shift_hi]`, accepting minor range overflow per L003 (soft hints).
Three candidates checked (k_near−1, k_near, k_near+1) with tie-break by
proximity to zero. Assert guards the result.

Logs a WARNING when the fallback fires, showing the label, valid range,
chosen shift, and overflow in semitones.

Added `import logging` and module-level `logger = logging.getLogger(__name__)`.

## DBG-1: creator tagging + polyphony asserts (2026-02-24)

Tagged all untagged `Note()` creation sites in `builder/`:
- `hold_writer.py` lines 294, 343 → `creator="hold"`
- `phrase_writer.py` `_write_pedal` line 668 → `creator="pedal"`
- `thematic_renderer.py` `_render_episode_fragment` line 195 → `creator="episode_fragment"`

Verified covered by downstream `replace()` stamps: `cadence_writer.py`, `galant/bass_writer.py`, `galant/soprano_writer.py`. `builder/strategies/diminution.py` confirmed dead code (no imports).

Added `_assert_no_polyphony()` to `builder/compose.py` — called on both voices before `return Composition(...)`.

Added `_assert_within_entry()` helper to `builder/phrase_writer.py` — called at all 7 note-producing paths in `_write_thematic` (HOLD, EPISODE, PEDAL bass, PEDAL voice0, CS+companion, CS, generic loop). ANSWER role uses `beat_role.render_offset` to widen the window start.

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
