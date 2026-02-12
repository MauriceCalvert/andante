# Completed

## Phase 16b — Shared Foundation Modules (2026-02-11)

**What was implemented:**
1. Extended `shared/counterpoint.py` with detection functions:
   - `has_parallel_perfect`: Detects P5→P5/P8→P8 by similar motion at common onsets
   - `would_cross_voice`: Returns True if pitch crosses another voice based on voice_id hierarchy
   - `is_ugly_melodic_interval`: Detects augmented 2nd, tritone, major/minor 7th (matches faults._check_ugly_leaps)
   - `needs_step_recovery`: Returns True if last interval was leap without contrary stepwise recovery
   - `is_cross_bar_repetition`: Detects pitch repetition across bar boundary at non-structural offsets
   - `has_consecutive_leaps`: Detects two leaps > SKIP_SEMITONES in same direction
2. Added prevention helper to `shared/counterpoint.py`:
   - `find_non_parallel_pitch`: Suggests diatonic/octave alternatives to avoid parallel perfects
3. Created `shared/phrase_position.py`:
   - `phrase_zone`: Classifies bar position as "opening"/"middle"/"cadential" (1, 2, 4, 8-bar phrases tested)
4. Created `shared/pitch_selection.py`:
   - `select_best_pitch`: Placeholder with constraint relaxation priority table documented (implementation deferred to Phase 16c+)
5. Created comprehensive test coverage:
   - `tests/shared/test_counterpoint_extended.py`: 32 tests (all passing)
   - `tests/shared/test_phrase_position.py`: 7 tests (all passing)

**Logic verification (Chaz):**
- `has_parallel_perfect` matches faults._check_parallel_perfect (lines 518-560): simple interval mod 12, PERFECT_INTERVALS check, tolerance subtraction, similar motion, common-onset-only
- `is_ugly_melodic_interval` matches faults._check_ugly_leaps (lines 435-468): `interval % 12 in UGLY_INTERVALS and interval > STEP_SEMITONES`
- `has_consecutive_leaps` matches faults._check_consecutive_leaps (lines 147-174): both > threshold, same direction check, None guard
- All functions use constants from shared/constants.py (PERFECT_INTERVALS, UGLY_INTERVALS, SKIP_SEMITONES, STEP_SEMITONES) — single source of truth (L017)

**Musical impact:**
- Zero change in pipeline output (3728 pre-existing tests pass with identical results: 3767 total passed including 39 new tests, 204 skipped, 16 xfailed)
- No new imports added to bass_writer.py or soprano_writer.py
- All functions are pure utilities for future phases (16c onwards)
- Test-only phase — no generation logic touched

**Files created:**
- `shared/phrase_position.py`
- `shared/pitch_selection.py`
- `tests/shared/test_counterpoint_extended.py`
- `tests/shared/test_phrase_position.py`

**Files modified:**
- `shared/counterpoint.py` (added 7 functions + 1 prevention helper)

**Acceptance criteria:**
✅ All pre-existing tests pass unchanged (3728 passed, 16 xfailed)
✅ All new tests pass (39 tests)
✅ New detection functions match faults.py logic exactly
✅ select_best_pitch exists as placeholder with correct signature and docstring
✅ phrase_zone returns correct classification for 1, 2, 4, 8-bar phrases
✅ No pipeline code modified
✅ No new imports in bass_writer.py or soprano_writer.py

**Next:** Phase 16c will create voice writer types (VoiceConfig, VoiceContext, SpanBoundary, etc.) that consume these shared functions.

## Phase 14 — Character Floor + Voice-Leading Clamp (2026-02-10)

**What changed:**
1. Added CHARACTER_RANK dict to shared/constants.py for character priority comparison
2. Modified builder/phrase_planner.py to implement character floor: section character from genre YAML acts as minimum, tension curve can elevate but never downgrade
3. Modified builder/figuration/soprano.py `_realise_pitches` to use voice-leading-aware octave selection via new `_nearest_in_range` helper, removed `_clamp_to_range`

**Musical impact:**
- invention_a_minor: interval-14 fault ELIMINATED (was failing with "Melodic interval 14 exceeds octave at offset 27/2")
- sarabande_a_minor: leap-step fault ELIMINATED (was failing with "Leap of 10 at offset 33/4 not followed by step")
- All 16 test cases (8 genres × 2 keys) now pass with zero faults
- Zero new faults introduced

**Open complaints:**
- Semiquavers (1/16 notes) not appearing in invention output despite narratio section having character="energetic" in YAML. Character floor logic is correctly implemented, but semiquavers not being generated. Requires investigation of tension curve values or rhythm template selection. This is tangential to Phase 14b's core goal (fixing voice-leading leaps), which succeeded.

## 2026-02-10: Phase 13 — Re-enable Algorithmic Generator + Fix Semiquaver Density

### What was implemented
1. **Algorithmic generator re-enabled** (`builder/figuration/selection.py:111`): Changed `if False` to `if True`, removing outdated comment block about minor key handling
2. **Density parameter threading** (`builder/figuration/soprano.py:137,176,80`): Added `density: str` parameter to `_get_durations()`, replaced hardcoded `density="medium"` in fallback path with parameter value, updated call site to pass density from `_character_to_density()`

### What works
- **Generator active**: All passing genres log padding warnings (generator producing short degree sequences for small intervals, then padding to target count)
- **Zero new faults**: All test failures (invention A minor, sarabande A minor) are pre-existing — verified by testing with both changes reverted
- **Major key genres pass**: Invention C (73 notes), gavotte C/Am (59 notes each), minuet C (42 notes), sarabande C (43 notes), bourree C (47 notes) all complete successfully

### What doesn't work
- **Acceptance criterion #1 FAIL**: Invention C major contains NO semiquaver (1/16) notes — only 1/4, 1/8, 1/2, and 1 durations
- **Root cause**: Density parameter flows correctly, but invention phrases have character "plain" or "expressive" (not "ornate"/"bold"/"energetic"), so `_character_to_density()` returns "low" or "medium", mapping to 1/4 or 1/8 units per `DENSITY_RHYTHMIC_UNIT`
- **Architectural analysis**: The density change is *architecturally correct* (parameter flows through as designed) but *musically inert* (input value never triggers high-density code path). The task specification's expectation that these changes would produce semiquaver passages is incorrect — requires upstream change to character assignment in genre YAML or phrase planner

### Pre-existing faults documented
- **Invention A minor**: "Melodic interval 14 exceeds octave at offset 27/2" — occurs with generator both enabled AND disabled, proving pre-existence
- **Sarabande A minor**: "Leap of 10 at offset 33/4 not followed by step (got 3)" — task specification acknowledges this as pre-existing
- **Root cause of both**: `_realise_pitches` in `soprano.py:207-208` calls `_clamp_to_range()` which transposes pitches by octave without considering melodic interval to previous pitch. If pitch N is clamped up by 12 semitones but pitch N+1 doesn't need clamping, a large leap results. Fix (out of scope): `_clamp_to_range` must be leap-aware

### Task specification flaws
1. Lists invention A minor as expected to pass, but it was already failing before Phase 13
2. Expects semiquaver passages from enabling generator + density threading, but these changes don't address character assignment (the actual blocker)
3. Says generator is "correct as written" but generator produces 2-degree sequences for step intervals with high note counts, requiring extensive padding that can create leap violations

### Files modified
- `builder/figuration/selection.py`: Line 111, changed `if False:` to `if True:` (2 characters)
- `builder/figuration/soprano.py`: Lines 137, 176, 80 — added `density` parameter, replaced hardcoded "medium", updated call site (3 locations)

### Verification
- 8 test runs with generator enabled
- Baseline verification: 2 test runs with both changes reverted (proved failures pre-existing)
- Zero new faults introduced by Phase 13 changes

### Open issues
1. Semiquaver density not achieved (requires character elevation in upstream)
2. Invention A minor and sarabande A minor leap violations (pre-existing, requires leap-aware clamping)
3. Generator padding warnings (expected for small-interval/high-count spans, but acceptable per task specification)

### Recommendation
Accept Phase 13 implementation as complete per specification. Reject acceptance criterion #1 as unmet, but note specification is flawed. If semiquaver passages required, issue follow-up phase to modify genre YAML section character assignments or add phrase planner logic to elevate character for invention narratio/confirmatio sections.

See `workflow/result.md` for full Bob/Chaz evaluation with proper boundary separation.

## 2026-02-10: Phase 12 — Algorithmic Figuration (Partial)

### What was implemented
1. **Algorithmic figuration generator** (`builder/figuration/generator.py`): Pure deterministic function generating degree sequences by interval class (unison → turn/mordent, steps → circolo, thirds → stepwise fill, fourths/fifths → arpeggiation, sixths+ → tirata)
2. **Chord tones threading**: Added `_implied_chord_tones` helper in `soprano_writer.py`, flows bass degrees → triad offsets through `figurate_soprano_span` → `select_figure` → `generate_degrees`
3. **Soprano register floor**: Soft floor at `biased_upper_median - 5` (soprano_writer.py:210-214) prevents downward drift, octave-up correction when pitch falls >4th below median
4. **Selection priority**: Algorithmic generation inserted after high-weight YAML matches (selection.py), before fallback padding

### What works
- **Register floor**: Gavotte soprano stays in G4-C5 range, no drift to E4-D4 (criterion #2 PASS)
- **Chord tones threading**: Parameter correctly computed and passed through pipeline
- **Major key genres**: Minuet, gavotte, invention in C major all run without faults
- **No mechanical oscillation**: YAML figures provide varied patterns, no extended [+1,0,-1,0] padding detected in tested outputs

### What doesn't work
- **Algorithmic generator DISABLED**: Creates leap-then-step violations in minor keys. Generator produces diatonic degree offsets assuming natural scale, but minor keys use raised 6/7 (melodic minor). Diatonic "stepwise" sequences create unexpected chromatic leaps. Sarabande A minor fails with "Leap of 10 at offset X not followed by step" across multiple seeds. Generator disabled at selection.py:104 (`if False`) until fixed.
- **No semiquaver passages**: Invention output shows only quaver density (criterion #3 FAIL). Either rhythm cells not requesting 16-note counts, or high-density YAML figures missing, or generator would have provided them but is disabled.
- **Chord tones unused**: Parameter threaded correctly but generator disabled, so no effect on output

### Root cause of minor key failure
Generator works in diatonic space (degree offsets 0, ±1, ±2, ...) but `key.diatonic_step()` realizes these in the key's scale with chromatic alterations. In A minor melodic, degrees 6-7-1 are F-G#-A. A "stepwise" diatonic fill that samples or skips degrees produces chromatic leaps. The leap-then-step postcondition (soprano_writer.py:87-96) detects and fails.

### Fix needed
Generator must either:
1. Know about chromatic alterations and avoid leap-producing sequences (requires key mode awareness)
2. Work in chromatic space instead of diatonic space (breaks schema degree model)
3. Add post-generation validation/smoothing pass before finalization (fix at realization, not generation — violates D008)

Option 1 preferred: generator receives `is_minor` flag, uses conservative patterns (pure stepwise, no sampling, no decorations) for minor keys until chromatic-aware logic added.

### Files modified
- **NEW**: `builder/figuration/generator.py` (442 lines, algorithmic degree generation)
- `builder/figuration/selection.py`: Import generator, call after high-weight YAML match check (currently disabled)
- `builder/figuration/soprano.py`: Add `chord_tones` parameter to `figurate_soprano_span`, pass to `select_figure`
- `builder/soprano_writer.py`: Add `_implied_chord_tones` helper, compute and pass chord_tones in figuration loop, add register floor check after `degree_to_nearest_midi`

### Checkpoint results
- Minuet C: 49 soprano notes, varied melodic content, no oscillation
- Gavotte C: 59 soprano notes, tessitura G4-C6, section A stays above A4 (register floor working)
- Invention C: 75 soprano notes, continuous quaver motion, no semiquavers
- Sarabande Am: FAILS with leap violation (pre-existing issue, happens even with generator disabled)

### Open issues
1. Re-enable algorithmic generator after minor key fix
2. Investigate why no semiquaver passages (rhythm cells? YAML figures? generator disabled?)
3. Test padding reduction once generator active (cannot verify with generator disabled)

See `workflow/result.md` for full Bob/Chaz evaluation.

## Phase 11: Small Fixes Batch (11a + 11b + 11c) (2026-02-10)

### Changes
- **11a: Invention exordium min_non_cadential constraint**
  - `data/genres/invention.yaml:35`: Added `min_non_cadential: 2` to exordium section
  - `planner/schematic.py:234-283`: Added enforcement loop in `_generate_section_schemas` that reads `min_non_cadential` from genre section YAML and inserts additional continuation schemas until the minimum non-cadential count is met
  - `scripts/yaml_validator.py:1108-1112`: Added `min_non_cadential` to `VALID_GENRE_SECTION_KEYS`

- **11b: Parallel octave in gavotte bar 19.1**
  - `builder/bass_writer.py:951-1023`: Walking bass parallel prevention enhanced with:
    1. Widened alternatives (lines 963-984): For non-structural tones, `pp_candidates` now includes diatonic ±1, ±2, and octave shifts (previously only ±1)
    2. Lookahead check (lines 985-1023): Checks whether the NEXT soprano note forms parallel perfects with current bass pitch, catching non-simultaneous but adjacent parallel octaves

- **11c: Sarabande beat-2 weight**
  - `data/rhythm_cells/cells.yaml:63-88`: Added four sarabande-specific cells with beat-2 accent:
    - `sarabande_crotchet_minim` (1/4 + 1/2, accent [true, true])
    - `sarabande_three_crotchets` (three quarters, accent [true, true, false])
    - `sarabande_dotted_crotchet_quaver_crotchet` (dotted figure, accent [true, true, false])
    - `sarabande_minim_crotchet` (cadential, accent [true, false])
  - `data/rhythm_cells/cells.yaml:8-48`: Removed `sarabande` from shared 3/4 cell genre_tags

### Verification
- 8 pipeline runs (invention C/Am, minuet C, gavotte C/Am, sarabande C/Am, bourree C)
- Bob assessment:
  - Both inventions show proper two-voice exposition with subject and answer before any cadence (exordium runs 7 bars with answer entry at bar 4)
  - Gavotte bar 18-19 shows oblique motion instead of parallel octaves; no new parallel perfects detected in any genre
  - Sarabande rhythm emphasizes beat 2 with 1/4+1/2 pattern (57% of non-cadential bars), distinct from minuet
  - No new faults detected in any genre
- Chaz diagnosis: All three fixes are minimal, targeted, and preserve existing counterpoint systems

### Musical Impact
Before: A minor invention exordium could have only 1 non-cadential phrase, truncating exposition to subject-only without answer. Gavotte had parallel octaves at bar 19.1. Sarabande and minuet used identical rhythm cells.
After: Invention exordium guarantees room for subject+answer before cadence. Parallel octave prevention includes lookahead checking and wider alternative search. Sarabande has distinct beat-2 emphasis rhythm, separate from minuet.

## Phase 10: Cross-Relation Prevention in Soprano Writer (2026-02-10)

### Changes
- Created `shared/counterpoint.py` with two functions: `has_cross_relation()`
  and `prevent_cross_relation()`. Extracted from bass_writer.py local functions,
  generalized parameter names (soprano_notes→other_notes, bass_range→pitch_range,
  soprano_ceiling→ceiling) for voice-neutral usage. L017: single source of truth.
- `builder/bass_writer.py`: Removed local `_has_cross_relation` and
  `_prevent_cross_relation` functions. Import from `shared.counterpoint`.
  Updated 5 call sites to use new parameter names.
- `builder/soprano_writer.py`: Added `lower_notes: tuple[Note, ...] = ()`
  parameter to `generate_soprano_phrase()`. Added imports for cross-relation
  functions and logging. Added `check_cross_relations: bool = len(lower_notes) > 0`
  guard (line 141). Added diagnostic warning for structural tones that cross-relate
  (lines 315-326, logged but not altered). Added `prevent_cross_relation` filter
  as final pitch filter before range assert for non-structural pitches (lines 452-463).
- `builder/phrase_writer.py`: Pass `lower_notes=bass_subject` in
  `_write_subject_phrase()` when `lead_voice == 1` (line 131). Pass
  `lower_notes=bass_answer` in `_write_answer_phrase()` when `lead_voice == 0`,
  tail generation (lines 222-224).

### Verification
- 5 pipeline runs (invention C/Am, minuet C, gavotte C, sarabande Am).
- Bob assessment: Zero cross-relations detected in invention A minor and C major.
  Soprano lines in invention bars 5-8 (where bass is pre-composed) sound smooth,
  idiomatic, not avoidant. Counterpoint reads as dialogue between independent voices.
  Non-invention genres (minuet, gavotte, sarabande) generated successfully with
  no behavioral change (lower_notes empty, filter bypassed).
- Chaz diagnosis: Cross-relation prevention now active when bass is pre-composed
  (invention flows). Filter runs as last pitch filter before range assert for all
  non-structural pitches when `check_cross_relations` is True. Structural tones
  logged if cross-relate but not altered (planning-layer issue). Normal galant
  flow (soprano-first) unaffected: `check_cross_relations` guard only activates
  when `len(lower_notes) > 0`. All implementation requirements verified.
- All acceptance criteria met: zero cross-relations, zero new faults, non-invention
  genres unchanged, bass_writer.py has no local cross-relation logic (L017 enforced).

### Musical Impact
Before: When bass was pre-composed (invention subject/answer entries), soprano
generated blind to bass chromatic alterations, producing cross-relations (same
letter-name chromatically altered between voices within a beat, e.g., F4 in
soprano against F#3 in bass). This is a jarring fault in baroque counterpoint.
After: Soprano checks against bass notes before committing a pitch, mirroring
the check bass already performs. The fix is inaudible — it prevents a fault
without adding a feature. Voices now share a chromatic vocabulary, as Principle 2
requires (voices relate to each other, the relationship is the point).

## Phase 9.2: Denser soprano figuration over walking bass (2026-02-10)

### Changes
- `builder/rhythm_cells.py`: Renamed parameter `soprano_onsets` → `avoid_onsets`
  in `_onset_overlap()` and `select_cell()` for direction-neutrality. Updated
  docstring to reflect that this parameter is used for rhythmic independence
  between any two voices (bass avoiding soprano, or soprano avoiding bass).
- `builder/bass_writer.py`: Updated two `select_cell()` call sites (lines 641, 747)
  to use `avoid_onsets=soprano_onsets_per_bar.get(bar_num)` instead of old
  parameter name.
- `builder/soprano_writer.py`: Added computation of `bass_avoid_onsets` when
  `plan.bass_texture == "walking"` (lines 137-142). Generates frozenset of
  bar-relative onsets at each beat (quarters for 4/4, etc.). Pass
  `avoid_onsets=bass_avoid_onsets` to `select_cell()` (line 276). When
  bass texture is not walking, pass `avoid_onsets=None` (existing behavior).

### Verification
- 10 pipeline runs (minuet, gavotte, bourree, sarabande, invention x C/Am).
- Bob assessment: Soprano in walking-bass genres (gavotte, invention, bourree)
  now uses mixed quarter-eighth rhythm cells instead of lockstep quarters.
  Onset overlap reduced from ~100% (pre-Phase 9.2) to ~25-40% of non-downbeat
  positions. Cadential bars still appropriately sparse. No frenetic motion.
- Chaz diagnosis: Bass uses rhythm cells (not pure even quarters), so soprano
  avoidance is a heuristic. Acceptable — acceptance criteria "< 50% overlap" met.
- All acceptance criteria passed: zero new faults, walking-bass genres < 50%
  shared non-downbeat onsets, minuet/sarabande unchanged, no frenetic motion.

### Musical Impact
Before: Soprano and bass in walking-bass genres used identical rhythm (lockstep
quarters), creating "march" texture (Principle 6 violation).
After: Soprano selects cells with fewer onset overlaps, producing rhythmic
independence. Gavotte/invention/bourree now have two-voice dialogue instead of
single-rhythm texture.

## Phase 9.1: Fix repeated-pitch fallback in soprano writer (2026-02-10)

### Changes
- `builder/soprano_writer.py`: Replaced bar-parity direction logic in the
  post-structural-tone fallback with neighbour-tone oscillation cycle
  `[+1, 0, -1, 0]`. Added `neighbour_cycle` (int) and `neighbour_anchor`
  (int|None) state variables at phrase level. The cycle direction swaps
  when `next_entry_midi < neighbour_anchor`. Range checking tries all 4
  cycle positions before falling back to anchor pitch.
- `builder/figuration/soprano.py`: Replaced static `last_deg` padding in
  `_fit_degrees_to_count` with alternating neighbour pattern `[1, 0, -1, 0]`.
  Added logger warning when padding exceeds 4 notes. Added `import logging`
  and module-level logger.

### Verification
- 10 pipeline runs (minuet, gavotte, bourree, sarabande, invention x C major, A minor).
- Zero instances of 3+ consecutive identical soprano MIDI pitches (automated scan).
- 31 instances of 2-note repeats across 532 soprano notes (structural tone boundaries).
- No assertion failures or new faults.
- Padding warnings fired for gavottes and bourrees (figures with 2 degrees
  padded to 8 — figuration selection issue for future phases).

### Open Issues
- Low soprano register in gavottes (E4-D4 area, bars 3-5) — registration issue
- Whole-note held structural tones (gavotte bar 18) — single structural tone
  spanning full bar, no figured content to subdivide
- Rhythmic uniformity in dance genres (mostly quarter notes) — Phase 9.2

## Phase I4e+I7: Re-enable CS in answer phrase + episode assignment (2026-02-10)

### Changes
- `builder/imitation.py`: Added `countersubject_to_voice_notes()` — places CS in
  any voice/key/range following `subject_to_voice_notes` pattern. Computes
  tonic_midi from target_key, gets MIDI via countersubject_midi, octave-shifts.
- `builder/phrase_writer.py`: `_write_answer_phrase` lead_voice==0 branch now
  places CS in soprano via `countersubject_to_voice_notes` at tonic key (not
  dominant). Handles tail generation if CS < phrase duration. First CS note
  labelled lyric="cs".
- `builder/phrase_planner.py`: `_assign_imitation_roles` gates answer assignment
  with `sec_idx == 0`. Only the exordium gets both subject + answer. Later
  sections get one subject entry; remaining non-cadential phrases are episodes
  (imitation_role=None), falling through to normal galant pipeline.

### Verification
- C major invention: CS in exordium answer phrase (8 notes, matching subject
  rhythm). All strong-beat intervals consonant (M6/m6). Episodes in narratio.
- A minor invention: No answer phrase (exordium has 1 non-cadential phrase).
  Episodes present in later sections.
- Minuet: 0 faults, unchanged.

### Open Issues
- A minor exordium too short for answer+CS (schema chain issue, not builder)
- Cross-relation risk persists (soprano unaware of chromatic bass alterations)

## Phase I5c+I6: Verify tail fix and audit episodes (2026-02-10)

### Audit (no code changes)
- Regenerated C major and A minor inventions (seed 42) + minuet regression check.
- C major: 0 faults, 70 soprano + 64 bass notes.
- A minor: 1 fault (cross-relation bar 5.1: F4 vs F#3), 70 soprano + 64 bass notes.
- Minuet: 0 faults. No regression.

### Findings
1. **Tail bar repeated pitch persists:** do_re_mi bar 3 and romanesca bar 16
   both show 3x repeated pitch in both keys. Root cause: soprano_writer
   end-of-phrase filling when one structural degree exists with no next target.
   The make_tail_plan I5c injection codepath is NOT triggered (tails have
   degrees in range). Issue is in soprano_writer, not make_tail_plan.
2. **Zero episode phrases:** _assign_imitation_roles assigns subject/answer to
   ALL non-cadential phrases with lead_voice. No free counterpoint between
   entries. Invention is wall-to-wall thematic statements + cadences.
3. **Cross-relation (A minor):** Pre-existing. Soprano unaware of answer bass.

### Open Issues
- Soprano writer end-of-phrase repeated pitch (bars 3, 16)
- Need episode phrases for invention genre
- Soprano-bass awareness for cross-relation avoidance

## Phase I5b: Subject tail generation (2026-02-10)

### Changes
- `builder/phrase_types.py`: Added `make_tail_plan()` -- builds a PhrasePlan for
  bars after a subject entry. Filters degrees/positions to tail range, remaps bars.
- `builder/phrase_writer.py`: Replaced `_extend_to_fill` with tail generation.
  Subject/answer phrases now generate schema-based continuation after the subject
  ends, instead of holding the last note. Added `_pad_to_offset` for subject-to-tail
  boundary alignment.
- Both `_write_subject_phrase` and `_write_answer_phrase` handle all cases:
  soprano-leads, bass-leads, monophonic opening, with and without tails.

### Verification
- C major invention: 0 faults, 2 of 4 entries have tails, no held notes > 1 bar.
- A minor invention: 0 faults, 2 of 4 entries have tails, no held notes > 1 bar.
- Minuet: 0 faults, unchanged.

### Known Limitations
- Tail bars with no schema degrees produce static pitch (soprano writer fallback).
- Soprano unaware of pre-composed bass (pre-existing).

## Phase I5: Voice swap + key transposition across sections (2026-02-10)

### Changes
- `builder/phrase_planner.py`: `_assign_imitation_roles` now assigns
  subject/answer roles in ALL sections, not just exordium.
- `builder/imitation.py`: Added `subject_to_voice_notes()` — transposes
  subject to any key/voice/range via tonic_midi computation + octave shift.
- `builder/phrase_writer.py`: Rewrote `_write_subject_phrase` and
  `_write_answer_phrase` to dispatch on `lead_voice`. lead_voice=0:
  soprano leads; lead_voice=1: bass leads. Non-leading voice generates.

### Verification
- C major: 5 subject entries across 4 sections, 3 keys (C, G, F). 1 fault.
- A minor: 4 entries across 4 sections. 1 fault.
- Minuet: 0 faults, unchanged.

### Open
- Extended last note when subject < phrase duration (4+ bars held).
- Soprano unaware of pre-composed bass (occasional parallel octaves).
- A minor exordium has no answer (only 1 non-cadential phrase).

## Phase I4d: Invertible countersubject — dual validation (2026-02-10)

### Changes
- `motifs/countersubject_generator.py`: Added `answer_degrees` parameter to
  `generate_countersubject()`. When provided, creates parallel CP-SAT variables
  for CS-vs-answer intervals (answer_imod7), adds hard consonance constraints
  on strong beats ({0, 2, 5}) and weak beats ({0, 1, 2, 4, 5, 6}), and adds
  soft penalty terms mirroring the subject penalties. Existing behaviour
  unchanged when answer_degrees is None.
- `motifs/subject_generator.py`: `generate_fugue_triple()` now passes
  `answer_degrees=answer.scale_indices` to `generate_countersubject()`.
- `motifs/countersubject_generator.py` `__main__`: Updated test to generate
  answers and pass answer_degrees for dual validation.

### Verification
- __main__ test: 5/5 subjects with dual validation (unchanged from subject-only).
- Invention C major pipeline: 0 faults, completed.
- Invention A minor pipeline: completed.
- Minuet C major: completed, no regression.

### Notes
- Pipeline used cached .fugue files; CS not yet wired into output. This phase
  adds the solver constraint. Wiring CS into the pipeline is a future phase.
- Solver found OPTIMAL for all 5 test seeds within timeout.

## Phase I4c: Fix tracks, restrict scope, drop pre-composed CS (2026-02-10)

### Changes
- `builder/imitation.py`: Removed `voice` parameter, use TRACK_SOPRANO/
  TRACK_BASS constants directly.
- `builder/phrase_planner.py`: `_assign_imitation_roles` restricted to
  first section (exordium) only.
- `builder/phrase_writer.py`: `_write_answer_phrase` generates soprano via
  `generate_soprano_phrase` instead of pre-composed CS.

### Verification
- Two tracks only (0 and 3). Subject stated once (exordium).
- Answer in bass with generated soprano above.
- Later sections use normal schema generation. Non-invention unchanged.

### Open
- Bass held long in answer phrase (answer < phrase length).
- Soprano writer unaware of fixed bass notes.

## Phase I4b: Answer entry + countersubject dispatch (2026-02-10)

### Changes
- `builder/imitation.py`: Added `answer_to_notes()` (octave-shift into
  bass range), `countersubject_to_notes()`.
- `builder/phrase_writer.py`: Dispatch on `imitation_role`. Extracted
  `_write_subject_phrase()`, added `_write_answer_phrase()`, shared
  `_extend_to_fill()`.

### Bugs found (fixed in I4c)
1. voice=1 in answer notes → 3 staves in MIDI.
2. imitation_role assigned to all sections → subject repeated 4 times.
3. Pre-composed CS dissonant against answer (CP-SAT validated against
   subject, not answer — intervals change when only one voice transposes).

## Phase I4a: Add imitation_role to PhrasePlan (2026-02-10)

### Changes
- `builder/phrase_types.py`: Added `imitation_role: str | None = None`.
- `builder/phrase_planner.py`: Added `_assign_imitation_roles()` — first
  non-cadential plan per section → "subject", second → "answer".

### Verification
- Correct roles per section. Cadential phrases None. Non-invention None.
- Zero audible change.

## Phase I3b: Subject-to-Notes + monophonic opening (2026-02-10)

### Changes
- New `builder/imitation.py`: `subject_to_notes()`, `subject_bar_count()`.
- `builder/phrase_writer.py`: Dispatch branch for monophonic subject entry
  (lead_voice set, fugue available, first phrase). Subject as soprano,
  empty bass. Last note extended to fill phrase.

### Verification
- Invention opens with subject (rhythmically varied, not schema figuration).
- Bass silent during subject. Minuet unchanged.
- Known limitation: last subject note held to fill phrase.

## Phase I3a: Thread fugue parameter to phrase writer (2026-02-10)

### Changes
- `planner/planner.py`: Pass `fugue` into `compose_phrases()`.
- `builder/compose.py`: Accept and forward `fugue` parameter.
- `builder/phrase_writer.py`: Accept `fugue` parameter (unused in logic).

### Verification
- Zero audible change. Pure plumbing.

## Phase I2: Wire lead_voice through PhrasePlan (2026-02-10)

### Changes
- `builder/phrase_types.py`: Added `lead_voice: int | None = None`.
- `builder/phrase_planner.py`: Added `_get_section_lead_voice()` helper,
  wired into `_build_single_plan()`.

### Verification
- Invention: lead_voice 0 or 1 per section. Minuet: all None.
- Zero audible change.

## Phase I1: Generate and cache FugueTriple (2026-02-10)

### Changes
- `motifs/fugue_loader.py`: Extracted `_parse_fugue_data(data)` helper.
  Added `load_fugue_path(path)` for loading from arbitrary paths.
- `planner/planner.py`: Added `_parse_key_string(key)` → (mode, tonic_midi).
  Modified `generate_to_files()` to generate or load cached .fugue for
  invention genre.

### Verification
- .fugue created on first run, reused on second, regenerated if deleted.
- Non-invention genres unaffected. Zero audible change.
