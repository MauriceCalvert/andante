# Completed

## 2026-02-14: TP-A — Subject Catalogue + Thematic Planner Skeleton

**Goal:** Build fragment library and beat-level planning infrastructure for thematic composition. No musical output change.

**Implementation:**
1. Created `motifs/catalogue.py`:
   - Fragment dataclass (name, intervals, durations, total_duration, source)
   - SubjectCatalogue class extracts all fragments from LoadedFugue
   - Transforms: head(n), tail(n), inversion, augmentation, diminution
   - 14 fragments generated from call_response.fugue

2. Created `planner/thematic.py`:
   - ThematicRole enum (SUBJECT, ANSWER, CS, EPISODE, CADENCE, STRETTO, LINK, PEDAL, FREE)
   - BeatRole dataclass with complete beat-level assignment fields
   - plan_thematic_roles() stub returning all FREE (192 beat-roles for invention)

3. Modified `builder/phrase_types.py`:
   - Added `thematic_roles: tuple | None = None` to PhrasePlan

4. Modified `planner/planner.py`:
   - When genre has `thematic:` section: build catalogue, plan roles, slice per phrase
   - When absent: skip entirely (galant genres unaffected)

5. Modified `data/genres/invention.yaml`:
   - Added thematic: section with voice_count, exposition, stretto, pedal, episode_derivation, invertible_counterpoint

6. Modified `scripts/yaml_validator.py`:
   - Added "thematic" to VALID_GENRE_KEYS

**Result:**
- Invention pipeline runs successfully with thematic infrastructure
- SubjectCatalogue: 14 fragments extracted
- Thematic plan: 192 beat-roles (96 beats × 2 voices), 100% FREE
- Musical output unchanged (all FREE means builder behaves as before)
- All 8 genres in test suite pass
- Galant genres (gavotte, minuet, sarabande) completely unaffected

**Next:** TP-2 will implement actual role assignment (SUBJECT, ANSWER, CS) and thematic renderer.

## 2026-02-14: INV-2 + INV-3 (Episodes and Stretto)

**What was done:**

- **INV-2 (Episodes):** Created `builder/episode_writer.py` to generate episodes from subject head fragments. Episodes place the first bar of the subject in the lead voice at each segment (bar) of sequential schemas (fonte, monte), transposed to the segment's local key. The non-fragment voice uses Viterbi fill. Modified `phrase_planner.py` to assign `imitation_role="episode"` and `phrase_writer.py` to dispatch. Added lyric column to .note output.

- **INV-3 (Stretto):** Added `_write_stretto_phrase()` in `phrase_writer.py` to place subject in both voices with 1-beat delay (close stretto). Voice A starts at phrase beginning, voice B enters 1 beat later. Modified `phrase_planner.py` to assign `imitation_role="stretto"` to first non-cadential phrase in peroratio. Includes fallback to subject entry when phrase too short.

**Musical result:**

- Episodes (monte schema, bars 7-9): Bass states subject head fragment at each ascending step (C-F-G-F → D-G-A-G → E-A-B-A), creating recognizable motivic development between subject entries. Soprano provides continuous counterpoint.

- Stretto: Implementation complete. Default planning generates 2-bar peroratio phrases (too short for stretto with 2-bar subject + delay). Fallback mechanism works correctly. Stretto will execute when longer peroratio phrases are generated.

**Files:** New: `builder/episode_writer.py`. Modified: `phrase_planner.py`, `phrase_writer.py`, `note_writer.py`. All 8 genres pass.

## INV-1 — Countersubject in All Subject Entries (2026-02-13)

Modified `_write_subject_phrase` to place the countersubject in the free voice for all non-monophonic subject entries (narratio, confirmatio, peroratio). Previously, only the exordium answer phrase received a CS; all other subject entries generated the free voice via Viterbi, producing wallpaper instead of dialogue.

**Musical result (Bob):**
- Subject entries now sound like two-part dialogues with recognisable melodic material in both voices
- Rhythmic complementarity: CS and subject use identical duration profiles, creating interlocking texture
- Contrary motion visible at subject entry points (e.g., narratio bar 5: soprano ascends B4→E5, bass descends G3→C3)
- Clear texture shift at subject entries: pre-composed CS creates denser contrapuntal texture vs. surrounding Viterbi fill

**Changes (1 file modified, 0 new files):**
- `builder/phrase_writer.py:115-160,185-222`: Added CS generation in both lead_voice branches of `_write_subject_phrase`
  - Soprano-led (lead_voice==0): bass receives CS via `countersubject_to_voice_notes`, padded to tail offset, tail bass generated via `_bass_for_plan`
  - Bass-led (lead_voice==1): soprano receives CS via `countersubject_to_voice_notes`, padded to tail offset, tail soprano generated via `generate_soprano_viterbi`

**Technical verification (Chaz):**
- All 8 genres run without error
- CS transposed correctly to local key of each entry (verified narratio A minor, peroratio G major)
- Existing `countersubject_to_voice_notes` API used; no new dependencies

**Open issues carried to INV-2:**
- Exordium lacks answer phrase (genre YAML provides only 1 non-cadential schema; `_assign_imitation_roles` has no target for "answer")
- Tail bars after CS revert to Viterbi fill (motivic continuity addressed in INV-2)
- Episode phrases lack subject fragments (INV-2 scope)

---

## HRL-2 — Harmonic Grid Wired into Voice Generation (2026-02-13)

Wired schema-annotated Roman numeral harmony into both soprano and bass Viterbi voice generation. Both voices now read from the same harmonic source (schema YAML annotations) instead of inferring chords from surface bass.

**Changes (4 files, no new files):**
- `builder/harmony.py:184-198`: Fixed to_beat_list() to accept absolute offset floats; added sequential schema tiling (harmony pattern repeats across segments)
- `builder/soprano_writer.py:199,303-352`: Added harmonic_grid parameter; replaced H3 surface-bass inference with grid lookup as primary path; H3 fallback retained with warning
- `builder/bass_viterbi.py:36,217-226`: Added harmonic_grid parameter; bass receives chord_pcs_per_beat for first time (was None before)
- `builder/phrase_writer.py:7,24,51-67,385-404`: Build grid from schema.harmony in galant path; pass to both soprano/bass Viterbi

**Musical effect:** Strong-beat notes land more consistently on chord tones. Harmony column in .note files now populated with Roman numerals at every beat (I, V, vi, IV, etc.). Both voices agree on active chord at each moment. Bass has harmonic awareness without over-constraint (still moves melodically with passing tones).

**Checkpoint (Bob+Chaz):** Evaluated gavotte, invention, minuet. All genres show proper harmonic awareness. Bass doesn't sound arpeggio-like or "stuck" despite new chord-tone magnetism. Sparse grid limitations (one chord per schema position) acceptable for Phase 1. All 8 genres run without error.

**Acceptance criteria met:** Both voices receive grid data (non-cadential, non-imitative) ✓ | H3 bypassed ✓ | Bass gets chord_pcs_per_beat ✓ | All genres run ✓

**Next:** VG5 (cost weight tuning) when needed. HRL Phase 2 (harmonic interpolation) to densify grid for faster harmonic rhythm.

## HRL-1 — Harmonic Grid Infrastructure (2026-02-13)

Built schema-annotated harmonic grid infrastructure. Every phrase now knows what chord is active at every beat via curated Roman numeral annotations in schema YAML.

**Components:**
- `shared/schema_types.py`: Added `harmony: tuple[str, ...] | None` field to Schema
- `planner/schema_loader.py`: Parse harmony from YAML (both segment and non-segment schemas), validate length matches degrees
- `builder/harmony.py`: New module (202 lines) with ChordLabel, parse_roman(), chord_pcs(), HarmonicGrid, build_harmonic_grid()

**Vocabulary:** I, ii, iii, IV, V, V7, vi, viio (major), i, III (minor). Systematic parser handles Roman numeral base + quality suffix (case/o/+) + 7th. Members are scale degrees (1-7), converted to pitch classes via Key with quality adjustment for minor-key V/viio.

**HarmonicGrid:** Block-style lookup with chord_at(offset), chord_pcs_at(offset), to_beat_list(). Returns tonic before first entry, extends last chord indefinitely. Never returns None.

**Checkpoint:** All 16 schemas annotated. All 9 unique numerals parse correctly. C major grid verified. A minor V produces {E, G#, B} = {4, 8, 11} (quality adjustment working). to_beat_list length matches input.

**Files:** shared/schema_types.py (+1 line), planner/schema_loader.py (+10 lines), builder/harmony.py (+202 lines).

**No musical output:** Infrastructure only. Voice generation unchanged until HRL-2 integration.

## VG3.1 — Hard Counterpoint Constraints (2026-02-13)

Implemented 6 hard counterpoint constraints in the Viterbi solver, replacing soft-cost-only approach with mandatory rules enforced via `HARD = float("inf")`. Constraints ensure fundamental baroque counterpoint correctness in all Viterbi-generated fill passages.

**Hard Constraints:**
- HC1: Anti-stasis (three consecutive identical pitches forbidden)
- HC2: Spacing ceiling (>24 semitones forbidden)
- HC3: Parallel perfects (moved from soft cost, now absolute block)
- HC4: Tritone on strong beat (two-voice texture only)
- HC5: Leap recovery (≥fifth must step back; relaxed from ≥fourth to allow thirds)
- HC6: Similar-motion leaps (both voices ≥third in same direction forbidden)

**Files:** `viterbi/costs.py` (added `HARD`, `hard_constraint_cost()`, removed parallel-perfect from `motion_cost`, raised `COST_STEP_UNISON` to 15.0), `viterbi/pathfinder.py` (added `hard_constraints` parameter, infeasibility fallback, optimized DP to skip infinite-cost transitions).

**Tests:** All 8 genres pass with zero fallbacks. HC5 initially at dist≥3 caused 50+ fallbacks; relaxed to dist≥4 achieves 0% fallback rate. Consonance: 5 of 8 genres ≥90% on strong beats (target was 7 of 8; shortfall due to structural schema knots with tritones, not Viterbi fill).

**Bob/Chaz Evaluation:** All hard constraints working correctly for Viterbi fill. Remaining issues (tritones on strong beats, bass stasis in chorale bars 1–3, voice gap in sarabande bar 5) traced to upstream structural knot placement (schema degree mapping + octave selection), which occurs before Viterbi runs. The solver cannot override hard-pinned schema degrees. Parallel fifths/octaves eliminated entirely. Similar-motion leaps eliminated. Unrecovered large leaps eliminated.

**Verdict:** VG3.1 complete. Hard constraints successfully enforce counterpoint rules in all Viterbi-generated passages. Structural issues require separate upstream task.

## VG1 — Unified Solver: N-voice pairwise cost function (2026-02-13)

Refactored Viterbi solver from single-leader to N-voice pairwise cost
evaluation. `LeaderNote` replaced by `ExistingVoice` throughout the solver
pipeline. `transition_cost` now iterates over a list of existing voices,
calling `pairwise_cost()` per voice. `build_corridors`, `find_path`, and
`solve_phrase` all accept `existing_voices: list[ExistingVoice]`.

**Files:** `viterbi/mtypes.py`, `viterbi/costs.py`, `viterbi/corridors.py`,
`viterbi/pathfinder.py`, `viterbi/pipeline.py`, `builder/soprano_writer.py`,
`builder/bass_viterbi.py`, `viterbi/test_brute.py`, `viterbi/demo.py`,
`viterbi/bach_compare.py`.

**Tests:** test_brute 200/200. All 8 genres produce identical output.
Zero `LeaderNote` in core solver files. Bit-identical two-voice output.

## BV1 — Bass Viterbi for Walking Texture (2026-02-13)

Replaced greedy forward-pass walking-bass generator with Viterbi pathfinding
against the soprano for walking-texture phrases.

**Files:** `builder/bass_viterbi.py` (new), `builder/bass_writer.py` (public
validate), `builder/phrase_writer.py` (dispatcher). All 8 genres pass, zero
faults on gavotte and invention.

**Open:** Whole-note pedal in walking sections (bar 18), occasional repeated
pitches in Viterbi walking bass.

## VG2 — Remove Hard Filters (2026-02-13)

Removed hard consonance and voice-crossing filters from the Viterbi solver.
Range is now the only hard constraint. All other constraints (consonance,
voice crossing, parallel fifths, dissonance) are soft costs.

**Changes:**
- Added `voice_crossing_cost()` to `viterbi/costs.py` with graduated cost
  (COST_VOICE_CROSSING_BASE = 15.0 + 3.0 per semitone depth)
- Removed strong-beat consonance filter from `viterbi/corridors.py:build_corridors`
  — all beats now get all diatonic pitches in range
- Removed bass voice-crossing post-filter from `builder/bass_viterbi.py` step 4
- Relaxed bass knot consonance check in `builder/bass_viterbi.py` step 1 to
  soft preference (try octave shift to consonance, log warning if none exists,
  keep original)
- Added `vc=` term to `viterbi/pathfinder.py` verbose output

**Tests:** test_brute 200/200 passed with wider search space. All 8 genres run
without error. Bob/Chaz evaluation complete.

**Results:**
- Voice crossing rate: 0.00% (target <5% — met)
- Strong-beat consonance rate: 73.8% (target >90% — not met)
- Listening gate required before VG3

**Analysis:** The architecture is correct. The solver now considers dissonances
on strong beats and can theoretically choose voice crossings. It rarely does
because the costs are high enough to maintain baroque norms. However,
COST_UNPREPARED_STRONG_DISS = 50.0 is too low relative to melodic costs
(leap, contour deviation). The solver accepts unprepared strong-beat
dissonances ~26% of the time because avoiding them would require suboptimal
melodic paths.

**Open:** Cost tuning needed to reach 90% consonance target. Options: (A) raise
COST_UNPREPARED_STRONG_DISS to 100-150, (B) bi-directional knot consonance
adjustment, (C) defer to VG5 style-as-weights tuning. Recommend (A) for VG2.1.

**Files:** `viterbi/costs.py`, `viterbi/corridors.py`, `builder/bass_viterbi.py`,
`viterbi/pathfinder.py`, `workflow/result.md`.

## VG3 — Unified generate_voice() (2026-02-13)

Created `viterbi/generate.py` with voice-agnostic `generate_voice()` function
that both soprano and bass now use. Completes BV1 API migration: soprano_writer
and bass_viterbi converted from `LeaderNote` to `ExistingVoice`. Extracted
common solver+note-conversion logic (~40 lines) from both voice generators into
single unified function. Both voices now follow identical generation pathway:
structural_knots → rhythm_grid → existing_voices → generate_voice → Notes.
Voice-specific logic (knot placement, rhythm, voice construction) remains in
callers. All 8 genres verified working.
