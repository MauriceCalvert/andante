# Composer's Guide

A framework for multi-voice tonal composition, applicable from pre-baroque through late romantic periods.

## Core Concepts

### Voice vs Instrument

A **voice** is a fixed staff assignment in the texture: soprano, alto, tenor, bass (SATB). Each voice maintains its own registral bounds and melodic continuity.

An **instrument** is the sound source assigned to render one or more voices. In a string quartet, violin I plays soprano, violin II plays alto, viola plays tenor, cello plays bass. In a piano reduction, one instrument renders all four voices.

### Principal Strand

The **principal strand** is the continuous melodic thread carrying the primary musical interest. It is a *role*, not a voice. The principal strand migrates between voices as the composition unfolds: the subject may enter in the soprano, be answered in the alto, then appear in the bass during development.

When we say "compose the principal strand first", we mean: determine *what* the melody is and *where* it appears, not which staff it occupies permanently.

### Counter-Subject

A **counter-subject** is a recurring melodic idea that accompanies the subject. In fugue, it typically appears whenever the subject appears, providing consistent contrapuntal partnership. Counter-subjects are optional in fugue and licit in all forms where recurring accompaniment patterns are desired.

The counter-subject is composed *to fit* the subject, not independently.

## The Four-Voice Skeleton

All tonal music from 1600–1900 reduces to a four-voice skeleton:

1. **Melody** (principal strand) — carries primary interest
2. **Bass** — harmonic foundation and rhythmic drive
3. **Counter-melody** — secondary melodic interest, complements melody
4. **Harmonic fill** — completes chords, smoothest possible voice-leading

A symphony orchestra has 20+ instruments but typically only 2–4 independent voices. The difference between chamber and orchestral music is *orchestration* (timbre, dynamics, blend), not voice count. The compositional thinking is identical.

## Composition Order

For four-voice textures, compose in this order:

### 1. Principal Strand

The subject and all its treatments:
- Literal statement
- Sequence (transposed repetition)
- Inversion (melodic mirror)
- Augmentation/diminution (rhythmic scaling)
- Fragmentation (motivic extraction)
- Modulation (tonal displacement)

This voice has maximum creative freedom. Every subsequent voice is increasingly constrained by what exists.

### 2. Counter-Subject (if applicable)

Composed to complement the principal strand. Must satisfy:

| Constraint | Description |
|------------|-------------|
| Rhythmic complementarity | Fills gaps in subject rhythm |
| Melodic motion | Contrary or oblique motion preferred |
| Invertible counterpoint | Intervals work when voices swap octaves |
| Harmonic consistency | Implies same chord progression as subject |
| Registral bounds | Fits available range without collision |

All these constraints are CSP-expressible.

### 3. Bass Line

Three categories, from most to least creative freedom:

**Participative bass** — shares the subject material. The bass is a full participant in the imitative texture. Examples: fugue, invention.

**Characterful support** — has its own identity but doesn't carry the principal strand:
- Motivic bass: characteristic rhythmic/melodic figure
- Ground bass/ostinato: repeating pattern
- Idiomatic figures: walking bass, arpeggios, Alberti, pedal points

**Neutral support** — purely functional. Free counterpoint following voice-leading rules, no memorable identity. Most constrained category.

### 4. Inner Voices

Alto and tenor in SATB; second violin and viola in quartet. These voices have minimal creative freedom. Their role is to:

- Complete the chord (supply missing triad/seventh tones)
- Follow voice-leading rules (resolve tendency tones, avoid parallels)
- Stay within registral bounds (no voice crossing unless deliberate)
- Match rhythmic texture (homophonic, polyphonic, or hybrid as context requires)

Inner voices are ideal for CSP solving: heavily determined by existing voices, limited solution space, clear constraint satisfaction.

## Constraint Categories

### Hard Constraints (must satisfy)

- Voice-leading rules (no parallel fifths/octaves, resolve leading tones)
- Registral bounds (each voice stays in range)
- Harmonic rhythm (chord changes at specified points)
- Cadence placement (structural points non-negotiable)

### Soft Constraints (prefer to satisfy)

- Contrary motion between outer voices
- Stepwise inner-voice movement
- Even distribution of chord tones
- Rhythmic variety within texture

### Period-Specific Constraints

What changes between periods is not the skeleton but the vocabulary and strictness:

| Aspect | Baroque | Classical | Romantic |
|--------|---------|-----------|----------|
| Harmonic vocabulary | Diatonic triads/sevenths | Same + augmented sixths | Extended chords, chromatic |
| Voice-leading | Strict counterpoint | Somewhat relaxed | Flexible, voice-doublings |
| Formal structures | Binary, fugue, ritornello | Sonata, rondo, theme/var | Expanded sonata, free forms |
| Treatment palette | Sequence, inversion, canon | Development, fragmentation | Transformation, leitmotif |
| Texture | Consistent polyphony | Melody + accompaniment | Varied, orchestral |
| Rhythmic flexibility | Steady pulse, hemiola | Phrase regularity | Rubato, irregular phrase |

## Applying to CSP Engine

The composition order maps directly to CSP solving phases:

1. **Phase 1**: Generate/accept principal strand (human-composed or ML-generated)
2. **Phase 2**: Solve counter-subject if required (CSP with invertibility constraints)
3. **Phase 3**: Solve bass line (CSP, category determines constraint set)
4. **Phase 4**: Solve inner voices (CSP, most constrained, fastest solve)

Each phase adds constraints for subsequent phases. The cumulative constraint set grows tighter, making later phases computationally easier despite having fewer degrees of freedom.

## Period-Agnostic Engine

A single four-voice engine with pluggable rulesets can theoretically generate music across all tonal Western periods:

```
Engine Core (fixed)
├── Voice representation (SATB skeleton)
├── Composition order (melody → bass → inner)
├── CSP solver infrastructure
└── Constraint evaluation framework

Period Plugin (swappable)
├── Harmonic vocabulary (allowed chords)
├── Voice-leading ruleset (strictness levels)
├── Treatment palette (available transformations)
├── Formal templates (structural patterns)
└── Rhythmic conventions (pulse, phrase structure)
```

The baroque plugin enforces strict counterpoint and diatonic harmony. The romantic plugin relaxes voice-leading and expands harmonic vocabulary. The engine core remains identical.

## Summary

1. All tonal music is four voices, regardless of instrumentation
2. Principal strand is a migrating role, not a fixed voice
3. Compose in order: melody → counter-subject → bass → inner voices
4. Each subsequent voice is more constrained, more mechanical
5. Period differences are vocabulary and strictness, not structure
6. CSP naturally handles the constraint accumulation
