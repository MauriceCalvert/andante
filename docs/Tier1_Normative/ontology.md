# Andante Ontology

## Status

DRAFT — under active refinement. Do not implement until stabilised.

---

## Context: Why This Document Exists

Andante has attempted two architectural approaches, both failed:

| Approach | What it got right | Why it failed |
|----------|-------------------|---------------|
| Melody-first | Subject has identity | No harmonic grounding; wandering tonality |
| Schema-first | Harmonic framework | Mechanically correct, musically dead |

The pattern: each approach captures one aspect of baroque composition, then assumes the rest will follow. It doesn't.

The knowledge needed to succeed exists — Gjerdingen (500 pages on schemas), Koch (phrase structure), Fux (counterpoint), partimento tradition (bass-driven harmony). But it is:

- **Fragmented** — scattered across sources, centuries, languages
- **Descriptive** — "good music has X" not "to make good music, do X"
- **Terminology soup** — same concept, different names

This document defines a **unified ontology** — one vocabulary, one set of primitives, explicit relationships.

All terminology is defined in `D:/projects/Barok/music4dummies/` for detailed reference.

---

## The Core Problem: Hierarchy vs Reality

Andante's current implicit ontology:

```
Piece → Section → Episode → Phrase → Bar → Note
```

This is a **containment hierarchy**. But baroque sources don't think this way:

| Source | Primary unit | Relationship to bars |
|--------|--------------|----------------------|
| Gjerdingen | Schema (2-8 bars) | May start mid-phrase, span boundaries |
| Koch | Phrase (caesura-delimited) | Defined by punctuation, not bar count |
| Partimento | Bass motion | Continuous; bars are incidental |
| Fux | Voice pair | Species spans arbitrary duration |

**Key insight:** The ontology isn't hierarchical. It's **layered and loosely coupled**. A schema might start mid-phrase. A cadence might span a phrase boundary. A subject entry might cut across a schema.

---

## The Six Layers

Baroque composition operates on six simultaneous layers. Each layer has:

- **Units** — the primitives it manipulates
- **Governs** — what decisions it controls
- **Why** — the musical purpose it serves
- **Sources** — where the rules come from

### Layer 1: Rhetorical

| Aspect | Value |
|--------|-------|
| Units | Rhetorical sections (exordium, narratio, confutatio, confirmatio, peroratio) |
| Governs | Large-scale trajectory, pacing, climax placement |
| Why | Music is persuasion. Structure mirrors oratory. The listener is led through an argument. |
| Sources | Mattheson (*Der vollkommene Capellmeister*, 1739) |

Rhetorical functions:

| Section | Function | Musical realisation |
|---------|----------|---------------------|
| Exordium | Capture attention, establish premise | Present subject, establish tonic |
| Narratio | Lay out material | Explore, modulate to dominant/relative |
| Confutatio | Create tension, challenge | Intensify, destabilise, remote keys |
| Confirmatio | Prove the thesis | Return, stretto, learned devices |
| Peroratio | Conclude, leave impression | Strong cadence, tonic confirmation |

### Layer 2: Tonal

| Aspect | Value |
|--------|-------|
| Units | Key, key areas, cadences |
| Governs | Where harmony goes |
| Why | Tension and release. The listener *feels* the journey away from and back to home. |
| Sources | Riepel, Koch, all sources implicitly |

Key distinctions:
- **Key**: The home tonic of the piece. Set once, never changes.
- **Key area**: A region where a harmonic function is emphasised, confirmed by cadence. A piece has one key but visits multiple key areas.
- **Modulation**: Movement to a key area other than tonic. The home key is never abandoned — all other keys are heard relative to it.

Constraints:
- Major mode: first structural goal **must** be V (dominant key area)
- Minor mode: first structural goal typically III (relative major key area)
- Final cadence must be authentic to I/i
- Cadence strength articulates form (authentic > half > deceptive)

### Layer 3: Schematic

| Aspect | Value |
|--------|-------|
| Units | Schema instances (fonte, monte, prinner, romanesca, etc.) |
| Governs | How voices move together between structural points |
| Why | Schemas are **proven solutions** to voice-leading problems. They answer: "How do I get from here to there without ugliness?" |
| Sources | Gjerdingen (*Music in the Galant Style*), partimento tradition |

Schemas have:
- Soprano and bass scale degree skeletons
- Typical tonal effect (stabilise, depart, intensify, cadential)
- Preferred predecessor/successor schemas
- Characteristic duration (1-4 bars typically)

**Schemas are not generative templates. They are validation patterns.** Music that follows schema voice-leading sounds good. Music that violates it sounds awkward.

### Layer 4: Metric

| Aspect | Value |
|--------|-------|
| Units | Bars, beats, phrases |
| Governs | When things align, proportions |
| Why | Breath. Proportion. 4 bars feels complete. 3 feels truncated. 5 feels extended. |
| Sources | Koch (*Introductory Essay*), Riepel |

Key distinctions:
- **Beat**: The basic pulse unit of the metre.
- **Bar**: A metric unit containing a fixed number of beats. Notational, not structural.
- **Phrase**: A unit of music terminating at a cadence or caesura. Length is a consequence, not a definition.
- **Caesura**: A point of melodic and harmonic rest (Koch's *Ruhepunct des Geistes*). Defines phrase boundaries.

Koch's constraints:
- Phrases end with caesuras (resting points)
- 4-bar phrases are normative ("most pleasing")
- Extensions are marked, not arbitrary
- I→I and V→V phrase sequences forbidden in same key

### Layer 5: Thematic

| Aspect | Value |
|--------|-------|
| Units | Subject, counter-subject, motifs |
| Governs | What material appears, identity |
| Why | Without thematic identity, the piece has no face. You recognise it, remember it, anticipate its return. |
| Sources | Marpurg (fugue), common practice |

Key distinctions:
- **Subject**: The primary thematic identity of a piece — what you would hum to identify it.
- **Motif**: The smallest melodically identifiable unit. A subject contains motifs. Motifs can be extracted and developed independently.

Subject constraints (for baroque viability):
- Permits tonal answer at fifth (1↔5 exchange in head)
- Survives inversion without harmonic catastrophe
- Contains intervals that allow sequential treatment
- Fits opening schema's harmonic implications

The subject is **engineered** — neither free nor mechanically derived. It is co-designed with awareness of harmonic and combinatorial constraints.

### Layer 6: Textural

| Aspect | Value |
|--------|-------|
| Units | Voices, treatments |
| Governs | Who does what, how voices relate |
| Why | Rhetoric. Imitation = learned, serious. Homophony = direct, emphatic. |
| Sources | Fux (counterpoint), common practice |

Key distinctions:
- **Voice**: A horizontal melodic strand. A voice is not an instrument.
- **Part**: The music assigned to a performer. May contain multiple voices. May be transposed.
- **Texture**: How voices relate — monophonic, homophonic, polyphonic. Texture is the result.
- **Counterpoint**: The technique of combining voices. Applies to all multi-voice music, whether homophonic or polyphonic.
- **Treatment**: How subject is deployed (statement, imitation, sequence, stretto). Context of presentation.
- **Transformation**: How notes are altered (inversion, retrograde, augmentation). Changes to the material itself.

Texture types:

| Type | Definition | Typical use |
|------|------------|-------------|
| Monophonic | One voice only | Chant, unaccompanied melody |
| Homophonic | Multiple voices, one dominates | Chorale, dance |
| Polyphonic | Multiple voices, all independent | Invention, fugue |

---

## The Causal Chain

Layers are not independent. Each answers "why" by pointing to the layer above:

```
Affect (emotional intent)
    ↓ implies
Rhetorical trajectory (how to structure the argument)
    ↓ implies
Tonal goals (where the harmonic tension points are)
    ↓ achieved by
Schema selection (which voice-leading patterns reach those goals)
    ↓ constrained by
Thematic deployment (subject must fit schema, appear at right moments)
    ↓ realised within
Metric structure (phrases, bars, beats)
    ↓ coloured by
Textural choices (who plays what, how voices relate)
    ↓ produces
Notes
```

**This is the order of decision-making**, not containment. Higher layers constrain lower layers. Lower layers realise higher layers.

---

## Computational Architecture

### Hierarchical CSP

Layers interact via **hierarchical constraint satisfaction**:

1. **Fix high layers** (rhetorical, tonal) — few decisions, set first
2. **Solve middle layers** (schematic, thematic) — many decisions, constrained by tonal goals, solved as CSP
3. **Verify low layers** (metric, textural) — realisation details, verify compliance

Backtrack only between tiers. If middle layers cannot satisfy tonal goals, revise tonal goals. If low layers cannot realise middle layers, revise middle layers.

**Fallback is forbidden.** If no valid solution exists, abort. Do not relax constraints, do not produce degraded output. A failed generation is better than a bad generation.

### Two Tiers of Rules

**Hard rules (validity):**
- Violations abort generation
- Parallel fifths/octaves forbidden
- Dissonances must resolve
- Cadence points must be reached
- Schema degrees must appear at strong beats

**Soft rules (quality):**
- Violations penalised, not forbidden
- Prefer melodic variety
- Prefer balance of steps and leaps
- Prefer rhythmic interest
- Prefer voice independence

**Ranking function:** Generate multiple valid solutions, rank by soft rule satisfaction, return highest-ranked.

**Success criteria:**
- **Competent** = satisfies all hard rules
- **Good** = also scores well on soft rules
- **Brilliant** = out of scope (requires human judgment)

### Schema Validation Granularity

**Schema degrees are hard constraints at strong beats.** Free decoration between.

The skeleton must be present; the flesh is flexible. Real baroque practice decorates schema skeletons with passing tones, neighbour tones, arpeggiation. The schema degrees appear at structurally strong points (strong beats), with decoration between.

### Source Hierarchy

When sources conflict or are silent, apply this precedence:

1. **Counterpoint (Fux)**: Always applies. Voice-leading rules are the floor — never violated.
2. **Phrase structure (Koch)**: Applies where relevant (phrase boundaries, caesuras, proportions).
3. **Schema (Gjerdingen)**: Applies where a schema is active.
4. **Genre conventions**: Apply where genre is specified (invention, minuet, etc.).

More specific rules override more general, but **counterpoint is never overridden**.

If after all sources there is still no guidance, the choice is free (but counterpoint still applies).

---

## Terminology Reference

All terms are defined in detail in `D:/projects/Barok/music4dummies/`. Key distinctions:

| Term | Definition | NOT the same as |
|------|------------|-----------------|
| Key | Home tonic of piece. Set once, never changes. | Key area |
| Key area | Region where harmonic function is emphasised | Key, modulation |
| Modulation | Movement to a key area. Home key never abandoned. | Key change |
| Cadence | Harmonic-melodic formula creating closure, including approach | Cadence point |
| Cadence point | Vertical sonority where resolution occurs | Cadence |
| Phrase | Unit terminating at cadence or caesura | Fixed bar count |
| Caesura | Point of rest defining phrase boundary | Rest, pause |
| Schema | Named voice-leading pattern. Validation, not generation. | Chord progression |
| Subject | Primary thematic identity. What you would hum. | Theme, melody |
| Motif | Smallest melodic unit. Subject contains motifs. | Subject |
| Voice | Horizontal melodic strand | Part, instrument |
| Part | Music assigned to performer. May contain multiple voices. | Voice |
| Texture | How voices relate (mono/homo/polyphonic) | Counterpoint |
| Counterpoint | Technique of combining voices | Texture |
| Treatment | How subject is deployed (imitation, stretto) | Transformation |
| Transformation | How notes are altered (inversion, augmentation) | Treatment |
| Interval | Vertical distance between simultaneous pitches | Melodic motion |
| Melodic motion | Horizontal relationship between successive pitches | Interval |
| Harmony | Vertical aspect — chords, the sound at any moment | Harmonic function |
| Harmonic function | Role a chord plays relative to tonic (T, D, PD) | Harmony |
| Consonance | Interval that sounds stable. Consonance rests. | Dissonance |
| Dissonance | Interval that sounds unstable. Dissonance moves. | Consonance |
| Scale degree | Note's position in scale (1-7). Independent of octave. | Pitch |

---

## Document History

| Date | Change |
|------|--------|
| 2025-01-20 | Initial draft from conversation analysis |
| 2025-01-20 | Terminology refined and cross-referenced to music4dummies |
| 2025-01-20 | Open questions resolved: hierarchical CSP, hard/soft rules, schema granularity, source hierarchy |

---

*This document is normative once stabilised. All implementation must trace to these definitions.*
