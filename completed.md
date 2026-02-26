# Completed

## CLR-2: Internal section cadences (2026-02-26)

Added half cadences at every internal section boundary (exordium→narratio, narratio→confirmatio, confirmatio→peroratio).

- `types.py`: Added `cadence_schema: str | None = None` to `BarAssignment`.
- `thematic.py`: Added `cadence_schema: str | None = None` to `BeatRole`.
- `subject_planner.py`: Loaded half_cadence template at startup; in step 2b, inserted `_internal_cadence` entry (schema="half_cadence", key=prev_key) before each auto-episode at section boundaries; added handler in step 3 to stamp function="cadence", local_key, and cadence_schema on those BarAssignments; stamped cadence_schema on final cadence BarAssignments.
- `entry_layout.py`: Propagated cadence_schema from BarAssignment through BeatRole into group dicts; `build_imitative_plans` cadence branch now reads cadence_schema and local_key from the group (not from SubjectPlan.cadence_schema / home_key).

Result: 3 internal HCs at bars 6, 17, 28 (A min, D min, C maj); final cadenza_composta at bars 33-34 unchanged. All HCs in local key, soprano 3→2, bass 1→5, breath 3/8. Total 34 bars (+3). Pipeline clean.

## M005: Remaining violations (2026-02-26)

**M005-3 — `catalogue.py` Fragment dispatch**: Changed `_generate_heads` and `_generate_tails` to accept `frag: Fragment` directly instead of `(intervals, durations, source)`. Updated 7 call sites in `_build_catalogue`. Removed redundant `inv_intervals`, `aug_durations`, `dim_durations` local variables.

**M005-5 — `note_writer.py` single-pass maps**: Replaced 3 separate `_build_key_map`, `_build_phrase_map`, `_build_cadence_map` functions with single `_build_annotation_maps` that iterates `phrase_plans` once, returning a 3-tuple.

**M005-7 — `KeyConfig.mode` property**: Added `mode` property to `KeyConfig` frozen dataclass (`builder/types.py`). Updated 2 production sites (`planner/planner.py`, `planner/metric/layer.py`). Updated 2 test files (`test_system.py`, `test_cross_phrase_counterpoint.py`).

**M005-6 — Test pipeline consolidation**: Added `run_pipeline_l5` and `run_pipeline_l7` to `tests/helpers.py`. Removed duplicated 35-line pipeline setup from 4 test files (`test_L6_phrase_writer.py`, `test_L7_compose.py`, `test_cross_phrase_counterpoint.py`, `test_system.py`). Standardized `home_mode=kc.mode if kc else "major"` across all pipeline calls (fixes test_L7's bug where minor keys used `home_mode="major"`).

Pipeline: 200 soprano + 134 bass notes, unchanged.

## CLR-1: Dynamic cadence type from genre YAML (2026-02-26)

**Plumbing-only task. No audible change.**

- `planner/imitative/types.py`: Added `cadence_schema: str = "cadenza_composta"` to `SubjectPlan`
- `planner/imitative/subject_planner.py`: Reads `cadence_schema` from `thematic_config.get("cadence", ...)`, looks up bar count from `load_cadence_templates()`, replaces `CADENCE_BARS` constant with template-derived value. Removed `CADENCE_BARS` import.
- `planner/imitative/entry_layout.py`: Added `_CADENCE_TYPE_MAP`. Uses `subject_plan.cadence_schema` to select schema and cadence type dynamically instead of hardcoded strings.
- `shared/constants.py`: Removed `CADENCE_BARS: int = 2` (dead).

Pipeline: 200 soprano + 134 bass notes, unchanged.

## M-violations Tasks 6-8: M005-2, M005-1, M003-6 (2026-02-26)

**M005-2 — `Schema.bar_count` property** (`shared/schema_types.py`):
Added `bar_count` property (sequential: `max(segments)`, else `len(soprano_degrees)`).
Replaced all 10 `_schema_bars()` call sites in `planner/schematic.py` with `schema_def.bar_count` / `schema_defs[s].bar_count`. Deleted `_schema_bars()` function.

**M005-1 — `Anchor.sort_key()` method** (`builder/types.py`):
Added `sort_key() -> float` that inlines `bar_beat_to_float` logic directly on the dataclass.
Updated 2 sort lambdas in `planner/metric/layer.py` to use `a.sort_key()`. Removed `bar_beat_to_float` import from `layer.py`.

**M003-6 — `_build_thematic_roles` accepts `metre`** (`planner/imitative/entry_layout.py`):
Changed signature from `(beats_per_bar: int, beat_unit: Fraction)` to `(metre: str)`. Function now calls `parse_metre` internally. Updated call site in `build_imitative_plans`.

Pipeline verified: 200 soprano + 134 bass notes, identical to pre-change output.

## ICP-2c: CS lyric labels cs1 / cs2 (2026-02-26)

**Work**: Labelling-only fix. CS notes now carry `cs1` or `cs2` in the MusicXML lyric
instead of bare `cs`.

**`builder/cs_writer.py`**: Step 9 label changed from `"cs"` to `f"cs{cs_index + 1}"`.

**`builder/entry_renderer.py`**: CS branch now parses `cs_index` from `beat_role.material`
and sets `lyric=f"cs{cs_index + 1}"`.

**`builder/compose.py`**: `_stamp_lyrics` whitelist guard extended from exact `"cs"` match
to `startswith("cs")` so any `csN` label survives the schema-metadata stamp-over. This was
the root bug: `cs1`/`cs2` were being silently overwritten by `subject_entry/exordium/plain`.

**Verified**: 4 CS lyrics in output XML — 2× `cs1` (bars 2, 11) and 2× `cs2` (bars 4, 18).

---

## ICP-2b: CS2 scheduling and rendering (2026-02-26)

**Work**: Wired CS variant selection through the full pipeline so development entries
alternate between CS1 (index 0) and CS2 (index 1). Six files modified, no new files.

**`planner/imitative/subject_planner.py`**: `generate_entry_sequence()` assigns
`cs_variant = (subject_cs_count + 1) % 2` before incrementing, stores it in the
entry dict. `plan_subject()` reads it into `VoiceAssignment.fragment`.

**`planner/imitative/entry_layout.py`**: `_build_thematic_roles()` overrides
`material = voice_assignment.fragment` for the "cs" role when fragment is not None.

**`builder/imitation.py`**: `countersubject_to_voice_notes()` gains `cs_index: int = 0`
param; uses `fugue.get_countersubject_midi(index=cs_index)` and
`fugue.get_countersubject(index=cs_index).durations`.

**`builder/thematic_renderer.py`**: `render_thematic_beat()` parses `cs_index` from
`role.material.isdigit()` guard; passes to `countersubject_to_voice_notes`.

**`builder/cs_writer.py`**: `generate_cs_viterbi()` gains `cs_index: int = 0` param;
uses indexed CS accessor methods.

**`builder/phrase_writer.py`**: `_write_thematic()` hoists `cs_index` computation
before Viterbi/fallback branches; passes to `generate_cs_viterbi`; trace updated to
`role_name=f"CS[{cs_index}]"` for verification.

**Result**: Trace confirms CS[0] at exposition (bar 2) and second dev entry (bar 11),
CS[1] at first dev entry (bar 4) and third dev entry (bar 18). Pipeline runs clean.
CS2 degrees `[-10,-9,-7,-8,...]` differ structurally from CS1 `[-8,-7,0,-1,...]`,
producing audibly distinct companion contours (steady descent vs hook-and-drop).

## ICP-2a: Second countersubject data layer (2026-02-26)

**Work**: Added CS2 infrastructure — generate at invertible tenth (distance 9),
store in YAML, load with backward compatibility, expose via accessor methods.

**`scripts/generate_subjects.py`**: Added `CS2_INVERSION_DISTANCE = 9` constant,
`countersubject_2` field to local SubjectTriple, CS2 generation in `generate_triple()`,
CS2 YAML output in `write_subject_file()`, `patch_library_files()` function, and
`--patch-library` CLI flag.

**`motifs/subject_loader.py`**: Added `countersubject_2: LoadedCountersubject | None = None`
to SubjectTriple, CS2 parsing in `_parse_triple_data()`, and `get_countersubject()` /
`get_countersubject_midi()` methods with CS1 fallback.

**`motifs/library/*.subject`**: All 6 library files patched with CS2 at distance 9.
`countersubject_midi()` and ThematicBias untouched.
Pipeline output unchanged.

## Knot Consolidation + Fix-1 verification (2026-02-26)

**Work**: Created `builder/knot_builder.py` as the single home for shared
knot utilities, eliminating duplicated logic across 5 files.

**Six utilities extracted**:
- `find_consonant_pitch` — from `cs_writer._find_consonant_near` and
  `hold_writer._find_consonant_near` (exact duplicates)
- `sort_and_dedup_knots` — from `soprano_viterbi` and `bass_viterbi` (both files)
- `ensure_final_knot` — from `soprano_viterbi` and `bass_viterbi` (both files)
- `check_structural_tone_consonance` — from `soprano_viterbi._check_knot_consonance`
- `strong_beat_offsets` — from `cs_writer._strong_beat_offsets`
- `enrich_companion_knots` — from `free_fill._enrich_companion_knots`

**Files updated**: `cs_writer.py`, `hold_writer.py`, `soprano_viterbi.py`,
`bass_viterbi.py`, `free_fill.py` — all call sites updated to use knot_builder.

**motifs/thematic_transform.py**: Promoted lazy `from viterbi.mtypes import Knot`
inside two function bodies to top-level import.

**Fix-1 verification**: Both fixes already implemented —
- Fix A (entry_layout.py): hold-exchange continuation merges into single group
- Fix B (soprano_viterbi.py): `_check_knot_consonance` exists and is called

Deleted `workflow/queue/fix1_hold_knots.md`. Pipeline ran clean (200 sop / 134 bass notes).

## PED-2: Pedal soprano knots follow contour (2026-02-26)

**Problem**: Pedal soprano in bars 28-29 leaped B5 at bar 29 beat 1 (major
7th from A4). Four structural knots (degrees 5, 4, 7, 1) were all placed
near the range ceiling via registral_bias=9, conflicting with the cup
contour that demands a nadir at ~50% progress.

**Fix**: Pre-compute knot MIDIs by interpolating the cup contour at each
knot's progress position, converting to a target MIDI, then using
degree_to_nearest_midi for octave selection. Knots passed via
bias.structural_knots, bypassing place_structural_tones entirely for the
2-bar 4/4 pedal path. Degree 7 now lands at B4 (step from A4) instead of
B5 (7th leap).

**Files**: `builder/phrase_writer.py` (_write_pedal)

## USI-3: Cell knot leap guard in sequence_cell_knots (2026-02-26)

**Change**: Added `MAX_KNOT_LEAP: int = 9` module constant and a post-selection leap
guard loop in `sequence_cell_knots` (`motifs/thematic_transform.py`). After
`build_thematic_knots` produces `new_knots`, each knot is checked against the previous
accepted pitch; knots that leap > 9 semitones are octave-shifted (if the shift lands in
range) or dropped. `current_midi` in step (i) updates only from the last accepted knot.

**Result**: `ugly_leap` fault count reduced from 5 to 3. The two mid-cell leaps at
bars 22 and 25 beat 3 (offsets 43/2 and 49/2) are eliminated. Three pre-existing leaps
remain (stretto entries at bars 23/28 beat 1 and peroratio leap at bar 29 beat 1),
all with different root causes outside `sequence_cell_knots`.

**Files**: `motifs/thematic_transform.py` only.

## USI-2: Companion knot enrichment — seed from actual previous pitch (2026-02-26)

**Change**: Added `seed_pitch: int | None = None` to `_enrich_companion_knots` in
`builder/free_fill.py`. Replaced the `companion_median` initialiser of `prev_pitch`
with `seed_pitch if seed_pitch is not None else companion_median`. Passed
`soprano_notes[-1].pitch` at the soprano FREE call site and `bass_notes[-1].pitch`
at the bass FREE call site.

**Rationale**: The first enriched knot was previously anchored to the voice median,
forcing the Viterbi solver to leap a 7th to reach it from the thematic tail. Seeding
from the last actual note before the FREE run keeps the first knot within a 3rd of
the seam, eliminating the D5→C6 splices at bars 22 and 25 beat 3.

**Files**: `builder/free_fill.py` only (signature, seed init, two call sites).

## CAD-1: Cadenza composta 4/4 bass formula (2026-02-26)

**Change**: Replaced four-minim block-chord bass (degrees [4,5,5,1], all 1/2) with a
five-note pre-dominant approach: IV(♩)→ii(♩)→V(𝅗𝅥)→V(𝅗𝅥)→I(𝅗𝅥).

**Rationale**: The old bass had no rhythmic momentum — four identical minims sounded
like a harmonisation exercise. The new formula introduces crotchet motion in bar 1
(IV→ii), arrives on V at beat 3, sustains V through bar 2, and resolves to I with a
full minim. Duration invariant preserved: 1/4+1/4+1/2+1/2+1/2 = 2 whole notes.

**Files**: `data/cadence_templates/templates.yaml` (YAML only, no code changes)

## FIX-1: Hold-exchange grouping + structural knot tritones (2026-02-26)

**Fix A — Hold-exchange group continuation (`planner/imitative/entry_layout.py`)**

Added `_HOLD_EXCHANGE_ROLES` module constant and a new `elif` branch in
`_group_beat_roles` that fires before the general split condition. When both
the current group and the incoming bar have `function="hold_exchange"`,
`voice_roles == {HOLD, FREE}`, and the same `entry_index`, the group is
extended rather than split. This ensures a 2-bar hold-exchange produces one
`PhrasePlan` with `bar_count=2`, so `cell_iteration` advances (0, 1) across
the bar boundary and the descending staircase character activates.

**Fix B — Structural knot tritone avoidance (`builder/soprano_viterbi.py`)**

Added `_check_knot_consonance` helper. After `place_structural_tones` returns
in the non-override path, each structural tone is checked against the bass note
sounding at that offset. If `abs(midi − bass) % 12` is in
`STRONG_BEAT_DISSONANT`, octave shifts (±12) are tried; the first candidate in
range that clears the dissonance is accepted. Falls back to original if no
consonant octave exists. Guarded by `if bass_notes` so the first-voice
(bass-absent) path is unaffected.

**Files**: `planner/imitative/entry_layout.py`, `builder/soprano_viterbi.py`

## USI-1: Companion soprano structural knot enrichment (2026-02-26)

**Problem**: Soprano Viterbi in FREE companion fills produced 7th leaps and
missing step recovery because it received too few structural knots (1-2
waypoints across 2-3 bars).

**Fix**: Added `_enrich_companion_knots` to `builder/free_fill.py`. After
thematic knots are built for each FREE bar run, the function supplements sparse
sets with consonant strong-beat pitches derived from the material voice. For
each strong beat (every half-bar in 4/4, every bar in 3/4) that has no
existing thematic knot within proximity, it picks the companion pitch at a
consonant interval class (m3/M3/m6/M6 = 3,4,8,9 semitones) with the material
note sounding at that beat, nearest to the previous knot pitch.

The enrichment is called in both FREE-voice branches:
- Soprano FREE: uses `bass_notes` as material, `upper_range` for companion
- Bass FREE: uses `soprano_notes` as material, `lower_range` for companion

Enrichment is strictly additive — existing thematic knots are never removed.

**Files**: `builder/free_fill.py`

## PSF-1: Peroration stretto fix — entry_index grouping (2026-02-26)

**Problem**: Two consecutive peroration stretto entries with identical criteria
(key=I, delay=2) merged into one 6-bar group. Renderer produced 3 bars of
stretto material; bars 4-6 of the peroration were hollow.

**Fix**: Added `entry_index: int` (monotonic per augmented entry) to
`BarAssignment` and `BeatRole`. Stamped it from `enumerate(augmented_entries)`
in `plan_subject()`. Added as a grouping criterion in `_group_beat_roles()` —
when `entry_index` changes, close the current group regardless of structural
identity.

**Files**: `planner/imitative/types.py`, `planner/imitative/subject_planner.py`,
`planner/thematic.py`, `planner/imitative/entry_layout.py`

## ICP-1: True double invertible counterpoint (2026-02-26)

**Goal**: Support inversion distances 7 (octave), 9 (tenth), 11 (twelfth) in
the CS generator. Store distance in the .subject file. Validate the inverted
orientation post-solve.

**Changes**:
- `motifs/countersubject_generator.py`: Added `STANDARD_CONSONANCES`,
  `VALID_INVERSION_DISTANCES`, `_consonances_for_distance()` with module-level
  regression assert. Added `inversion_distance` field to `GeneratedCountersubject`.
  Added `inversion_distance` param to `generate_countersubject()`; replaced
  hardcoded strong-beat consonance sets with dynamic call. Added
  `_validate_inverted_orientation()` post-solve belt-and-braces check.
  Updated `verify_countersubject()` to use distance-aware consonance set and
  check inverted orientation.
- `motifs/subject_loader.py`: Added `inversion_distance: int = 7` to
  `LoadedCountersubject`; parser reads from YAML with default 7 for
  backward compatibility.
- `scripts/generate_subjects.py`: Added `inversion_distance` param to
  `generate_triple()`, wired to `generate_countersubject()`. `write_subject_file()`
  now writes `inversion_distance` to countersubject YAML section. Added
  `--inversion-distance` CLI argument (choices: 7, 9, 11).

## STV-1: Stretto variety and form extension (2026-02-26)

**Goal**: Use both stretto offsets to create rhetorical arc — wide distance in development,
tightest in peroration. Extend invention to scope: extended (31 bars, 5 dev entries).

**Changes**:
- `planner/imitative/subject_planner.py`: Replaced single `min(stretto_offsets)` with
  rotation logic. Peroration strettos (key=="I") always get tightest offset. Development
  strettos cycle widest-first via `dev_stretto_count % len(sorted_offsets)`. Result:
  dev stretto 0 = 3-beat delay, dev stretto 1 = 2-beat delay, peroration = 2-beat delay.
- `data/genres/invention.yaml` brief: `scope: extended`, `stretto: multiple`,
  `key_journey_major: [vi, IV, V, ii, iii]`.
- `builder/cs_writer.py`: Fixed octave-shift algorithm. Old two-pass loop failed when no
  multiple of 12 fell in the valid shift range (D minor CS, span=17 semitones). New algorithm
  computes valid range directly and prefers nearest octave-multiple, falls back to center.

**Open fault (out of scope)**: bars 23-25 near-silent. Two peroration stretto_sections with
same key+delay are merged into one 6-bar group by `_group_beat_roles`; only the first 3 bars
have notes. Fix requires either deduplication-aware rendering or different delay for second
peroration stretto.

## EXP-1: Exposition overlap voice-leading (2026-02-26)

**Problem**: with `answer_offset_beats=4` in 4/4, the answer entered mid-way through
the solo-subject phrase via `render_offset=-1 bar`. The subject's bar-2 notes were
still emitted, producing a tritone against the answer's first note — the listener's
first two-voice moment.

**Fix — `planner/imitative/subject_planner.py`**: after computing per-entry bar costs,
when `answer_offset_beats > 0`, find the entry preceding the first "answer" entry and
reduce its cost by `overlap_bars = answer_offset_beats // beats_per_bar`. For invention:
entry 0 cost 2→1 (bar 1 only), entry 1 cost unchanged (bars 2–3). Total exposition
3 bars (was 4).

**Fix — `planner/imitative/entry_layout.py`**: removed the `render_offset` patching
block. Phrase [1] now starts at the answer entry point; `render_offset=0` (the
BeatRole default) is correct. The old negative shift would have displaced the answer
a full bar backwards.

**Result**: subject sounds bar 1 solo; CS enters bar 2 simultaneously with the answer
bass. No subject remnant at bar 2. Two-voice writing begins with CS vs answer (both
designed to be consonant together).

## HG-1: Surface chord inference for bass Viterbi
- `builder/bass_viterbi.py`: imported `triad_pcs as viterbi_triad_pcs` from `viterbi.scale`; added `else` branch in step 4 to derive `chord_pcs` from soprano pitches when no `harmonic_grid` is provided; non-diatonic soprano PCs produce empty `frozenset()` to avoid assertion failure
- Pipeline runs clean on `invention.brief` (seed 42): 151 soprano + 88 bass notes, 8 faults (all pre-existing), zero new faults from surface inference
- Surface inference confirmed executing for both stretto companion fills

## Subject generator bug fixes and rhythm cell expansion
- `duration_generator.py`: added `_spans_barline()` rejecting notes crossing bar boundaries; `bar_ticks` threaded through `_generate_sequences`; cache key v6
- `melody_generator.py`: rule 6.4b rejects consecutive repeated final pitch; CP patterns for 4 new cells (pyrrhic, snap, tribrach, amphibrach)
- `pitch_generator.py`: cache key bumped to `melody_pitch_v2`
- `rhythm_cells.py`: added PYRRHIC (1,1), SNAP (1,3), TRIBRACH (1,1,1), AMPHIBRACH (1,2,1); `notes` field replaced with derived `@property`; transition table expanded 7×7 → 11×11

## BM-3b: Scoring extension and dead code removal
- `constants.py`: added `W_HARMONIC_VARIETY: float = 1.0`
- `scoring.py`: added `_harmonic_variety()` — counts how many of I/IV/V/ii are touched by the degree sequence (mod 7), scores (touched-1)/3.0 clamped to [0,1]; functions reordered alphabetically (D, H, I, Re, Rh, S); `score_subject` max raised from 5.0 to 6.0; `subject_features` extended from 6D to 7D with harmonic variety as 7th dimension
- Deleted dead files: `head_enumerator.py`, `cpsat_generator.py`, `cpsat_prototype.py` — no import references remain in source

## BM-3a: Wire melody generator into pipeline
- `duration_generator.py`: `_generate_sequences` now yields `(indices, cells, score)`; `_cached_scored_durations` returns `dict[int, list[tuple[tuple[int,...], tuple[Cell,...]]]]`; cache key changed to `cell_dur_v2_*` to avoid stale cache reads
- `pitch_generator.py`: full rewrite — old cpsat/head_enumerator path deleted; new `_cached_validated_pitch_for_cells` delegates to `generate_pitched_subjects` and caches by `(cell_key, mode, n_bars, bar_ticks)`
- `selector.py`: import updated to `_cached_validated_pitch_for_cells`; main loop restructured to iterate `(d_seq, cells)` per dur_option and call pitch gen per cell sequence; HEAD_SIZE/MIN_HEAD_FINAL_DUR_TICKS filters applied before pitch gen; `fixed_midi` branch updated to unpack `(d_seq, _cells)`; `Cell` import added for type annotation

## BM-2: Melody generator
- Created `motifs/subject_gen/melody_generator.py`: pitch generation engine (steps 1-7 of baroque_melody.md)
- NoteSlot dataclass, CP_PATTERNS table (data not if-chains), recursive skeleton enumeration with gap/freq/range pruning, deterministic P-slot fill with neighbour-tone detours, full section-6 validation including melodic minor raising, contour classification
- Checkpoint: major 1 result, minor 1 result for spec test sequence; DOTTED*4 produces 2 per mode
- Some cell patterns (DACTYL*4, TIRATA*4) produce 0 results due to structural constraint interaction

## BM-1: Harmonic grid data module
- Created `motifs/subject_gen/harmonic_grid.py`: stock progressions (12 patterns, 3 levels), chord-tone sets (major+minor), minor equivalents, harmonic level selection, chord_at_tick lookup, cross-relation check, melodic minor helpers (degree_to_semitone, should_raise, is_raised_chord_degree)
- Pure data + lookup, no generation logic, no pitch pipeline imports
- All checkpoint assertions pass

## Cell-based rhythm engine (replaces bar-fill duration enumerator)
- Created `motifs/subject_gen/rhythm_cells.py`: Cell dataclass, 6 baroque rhythm cells, CELLS_BY_SIZE, TRANSITION table, SCALES
- Rewrote `motifs/subject_gen/duration_generator.py`: partition-based cell sequence generation with transition filtering and scoring
- Updated `motifs/subject_gen/constants.py`: DURATION_TICKS expanded to (1,2,3,4,6) for dotted values; removed 5 dead bar-fill constants
- `_cached_scored_durations` signature unchanged; new cache key `cell_dur_*`
