# Planner Design: Schema-First Composition

## The Problem

The current planner follows a melody-first approach:

1. Resolve frame (key, metre, tempo)
2. Acquire material (load/generate subject)
3. Plan structure (arcs, episodes, phrases)
4. Plan harmony (cadences derived after structure)

This is backwards. It treats the subject as the creative premise and derives everything else from it. This is a romantic/modern conception that produces historically inaccurate baroque output.

## The Solution

Schema-first planning, consistent with 18th-century partimento practice:

1. Fix frame (key, metre, bars, voices)
2. Plan cadences (arrival points determine structure)
3. Select schema chain (harmonic DNA of the piece)
4. Validate/derive subject from schema
5. Assign textures and treatments

The subject is **one voice's realisation** of the schema skeleton, not a free tune.

## Why This Works

### Schemas Encode Harmony and Counterpoint Together

A schema like `prinner` is not just a bass line (4-3-2-1) or a soprano line (6-5-4-3). It is a pre-validated voice-leading solution. The interval relationships are baked in. When you select a schema, you get:

- Bass degrees
- Soprano degrees  
- Implied harmonies
- Valid voice-leading

No separate "harmony planning" phase needed — the schema *is* the harmony.

### Cadences Drive Structure

In baroque music, form is articulated by cadences. A 16-bar invention has:

- Bar 4: half cadence (V)
- Bar 8: authentic cadence (I)
- Bar 12: cadence in secondary key
- Bar 16: final authentic cadence (I)

These arrival points are decided before any melodic content. The schema chain then fills the space between cadences. This is why baroque music sounds "inevitable" — the destination was always known.

### Subject Derivation, Not Subject Primacy

The subject emerges from the opening schema. If you choose `romanesca` as your opening, the subject must:

- Begin on a degree consonant with the romanesca bass (1, 5, or 3)
- Follow a contour compatible with the schema's soprano degrees
- End before the first strong cadence

The subject is constrained by the schema, not the reverse. This is why baroque subjects invert and sequence cleanly — they were designed to fit the harmonic framework.

### Episodes Are Redundant

The current planner has "episode types" (statement, continuation, development, climax, cadential) that describe rhetorical function. Schemas make these redundant:

| Schema | Inherent Function |
|--------|-------------------|
| romanesca, do-re-mi | opening/statement |
| fonte, monte | continuation/sequence |
| prinner, sol-fa-mi | cadential approach |
| ponte, indugio | prolongation/bridge |

Function emerges from content. Select the schema chain; function follows.

## How It Works

### Step 1: Cadence Plan

Input: frame (key, mode, bars), genre constraints

Output:
```yaml
cadence_plan:
  - bar: 4
    type: half
    target: V
  - bar: 8
    type: authentic
    target: I
```

Rules:
- Final bar always authentic to I
- Section boundaries get cadences
- Genre templates provide typical patterns
- Cadence density varies by genre (invention: frequent; minuet: sparse)

### Step 2: Schema Chain Selection

Input: cadence plan, mode, bars per section

Output:
```yaml
schemas:
  - type: romanesca
    bars: 2
    role: opening
  - type: prinner
    bars: 2
    role: answer
```

Rules:
- Opening schemas (romanesca, do-re-mi) start sections
- Sequential schemas (fonte, monte) provide continuation
- Cadential schemas (prinner, sol-fa-mi) approach arrival points
- Chain must land on cadence points

Selection criteria:
- Schema must fit available bars
- Schema transitions must be valid (not all pairs work)
- Mode compatibility (some schemas prefer major/minor)
- Character affinity (affect influences preferences)

### Step 3: Subject Validation

If subject provided in brief:
- Check first degree matches schema soprano entry
- Check last degree allows continuation
- Check invertibility (intervals consonant when flipped)
- Check answerability at fifth (transposition stays in mode)

If subject not provided:
- Derive from opening schema's soprano degrees
- Add rhythmic profile from genre template
- Ensure invertibility and answerability

### Step 4: Texture and Treatment Assignment

Orthogonal to schema selection:

```yaml
schemas:
  - type: romanesca
    bars: 2
    texture: imitative    # invention: both voices trace schema
    treatment: statement  # first appearance
    voice_entry: soprano  # which voice has subject
```

Texture options:
- `imitative`: both voices derive from schema (invention, fugue)
- `melody_bass`: soprano realises, bass supports (minuet, gavotte)
- `free`: counterpoint fills (inner voices in 4-part)

Treatment options:
- `statement`: literal subject
- `imitation`: answer at octave/fifth
- `sequence`: transposed repetition
- `inversion`: melodic mirror
- `stretto`: overlapped entries

## Plan YAML Structure

```yaml
brief:
  affect: Freudigkeit
  genre: invention
  forces: keyboard
  bars: 24

frame:
  key: C
  mode: major
  metre: 4/4
  tempo: allegro
  voices: 2
  upbeat: 0

material:
  subject:
    degrees: [1, 2, 3, 4, 5]
    durations: [1/8, 1/8, 1/8, 1/8, 1/4]
    bars: 1
    validated: true
    invertible: true
    answerable: true

structure:
  sections:
    - label: A
      key_area: I
      cadence_plan:
        - bar: 4
          type: half
          target: V
        - bar: 8
          type: authentic
          target: I
      schemas:
        - type: romanesca
          bars: 2
          texture: imitative
          treatment: statement
          voice_entry: soprano
        - type: prinner
          bars: 2
          texture: imitative
          treatment: imitation
          voice_entry: bass
        - type: fonte
          bars: 2
          texture: imitative
          treatment: sequence
          voice_entry: soprano
        - type: sol_fa_mi
          bars: 2
          texture: imitative
          treatment: statement
          voice_entry: bass
          cadence: authentic

actual_bars: 24
```

## Genre Mapping

All baroque genres use schema-first. Differences are:

| Genre | Texture | Cadence Density | Typical Opening |
|-------|---------|-----------------|-----------------|
| invention | imitative | high (every 2-4 bars) | romanesca, do-re-mi |
| minuet | melody_bass | low (every 8 bars) | do-re-mi |
| gavotte | melody_bass | medium | romanesca |
| sarabande | melody_bass | low | romanesca, prinner |
| fantasia | mixed | variable | any |

The schema library is shared; genre templates specify preferences and constraints.

## Constraint Summary

### Hard Constraints
- Schema chain must land on cadence points
- Subject must fit opening schema
- Voice-leading rules (no parallel 5ths/8ves)
- Registral bounds

### Soft Constraints
- Prefer contrary motion in outer voices
- Prefer stepwise inner voice movement
- Avoid schema repetition (max 2 occurrences)
- Match schema character to affect

## References

- composerguide.md (Tier3_Guides): procedural guide
- schemas.yaml (data): schema definitions
- cadences.yaml (data): cadence formulas
