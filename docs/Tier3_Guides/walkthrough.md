# Walkthrough: Brief to Plan

This document traces a complete example from Brief input to Plan output.

## Input

```yaml
Brief:
  affect: Majestaet
  genre: invention
  forces: keyboard
  bars: 32
```

## Step 1: Frame Resolution (P1)

### Lookups

**affects.yaml:**
```yaml
Majestaet:
  description: "Majesty, grandeur, ceremonial nobility"
  mode: major
  tempo: allegro
  key_character: dark
  archetype: assertion_confirmation
```

**keys.yaml:**
```yaml
dark:
  - Bb
  - D
  - F
```

### Key Selection

Candidates sorted alphabetically: [Bb, D, F]

Rule: first candidate chosen → `Bb`

### Genre Defaults (invention.yaml)

```yaml
voices: 2
metre: 4/4
form: binary
upbeat: 0
```

### Output

```yaml
Frame:
  key: Bb
  mode: major
  metre: 4/4
  tempo: allegro
  voices: 2
  form: binary
  upbeat: 0
```

## Step 2: Dramaturgy (P2)

### Archetype Lookup

From affect → archetype: `assertion_confirmation`

**archetypes.yaml:**
```yaml
assertion_confirmation:
  description: "Strong opening statement followed by confirmation and triumphant close"
  rhetoric_proportions:
    exordium: 0.15
    narratio: 0.25
    confutatio: 0.20
    confirmatio: 0.25
    peroratio: 0.15
  tension_profile: plateau
  climax_timing: 0.75
```

### Output

```yaml
RhetoricalStructure:
  archetype: assertion_confirmation
  sections:
    - name: exordium
      start_bar: 1
      end_bar: 2
      function: "Opening statement establishing character"
      proportion: 0.15
    - name: narratio
      start_bar: 3
      end_bar: 6
      function: "Development of initial material"
      proportion: 0.25
    # ... etc

TensionCurve:
  points: [(0.0, 0.3), (0.3, 0.6), (0.75, 1.0), (1.0, 0.5)]
  climax_position: 0.75
  climax_level: 1.0
```

## Step 3: Material Acquisition (P3)

### Input

Frame with mode=major, tempo=allegro, metre=4/4

### Subject Generation

Call `generate_subject()` using motifs/ generators (or load from Brief.motif_source if provided).

### Subject Validation

```
bar_duration = 4/4 = 1 whole note
subject.bars = 2
expected duration = 2 × 1 = 2 whole notes

Generated subject:
  degrees: [1, 3, 5, 4, 3, 2, 1]
  durations: [1/4, 1/4, 1/4, 1/4, 1/4, 1/4, 1/2]

sum(durations) = 6 × 1/4 + 1/2 = 1.5 + 0.5 = 2 whole notes ✓
```

### Counter-Subject Generation

Counter-subject generated lazily via CP-SAT solver when first needed.

### Output

```yaml
Material:
  subject:
    degrees: [1, 3, 5, 4, 3, 2, 1]
    durations: [1/4, 1/4, 1/4, 1/4, 1/4, 1/4, 1/2]
    bars: 2
  counter_subject: null  # Generated lazily
  derived_motifs: []
```

## Step 4: Structure Planning (P4)

### Arc Selection

**arcs.yaml:**
```yaml
invention_2voice:
  voices: 2
  treatments: [statement, imitation, sequence, statement]
  climax: late
  surprise: mid
  surprise_type: evaded_cadence
```

### Genre Structure (invention.yaml)

```yaml
sections:
  - label: A
    tonal_path: [I, V]
    final_cadence: half
    bars_per_phrase: 4
  - label: B
    tonal_path: [V, I]
    final_cadence: authentic
    bars_per_phrase: 4
```

### Build Episodes and Phrases

Section A:
- Episode 1: type=exposition, phrases for tonal_path [I, V]

Section B:
- Episode 1: type=development, phrases for tonal_path [V, I]

### Calculate Climax and Surprise

```
Total phrases: 4
Climax at position 0.7: phrase_at_position(0.7, 4) = 2
Surprise at position 0.5: phrase_at_position(0.5, 4) = 2
```

### Build Phrases

| Index | Section | Episode | Tonal Target | Bars | Cadence | Treatment | Surprise | Climax |
|-------|---------|---------|--------------|------|---------|-----------|----------|--------|
| 0 | A | exposition | I | 4 | null | statement | null | false |
| 1 | A | exposition | V | 4 | half | imitation | null | false |
| 2 | B | development | V | 4 | deceptive | sequence | evaded_cadence | true |
| 3 | B | development | I | 4 | authentic | statement | null | false |

### Output

```yaml
Structure:
  arc: invention_2voice
  sections:
    - label: A
      tonal_path: [I, V]
      final_cadence: half
      episodes:
        - type: exposition
          bars: 8
          texture: polyphonic
          phrases:
            - index: 0
              bars: 4
              tonal_target: I
              cadence: null
              treatment: statement
              surprise: null
              is_climax: false
              energy: null
            - index: 1
              bars: 4
              tonal_target: V
              cadence: half
              treatment: imitation
              surprise: null
              is_climax: false
              energy: null
    - label: B
      tonal_path: [V, I]
      final_cadence: authentic
      episodes:
        - type: development
          bars: 8
          texture: polyphonic
          phrases:
            - index: 2
              bars: 4
              tonal_target: V
              cadence: deceptive
              treatment: sequence
              surprise: evaded_cadence
              is_climax: true
              energy: high
            - index: 3
              bars: 4
              tonal_target: I
              cadence: authentic
              treatment: statement
              surprise: null
              is_climax: false
              energy: null
```

## Step 5: Harmony Planning (P5)

### Key Scheme

Based on tonal_path across sections:

```yaml
HarmonicPlan:
  targets:
    - key_area: I
      cadence_type: null
      bar: 4
    - key_area: V
      cadence_type: half
      bar: 8
    - key_area: V
      cadence_type: deceptive
      bar: 12
    - key_area: I
      cadence_type: authentic
      bar: 16
  modulations: []  # Invention stays in home key
```

## Step 6: Devices (P6)

Figurenlehre devices assigned based on affect and rhetoric position:

- Phrase 0 (exordium): No special device
- Phrase 2 (climax): Device candidates considered
- Phrase 3 (peroratio): Final statement, no device

## Step 7: Coherence (P7)

### Callbacks

Check for motivic return opportunities:
- Final phrase recalls opening material

### Surprises

Surprise already placed at phrase 2 (evaded_cadence)

### Proportions

```
Golden ratio point = 16 × 0.618 ≈ bar 10
Climax at bar 9-12 (phrase 2)
Proportion score: 0.85 (good alignment)
```

### Output

```yaml
CoherencePlan:
  callbacks:
    - target_bar: 13
      source_bar: 1
      transform: none
      voice: 0
      material: subject
  climax_bar: 9
  surprises:
    - bar: 11
      beat: 3.0
      type: deceptive_cadence
      duration: 1.0
  golden_ratio_bar: 10
  proportion_score: 0.85
```

## Step 8: Validator

### Structural Checks

| Check | Result |
|-------|--------|
| sections non-empty | ✓ (2 sections) |
| episodes non-empty | ✓ (1 each) |
| phrases non-empty | ✓ (2 each) |
| labels unique | ✓ (A, B) |
| tonal_path non-empty | ✓ |
| motif durations sum = bars × bar_duration | ✓ (2 = 2) |
| phrase indices sequential 0,1,2,3 | ✓ |

### Semantic Checks

| Check | Result |
|-------|--------|
| Last section final_cadence = authentic | ✓ |
| Surprise only if index > 0 | ✓ (phrase 2) |
| Last phrase of each section has correct cadence | ✓ |
| Arc treatments count = phrase count | ✓ (4=4) |

### Referential Checks

| Check | Result |
|-------|--------|
| affect exists in affects.yaml | ✓ |
| arc exists in arcs.yaml | ✓ |
| treatments exist in treatments.yaml | ✓ |

### Result

```
(True, [])
```

## Step 9: build_plan Final Output

```yaml
Plan:
  brief:
    affect: Majestaet
    genre: invention
    forces: keyboard
    bars: 32
    virtuosic: false
    motif_source: null

  frame:
    key: Bb
    mode: major
    metre: 4/4
    tempo: allegro
    voices: 2
    form: binary
    upbeat: 0

  material:
    subject:
      degrees: [1, 3, 5, 4, 3, 2, 1]
      durations: [1/4, 1/4, 1/4, 1/4, 1/4, 1/4, 1/2]
      bars: 2
    counter_subject: null
    derived_motifs: []

  structure:
    arc: invention_2voice
    sections:
      - label: A
        tonal_path: [I, V]
        final_cadence: half
        episodes:
          - type: exposition
            bars: 8
            texture: polyphonic
            phrases:
              - index: 0
                bars: 4
                tonal_target: I
                cadence: null
                treatment: statement
                surprise: null
                is_climax: false
                energy: null
              - index: 1
                bars: 4
                tonal_target: V
                cadence: half
                treatment: imitation
                surprise: null
                is_climax: false
                energy: null
      - label: B
        tonal_path: [V, I]
        final_cadence: authentic
        episodes:
          - type: development
            bars: 8
            texture: polyphonic
            phrases:
              - index: 2
                bars: 4
                tonal_target: V
                cadence: deceptive
                treatment: sequence
                surprise: evaded_cadence
                is_climax: true
                energy: high
              - index: 3
                bars: 4
                tonal_target: I
                cadence: authentic
                treatment: statement
                surprise: null
                is_climax: false
                energy: null

  actual_bars: 16

  tension_curve:
    points: [(0.0, 0.3), (0.3, 0.6), (0.75, 1.0), (1.0, 0.5)]
    climax_position: 0.75
    climax_level: 1.0

  rhetoric:
    archetype: assertion_confirmation
    sections: [...]
    climax_position: 0.75
    climax_bar: 9

  harmonic_plan:
    targets: [...]
    modulations: []

  coherence:
    callbacks: [...]
    climax_bar: 9
    surprises: [...]
    golden_ratio_bar: 10
    proportion_score: 0.85
```

## Observations

1. **Bar delta:** Plan produces 16 bars, not 32. The genre template determines structure; brief.bars is advisory.

2. **Climax and surprise coincide:** Both land on phrase 2. This is permitted and musically sensible — the surprise contributes to climactic tension.

3. **Surprise implies cadence:** When surprise = evaded_cadence, cadence must be deceptive. This is a derived rule, not stored redundantly.

4. **Subject fits metre:** The 2-bar subject contains exactly 2 bars worth of duration in 4/4 time.

5. **Surprise placement constraint:** Surprise cannot land on last phrase of any section (phrases 1 or 3) because it would conflict with section final_cadence.

6. **Episode layer:** The Episode layer groups phrases by dramatic function (exposition, development) and texture.

7. **Lazy counter-subject:** Counter-subject is null in plan output; generated on demand during execution.

8. **7-stage pipeline:** The planner now runs frame → dramaturgy → material → structure → harmony → devices → coherence before validation.

---

*Last updated: 2026-01-14*
