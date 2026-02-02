# Phase 6: VoiceWriter + WritingStrategy Design

## Status

v0.1.0 | 2026-02-01 | Initial design, all questions resolved

---

## Purpose

Replace the old figuration + realisation pipeline (~200KB) with a
voice-agnostic writer driven entirely by the plan.  The old pipeline
makes compositional decisions (bar_context.py infers density, hemiola,
cadence approach, etc.) and applies downstream fixes
(adjust_downbeat_consonance).  The new pipeline receives all decisions
in the VoicePlan and executes them mechanically.

---

## Entry Point

```python
# builder/compose.py (~30 lines)

def compose_voices(plan: CompositionPlan) -> Composition:
    """Execute a CompositionPlan to produce a Composition."""
    prior_voices: dict[str, tuple[Note, ...]] = {}
    for voice_plan in plan.voice_plans:
        writer: VoiceWriter = VoiceWriter(
            plan=voice_plan,
            home_key=plan.home_key,
            anchors=plan.anchors,
            prior_voices=prior_voices,
        )
        notes: tuple[Note, ...] = writer.compose()
        prior_voices[voice_plan.voice_id] = notes
    return Composition(
        voices=prior_voices,
        metre=plan.voice_plans[0].metre,
        tempo=plan.tempo,
        upbeat=plan.upbeat,
    )
```

`voice_plans` is already sorted by `composition_order`.  Each writer
sees all previously-completed voices.  Pure sequential execution, no
iteration, no backtracking.

---

## VoiceWriter

One class, one instance per voice.  Produces a `tuple[Note, ...]`.

### Responsibilities

| Responsibility | How |
|---|---|
| Iterate sections and gaps | Loop over `voice_plan.sections` |
| Resolve anchor pitches by role | Read `upper_pitch` or `lower_pitch` per section role |
| Dispatch to writing strategy | Strategy selected by `GapPlan.writing_mode` |
| Check counterpoint against prior voices | Per-note filtering during strategy execution |
| Check junctions between gaps | After each gap, validate connection to next anchor |
| Check actuator range | MIDI derivation + range assert |
| Handle anacrusis | Before first section |
| Handle section sequencing | Independent vs Fortspinnung |
| Assemble final notes | Collect, sort by offset, freeze as tuple |

### Class shape

```python
# builder/voice_writer.py (~100 lines)

class VoiceWriter:
    def __init__(
        self,
        plan: VoicePlan,
        home_key: Key,
        anchors: tuple[PlanAnchor, ...],
        prior_voices: dict[str, tuple[Note, ...]],
    ) -> None: ...

    def compose(self) -> tuple[Note, ...]: ...

    # ── Section-level ─────────────────────────────────────
    def _compose_section(
        self,
        section: SectionPlan,
    ) -> list[Note]: ...

    def _compose_gap(
        self,
        gap: GapPlan,
        source_pitch: DiatonicPitch,
        target_pitch: DiatonicPitch,
        gap_offset: Fraction,
    ) -> list[Note]: ...

    # ── Anchor reading ────────────────────────────────────
    def _pitch_for_role(
        self,
        anchor: PlanAnchor,
        role: Role,
    ) -> DiatonicPitch: ...

    def _degree_for_role(
        self,
        anchor: PlanAnchor,
        role: Role,
    ) -> int: ...

    # ── Checking ──────────────────────────────────────────
    def _check_candidate(
        self,
        pitch: DiatonicPitch,
        offset: Fraction,
        duration: Fraction,
    ) -> bool: ...

    # ── Conversion ────────────────────────────────────────
    def _to_note(
        self,
        pitch: DiatonicPitch,
        offset: Fraction,
        duration: Fraction,
    ) -> Note: ...

    # ── Anacrusis ─────────────────────────────────────────
    def _compose_anacrusis(self) -> list[Note]: ...
```

### Anchor reading by role

```
SCHEMA_UPPER  → anchor.upper_pitch, anchor.upper_degree
SCHEMA_LOWER  → anchor.lower_pitch, anchor.lower_degree
IMITATIVE     → see §IMITATIVE below
HARMONY_FILL  → see §HARMONY_FILL below
```

For schema-bound roles, the anchor pitch is the DiatonicPitch set
during planning (tessitura-placed).  The writer reads it directly.

### State carried across gaps

The writer carries minimal sequential state:

| State | Purpose |
|---|---|
| `_prev_figure_name: str` | Avoid immediate figure repetition |
| `_prev_ended_with_leap: bool` | Trigger compensation in next gap |
| `_prev_exit_pitch: DiatonicPitch` | Junction checking |
| `_rng: Random` | Seeded from `voice_plan.seed` |

All four reset at section boundaries (each SectionPlan starts fresh).

### Note assembly

Each `_compose_gap` returns a `list[Note]` with offsets relative to
the gap's start.  The section composer adds the section's absolute
offset.  The voice composer concatenates all sections.  Final sort
by offset, freeze as `tuple[Note, ...]`.

Note fields:
- `offset`: absolute position in whole notes from bar 1 beat 1
- `pitch`: MIDI integer, derived from `home_key.diatonic_to_midi(dp)`
- `duration`: in whole notes (from rhythm template, multiplied by gate 0.95 per L013)
- `voice`: integer index from composition_order (for faults.py compatibility)
- `lyric`: trace string (schema name + figure name, for debugging)

---

## WritingStrategy

Abstract base class.  One method.

```python
# builder/writing_strategy.py (~20 lines)

class WritingStrategy(ABC):
    @abstractmethod
    def fill_gap(
        self,
        gap: GapPlan,
        source_pitch: DiatonicPitch,
        target_pitch: DiatonicPitch,
        home_key: Key,
        metre: str,
        rng: Random,
        candidate_filter: Callable[[DiatonicPitch, Fraction], bool],
    ) -> tuple[tuple[DiatonicPitch, Fraction], ...]:
        """Return (pitch, duration) pairs filling the gap.

        candidate_filter: called by the strategy for each candidate
        note.  Returns True if the note passes counterpoint and range
        checks.  The strategy must not emit notes that fail the filter.
        """
        ...
```

### candidate_filter callback

The VoiceWriter passes a closure that checks:
1. Parallel fifths/octaves/unisons with all prior voices at this offset
2. Direct fifths/octaves
3. Dissonance on strong beats
4. Actuator range
5. Voice overlap

The strategy calls this for each candidate note before committing.
If all candidates for a gap fail, the strategy returns the best
available (source_pitch held for gap_duration — the "hold" fallback).

**Hold is not a fix.** It is the simplest valid realisation: a note
at the anchor pitch held for the gap duration.  It satisfies all
counterpoint rules trivially (the anchor is already validated by the
planner).  If the strategy must fall back to hold for more than one
gap in a section, it logs a warning.

### Why callback, not return-and-check

If the strategy returns all candidates and the writer filters, the
strategy cannot respond to rejections.  With the callback, the strategy
can try alternative figures immediately when a candidate fails, without
re-entering the writer.

---

## Concrete Strategies

### FigurationStrategy

The main strategy.  Replaces the old figurate.py + selector.py +
junction.py pipeline.

```python
# builder/figuration_strategy.py (~80-100 lines)

class FigurationStrategy(WritingStrategy):
    def __init__(self, vocabulary: tuple[Figure, ...]) -> None: ...

    def fill_gap(self, ...) -> tuple[tuple[DiatonicPitch, Fraction], ...]: ...

    def filter_figures(
        self,
        gap: GapPlan,
        figures: tuple[Figure, ...],
    ) -> list[Figure]: ...

    def expand_figure(
        self,
        figure: Figure,
        source_pitch: DiatonicPitch,
        target_pitch: DiatonicPitch,
        gap: GapPlan,
        home_key: Key,
        metre: str,
        candidate_filter: Callable[[DiatonicPitch, Fraction], bool],
    ) -> tuple[tuple[DiatonicPitch, Fraction], ...] | None: ...

    def _get_rhythm(
        self,
        note_count: int,
        gap: GapPlan,
        metre: str,
    ) -> tuple[Fraction, ...]: ...
```

`filter_figures` and `expand_figure` are public so the section
composer can use them for Fortspinnung sequencing (see §Section
Sequencing below).

#### Filter pipeline

Simplified from the old 13-step pipeline.  The GapPlan carries
pre-resolved values, so inference steps vanish:

| Step | Old pipeline | New pipeline |
|---|---|---|
| 1. Compute interval | bar_context.py infers | `gap.interval` (pre-computed) |
| 2. Filter by interval | selector.py | Same — match `figure.contour` to `gap.interval` |
| 3. Filter by direction | selector.py | Same — match to `gap.ascending` |
| 4. Filter by tension | selector.py | Same — match to `gap.harmonic_tension` |
| 5. Filter by character | bar_context.py infers position | `gap.character` (pre-computed) |
| 6. Filter by density | bar_context.py infers | `gap.density` (pre-computed) |
| 7. Filter by minor | key lookup | `home_key.mode == "minor"` |
| 8. Filter by compensation | tracked in writer | `_prev_ended_with_leap` from writer state |
| 9. Misbehaviour | selector.py | Deferred to planner (Phase 7) |
| 10. Sort by weight | selector.py | Same |
| 11. Select via RNG | selector.py | Same |
| 12. Check junction | junction.py | Same, but with DiatonicPitch (no mod-7 wrapping) |
| 13. Candidate filter | — (NEW) | callback to VoiceWriter for counterpoint check |

Steps 1, 5, 6 collapse from ~60KB of context inference to direct
field reads.  Step 13 is new — the old pipeline did not check
counterpoint during figure selection (that was post-hoc in faults.py).

#### Figure expansion

Old: `start_degree + figure.degrees[i]` with mod-7 wrapping.
New: `source_pitch.transpose(figure.degrees[i])` — signed offset,
no wrapping.

```python
for i, offset in enumerate(figure.degrees):
    pitch: DiatonicPitch = source_pitch.transpose(offset)
    duration: Fraction = durations[i]
    if candidate_filter(pitch, gap_offset + elapsed):
        notes.append((pitch, duration))
    else:
        # Try next figure candidate
        break
```

If the inner loop breaks (counterpoint rejection), the strategy
tries the next figure in the sorted candidate list.  If all figures
are exhausted, fall back to hold.

#### Rhythm templates

Existing rhythm template system (loader.py, rhythm_calc.py) is
reused.  The strategy calls `get_rhythm_template(note_count, metre,
overdotted)` exactly as the old realiser does.  Hemiola templates
selected when `gap.use_hemiola` is True.

### CadentialStrategy

Thin wrapper around FigurationStrategy that uses the cadential
figure vocabulary instead of the main vocabulary.

```python
# builder/cadential_strategy.py (~30 lines)

class CadentialStrategy(FigurationStrategy):
    def __init__(self) -> None:
        super().__init__(vocabulary=load_cadential_figures())
```

Uses cadential figures from `cadential.yaml`.  Same filter pipeline,
same expansion.  The GapPlan's `writing_mode = CADENTIAL` tells the
writer to dispatch here.

### PillarStrategy

Trivial.  Holds the source anchor pitch for the gap duration.

```python
# builder/pillar_strategy.py (~15 lines)

class PillarStrategy(WritingStrategy):
    def fill_gap(self, ...) -> tuple[tuple[DiatonicPitch, Fraction], ...]:
        return ((source_pitch, gap.gap_duration),)
```

Used for sustained bass notes, held tones, pedal points.

### StaggeredStrategy

Delayed entry.  Rests for a portion of the gap, then fills the
remainder with figuration.

```python
# builder/staggered_strategy.py (~25 lines)

class StaggeredStrategy(WritingStrategy):
    def __init__(self, fill_strategy: FigurationStrategy) -> None:
        self._fill = fill_strategy

    def fill_gap(self, ...) -> tuple[tuple[DiatonicPitch, Fraction], ...]:
        delay: Fraction = _compute_delay(gap.start_beat, metre)
        remaining: Fraction = gap.gap_duration - delay
        adjusted_gap: GapPlan = _with_duration(gap, remaining)
        fill: tuple[...] = self._fill.fill_gap(
            adjusted_gap, source_pitch, target_pitch,
            home_key, metre, rng, candidate_filter,
        )
        return fill  # Offset adjustment handled by caller
```

The delay creates silence (no Note emitted).  The caller
(VoiceWriter._compose_gap) adds the delay to all offsets in the
returned notes.

### Future strategies (stubs)

WALKING and ARPEGGIATED assert-fail in the writer if received.  They
become real in a future phase.  No code for them now.

---

## Section Sequencing (Fortspinnung)

`SectionPlan.sequencing` controls how figures relate across gaps
within a section.

### independent

Default.  Each gap calls the strategy independently.  No figure
memory across gaps (beyond the writer's `_prev_figure_name` for
avoidance and `_prev_ended_with_leap` for compensation).

### Fortspinnung strategies

For non-independent sequencing, the section composer uses the
two-phase select/expand approach:

1. Calls `strategy.filter_figures(gap_0)` + RNG selection to get
   the Figure object for gap 0.
2. Calls `strategy.expand_figure(figure, ...)` to realise gap 0.
3. For gaps 1, 2, ...: applies the named transform to the Figure,
   then calls `strategy.expand_figure(transformed, ...)`.

| Strategy | Transform for gap N (N > 0) |
|---|---|
| `repeating` | Transpose gap-0 figure to gap-N's anchor interval. Exact shape preserved. |
| `static` | Re-use gap-0 figure unchanged (transposition = 0). For pedal/prolongation. |
| `accelerating` | Gap 0: full figure. Gap 1: full figure transposed. Gap 2+: fragment of figure transposed. Creates momentum. |
| `relaxing` | Gap 0: full figure. Subsequent gaps: progressively simpler (fewer notes, longer durations). |
| `dyadic` | Even gaps: figure A. Odd gaps: contrasting figure B (selected independently at gap 1). Call-response. |

All transforms use `transpose_figure(figure, interval)` from the
existing sequencer.py.  Fragmentation uses `fragment_figure(figure)`.

The transformed figure is still subject to counterpoint filtering
via the candidate_filter callback.  If a transformed figure fails
filtering, the section falls back to independent selection for that
gap.

### Implementation location

Sequencing logic lives in VoiceWriter._compose_section, not in the
strategies.  The strategy fills individual gaps; the section composer
controls how gaps relate.  This keeps the strategy interface clean.

---

## IMITATIVE Role

When `section.role == Role.IMITATIVE`:

The voice does not read anchor pitches.  Instead it reads notes
from the followed voice, transposes by `section.follow_interval`,
and delays by `section.follow_delay`.

```python
def _compose_imitative_section(
    self,
    section: SectionPlan,
) -> list[Note]:
    source_voice: str = section.follows
    source_notes: tuple[Note, ...] = self._prior_voices[source_voice]
    interval: int = section.follow_interval   # diatonic steps
    delay: Fraction = section.follow_delay     # whole notes
    result: list[Note] = []
    for note in source_notes:
        if not _in_section_range(note.offset, section, ...):
            continue
        dp: DiatonicPitch = self._home_key.midi_to_diatonic(note.pitch)
        transposed: DiatonicPitch = dp.transpose(interval)
        new_offset: Fraction = note.offset + delay
        if self._check_candidate(transposed, new_offset, note.duration):
            result.append(self._to_note(transposed, new_offset, note.duration))
    return result
```

This produces a strict canonic imitation.  The counterpoint filter
ensures no parallel fifths or dissonances arise from the transposition.

Notes from the followed voice that fall outside the section's gap
range are excluded.  The delay shifts all onsets forward.

### Limitation

Strict imitation only.  Free imitation (motivic allusion without
note-for-note copying) is a future enhancement — it would require
a separate strategy that takes the source voice's notes as reference
material rather than copying them.

---

## HARMONY_FILL Role

When `section.role == Role.HARMONY_FILL`:

The voice fills in chord tones not already covered by schema-bound
and imitative voices.  Not needed for 2-voice invention.  Deferred
to a future phase.  The writer asserts on receiving HARMONY_FILL.

---

## Counterpoint Checking

The writer needs per-note checking against all prior voices.  This
is different from faults.py (which runs post-hoc on completed output).

### What to check (per candidate note)

| Check | Input | Rule |
|---|---|---|
| Parallel 5th/8ve/unison | Candidate + prior note at same offset, previous offset pair | Both voices move to perfect interval in same direction |
| Direct 5th/8ve | Candidate + prior note, motion type | Contrary or oblique motion required if arriving at perfect interval |
| Strong-beat dissonance | Candidate + prior note, beat strength | Consonance required on strong beats unless prepared |
| Actuator range | MIDI of candidate | `actuator_range.low <= midi <= actuator_range.high` |
| Voice overlap | Candidate pitch vs prior voice's previous pitch | No crossing into pitch just vacated |

### Implementation

```python
# builder/voice_checks.py (~80 lines)

def check_parallels(
    prev_upper: int,   # MIDI
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
) -> bool: ...

def check_direct_motion(
    prev_upper: int,
    prev_lower: int,
    curr_upper: int,
    curr_lower: int,
) -> bool: ...

def check_strong_beat_consonance(
    upper_midi: int,
    lower_midi: int,
    offset: Fraction,
    metre: str,
) -> bool: ...

def check_range(
    midi: int,
    actuator_range: Range,
) -> bool: ...
```

Reuses the logic from existing `builder/counterpoint.py` — those
functions are pure and correct.  The new module wraps them with
the DiatonicPitch → MIDI derivation step.

### Prior-voice lookup

The writer needs to find prior-voice notes at a given offset.  Build
a `dict[Fraction, list[int]]` mapping offset → list of MIDI pitches
for all prior voices.  O(1) lookup per candidate.  Built once when
VoiceWriter is constructed (prior voices are immutable).

```python
self._prior_at_offset: dict[Fraction, list[int]] = {}
for voice_notes in prior_voices.values():
    for note in voice_notes:
        self._prior_at_offset.setdefault(note.offset, []).append(note.pitch)
```

For parallel/direct checks, we also need the previous offset's
pitches.  The index stores both.

---

## Junction Checking

Between consecutive gaps (gap N → gap N+1), the writer validates:

| Check | Rule |
|---|---|
| Grotesque leap | `abs(midi_a - midi_b) <= 19` (< octave + fifth) |
| Consecutive leaps | Two leaps > 4 semitones same direction forbidden |
| Ugly interval | Augmented/diminished intervals forbidden (requires MIDI derivation) |

Existing `junction.py` logic is correct but uses mod-7 degrees.  The
new version uses DiatonicPitch → MIDI derivation for exact interval
measurement.

Junction checking happens in VoiceWriter._compose_section after each
gap.  If the junction from the last figure note to the next anchor
fails, the strategy re-fills the gap with the next candidate figure.

---

## Figure Vocabulary

### Current state

Figures are loaded from YAML by `builder/figuration/loader.py`.  The
`Figure` type has `degrees: tuple[int, ...]` with values that are
signed offsets from the starting degree.

### Required changes

1. **Confirm degree semantics.**  Inspect the actual YAML before
   coding 6b to verify degrees are signed offsets.  If unsigned,
   convert to signed offsets during loading.

2. **Reuse loader.py.**  The figure loading code is tested and correct.
   Import from `builder.figuration.loader` (do not move yet — that
   module survives until Phase 8 deletes the old pipeline).

3. **Reuse rhythm templates.**  Same — import from
   `builder.figuration.realiser` and `builder.figuration.rhythm_calc`.

### Vocabulary sources

| WritingMode | Vocabulary source |
|---|---|
| FIGURATION | `figurations.yaml` via `get_diminutions()` |
| CADENTIAL | `cadential.yaml` via `select_cadential_figure()` |
| PILLAR | No vocabulary (single held note) |
| STAGGERED | `figurations.yaml` for the fill portion |

---

## Module Structure

```
builder/
  compose.py                   # compose_voices() entry point (~30 lines)
  voice_writer.py              # VoiceWriter class (~100 lines)
  writing_strategy.py          # WritingStrategy ABC (~20 lines)
  figuration_strategy.py       # FigurationStrategy (~100 lines)
  cadential_strategy.py        # CadentialStrategy (~30 lines)
  pillar_strategy.py           # PillarStrategy (~15 lines)
  staggered_strategy.py        # StaggeredStrategy (~25 lines)
  voice_checks.py              # Counterpoint/range checking (~80 lines)
  # ── Existing (unchanged) ──
  figuration/                  # Old pipeline — survives until Phase 8
  counterpoint.py              # Existing pure functions — reused
  types.py                     # Note, Composition, Anchor, etc.
  faults.py                    # Guard — unchanged
  io.py                        # Output — unchanged
  musicxml_writer.py           # Output — unchanged
  ...
```

New code: ~400 lines across 7 files.  Old pipeline (~200KB) stays
untouched until Phase 8.

---

## Data Flow

```
CompositionPlan
  │
  ├─ home_key ──────────────────────────────────────────┐
  ├─ anchors ───────────────────────────────────────────┤
  │                                                     │
  └─ voice_plans[0]                                     │
       │                                                │
       ├─ sections[0]                                   │
       │    ├─ role → _pitch_for_role(anchor) ──────────┤
       │    ├─ sequencing → _compose_section logic      │
       │    └─ gaps[0]                                  │
       │         ├─ writing_mode → strategy dispatch    │
       │         ├─ interval, ascending, density, ...   │
       │         │   → strategy.filter_figures()        │
       │         ├─ gap_duration, use_hemiola, ...      │
       │         │   → strategy._get_rhythm()           │
       │         └─ ─── strategy.fill_gap() ──────────→ │
       │              candidate_filter(pitch, offset) ←─┤
       │              → [(DiatonicPitch, Fraction), ...]│
       │              → [Note, ...]                     │
       │                                                │
       └─ anacrusis → _compose_anacrusis()              │
                                                        │
  prior_voices ─────────────────────────────────────────┘
       (grows after each voice completes)

  → Composition(voices=..., metre=..., tempo=..., upbeat=...)
```

---

## Implementation Order

Phase 6 is large.  Break into sub-phases to avoid MCP timeouts
and allow testing between steps.

### 6a: Skeleton + PillarStrategy

- `compose.py`: entry point, loops voice_plans.
- `voice_writer.py`: VoiceWriter with compose(), _compose_section
  (independent only), _compose_gap, _pitch_for_role, _to_note.
  No counterpoint checking yet.
- `writing_strategy.py`: WritingStrategy ABC.
- `pillar_strategy.py`: PillarStrategy (hold source pitch).
- `voice_checks.py`: check_range only.

**Test:** Build a CompositionPlan by hand with all PILLAR gaps.
Run compose_voices.  Output should be a Composition with held notes
at each anchor pitch.  Verify MIDI values match expected.

### 6b: FigurationStrategy (core)

- `figuration_strategy.py`: Figure filtering, selection, expansion.
  Reuse loader.py for vocabulary.  Reuse rhythm templates.
  No counterpoint callback yet (pass `lambda: True`).

**Test:** Build a plan with FIGURATION gaps.  Run compose_voices.
Output should contain figured notes.  Inspect manually for sanity.

### 6c: Counterpoint checking

- `voice_checks.py`: Full implementation — parallels, direct motion,
  dissonance, range, overlap.
- Wire candidate_filter callback into VoiceWriter._check_candidate.
- Build prior-voice offset index.

**Test:** Two-voice plan.  First voice (PILLAR).  Second voice
(FIGURATION).  Verify no parallel fifths in output.

### 6d: Junction checking + sequencing

- Junction validation between gaps.
- Section sequencing: repeating, accelerating, relaxing, static,
  dyadic transforms.
- CadentialStrategy, StaggeredStrategy.

**Test:** Full plan matching current pipeline's structure.  Compare
with old pipeline output for musical plausibility.

### 6e: Anacrusis + IMITATIVE

- VoiceWriter._compose_anacrusis.
- VoiceWriter._compose_imitative_section.

**Test:** Two-voice invention with imitative exordium.

---

## Resolved Questions

### 1. Figure degree semantics

**Resolved: inspect YAML before coding 6b.**  The design assumes
signed offsets.  If the YAML uses unsigned scale degrees, the loader
converts to signed offsets during loading.  Architectural risk: none.

### 2. CompositionPlan additions

**Resolved: add `tempo: int` and `upbeat: Fraction` to
CompositionPlan.**  Both are planning decisions.  Already applied to
`shared/plan_types.py` and `test_plan_contract.py`.

### 3. Note.voice field

**Resolved: keep `int` (composition_order).**  faults.py indexes by
integer throughout.  Change to string id in Phase 9 when faults.py
is rewritten.  Avoids coupling Phase 6 to faults.py changes.

### 4. Strategy instantiation

**Resolved: once per VoiceWriter.**  FigurationStrategy and
CadentialStrategy load vocabulary in `__init__`, reused for all gaps.
PillarStrategy and StaggeredStrategy are stateless.

### 5. Fortspinnung figure memory

**Resolved: two-phase select/expand.**  FigurationStrategy exposes
`filter_figures()` and `expand_figure()` as public methods.  The
section composer calls `filter_figures` + `select_figure` to get
the Figure object, applies sequencing transforms (transpose,
fragment), then calls `expand_figure`.  The `fill_gap` ABC method
remains single-phase for strategies that don't need sequencing
(Pillar, Staggered).  Fortspinnung is a section-composer concern.

### 6. Misbehaviour

**Resolved: move to planner (Phase 7).**  The planner occasionally
relaxes a GapPlan's `character` or `density` using its RNG seed.
The writer applies filters strictly as specified.  The old
`apply_misbehaviour` function is deleted in Phase 8.

---

## Dependencies on Existing Code

| Module | What we use | Status |
|---|---|---|
| `builder/figuration/loader.py` | `get_diminutions()`, `get_rhythm_templates()`, `get_hemiola_templates()` | Reuse as-is |
| `builder/figuration/types.py` | `Figure`, `RhythmTemplate` | Reuse as-is |
| `builder/figuration/rhythm_calc.py` | `compute_rhythmic_distribution()` | Reuse as-is |
| `builder/figuration/sequencer.py` | `transpose_figure()`, `fragment_figure()` | Reuse as-is |
| `builder/figuration/selection.py` | `sort_by_weight()`, `select_figure()` | Reuse as-is |
| `builder/counterpoint.py` | `is_consonant()`, `is_perfect()`, `interval_class()` | Reuse as-is |
| `shared/plan_types.py` | All plan types | Phase 5 output |
| `shared/diatonic_pitch.py` | `DiatonicPitch` | Phase 5 output |
| `shared/key.py` | `Key`, `diatonic_to_midi()`, `midi_to_diatonic()` | Phase 5 output |
| `shared/voice_types.py` | `Role`, `Range` | Phase 2 output |

No modifications to existing code in Phase 6.  All new files.

---

## What This Does NOT Do

| Item | Where |
|---|---|
| Produce VoicePlans from the existing planner | Phase 7 |
| Delete old figuration pipeline | Phase 8 |
| Update faults.py for N-voice checking | Phase 9 |
| Implement WALKING/ARPEGGIATED strategies | Future phase |
| Implement HARMONY_FILL role | Future phase |
| Implement free imitation | Future phase |

---

## Document History

| Date | Change |
|------|--------|
| 2026-02-01 | v0.1.0: Initial design, all questions resolved |
