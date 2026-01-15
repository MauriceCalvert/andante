# Texture System Design

**Status**: Implemented. See `engine/texture.py` and `data/textures.yaml`.

## Problem

The current system conflates two orthogonal concepts:

- **Treatment**: melodic transformation (invert, fragment, sequence)
- **Texture**: voice relationship pattern (polyphonic, interleaved, hocket)

This conflation forced hacks like `interleaved_invert`, `interleaved_head` - combinatorial explosion of what should be independent parameters.

## Core Insight

Treatment answers: **what notes?**
Texture answers: **how do voices interact?**

These compose orthogonally:

```yaml
- {treatment: inversion, texture: interleaved}   # inverted subject, Goldberg-style voicing
- {treatment: inversion, texture: hocket}        # inverted subject, interlocking gaps
- {treatment: fragmentation, texture: canon}     # head motif in canon
```

## Three-Way Split: Source × Treatment × Texture

The complete model separates three concerns:

| Layer | Question | Examples |
|-------|----------|----------|
| **Source** | Where does raw material come from? | subject, schema, figures |
| **Treatment** | How is material transformed? | invert, fragment, augment |
| **Texture** | How do voices relate? | polyphonic, canon, hocket |

This enables figured bass to work cleanly:
- Source: `schema` (bass from partimento patterns)
- Treatment: `none` or embellishment transforms
- Texture: `stratified` (melody + accompaniment layers)

## Texture Definition

A texture specifies voice relationships across two dimensions:

### Time Relationship

How voices align temporally:

| Value | Meaning |
|-------|---------|
| `independent` | Voices move freely, no temporal constraint |
| `synchronized` | Voices attack together |
| `offset` | Fixed delay between voice entries |
| `phased` | Gradual accumulating offset (Reich) |
| `interlocking` | Voices fill each other's gaps (hocket) |

### Pitch Relationship

How voices relate in pitch space:

| Value | Meaning |
|-------|---------|
| `independent` | Each voice has own material |
| `harmonic` | Voices form chords from harmony |
| `transposed` | Follower copies leader at interval |
| `variant` | Follower elaborates leader's line |
| `partials` | Voices as overtone relationships |

### Voice Roles

Named roles that texture assigns to voices:

| Role | Typical behavior |
|------|------------------|
| `leader` | Primary melodic voice, uses treated subject |
| `follower` | Derives from leader per pitch_relation |
| `dux` | Canon leader - states theme first |
| `comes` | Canon follower - imitates dux |
| `accompaniment` | Harmonic support, less active |
| `pedal` | Sustained reference pitch |
| `filler` | Completes harmonic texture |

## Design Decisions

### Q1: Voice Count

**Decision**: Texture adapts to available voices (Option C).

Textures define roles abstractly. The engine maps available voices to roles dynamically:
- 2-voice canon: dux + comes
- 3-voice canon: dux + comes + accompaniment
- 4-voice canon: dux + comes + filler + accompaniment

### Q2: Offset Units

**Decision**: Fraction of bar.

```yaml
parameters:
  offset: 1/2  # half bar, regardless of metre
```

In 4/4: 2 beats. In 3/4: 1.5 beats. In 6/8: 3 eighth notes.

### Q3: Canon and Treatment Interaction

**Decision**: Treatment applies to dux; canon_type specifies dux→comes relationship.

Canon texture has a `canon_type` parameter:

```yaml
canon:
  parameters:
    canon_type: strict | inversion | retrograde | augmentation | diminution
    interval: -4        # comes at fifth below
    offset: 1/2         # comes enters half bar later
```

Example: `{treatment: fragmentation, texture: canon, canon_type: inversion}`
1. Treatment: take head motif (fragmentation) → dux material
2. Texture: comes = inversion of dux

This matches historical practice:
- Bach Invention 1: strict canon (dux = comes)
- Art of Fugue Contrapunctus 5: inversion canon (comes mirrors dux)

### Q4: Figured Bass

**Decision**: Three-way split (source × treatment × texture).

Figured bass uses:
- Source: `schema` (bass from partimento patterns)
- Treatment: optional embellishment
- Texture: `stratified` or `homophonic`

Figure realization is a voice generation method within the source layer, not a texture.

## Schema

```yaml
# data/textures.yaml

polyphonic:
  time_relation: independent
  pitch_relation: independent
  voice_roles:
    soprano: leader
    bass: leader
  interdictions: []

homophonic:
  time_relation: synchronized
  pitch_relation: harmonic
  voice_roles:
    soprano: leader
    alto: filler
    tenor: filler
    bass: accompaniment
  interdictions:
    - ornaments  # disrupts synchronization

interleaved:
  time_relation: offset
  pitch_relation: independent
  parameters:
    offset: 1/2              # half-bar offset
    tessitura: overlapping   # voices share register
  voice_roles:
    voice_1: leader          # treated subject
    voice_2: leader          # counter-subject
    bass: pedal
  interdictions:
    - inner_voice_gen
    - voice_crossing_penalty
    - ornaments

canon:
  time_relation: offset
  pitch_relation: transposed
  parameters:
    canon_type: strict       # strict | inversion | retrograde | augmentation | diminution
    offset: 1/2              # entry delay
    interval: -4             # at the fifth below
  voice_roles:
    dux: leader              # states theme first
    comes: follower          # imitates dux per canon_type
    bass: accompaniment
  interdictions:
    - inner_voice_gen

hocket:
  time_relation: interlocking
  pitch_relation: independent
  parameters:
    gap_fill: true           # voices complete each other
  voice_roles:
    voice_1: leader
    voice_2: leader
  interdictions:
    - ornaments

heterophony:
  time_relation: independent
  pitch_relation: variant
  parameters:
    variation: ornamental    # follower adds ornaments to leader
  voice_roles:
    plain: leader
    elaborated: follower
  interdictions: []

stratified:
  time_relation: independent
  pitch_relation: independent
  parameters:
    layers:
      - {role: melody, register: high, activity: active}
      - {role: bass, register: low, activity: steady}
      - {role: filler, register: mid, activity: sparse}
  voice_roles:
    soprano: melody
    bass: bass
    alto: filler
  interdictions: []

# Future textures

phasing:
  time_relation: phased
  pitch_relation: transposed
  parameters:
    initial_offset: 0
    phase_increment: 1/32    # accumulates each repetition
    interval: 0              # unison
  voice_roles:
    voice_1: leader
    voice_2: follower
  interdictions:
    - all  # pure process music

pointillist:
  time_relation: independent
  pitch_relation: independent
  parameters:
    density: sparse
    register_priority: true  # register more important than line
  voice_roles:
    all: equal
  interdictions:
    - ornaments
    - inner_voice_gen

spectral:
  time_relation: synchronized
  pitch_relation: partials
  parameters:
    fundamental: bass
    partials: [1, 2, 3, 5, 7]  # which harmonics
  voice_roles:
    bass: fundamental
    others: partials
  interdictions:
    - voice_leading  # partials don't voice-lead traditionally
```

## Pipeline Integration

Current flow:
```
subject → treatment → voices
```

New flow:
```
source → treatment → texture → orchestration → realiser → output
```

### Implementation

```python
# engine/texture.py

@dataclass(frozen=True)
class TextureSpec:
    time_relation: str
    pitch_relation: str
    voice_roles: dict[str, str]
    parameters: dict
    interdictions: list[str]

def apply_texture(
    treated_material: TimedMaterial,
    counter_subject: TimedMaterial,
    texture: TextureSpec,
    budget: Fraction,
    voice_count: int,
) -> tuple[TimedMaterial, ...]:
    """Arrange treated material according to texture spec."""

    if texture.time_relation == "offset":
        return _apply_offset_texture(
            treated_material, counter_subject, texture, budget, voice_count
        )
    elif texture.time_relation == "synchronized":
        return _apply_synchronized_texture(...)
    elif texture.time_relation == "interlocking":
        return _apply_hocket_texture(...)
    # etc.
```

### Voice Expander Changes

```python
# engine/voice_expander.py

def expand_voices(
    treatment_name: str,
    texture_name: str,      # NEW PARAMETER
    subj: Subject,
    ...
) -> tuple[TimedMaterial, ...]:

    treatment = TREATMENTS.get(treatment_name, {})
    texture = TEXTURES.get(texture_name, TEXTURES["polyphonic"])

    # Step 1: Apply treatment to get transformed material
    sop_spec = voice_spec_from_treatment(treatment, "soprano")
    treated = expand_voice(sop_spec, subject, counter_subject, budget, seed, "soprano")

    # Step 2: Apply texture to arrange voices
    return apply_texture(treated, counter_subject, texture, budget, voice_count)
```

## YAML Plan Changes

The interleaved_* treatments have been removed. Use texture field instead:

```yaml
phrases:
  - {index: 0, treatment: statement, texture: polyphonic}
  - {index: 1, treatment: statement, texture: interleaved}
  - {index: 2, treatment: inversion, texture: interleaved}
  - {index: 3, treatment: fragmentation, texture: hocket}
  - {index: 4, treatment: fragmentation, texture: canon, canon_type: inversion}
```

## Orchestration Layer

Voice roles provide the natural interface for instrumentation:

```yaml
# Future orchestration config
orchestration:
  leader: violin_1
  follower: violin_2
  accompaniment: viola
  pedal: cello
```

Or for keyboard:

```yaml
orchestration:
  leader: rh_upper
  follower: rh_lower
  accompaniment: lh
  pedal: lh_bass
```

### Role → Instrument → Register

The texture assigns abstract roles. Orchestration maps roles to instruments. The realiser uses instrument ranges for octave selection:

```
voice role → instrument → register constraints → octave selection
```

Example: `FloatingNote(5)` (degree 5, no octave)
- Assigned to double bass → MIDI ~31 (G1)
- Assigned to violin → MIDI ~67 (G4)

The current `voice_realiser.py` already has the machinery for octave selection. It just needs instrument range lookup instead of hardcoded soprano/bass assumptions.

### Orchestration Capabilities

- **Doubling**: `leader: [violin_1, flute]`
- **Register assignment**: roles specify octave preferences per instrument
- **Timbre variation**: same texture, different instruments across sections
- **Dynamic reassignment**: role→instrument mapping can change mid-piece

### Complete Pipeline

```
source → treatment → texture → orchestration → realiser → output
         (what)      (how)      (who)          (where)
```

| Stage | Responsibility |
|-------|----------------|
| Source | Where notes come from (subject, schema, figures) |
| Treatment | Melodic transformation (invert, fragment, augment) |
| Texture | Voice relationships (time, pitch, roles) |
| Orchestration | Role → instrument mapping |
| Realiser | FloatingNote → MIDI pitch (octave selection via instrument range) |

## Migration

1. Create `data/textures.yaml`
2. Create `engine/texture.py` with `TextureSpec` and `apply_texture()`
3. Modify `expand_voices()` to accept texture parameter
4. Modify `expand_phrase()` to pass texture
5. Update `PhraseAST` to include texture field
6. Remove `interleaved`, `interleaved_*` from `treatments.yaml`
7. Move interdictions from treatment to texture config
8. Update plan parser and serializer
9. (Future) Create `data/orchestrations.yaml` and `engine/orchestration.py`
10. (Future) Add instrument range data to realiser

## Interdiction Ownership

Some interdictions belong to texture, some to treatment:

| Interdiction | Owner | Reason |
|--------------|-------|--------|
| `inner_voice_gen` | texture | voice arrangement concern |
| `voice_crossing_penalty` | texture | register arrangement |
| `ornaments` | texture | can disrupt time relationships |
| `energy_shift` | treatment | melodic transformation concern |
| `climax_boost` | treatment | melodic transformation concern |

## Benefits

1. **Combinatorial power**: N treatments × M textures vs N×M hardcoded combinations
2. **Clear separation**: each system has single responsibility
3. **Extensibility**: add new textures without touching treatment code
4. **Historical accuracy**: matches how composers think (vary a theme, then arrange for forces)
5. **Future-proof**: spectral, phasing, pointillist textures slot in naturally
6. **Orchestration-ready**: voice roles are the natural interface for instrumentation
7. **Realiser integration**: instrument ranges drive octave selection cleanly

## Terminology

| Term | Definition |
|------|------------|
| **Dux** | (Latin: "leader") The voice that introduces the theme in a canon |
| **Comes** | (Latin: "companion") The voice that imitates the dux after a delay |

In strict canon, comes reproduces dux exactly (possibly transposed). In inversion canon, comes mirrors dux melodically. See `music4dummies/dux.html` and `music4dummies/comes.html`.

## References

- Ortiz, Diego. *Trattado de Glosas* (1553) - diminution as texture
- Reich, Steve. *Piano Phase* (1967) - phasing texture
- Goldberg Variations - interleaved texture archetype
- Medieval hocket - interlocking texture
- Ligeti - micropolyphony as texture extreme
- Art of Fugue - canon types (strict, inversion, augmentation, etc.)
