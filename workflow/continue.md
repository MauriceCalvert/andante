# Continue

## Current state

Phase 16a complete (2026-02-11). PhrasePlan.degree_keys always populated.
Phase 16b complete (2026-02-11). Shared foundation modules: 7 counterpoint
detection functions + 1 prevention helper in shared/counterpoint.py,
phrase_zone in shared/phrase_position.py, select_best_pitch stub in
shared/pitch_selection.py. 39 new tests all passing. 3767 total passed.

Phase 16f brief issued to task.md — wire DiminutionFill into
soprano_writer.py, replacing _fill_all_spans + _apply_guards with
write_voice pipeline call.

Phases 15a/15b complete. Phase 15b has 16 test failures — abandoned,
not worth fixing since voice_writer replaces the code anyway.

Decision: build unified voice_writer that handles all voices with pluggable
fill strategies, using soprano and bass writers as lessons. Old writers
remain in place until replaced.

### Interface design complete

`workflow/voice_writer_interfaces.md` defines all interfaces for voice_writer
and its sub-components. Agreed in discussion. Key decisions:

1. **Types**: StructuralTone, SpanBoundary, VoiceConfig, VoiceContext,
   SpanResult, SpanMetadata (typed hierarchy), WriteResult — all frozen
   dataclasses.
2. **FillStrategy protocol**: `fill_span(span, config, context) -> SpanResult`.
   Three parameters, all immutable.
3. **No apply_guards**: the old soprano_writer _apply_guards (170 lines of
   downstream fixing) is eliminated. Replaced by audit_voice (detect-only,
   raises on fault). D001/D008/D010 compliant.
4. **Strategies prevent faults (D010)**: strategies call shared counterpoint
   detection functions to check candidates before committing. Same functions
   used by audit_voice. Single source of truth (L017).
5. **No mutable state (L014)**: VoiceContext rebuilt immutably per span.
   No closures, no mutable captures.
6. **VoiceContext bundle**: other_voices, own_prior_notes, prior_phrase_tail,
   structural_offsets. Strategies call shared functions directly with this data.
7. **Phrase boundary continuity**: prior_phrase_tail (last Note of previous
   phrase) on VoiceContext. Strategy's first span prevents faults at the
   join. Audit checks it too.
8. **SpanMetadata typed hierarchy**: base class + per-strategy subclass
   (DiminutionMetadata, WalkingMetadata, etc.). Not a dict.
9. **Testing architecture**: 4 layers — shared functions (crafted notes),
   strategy creative (empty context), strategy counterpoint (minimal context),
   pipeline integration (full phrase).
10. **phrase_start on VoiceConfig**: for bar-boundary computation in
    cross-bar repetition checks.
11. **validate_voice runs before audit_voice**: hard invariants first
    (gaps, range, durations), then counterpoint/melodic style rules.

### Architectural review complete (2026-02-11)

Full review in `workflow/voice_writer_plan.md` under "Review Findings".
Verdict: design is solid. Two MUST FIX items before implementation:

**RF-1: Constraint relaxation priority.** When no pitch satisfies all
constraints, strategies need a shared, documented relaxation order.
Without it, bass and soprano will behave inconsistently. Suggested
order: step recovery relaxed first, hard invariants never relaxed.
Document in interfaces doc §2.

**RF-2: Deterministic variation (A005/D009/V001).** fill_span must be
deterministic given its inputs. Variation comes from VoiceConfig/
SpanBoundary fields, not RNG. State in FillStrategy contract.

SHOULD FIX (before or during Phase 16):
- RF-3: other_voices → dict[int, tuple[Note, ...]] keyed by voice_id
  (or defer to Phase 18 with documented gap)
- RF-4: character → Literal or enum, not bare str

DOCUMENT (add to interfaces doc / plan as notes):
- RF-5: L003 reconciliation (range assertion is detection, not clamping)
- RF-6: Harmonic data extension point (future field on VoiceContext)
- RF-7: Rests would require relaxing no-gap invariant
- RF-8: SpanMetadata as future ornament extension point
- RF-9: Expect Phase 16 integration test failures (guard removal)
- RF-11: end_midi=None fallback must be specified per strategy
- RF-12: phrase_zone() shared helper for consistent position interpretation

### Next step: update interfaces doc, then Phase 16 implementation

1. Update `workflow/voice_writer_interfaces.md` to address RF-1, RF-2,
   RF-3, RF-4, RF-5, RF-6, RF-7, RF-8, RF-11, RF-12 (add sections,
   notes, or type changes as specified in the review findings).
2. Then proceed with Phase 16 implementation.

Read `workflow/voice_writer_interfaces.md` for all type definitions,
function signatures, and contracts.

Read `workflow/voice_writer_plan.md` for architecture, migration path,
strategy estimates, and review findings. (Interfaces doc is authoritative
on design.)

New audit documents:
- `workflow/if_audit.md` — soprano `if` analysis (58 → ~10)
- `workflow/if_audit_bass.md` — bass `if` analysis (108 → ~20)
- `workflow/if_audit_never_none.md` — upstream fixes (32 eliminations)

Phase 16 scope:
- `builder/voice_types.py` — all types from §1 of interfaces doc
- `builder/voice_writer.py` — write_voice pipeline, audit_voice, validate_voice
- `builder/strategies/diminution.py` — DiminutionFill + DiminutionMetadata
- Extract shared counterpoint functions to `shared/counterpoint.py`
  (including new `has_consecutive_leaps`)
- Upstream data contract fixes (do first, before voice_writer):
  - PhrasePlan.degree_keys: always populate in phrase_planner
  - PhrasePlan.lead_voice: always populate in phrase_planner
  - next_phrase_entry_degree: assert in soprano caller
  - Soprano pitch lookup: assert coverage, return int not int|None
- Wire soprano through voice_writer (soprano_writer.py calls write_voice)
- Existing integration tests: expect some failures from guard removal
  (RF-9). Each failure is a generator bug the old guards were hiding.
- VoiceConfig now includes cadence_type (str | None)
- Keep old soprano_writer functions in git until Phase 16 passes (RF-13)

Do NOT touch bass_writer.py (Phase 17).

### soprano_writer.py state
The file currently contains Phase 15b code (span pipeline with bugs).
Phase 16 will replace generate_soprano_phrase to call write_voice instead.
The structural tone placement (_place_structural_tones) stays in soprano_writer
as caller logic. The fill/guard/validate logic moves to voice_writer.

### bass_writer.py state
Untouched. ~620 lines, one massive function with three texture branches.
Phase 17 target.

### Known test failures (Phase 15b, in current soprano_writer.py)
- 7 bass degree mismatches (bourree/chorale/gavotte/trio_sonata fenaroli + passo_indietro)
- 8 ugly leap faults (bourree/chorale/gavotte/invention/sarabande/trio_sonata)
- 1 minuet rhythmic character (0% crotchets)
Total: 16 failures. These will be resolved by Phase 16 replacing the code.

### Genre YAML characters (unchanged)
- invention: exordium=plain, narratio=energetic, confirmatio=expressive, peroratio=ornate
- bourree: A=energetic, B=bold
- fantasia: A=bold
- gavotte: A=expressive, B=expressive
- minuet: A=expressive, B=expressive
- sarabande: A=expressive, B=expressive

## Key files
- workflow/voice_writer_interfaces.md — interface design (types, protocols, signatures)
- workflow/voice_writer_plan.md — architecture and migration path
- workflow/result.md — Phase 15 results (for reference on what went wrong)
- workflow/todo.md — deferred work
- completed_260219.md — full history through Phase 14
