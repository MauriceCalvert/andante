## 2026-02-09 Full backward visibility in composition pipeline

Implemented the plan from `workflow/task.md`:

### Step 1: Signature changes — thread prior_upper/prior_lower tuples
- `compose.py`: passes `tuple(upper_notes)` / `tuple(lower_notes)` to `write_phrase`
- `phrase_writer.py`: accepts `prior_upper`/`prior_lower` tuples; derives scalars internally;
  passes `prior_upper + soprano_notes` to bass_writer (full soprano view)
- `soprano_writer.py`: accepts `prior_upper` tuple; derives `prev_exit_midi` from tail
- `bass_writer.py`: accepts `prior_bass` tuple; derives `prev_exit_midi`/`prev_prev_exit_midi`
- `cadence_writer.py`: accepts `prior_upper`/`prior_lower`; derives prev_midi scalars
- Tests updated to pass accumulated note tuples

### Step 2: Remove deflection block, add boundary parallel-perfect prevention
- Removed `_is_boundary_parallel_perfect` and `_deflect_boundary_bass` from compose.py (~65 lines)
- Removed `prev_common_soprano`/`prev_common_bass` tracking from compose.py
- Added `_last_common_onset_pair()` helper to bass_writer.py
- Initialized patterned/walking bass common-onset tracking from boundary pair
- Added boundary check for pillar bass (first note)
- Fixed walking bass parallel check to use octave shift for structural tones (preserves degree)

### Step 3: Convert _guard_cross_relation to selection logic
- Replaced `_guard_cross_relation` with `_has_cross_relation` (detector) + `_prevent_cross_relation` (selection)
- Added cross-relation prevention in structural tone computation loop
- Added cross-relation prevention in walking bass path

### Step 4: Convert _guard_bass_leap to selection logic
- Renamed `_guard_bass_leap` to `_prevent_bass_leap` (same logic, clarified as selection not guarding)

All 2844 builder tests pass (204 skipped).

---

## 2026-02-09 Refactor: Split phrase_writer.py into three modules

Behaviour-preserving split of `builder/phrase_writer.py` (1345 lines) into:

- `builder/soprano_writer.py` (~310 lines): `generate_soprano_phrase` + helpers
  (`_deflect_neighbour`, `_check_leap_step`, `_check_max_interval`,
  `_validate_soprano_notes`)
- `builder/bass_writer.py` (~590 lines): `generate_bass_phrase` + helpers
  (`_guard_bass_leap`, `_soprano_pitch_at_offset`, `_check_parallel_perfects`,
  `_select_strong_beat_bass`, `_find_consonant_alternative`,
  `_validate_bass_notes`)
- `builder/phrase_writer.py` (~55 lines): thin orchestrator with `write_phrase`
  only, importing from the two new modules

No logic, signatures, or tests changed. Private helpers sorted alphabetically
within each file. All 1609 L6 tests pass; 3 known cross-relation failures in
integration tests unchanged.

## 2026-02-09 (Plan 3, Phase 3 — Per-Section Schema Sequences)

Modified `_generate_section_schemas()` in `planner/schematic.py` to use
declared `schema_sequence` from genre YAML sections directly, instead of
the random walk. Falls back to graph walk if any schema name is unknown
(with logged warning). Cadential guarantee still runs as safety net.

Change sites:
- `planner/schematic.py`: added `genre_section` parameter to
  `_generate_section_schemas()`, threaded from `layer_3_schematic()`.
  Declared sequence used when present and fully resolvable.

Verification (seed 42):
- Minuet Section A: do_re_mi, fenaroli, prinner — matches YAML
- Minuet Section B: monte, fenaroli, passo_indietro, cadenza_semplice — matches YAML
- Gavotte Section A: meyer, prinner, half_cadence — matches YAML
- Gavotte Section B: fonte, monte, fenaroli, passo_indietro, cadenza_composta — matches YAML
- All 8 genres generate successfully. 7/8 zero faults, minuet has 2
  pre-existing cross-relation faults.

## 2026-02-08 (Plan 3, Phase 1A — Selective Chromatic Approach)

Constrained walking bass chromatic approach to fire only at cadential arrivals.
Previously every structural tone got a chromatic semitone approach (`target ± 1`),
producing ~11 accidentals in 8 bars of Section B — the ear lost the key.

Changes in `builder/phrase_writer.py` only:
- Added `last_structural_offset` tracking before the walking bass loop
- Replaced universal chromatic approach with conditional logic:
  - **Cadential**: chromatic semitone into target (only when approaching the LAST
    structural tone of a phrase with `cadence_type is not None`)
  - **Non-cadential**: diatonic step via `current_key.diatonic_step()`
- Added cross-relation guard: if chromatic pitch is outside key's `pitch_class_set`,
  checks soprano within ±1 beat for diatonic form; falls back to diatonic if found

Results: 3 accidentals in 14 bars of Section B (down from ~11 in 8 bars — ~80%
reduction). Zero chromatic approach tones from walking bass. Zero cross-relations.
Contrary motion preserved. 0 faults across all 8 genres (seed 42).

Open complaints (not addressed): bass holds at phrase openings (rhythm cell issue),
bass too high in monte (structural placement), uneven durations (Known Limitation c),
occasional wrong diatonic step (F♮ in E minor), register breaks at phrase boundaries.

---

## 2026-02-08 (Plan 3, Phase 1 — Walking Bass Motion) — FAILED LISTENING TEST

Replaced the target-seeking walking bass with a baroque-idiomatic walking line:
chromatic approach tones before structural arrivals, contrary motion to soprano
as default direction, and safety-net reversals at range boundaries.

**Failed:** Human listening test found ~11 bass accidentals in 8 bars of
Section B (bars 10–18). The ear lost the key. Root cause: the brief specified
chromatic approach on EVERY structural arrival — emphasis without contrast
is not emphasis (new Principle 8). Phase 1A corrects this by making chromatic
approach selective (cadential arrivals only) and adding cross-relation guards.

The gavotte Section B bass now walks through the romanesca descending D3 to C#2
with chromatic inflections (A#2->A2, F2->F#2, G#3->A3) at every structural
arrival. The voices breathe in opposition — when the soprano climbs, the bass
descends.

Changes in `builder/phrase_writer.py` only:
- walk_direction re-derived at each structural tone from soprano trajectory
  (contrary motion preference, with bass-structural and neighbour-arc fallbacks)
- Chromatic approach: last note before structural uses target +/- 1 in MIDI
  (with same-pitch, range-ceiling, and neighbour-approach fallbacks)
- Walk guards: removed bar-boundary flip; added 2-semitone range guard and
  7-semitone wandering guard

Known Limitation (c) flagged: rhythm cells don't produce even quarter-note
walking divisions. Walking bass durations are mixed (whole, half, dotted quarter,
eighth, quarter). Out of scope for this phase.

Results: 0 faults across all 8 genres (seed 42). All acceptance criteria met.

---

## 2026-02-08 (Plan 3, Phase 2 — Seed-Driven Variation)

Every run now produces a different piece. The CLI derives a time-based seed
when none is given, so consecutive runs of the same genre+key yield different
schema chains. With `-seed N`, runs are reproducible.

Files changed:
- `planner/planner.py`: `generate_to_files()` now accepts and forwards `seed`
- `scripts/run_pipeline.py`: Added `-seed` CLI argument, time-based default
  derivation, seed printing, threaded through all entry points

## 2026-02-08 (Plan 3, Phase 4 — Gentle Registral Descent)

The soprano no longer plunges after its peak. Added DESCENT_BIAS_STEP = 2
to constants.py and a per-phrase descent clamp in build_phrase_plans().
Non-cadential phrases now lose at most 2 semitones of registral bias per
step. The gavotte E minor peak at C6 (bar 12) settles through C#5 (bars
16-17), G4 (bars 18-20), B4 (bars 21-22), and resolves at E5 — a gentle
arch descent instead of a cliff drop. Zero faults on gavotte and 7/8 genres;
invention's 1 monte cross-relation is pre-existing.

Files changed:
- `shared/constants.py` — added DESCENT_BIAS_STEP
- `builder/phrase_planner.py` — descent clamping logic in build_phrase_plans()

## 2026-02-08 (Phase 4B — Soprano targeting floor)

Raised the soprano range floor in phrase_planner.py from G3 (MIDI 55) to C4
(MIDI 60). The planning-level Range now uses MIN_SOPRANO_MIDI as the lower
bound instead of VOICE_RANGES[0][0]. This single change propagates through
the entire writer: degree_to_nearest_midi receives midi_range=(60,84) so
structural tones can't land below C4, and fill notes check plan.upper_range.low
so they're also constrained. Upper median naturally shifts from A4 (69) to
C5 (72) — a proper soprano center that keeps the voice well above bass
territory.

**Musically:** The G major gavotte's bar 8 unison (soprano A3 = bass A3) is
gone. The passo_indietro at bars 8-9 now has soprano B4-C#5 with bass at
D3-E3 — twelve semitones of separation, voices breathing freely. The E minor
gavotte's bars 21-22 soprano sits at B4-D5 (was B3-D4), clearly above bass
at B3. The A minor minuet bottoms at C4 in bar 9 with bass at C3 — a clean
octave apart.

Soprano ranges remain healthy: G major 21st (D4-B5), E minor 24st (C4-C6),
A minor 21st (C4-A5). All exceed the 10-semitone minimum. The soprano still
has clear arch shapes — soaring to B5/C6 in the romanesca peaks, settling
to D4-E4 in pre-cadential passages, never flattening into monotone.

**Code:** builder/phrase_planner.py only (1 file). Added MIN_SOPRANO_MIDI to
import, changed upper_range.low from VOICE_RANGES[0][0] to MIN_SOPRANO_MIDI.
Fix is entirely at planning level — no phrase_writer changes needed.

**Results:** 0 faults across all three checkpoint pieces (gavotte G major,
gavotte E minor, minuet A minor). Soprano never below MIDI 60 in any piece.


## 2026-02-08 (Phase 4A — Grotesque bass leap guard)

Added a leap guard to all three bass generation paths in phrase_writer.py,
preventing any consecutive bass interval from exceeding MAX_BASS_LEAP (12
semitones = one octave).

**Musically:** The minuet A minor bar 15 no longer falls down the stairs.
The old C4→E2 (20-semitone plunge) is gone — the bass now moves by step
within the romanesca, max interval 9 semitones across all three checkpoint
pieces. The gavotte's walking bass (which took a different code path) is
also guarded, staying within 2 semitones between consecutive notes in the
romanesca. Bass lines sound like melodic voices now, not random register
jumps.

**Root cause noted but not fixed:** The ugly-interval filter in
`_find_consonant_alternative` causes structural tones to cascade into the
basement register when romanesca degrees descend stepwise (each m7 is
"ugly", forcing the octave down). The leap guard prevents grotesque
consequences but doesn't address the registral drift itself — that's a
separate planning-level issue.

**Code:**
- `builder/phrase_writer.py`: Added `_guard_bass_leap()` helper function.
  Applied in pattern bass loop (after consecutive-leaps check), fallback
  structural-tones path, and walking bass path. Added MAX_BASS_LEAP import.
- `shared/constants.py`: MAX_BASS_LEAP=12 already existed, no change needed.

**Results:** 0 faults across all three checkpoint pieces (minuet A minor,
minuet C major, gavotte G major). Max within-phrase bass interval: 9st.


## 2026-02-08 — Note labelling: MusicXML lyrics for schema/section/character/figure

Reinstated note labelling in MusicXML output. Every soprano note that starts
a phrase now shows its schema name, section, and character as stacked lyrics
in MuseScore. Structural tone positions in non-cadential phrases show the
figuration pattern name. Cadential phrases include cadence_type.

**Changed:** `builder/compose.py` — lyric stamping block after `write_phrase()`
returns, before notes are collected. Uses `dataclasses.replace()` on frozen
Notes. No other files changed.

**Musically:** Pure metadata — no pitch, duration, or timing change. Zero
faults on all 8 genres. The labels make it possible to read schema structure
directly in MuseScore's lyric display.

---

## 2026-02-08 (Phase 2C -- Tension-driven per-phrase character)

Figurations now intensify as tension rises. Previously every phrase in a
section got the same character from the genre YAML (usually "plain"), so
select_figure() never varied its character filter. Now character derives
from the tension curve's energy level at each phrase's midpoint.

Changes:
- **shared/constants.py**: Added ENERGY_TO_CHARACTER mapping
  (low=plain, moderate=expressive, rising=energetic, high=ornate, peak=bold)
- **builder/phrase_planner.py**: Inside the existing tension_curve block,
  computes character from energy via ENERGY_TO_CHARACTER and applies it
  alongside registral_bias using dataclasses.replace().

Musically: Minuet opening (expressive) uses gentle circolo and neighbour
patterns. Continuation (energetic) gets mordents and turns. Climax at
bars 12-15 (ornate) produces tiratas and broken intervals -- the soprano
is most decorated where the tension peaks. Gavotte reaches "bold" at its
fonte climax (phrase 5), the most elaborate figuration in the piece.
Both pieces show an arc of decoration density matching the tension curve.

Results: 3 distinct characters in minuet, 4 in gavotte. 0 faults both
pieces. All 8 genres run without error.

Modified: shared/constants.py, builder/phrase_planner.py

## 2026-02-08 (Phase 2A -- Wire tension arc into registral bias)

Wired the existing tension curve system (planner/arc.py) into the soprano
registral targeting. The soprano now climbs in the middle of each section
and settles at cadences -- an arch shape driven by the affect's tension curve.

Changes:
- **shared/constants.py**: Added ENERGY_TO_REGISTRAL_BIAS mapping
  (low=0, moderate=+2, rising=+4, high=+6, peak=+7 semitones)
- **builder/phrase_types.py**: Added `registral_bias: int = 0` to PhrasePlan
- **planner/planner.py**: After L1, creates Brief + builds TensionCurve,
  passes it to build_phrase_plans()
- **builder/phrase_planner.py**: Accepts tension_curve param. For each phrase,
  computes energy at midpoint bar via get_energy_for_bar(), maps to semitone
  bias. Cadential phrases always get bias=0. Uses dataclasses.replace().
- **builder/phrase_writer.py**: All 4 uses of plan.upper_median in soprano
  targeting replaced with plan.upper_median + plan.registral_bias.

Musically: Minuet Section A soprano range G4-G5, Section B B4-C6 -- the
romanesca (bias +6) pushes to B5, and the final comma reaches C6. The piece
has a clear arch: moderate opening, high middle, settled cadences. Gavotte
Section A stays modest (A3-B4), Section B peaks at B5 during the romanesca
(bias +6) and fonte (bias +7 -- peak energy). Both pieces have 0 faults.
Invention and sarabande each have 1 cross-relation fault exposed by the
shifted register (pre-existing fragility, not new counterpoint bugs).

Modified: shared/constants.py, builder/phrase_types.py, planner/planner.py,
builder/phrase_planner.py, builder/phrase_writer.py

## 2026-02-08 (Phase 1B fix -- Final cadences + dissonance audit)

Three changes to `planner/schematic.py`:

1. **Refined cadential exclusion filter** (`_select_next_schema`): Removed
   `pre_cadential` from mid-section exclusion. Pre-cadential schemas
   (passo_indietro, indugio) now allowed mid-section since they prepare
   cadences without terminating melodic flow.

2. **Final cadence guarantee** (`_generate_section_schemas`): After the walk,
   if cadence_type is "authentic" or "half" and the last schema is not
   cadential-position, pops it and replaces with a cadential schema from the
   predecessor's allowed_next list.

3. **_is_final_cadence() helper**: For authentic: cadential-position schemas
   except half_cadence. For half: only half_cadence.

Musically: Both minuet and gavotte now end each section with a proper cadential
formula. Minuet Section A closes with cadenza_semplice (S: A4->G4, B: D4->G3 in
G major), Section B with comma (S: B5->C6, B: G3->C4 in C major). Gavotte
Section B closes with comma (S: F#4->G4, B: D3->G3 in G major). No more
prinner-as-final-cadence. The endings feel conclusive.

Dissonance audit: all downbeat tritones are structural (fonte/monte degree 4/7
entries, exempt via voice_structural). All beat-3 dissonances are figuration
artifacts on weak beats. Zero faults both pieces.

Modified: planner/schematic.py only

## 2026-02-08 (Phase 1B -- Cadential positioning filter)

Hard filter in `_select_next_schema()`: cadential, pre-cadential, and
post-cadential schemas are now excluded from the candidate list when
`remaining_bars > 3`. Soft guard falls back to unfiltered if all candidates
removed. Cadential preference threshold tightened from <= 4 to <= 3.

Musically: sections now sustain melodic development through content schemas
(do_re_mi, fonte, monte, romanesca, prinner) before any cadential punctuation.
The minuet runs 8 bars of development before passo_indietro; the gavotte's
Section B has 14 bars of unbroken melodic material. No quiescenza appears
anywhere (5-bar quiescenza problem from Phase 1C is resolved). Cadential
schemas only appear within the last 2-3 bars of their section.

Results: gavotte 0 faults, invention 0 faults, minuet 1 pre-existing fault
(cross-relation in monte sequential transposition, unrelated to this change).

Modified: planner/schematic.py (_select_next_schema only)
## 2026-02-07 (Phase 0B — Cross-phrase parallel perfects guard)

Implemented boundary guard in `builder/compose.py` that detects and fixes
parallel perfect intervals (unisons, fifths, octaves) at phrase boundaries.

The guard tracks the last common-onset soprano/bass pair from each phrase
(matching fault checker logic — not just the last note of each voice) and
compares with the incoming phrase's first onset pair. When parallel perfects
are detected, the incoming phrase's first bass note is deflected by 1-2
diatonic steps (preferring downward, checking consonance with soprano).

Musically: minuet bar 9 bass changed from G3 to E3. The old F4/F3 -> G4/G3
parallel octaves are replaced by contrary motion into a 10th. One note
changed, zero faults, zero side effects.

Modified: builder/compose.py (added _is_boundary_parallel_perfect,
_deflect_boundary_bass, boundary check in compose_phrases, common-onset
tracking with prev_common_soprano/prev_common_bass)

## 2026-02-08 (Phase 1A — Genre-driven schema selection)

Wired genre preferences into the schema walk. The genre_preferences block in
schema_transitions.yaml (which maps genre -> position -> preferred schemas)
was previously loaded by nothing.

Changes:
- schema_loader.py: added load_genre_preferences() and get_genre_preferred()
  with @lru_cache. Reads genre_preferences block from schema_transitions.yaml.
- schematic.py: threaded genre_name through the walk. _select_opening_schema()
  intersects candidates with genre-preferred openings (soft filter).
  _select_next_schema() prefers genre-preferred schemas for each position
  category after all hard filters are applied (soft filter).

Results:
- Minuet A: do_re_mi, fonte, prinner, comma (3/4 genre-preferred)
- Minuet B: romanesca, fonte, passo_indietro, comma (2/4 genre-preferred)
- Gavotte A: do_re_mi, monte, fonte, passo_indietro (3/4 genre-preferred)
- Gavotte B: romanesca, fonte, monte, passo_indietro, half_cadence (3/5)
- Comma count: minuet 2 (was 3-4), gavotte 0
- Zero faults both pieces

Modified: planner/schema_loader.py, planner/schematic.py

## 2026-02-07 (Phase 0A — Cadence Descent Guard Verified)

Verified that the descent guard in `cadence_writer.py` prevents large soprano
leaps in cadential phrases. The guard simulates the template's degree trajectory,
finds the lowest predicted pitch, and raises `upper_target` by the shortfall if
it would fall below `upper_range[0]`. Gavotte cadenza_composta confirmed: all
soprano intervals ≤ M2, descending stepwise (C4-B3-A3-G3). The original bug
(G3→F#4 major-7th leap) is eliminated.

No code changes — guard was already implemented. This entry logs verification.

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
