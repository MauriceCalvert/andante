# Voice Writer — Plan

Status: interfaces finalised in voice_writer_interfaces.md.
This document retains lessons, migration path, and risks.
**All type definitions, function signatures, design decisions, and test
architecture are in voice_writer_interfaces.md, which is authoritative.**
If this document conflicts with the interfaces doc, the interfaces doc wins.

Upstream fixes identified (see if_audit_never_none.md):
- PhrasePlan.degree_keys: always populate (eliminates 15 downstream ifs).
- Soprano coverage: assert, not branch (eliminates 12 downstream ifs).
- next_phrase_entry_degree: assert for non-cadential (eliminates 3 ifs).
- PhrasePlan.lead_voice: always populate (eliminates 2 ifs).

---

## Lessons from Reading Both Writers

### Soprano (post-Phase 15b, buggy)
- 5-step pipeline: place structural tones → compute exit → fill spans → guards → validate
- ~460 lines across 7 functions
- Fill spans: figuration produces both pitch and rhythm per span
- Guards: 115-line post-pass (cross-bar repetition, ugly intervals, cross-relations, leap-step)
- Bugs: template gating wrong for moderate genres, no ugly interval filter in realise_pitches

### Bass (untouched, ~620 lines)
- One 500-line function (generate_bass_phrase) with three texture branches
- Patterned: bass pattern provides both rhythm and pitch, structural overrides applied
- Pillar: rhythm cells provide durations, structural tones provide pitch, gaps hold
- Walking: rhythm cells provide durations, stepwise logic provides pitch per onset
- All three share: structural tone placement, parallel checking, cross-relation,
  range validation, voice crossing prevention, leap prevention
- Walking bass interleaves generation and checking — picks each pitch while
  checking against soprano. ~300 lines of interleaved logic.

### What's genuinely shared
1. Structural tone placement from schema degrees (degree_to_nearest_midi with prev tracking)
2. Counterpoint guards (parallels, cross-relations, voice crossing, ugly intervals, leaps)
3. Range validation and voice-leading-aware octave selection
4. Duration validation (VALID_DURATIONS_SET, gap/overlap checks, total duration)
5. Soprano pitch lookup at offset (used by bass for crossing prevention)

### What differs
1. **Structural tone enrichment**: bass checks consonance with soprano
   (_find_consonant_alternative); soprano doesn't check against bass.
   This is caller-side: the caller enriches structural tones before
   passing them to the writer.
2. **Rhythm source**: figuration (soprano), cells (pillar/walking bass),
   patterns (patterned bass). Always determined before pitch fill runs.
3. **Pitch fill logic**: diminution figures, stepwise walking, pattern lookup,
   chord sustain. Different algorithms, same interface shape.
4. **Guard interleaving**: soprano applies guards as a post-pass. Bass
   interleaves guards with generation. Both strategies now use shared
   counterpoint functions during generation (D010).

### Key Insight: Strategy Owns Both Rhythm and Pitch

The Phase 15 design split rhythm computation from pitch fill. Reading the
bass writer shows this split doesn't generalise. Walking bass rhythm
comes from cells, patterned bass rhythm comes from patterns, diminution
rhythm comes from figuration templates. Each texture has its own rhythm
source.

The fill strategy must produce complete notes (pitch + duration) for its
span. The pipeline provides structural tones and runs audit/validate.
The strategy decides everything between structural tones.

---

## Migration Path

### Phase 16: voice_writer.py + shared types

Create:
- `builder/voice_writer.py` — write_voice pipeline, audit_voice, validate_voice
- `builder/voice_types.py` — all types from interfaces doc §1
- `builder/strategies/diminution.py` — DiminutionFill (150–200 lines)
- `builder/strategies/__init__.py` — empty
- `shared/counterpoint.py` — extract/create shared functions from interfaces doc §7
- `shared/pitch_selection.py` — select_best_pitch helper from interfaces doc §2.1

Wire soprano through voice_writer:
- soprano_writer.py keeps _place_structural_tones (caller responsibility)
- generate_soprano_phrase becomes: place tones → build config → call write_voice
- Existing integration tests will initially fail where _apply_guards was
  patching faults. Each failure reveals a fault DiminutionFill must learn
  to prevent. This is by design, not regression. (RF-9.)

Do NOT touch bass_writer.py yet.

### Phase 17: Bass strategies

Create:
- `builder/strategies/walking.py` — WalkingFill (300–350 lines)
- `builder/strategies/pillar.py` — PillarFill (40–60 lines)
- `builder/strategies/patterned.py` — PatternedFill (60–80 lines)

Wire bass through voice_writer:
- bass_writer.py keeps structural tone placement with consonance enrichment
- generate_bass_phrase becomes: place tones → build config → call write_voice
- WalkingFill is the hardest extraction. It builds output incrementally
  with per-pitch checking — fill_span is not a batch operation internally.
  The interleaved generate-and-check is the algorithm, not a flaw.
- Budget 20–30 Layer 3 tests for WalkingFill edge cases. (RF-10.)

### Phase 18+: Inner voices

- `builder/strategies/chord.py` — ChordFill (~50 lines)
- Structural tone derivation from harmony (planner concern)
- Wire into phrase_writer
- other_voices dict keyed by voice_id already supports arbitrary voice count

### Line estimates (revised after Chaz review)

| Strategy | Realistic lines |
|----------|----------------|
| WalkingFill | 300–350 |
| DiminutionFill | 150–200 (with figure rejection + stepwise fallback) |
| PillarFill | 40–60 |
| PatternedFill | 60–80 |
| select_best_pitch helper | 40–60 |

WalkingFill exceeds the 100-line guideline. It stays as one file —
splitting would harm cohesion, since direction tracking, chromatic
approach logic, and pitch selection are tightly coupled.

---

## Resolved Questions

### 1. Rhythm ownership
Strategy owns both rhythm and pitch. Each strategy has its own rhythm
source. The pipeline doesn't prescribe rhythm.

### 2. is_acceptable callback scope
Replaced by VoiceContext + direct shared function calls. No callback.

### 3. Guard tolerance by texture
VoiceConfig.guard_tolerance: frozenset[int]. Default frozenset().
Walking bass sets {5} (perfect 4th). Guard pass is voice-agnostic.

### 4. Walking bass soprano trajectory
VoiceContext.other_voices (dict keyed by voice_id) gives the strategy
explicit access to soprano notes by TRACK_SOPRANO key.

### 5. Cadence type for chromatic approach
cadence_type on VoiceConfig. Strategy checks
`span.is_final_span and config.cadence_type is not None`.

### 6. Consecutive same-direction leaps
Added to shared/counterpoint.py. Applies to all voices.

### 7. Constraint relaxation priority (was RF-1)
Shared select_best_pitch helper with fixed priority. See interfaces
doc §2.1. Order: hard invariants and voice crossing never relax;
parallel fifths relax last; step recovery relaxes first.

### 8. other_voices labelling (was RF-3)
Fixed now, not deferred. dict[int, tuple[Note, ...]] keyed by voice_id.

### 9. character typing (was RF-4)
Literal type. Genre added to VoiceConfig as separate Literal field.

### 10. Audit failure mode (was Chaz review #7)
Two-mode: strict (AssertionError) during development, lenient
(returns violation list) once strategies mature. See interfaces doc §3.

### 11. DiminutionFill fallback (was Chaz review #4)
Try figures in preference order → stepwise fallback → select_best_pitch
ensures something is always produced. See interfaces doc §2.2.

---

## Review Findings

### RF-2: Deterministic variation (A005/D009/V001) (MUST FIX)

fill_span must be deterministic given its inputs. Variation comes from
VoiceConfig or SpanBoundary fields (phrase_bar, character, genre), not
from RNG. Stated in the FillStrategy contract (interfaces doc §2).

### RF-5: L003 reconciliation (DOCUMENT)

validate_voice docstring: "Range assertion is detection (D001), not
clamping (L003). The strategy must produce in-range pitches; this
catches strategy bugs."

### RF-6: No harmonic data extension point (DOCUMENT)

When harmonic analysis becomes available, it enters via VoiceContext
(rebuilt per span). Named as a future field.

### RF-7: Rests not precluded but not possible (DOCUMENT)

Rests would require relaxing the no-gap invariant in validate_voice.

### RF-8: SpanMetadata as ornament extension point (DOCUMENT)

SpanMetadata is the natural place for trill/mordent intent if ornaments
are added later.

### RF-9: Expect Phase 16 integration test failures (DOCUMENT)

Each failure reveals a fault the generator must learn to prevent. By
design, not regression.

### RF-10: Walking bass Layer 3 test volume (PLAN)

Budget 20–30 Layer 3 tests. See interfaces doc §8 for enumerated
categories.

### RF-11: SpanBoundary.end_midi = None fallback (DOCUMENT)

Must be specified per strategy. Bass arriving "freely" still means
harmonically sensible (chord tone of current key). Each strategy
documents its end_midi=None behaviour.

### RF-12: Phrase position interpretation (DOCUMENT)

Shared helper phrase_zone(phrase_bar, total_bars) ensures consistent
interpretation across strategies. See interfaces doc §7.

### RF-13: Keep old soprano_writer intact (PRACTICE)

Don't delete old functions until Phase 16 integration tests pass.

### RF-14: own_prior_notes carries full history (OBSERVATION)

Harmless at baroque phrase lengths (≤100 notes). Sliding window of 3
would suffice if performance mattered later.

---

## Risks

1. **Walking bass extraction is hard.** The current code has ~300 lines of
   interleaved pitch selection and checking. Extracting into WalkingFill
   while preserving behaviour requires care. Budget Phase 17 as the
   largest phase.

2. **Regression risk.** Mitigation: Phase 16 does soprano only, Phase 17
   does bass only. Never both at once.

3. **DiminutionFill figure rejection may cascade.** If many figures fail
   counterpoint checks, the stepwise fallback produces correct but bland
   output. This is acceptable for Phase 16 — the alternative is the old
   _apply_guards which produces incorrect output that sounds plausible.
   Correct-and-bland beats plausible-and-wrong.
