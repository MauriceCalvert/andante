# Completed

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
