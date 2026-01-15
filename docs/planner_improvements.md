# Planner Improvements: From Form-Filler to Composer

The current planner is a template stamper. It produces structurally valid but musically empty plans. This document specifies a planner that thinks like a composer.

---

## Executive Summary

We have the pieces:
- **Generator** (`motifs/motif_generator.py`) - weighted interval/rhythm sampling
- **Scorer** (`motifs/motif_scorer.py`) - six-stage evaluation pipeline
- **Optimizer** (`motifs/motif_annealer.py`) - simulated annealing refinement
- **Style system** (`motifs/motif_style.py`) - YAML-configurable distributions
- **Theory** (`motifs/styles/memorable.yaml`) - three-axis model from corpus analysis
- **Solver** (`planner/solver.py`) - CP-SAT counter-subject generation

What's missing is the wiring:
- **Affect drives nothing** - no mapping from *Sehnsucht* to interval weights
- **Generator is orphaned** - `planner/material.py` uses hardcoded motifs
- **Schemas diverge** - `memorable.yaml` doesn't load into `MotifStyle`
- **No dramatic arc** - tension curves exist in theory, not in practice

This document unifies everything into a single coherent system.

---

## Part I: Architecture

### The Complete Pipeline

```
Brief (affect, genre, bars, forces)
    │
    ├─────────────────────────────────────────────────────────────┐
    │                                                             │
    ▼                                                             │
┌─────────────────────────────────────────────────────────────────┴───┐
│  STAGE 1: DRAMATURGICAL PLANNING                                    │
│  ════════════════════════════════                                   │
│                                                                     │
│  1.1 Affect → Archetype                                             │
│      Input:  affect (Sehnsucht, Klage, Freudigkeit, ...)            │
│      Output: archetype (quest_to_discovery, lament_to_acceptance)   │
│      Method: lookup table with weighted random for variety          │
│                                                                     │
│  1.2 Archetype → Rhetorical Structure                               │
│      Input:  archetype, duration_bars                               │
│      Output: section boundaries with rhetorical labels              │
│              (exordium, narratio, confutatio, confirmatio, peroratio)
│      Method: proportional templates scaled to duration              │
│                                                                     │
│  1.3 Rhetoric → Tension Curve                                       │
│      Input:  rhetorical structure, archetype                        │
│      Output: per-bar tension values (0-100)                         │
│      Method: interpolate archetype-specific curve shapes            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 2: THEMATIC INVENTION                                        │
│  ═══════════════════════════                                        │
│                                                                     │
│  2.1 Affect → Style Profile                                         │
│      Input:  affect, mode, metre                                    │
│      Output: MotifStyle (interval weights, rhythm groupings, contour)
│      Method: AffectStyleMapper translates affect to generator params│
│                                                                     │
│  2.2 Subject Generation                                             │
│      Input:  MotifStyle, duration_bars                              │
│      Output: candidate subjects                                     │
│      Method: MotifGenerator with rejection sampling                 │
│                                                                     │
│  2.3 Subject Evaluation                                             │
│      Input:  candidates, affect                                     │
│      Output: scored subjects with affect-embodiment rating          │
│      Method: MotifScorer + AffectScorer (new component)             │
│                                                                     │
│  2.4 Subject Optimization                                           │
│      Input:  top candidates                                         │
│      Output: refined subject with highest combined score            │
│      Method: MotifAnnealer with affect-aware mutations              │
│                                                                     │
│  2.5 Counter-Material Generation                                    │
│      Input:  subject, affect                                        │
│      Output: counter-subject, episode fragments                     │
│      Method: CP-SAT solver (existing) + affect constraints (new)    │
│                                                                     │
│  2.6 Developmental Potential Analysis                               │
│      Input:  subject, counter-subject                               │
│      Output: invertibility score, stretto points, fragmentation map │
│      Method: automated analysis of transformations                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3: HARMONIC ARCHITECTURE                                     │
│  ══════════════════════════════                                     │
│                                                                     │
│  3.1 Key Scheme Selection                                           │
│      Input:  archetype, mode, rhetorical structure                  │
│      Output: key areas per section                                  │
│      Method: archetype-specific templates                           │
│                                                                     │
│  3.2 Cadence Planning                                               │
│      Input:  rhetorical positions, tension curve                    │
│      Output: cadence types per phrase boundary                      │
│      Method: rhetoric → cadence mapping with tension modulation     │
│                                                                     │
│  3.3 Harmonic Rhythm                                                │
│      Input:  tension curve, metre                                   │
│      Output: chord change rate per bar                              │
│      Method: tension → harmonic density correlation                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 4: DEVICE ORCHESTRATION                                      │
│  ═════════════════════════════                                      │
│                                                                     │
│  4.1 Figurae Selection                                              │
│      Input:  affect, rhetorical position, tension                   │
│      Output: musical figures per phrase                             │
│      Method: Figurenlehre library with affect/rhetoric filtering    │
│                                                                     │
│  4.2 Texture Planning                                               │
│      Input:  tension curve, voices                                  │
│      Output: texture per bar (solo, duo, tutti, etc.)               │
│      Method: tension → texture density mapping                      │
│                                                                     │
│  4.3 Register Allocation                                            │
│      Input:  tension curve, climax position                         │
│      Output: register extremes reserved for climax                  │
│      Method: register budget with climax reservation                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 5: COHERENCE ENGINEERING                                     │
│  ══════════════════════════════                                     │
│                                                                     │
│  5.1 Callback Planning                                              │
│      Input:  subject, derived motifs, rhetorical structure          │
│      Output: bar → material reference map                           │
│      Method: rule-based placement with variety constraints          │
│                                                                     │
│  5.2 Proportion Validation                                          │
│      Input:  section durations, climax position                     │
│      Output: golden ratio compliance, symmetry metrics              │
│      Method: geometric analysis with adjustment suggestions         │
│                                                                     │
│  5.3 Surprise Injection                                             │
│      Input:  tension curve, phrase boundaries                       │
│      Output: surprise events (pauses, deceptive cadences, etc.)     │
│      Method: strategic placement at expectation peaks               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 6: CONSTRAINT SYNTHESIS                                      │
│  ═════════════════════════════                                      │
│                                                                     │
│  All musical intent → solver-ready constraint packages              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
Plan (YAML with intent)
```

---

## Part II: The Affect System

### 2.1 Affect Vocabulary

The *Affektenlehre* provides our emotional vocabulary. Each affect has specific musical implications:

| Affect | German | Character | Motion | Interval Bias | Rhythm Bias | Contour |
|--------|--------|-----------|--------|---------------|-------------|---------|
| Joy | *Freudigkeit* | Bright, energetic | Rising | 3rds, 4ths, 5ths | Isochronous, dance | Ascending, oscillating |
| Grief | *Klage* | Heavy, weighted | Falling | 2nds (esp. chromatic) | Long-short, halting | Descending |
| Yearning | *Sehnsucht* | Reaching, unresolved | Rising then falling | 6ths, appoggiaturas | Dotted, anacrustic | Arch |
| Tenderness | *Zärtlichkeit* | Gentle, intimate | Stepwise | 2nds, 3rds | Flowing, regular | Undulating |
| Majesty | *Majestät* | Grand, ceremonial | Bold | 4ths, 5ths, octaves | Dotted (French) | Plateau, descending |
| Anger | *Zorn* | Agitated, violent | Erratic | Augmented, diminished | Irregular, driving | Jagged |
| Wonder | *Verwunderung* | Surprising, questioning | Pausing | Wide leaps | Interrupted | Fragmentary |
| Resolution | *Entschlossenheit* | Firm, decisive | Direct | Perfect intervals | Regular, strong | Linear |

### 2.2 AffectStyleMapper

**Location:** `motifs/affect_style.py` (new file)

This component translates affect into MotifStyle parameters:

```python
@dataclass(frozen=True)
class AffectProfile:
    """Musical characteristics associated with an affect."""

    # Interval weights (scale degree distances)
    interval_weights: dict[int, float]
    first_interval_weights: dict[int, float]

    # Signature intervals (must appear at least once)
    signature_intervals: tuple[int, ...]

    # Forbidden intervals (never use)
    forbidden_intervals: tuple[int, ...]

    # Rhythm groupings with weights
    rhythm_groupings: tuple[RhythmGrouping, ...]

    # Contour preferences
    contour_type: str  # "ascending", "descending", "arch", "oscillating"
    direction_bias: float  # -1.0 (descending) to +1.0 (ascending)

    # Range constraints
    range_min_semitones: int
    range_max_semitones: int

    # Tempo implications
    tempo_modifier: float  # multiplier on genre base tempo

    # Character bonuses to seek (from memorable.yaml)
    seek_characters: tuple[str, ...]

    # Character penalties to avoid
    avoid_characters: tuple[str, ...]
```

### 2.3 Affect Profiles

#### Sehnsucht (Yearning)

```yaml
sehnsucht:
  description: "Reaching, unresolved, chromatic — building to fulfillment"

  intervals:
    # Rising 6th is the signature gesture (reaching upward)
    signature: [8]  # minor 6th in semitones

    weights:
      0: 0.05      # unison — rare
      1: 0.18      # m2 up — sighing
      -1: 0.22     # m2 down — sighing resolution
      2: 0.12      # M2 up
      -2: 0.15     # M2 down
      3: 0.08      # m3 up
      -3: 0.06     # m3 down
      4: 0.04      # M3 up
      -4: 0.03     # M3 down
      5: 0.02      # P4 up
      -5: 0.01     # P4 down
      8: 0.04      # m6 up — THE yearning interval

    first_weights:
      # Opening should be moderate, room to reach
      0: 0.03
      1: 0.20
      -1: 0.15
      2: 0.25
      -2: 0.20
      3: 0.10
      -3: 0.07

  rhythm:
    groupings:
      # Anacrusis (reaching forward)
      - pattern: [0.125, 0.375]
        weight: 1.4
      # Long after leap (dwelling)
      - pattern: [0.125, 0.125, 0.25]
        weight: 1.3
      # Dotted urgency
      - pattern: [0.1875, 0.0625]
        weight: 1.2
      - pattern: [0.375, 0.125]
        weight: 1.0
      # Appoggiatura preparation
      - pattern: [0.0625, 0.1875]
        weight: 0.9

  contour:
    type: arch
    direction_bias: 0.2  # slight ascending tendency
    climax_position: 0.6  # peak in second half
    must_return: true     # end lower than peak

  range:
    min_semitones: 8   # need room for the 6th
    max_semitones: 12  # but not excessive

  tempo_modifier: 0.9  # slightly slower than genre default

  seek_characters:
    - chromatic       # expressive semitones
    - ground_compatible  # works with ostinato (passacaglia)

  avoid_characters:
    - obsessive       # not mechanical repetition
    - mordent_identity  # ornament shouldn't dominate
```

#### Klage (Grief/Lament)

```yaml
klage:
  description: "Heavy, descending, slow — the weight of sorrow"

  intervals:
    # Passus duriusculus (chromatic descent) is signature
    signature: [-1]  # descending semitone

    weights:
      0: 0.08       # unison — dwelling in pain
      1: 0.10       # m2 up — brief hope
      -1: 0.28      # m2 down — THE lament interval (tears)
      2: 0.08       # M2 up
      -2: 0.20      # M2 down — sighing
      3: 0.04       # m3 up
      -3: 0.10      # m3 down — grief
      4: 0.02       # M3 up
      -4: 0.06      # M3 down
      -6: 0.04      # tritone down — anguish

    first_weights:
      # Start weighted, not bright
      0: 0.05
      -1: 0.30
      -2: 0.28
      -3: 0.20
      1: 0.08
      2: 0.05
      3: 0.04

  rhythm:
    groupings:
      # Slow, weighted values
      - pattern: [0.5]
        weight: 1.0
      - pattern: [0.375, 0.125]
        weight: 1.3
      # Halting, interrupted
      - pattern: [0.25, 0.125, 0.125]
        weight: 1.1
      # Suspension preparation
      - pattern: [0.25, 0.25]
        weight: 1.2
      # Sighing (short-long)
      - pattern: [0.125, 0.375]
        weight: 1.4

  contour:
    type: descending
    direction_bias: -0.6  # strong descending pull
    climax_position: 0.25  # peak early, then descent
    must_return: false

  range:
    min_semitones: 5   # concentrated
    max_semitones: 10  # not expansive

  tempo_modifier: 0.7  # significantly slower

  seek_characters:
    - chromatic
    - silence  # expressive pauses

  avoid_characters:
    - phrase_repeat   # not dance-like
    - triad_skeleton  # not fanfare
```

#### Freudigkeit (Joy)

```yaml
freudigkeit:
  description: "Bright, energetic, rising — sustained or building"

  intervals:
    signature: [4, 7]  # major 3rd, perfect 5th

    weights:
      0: 0.06
      1: 0.12
      -1: 0.10
      2: 0.18      # M2 up — bright
      -2: 0.12
      3: 0.08      # m3 up
      -3: 0.06
      4: 0.12      # M3 up — major brightness
      -4: 0.04
      5: 0.06      # P4 up
      -5: 0.03
      7: 0.03      # P5 up — fanfare

    first_weights:
      # Strong, bright opening
      2: 0.25
      4: 0.20
      5: 0.15
      7: 0.10
      0: 0.08
      1: 0.10
      3: 0.07
      -2: 0.05

  rhythm:
    groupings:
      # Dance-like, regular
      - pattern: [0.125, 0.125, 0.125, 0.125]
        weight: 1.4
      - pattern: [0.25, 0.25]
        weight: 1.2
      - pattern: [0.125, 0.125, 0.25]
        weight: 1.3
      # Energetic
      - pattern: [0.0625, 0.0625, 0.125]
        weight: 1.0

  contour:
    type: ascending
    direction_bias: 0.4
    climax_position: 0.7
    must_return: false

  range:
    min_semitones: 7
    max_semitones: 14  # expansive

  tempo_modifier: 1.15  # faster than default

  seek_characters:
    - triad_skeleton
    - phrase_repeat

  avoid_characters:
    - chromatic
    - silence
```

#### Majestät (Majesty)

```yaml
majestaet:
  description: "Grand, dotted, ceremonial — assertion and confirmation"

  intervals:
    signature: [5, 7, 12]  # P4, P5, P8

    weights:
      0: 0.10      # unison — repeated notes for emphasis
      1: 0.05
      -1: 0.05
      2: 0.12
      -2: 0.15
      3: 0.06
      -3: 0.08
      4: 0.08
      -4: 0.06
      5: 0.12      # P4 — heraldic
      -5: 0.08
      7: 0.03      # P5 — fanfare
      12: 0.02     # P8 — grandeur

    first_weights:
      # Bold opening
      5: 0.25      # P4 up
      7: 0.20      # P5 up
      4: 0.15
      0: 0.12
      2: 0.10
      -5: 0.10
      -7: 0.08

  rhythm:
    groupings:
      # French overture (THE majesty rhythm)
      - pattern: [0.375, 0.125]
        weight: 1.8
      - pattern: [0.1875, 0.0625, 0.25]
        weight: 1.5
      # Stately
      - pattern: [0.5]
        weight: 1.2
      - pattern: [0.25, 0.25]
        weight: 1.0
      # Tirade (flourish)
      - pattern: [0.0625, 0.0625, 0.0625, 0.0625]
        weight: 0.6

  contour:
    type: plateau  # or descending
    direction_bias: -0.2  # slight descent (nobility condescends)
    climax_position: 0.3  # state grandly early
    must_return: true

  range:
    min_semitones: 10
    max_semitones: 15  # bold range

  tempo_modifier: 0.85  # grave, not rushed

  seek_characters:
    - triad_skeleton
    - obsessive  # repeated notes for emphasis

  avoid_characters:
    - chromatic
    - mordent_identity
```

### 2.4 Affect → Archetype Mapping

Each affect implies a dramatic trajectory:

```yaml
affect_archetypes:
  Sehnsucht:
    primary: quest_to_discovery
    secondary: [struggle_to_triumph, meditation_deepening]
    trajectory: building_to_fulfillment

  Klage:
    primary: lament_to_acceptance
    secondary: [storm_to_calm]
    trajectory: deepening_then_resolving

  Freudigkeit:
    primary: playful_dialogue
    secondary: [struggle_to_triumph, assertion_confirmation]
    trajectory: sustained_or_building

  Zärtlichkeit:
    primary: meditation_deepening
    secondary: [playful_dialogue, lament_to_acceptance]
    trajectory: sustained_intimate

  Majestät:
    primary: assertion_confirmation
    secondary: [struggle_to_triumph]
    trajectory: direct_unwavering

  Zorn:
    primary: storm_to_calm
    secondary: [struggle_to_triumph]
    trajectory: explosion_then_exhaustion

  Verwunderung:
    primary: quest_to_discovery
    secondary: [meditation_deepening]
    trajectory: sudden_shifts

  Entschlossenheit:
    primary: assertion_confirmation
    secondary: [struggle_to_triumph]
    trajectory: direct_unwavering
```

---

## Part III: The Archetype System

### 3.1 Archetype Definitions

Each archetype is a proven dramatic journey with specific rhetorical proportions:

```yaml
archetypes:

  struggle_to_triumph:
    description: "Build tension, overcome obstacles, celebrate victory"
    suitable_affects: [Sehnsucht, Entschlossenheit, Freudigkeit]

    rhetoric_proportions:
      exordium: 0.12      # Brief: establish the struggle
      narratio: 0.20      # Moderate: present material
      confutatio: 0.35    # EXTENDED: the struggle itself
      confirmatio: 0.18   # Dramatic: breakthrough moment
      peroratio: 0.15     # Celebratory: triumph

    tension_curve:
      # (position, level) - position is 0-1, level is 0-100
      - [0.00, 35]   # Start with tension
      - [0.12, 45]   # End exordium
      - [0.32, 60]   # End narratio
      - [0.50, 75]   # Mid-confutatio
      - [0.62, 95]   # CLIMAX
      - [0.67, 90]   # Post-climax
      - [0.85, 50]   # Confirmatio release
      - [1.00, 15]   # Peroratio peace

    key_scheme_minor:
      exordium: [i]
      narratio: [i, III]
      confutatio: [III, vi, iv]
      confirmatio: [V]
      peroratio: [i, I]  # Tierce de picardie for triumph

    key_scheme_major:
      exordium: [I]
      narratio: [I, V]
      confutatio: [V, vi, ii, V/V]
      confirmatio: [V]
      peroratio: [I]

    climax:
      position_range: [0.58, 0.68]  # Golden ratio zone
      register: extremes
      texture: full

  lament_to_acceptance:
    description: "Grieve, deepen, exhaust, find peace"
    suitable_affects: [Klage, Zärtlichkeit]

    rhetoric_proportions:
      exordium: 0.20      # Weighted: state grief fully
      narratio: 0.30      # Extended: dwell in sorrow
      confutatio: 0.18    # Brief: failed escape attempt
      confirmatio: 0.17   # Quiet: acceptance dawns
      peroratio: 0.15     # Peaceful: resignation

    tension_curve:
      - [0.00, 55]
      - [0.20, 70]
      - [0.35, 85]   # CLIMAX early (bar ~35%)
      - [0.50, 75]
      - [0.68, 55]
      - [0.85, 35]
      - [1.00, 20]

    key_scheme_minor:
      exordium: [i]
      narratio: [i, iv]
      confutatio: [iv, VI, III]  # Attempted brightness fails
      confirmatio: [V]
      peroratio: [i]  # Or i → I for transfiguration

    climax:
      position_range: [0.30, 0.40]  # Early
      register: middle_low
      texture: full_then_thinning

  playful_dialogue:
    description: "Exchange, elaborate, agree"
    suitable_affects: [Freudigkeit, Zärtlichkeit]

    rhetoric_proportions:
      exordium: 0.15
      narratio: 0.30
      confutatio: 0.25    # Development is playful, not struggle
      confirmatio: 0.15
      peroratio: 0.15

    tension_curve:
      - [0.00, 40]
      - [0.15, 50]
      - [0.45, 65]
      - [0.60, 70]   # Gentle climax
      - [0.85, 55]
      - [1.00, 30]

    key_scheme_major:
      exordium: [I]
      narratio: [I, V]
      confutatio: [V, vi, ii]
      confirmatio: [V]
      peroratio: [I]

    climax:
      position_range: [0.55, 0.65]
      register: middle_high
      texture: alternating

  meditation_deepening:
    description: "Surface, layer, depth, stillness"
    suitable_affects: [Verwunderung, Zärtlichkeit]

    rhetoric_proportions:
      exordium: 0.15      # Gentle: invite contemplation
      narratio: 0.40      # Extended: layers unfold
      confutatio: 0.10    # Minimal: no conflict
      confirmatio: 0.15   # Merged with narratio feel
      peroratio: 0.20     # Open: stillness, not closure

    tension_curve:
      - [0.00, 25]
      - [0.15, 35]
      - [0.40, 50]
      - [0.55, 60]   # Gentle peak
      - [0.75, 45]
      - [1.00, 20]   # Doesn't resolve to zero

    key_scheme_minor:
      exordium: [i]
      narratio: [i, III, i]
      confutatio: [iv]
      confirmatio: [v]  # Not V - softer
      peroratio: [i]

    climax:
      position_range: [0.50, 0.60]
      register: middle
      texture: gradual_addition

  quest_to_discovery:
    description: "Seek, wander, false paths, arrive"
    suitable_affects: [Sehnsucht, Verwunderung]

    rhetoric_proportions:
      exordium: 0.12
      narratio: 0.22
      confutatio: 0.38    # Extended wandering
      confirmatio: 0.15   # Discovery
      peroratio: 0.13

    tension_curve:
      - [0.00, 30]
      - [0.12, 40]
      - [0.34, 55]
      - [0.50, 70]
      - [0.60, 85]   # False peak
      - [0.65, 60]   # Deflection
      - [0.72, 90]   # TRUE climax (discovery)
      - [0.87, 50]
      - [1.00, 20]

    key_scheme_minor:
      exordium: [i]
      narratio: [i, III]
      confutatio: [III, VII, iv, ii°]  # Wandering
      confirmatio: [V]
      peroratio: [i]

    climax:
      position_range: [0.68, 0.75]
      register: expanding
      texture: building

  assertion_confirmation:
    description: "State, develop, restate grandly"
    suitable_affects: [Majestät, Entschlossenheit]

    rhetoric_proportions:
      exordium: 0.18      # Bold statement
      narratio: 0.25
      confutatio: 0.22
      confirmatio: 0.20   # Grand restatement
      peroratio: 0.15

    tension_curve:
      - [0.00, 50]   # Start strong
      - [0.18, 60]
      - [0.43, 70]
      - [0.55, 80]
      - [0.65, 90]   # Climax
      - [0.85, 70]   # Stays elevated
      - [1.00, 40]

    key_scheme_major:
      exordium: [I]
      narratio: [I, V]
      confutatio: [V, vi, IV]
      confirmatio: [V, I]
      peroratio: [I]

    climax:
      position_range: [0.60, 0.70]
      register: high
      texture: full

  storm_to_calm:
    description: "Rage, exhaust, settle"
    suitable_affects: [Zorn, Klage]

    rhetoric_proportions:
      exordium: 0.10      # Quick ignition
      narratio: 0.25
      confutatio: 0.35    # The storm
      confirmatio: 0.15   # Exhaustion
      peroratio: 0.15     # Calm

    tension_curve:
      - [0.00, 60]   # Start agitated
      - [0.10, 75]
      - [0.25, 85]
      - [0.40, 95]   # CLIMAX (peak fury)
      - [0.45, 90]
      - [0.60, 70]
      - [0.75, 45]
      - [1.00, 15]

    key_scheme_minor:
      exordium: [i]
      narratio: [i, v]
      confutatio: [v, VII, iv, ii°]
      confirmatio: [V]
      peroratio: [i]

    climax:
      position_range: [0.35, 0.45]  # Early climax
      register: extremes
      texture: dense
```

---

## Part IV: Subject Generation Pipeline

### 4.1 Overview

The existing `motifs/` module provides:
- `MotifGenerator` - weighted random generation
- `MotifScorer` - six-stage evaluation
- `MotifAnnealer` - simulated annealing optimization

We enhance this with:
- `AffectStyleMapper` - translates affect → MotifStyle
- `AffectScorer` - scores affect-embodiment
- `DevelopmentalAnalyzer` - assesses transformational potential

### 4.2 AffectStyleMapper

**File:** `motifs/affect_style.py`

```python
class AffectStyleMapper:
    """Translates affect specifications into MotifStyle parameters."""

    def __init__(self) -> None:
        self.profiles: dict[str, AffectProfile] = load_affect_profiles()

    def to_style(
        self,
        affect: str,
        mode: str,
        metre: tuple[int, int],
        duration_bars: int,
    ) -> MotifStyle:
        """Generate MotifStyle from affect and musical context."""
        profile = self.profiles[affect]

        # Adjust interval weights for mode
        weights = self._adjust_for_mode(profile.interval_weights, mode)

        # Build rhythm config
        rhythm = RhythmConfig(
            meter=metre,
            groupings=list(profile.rhythm_groupings),
            allow_rests=affect in ("Klage", "Verwunderung"),
            min_notes=self._min_notes_for_duration(duration_bars, metre),
            max_notes=self._max_notes_for_duration(duration_bars, metre),
        )

        # Build interval config
        intervals = IntervalConfig(
            weights=weights,
            first_weights=self._adjust_for_mode(profile.first_interval_weights, mode),
            max_interval=max(abs(k) for k in weights.keys()),
            step_threshold=1,
            step_inertia_boost=self._inertia_for_affect(affect),
        )

        # Build contour config
        contour = ContourConfig(
            prefer_arch=(profile.contour_type == "arch"),
            prefer_descent=(profile.direction_bias < 0),
            range_min=0,
            range_max=profile.range_max_semitones // 2,  # Convert to scale degrees
        )

        # Calculate target duration
        bar_duration = Fraction(metre[0], metre[1])
        target = float(bar_duration * duration_bars)

        return MotifStyle(
            name=f"{affect}_{mode}",
            rhythm=rhythm,
            intervals=intervals,
            contour=contour,
            target_duration_min=target * 0.95,
            target_duration_max=target * 1.05,
            scale_pattern=MINOR_SCALE if mode == "minor" else MAJOR_SCALE,
        )
```

### 4.3 AffectScorer

**File:** `motifs/affect_scorer.py`

```python
class AffectScorer:
    """Scores how well a motif embodies its target affect."""

    def __init__(self, affect: str) -> None:
        self.affect = affect
        self.profile = load_affect_profile(affect)

    def score(
        self,
        scale_indices: list[int],
        durations: list[float],
    ) -> tuple[float, dict[str, float], str]:
        """Score affect embodiment. Returns (score, breakdown, reason)."""
        breakdown = {}

        # 1. Signature interval presence (required)
        sig_score, sig_found = self._score_signature_intervals(scale_indices)
        breakdown["signature"] = sig_score
        if not sig_found:
            return 0.0, breakdown, "missing_signature_interval"

        # 2. Forbidden interval absence
        forbidden = self._check_forbidden_intervals(scale_indices)
        if forbidden:
            return 0.0, breakdown, f"forbidden_interval_{forbidden}"

        # 3. Interval distribution match
        breakdown["distribution"] = self._score_interval_distribution(scale_indices)

        # 4. Contour match
        breakdown["contour"] = self._score_contour(scale_indices)

        # 5. Rhythm character match
        breakdown["rhythm"] = self._score_rhythm_character(durations)

        # 6. Character bonus match
        breakdown["character"] = self._score_character_bonuses(scale_indices, durations)

        # Weighted combination
        total = (
            breakdown["signature"] * 0.25 +
            breakdown["distribution"] * 0.20 +
            breakdown["contour"] * 0.25 +
            breakdown["rhythm"] * 0.15 +
            breakdown["character"] * 0.15
        )

        return total, breakdown, "ok"

    def _score_signature_intervals(
        self,
        scale_indices: list[int],
    ) -> tuple[float, bool]:
        """Check for required signature intervals."""
        intervals = compute_scale_intervals(scale_indices)
        semitone_intervals = self._to_semitones(intervals)

        required = set(self.profile.signature_intervals)
        found = set()

        for si in semitone_intervals:
            if abs(si) in required:
                found.add(abs(si))

        if not found:
            return 0.0, False

        # Score based on how many signatures found and their prominence
        prominence = self._signature_prominence(semitone_intervals, required)
        coverage = len(found) / len(required)

        return prominence * coverage, True

    def _score_contour(self, scale_indices: list[int]) -> float:
        """Score contour match against affect profile."""
        expected_type = self.profile.contour_type
        actual_type = self._identify_contour(scale_indices)

        if actual_type == expected_type:
            return 1.0

        # Partial credit for related contours
        related = {
            "arch": ["ascending", "descending"],
            "ascending": ["arch"],
            "descending": ["arch"],
            "oscillating": [],
            "plateau": ["descending"],
        }

        if actual_type in related.get(expected_type, []):
            return 0.6

        return 0.2
```

### 4.4 DevelopmentalAnalyzer

**File:** `motifs/developmental.py`

```python
class DevelopmentalAnalyzer:
    """Analyzes a subject's potential for contrapuntal development."""

    def analyze(
        self,
        scale_indices: list[int],
        durations: list[float],
        mode: str,
    ) -> DevelopmentalReport:
        """Comprehensive analysis of developmental potential."""

        return DevelopmentalReport(
            invertibility=self._score_invertibility(scale_indices, mode),
            stretto_points=self._find_stretto_entries(scale_indices, durations),
            fragmentation_map=self._map_fragments(scale_indices, durations),
            sequence_potential=self._score_sequence_potential(scale_indices),
            answer_quality=self._score_tonal_answer(scale_indices, mode),
        )

    def _score_invertibility(
        self,
        scale_indices: list[int],
        mode: str,
    ) -> float:
        """Score how well the subject inverts at octave/10th/12th."""
        intervals = compute_scale_intervals(scale_indices)

        # Check for problematic intervals in inversion
        # 5ths become 4ths (OK), but 4ths become 5ths (parallel risk)
        # 2nds become 7ths (dissonant)

        problematic = 0
        for interval in intervals:
            inverted = -interval
            # In species counterpoint, some inverted intervals are worse
            if abs(interval) == 4:  # P4 → P5 (parallel fifth risk)
                problematic += 1
            if abs(interval) == 1:  # m2 → M7 (strong dissonance)
                problematic += 0.5

        return max(0, 1.0 - problematic * 0.15)

    def _find_stretto_entries(
        self,
        scale_indices: list[int],
        durations: list[float],
    ) -> list[StrettoPoint]:
        """Find points where subject can enter in stretto."""
        points = []

        # Try stretto at each beat offset
        attacks = self._compute_attacks(durations)

        for attack in attacks[1:]:  # Skip first attack
            # Check if entry at this point creates valid counterpoint
            if self._valid_stretto_entry(scale_indices, durations, attack):
                points.append(StrettoPoint(
                    offset=attack,
                    interval=self._best_stretto_interval(scale_indices, attack),
                    quality=self._stretto_quality(scale_indices, durations, attack),
                ))

        return points

    def _map_fragments(
        self,
        scale_indices: list[int],
        durations: list[float],
    ) -> FragmentationMap:
        """Identify usable fragments for development."""
        n = len(scale_indices)

        # Head (first 3-4 notes)
        head_size = min(4, n // 2)
        head = Fragment(
            indices=scale_indices[:head_size],
            durations=durations[:head_size],
            character=self._fragment_character(scale_indices[:head_size]),
        )

        # Tail (last 2-3 notes)
        tail_size = min(3, n // 3)
        tail = Fragment(
            indices=scale_indices[-tail_size:],
            durations=durations[-tail_size:],
            character=self._fragment_character(scale_indices[-tail_size:]),
        )

        # Internal motives (repeated patterns)
        internal = self._find_internal_motives(scale_indices, durations)

        return FragmentationMap(head=head, tail=tail, internal=internal)
```

### 4.5 Unified Subject Generation

**File:** `motifs/subject_generator.py`

```python
def generate_subject(
    affect: str,
    mode: str,
    metre: tuple[int, int],
    duration_bars: int = 1,
    min_score: float = 0.70,
    seed: int | None = None,
) -> GeneratedSubject:
    """Generate a subject that embodies the specified affect.

    This is the main entry point for affect-driven subject generation.
    It orchestrates the full pipeline:
    1. Affect → Style mapping
    2. Candidate generation with rejection sampling
    3. Affect-aware scoring
    4. Simulated annealing optimization
    5. Developmental potential analysis

    Returns:
        GeneratedSubject containing:
        - scale_indices: List of scale degree indices
        - durations: List of note durations
        - score: Combined quality score
        - affect_score: How well it embodies the affect
        - developmental: Analysis of transformational potential
    """

    # 1. Map affect to style
    mapper = AffectStyleMapper()
    style = mapper.to_style(affect, mode, metre, duration_bars)

    # 2. Set up scorers
    base_scorer = MotifScorer()
    affect_scorer = AffectScorer(affect)

    def combined_score(indices: list[int], durs: list[float]) -> float:
        base, _, reason = base_scorer.score(indices, durs)
        if base == 0:
            return 0
        affect, _, _ = affect_scorer.score(indices, durs)
        return base * 0.5 + affect * 0.5

    # 3. Rejection sampling for candidates
    base_seed = seed if seed is not None else int(time.time() * 1000) % 100000
    candidates = []

    for attempt in range(MAX_ATTEMPTS):
        generator = MotifGenerator(
            seed=base_seed + attempt,
            tonic_midi=60,  # C4, will be transposed later
            style=style,
        )

        pitches, indices, durs = generator.generate(
            start_index=style.contour.range_max // 2,
            target_duration=style.target_duration_max,
        )

        score = combined_score(indices, durs)
        if score >= min_score * 0.7:  # Lower threshold for candidates
            candidates.append((indices, durs, score))

        if len(candidates) >= CANDIDATE_COUNT:
            break

    if len(candidates) < 3:
        raise RuntimeError(f"Could not generate enough candidates for {affect}")

    # 4. Simulated annealing with affect-aware mutations
    annealer = AffectAnnealer(base_scorer, affect_scorer, seed=base_seed)
    population = [(c[0], c[1]) for c in candidates]
    optimized = annealer.anneal_population(population)

    best_indices, best_durs, best_score = optimized[0]

    # 5. Developmental analysis
    analyzer = DevelopmentalAnalyzer()
    developmental = analyzer.analyze(best_indices, best_durs, mode)

    # 6. Final affect scoring
    final_affect_score, affect_breakdown, _ = affect_scorer.score(best_indices, best_durs)

    return GeneratedSubject(
        scale_indices=best_indices,
        durations=best_durs,
        score=best_score,
        affect_score=final_affect_score,
        affect_breakdown=affect_breakdown,
        developmental=developmental,
        style=style,
        seed=base_seed,
    )
```

---

## Part V: Integration with Planner

### 5.1 Updated Material Acquisition

**File:** `planner/material.py` (modified)

```python
def acquire_material(
    frame: Frame,
    brief: Brief,
    user_motif: Motif | None = None,
) -> Material:
    """Acquire material: use user motif or generate affect-driven one."""

    if user_motif is not None:
        # User provided motif - use as-is
        motif = user_motif
    else:
        # Generate affect-driven subject
        from motifs.subject_generator import generate_subject

        generated = generate_subject(
            affect=brief.affect,
            mode=frame.mode,
            metre=parse_metre(frame.metre),
            duration_bars=1,  # Standard 1-bar subject
            min_score=0.70,
        )

        # Convert to Motif
        motif = Motif(
            degrees=tuple(idx + 1 for idx in generated.scale_indices),  # 0-indexed to 1-indexed
            durations=tuple(Fraction(d).limit_denominator(32) for d in generated.durations),
            bars=1,
        )

    # Generate counter-subject using existing CP-SAT solver
    subj = Subject(
        motif.degrees,
        motif.durations,
        motif.bars,
        frame.mode,
        brief.genre,
    )
    cs = subj.counter_subject

    # Compute derived motifs
    derived = compute_derived_motifs(motif, cs)

    return Material(
        subject=motif,
        counter_subject=cs,
        derived_motifs=derived,
    )
```

### 5.2 Updated Planner Pipeline

**File:** `planner/planner.py` (modified)

```python
def build_plan(brief: Brief, user_motif: Motif | None = None) -> Plan:
    """Build complete plan from brief with affect-driven dramaturgy."""

    # Validate brief
    valid, errors = validate_brief(brief.genre, brief.affect, brief.bars)
    assert valid, f"Brief validation failed: {errors}"

    # Stage 1: Resolve frame (key, mode, metre, tempo, voices)
    frame: Frame = resolve_frame(brief)

    # Stage 2: Dramaturgical planning
    archetype = select_archetype(brief.affect)
    rhetoric = compute_rhetorical_structure(archetype, brief.bars)
    tension_curve = compute_tension_curve(archetype, rhetoric, brief.bars)

    # Stage 3: Acquire material (now affect-driven)
    material: Material = acquire_material(frame, brief, user_motif)

    # Stage 4: Plan harmonic trajectory
    harmonic_plan = plan_harmony(archetype, rhetoric, frame.mode)

    # Stage 5: Plan structure with rhetorical awareness
    structure: Structure = plan_structure(brief, frame, material, rhetoric, tension_curve)

    # Stage 6: Assign devices per phrase
    structure = assign_devices(structure, brief.affect, tension_curve)

    # Stage 7: Plant coherence mechanisms
    coherence = plan_coherence(structure, material, rhetoric)

    # Compute actual bars
    actual_bars = sum(
        sum(phrase.bars for episode in section.episodes for phrase in episode.phrases)
        for section in structure.sections
    )

    plan = Plan(
        brief=brief,
        frame=frame,
        material=material,
        structure=structure,
        actual_bars=actual_bars,
        tension_curve=tension_curve,
        rhetoric=rhetoric,
        harmonic_plan=harmonic_plan,
        coherence=coherence,
    )

    # Validate
    valid, errors = validate(plan)
    assert valid, f"Plan validation failed: {errors}"

    return plan
```

---

## Part VI: Figurenlehre Library

### 6.1 Figure Definitions

**File:** `data/figurae.yaml`

```yaml
# Musical Figures (Figurenlehre)
# Each figure has affect associations and constraint translations

melodic_figures:

  anabasis:
    description: "Rising line - triumph, aspiration, joy"
    affects: [Freudigkeit, Sehnsucht, Majestät]
    rhetoric_positions: [confirmatio, peroratio]
    constraints:
      direction: ascending
      min_notes: 4
      max_interval: 2  # stepwise

  catabasis:
    description: "Falling line - grief, humility, descent"
    affects: [Klage, Zärtlichkeit]
    rhetoric_positions: [narratio, confutatio]
    constraints:
      direction: descending
      min_notes: 4
      max_interval: 2

  circulatio:
    description: "Circular turn - contemplation, wonder"
    affects: [Verwunderung, Zärtlichkeit]
    rhetoric_positions: [narratio, confutatio]
    constraints:
      pattern: [0, 1, 0, -1, 0]  # relative degrees

  tirata:
    description: "Running scale - energy, excitement"
    affects: [Freudigkeit, Zorn]
    rhetoric_positions: [confutatio, confirmatio]
    constraints:
      direction: any
      min_notes: 6
      rhythm: uniform_fast

  suspiratio:
    description: "Sigh figure - yearning, grief"
    affects: [Sehnsucht, Klage]
    rhetoric_positions: [exordium, narratio]
    constraints:
      pattern: rest_before_repeat
      interval: -1  # falling semitone

  passus_duriusculus:
    description: "Chromatic descent - lament, anguish"
    affects: [Klage]
    rhetoric_positions: [narratio, confutatio]
    constraints:
      type: chromatic_descent
      min_notes: 4
      all_semitones: true

  saltus_duriusculus:
    description: "Diminished leap - pain, dissonance"
    affects: [Klage, Zorn]
    rhetoric_positions: [confutatio]
    constraints:
      interval: [6, -6]  # tritone
      resolve_by_step: true

rhythmic_figures:

  syncope:
    description: "Syncopation - urgency, unrest"
    affects: [Sehnsucht, Zorn]
    tension_range: [50, 100]
    constraints:
      off_beat_emphasis: true

  anticipatio:
    description: "Anticipation - eagerness, reaching"
    affects: [Sehnsucht, Freudigkeit]
    tension_range: [40, 80]
    constraints:
      early_arrival: true

  retardatio:
    description: "Suspension - longing, delay"
    affects: [Sehnsucht, Klage, Zärtlichkeit]
    tension_range: [30, 70]
    constraints:
      held_note: true
      resolution_down: preferred

  punctus:
    description: "Dotted rhythm - majesty, ceremony"
    affects: [Majestät]
    tension_range: [40, 80]
    constraints:
      pattern: dotted
      strong_beat_long: true

texture_figures:

  fuga:
    description: "Imitation - dialogue, order"
    affects: [all]
    rhetoric_positions: [exordium, narratio]
    constraints:
      imitation_distance: [1, 4]  # bars

  noema:
    description: "Homophonic block - emphasis"
    affects: [Majestät, Entschlossenheit]
    rhetoric_positions: [confirmatio, peroratio]
    constraints:
      all_voices_together: true

  fauxbourdon:
    description: "Parallel sixths - sweetness"
    affects: [Zärtlichkeit, Freudigkeit]
    tension_range: [20, 50]
    constraints:
      parallel_sixths: true
```

### 6.2 Device Assignment Algorithm

**File:** `planner/devices.py`

```python
def assign_devices(
    structure: Structure,
    affect: str,
    tension_curve: TensionCurve,
) -> Structure:
    """Assign musical figures to each phrase based on affect and tension."""

    figurae = load_figurae()
    affect_figures = filter_by_affect(figurae, affect)

    new_sections = []
    bar_offset = 0

    for section in structure.sections:
        new_episodes = []

        for episode in section.episodes:
            new_phrases = []

            for phrase in episode.phrases:
                # Get tension at this phrase
                phrase_start = bar_offset / tension_curve.total_bars
                phrase_tension = interpolate_tension(tension_curve, phrase_start)

                # Get rhetorical position
                rhetoric_pos = get_rhetoric_position(bar_offset, structure)

                # Select compatible figures
                candidates = filter_figures(
                    affect_figures,
                    tension=phrase_tension,
                    rhetoric=rhetoric_pos,
                    previous=get_previous_devices(new_phrases),
                )

                # Select 1-2 figures, ensuring variety
                selected = select_diverse(candidates, count=2)

                # Create new phrase with devices
                new_phrase = Phrase(
                    index=phrase.index,
                    bars=phrase.bars,
                    tonal_target=phrase.tonal_target,
                    cadence=phrase.cadence,
                    treatment=phrase.treatment,
                    surprise=phrase.surprise,
                    is_climax=phrase.is_climax,
                    energy=phrase.energy,
                    devices=tuple(selected),  # NEW FIELD
                )

                new_phrases.append(new_phrase)
                bar_offset += phrase.bars

            new_episodes.append(Episode(
                type=episode.type,
                bars=episode.bars,
                texture=episode.texture,
                phrases=tuple(new_phrases),
                is_transition=episode.is_transition,
            ))

        new_sections.append(Section(
            label=section.label,
            tonal_path=section.tonal_path,
            final_cadence=section.final_cadence,
            episodes=tuple(new_episodes),
        ))

    return Structure(sections=tuple(new_sections), arc=structure.arc)
```

---

## Part VII: Coherence System

### 7.1 Callback Planning

```python
@dataclass(frozen=True)
class Callback:
    """A motivic reference to earlier material."""
    target_bar: int
    source_bar: int
    transform: str  # "exact", "inversion", "retrograde", "augmentation"
    voice: str

@dataclass(frozen=True)
class Surprise:
    """A planned surprise event."""
    bar: int
    beat: float
    type: str  # "general_pause", "deceptive_cadence", "register_shift"
    duration: float | None = None

@dataclass(frozen=True)
class CoherencePlan:
    """Long-range coherence mechanisms."""
    callbacks: tuple[Callback, ...]
    climax_bar: int
    climax_beat: float
    surprises: tuple[Surprise, ...]
    proportion_score: float  # How close to golden ratio

def plan_coherence(
    structure: Structure,
    material: Material,
    rhetoric: RhetoricalStructure,
) -> CoherencePlan:
    """Plan long-range coherence mechanisms."""

    total_bars = sum(s.bars for s in structure.sections)

    # 1. Plan callbacks
    callbacks = []

    # Rule: Subject must return at confirmatio
    confirmatio_start = rhetoric.confirmatio.start_bar
    callbacks.append(Callback(
        target_bar=confirmatio_start,
        source_bar=1,
        transform="exact",
        voice="soprano",
    ))

    # Rule: Climax material should be inverted in peroratio
    climax_bar = int(total_bars * rhetoric.climax_position)
    peroratio_start = rhetoric.peroratio.start_bar
    callbacks.append(Callback(
        target_bar=peroratio_start + 2,
        source_bar=climax_bar,
        transform="inversion",
        voice="soprano",
    ))

    # Rule: Counter-subject head appears in confutatio
    confutatio_mid = (rhetoric.confutatio.start_bar + rhetoric.confutatio.end_bar) // 2
    callbacks.append(Callback(
        target_bar=confutatio_mid,
        source_bar=2,  # CS typically enters bar 2
        transform="exact",
        voice="alto",
    ))

    # 2. Determine climax
    climax_bar = int(total_bars * rhetoric.climax_position)
    climax_beat = 1.0  # Usually downbeat

    # 3. Plan surprises
    surprises = []

    # Rule: At least one surprise per major section
    # General pause in narratio
    narratio_mid = (rhetoric.narratio.start_bar + rhetoric.narratio.end_bar) // 2
    surprises.append(Surprise(
        bar=narratio_mid,
        beat=3.0,  # Before expected continuation
        type="general_pause",
        duration=0.5,
    ))

    # Deceptive cadence before climax
    surprises.append(Surprise(
        bar=climax_bar - 2,
        beat=4.0,
        type="deceptive_cadence",
    ))

    # 4. Check proportions
    golden = 0.618
    actual_climax_ratio = climax_bar / total_bars
    proportion_score = 1.0 - abs(golden - actual_climax_ratio)

    return CoherencePlan(
        callbacks=tuple(callbacks),
        climax_bar=climax_bar,
        climax_beat=climax_beat,
        surprises=tuple(surprises),
        proportion_score=proportion_score,
    )
```

---

## Part VIII: Enhanced Data Types

### 8.1 Updated Plan Output

```python
@dataclass(frozen=True)
class RhetoricalSection:
    """A section of rhetorical structure."""
    name: str  # exordium, narratio, etc.
    start_bar: int
    end_bar: int
    function: str

@dataclass(frozen=True)
class RhetoricalStructure:
    """Complete rhetorical structure."""
    exordium: RhetoricalSection
    narratio: RhetoricalSection
    confutatio: RhetoricalSection
    confirmatio: RhetoricalSection
    peroratio: RhetoricalSection
    climax_position: float  # 0-1

@dataclass(frozen=True)
class HarmonicTarget:
    """Harmonic target for a phrase."""
    bar_range: tuple[int, int]
    key: str
    cadence: str | None

@dataclass(frozen=True)
class HarmonicPlan:
    """Complete harmonic trajectory."""
    targets: tuple[HarmonicTarget, ...]

@dataclass(frozen=True)
class Phrase:
    """Musical phrase within an episode."""
    index: int
    bars: int
    tonal_target: str
    cadence: str | None
    treatment: str
    surprise: str | None
    is_climax: bool = False
    energy: str | None = None
    devices: tuple[str, ...] = ()  # NEW: assigned figures
    tension: float = 50.0          # NEW: tension level
    callbacks: tuple[str, ...] = () # NEW: motivic references

@dataclass(frozen=True)
class Plan:
    """Complete plan output with full dramaturgy."""
    brief: Brief
    frame: Frame
    material: Material
    structure: Structure
    actual_bars: int
    archetype: str                          # NEW
    rhetoric: RhetoricalStructure           # NEW
    tension_curve: TensionCurve
    harmonic_plan: HarmonicPlan             # NEW
    coherence: CoherencePlan                # NEW
    macro_form: MacroForm | None = None
```

---

## Part IX: The Memorable Framework

### 9.1 Origin: Corpus Analysis

The `memorable.yaml` file (`motifs/styles/memorable.yaml`) contains a theoretical model derived from systematic analysis of 9 iconic baroque melodies:

- **Canon** (Pachelbel)
- **Dido's Lament** (Purcell)
- **Toccata BWV 565** (Bach)
- **Little Fugue BWV 578** (Bach)
- **La Primavera** (Vivaldi)
- **Hallelujah** (Handel)
- **Brandenburg 3** (Bach)
- **Tambourin** (Rameau)
- **La Folia** (traditional)

**Key statistical findings:**
- 73% of intervals are stepwise (m2/M2) or unison
- Leaps (≥m3) occur at phrase boundaries, followed by contrary steps
- Kernels use only 2-3 distinct rhythmic values
- Initial range ≤ P8; expansion signals development
- Every kernel outlines tonic triad within first 4 notes

### 9.2 The Three-Axis Model

Every memorable melody has exactly one value on each of three orthogonal axes:

**Axis 1 - Pitch Strategy:**
| Strategy | Description | Examples |
|----------|-------------|----------|
| `stepwise` | Conjunct motion dominates | Canon, Dido, Toccata, Brandenburg, La Folia |
| `repetition` | Repeated notes as foundation | Hallelujah, Primavera |
| `leap_fill` | Large interval + stepwise compensation | Little Fugue |

**Axis 2 - Rhythmic Character:**
| Strategy | Description | Examples |
|----------|-------------|----------|
| `isochronous` | Equal note values, metric regularity | Canon, Hallelujah |
| `long_short` | Dotted rhythms, agogic accent | Little Fugue, Dido |
| `ornamental` | Mordents, turns, rapid figuration | Toccata, Brandenburg, Primavera |
| `dance` | Strong metric pulse, phrase regularity | Tambourin, La Folia |

**Axis 3 - Contour:**
| Strategy | Description | Examples |
|----------|-------------|----------|
| `descending` | Gravitational pull downward | Canon, Dido bass, Toccata, La Folia |
| `arch` | Rise then fall, tension-release | Dido vocal, Little Fugue |
| `ascending` | Building energy upward | Hallelujah sequences |
| `oscillating` | Neighbour-note motion, wave-like | Primavera, Brandenburg, Tambourin |

### 9.3 Character Bonuses

Optional distinctive features (0-2 per motif) that add flavor:

| Character | Description | Bonus | Examples |
|-----------|-------------|-------|----------|
| `chromatic` | Semitone motion as expressive device | +12% | Dido bass (G-F#-F-E-Eb-D) |
| `mordent_identity` | The ornament IS the motif | +15% | Toccata (A-G-A), Brandenburg |
| `obsessive` | Repetition beyond functional necessity | +10% | Hallelujah (D-D-D-D) |
| `silence` | Rest/pause as structural element | +8% | Toccata (gesture, pause, gesture) |
| `ground_compatible` | Works over repeating bass | +10% | Canon, Dido, La Folia |
| `triad_skeleton` | Opens by spelling tonic triad | +12% | Little Fugue (G-D-Bb) |
| `phrase_repeat` | Immediate full restatement | +10% | Primavera |

### 9.4 Corpus Classification

| Piece | Pitch | Rhythm | Contour | Characters |
|-------|-------|--------|---------|------------|
| Canon | stepwise | isochronous | descending | ground_compatible |
| Dido bass | stepwise | long_short | descending | chromatic, ground_compatible |
| Dido vocal | stepwise | long_short | arch | chromatic |
| Toccata | stepwise | ornamental | descending | mordent_identity, silence |
| Little Fugue | leap_fill | long_short | arch | triad_skeleton |
| Primavera | repetition | ornamental | oscillating | phrase_repeat |
| Hallelujah | repetition | isochronous | ascending | obsessive |
| Brandenburg | stepwise | ornamental | oscillating | mordent_identity |
| Tambourin | stepwise | dance | oscillating | mordent_identity |
| La Folia | stepwise | dance | descending | ground_compatible |

### 9.5 Affect → Memorable Mapping

Each affect maps to specific axis values and characters:

```yaml
affect_to_memorable:

  Sehnsucht:
    pitch_strategy: stepwise
    rhythm_strategy: long_short
    contour_strategy: arch
    characters: [chromatic]
    # Like: Dido vocal

  Klage:
    pitch_strategy: stepwise
    rhythm_strategy: long_short
    contour_strategy: descending
    characters: [chromatic, silence]
    # Like: Dido bass + Toccata drama

  Freudigkeit:
    pitch_strategy: stepwise  # or repetition
    rhythm_strategy: isochronous
    contour_strategy: ascending  # or oscillating
    characters: [triad_skeleton, phrase_repeat]
    # Like: Hallelujah energy

  Majestät:
    pitch_strategy: leap_fill
    rhythm_strategy: long_short
    contour_strategy: descending
    characters: [triad_skeleton]
    # Like: Little Fugue grandeur

  Zärtlichkeit:
    pitch_strategy: stepwise
    rhythm_strategy: dance
    contour_strategy: oscillating
    characters: [ground_compatible]
    # Like: gentle minuet

  Zorn:
    pitch_strategy: stepwise
    rhythm_strategy: ornamental
    contour_strategy: descending
    characters: [mordent_identity, silence]
    # Like: Toccata fury

  Verwunderung:
    pitch_strategy: repetition
    rhythm_strategy: ornamental
    contour_strategy: oscillating
    characters: [silence]
    # Surprising pauses

  Entschlossenheit:
    pitch_strategy: leap_fill
    rhythm_strategy: isochronous
    contour_strategy: ascending
    characters: [triad_skeleton, obsessive]
    # Direct, fanfare-like
```

### 9.6 Base Constraints (All Memorable Melodies)

From `memorable.yaml`:

```yaml
base_constraints:
  range:
    max_semitones: 12          # P8 maximum for kernel
    typical_semitones: 7       # P5 typical

  intervals:
    min_stepwise_percent: 70   # At least 70% steps/unisons

  triad_outline:
    required: true
    within_first_n_notes: 4    # First 4 notes hit ≥2 triad tones

  climax:
    single_peak: true          # One highest note
    single_trough: true        # One lowest note

  gap_fill:
    required_after_leap: true
    leap_threshold: 3          # m3 or larger
    fill_direction: contrary

  duration:
    kernel_min_beats: 2        # At least half a bar
    kernel_max_beats: 4        # At most one bar

  note_count:
    min: 4
    max: 8
```

---

## Part X: YAML Schema Unification

### 10.1 Unified Style Schema

The system supports two schema formats, auto-detected by the loader:

```yaml
# Unified motif style schema
# Supports both direct configuration and memorable.yaml's three-axis model

name: sehnsucht_minor

# --- DIRECT CONFIGURATION (existing schema) ---
rhythm:
  meter: [4, 4]
  groupings:
    - pattern: [0.125, 0.375]
      weight: 1.4
    # ...
  allow_rests: false
  min_notes: 6
  max_notes: 10

intervals:
  weights: {0: 0.05, 1: 0.18, -1: 0.22, ...}
  first_weights: {0: 0.03, 1: 0.20, ...}
  max_interval: 5
  step_threshold: 1
  step_inertia_boost: 1.3

contour:
  prefer_arch: true
  prefer_descent: false
  range_min: 0
  range_max: 8

target_duration_min: 0.9
target_duration_max: 1.1
scale_pattern: [0, 2, 3, 5, 7, 8, 10]

# --- THREE-AXIS MODEL (memorable.yaml style) ---
# If present, these override the direct configuration

pitch_strategy: stepwise      # or: repetition, leap_fill
rhythm_strategy: long_short   # or: isochronous, ornamental, dance
contour_strategy: arch        # or: descending, ascending, oscillating

# Character bonuses to apply
characters:
  - chromatic
  - ground_compatible
```

### 9.2 Updated MotifStyle Loader

```python
@classmethod
def from_yaml(cls, path: str) -> "MotifStyle":
    """Load style from YAML, supporting both schemas."""
    with open(path, "r", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)

    # Check for three-axis model
    if "pitch_strategy" in data:
        return cls._from_three_axis(data)

    # Otherwise use direct configuration
    return cls._from_direct(data)

@classmethod
def _from_three_axis(cls, data: dict) -> "MotifStyle":
    """Build style from memorable.yaml three-axis model."""

    # Load the base memorable.yaml definitions
    memorable = load_memorable_definitions()

    pitch = memorable.pitch_strategies[data["pitch_strategy"]]
    rhythm = memorable.rhythm_strategies[data["rhythm_strategy"]]
    contour = memorable.contour_strategies[data["contour_strategy"]]

    # Build interval config from pitch strategy
    intervals = IntervalConfig(
        weights=pitch.intervals.weights,
        first_weights=pitch.intervals.get("first_weights", pitch.intervals.weights),
        max_interval=pitch.intervals.max_interval,
        step_threshold=1,
        step_inertia_boost=pitch.intervals.step_inertia_boost,
    )

    # Build rhythm config
    rhythm_config = RhythmConfig(
        meter=tuple(rhythm.meter),
        groupings=[
            RhythmGrouping(pattern=tuple(g["pattern"]), weight=g["weight"])
            for g in rhythm.groupings
        ],
        allow_rests=rhythm.allow_rests,
        min_notes=rhythm.min_notes,
        max_notes=rhythm.max_notes,
    )

    # Build contour config
    contour_config = ContourConfig(
        prefer_arch=(data["contour_strategy"] == "arch"),
        prefer_descent=(contour.shape.direction_bias < 0),
        range_min=0,
        range_max=contour.range.max_semitones // 2,
    )

    # Apply character bonuses
    characters = data.get("characters", [])
    # Characters modify weights and add constraints
    # (implementation details...)

    return cls(
        name=data.get("name", "three_axis"),
        rhythm=rhythm_config,
        intervals=intervals,
        contour=contour_config,
        target_duration_min=data.get("target_duration_min", 0.75),
        target_duration_max=data.get("target_duration_max", 1.0),
        scale_pattern=tuple(data.get("scale_pattern", MAJOR_SCALE)),
    )
```

---

## Part XI: Implementation Roadmap

### Phase 1: Foundation (Core Wiring)

**Goal:** Connect existing pieces without new features.

1. **Fix import paths** in `motif_generator.py`
   - Change `source.datalayer.note` to new structure

2. **Create `AffectStyleMapper`** (`motifs/affect_style.py`)
   - Hardcode 4 affects: Sehnsucht, Klage, Freudigkeit, Majestät
   - Direct mapping to MotifStyle parameters

3. **Update `planner/material.py`**
   - Call `generate_subject()` when no user motif provided
   - Pass affect from brief

4. **Add affect to Brief**
   - Already exists, ensure it's used

**Deliverable:** `python -m scripts.run_planner` generates affect-driven subjects.

### Phase 2: Dramaturgy (Tension & Rhetoric)

**Goal:** Plans have dramatic shape.

1. **Create archetype definitions** (`data/archetypes.yaml`)
   - Define 7 archetypes with rhetoric proportions
   - Define tension curve shapes

2. **Implement `select_archetype()`** (`planner/dramaturgy.py`)
   - Affect → archetype lookup

3. **Implement `compute_rhetorical_structure()`**
   - Scale archetype template to duration

4. **Implement `compute_tension_curve()`**
   - Interpolate archetype-specific shape

5. **Update `plan_structure()`**
   - Use rhetoric boundaries instead of fixed ratios

**Deliverable:** Plans show rhetoric sections and per-bar tension.

### Phase 3: Affect Scoring

**Goal:** Generated subjects actually embody affect.

1. **Create `AffectScorer`** (`motifs/affect_scorer.py`)
   - Signature interval detection
   - Contour matching
   - Rhythm character matching

2. **Create affect profiles** (`data/affects.yaml`)
   - All 8 affects with full specifications

3. **Integrate affect scoring into generation**
   - Combined score = base * 0.5 + affect * 0.5

4. **Add affect-aware mutations to annealer**
   - Mutations that move toward signature intervals

**Deliverable:** Sehnsucht subjects have rising 6ths; Klage subjects descend chromatically.

### Phase 4: Harmonic Architecture

**Goal:** Key schemes serve dramaturgy.

1. **Create key scheme templates** (`data/key_schemes.yaml`)
   - Per archetype, per mode

2. **Implement `plan_harmony()`** (`planner/harmony.py`)
   - Select key scheme
   - Plan cadences per rhetoric position

3. **Update phrase generation**
   - Tonal targets from harmonic plan

**Deliverable:** Plans have coherent harmonic trajectories.

### Phase 5: Device Assignment

**Goal:** Figures serve affect and tension.

1. **Create figurae library** (`data/figurae.yaml`)
   - All figures with affect/rhetoric associations

2. **Implement `assign_devices()`** (`planner/devices.py`)
   - Filter by affect, tension, rhetoric
   - Ensure variety

3. **Add devices to phrase output**

**Deliverable:** Each phrase has appropriate figures assigned.

### Phase 6: Coherence

**Goal:** Pieces have long-range unity.

1. **Implement `plan_coherence()`** (`planner/coherence.py`)
   - Callback planning
   - Proportion validation
   - Surprise injection

2. **Add coherence to plan output**

3. **Validate golden ratio compliance**

**Deliverable:** Plans specify callbacks, climax, surprises.

### Phase 7: Developmental Analysis

**Goal:** Subjects are verified for contrapuntal potential.

1. **Create `DevelopmentalAnalyzer`** (`motifs/developmental.py`)
   - Invertibility scoring
   - Stretto point finding
   - Fragment mapping

2. **Integrate into subject selection**
   - Reject subjects with poor developmental potential

3. **Add developmental report to material**

**Deliverable:** All subjects can be inverted, have stretto points, fragment cleanly.

### Phase 8: Schema Unification

**Goal:** `memorable.yaml` is usable.

1. **Update `MotifStyle.from_yaml()`**
   - Support three-axis model

2. **Create style presets**
   - Canon-like, Toccata-like, Little Fugue-like

3. **Test all style combinations**

**Deliverable:** Any memorable.yaml configuration produces valid subjects.

### Phase 9: Constraint Synthesis

**Goal:** Musical intent becomes solver constraints.

1. **Define constraint vocabulary**
   - Chromatic descent, register extremes, etc.

2. **Implement translation layer**
   - Figure → constraint
   - Tension → constraint
   - Callback → constraint

3. **Generate constraint packages per phrase**

**Deliverable:** Plans include solver-ready constraint packages.

### Phase 10: Validation & Polish

**Goal:** System is robust and documented.

1. **Comprehensive test suite**
   - Each affect produces distinct subjects
   - Archetypes shape tension correctly
   - Figures are compatible

2. **Bob review**
   - Generate 10 plans per affect
   - Evaluate for baroque authenticity

3. **Documentation**
   - Update this document with learnings
   - Create user guide for affect selection

**Deliverable:** Production-ready affect-driven planner.

---

## Part XII: Success Criteria

The improved planner succeeds when:

1. **Affect differentiation** - Listening to a Klage and a Freudigkeit, without knowing labels, a musician identifies the intended affects

2. **Subject recognition** - The subject is memorable; after one hearing, a listener can hum it

3. **Climax perception** - A listener can point to the climax without being told

4. **Resolution satisfaction** - The ending feels earned, not arbitrary

5. **Coherence perception** - A listener notices when the opening returns, senses callbacks

6. **Variety** - Ten pieces with the same affect sound distinct, not templated

7. **Bob approval** - The baroque specialist finds authentic compositional thinking

8. **Computational tractability** - Full plan generation completes in <10 seconds

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| Affect | Emotional state from *Affektenlehre* (e.g., Sehnsucht, Klage) |
| Archetype | Dramatic journey template (e.g., struggle_to_triumph) |
| Rhetoric | Musical structure mapped to classical oratory |
| Exordium | Opening section that captures attention |
| Narratio | Exposition of main material |
| Confutatio | Development, argument, tension building |
| Confirmatio | Resolution, breakthrough |
| Peroratio | Conclusion, closure |
| Tension curve | Per-bar emotional intensity values |
| Figure/*Figura* | Musical gesture from *Figurenlehre* |
| Callback | Motivic reference to earlier material |
| Signature interval | Interval required for affect embodiment |

---

## Appendix B: File Map

```
motifs/
├── affect_style.py         # NEW: AffectStyleMapper
│                           #   - Loads memorable.yaml strategies
│                           #   - Maps affect → pitch/rhythm/contour axes
│                           #   - Applies character bonuses
├── affect_scorer.py        # NEW: AffectScorer
│                           #   - Signature interval detection
│                           #   - Contour matching
│                           #   - Uses memorable.yaml base_constraints
├── developmental.py        # NEW: DevelopmentalAnalyzer
├── subject_generator.py    # NEW: Unified entry point
│                           #   - generate_subject(affect, mode, metre)
│                           #   - Orchestrates full pipeline
├── motif_generator.py      # EXISTING: weighted generation
├── motif_scorer.py         # EXISTING: six-stage scoring
├── motif_annealer.py       # EXISTING: optimization
├── motif_style.py          # MODIFIED: three-axis support
│                           #   - from_yaml() auto-detects schema
│                           #   - _from_three_axis() loads memorable format
│                           #   - _from_direct() loads existing format
└── styles/
    ├── memorable.yaml      # EXISTING: corpus-derived model (Part IX)
    │                       #   - Three-axis definitions
    │                       #   - Character bonuses
    │                       #   - Base constraints
    │                       #   - Corpus classification
    ├── baroque_minuet.yaml # EXISTING: dance style
    └── affects/            # NEW: per-affect configurations
        ├── sehnsucht.yaml  #   - Uses memorable.yaml axes
        ├── klage.yaml      #   - Specifies pitch_strategy, rhythm_strategy
        ├── freudigkeit.yaml#   - Specifies contour_strategy, characters
        ├── majestaet.yaml
        ├── zaertlichkeit.yaml
        ├── zorn.yaml
        ├── verwunderung.yaml
        └── entschlossenheit.yaml

planner/
├── planner.py              # MODIFIED: dramaturgy integration
├── material.py             # MODIFIED: affect-driven generation
│                           #   - Calls generate_subject() when no user motif
│                           #   - Passes affect from brief
├── dramaturgy.py           # NEW: archetype/rhetoric/tension
├── harmony.py              # NEW: key scheme planning
├── devices.py              # NEW: figure assignment
├── coherence.py            # NEW: callback/surprise planning
└── plannertypes.py         # MODIFIED: enhanced types

data/
├── archetypes.yaml         # NEW: archetype definitions
│                           #   - 7 archetypes with rhetoric proportions
│                           #   - Tension curve shapes
│                           #   - Key schemes per mode
├── affects.yaml            # NEW: affect profiles (references Part II)
├── figurae.yaml            # NEW: figure library (Figurenlehre)
├── key_schemes.yaml        # NEW: harmonic templates
└── affect_archetypes.yaml  # NEW: affect → archetype mapping
```

### Data Flow: Affect → Subject

```
Brief.affect (e.g., "Sehnsucht")
    │
    ▼
AffectStyleMapper.to_style()
    │
    ├── Loads motifs/styles/memorable.yaml
    │   └── Gets pitch_strategy: stepwise
    │       Gets rhythm_strategy: long_short
    │       Gets contour_strategy: arch
    │       Gets characters: [chromatic]
    │
    ├── Loads base_constraints from memorable.yaml
    │   └── min_stepwise_percent: 70
    │       triad_outline required
    │       gap_fill after leaps
    │
    ▼
MotifStyle (configured for Sehnsucht)
    │
    ▼
MotifGenerator.generate()
    │
    ▼
MotifScorer.score() + AffectScorer.score()
    │
    ▼
MotifAnnealer.anneal_population()
    │
    ▼
GeneratedSubject
    ├── scale_indices: [0, 2, 4, 5, 8, 7, 5, 4, 2, 0]
    ├── durations: [0.375, 0.125, 0.25, 0.25, ...]
    ├── affect_score: 0.85
    └── developmental: {invertibility: 0.9, stretto_points: [...]}
```

---

*Document version: 2.0*
*Status: Unified design specification*
*Previous version: 1.0 (design only, no integration)*
