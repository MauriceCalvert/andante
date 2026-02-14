# Completed

## TD-2 — CADENCE-Only Phrases Fall Through to Galant Path (2026-02-14)

`write_phrase()` in `builder/phrase_writer.py` routed CADENCE-only phrases into `_write_thematic_phrase`, which filtered them out (only keeps SUBJECT/ANSWER/CS). Bars 17–24 (confirmatio + peroratio) were silent — no final cadence.

**Fix:** Changed `has_thematic` check from `role.role != ThematicRole.FREE` to explicit membership test for SUBJECT, ANSWER, CS, EPISODE. CADENCE-only and FREE-only phrases now fall through to the galant/cadence_writer path.

**Result:** Invention now renders 23 bars with final PAC (soprano 4→3→2→1, bass 5→1 in C major). All 4 sections present. Gavotte unchanged.

## TD-1 — Entry Sequence Parser + Declarative Planner (2026-02-14)

Replaced algorithmic thematic planner with declarative entry sequence read from genre YAML. Every thematic entry is now data-driven — who plays what material, in which key, in what order. The planner walks the list top to bottom and stamps bars. No heuristics, no voice-alternation bugs, no coverage shortfalls.

**Changes (1 new file, 5 modified files):**
- `data/genres/invention.yaml`: Added entry_sequence to thematic section (7 entries: 6 subject/answer/CS entries + cadence marker). Removed old fields: exposition, stretto, pedal, episode_derivation. Kept voice_count and invertible_counterpoint.
- `planner/thematic.py`: Rewrote plan_thematic_roles() with _place_entry_sequence(). Deleted _place_subject_entries() and _place_episodes(). Added thematic_config and subject_bars parameters. Walks entry_sequence top to bottom, stamping bars with SUBJECT/ANSWER/CS roles based on voice slot specifications. Handles "none" slots (leaves FREE). Skips stretto entries (TD-3). Maps material names to ThematicRole enum.
- `builder/imitation.py`: Added answer_to_voice_notes(fugue, start_offset, target_track, target_range). Uses fugue.answer_midi() with no tonic_midi override (defaults to fugue.tonic_midi). Octave-shifts into target_range. Analogous to subject_to_voice_notes() but for answer material.
- `builder/thematic_renderer.py`: Updated render_thematic_beat() to call answer_to_voice_notes() for ANSWER role instead of subject_to_voice_notes(). EPISODE role now returns None (deferred to TD-2). Added answer_to_voice_notes import.
- `planner/planner.py`: Passes thematic_config dict and subject_bars (from fugue.subject.bars) to plan_thematic_roles() at line 192-200.
- `scripts/yaml_validator.py`: Added validate_thematic_entry_sequence() function. Validates entry_sequence structure: each entry is "cadence" or dict with upper/lower keys. Voice slots are "none" or [material, key_label]. Valid materials: subject, answer, cs, stretto. Valid key labels: I, V, IV, vi, iii, ii, III, VI.

**Musical effect:** Monophonic opening (soprano alone bars 1-2, bass silent). Answer enters bass bar 3 in dominant key. Subject/CS entries alternate voices across 4 different keys (I, V, vi, IV). Thematic coverage 96.2% (200/208 beat-roles assigned, only 8 FREE). Far exceeds 50% minimum.

**Checkpoint (Bob+Chaz):** All 9 acceptance criteria PASSED. Monophonic opening structurally correct (bass silent bars 1-2). Answer audible in bass bars 3-4. Subject appears in both voices (upper bars 1-2,5-6,9-10; lower bars 7-8,11-12). CS in complementary voice for all non-monophonic entries. 4 keys used. Pipeline completes without error for invention. Gavotte (galant genre without entry_sequence) unchanged. No stretto rendered (deferred to TD-3).

**Issue noted (non-blocking):** Builder renders BOTH thematic material AND schema material for same beat, creating double notes in bars 1-2 (e.g., offset 0.0 has both B4 from thematic and G4 from schema). Thematic notes should REPLACE schema notes, not overlay. Planner is correct (assigns roles correctly), builder composition assembly needs priority logic. Will be addressed in TD-2 when full thematic/schema/Viterbi pipeline is unified.

**Acceptance criteria: 9/9 PASS.** Ready for TD-2: Episode Insertion.

## TP-B2 — Episode Rendering with Fragment Catalogue (2026-02-14)

Implemented episode rendering for invention genre. Episodes now fill non-cadential all-FREE schemas with the subject's head fragment sequenced through descending scale degrees. Thematic coverage increased from 65% to 75%.

**Changes (2 new files, 3 modified):**
- NEW `motifs/fragment_catalogue.py`: Fragment dataclass, extract_head(fugue, bar_length), extract_tail(fugue, bar_length)
- NEW `planner/thematic.py:_place_episodes()`: walks schemas after subject entries, marks non-cadential all-FREE schemas as EPISODE with fragment_iteration per bar
- `builder/thematic_renderer.py:_render_episode_fragment()`: extracts head fragment, transposes down by fragment_iteration diatonic steps, converts to MIDI in material_key, octave-shifts into target_range
- `builder/phrase_writer.py:_write_episode_phrase()`: detects EPISODE roles, renders each bar's fragment separately, generates Viterbi fill for FREE voice
- `planner/thematic.py:plan_thematic_roles()`: calls _place_episodes() after _place_subject_entries()

**Musical effect:** Episode bars (prinner bars 4-7, passo_indietro bars 22-23) now contain recognizable head fragment (G-E-C descending call) stepped down bar-by-bar. Thematic coverage: 75% (144/192 beats) = SUBJECT 50% + CS 12.5% + EPISODE 12.5%. Episodes create directed harmonic motion via sequential descent. Free voice (soprano when episode in bass) gets Viterbi fill with existing counterpoint constraints.

**Checkpoint (Bob+Chaz):** Head fragment audible in episode bars (Bob hears "the opening call's shape in the bass" at bars 4-7, 22-23). Fragment steps down G3→F3→E3 correctly (bars 4-6), but bar 7 octave-shifts to D4 instead of continuing to D3, breaking contour. Episode voice alternation broken: section 4 has bass subject (bars 18-20) then bass episode (bars 22-23) — same voice twice, not dialogue. All 8 genres run without error. Cadence bars unchanged.

**Acceptance criteria:**
- Head fragment recognizable: ✓ PASS
- Fragment steps down in pitch: ⚠ PARTIAL (G→F→E descends, D4 breaks)
- Episode voice opposite of preceding subject: ✗ FAIL (same voice in section 4)
- Thematic coverage >85%: ✗ FAIL (75% vs. 85% target)
- FREE voice counterpoint aware: ✓ PASS
- Pipeline completes all genres: ✓ PASS
- Cadence bars unchanged: ✓ PASS

**Known issues:**
1. Voice alternation: `_place_episodes()` uses first subject voice per section instead of most recent subject voice globally; sections with multiple subject entries assign episode to wrong voice
2. Octave discontinuity: bar 7 episode jumps to D4 instead of D3; degree transposition or octave-shift logic needs verification
3. Below coverage target: 75% vs. 85%; need more episode schemas or adjust min_non_cadential per section

**Next:** Fix voice alternation (track last_subject_voice globally), debug octave-shift contour, adjust genre YAML to increase episode density.

## TP-B1 — Subject + CS Placement and Thematic Renderer (2026-02-14)

Implemented beat-level thematic planner and renderer for invention subject/CS entries. Replaced phrase-level imitation dispatch with beat-granular thematic roles that span freely across bar lines.

**Changes (3 new files, 2 modified):**
- NEW `builder/thematic_renderer.py`: render_thematic_beat() converts BeatRole → Notes using imitation.py transposition functions
- NEW thematic placement in `planner/thematic.py:_place_subject_entries()`: walks sections, marks first non-cadential schema beats as SUBJECT/CS with invertible counterpoint alternation
- `builder/phrase_writer.py:_write_thematic_phrase()`: new dispatch path checks plan.thematic_roles, renders subject/CS via thematic_renderer, handles tail bars with existing generators
- `planner/planner.py:197`: passes schema_chain, schemas, genre_config to plan_thematic_roles
- Old dispatch code (_write_subject_phrase, _write_answer_phrase) preserved but bypassed

**Musical effect:** Subject entries now placed by planner (Layer 4b) rather than imitation_role field. Thematic coverage: 65.2% of beats (vs. previous ~0% for non-subject bars). Invertible counterpoint implemented: entry_count alternates subject/CS voices across sections. Subject adapts tonally to local keys (C major → A minor narratio).

**Checkpoint (Bob+Chaz):** Subject entries audible at section boundaries with call_response contour (descending call + rushing sixteenth response). CS present in complementary voice. Both rendered by thematic_renderer via existing imitation.py. FREE beats (34.8%) fall through to Viterbi as expected. Old dispatch bypassed but not deleted (TP-B2 confirmation). Known limitation: subject lyrics set in code but not appearing in .note export (CS/episode lyrics do appear; likely downstream export filtering).

**Acceptance criteria met:** Subject entries recognizable ✓ | CS in complementary voice ✓ | Invertible counterpoint alternation ✓ | Non-subject bars unchanged ✓ | Pipeline completes ✓

**Next:** TP-B2 (episode rendering with fragment catalogue, head/tail extraction).


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

## 2026-02-14 TD-1f — Multi-Entry Thematic Phrase Rendering

**Problem:** `_write_thematic_phrase` was written for TP-B1 (one entry per phrase) and failed for TD-1 multi-entry phrases:
1. Only handled SUBJECT + CS roles (skipped ANSWER)
2. Rendered everything at plan.start_offset (entries crammed at bar 1)
3. Did not handle monophonic entries (FREE voice not silent)

**Solution:**
- Added `_segment_into_entries()` to detect entry boundaries from BeatRoles
- Rewrote `_write_thematic_phrase` to iterate by entry:
  - Each entry renders SUBJECT/ANSWER/CS at its actual bar offset
  - Monophonic entries handled (FREE voice = silence or padding)
  - Entry-to-entry padding and tail generation via Viterbi
- Modified `_stamp_lyrics()` in compose.py to preserve thematic lyrics

**Files:** builder/phrase_writer.py, builder/compose.py

**Result:** All 7 acceptance criteria met. Monophonic opening (bars 1-2) renders correctly, answer enters at bar 3, all entries at correct offsets. Galant genres unchanged.

## 2026-02-14 — TD-3: Thematic Dispatcher Rewrite

Eliminated double notes by replacing dual dispatch (imitation_role + thematic_roles) with unified three-way dispatcher:
- Cadential: fixed templates from cadence writer
- Thematic: subject/answer/CS/episode/stretto from thematic renderer with time-window contract
- Schematic: galant order (structural soprano → bass → soprano)

**Implementation:**
1. Added end_offset parameter to render_thematic_beat (time-window contract: drop/truncate notes outside window)
2. Rewrote _write_thematic_phrase → _write_thematic with unified entry loop handling all roles (SUBJECT, ANSWER, CS, EPISODE)
3. Extracted _write_schematic from galant else-block
4. Rewrote write_phrase as three-way dispatcher with _has_material helper + _write_cadential wrapper
5. Deleted all legacy code:
   - phrase_writer.py: _clip_to_phrase, _write_subject_phrase, _write_answer_phrase, _write_stretto_phrase, _write_episode_phrase
   - compose.py: _clip_notes function + all calls
   - phrase_planner.py: _assign_imitation_roles function + call
   - phrase_types.py: imitation_role field from PhrasePlan
6. Verified: invention/gavotte/minuet run clean; all 8 genres pass run_tests

**Verification:**
- Zero doubled notes (awk scan confirms no duplicate offset+track pairs)
- Monophonic opening in invention bars 1-2 (soprano only, zero bass notes)
- All 8 genres run without error (bourree, chorale, fantasia, gavotte, invention, minuet, sarabande, trio_sonata)
- Legacy code deleted (grep confirms zero hits for all 8 deleted items)
- write_phrase dispatches to exactly one path per phrase (no fallthrough, no overlap)

