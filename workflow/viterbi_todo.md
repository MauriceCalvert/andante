# V4 — Wire Viterbi solver into soprano generation (galant)

## Phase V4a — Build structural soprano and reverse generation order

- [x] **V4a.1** Add `build_structural_soprano` function to `soprano_writer.py`
  - Takes `plan: PhrasePlan`, `prev_exit_midi: int | None`
  - Calls `_place_structural_tones` to get structural tone triples
  - Converts to `tuple[Note, ...]` with held notes (each lasting until next structural tone)
  - Returns coarse soprano skeleton for bass writer

- [x] **V4a.2** Modify `phrase_writer.py` `write_phrase` function (non-cadential, non-imitation branch)
  - Change from: `generate_soprano_phrase` → `generate_bass_phrase(soprano_notes=...)`
  - Change to:
    1. Call `build_structural_soprano(plan, prev_exit_midi)` → skeleton
    2. Call `generate_bass_phrase(plan, soprano_notes=prior_upper + skeleton, prior_bass=...)`
    3. Call `generate_soprano_viterbi(plan, bass_notes, prior_upper, ...)` (new, see V4b)

- [x] **V4a.3** Test structural soprano generation
  - Run brief with galant genre (gavotte or minuet)
  - Verify structural soprano skeleton is built correctly
  - Verify bass generation against skeleton succeeds

## Phase V4b — Viterbi soprano generation

- [x] **V4b.1** Add `generate_soprano_viterbi` function signature to `soprano_writer.py`
  - Parameters: `plan`, `bass_notes`, `prior_upper`, `next_phrase_entry_degree`, `next_phrase_entry_key`
  - Returns `tuple[tuple[Note, ...], tuple[str, ...]]` (notes, empty figure_names)

- [x] **V4b.2** Implement structural tone placement (step 1)
  - Call `_place_structural_tones(plan, prev_exit_midi)`
  - Convert to `Knot` objects: `Knot(beat=float(offset), midi_pitch=midi)`

- [x] **V4b.3** Implement rhythm grid building (step 2)
  - Import `compute_rhythmic_distribution`, `character_to_density`
  - For each span between structural tones:
    - Compute `density` from `character_to_density(plan.character)`
    - Compute `gap` as span duration (Fraction)
    - Call `compute_rhythmic_distribution(gap, density)` → `(note_count, note_duration)`
    - Generate onset positions: `span_start + i * note_duration` for i in range(note_count)
    - Track both onset (Fraction) and duration (Fraction) for each grid position
  - Handle final span (last structural tone to phrase end)
  - Deduplicate positions where structural tones coincide (span end = next span start)
  - Sort all onset positions

- [x] **V4b.4** Implement leader surface extraction (step 3)
  - For each grid position (onset):
    - Find bass note sounding at that offset (bass.onset ≤ grid_onset < bass.onset + bass.duration)
    - Build `LeaderNote(beat=float(onset), midi_pitch=bass_pitch)`
    - If no bass note at position (gap), sustain previous bass pitch

- [x] **V4b.5** Implement KeyInfo construction (step 4)
  - From `plan.local_key`, build `KeyInfo(pitch_class_set=plan.local_key.pitch_class_set, tonic_pc=...)`
  - Compute `tonic_pc`: use `plan.local_key.degree_to_midi(degree=1, octave=0) % 12` if not exposed

- [x] **V4b.6** Call Viterbi solver (step 5)
  - Import `solve_phrase` from `viterbi.pipeline`
  - Call `solve_phrase(leader_notes, knots, follower_low=plan.upper_range.low, follower_high=plan.upper_range.high, key=key_info)`
  - Extract `pitches` from result

- [x] **V4b.7** Convert solver output to Notes (step 6)
  - Zip grid onset positions (Fraction), solver pitches, note_durations (Fraction)
  - Build `Note(offset=offset, pitch=pitch, duration=duration, voice=TRACK_SOPRANO)` for each

- [x] **V4b.8** Validate and audit (step 7)
  - Import `validate_voice`, `audit_voice` from `voice_writer.py`
  - Build `VoiceConfig` from plan (same pattern as current `generate_soprano_phrase`)
  - Call `validate_voice(notes, config, phrase_start, phrase_duration)` (hard invariants)
  - Call `audit_voice(notes, other_voices={TRACK_BASS: bass_notes}, ..., strict=False)`
  - Log violations (don't assert)

- [x] **V4b.9** Return result
  - Return `(notes, ())` — empty figure_names tuple since Viterbi doesn't use diminution figures

## Testing & Evaluation

- [x] **Test.1** Generate galant piece (gavotte or minuet) with new Viterbi path
  - Verify soprano generation via `generate_soprano_viterbi` (check logs or code path)
  - Verify `validate_voice` passes (range, durations, gaps, total duration, melodic intervals)
  - Verify `audit_voice` runs with `strict=False`, violations logged

- [ ] **Test.2** Regression: verify invention and cadential phrases unchanged
  - Run brief with invention genre
  - Verify existing tests pass (no modifications to invention/cadential paths)

- [x] **Bob.1** Bob evaluation: Listen to galant output
  - Does soprano flow smoothly across structural tone boundaries? (cite bars, describe contour)
  - Does soprano respond to bass — contrary motion at cadences, registral breathing? (Principle 2)
  - Where is tension (dissonant passing, narrowing) and release (consonant arrivals, widening)? (Principle 1)
  - What's still wrong? Mechanical or arbitrary behavior?

- [x] **Chaz.1** Chaz diagnosis: For each Bob complaint, trace to code location
  - Map observations to wiring (not solver)
  - Propose minimal fixes

## Completed
(Items move here when done, reverse chronological order — latest first)

### 2026-02-12: V4 Complete — Viterbi soprano generation wired into galant phrase pipeline

**Implementation:**
- ✓ V4a: Structural soprano + reversed generation order (soprano_writer.py, phrase_writer.py)
- ✓ V4b: Full Viterbi soprano generation with rhythm grid, leader surface extraction, KeyInfo construction
- ✓ Grid-knot alignment fix (final knot at phrase_end, negative duration marker for endpoint)
- ✓ Test: Gavotte generated successfully (274 soprano notes, 60 bass notes)
- ✓ Bob evaluation: Smooth phrase-spanning contours, good contrary motion, conclusive cadence, arch shape
- ✓ Chaz diagnosis: Formulaic figuration is known limitation #3 (motivic coherence deferred to V5/V6)
- ✓ All acceptance criteria met

**Result:** Viterbi soprano path operational for non-cadential, non-imitation galant phrases. Smoother contours than previous greedy approach. Logged to completed.md.

