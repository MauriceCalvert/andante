# Voice Writer — Interface Design

Status: authoritative.
Prerequisite: voice_writer_plan.md (lessons and migration path).

This document defines the interfaces — types, protocols, function signatures —
that voice_writer.py and its sub-components expose. The goal is to agree these
before writing code, since everything downstream (strategies, guards, callers)
depends on them.

Governing laws:
- D001: Validate, don't fix.
- D008: No downstream fixes.
- D010: Guards detect, generators prevent.
- L014: Clone before modify, never mutate parameters.
- L015: NamedTuple/dataclass, not tuples.
- L017: Single source of truth, inherit not repeat.

Consequence: there is no post-pass that corrects notes. Strategies must
produce correct output. The audit pass detects violations and raises.
If the audit fires, it is a strategy bug.

---

## 1. Types

### 1.1 StructuralTone

What the caller provides for each schema arrival point.

```python
@dataclass(frozen=True)
class StructuralTone:
    offset: Fraction       # absolute offset in whole notes
    midi: int              # resolved MIDI pitch
    key: Key               # local key at this point
```

The caller is responsible for:
- Resolving degrees to MIDI (using degree_to_nearest_midi, voice-leading)
- Consonance enrichment (bass checking against soprano)
- Octave selection relative to previous pitch

The writer receives resolved pitches and doesn't know or care about degrees.


### 1.2 SpanBoundary

What a FillStrategy receives for one span between adjacent structural tones
(or last structural tone to phrase end).

```python
@dataclass(frozen=True)
class SpanBoundary:
    start_offset: Fraction
    start_midi: int
    start_key: Key
    end_offset: Fraction
    end_midi: int | None       # None when no next target known (phrase end)
    end_key: Key | None        # None when end_midi is None
    phrase_bar: int             # which bar of the phrase this span starts in (1-based)
    total_bars: int             # total bars in the phrase
    is_final_span: bool        # True if this is the last span in the phrase
```

Design notes:
- `end_midi` is None for the final span when no next-phrase entry pitch is known.
  The strategy must handle this — see §2.3 for per-strategy fallback behaviour.
- `phrase_bar` and `total_bars` let the strategy infer phrase position
  via phrase_zone() (see §7).
- `start_key` and `end_key` may differ at modulation boundaries.


### 1.3 VoiceConfig

Static configuration for the voice being written. Assembled once per
phrase by the caller from PhrasePlan fields.

```python
GENRES = Literal[
    "bourree", "chorale", "fantasia", "gavotte",
    "invention", "minuet", "sarabande", "trio_sonata",
]
CHARACTERS = Literal["plain", "expressive", "energetic", "bold", "ornate"]
PHRASE_ZONE = Literal["opening", "middle", "cadential"]

@dataclass(frozen=True)
class VoiceConfig:
    voice_id: int               # TRACK_SOPRANO, TRACK_BASS, etc.
    range_low: int              # MIDI floor
    range_high: int             # MIDI ceiling
    key: Key                    # phrase-level key (spans may override locally)
    metre: str                  # "3/4", "4/4", etc.
    bar_length: Fraction        # precomputed from metre
    beat_unit: Fraction         # precomputed from metre
    phrase_start: Fraction      # absolute offset of phrase start
    genre: GENRES               # shapes rhythmic weight, leap frequency, character
    character: CHARACTERS       # "plain", "expressive", "energetic", etc.
    is_minor: bool
    guard_tolerance: frozenset[int]  # interval classes the audit ignores (e.g. {5} for P4)
    cadence_type: str | None         # "HC", "PAC", etc. or None
```

Design notes:
- `bar_length` and `beat_unit` are precomputed by the caller so that
  neither the strategy nor the audit need to re-parse the metre string.
- `guard_tolerance` lets walking bass tolerate parallel 4ths while keeping
  the audit logic voice-agnostic. Default: `frozenset()`.
- `character` flows through to strategies that need it (DiminutionFill
  uses it for figure selection). Typed as Literal to prevent stringly-typed
  drift.
- `genre` is the dance/form type. Strategies use it to shape rhythmic
  weight and leap frequency. A gavotte bass is grounded on beat 3; a
  gigue bass leaps; a sarabande bass sustains. Without genre, output is
  generic and belongs to no form.
- `cadence_type` flows through to WalkingFill, which uses chromatic
  approach only at cadential arrivals (`span.is_final_span and
  config.cadence_type is not None`). Default: None.


### 1.4 VoiceContext

Everything a strategy needs to check its output against. Rebuilt by the
pipeline before each span call. Immutable (L014).

```python
@dataclass(frozen=True)
class VoiceContext:
    other_voices: dict[int, tuple[Note, ...]]   # keyed by voice_id (TRACK_SOPRANO, etc.)
    own_prior_notes: tuple[Note, ...]            # notes from earlier spans in this phrase
    prior_phrase_tail: Note | None               # last note of previous phrase
    structural_offsets: frozenset[Fraction]
```

**other_voices is keyed by voice_id**, not positional. WalkingFill accesses
`context.other_voices[TRACK_SOPRANO]` explicitly. Shared counterpoint
functions that check against all voices iterate `.values()`. This supports
arbitrary voice counts without positional assumptions. (Chaz review: fix
now, not Phase 18.)

The strategy uses `other_voices` for vertical checks (parallels, crossing,
cross-relations) and `own_prior_notes` for melodic continuity checks
(leap-step recovery across span boundaries, cross-bar repetition, ugly
intervals against the last note of the previous span).

`prior_phrase_tail` is the final note of the previous phrase in this voice
(or None for the first phrase). The strategy's first span uses it for:
- Leap-step recovery across the phrase boundary
- Cross-bar repetition at the phrase boundary
- Ugly melodic interval from previous phrase's last note to first fill note

`structural_offsets` tells the strategy which offsets are structurally
fixed, so it can apply different rules at structural boundaries
(e.g. structural-to-structural leaps are exempt from step recovery).

No callbacks. The strategy calls shared counterpoint functions directly,
passing the data it needs from VoiceContext. This keeps the interface
explicit and testable — no closures, no mutable captures.

**Performance note:** Immutable rebuild per span means copying growing
tuples. At baroque phrase lengths (≤100 notes, ≤8 spans) this is
microseconds. Immutability over performance is a conscious design choice.


### 1.5 SpanMetadata (base class)

Strategy-specific information about how a span was filled.
Typed and inheritable (not a dict).

```python
@dataclass(frozen=True)
class SpanMetadata:
    """Base class for strategy-specific span metadata."""
    strategy_name: str


@dataclass(frozen=True)
class DiminutionMetadata(SpanMetadata):
    """Metadata from DiminutionFill."""
    figure_name: str
    used_stepwise_fallback: bool   # True if no figure passed counterpoint checks


@dataclass(frozen=True)
class WalkingMetadata(SpanMetadata):
    """Metadata from WalkingFill."""
    direction: str          # "ascending" | "descending"
    approach_type: str      # "chromatic" | "diatonic" | "direct"


@dataclass(frozen=True)
class PillarMetadata(SpanMetadata):
    """Metadata from PillarFill."""
    held: bool              # True if structural tone was sustained


@dataclass(frozen=True)
class PatternedMetadata(SpanMetadata):
    """Metadata from PatternedFill."""
    pattern_name: str
```

Design notes:
- Frozen dataclass hierarchy. Each strategy defines its own subclass.
- `strategy_name` on the base class allows generic logging without
  isinstance checks.
- `used_stepwise_fallback` on DiminutionMetadata makes fallback usage
  visible for diagnostics without hiding it in the output.
- SpanMetadata is the natural extension point for ornament intent
  (trill markers, mordent) if performance practice is added later.


### 1.6 SpanResult

What a FillStrategy returns for one span.

```python
@dataclass(frozen=True)
class SpanResult:
    notes: tuple[Note, ...]
    metadata: SpanMetadata
```


---

## 2. FillStrategy Protocol

```python
class FillStrategy(Protocol):
    def fill_span(
        self,
        span: SpanBoundary,
        config: VoiceConfig,
        context: VoiceContext,
    ) -> SpanResult: ...
```

### Parameters

- **span**: boundary pitches, offsets, and phrase-position context.
- **config**: voice range, key, metre, genre, character.
- **context**: other voices (keyed by voice_id), own prior notes,
  structural offsets. All immutable. Rebuilt by the pipeline before
  each span call.

### Contract

1. Returned notes must span [span.start_offset, span.end_offset) with no
   gaps and no overlaps.
2. First note must have pitch == span.start_midi (structural tone placement
   is the caller's job; the strategy doesn't move it).
3. All pitches must be within [config.range_low, config.range_high].
4. All durations must be in VALID_DURATIONS_SET.
5. If span.end_midi is None, strategy applies its fallback (see §2.3).
6. If span.end_midi is not None, the last note must arrive at or approach
   span.end_midi. "Approach" means the next structural tone placement
   will land on end_midi — the strategy's last note need not equal it
   (that's the next span's start_midi).
7. No parallel perfect intervals at common onsets with other_voices
   (respecting config.guard_tolerance).
8. No cross-relations within beat window with other_voices.
9. No voice crossing where prohibited.
10. No ugly melodic intervals (augmented 2nd, tritone, major 7th).
11. Leap-step recovery (except structural-to-structural, identified via
    context.structural_offsets).
12. No cross-bar pitch repetition at non-structural boundaries.
13. **fill_span must be deterministic given its inputs.** Variation comes
    from VoiceConfig fields (genre, character) and SpanBoundary fields
    (phrase_bar, is_final_span), not from RNG. (A005, D009, V001.)

Items 7–12 are the strategy's responsibility to prevent (D010). The
audit pass detects violations of these same rules and raises (D001).
When no candidate pitch satisfies all constraints, the strategy uses
the constraint relaxation protocol (§2.1).


### 2.1 Constraint Relaxation Protocol

When no candidate pitch simultaneously satisfies all constraints, the
strategy relaxes them in a fixed order. This order is shared across all
strategies via `select_best_pitch` in `shared/pitch_selection.py`.

**Relaxation priority (strictest last to relax):**

| Priority | Constraint | Relax? |
|----------|-----------|--------|
| 0 | Hard invariants (range, duration, gaps) | Never |
| 1 | Voice crossing | Never |
| 2 | Parallel perfect intervals | Last resort only |
| 3 | Cross-relations | Before parallels |
| 4 | Cross-bar repetition | Before cross-relations |
| 5 | Ugly melodic intervals | Before cross-bar repetition |
| 6 | Consecutive same-direction leaps | Before ugly intervals |
| 7 | Step recovery | First to relax (least audible) |

Rationale: parallel fifths destroy voice independence (the fundamental
sin in counterpoint — Bach would relax almost anything before accepting
them). Cross-relations are contextual; Bach used them deliberately in
chromatic passages. Step recovery is the least audible fault.

```python
def select_best_pitch(
    candidates: tuple[int, ...],
    offset: Fraction,
    config: VoiceConfig,
    context: VoiceContext,
    own_previous: tuple[Note, ...],
) -> int:
    """Select the candidate pitch with fewest/least-severe violations.

    Scores each candidate against the constraint set using the priority
    table above. Returns the candidate with the lowest total penalty.
    Never fails — always returns something within hard invariants.

    Candidates must all be within range (priority 0). The caller is
    responsible for generating only in-range candidates.
    """
```

The strategy generates candidates (stepwise neighbours for walking,
figure realisations for diminution), filters out hard-invariant
violations (range, crossing), then calls `select_best_pitch` on the
survivors. If all candidates violate something, the one violating only
the lowest-priority rule wins.

The audit then fires on whatever violation was accepted. In strict mode
(development) this crashes and identifies the case. In lenient mode
(production) this logs and continues. See §3.


### 2.2 DiminutionFill Fallback Path

DiminutionFill tries figures in preference order:

1. **Preferred figure**: character-appropriate, selected deterministically
   from genre + phrase_bar + span interval.
2. **Alternative figures**: other figures compatible with the span interval,
   tried in a fixed order.
3. **Stepwise fallback**: step diatonically from start_midi toward
   end_midi, checking each pitch via shared counterpoint functions.
   Uses `select_best_pitch` when no clean step exists.

For each candidate figure (steps 1–2), DiminutionFill realises the
pitches and checks each note against counterpoint constraints. If any
note fails and no alternative pitch within the figure's logic resolves
it, the figure is rejected and the next is tried.

Stepwise fallback always produces output. It is correct but bland —
acceptable because correct-and-bland beats plausible-and-wrong (the old
_apply_guards produced the latter).

DiminutionMetadata.used_stepwise_fallback = True when the fallback is
used, making it visible for diagnostics.


### 2.3 end_midi = None Fallback (per strategy)

When end_midi is None (final span, no next-phrase entry known), each
strategy must specify its behaviour. "Decide freely" is not acceptable —
the bass must arrive somewhere harmonically sensible.

| Strategy | end_midi = None behaviour |
|----------|--------------------------|
| DiminutionFill | Hold or step to nearest chord tone of current key |
| WalkingFill | Step toward tonic or fifth of current key |
| PillarFill | Hold structural tone |
| PatternedFill | Complete pattern; final pitch = tonic or fifth |

Without per-beat harmonic data, "harmonically sensible" means chord tone
of the current key. This is a known limitation — see §12.


### 2.4 WalkingFill: Incremental Construction

WalkingFill builds its output incrementally with per-pitch checking.
`fill_span` is not a batch operation internally. The strategy picks
each pitch, checks it against the soprano and prior notes, adjusts if
needed, then picks the next. This interleaved generate-and-check is the
algorithm — it was not a design flaw in the original bass_writer.

The difference from the original: WalkingFill calls shared counterpoint
functions (§7) instead of inline checks, and receives context through
VoiceContext instead of capturing variables from an enclosing scope.
When no clean pitch exists, it uses `select_best_pitch` (§2.1).


---

## 3. Audit Interface

Replaces the old `apply_guards`. Detects faults and raises or reports.
Never fixes. (D001, D008, D010.)

```python
@dataclass(frozen=True)
class AuditViolation:
    """One detected counterpoint or melodic fault."""
    rule: str                   # e.g. "parallel_fifth", "cross_relation"
    offset: Fraction
    pitch: int
    detail: str                 # human-readable description


def audit_voice(
    notes: tuple[Note, ...],
    other_voices: dict[int, tuple[Note, ...]],
    structural_offsets: frozenset[Fraction],
    config: VoiceConfig,
    prior_phrase_tail: Note | None = None,
    strict: bool = True,
) -> list[AuditViolation]:
    """Detect counterpoint and melodic faults.

    Checks (using the same shared functions the strategies use):
    - Parallel 5ths/octaves at common onsets (respecting config.guard_tolerance)
    - Cross-relations within beat window
    - Voice crossing
    - Ugly melodic intervals
    - Cross-bar pitch repetition (non-structural only)
    - Leap-step recovery (except structural-to-structural)
    - Consecutive same-direction leaps
    - Phrase boundary continuity (if prior_phrase_tail provided):
      ugly interval, leap-step, cross-bar repetition at the join

    If strict=True (default): raises AssertionError on first violation.
    Use during development — every failure is a case to examine.

    If strict=False: collects all violations and returns them.
    Use once strategies are mature — output is degraded but playable.
    The returned list gives a queue of cases to investigate.

    Returns empty list if no violations found.

    This is a detection-only pass. If it fires, the fault is in the
    strategy that generated the notes, not in the audit.

    Range assertion is detection (D001), not clamping (L003). The
    strategy must produce in-range pitches; this catches strategy bugs.
    """
```

The audit and the strategies call the same shared functions. The audit
is the strategies' safety net, not their substitute.


---

## 4. Validation Interface

Separate from the audit. Checks invariants that are never voice-interaction
faults — purely about the note sequence's internal consistency.

```python
def validate_voice(
    notes: tuple[Note, ...],
    config: VoiceConfig,
    phrase_start: Fraction,
    phrase_duration: Fraction,
) -> None:
    """Assert structural invariants. Raises AssertionError on failure.

    Checks:
    - All pitches in [config.range_low, config.range_high]
    - All durations in VALID_DURATIONS_SET
    - No gaps or overlaps between consecutive notes
    - Total duration == phrase_duration
    - No melodic intervals exceeding MAX_MELODIC_INTERVAL

    Range assertion is detection (D001), not clamping (L003). The strategy
    must produce in-range pitches; this catches strategy bugs.

    Known limitation: rests would require relaxing the no-gap invariant.
    """
```

Pure assertion function. These are hard invariants, not style rules.


---

## 5. Pipeline Interface

```python
def write_voice(
    structural_tones: tuple[StructuralTone, ...],
    phrase_start: Fraction,
    phrase_duration: Fraction,
    fill_strategy: FillStrategy,
    other_voices: dict[int, tuple[Note, ...]],
    config: VoiceConfig,
    next_entry_midi: int | None = None,
    prior_phrase_tail: Note | None = None,
    strict_audit: bool = True,
) -> WriteResult:
    """Generate a complete voice for one phrase.

    Steps:
    1. Compute structural_offsets from structural_tones.
    2. Build SpanBoundary for each pair of adjacent structural tones
       (plus final span to phrase_start + phrase_duration, using
       next_entry_midi as end_midi if provided).
    3. For each span:
       a. Build VoiceContext with other_voices, accumulated prior notes,
          prior_phrase_tail, and structural_offsets. Immutable; rebuilt
          each iteration (L014).
       b. Call fill_strategy.fill_span(span, config, context) → SpanResult.
       c. Accumulate notes for next iteration's own_prior_notes.
    4. Concatenate all span notes into final sequence.
    5. validate_voice(notes, config, phrase_start, phrase_duration).
       (Hard invariants first — gaps, range, durations.)
    6. audit_voice(notes, other_voices, structural_offsets, config,
       prior_phrase_tail, strict=strict_audit).
       (Counterpoint and melodic style rules.)
    7. Return WriteResult (with any audit violations if lenient mode).
    """
```

No mutable state crosses function boundaries. The accumulated notes are
a growing tuple, rebuilt each iteration (L014).


### WriteResult

```python
@dataclass(frozen=True)
class WriteResult:
    notes: tuple[Note, ...]
    span_metadata: tuple[SpanMetadata, ...]     # one per span, typed
    structural_offsets: frozenset[Fraction]       # for downstream use
    audit_violations: tuple[AuditViolation, ...]  # empty if strict or clean
```

`structural_offsets` is derivable from the input but returned for
convenience — the caller (faults module, enrichment) needs it and
shouldn't recompute it.

`audit_violations` is empty in strict mode (violations raise before
reaching this point) and in clean output. Non-empty only in lenient
mode when the strategy accepted a low-priority constraint violation
via select_best_pitch.


---

## 6. Caller Interface (soprano_writer / bass_writer → write_voice)

The existing writers keep their public signatures unchanged. Internally,
they translate PhrasePlan into voice_writer types and delegate.

### Soprano (Phase 16)

```python
def generate_soprano_phrase(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...] = (),
    lower_notes: tuple[Note, ...] = (),
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
    recall_figure_name: str | None = None,
) -> tuple[tuple[Note, ...], tuple[str, ...]]:
    """Unchanged public signature.

    Internally:
    1. _place_structural_tones(plan, prev_exit_midi) → tuple[StructuralTone, ...]
    2. Build VoiceConfig from plan fields (including genre from plan)
    3. Build DiminutionFill(character, recall_figure_name, ...)
    4. Compute next_entry_midi if degree/key given
    5. result = write_voice(structural_tones, ...,
       other_voices={TRACK_BASS: lower_notes}, ...)
    6. Extract figure_names from result.span_metadata (isinstance DiminutionMetadata)
    7. Return (result.notes, figure_names)
    """
```

### Bass (Phase 17)

```python
def generate_bass_phrase(
    plan: PhrasePlan,
    soprano_notes: tuple[Note, ...],
    prior_bass: tuple[Note, ...] = (),
) -> tuple[Note, ...]:
    """Unchanged public signature.

    Internally:
    1. _place_structural_tones_with_consonance(plan, soprano_notes)
       → tuple[StructuralTone, ...]
    2. Build VoiceConfig from plan fields (with guard_tolerance for texture)
    3. Select strategy: WalkingFill / PillarFill / PatternedFill
       from plan.bass_texture
    4. result = write_voice(structural_tones, ...,
       other_voices={TRACK_SOPRANO: soprano_notes}, ...)
    5. Return result.notes
    """
```


---

## 7. Shared Functions

### 7.1 Counterpoint Functions (shared/counterpoint.py)

These are the single source of truth (L017) for counterpoint rules.
Both strategies and audit_voice call them. All are pure query functions
(bool or int return, no mutation).

#### Existing (in shared/counterpoint.py):

```python
has_cross_relation(pitch, other_notes, offset, beat_unit) -> bool
prevent_cross_relation(pitch, other_notes, offset, beat_unit, key, pitch_range, ceiling) -> int
```

Note: `prevent_cross_relation` returns an alternative pitch. This is a
*generator helper* — it helps the strategy find a non-faulty pitch.
It does not belong in the audit path. Consistent with D010.

#### To extract / create:

```python
def has_parallel_perfect(
    pitch: int,
    offset: Fraction,
    other_voice_notes: tuple[Note, ...],
    own_previous_note: Note | None,
    tolerance: frozenset[int],
) -> bool:
    """True if pitch at offset creates parallel perfect interval with other voice."""

def would_cross_voice(
    pitch: int,
    offset: Fraction,
    other_voices: dict[int, tuple[Note, ...]],
    voice_id: int,
) -> bool:
    """True if pitch at offset crosses another voice.

    Uses voice_id to determine direction: bass must not exceed soprano,
    soprano must not go below bass, etc.
    """

def is_ugly_melodic_interval(
    from_pitch: int,
    to_pitch: int,
) -> bool:
    """True if interval is augmented 2nd, tritone, or major 7th."""

def needs_step_recovery(
    previous_notes: tuple[Note, ...],
    candidate_pitch: int,
    structural_offsets: frozenset[Fraction],
) -> bool:
    """True if the last interval was a leap and candidate doesn't provide
    contrary stepwise recovery. Returns False (no problem) if last interval
    was a step, or if both notes are structural."""

def is_cross_bar_repetition(
    pitch: int,
    offset: Fraction,
    previous_note: Note | None,
    bar_length: Fraction,
    phrase_start: Fraction,
    structural_offsets: frozenset[Fraction],
) -> bool:
    """True if pitch repeats the previous note's pitch across a bar boundary,
    and neither note is structural."""

def has_consecutive_leaps(
    prev_prev_pitch: int | None,
    prev_pitch: int,
    candidate_pitch: int,
    threshold: int = SKIP_SEMITONES,
) -> bool:
    """True if both prev→candidate and prev_prev→prev exceed threshold
    in the same direction. Returns False if prev_prev is None."""
```

#### Prevention helpers (for strategies only):

```python
def find_non_parallel_pitch(
    pitch: int,
    offset: Fraction,
    other_voice_notes: tuple[Note, ...],
    own_previous_note: Note | None,
    tolerance: frozenset[int],
    key: Key,
    pitch_range: tuple[int, int],
) -> int | None:
    """Suggest an alternative pitch that avoids parallel perfects.
    Returns None if no alternative found within range."""
```

Detection functions serve both strategies and audit. Prevention helpers
serve only strategies.


### 7.2 Phrase Zone Helper (shared/phrase_position.py)

```python
def phrase_zone(
    phrase_bar: int,
    total_bars: int,
) -> PHRASE_ZONE:
    """Classify bar position within a phrase.

    Returns "opening", "middle", or "cadential" based on proportional
    position. Ensures consistent interpretation across all strategies.

    - opening: first ~25% of the phrase (establishing key, grounding)
    - middle: ~25%–75% (exploratory, building momentum)
    - cadential: last ~25% (directed, intensifying toward cadence)

    For very short phrases (≤2 bars), opening and cadential may overlap.
    """
```

This is a design choice: the strategy owns the musical interpretation of
phrase position, but this shared helper ensures all strategies use the
same boundary logic. Strategies may further refine within a zone.


### 7.3 Pitch Selection Helper (shared/pitch_selection.py)

`select_best_pitch` as specified in §2.1. Lives in its own module
because it is substantial (~40–60 lines) and has its own test surface.


---

## 8. Testing Architecture

The context-rich VoiceContext creates a tension: strategies need full
visibility to prevent faults (D010), but isolated testing needs minimal
setup. The resolution is two independent testing surfaces.

### Layer 1: Shared counterpoint functions

Tested with minimal, crafted inputs. No strategy, no pipeline.

```python
def test_has_parallel_perfect_detects_parallel_fifths():
    assert has_parallel_perfect(
        pitch=53, offset=Fraction(1),
        other_voice_notes=(Note(offset=Fraction(0), pitch=67, ...), Note(offset=Fraction(1), pitch=72, ...)),
        own_previous_note=Note(offset=Fraction(0), pitch=48, ...),
        tolerance=frozenset(),
    )

def test_is_ugly_melodic_interval_tritone():
    assert is_ugly_melodic_interval(from_pitch=60, to_pitch=66)

def test_needs_step_recovery_after_leap():
    prev = (Note(offset=Fraction(0), pitch=60, ...), Note(offset=Fraction(1, 4), pitch=67, ...))
    assert needs_step_recovery(
        previous_notes=prev, candidate_pitch=69, structural_offsets=frozenset(),
    )
```

### Layer 2: Strategy creative logic

Tested with empty or trivial context. Verifies the strategy's pitch and
rhythm choices, figure selection, span coverage.

```python
def test_diminution_fill_covers_span():
    span = SpanBoundary(start_offset=Fraction(0), start_midi=60, ...,
                        end_offset=Fraction(1), end_midi=64, ...)
    config = VoiceConfig(...)
    context = VoiceContext(
        other_voices={},           # no other voices — all vertical checks pass trivially
        own_prior_notes=(),
        prior_phrase_tail=None,
        structural_offsets=frozenset({Fraction(0), Fraction(1)}),
    )
    result = DiminutionFill(...).fill_span(span=span, config=config, context=context)
    assert result.notes[0].pitch == 60
    assert result.notes[-1].offset + result.notes[-1].duration == Fraction(1)
    assert all(config.range_low <= n.pitch <= config.range_high for n in result.notes)
```

### Layer 3: Strategy counterpoint reactions

Tested with crafted minimal context to trigger specific counterpoint
conflicts. Verifies the strategy avoids the fault (or accepts the
lowest-priority violation via select_best_pitch).

**Enumerated test categories** (2–3 cases each, mostly for WalkingFill):

1. Parallel fifth avoidance at common onsets
2. Parallel octave avoidance at common onsets
3. Cross-relation near chromatic approach tone
4. Voice crossing near range boundary
5. Leap-step recovery when recovery pitch creates a new violation
6. Consecutive same-direction leaps near range boundary
7. Cross-bar repetition at span boundary
8. Ugly interval avoidance (augmented 2nd, tritone, major 7th)
9. Phrase boundary continuity (prior_phrase_tail interactions)
10. Constraint relaxation — no clean pitch exists, verify least-bad selection

Budget: 20–30 Layer 3 tests total.

```python
def test_diminution_avoids_parallel_fifth():
    soprano = (Note(offset=Fraction(1, 2), pitch=72, duration=Fraction(1, 2), voice=0),)
    context = VoiceContext(
        other_voices={TRACK_SOPRANO: soprano},
        own_prior_notes=(Note(offset=Fraction(0), pitch=48, ...),),
        prior_phrase_tail=None,
        structural_offsets=frozenset({Fraction(0), Fraction(1)}),
    )
    result = DiminutionFill(...).fill_span(span=..., config=..., context=context)
    mid_note = next(n for n in result.notes if n.offset == Fraction(1, 2))
    assert abs(mid_note.pitch - 72) % 12 != 7
```

### Layer 4: Pipeline integration

Existing end-to-end tests (16 genre/key combinations). These run the
full chain: caller → write_voice → strategy → audit → validate. They
don't change. If they pass, the wiring is correct.

Expect initial failures in Phase 16 where the old _apply_guards was
patching faults. Each failure reveals a case DiminutionFill must learn
to prevent. This is by design, not regression. (RF-9.)

### Summary

| Layer | What's tested | Context needed | Speed |
|-------|--------------|----------------|-------|
| 1. Shared functions | Detection rules | 2–3 crafted notes | Fast |
| 2. Strategy creative | Pitch/rhythm choices | Empty context | Fast |
| 3. Strategy counterpoint | Fault avoidance | 1–2 crafted notes | Fast |
| 4. Pipeline integration | Full wiring | Full phrase | Slow |

Layers 1–3 are unit tests. Layer 4 is integration. A strategy bug
should be catchable at layer 2 or 3 before reaching layer 4.


---

## 9. File Layout

```
builder/
    voice_writer.py          — write_voice pipeline, validate_voice
    voice_types.py           — StructuralTone, SpanBoundary, VoiceConfig,
                               VoiceContext, SpanResult, SpanMetadata (base),
                               WriteResult, AuditViolation, FillStrategy protocol,
                               GENRES/CHARACTERS/PHRASE_ZONE Literals
    strategies/
        __init__.py
        diminution.py        — DiminutionFill, DiminutionMetadata (Phase 16, 150–200 lines)
        walking.py           — WalkingFill, WalkingMetadata (Phase 17, 300–350 lines)
        pillar.py            — PillarFill, PillarMetadata (Phase 17, 40–60 lines)
        patterned.py         — PatternedFill, PatternedMetadata (Phase 17, 60–80 lines)
shared/
    counterpoint.py          — detection functions + prevention helpers
                               (single source of truth for all rules)
    pitch_selection.py       — select_best_pitch (constraint relaxation, 40–60 lines)
    phrase_position.py       — phrase_zone helper
```


---

## 10. Design Goals

### Code quality is inversely proportional to the number of conditional statements

Ideal code has no conditional statements. Every `if` is a question the
code is asking at runtime that should have been answered at design time.
The voice_writer design eliminates conditionals by:

- **Typed data contracts**: SpanBoundary always has start_key, start_midi,
  end_offset. No `if X is not None` checks on data that is structurally
  always present.
- **Span-based iteration**: the pipeline builds spans with explicit
  boundaries. Strategies never index into structural tone lists, never
  scan forward for the next target, never track pointers.
- **Strategy dispatch**: texture selection happens once in the caller.
  No three-way branching inside generation loops.
- **Shared functions**: counterpoint rules exist once. No per-branch
  reimplementation with slight variations.
- **Asserts replace ifs**: when a condition reflects a system invariant
  (not a domain branch), assert it. If it fires, it's a bug upstream,
  not a case to handle.
- **Prevent, don't fix**: strategies produce correct output. No post-pass
  that detects faults and patches them with fallback chains.
- **Typed enums over bare strings**: genre, character, and phrase_zone
  are Literals, not str. No misspelling bugs, no invalid-value branches.

When reviewing code, count the `if` statements. If the count is rising,
the design is deteriorating. If a new `if` is needed, ask: what design
change would make this condition structurally impossible?

### Musical intent bottleneck

The code receives musical direction through VoiceConfig fields: genre,
character, cadence_type, key, is_minor, and through SpanBoundary fields:
phrase_bar, total_bars, is_final_span. The conductor's rich musical
briefs (phrase arc, tension/release, idiomatic practice) compress into
these discrete parameters.

This is a known limitation. The code cannot hear; it receives typed
parameters. The phrase_zone helper and genre field are the current
channels. Future extensions: per-span intensity (scalar 0.0–1.0
governing chromaticism and dissonance density), per-beat harmonic data
on VoiceContext (see §12).

---

## 11. Design Decisions Record

### A. VoiceContext bundle — DECIDED: bundle
Flat parameters replaced by immutable VoiceContext dataclass.

### B. SpanBoundary — DECIDED: yes
Span data bundled into frozen dataclass. Protocol has three parameters.

### C. No mutable state — DECIDED: immutable rebuild per span
VoiceContext.own_prior_notes is a tuple, rebuilt by the pipeline before
each span call. No closures, no mutable captures (L014).

### C2. phrase_start on VoiceConfig — DECIDED: yes
Strategies need phrase_start for bar boundary computation.

### D. next_entry_midi on write_voice — DECIDED: explicit parameter
Not a phantom structural tone. Clean and explicit.

### E. SpanMetadata — DECIDED: typed class hierarchy
Base class + per-strategy frozen dataclass subclasses.

### F. structural_offsets on WriteResult — DECIDED: included
Derivable but returned for convenience.

### G. No apply_guards post-pass — DECIDED: audit_voice (detect only)
D001, D008, D010. Two-mode: strict (raise) or lenient (report).

### H. Shared counterpoint functions — DECIDED: detect + prevent helpers
Detection serves both strategies and audit. Prevention serves only
strategies. Single source of truth (L017).

### I. Phrase boundary continuity — DECIDED: prior_phrase_tail
One Note on VoiceContext. Enough for leap-step, cross-bar, ugly interval.

### J. phrase_start on VoiceConfig — DECIDED: yes

### K. cadence_type on VoiceConfig — DECIDED: yes

### L. has_consecutive_leaps in shared counterpoint — DECIDED: yes

### M. Upstream data contract fixes — DECIDED: do in Phase 16
Four fixes eliminating 32 downstream conditionals. See if_audit_never_none.md.

### N. other_voices keyed by voice_id — DECIDED: dict[int, tuple[Note, ...]]
Not positional tuple. Supports arbitrary voice counts without refactor.

### O. Constraint relaxation protocol — DECIDED: shared select_best_pitch
Fixed priority order across all strategies. See §2.1.

### P. Audit two-mode — DECIDED: strict parameter
strict=True (raise) during development. strict=False (report) once mature.

### Q. DiminutionFill fallback — DECIDED: figure rejection → stepwise
Try figures in order → stepwise fallback → select_best_pitch. See §2.2.

### R. genre on VoiceConfig — DECIDED: Literal type
Shapes rhythmic weight, leap frequency, dance character.

### S. character typing — DECIDED: Literal
Closed set: plain, expressive, energetic, bold, ornate.

### T. phrase_zone shared helper — DECIDED: yes
Consistent phrase position interpretation across strategies. See §7.2.

---

## 12. Known Limitations and Future Extensions

These are named explicitly so Claude Code doesn't stumble into the gaps
and invent bad workarounds.

1. **No per-beat harmonic data.** The system lacks beat-level chord
   information. When this becomes available, it enters via VoiceContext
   (rebuilt per span). Strategies currently treat pitches as scale
   degrees or intervals, not as chord members. A musician would think
   harmonically — this gap produces correct counterpoint but not yet
   harmonic voice-leading.

2. **Rests not possible.** fill_span requires no gaps in returned notes.
   Rests would require relaxing the no-gap invariant in validate_voice.

3. **No ornaments.** SpanMetadata is the natural extension point for
   trill markers, mordent intent, appoggiatura, etc.

4. **Musical intent compression.** The conductor's rich musical briefs
   compress into discrete VoiceConfig/SpanBoundary parameters. Future:
   per-span intensity scalar, harmonic tension indicator.

5. **No inner voice awareness.** Currently two voices only. The dict-keyed
   other_voices and voice_id system supports arbitrary voice counts, but
   inner-voice strategies (ChordFill) and their interaction rules are
   not yet designed.
