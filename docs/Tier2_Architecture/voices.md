# Voice and Instrument Model

## Status

v1.0.0 | Normative

---

## Purpose

This document defines the canonical entities for voices, instruments, and their relationships. It eliminates the brittleness of magic integers and hardcoded assumptions (e.g., `voice == 3` means bass, `VOICE_RANGES[0]` is soprano).

---

## Core Entities

### Voice

A single monophonic melodic line with continuity. The atomic unit for counterpoint.

```yaml
Voice:
  id: str           # Mnemonic identifier (e.g., "upper", "lower", "alto")
  role: Role        # How pitches are determined
```

A voice is abstract — it exists in the composition, not in the physical world. The same voice can be played by different instruments in different performances.

**Identity:** Voice id is a mnemonic chosen by the composer. No integers. No implicit meaning. "upper" and "lower" describe register; "fred" and "joe" are equally valid if less informative.

### Role

How a voice's pitches are determined. Enum with four values:

| Role | Pitch Source | Description |
|------|--------------|-------------|
| `schema_upper` | `anchor.upper_degree` | Outer voice, reads upper degree from schema framework |
| `schema_lower` | `anchor.lower_degree` | Outer voice, reads lower degree from schema framework |
| `imitative` | Transform of another voice | Follows a specified voice with delay/transposition/inversion |
| `harmony_fill` | Chord voicing | Inner voice derived from vertical harmony |

**Schema-bound voices** (schema_upper, schema_lower) are the outer-voice framework defined by Gjerdingen schemas. Anchors provide degree pairs; these roles select which degree.

**Imitative voices** follow another voice. Must specify `follows` (voice id) and transform parameters.

**Harmony-fill voices** are derived at realisation time from the chord implied by outer voices. Used for inner voices in 4-part textures.

### Instrument

A physical sound producer with defined capabilities.

```yaml
Instrument:
  id: str                    # Mnemonic (e.g., "harpsichord", "violin_1")
  type: InstrumentType       # Reference to instrument definition
  actuators: list[Actuator]  # Derived from type
```

**Instrument type** is a reference to a library of instrument definitions (e.g., `piano`, `violin`, `violoncello`). The library defines actuators and their ranges.

### Actuator

The mechanism that produces notes on an instrument.

```yaml
Actuator:
  id: str           # Mnemonic (e.g., "right_hand", "left_hand", "bow")
  range: Range      # Pitch limits
```

| Instrument | Actuators |
|------------|-----------|
| Piano | right_hand, left_hand |
| Organ | right_hand, left_hand, pedals |
| Harpsichord | right_hand, left_hand |
| Violin | bow |
| Violoncello | bow |
| Flute | embouchure |

### Range

Pitch limits for an actuator.

```yaml
Range:
  low: int    # MIDI pitch (e.g., 21 for A0)
  high: int   # MIDI pitch (e.g., 108 for C8)
```

Range is a property of the actuator, not the voice. A voice's effective range is determined by which actuator it is assigned to.

### Scoring

Assignment of voices to actuators. Composition-time configuration.

```yaml
Scoring:
  assignments: dict[voice_id, instrument.actuator]
```

Scoring bridges the abstract (voices) and physical (instruments). It determines:
- Which actuator plays which voice
- Therefore, what range each voice has
- How voices group for performance

### Track

MIDI output assignment. Explicit, not derived.

```yaml
Track:
  voice_id: str
  channel: int      # MIDI channel (0-15)
  program: int      # MIDI program number
```

Track assignment is explicit in the brief. No derivation from voice order.

---

## Derived Entities (Output)

These are derived at output time, not specified in the brief.

### Part

Sheet music for a single performer. Derived from scoring by grouping voices assigned to the same instrument.

```yaml
Part:
  instrument: Instrument
  voices: list[Voice]       # Voices this performer plays
  staves: list[Staff]       # Notational layout
```

### Staff

Notational container. Derived from part layout rules.

```yaml
Staff:
  clef: Clef
  voices: list[Voice]       # Voices notated on this staff
```

A keyboard part typically has two staves (treble/bass). A violin part has one staff. Multiple voices can share a staff (distinguished by stem direction).

---

## Brief Structure

The brief specifies voices, instruments, scoring, and tracks:

```yaml
genre: invention
key: c_major
affect: freudigkeit

voices:
  - id: upper
    role: schema_upper
  - id: lower
    role: schema_lower

instruments:
  - id: keyboard
    type: harpsichord

scoring:
  upper: keyboard.right_hand
  lower: keyboard.left_hand

tracks:
  upper: {channel: 0, program: 6}
  lower: {channel: 1, program: 6}
```

### Example: Trio Sonata

```yaml
genre: trio_sonata
key: g_major
affect: lyrical

voices:
  - id: melody_a
    role: schema_upper
  - id: melody_b
    role: imitative
    follows: melody_a
    delay: 2 bars
    interval: unison
  - id: bass
    role: schema_lower

instruments:
  - id: violin_1
    type: violin
  - id: violin_2
    type: violin
  - id: cello
    type: violoncello

scoring:
  melody_a: violin_1.bow
  melody_b: violin_2.bow
  bass: cello.bow

tracks:
  melody_a: {channel: 0, program: 40}
  melody_b: {channel: 1, program: 40}
  bass: {channel: 2, program: 42}
```

### Example: Four-Voice Fugue for Keyboard

```yaml
genre: fugue
key: d_minor
affect: grounded

voices:
  - id: soprano
    role: schema_upper
  - id: alto
    role: imitative
    follows: soprano
    delay: 2 bars
    interval: -5
  - id: tenor
    role: imitative
    follows: soprano
    delay: 4 bars
    interval: -12
  - id: bass
    role: schema_lower

instruments:
  - id: organ
    type: organ

scoring:
  soprano: organ.right_hand
  alto: organ.right_hand
  tenor: organ.left_hand
  bass: organ.pedals

tracks:
  soprano: {channel: 0, program: 19}
  alto: {channel: 1, program: 19}
  tenor: {channel: 2, program: 19}
  bass: {channel: 3, program: 19}
```

### Example: String Quartet Fugue

```yaml
genre: fugue
key: d_minor
affect: grounded

voices:
  - id: soprano
    role: schema_upper
  - id: alto
    role: imitative
    follows: soprano
    delay: 2 bars
    interval: -5
  - id: tenor
    role: imitative
    follows: soprano
    delay: 4 bars
    interval: -12
  - id: bass
    role: schema_lower

instruments:
  - id: vln1
    type: violin
  - id: vln2
    type: violin
  - id: vla
    type: viola
  - id: vcl
    type: violoncello

scoring:
  soprano: vln1.bow
  alto: vln2.bow
  tenor: vla.bow
  bass: vcl.bow

tracks:
  soprano: {channel: 0, program: 40}
  alto: {channel: 1, program: 40}
  tenor: {channel: 2, program: 41}
  bass: {channel: 3, program: 42}
```

---

## Anchor Changes

Current anchor structure uses `soprano_degree` and `bass_degree`. This assumes SATB terminology.

**New structure:**

```python
@dataclass(frozen=True)
class Anchor:
    bar_beat: str
    upper_degree: int   # Was soprano_degree
    lower_degree: int   # Was bass_degree
    local_key: Key
    schema: str | None
    stage: int
```

Role determines which degree a voice reads:
- `schema_upper` reads `upper_degree`
- `schema_lower` reads `lower_degree`
- `imitative` transforms from followed voice
- `harmony_fill` derives from chord

---

## Range Resolution

During composition, each voice needs a range. This flows from scoring:

```
voice → scoring[voice] → actuator → actuator.range
```

Example:
```
voice "upper" → keyboard.right_hand → Range(low=60, high=96)
```

No hardcoded `VOICE_RANGES[0]`. Range comes from instrument definition.

---

## Realisation Order

Voices are realised in dependency order:

1. Schema-bound voices first (schema_upper, schema_lower)
2. Imitative voices second (depend on their source)
3. Harmony-fill voices last (depend on outer voices)

Within a category, order is determined by the `follows` chain for imitative voices, or arbitrary for others.

**Not derived from voice list order.** Explicit in the model.

---

## Instrument Library

Instrument definitions live in `data/instruments.yaml`:

```yaml
piano:
  actuators:
    right_hand:
      range: {low: 60, high: 108}
    left_hand:
      range: {low: 21, high: 72}

harpsichord:
  actuators:
    right_hand:
      range: {low: 53, high: 89}
    left_hand:
      range: {low: 29, high: 65}

violin:
  actuators:
    bow:
      range: {low: 55, high: 103}

viola:
  actuators:
    bow:
      range: {low: 48, high: 91}

violoncello:
  actuators:
    bow:
      range: {low: 36, high: 76}

organ:
  actuators:
    right_hand:
      range: {low: 53, high: 96}
    left_hand:
      range: {low: 36, high: 72}
    pedals:
      range: {low: 24, high: 55}
```

---

## Migration Path

### Phase 1: Anchor rename
- `soprano_degree` → `upper_degree`
- `bass_degree` → `lower_degree`

### Phase 2: Brief extension
- Add `voices`, `instruments`, `scoring`, `tracks` to Brief dataclass
- Validate scoring references valid voice and actuator ids

### Phase 3: Range resolution
- Replace `VOICE_RANGES[voice_index]` with lookup via scoring
- Load instrument library at startup

### Phase 4: Remove magic integers
- Replace `voice == 0` with `voice.role == Role.SCHEMA_UPPER`
- Replace `voice == 3` with `voice.role == Role.SCHEMA_LOWER`
- Replace array indexing with dict by voice id

---

## Guarantees

1. **No magic integers** — all voice references by mnemonic id
2. **No implicit order** — realisation order from dependency, tracks from explicit assignment
3. **No hardcoded ranges** — all ranges from instrument definitions
4. **Scoring required** — brief must specify voice-to-actuator assignment
5. **Traceable** — every pitch range traces to instrument definition

---

## Document History

| Date | Change |
|------|--------|
| 2025-01-28 | Initial version: entity model for voices, instruments, scoring |

---

*This document is normative. All implementation must align with these entity definitions.*
