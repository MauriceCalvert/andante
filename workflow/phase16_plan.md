# Phase 16 — Voice Writer (Soprano) — Sub-phase Breakdown

Each sub-phase is one CC brief. Max 2 files modified. Evaluated
before the next sub-phase starts.

## 16a — Upstream data contract fixes

**Goal**: Eliminate 32 downstream `if X is None` branches by always
populating PhrasePlan.degree_keys and PhrasePlan.lead_voice.

**Files**: builder/phrase_types.py, builder/phrase_planner.py

**Detail**: degree_keys is currently None for non-sequential,
non-cadential schemas. Always build a tuple of Keys — for
non-sequential schemas, every degree gets local_key. lead_voice
is currently None when YAML doesn't specify; default to
TRACK_SOPRANO (soprano leads unless told otherwise). Change the
type annotations to remove the None option. Downstream consumers
(soprano_writer, bass_writer, phrase_writer) should not break because
they already handle both cases; we're just guaranteeing the non-None
path is always taken.

## 16b — Shared foundation modules

**Goal**: Create the shared modules that voice_writer and strategies
depend on.

**Files created**:
- shared/pitch_selection.py — select_best_pitch (~50 lines)
- shared/phrase_position.py — phrase_zone helper (~20 lines)

**Files modified**:
- shared/counterpoint.py — add detection functions (has_parallel_perfect,
  would_cross_voice, is_ugly_melodic_interval, needs_step_recovery,
  is_cross_bar_repetition, has_consecutive_leaps) + prevention helper
  (find_non_parallel_pitch)

Note: 3 files touched. If CC context is tight, split into two briefs
(16b1: counterpoint extensions, 16b2: pitch_selection + phrase_position).

## 16c — Voice types + strategy skeleton

**Goal**: Create the type definitions that all subsequent modules import.

**Files created**:
- builder/voice_types.py — StructuralTone, SpanBoundary, VoiceConfig,
  VoiceContext, SpanResult, SpanMetadata base, WriteResult,
  AuditViolation, FillStrategy protocol, Literal types
- builder/strategies/__init__.py — empty

## 16d — Voice writer pipeline

**Goal**: Create the write_voice pipeline, audit_voice, validate_voice.

**Files created**:
- builder/voice_writer.py (~150 lines)

Depends on: 16b (shared modules), 16c (types).

## 16e — DiminutionFill strategy

**Goal**: Create the soprano fill strategy wrapping existing figuration
code.

**Files created**:
- builder/strategies/diminution.py (~150–200 lines)
- builder/strategies/diminution_metadata.py (DiminutionMetadata, if
  needed for import hygiene — or keep in diminution.py)

Depends on: 16b, 16c, 16d.

## 16f — Wire soprano

**Goal**: Replace soprano_writer.py internals to call write_voice.
Keep public signature unchanged. Keep old functions until tests pass.

**Files modified**:
- builder/soprano_writer.py

Depends on: all previous sub-phases.

**Expected outcome**: Some integration test failures from guard removal
(RF-9). Each failure is a generator bug the old _apply_guards was
hiding. These get fixed in 16f or a follow-up 16g.

## Ordering and dependencies

```
16a (upstream fixes) — independent, do first
16b (shared modules)  ─┐
16c (voice types)      ─┤── can be done in any order
                        │
16d (voice_writer)     ─┘── needs 16b + 16c
16e (DiminutionFill)   ─── needs 16b + 16c + 16d
16f (wire soprano)     ─── needs all of the above
```
