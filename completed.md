# Completed Work Log

## 2026-02-11 — Phase 16f: Wire DiminutionFill into soprano_writer

Replaced soprano generation pipeline from old `_fill_all_spans` + `_apply_guards` (downstream fix) with new `write_voice` + `DiminutionFill` (prevent at source).

**Changed files:**
- `builder/soprano_writer.py`: Deleted 6 functions (_fill_all_spans, _apply_guards, _validate_soprano_notes, _check_leap_step, _check_max_interval, _deflect_neighbour); rewrote generate_soprano_phrase to call write_voice with DiminutionFill strategy. Exactly 2 functions remain. Public API unchanged.

**Test results:**
- Import: ✓ Success
- Pipeline: ✓ Generates output (minuet c_major: 178 soprano, 52 bass notes)
- Test suite: 37 new failures (cross-bar repetition, leap-step recovery)

**Known issue:** DiminutionFill does not yet prevent cross-bar repetition (D007) or enforce leap-step recovery. Old _apply_guards fixed these downstream; new audit_voice detects them (logged with strict_audit=False) but does not fix. Task Known Limitation #3 identifies this as expected behavior, not a wiring bug. Tests enforce old postconditions that new system does not guarantee.

**Audit violations:** Pipeline logged "needs step recovery at 71 at offset 7" - confirms that leap-recovery prevention is not yet in DiminutionFill.

**Chaz verdict:** Wiring complete and correct. Public API unchanged. Code follows all CLAUDE.md rules (2 functions, no nested ifs, all constants in shared/constants). The soprano generation path now uses the unified voice writer pipeline.

**Outstanding:** Either (1) enhance DiminutionFill to prevent cross-bar repetition and leap-step violations, or (2) update tests to reflect new postconditions, or (3) accept lenient behavior and monitor audit violations in production output.

---

## 2026-02-11 — Phase 16d: Voice Writer Pipeline

Created `builder/voice_writer.py` with three public functions implementing the voice generation pipeline:

1. **validate_voice** — Pure assertion function checking 5 hard invariants (range, durations, gaps/overlaps, total duration, max melodic interval). Raises AssertionError on violation.

2. **audit_voice** — Detection-only counterpoint pass using shared/counterpoint.py functions. Checks: parallel perfects, cross-relations, voice crossing, ugly intervals, cross-bar repetition, leap-step recovery, consecutive leaps, phrase boundary continuity. Two modes: strict (raise on first fault) and lenient (collect all violations).

3. **write_voice** — 7-step pipeline: compute structural_offsets → build SpanBoundary spans → for each span (build immutable VoiceContext → call fill_strategy.fill_span → accumulate notes) → concatenate → validate_voice → audit_voice → return WriteResult.

Checkpoints:
- Import test: ✓ PASS
- Test suite: ✓ PASS (3767 passed, 204 skipped, 16 xfailed — exact baseline match)
- Chaz review: ✓ PASS (all 6 review points confirmed, 25 if statements all justified)

Module is ~418 lines of pure pipeline plumbing with no strategy-specific logic. VoiceContext rebuilt immutably each span iteration, no mutable state leaks. All counterpoint checks use shared functions (single source of truth).

## 2026-02-11 — Phase 16c: Voice Writer Types

Created `builder/voice_types.py` with all frozen dataclass types from voice_writer_interfaces.md:

**Types created (14 total):**
- 3 Literal types: GENRES (8 genre names), CHARACTERS (5 levels), PHRASE_ZONE (3 positions)
- 11 frozen dataclasses: StructuralTone, SpanBoundary, VoiceConfig, VoiceContext, SpanMetadata (base), DiminutionMetadata, WalkingMetadata, PillarMetadata, PatternedMetadata, SpanResult, AuditViolation, WriteResult
- 1 Protocol: FillStrategy (with fill_span method)

**Infrastructure:**
- Created `builder/strategies/__init__.py` (empty package init per L018)

**GENRES correction applied:** Used actual genre names from data/genres/*.yaml (bourree, chorale, fantasia, gavotte, invention, minuet, sarabande, trio_sonata), not hypothetical names from interface doc.

**Checkpoints passed:**
- Import test: `python -c "from builder.voice_types import *"` — success
- Test suite: 3767 passed, 204 skipped, 16 xfailed (exact match to Phase 16b baseline)
- Chaz review: all types match interface doc, all frozen, no circular imports

**Files created:**
- builder/voice_types.py (177 lines)
- builder/strategies/__init__.py (1 line)

Zero logic implementation — types only. No test regressions. Ready for Phase 16d (DiminutionFill strategy).

## 2026-02-11 — Phase 16e: DiminutionFill Strategy

Created `builder/strategies/diminution.py` implementing FillStrategy protocol with counterpoint-aware figure selection and stepwise fallback.

**Implementation (407 lines):**
- Constructor stores character, recall_figure_name, prev_figure_name state
- fill_span follows 5-step logic: (1) compute span parameters, (2) try preferred figure with counterpoint checks, (3) try alternative figures, (4) stepwise fallback if all rejected, (5) build SpanResult with DiminutionMetadata

**Counterpoint checking (_check_figure_pitches):**
- First pitch (structural tone) always exempt — never checked
- For each subsequent pitch: check has_parallel_perfect (all voices), has_cross_relation (all voices), is_ugly_melodic_interval (vs previous), would_cross_voice (at common onsets)
- Returns (accepted, notes) — rejects entire figure on first violation

**Stepwise fallback (_stepwise_fallback):**
- Generates diatonic step candidates toward end_midi
- Filters to range, prefers direction toward target
- Calls select_best_pitch (constraint relaxation protocol)
- Always produces output — falls back to current_pitch if no candidates
- Sets used_stepwise_fallback=True

**No duplication:**
- Calls classify_interval, select_figure, realise_pitches from figuration modules
- Calls compute_rhythmic_distribution, character_to_density, get_rhythm_templates, select_rhythm_template, get_diminutions from loader/rhythm modules
- Calls has_parallel_perfect, has_cross_relation, is_ugly_melodic_interval, would_cross_voice from shared.counterpoint
- Calls select_best_pitch from shared.pitch_selection

Checkpoints:
- Import test: ✓ PASS
- Test suite: ✓ PASS (3767 passed, 204 skipped, 16 xfailed — zero regressions)
- Chaz review: ✓ PASS (all 7 review points confirmed, all if statements structural)

Known limitations (acknowledged in task): select_best_pitch placeholder (returns first candidate), figure rejection bias (correct trade-off), no per-beat harmonic data, rhythm preserved from existing system.

Next: Phase 16f — wire DiminutionFill into soprano_writer.py, replace _fill_all_spans + _apply_guards.
