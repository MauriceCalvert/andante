# Andante Revision Plan

## Status

v1.1.0 | 2026-02-01 | Phase 5 design complete, testing approach defined

---

## Problem Statement

The builder execution path (figuration + realisation) is trapped in a whack-a-mole cycle:

1. faults.py reports anomaly X
2. We fix X
3. faults.py reports anomaly Y
4. We fix Y
5. goto 1

**Root cause:** The builder makes compositional decisions that belong in the planner. Figuration detects parallel fifths, checks dissonances, chooses hemiola, calculates density, selects figures by context — all decisions that should arrive pre-made in the plan. Realisation contains ad hoc fixes: `adjust_downbeat_consonance()` literally mutates bass notes after generation. This violates D008 (no downstream fixes), D010 (guards detect, generators prevent), and X001/X002 (post-realisation adjustment, iterative fix loops).

The fundamental flaw: soprano and bass figures are selected semi-independently, then validated together post-hoc. When the combined result violates a rule, patching one filter destabilises another bar.

**The fix:** Sequential voice writing with full awareness of prior voices, where every compositional decision arrives from the plan. The builder becomes purely mechanical: it receives all decisions and executes them deterministically.

---

## What Works (Do Not Touch)

| Component | Size | Why |
|-----------|------|-----|
| Planner layers 1–4 (rhetorical→metric) | ~80KB | Conceptually sound, tested |
| cs_generator.py | 52KB | CP-SAT counter-subject solver, 7 constraint groups. Months of work |
| Subject generation (motifs/) | 98KB | Head+tail generators, melodic features, affect scoring. Independent |
| Key class (shared/key.py) | 6KB | diatonic_step, degree_to_midi. Fundamental |
| Schema definitions + loader | 25KB | YAML data + schema_loader.py |
| All YAML data files | ~50 files | Genres, affects, schemas, cadences, instruments, figuration vocabulary |
| faults.py | 22KB | Guard logic is correct; becomes pure guard (expects zero faults) |
| Normative documents | Tier1, Tier2 | The specification, not the code |
| Learnings (both docs) | — | Hard-won knowledge |
| MIDI/MusicXML output | 14KB | io.py, musicxml_writer.py, midi_writer.py |

---

## What Must Be Replaced

~200KB of builder execution code:

| File(s) | Size | Problem |
|---------|------|---------|
| builder/figuration/ (18 files) | 176KB | Makes compositional decisions; 60KB in figurate.py + selector.py alone |
| builder/realisation.py | 17KB | Soprano/bass hardcoded; ad hoc bass modes |
| builder/realisation_bass.py | 3KB | `adjust_downbeat_consonance()` — a literal "fix" function |
| builder/realisation_util.py | 3KB | Coupled to soprano/bass naming |

Also affected (type changes propagate):

| File | Size | Change needed |
|------|------|---------------|
| builder/types.py | 7KB | NoteFile → voice-dict; Anchor rename |
| shared/constants.py | 12KB | Purge 30+ unused constants |

---

## Dead Wood to Delete

From unused_items.txt: 80+ unused items across the codebase.

### Entire unused modules

| Module | Size | Notes |
|--------|------|-------|
| shared/dissonance.py | 6KB | Never imported |
| shared/timed_material.py | 6KB | Never imported |
| shared/constraint_validator.py | 6KB | Never imported |
| shared/validate.py | 1KB | Never imported |
| shared/voice_role.py | 4KB | Replaced by voices.md entity model |
| builder/figuration/melodic_minor.py | 8KB | Never imported |

### Dead functions in live modules

| Module | Dead functions |
|--------|----------------|
| builder/figuration/sequencer.py | accelerate_to_cadence, apply_fortspinnung, compute_transposition_interval, create_sequence_figures, detect_melodic_rhyme, should_break_sequence, SequencerState |
| builder/figuration/realiser.py | apply_augmentation, apply_diminution, compute_bar_duration, compute_gap_duration, generate_default_durations, is_anacrusis_beat, realise_rhythm |
| builder/figuration/junction.py | compute_junction_penalty, suggest_alternative, validate_figure_sequence |
| shared/pitch.py | cycle_pitch_with_variety, degree_interval, is_degree_consonant, is_floating, is_midi_pitch, is_rest, place_degree, CONSONANT_DEGREE_INTERVALS |
| shared/music_math.py | bar_duration, beat_duration, build_offsets, repeat_to_fill, MusicMathError |
| shared/constants.py | 30+ unused constants (AUGMENTATION, CADENCE_DENSITY, DEGREE_TO_CHORD, DENSITY_LEVELS, DIATONIC_DEFAULTS, DIMINUTION, DOMINANT_TARGETS, FIGURE_ARRIVALS, FIGURE_CHARACTERS, FIGURE_PLACEMENTS, FIGURE_POLARITIES, HARMONIC_MINOR_SCALE, KEY_AREA_OFFSETS, LARGE_LEAP_SEMITONES, LEAP_SEMITONES, MELODIC_MINOR_SCALE, MIN_TONAL_SECTION_BARS, PHRASE_DEFORMATIONS, PHRASE_POSITIONS, TENSION_LEVELS, TESSITURA_DRIFT_THRESHOLD, TONAL_PROPORTION_TOLERANCE, TONAL_ROOTS, VALID_DURATION_OPS, VALID_PITCH_OPS, VOICE_TRACKS) |
| shared/errors.py | HarmonyGenerationError, MissingContextError, SubjectValidationError, VoiceGenerationError |

---

## Architecture: Before and After

### Before (current)

```
Plan (anchors with degree pairs)
  → figurate soprano (60KB of compositional logic)
  → figurate bass (semi-independently, with soprano onset hints)
  → adjust_downbeat_consonance (patch bass after the fact)
  → faults.py (reports violations from decisions made in figuration)
  → loop back to fix figuration filters
```

### After (target)

```
Plan (VoicePlan per voice: strategy + all decisions)
  → VoiceWriter (generic, service functions)
      uses WritingStrategy (walking / arpeggiated / sustained / contrapuntal)
      receives prior_voices: list[list[Note]]
      receives decisions: VoicePlan (density, character, hemiola, cadence flags)
  → faults.py (guard only, expects zero faults)
```

**Key properties of the new design:**

1. **Sequential writing.** Each voice is composed seeing all prior voices. No post-hoc conflict resolution.
2. **Strategy, not inheritance.** One VoiceWriter class with interchangeable WritingStrategy. No combinatorial subclass explosion.
3. **Voice-agnostic.** Writer doesn't know it's "bass" — it knows it's "the lower schema voice with walking strategy." Role determines dependency order.
4. **Decisions from plan.** Density, character, hemiola, cadence approach, anacrusis, figure vocabulary — all arrive in the VoicePlan. The writer does not infer context.
5. **Dependency-ordered.** Composition order from the plan's dependency graph: schema-bound voices first, imitative second, harmony-fill last.
6. **N-voice.** Same architecture handles 2, 3, 4, or more voices. Anchors stay 2-voice (schema framework); additional voices derive via role per section.
7. **Role per section.** Invertible counterpoint, compound melody, and role changes across sections are all expressed by SectionPlan.role, not by hacks.

### Why not inheritance?

The proposed subclass hierarchy (galant_bass_writer, soprano_writer, walking_bass_writer, etc.) conflates three independent axes:

| Axis | Examples |
|------|----------|
| Genre | galant, contrapuntal, chorale |
| Texture | walking, arpeggiated, sustained, Alberti |
| Role | schema_upper, schema_lower, imitative, harmony_fill |

These combine freely. A minuet bass is galant + arpeggiated + schema_lower. An invention bass is contrapuntal + walking + schema_lower. A voice can change texture within a piece (sustained at opening, walking in narratio, arpeggiated at cadences). Strategy composition handles this; inheritance cannot.

---

## Testing Approach

### Principle

Most conventional unit tests add little value to this codebase.  Three
properties make them low-yield:

1. **Deterministic pipeline.** Given the same YAML and seed, identical output.
   No concurrency, no external state.  If it works once, it works forever.
2. **Rich runtime assertions.** Precondition asserts on types, ranges, shapes
   fire on every execution — better than unit tests because they check the
   production path, not a synthetic one.
3. **faults.py IS the test suite.** 15 categories of real musical rules
   checked on every composition.  The faults contract (phase5_design.md)
   guarantees every fault = a code bug.

### What we test

| File | Tests | Lines | Value |
|------|-------|-------|-------|
| test_pitch.py | Property tests: round-trip, monotonicity, octave consistency, interval arithmetic, cross-check against degree_to_midi | ~180 | Catches off-by-one in the one function all pitch derivation depends on |
| test_plan_contract.py | validate_plan() on edge-case plans: reciprocal shared_actuator, composition_order vs follows, gap index contiguity, role-specific field presence | ~80 | Catches planner structural bugs that faults.py can't see |
| test_smoke.py | Compose all YAML pieces, assert zero faults | ~30 | End-to-end integration: if it passes, the system works |

Three files, ~300 lines total.

### What we do NOT test

- Dataclass construction (frozen dataclasses with type hints are self-testing)
- Individual planner functions (smoke test covers them in combination)
- Mocks (no external dependencies to mock)
- Specific note sequences (brittle, uninformative, break on vocabulary changes)

### Runtime guards (not test files)

- **validate_plan():** ~20 lines of assertions in the planner, run every time
  a plan is built.  Checks structural invariants (reciprocal shared_actuator,
  composition_order respects follows, gap indices contiguous, etc.).
- **Precondition asserts:** Already throughout the codebase.  Continue adding
  to new code.
- **faults.py:** Runs on every composition.  The 15-category faults contract
  (phase5_design.md §Faults Contract) defines "correct."

### Current status

| Test | Status |
|------|--------|
| test_pitch.py | Written.  Tests DiatonicPitch + Key.diatonic_to_midi/midi_to_diatonic. |
| test_plan_contract.py | Not yet.  Requires VoicePlan types (Phase 5 implementation). |
| test_smoke.py | Not yet.  Requires new builder (Phase 6+). |

---

## Phases

### Phase 1: Delete dead wood

Delete all unused modules, functions, constants, and imports listed above. Run tests after each deletion to verify nothing breaks.

**Risk:** Low. Items are confirmed unused.
**Effort:** Small.
**Touches:** shared/, builder/, planner/

### Phase 2: Voice entity model

Implement voices.md entity model in shared/. Voice, Role, Instrument, Actuator, Scoring, Track as frozen dataclasses. Role enum: schema_upper, schema_lower, imitative, harmony_fill.

**Risk:** Low. New files, no existing code changes yet.
**Effort:** Small.
**Touches:** shared/ (new files)

### Phase 3: NoteFile → voice-dict

Replace `NoteFile(soprano=..., bass=...)` with voice-indexed structure: `dict[str, tuple[Note, ...]]` keyed by voice id. Update io.py, midi_writer.py, musicxml_writer.py, faults.py to iterate voices generically.

**Risk:** Medium. Propagates to output chain and tests.
**Effort:** Medium.
**Touches:** builder/types.py, builder/io.py, builder/faults.py, shared/midi_writer.py, builder/musicxml_writer.py, tests/

### Phase 4: Anchor field rename

`soprano_degree` → `upper_degree`, `bass_degree` → `lower_degree`, `soprano_midi` → `upper_midi`, `bass_midi` → `lower_midi`. As specified in voices.md.

**Risk:** Medium. Broad find-and-replace across planner and builder.
**Effort:** Small-medium.
**Touches:** planner/, builder/, shared/

### Phase 5: VoicePlan contract design ✓

**Status: COMPLETE.** See phase5_design.md v0.3.0.

Design deliverables:
- **DiatonicPitch** — linear step count, no mod-7 wrapping (shared/diatonic_pitch.py — implemented)
- **Key.diatonic_to_midi / midi_to_diatonic** — pitch conversion (shared/key.py — implemented)
- **MIDI elimination** — derive at point of need, never store internally
- **VoicePlan / SectionPlan / GapPlan / CompositionPlan** — complete contract
- **Role per section** — supports invertible counterpoint, compound melody
- **shared_actuator_with** — compound melody (interleaved solo voices)
- **Faults contract** — all 15 categories fire if and only if code bug
- **N-voice scaling** — architecture handles 2, 3, 4+ voices
- **test_pitch.py** — property tests for the mathematical foundation (written)

**Not yet implemented** (Phase 5 code tasks remaining):
- Plan dataclass types (VoicePlan, SectionPlan, GapPlan, etc.)
- validate_plan() runtime guard
- test_plan_contract.py

### Phase 6: VoiceWriter + WritingStrategy

Build the new voice writing system:

- `VoiceWriter`: generic class with service functions (diatonic step, octave selection, duration validation, junction checking).
- `WritingStrategy` (abstract): interface for texture-specific logic.
- Concrete strategies: `ContrapuntalStrategy`, `WalkingBassStrategy`, `ArpeggiatedBassStrategy`, `SustainedStrategy`, `SchemaStrategy`.
- Composition order driven by dependency graph in the plan.

Each voice writer receives:
- Its VoicePlan (all decisions pre-made).
- The home Key.
- All previously-written voices as `list[list[Note]]`.
- Its actuator range (from scoring → instrument → actuator).

It produces: `list[Note]` for that voice.

**Risk:** Medium. New code, but design is clear after Phase 5.
**Effort:** Large. This is the main implementation phase.
**Touches:** builder/ (new files, replacing old)

### Phase 7: Enrich planner output

Update the planner to produce VoicePlan per voice. This means the planner must now decide:

- Writing strategy per voice per section
- Density and character per phrase
- Hemiola flags
- Cadence approach decisions
- Anacrusis decisions
- Figure vocabulary constraints
- Start offsets and rhythmic units
- Role per section (for invertible counterpoint)
- shared_actuator_with (for compound melody)
- Rhythmic asymmetry between simultaneous voices

Most of this information already exists somewhere (bar_context.py, passage_assignments, genre config). The work is collecting it into an explicit VoicePlan output rather than letting figuration infer it.

**Risk:** Medium. Touches planner, but additions not rewrites.
**Effort:** Medium.
**Touches:** planner/textural.py, planner/rhythmic.py, possibly planner/planner.py

### Phase 8: Delete old builder execution path

Delete:
- builder/figuration/ (entire directory, 176KB)
- builder/realisation.py (17KB)
- builder/realisation_bass.py (3KB)
- builder/realisation_util.py (3KB)

Also delete or simplify:
- builder/constraints.py, builder/costs.py, builder/solver.py, builder/greedy_solver.py, builder/counterpoint.py, builder/slice.py — if no longer needed by the new builder.

**Risk:** Low (by this point the new builder is tested).
**Effort:** Small. The satisfying part.

### Phase 9: Integration test + faults.py updates

Run the full pipeline with existing briefs. faults.py must report zero faults.

faults.py updates required (from faults contract analysis):
1. Accept actuator ranges as parameter (replace hardcoded VOICE_RANGES)
2. Check ugly_leap for all voices (currently soprano only)
3. Check dissonance for all voice pairs (currently soprano vs bass only)
4. Fix direct_motion for voice crossing (use pitch-ordered pairs, not index)
5. Fix direct_motion for N voices (check all relevant pairs)

Write test_smoke.py: compose all YAML pieces, assert zero faults.

Compare MIDI output with pre-revision output to verify musical plausibility (not identity — the output will differ, but should be at least as good).

**Risk:** Medium. Integration always surfaces surprises.
**Effort:** Medium.
**Touches:** builder/faults.py, test_smoke.py

---

## Success Criteria

1. faults.py reports zero faults on all existing briefs.
2. No function in the builder infers compositional context — all decisions arrive in the VoicePlan.
3. No "fix" or "adjust" functions anywhere in the builder.
4. Voice-agnostic: same VoiceWriter handles soprano, bass, or any future voice.
5. Adding a new texture (e.g. Alberti bass) requires only a new WritingStrategy, no changes to VoiceWriter.
6. Adding a third voice requires only a new VoicePlan entry and dependency edge, no structural changes.
7. All 15 fault categories are bug-only guards (faults contract holds).
8. test_pitch.py, test_plan_contract.py, test_smoke.py all pass.

---

## Risk: Sequential writing may over-constrain later voices

If voice A is written first and voice B must avoid all conflicts with A, then B is heavily constrained. If A's figure leaves B with no legal options, dead end.

**Mitigation:** The plan must ensure feasibility. If the plan specifies an anchor pair and a figure strategy, the combination must guarantee a legal voice B exists. This pushes intelligence into the planner — which is where it belongs.

**Fallback:** If the writer exhausts all candidates for a bar, it reports the failure upstream with enough context to diagnose the plan. No silent fallback. No "fix" function. Abort is acceptable; garbage is not.

---

## Document History

| Date | Change |
|------|--------|
| 2026-02-01 | Initial version from architectural discussion |
| 2026-02-01 | v1.1.0: Phase 5 marked complete. Testing approach section added. Phase 7 updated with role-per-section and compound melody planning. Phase 9 expanded with faults.py updates. Success criteria expanded (items 7, 8). Architecture section updated (items 6, 7). |

---

*This document is normative. The VoicePlan contract is agreed (phase5_design.md v0.3.0).*
