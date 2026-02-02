# Phase 5: VoicePlan Contract Design

## Status

v0.3.0 | 2026-02-01 | Role per section, compound melody, faults contract

---

## Purpose

Define the data structures the planner hands to each voice writer.
Every compositional decision lives in the plan.  The writer makes
zero compositional choices — it selects figures from a filtered
candidate set and realises them mechanically.

This document is the specification for Phase 5 of revision_plan.md.

---

## DiatonicPitch

All pitch representation in the plan and writer uses a single linear
integer counting diatonic steps from a reference point.  No mod-7
wrapping.  Analogous to MIDI (which counts semitones) but counting
scale steps.

```python
@dataclass(frozen=True)
class DiatonicPitch:
    """Diatonic pitch as linear step count, key-relative.

    step counts scale degrees from the tonic.  step 0 = tonic at
    the lowest representable octave.  Always relative to the home key
    of the composition — never to a local key area.

    Arithmetic on steps is always meaningful: subtraction gives a
    signed diatonic interval, addition transposes.  No mod-7 ambiguity.
    """
    step: int

    @property
    def degree(self) -> int:
        """Scale degree 1-7."""
        return (self.step % 7) + 1

    @property
    def octave(self) -> int:
        """Diatonic octave (number of complete scales above reference)."""
        return self.step // 7

    def interval_to(self, other: "DiatonicPitch") -> int:
        """Signed diatonic interval.  Positive = up, negative = down."""
        return other.step - self.step

    def transpose(self, steps: int) -> "DiatonicPitch":
        """Move by diatonic steps."""
        return DiatonicPitch(step=self.step + steps)
```

### Why

Every octave-ambiguity bug in the project traces to the same cause:
degree 1-7 wraps, so the system cannot distinguish "step down from 1
to 7-below" from "sixth up from 1 to 7-above."  The anchor's MIDI
field resolves it at the boundary, but the moment figure-land uses
relative degrees (also wrapping), the information is lost.

Linear diatonic pitch eliminates the entire class:

- **ascending** = `target.step > source.step` — always unambiguous
- **interval size** = `abs(target.step - source.step)` — no wrapping
- **Figure degrees** become signed offsets from the anchor's step
- **Key.diatonic_to_midi(dp)** maps to MIDI using key pitch set + octave

### Reference convention

`step = 0` is the tonic of the home key at the lowest representable
register.  The mapping to MIDI is:

```
MIDI = tonic_pc + (step // 7) * 12 + scale[step % 7]
```

Step values are always relative to the home key, never to a local key
area.  In diatonic mode, all notes belong to the home key's scale, so
this is the only space needed.  The `local_key` field on anchors
indicates tonal function (which key area we are targeting), not pitch
derivation.

### Worked example (C major)

| DiatonicPitch.step | degree | octave | Note | MIDI |
|--------------------|--------|--------|------|------|
| 28 | 1 | 4 | C3 | 48 |
| 29 | 2 | 4 | D3 | 50 |
| 35 | 1 | 5 | C4 | 60 |
| 36 | 2 | 5 | D4 | 62 |
| 37 | 3 | 5 | E4 | 64 |
| 40 | 6 | 5 | A4 | 69 |
| 41 | 7 | 5 | B4 | 71 |
| 42 | 1 | 6 | C5 | 72 |

Typical voice ranges (C major):

| Voice | Step range | MIDI range | Notes |
|-------|-----------|------------|-------|
| Soprano | ~33–45 | ~57–81 | A3–A5 |
| Bass | ~24–34 | ~40–62 | E2–D4 |

The diatonic octave number does not match standard octave naming
(step 35 = C4 has `octave = 5`).  This is intentional — octave is
a derived convenience for tracing, not for computation.  All
arithmetic uses `step` directly.

### Key-relativity across keys

The same step number means "the same scale position" in any key:

| Step 35 | Key | MIDI |
|---------|-----|------|
| 35 | C major | 60 (C4) |
| 35 | G major | 67 (G4) |
| 35 | A major | 69 (A4) |

This is correct.  DiatonicPitch is a scale-step address.  The Key
converts it to absolute pitch.

---

## MIDI Elimination

### Decision

**MIDI exists only at the output boundary and at point-of-need
derivation.**  It is never stored on any internal data structure.
No ChromaticPitch companion is needed.

DiatonicPitch is the compositional truth — it says which scale step
a note occupies.  MIDI is a derived physical quantity — it says which
frequency to play.  The two are related by `Key.diatonic_to_midi(dp)`,
a trivial lookup.  Storing both creates a synchronisation hazard (the
entire class of bug that prompted this redesign).

### Key class additions

```python
def diatonic_to_midi(self, dp: DiatonicPitch) -> int:
    """Convert DiatonicPitch to MIDI pitch number."""
    degree_idx: int = dp.step % 7
    diatonic_octave: int = dp.step // 7
    return self.tonic_pc + diatonic_octave * 12 + self.scale[degree_idx]

def midi_to_diatonic(self, midi: int) -> DiatonicPitch:
    """Find nearest DiatonicPitch for a MIDI pitch.

    Used only during planning (tessitura placement, range
    conversion).  Not for real-time use.
    """
    adjusted: int = midi - self.tonic_pc
    diatonic_octave: int = adjusted // 12
    remainder: int = adjusted % 12
    best_idx: int = 0
    best_dist: int = 12
    for i, semitones in enumerate(self.scale):
        dist: int = abs(remainder - semitones)
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return DiatonicPitch(step=diatonic_octave * 7 + best_idx)
```

`diatonic_to_midi` replaces `degree_to_midi(degree, octave)` with a
single-argument version that reads both from the DiatonicPitch.

`midi_to_diatonic` is used during planning to convert actuator ranges
and tessitura medians from MIDI to step space.  It maps chromatic
MIDI values to the nearest diatonic step.

`diatonic_step(midi, steps)` is replaced by `DiatonicPitch.transpose(steps)` —
trivial arithmetic on integers, no MIDI involved.

### Chromatic checks by derivation

Four use cases currently rely on stored MIDI.  All derive it instead.

**1. Parallel fifth/octave detection**

The writer has the Key and both DiatonicPitches.  Compute:

```python
semitone_a: int = key.diatonic_to_midi(upper_a) - key.diatonic_to_midi(lower_a)
semitone_b: int = key.diatonic_to_midi(upper_b) - key.diatonic_to_midi(lower_b)
# Both == 7 (mod 12) → parallel fifth
# Both == 0 (mod 12) → parallel octave/unison
```

A diatonic 5th is usually perfect (7 semitones) but B–F is diminished
(6 semitones).  DiatonicPitch alone says "5 steps" for both.  The MIDI
derivation distinguishes them.  This is why derivation at point of need
is essential — but storing is not.

**2. Cross-relation detection**

Same letter-name with conflicting accidentals across voices.  In
diatonic mode this cannot happen (all notes from one scale), so
cross-relation detection is a no-op.

For future chromatic mode:

```python
pc_a: int = key_a.diatonic_to_midi(dp_a) % 12
pc_b: int = key_b.diatonic_to_midi(dp_b) % 12
# If dp_a.degree == dp_b.degree but pc_a != pc_b → cross-relation
```

The hack `_degree_to_semitone_approx` disappears entirely — replaced
by exact computation.

**3. Range checking**

Actuator ranges are physical (a violin's G string is MIDI 55 regardless
of key).  They stay in MIDI.

```python
midi: int = key.diatonic_to_midi(dp)
assert actuator.range.low <= midi <= actuator.range.high
```

One derivation per note per range check.

**4. Tessitura placement**

The median is stored as a DiatonicPitch (the scale step that maps to
the desired MIDI register).  Computed during planning:

```python
median_dp: DiatonicPitch = key.midi_to_diatonic(desired_midi_median)
```

Tessitura cost during writing:

```python
cost: int = abs(candidate.step - median_dp.step)
```

Pure diatonic arithmetic.  No MIDI in the loop.

### What changes (summary)

| Component | Before | After |
|-----------|--------|-------|
| Anchor | `upper_midi`, `lower_midi` | `upper_pitch`, `lower_pitch` (DiatonicPitch) |
| `place_anchors_in_tessitura` | Sets MIDI on anchors | Sets DiatonicPitch.step (octave from tessitura) |
| Figure degrees | Unsigned 1–7 | Signed offsets from anchor's step |
| `selector.py` checks | `_degree_to_semitone_approx` | `key.diatonic_to_midi(dp)` — exact |
| `figurate.py` | `soprano_start_midi`, `bass_start_midi` | DiatonicPitch; MIDI derived if needed |
| `Key.diatonic_step(midi, steps)` | MIDI arithmetic | `DiatonicPitch.transpose(steps)` |
| Range checking | Direct MIDI compare | Derive then compare |
| Tessitura median | MIDI int | DiatonicPitch |
| Output (MIDI/MusicXML) | Uses stored MIDI | Derives at serialisation boundary |

### Why not a ChromaticPitch companion

ChromaticPitch would be a wrapped integer counting semitones — which is
exactly MIDI.  Adding it creates a three-way representation
(DiatonicPitch, ChromaticPitch, MIDI) with two mapping boundaries.
The information is already available via `Key.diatonic_to_midi()`.
One representation, one derivation function, one boundary.

---

## Anchor

```python
@dataclass(frozen=True)
class Anchor:
    """Schema arrival constraint at specific bar.beat position."""
    bar_beat: str
    upper_degree: int               # Scale degree for schema_upper role
    lower_degree: int               # Scale degree for schema_lower role
    upper_pitch: DiatonicPitch      # Octave-resolved, key-relative
    lower_pitch: DiatonicPitch      # Octave-resolved, key-relative
    local_key: Key                  # Tonal target (harmonic context, not pitch derivation)
    schema: str
    stage: int
    upper_direction: str | None = None
    lower_direction: str | None = None
    section: str = ""
```

`upper_midi` and `lower_midi` are gone.  `upper_pitch` and `lower_pitch`
carry the same octave-placement information as DiatonicPitch values,
set during planning by `place_anchors_in_tessitura`.

The writer derives MIDI on demand:

```python
upper_midi: int = home_key.diatonic_to_midi(anchor.upper_pitch)
```

Anchors always define two schema voices (Gjerdingen outer-voice
framework).  This is not a 2-voice limitation — schemas are inherently
two-voice structures.  Additional voices derive from these via
imitation, inversion, or harmony fill (see N-voice scaling below).

---

## WritingMode

How to fill a single gap between consecutive anchors.

```python
class WritingMode(Enum):
    FIGURATION = "figuration"      # Select from diminution table
    CADENTIAL = "cadential"        # Select from cadential figure table
    PILLAR = "pillar"              # Single sustained note
    STAGGERED = "staggered"        # Delayed entry, then fill remainder
    WALKING = "walking"            # Stepwise quarter-note bass (future)
    ARPEGGIATED = "arpeggiated"    # Chord-tone arpeggio pattern (future)
```

WALKING and ARPEGGIATED are placeholders for forward compatibility.
The writer asserts on receiving them until the corresponding
strategies are implemented.

---

## GapPlan

All decisions for one figuration gap (anchor[i] → anchor[i+1]).

```python
@dataclass(frozen=True)
class GapPlan:
    bar_num: int
    writing_mode: WritingMode
    # --- Interval context (from anchors, resolved by planner) ---
    interval: str               # "step_up", "third_down", "unison", etc.
    ascending: bool             # Direction of motion to next anchor
    gap_duration: Fraction      # Effective duration (adjusted for start_beat)
    # --- Filter criteria (FIGURATION / CADENTIAL modes) ---
    density: str                # low | medium | high (pre-adjusted for role)
    character: str              # plain | expressive | energetic
    harmonic_tension: str       # low | medium | high
    # --- Realisation parameters ---
    bar_function: str           # cadential | preparatory | schema_arrival | passing
    near_cadence: bool          # True if within 1 bar of cadence
    use_hemiola: bool
    overdotted: bool
    start_beat: int             # 1 = lead, 2 = accompanying
    next_anchor_strength: str   # strong | weak
    required_note_count: int | None  # Pre-computed; None = figure decides
    compound_allowed: bool      # Whether compound-melody figures permitted
```

### Field count

16 fields.  Every one is needed.  Sub-grouping (FilterCriteria,
RealisationParams) would add indirection without reducing information.
Flat is clearer.

### interval and ascending

These duplicate information derivable from anchors.  They stay because:

1. The plan should be self-contained — the writer should not compute.
2. Direction ambiguity (degree 1→7: step down or sixth up?) is resolved
   during planning using DiatonicPitch arithmetic: `anchor_b.upper_pitch.step -
   anchor_a.upper_pitch.step` is always unambiguous.  The writer must
   not re-derive this.
3. Redundancy costs 2 fields.  Ambiguity bugs cost hours.

### required_note_count

For FIGURATION mode the planner pre-computes from
`compute_rhythmic_distribution(gap_duration, density)`.  For CADENTIAL,
PILLAR, STAGGERED it is None (irrelevant).

### Writing mode resolution

The current code has a cascade: passage assignment → schema default →
"walking".  The planner resolves this cascade during planning and writes
the resolved WritingMode into the GapPlan.  The writer does not look up
textures.

---

## SectionPlan

A contiguous span of gaps sharing one sequencing strategy and one
compositional role.

```python
@dataclass(frozen=True)
class SectionPlan:
    start_gap_index: int        # Index into anchor array
    end_gap_index: int          # Exclusive
    schema_name: str | None     # None for non-schema spans
    sequencing: str             # "independent" | "accelerating" | "relaxing"
                                # | "static" | "dyadic" | "repeating"
    figure_profile: str | None  # From figuration_profiles.yaml
    # --- Role and derivation ---
    role: Role                  # SCHEMA_UPPER | SCHEMA_LOWER | IMITATIVE | HARMONY_FILL
    follows: str | None         # For IMITATIVE: voice_id to follow
    follow_interval: int | None # For IMITATIVE: transposition in diatonic steps
    follow_delay: Fraction | None  # For IMITATIVE: delay in whole notes
    # --- Compound melody ---
    shared_actuator_with: str | None  # Voice id sharing same actuator
    gaps: tuple[GapPlan, ...]   # One per gap in [start, end)
```

### Why role is per section, not per voice

A voice's compositional role can change across sections.  In invertible
counterpoint, the upper performed voice reads `anchor.lower_degree` in
the recapitulation (it takes the schema-lower role).  In a Bach
invention, a voice might be SCHEMA_UPPER in the exordium, IMITATIVE
in an episode (following the other voice), and SCHEMA_LOWER in the
inverted reprise.

With role on VoicePlan, this would require hacks (swapping anchor
fields, duplicating anchors with swapped degrees).  With role on
SectionPlan, the mapping is explicit:

```
Exordium:      voice "upper" role=SCHEMA_UPPER,  voice "lower" role=SCHEMA_LOWER
Episode:       voice "upper" role=IMITATIVE(follows=lower), voice "lower" role=SCHEMA_LOWER
Confirmatio:   voice "upper" role=SCHEMA_LOWER,  voice "lower" role=SCHEMA_UPPER
```

The anchors never change.  The reading direction changes per section.

### follows, follow_interval, follow_delay

These also move to SectionPlan because a voice might follow different
sources in different sections, or switch between schema-bound and
imitative modes.  A voice that is SCHEMA_UPPER in section 1 might be
IMITATIVE (following the bass) in section 2.

For non-IMITATIVE sections, all three are None.

### shared_actuator_with (compound melody)

When two compositional voices share one physical actuator (e.g. two
melodic streams interleaved in a single keyboard hand), the writer
must apply additional checks beyond normal counterpoint:

1. Merge the two streams' notes by offset.
2. Check that consecutive intervals in the merged sequence are
   melodically coherent (no grotesque inter-stream leaps).
3. Prefer inter-stream intervals that outline consonances (the
   listener hears implied harmony between streams).
4. Ensure onset complementarity (streams alternate, not collide).

This is what Bach does in solo violin partitas and in keyboard
inventions where one hand weaves between two threads.  The listener
hears two (or three) independent voices from a single performed line.

When `shared_actuator_with` is set, the writer activates compound-melody
checks.  When None, normal counterpoint applies.

The planner must assign complementary density and start_beat values
to the two streams' GapPlans.  If stream A has high density on
beats 1 and 3, stream B gets beats 2 and 4.

### Sequencing and the writer

**independent:** Writer treats each gap independently.  Select figure,
realise, move on.

**Fortspinnung strategies** (accelerating, relaxing, static, dyadic,
repeating): Writer selects an initial figure using the first gap's
filter criteria, then applies the named strategy to produce a figure
sequence (transpose, fragment per strategy rules).  Each resulting
figure is realised using its individual GapPlan's rhythmic parameters.

The strategies are mechanical procedures.  They execute an instruction
from the plan; they do not choose what to do.

### Anchors are not embedded

The writer receives anchors separately (from L4 metric output).
`start_gap_index` and `end_gap_index` are indices into the anchor array.
Gap *i* spans anchor[*i*] → anchor[*i*+1].  This avoids duplicating
anchor data.

---

## AnacrusisPlan

```python
@dataclass(frozen=True)
class AnacrusisPlan:
    target_pitch: DiatonicPitch # Pitch the anacrusis leads into
    duration: Fraction          # Total anacrusis duration in whole notes
    note_count: int             # Number of anacrusis notes
    ascending: bool             # Direction of approach
```

---

## VoicePlan

Complete plan for one voice.

```python
@dataclass(frozen=True)
class VoicePlan:
    voice_id: str
    actuator_range: Range       # From scoring → instrument → actuator (MIDI)
    tessitura_median: DiatonicPitch  # Gravity centre for pitch selection
    composition_order: int      # 0 = written first, 1 = second, etc.
    seed: int                   # Deterministic RNG seed for this voice
    metre: str                  # "4/4", "3/4"
    rhythmic_unit: Fraction     # Genre characteristic, e.g. 1/16
    sections: tuple[SectionPlan, ...]
    anacrusis: AnacrusisPlan | None
```

### Notes

`role` and `follows` have moved to SectionPlan — see above.

`actuator_range` stays in MIDI — it is a physical property of the
instrument.  The writer converts DiatonicPitch to MIDI when checking
range.

`tessitura_median` is a DiatonicPitch — it is a compositional property
(voice sits around this scale step).  Tessitura cost is pure step
arithmetic: `abs(candidate.step - median.step)`.

### Composition order

The planner assigns `composition_order` based on the dependency graph
across all sections.  A voice whose earliest section depends on another
voice (via `follows`) must have a higher order than that voice.

For a typical 2-voice invention: upper = 0, lower = 1 in the exordium
(upper is SCHEMA_UPPER, written first).  In the inverted confirmatio,
roles swap but the order stays the same — both voices are schema-bound,
so the planner can choose either order.

For a 4-voice fugue:

| Voice | First section role | Order |
|---|---|---|
| soprano | SCHEMA_UPPER (subject) | 0 |
| bass | SCHEMA_LOWER | 1 |
| alto | IMITATIVE (follows soprano) | 2 |
| tenor | IMITATIVE (follows soprano) | 3 |

---

## CompositionPlan

```python
@dataclass(frozen=True)
class CompositionPlan:
    home_key: Key                           # Single key for all DiatonicPitch derivation
    voice_plans: tuple[VoicePlan, ...]      # Sorted by composition_order
    anchors: tuple[Anchor, ...]             # Shared anchor sequence (from L4)
```

The builder iterates `voice_plans` in order.  Each writer receives all
previously-completed voice note lists.

`home_key` is the single Key used for all `diatonic_to_midi` calls.
Anchor `local_key` is for harmonic context (chord-tone selection), not
for pitch derivation.  In diatonic mode, all pitches belong to the
home key's scale.

---

## N-Voice Scaling

The plan hierarchy scales to any number of voices without structural
changes.

### What scales

- `CompositionPlan.voice_plans` is a tuple of arbitrary length.
- `composition_order` gives a total order for sequential writing.
- The writer receives all prior voices as `list[list[Note]]` — works
  for any count.
- SectionPlan.role covers four derivation modes: two schema-bound
  outer voices, N-2 imitative or harmony-fill voices.
- `SectionPlan.follows` creates arbitrary dependency chains.

### Why Anchor stays 2-voice

Anchors define the Gjerdingen outer-voice framework.  Schemas are
inherently two-voice structures (upper degree + lower degree).  This
is not a limitation — it is the model.

A 4-voice fugue still has only two schema voices.  The other voices
derive:

| Voice | Section role | Pitch source |
|---|---|---|
| soprano | SCHEMA_UPPER | `anchor.upper_pitch` |
| bass | SCHEMA_LOWER | `anchor.lower_pitch` |
| alto | IMITATIVE | follows soprano, interval -5 |
| tenor | IMITATIVE | follows soprano, interval -12 |

The anchor does not change.  The number of voices reading from it, and
how they read, is determined by SectionPlans.

---

## Voice Crossing and Invertible Counterpoint

### Voice crossing

The design is crossing-agnostic.  Nothing prevents a voice's notes
from sounding below (or above) another voice at any point.  The
writer checks intervals against all prior voices regardless of
register.  DiatonicPitch subtraction is signed, so crossing produces
negative intervals where positive ones were expected (or vice versa).
The writer does not care — it checks for parallel fifths, dissonances,
etc. using absolute interval size.

L004 (laws.md) says: "Voice crossing allowed — Bach crosses freely
in counterpoint."

### Invertible counterpoint

With role on SectionPlan, inversion is expressed by swapping which
anchor field each voice reads:

```
Normal:    soprano reads upper_pitch,  bass reads lower_pitch
Inverted:  soprano reads lower_pitch,  bass reads upper_pitch
```

The anchors are unchanged.  The compositional intent (invertible
counterpoint at the octave, tenth, or twelfth) is captured by the
combination of role assignments and tessitura placement.

The writer does not know or care that this is "inverted counterpoint."
It reads the degree its section's role indicates and applies the same
figuration and checking logic.

### Compound melody (interleaved solo voices)

Two compositional voices share one physical actuator.  The performed
line alternates between registers; the listener hears two (or three)
independent melodic streams.

This is not a special mode — it is the normal composition pipeline
with an additional constraint.  Two voices are planned and written
independently (with full counterpoint checking between them).  The
`shared_actuator_with` field tells the writer to also check that the
interleaved result is coherent as a single performed line:

- Merged consecutive intervals must not be grotesque.
- Inter-stream intervals should outline consonances (implied harmony).
- Onsets must be complementary (streams alternate, not collide).
- The two streams should stay close enough for the ear to separate
  them (typically within a 10th).

The planner enforces this by assigning complementary density and
start_beat values.  The writer enforces it by filtering figures
against the merged sequence.

---

## Faults Contract

Every fault category in `faults.py` must fire if and only if there is a
code bug — either in the planner (created an infeasible or incorrect
plan) or in the writer (selected a figure that violates a rule).

### Analysis by category

**parallel_fifth, parallel_octave, parallel_unison**

Not prevented by construction.  The writer filters candidates against
all prior voices and rejects those that create parallel perfect
intervals.  If no legal candidate exists, the writer aborts (never
emits garbage).  Any parallel in completed output = writer filtering
bug.  Bug-only: yes.

**direct_fifth, direct_octave**

Not prevented by construction.  The writer checks motion type and
resulting interval against prior voices.  Same filtering/abort logic.
Bug-only: yes.

**unprepared_dissonance, unresolved_dissonance**

Anchors on strong beats are consonant by schema definition (planner
guarantee).  The writer checks figure notes at strong-beat offsets
against prior voices and rejects dissonant combinations.  Any
dissonance on a strong beat = either planner bug (schema degrees
are dissonant) or writer bug (failed to check).  Bug-only: yes.

**grotesque_leap (> 19 semitones)**

Within a single gap, figure offsets are small (vocabulary bounded,
max ~6 diatonic steps = ~11 semitones).  Risk is at gap boundaries:
last figure note → next anchor.  The planner spaces anchors within
reasonable distance; the writer's junction checker validates
figure-to-anchor transitions.  Any grotesque leap = planner spacing
bug or writer junction bug.  Bug-only: yes.

**consecutive_leaps (two leaps > 4 semitones, same direction)**

Not prevented by construction.  The writer's junction checker rejects
figures whose exit creates consecutive leaps with the upcoming anchor.
Bug-only: yes.

**ugly_leap (augmented/diminished intervals)**

Not prevented by construction.  The same diatonic figure offset can
produce different chromatic intervals at different anchor degrees
(e.g. a diatonic 4th from B is a tritone B–F, but from C is a
perfect 4th C–F).  The writer must derive MIDI and check.  Bug-only:
yes.

Note: faults.py currently only checks voice 0 (soprano).  This should
be extended to all voices — see faults.py issues below.

**cross_relation**

Impossible in diatonic mode.  All pitches derive from the home key's
scale via `home_key.diatonic_to_midi(dp)`.  Two notes with the same
degree always have the same pitch class.  If a cross-relation appears,
something has violated the DiatonicPitch + home_key contract — a
catastrophic bug.

The check runs but is dormant.  It costs nothing and reactivates
when chromatic mode is implemented.  Bug-only: stronger than
bug-only — structurally impossible.

**tessitura_excursion**

Not prevented by construction.  Figures are offsets from anchors; if
the anchor is near a range edge and the figure moves outward, MIDI
exceeds the actuator range.  The writer derives MIDI and checks
against `VoicePlan.actuator_range`.  The planner places anchors with
room for figuration.  Any excursion = planner placement bug or writer
range-check bug.  Bug-only: yes.

Note: faults.py currently uses hardcoded VOICE_RANGES by index.  Must
accept actuator ranges as a parameter — see faults.py issues below.

**voice_overlap (voice moves to pitch just vacated by other voice)**

Not prevented by construction.  The writer filters candidates against
prior voices at each offset.  Bug-only: yes.

**spacing_error (adjacent voices > 2 octaves apart)**

Skipped for 2-voice texture (current scope).  For future 3+ voices,
the planner must place inner-voice anchors (or tessitura medians)
within 2 octaves of neighbours.  Bug-only: yes (when enabled).

**parallel_rhythm (> 4 consecutive simultaneous attacks)**

Partially prevented by construction: the plan's `start_beat` field
creates rhythmic offset between voices.  However, in equal-density
episodes where both voices start on beat 1, lockstep is theoretically
possible even with correct code.

Resolution: the planner must always differentiate at least one of
`density` or `start_beat` between simultaneously-active voices.  This
makes parallel_rhythm a bug-only guard: if it fires, the planner
failed to enforce rhythmic asymmetry.  Bug-only: yes (with planner
constraint).

### Summary

| Fault | Bug-only? | Responsible |
|---|---|---|
| parallel_fifth | Yes | Writer (filtering) |
| parallel_octave | Yes | Writer (filtering) |
| parallel_unison | Yes | Writer (filtering) |
| direct_fifth | Yes | Writer (motion check) |
| direct_octave | Yes | Writer (motion check) |
| unprepared_dissonance | Yes | Planner (anchors) + writer (figures) |
| unresolved_dissonance | Yes | Writer (resolution check) |
| grotesque_leap | Yes | Planner (spacing) + writer (junction) |
| consecutive_leaps | Yes | Writer (junction) |
| ugly_leap | Yes | Writer (MIDI derivation check) |
| cross_relation | Impossible (diatonic) | Structural guarantee |
| tessitura_excursion | Yes | Planner (placement) + writer (range) |
| voice_overlap | Yes | Writer (filtering) |
| spacing_error | Yes (3+ voices) | Planner (placement) |
| parallel_rhythm | Yes | Planner (asymmetry constraint) |

All 15 categories fire if and only if there is a code bug.

### faults.py issues for future phases

These are implementation tasks, not design issues.  The plan and writer
architecture are correct; faults.py needs updating to match.

**1. Accept actuator ranges as parameter.**  Replace hardcoded
`VOICE_RANGES` lookup by voice index with ranges passed from
`VoicePlan.actuator_range`.

```python
def find_faults(
    voices: Sequence[Sequence[Note]],
    metre: str,
    voice_ranges: dict[int, tuple[int, int]],
) -> list[Fault]:
```

**2. Check ugly_leap for all voices.**  Currently voice 0 only.
Extend to all voices.  If baroque convention permits certain bass
leaps, encode that tolerance in the figure vocabulary (don't include
such figures), not in the fault checker.

**3. Check dissonance for all voice pairs.**  Currently
soprano-vs-bass only.  For 3+ voices, check all adjacent pairs
(sorted by sounding pitch at each time point).

**4. Fix direct_motion for crossing.**  Currently assumes voice 0 is
always highest-sounding.  Should identify which voice is higher at
each time point, not by index.  The "soprano leap" criterion applies
to whichever voice is currently on top.

**5. Fix direct_motion for N voices.**  Currently checks voice 0
against each other voice.  Should check all pairs where one voice is
the locally-highest.

---

## Decision mapping

How each currently-inferred decision maps to the plan.

| Current inference | Plan location |
|---|---|
| Voice role (schema / imitative / fill) | `SectionPlan.role` |
| Imitation source | `SectionPlan.follows` |
| Imitation interval | `SectionPlan.follow_interval` |
| Imitation delay | `SectionPlan.follow_delay` |
| Compound melody pairing | `SectionPlan.shared_actuator_with` |
| Phrase position (opening / continuation / cadence) | `GapPlan.character` + `GapPlan.bar_function` |
| Character (plain / expressive / energetic) | `GapPlan.character` |
| Harmonic tension | `GapPlan.harmonic_tension` |
| Bar function (cadential / preparatory / schema_arrival / passing) | `GapPlan.bar_function` |
| Density (with accompanying reduction) | `GapPlan.density` (pre-adjusted) |
| Hemiola | `GapPlan.use_hemiola` |
| Overdotted | `GapPlan.overdotted` |
| Next anchor strength | `GapPlan.next_anchor_strength` |
| Beat class / start beat | `GapPlan.start_beat` |
| Accompany texture (pillar / staggered / walking / complementary) | `GapPlan.writing_mode` |
| Lead voice | Implicit: start_beat=1 = lead, start_beat=2 = accompany |
| Anacrusis | `VoicePlan.anacrusis` |
| Schema strategy (accelerating / relaxing / etc.) | `SectionPlan.sequencing` |
| Figure profile | `SectionPlan.figure_profile` |
| Schema section detection | `SectionPlan` boundaries |
| Cadential figure selection | `GapPlan.writing_mode = CADENTIAL` |
| Compound melody | `GapPlan.compound_allowed` |
| Phrase deformation | Pre-applied: effects baked into character + bar_function |
| Octave/register of anchor | `Anchor.upper_pitch` / `Anchor.lower_pitch` (DiatonicPitch) |
| Tessitura gravity | `VoicePlan.tessitura_median` (DiatonicPitch) |

---

## What stays in the writer

Mechanical state only — not compositional decisions.

| State | Why it stays |
|---|---|
| Previous figure name | Depends on which figure was actually selected (avoidance) |
| Previous figure ending leap | Depends on selected figure's degree sequence (compensation) |
| Junction checking | Depends on selected figure's exit degrees |
| Prior-voice filtering (parallel 5ths/8ves, etc.) | Depends on actual notes of previously-written voices |
| Compound-melody interleave check | Depends on actual notes of shared-actuator partner |
| MIDI derivation for counterpoint checks | Point-of-need: `home_key.diatonic_to_midi(dp)` |
| MIDI derivation for range checks | Point-of-need: `home_key.diatonic_to_midi(dp)` |

These are all consequences of the writer's single permitted action:
selecting the best figure from the filtered candidate set.  The plan
provides the criteria; the writer applies them and tracks sequential
mechanics.

---

## Design notes

### Phrase deformation is baked in, not carried

The current code selects a deformation (early_cadence /
extended_continuation) then adjusts character and bar_function.  In
the new design the planner applies the deformation during planning and
writes the adjusted values directly into GapPlan.  The writer never
sees "deformation" — just the final character and bar_function.

Deformation is a planning decision, not a writing instruction.

### compound_allowed propagation

The current code makes compound melody "sticky" — if bar 1 gets a
compound figure, bars 2+ prefer compound.  In the new design the
planner pre-decides this: if the opening schema is in a
compound-friendly affect, set compound_allowed=True for that section's
gaps.  The writer does not track stickiness.

### Figure degrees become signed offsets

With DiatonicPitch, figure degrees change from unsigned 1-7 to signed
offsets (0, +1, +2, -1, ...).  A descending third from degree 5 is
`(0, -1, -2)` not `(5, 4, 3)`.  The current code already does
`start_degree + figure.degrees[i]` arithmetic that quietly assumes
offset semantics.  Making this explicit removes a category of error.

Realisation computes absolute pitch:

```python
absolute: DiatonicPitch = anchor_pitch.transpose(figure_offset)
midi: int = home_key.diatonic_to_midi(absolute)
```

### WALKING and ARPEGGIATED are forward stubs

They exist in WritingMode for the enum to be complete from the start.
The writer asserts on receiving them.  They become real when their
WritingStrategy implementations land in Phase 6.

### Feasibility guarantee

If the plan specifies an anchor pair and a figure strategy, the
combination must guarantee a legal result exists.  If the writer
exhausts all candidates for a gap, it reports the failure upstream with
full context.  No silent fallback.  No "fix" function.  Abort is
acceptable; garbage is not.

### home_key vs local_key

In diatonic mode, `home_key` is the only key used for pitch derivation.
Every `diatonic_to_midi` call uses `home_key`.

`local_key` on anchors indicates tonal function: "this Monte segment
targets V" means the anchor degrees are interpreted in the context of
the dominant key area.  But the actual pitches still come from the home
key's scale.  No chromatic alterations, no second pitch space.

For future chromatic mode, `local_key` would be used for pitch derivation
(raising leading tones, etc.).  That changes the mapping function, not
the representation.  DiatonicPitch remains the internal representation;
the Key that interprets it changes.

---

## Resolved questions

### 1. is_minor in GapPlan

**Resolved: omit.**  The Key is available to the writer (passed
separately as `home_key`).  Minor status is a property of the key,
not of individual gaps.  The writer reads `home_key.mode == "minor"`
when filtering by minor safety.

### 2. SectionPlan carrying local Key

**Resolved: writer reads from anchor.**  Each anchor carries `local_key`
for harmonic context.  The writer accesses it via the shared anchor
array.  No duplication in SectionPlan.

### 3. Trill information for cadential figures

**Resolved: stays in figure data.**  The plan says
`writing_mode = CADENTIAL`; the cadential figure table says "trill on
degree N."  The plan specifies *when* to use cadential mode; the
vocabulary specifies *how* the cadence is ornamented.  Clean separation.

### 4. Affect name vs consequences

**Resolved: carry consequences only.**  The plan carries character,
density, overdotted, etc. — the concrete values the writer needs.  The
affect name ("cantabile", "freudigkeit") is a planner concept that
resolves into these values during planning.  The writer never sees it.

### 5. Role per voice vs per section

**Resolved: per section.**  A voice's compositional role can change
across sections (invertible counterpoint, episodes with imitation).
SectionPlan carries `role`, `follows`, `follow_interval`, and
`follow_delay`.  VoicePlan carries only voice-level invariants.

### 6. Compound melody representation

**Resolved: `shared_actuator_with` on SectionPlan.**  Two compositional
voices sharing one actuator are planned and written independently with
full counterpoint checking.  The `shared_actuator_with` field activates
additional interleaved-coherence checks in the writer.  The planner
assigns complementary density and start_beat values.

---

## Document history

| Date | Change |
|------|--------|
| 2026-02-01 | Initial draft from design session |
| 2026-02-01 | v0.2.0: MIDI elimination resolved. DiatonicPitch reference convention. Key class additions. Updated Anchor. All 4 open questions closed. |
| 2026-02-01 | v0.3.0: Role, follows, follow_interval, follow_delay moved from VoicePlan to SectionPlan (invertible counterpoint). shared_actuator_with added to SectionPlan (compound melody). Faults contract: all 15 categories analysed, all bug-only. N-voice scaling section. Voice crossing and invertible counterpoint section. 5 faults.py issues documented for future phases. Resolved questions 5 and 6 added. |
