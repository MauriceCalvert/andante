# Andante Grammar

## Overview

This document defines the formal structure of Andante data types and YAML files.

**vocabulary.md is normative.** Terminal symbols here must match vocabulary.md exactly. Any divergence is an error.

## Type Grammar

```
Plan        ::= brief: Brief
                frame: Frame
                material: Material
                structure: Structure
                actual_bars: POS_INT
                macro_form: MacroForm | NULL
                tension_curve: TensionCurve | NULL
                rhetoric: RhetoricalStructure | NULL
                harmonic_plan: HarmonicPlan | NULL
                coherence: CoherencePlan | NULL

Brief       ::= affect: AFFECT
                genre: GENRE
                forces: FORCES
                bars: POS_INT
                virtuosic: BOOL
                motif_source: STRING | NULL

Frame       ::= key: KEY
                mode: MODE
                metre: METRE
                tempo: TEMPO
                voices: POS_INT
                upbeat: FRACTION
                form: FORM

Material    ::= subject: Motif
                counter_subject: Motif | NULL
                derived_motifs: [DerivedMotif*]

Motif       ::= degrees: [DEGREE+]
                durations: [FRACTION+]
                bars: POS_INT

DerivedMotif ::= name: STRING
                 degrees: [DEGREE+]
                 durations: [FRACTION+]
                 source: MOTIF_SOURCE
                 transforms: [TRANSFORM+]

Structure   ::= sections: [Section+]
                arc: ARC

Section     ::= label: LABEL
                tonal_path: [ROMAN+]
                final_cadence: CADENCE
                episodes: [Episode+]

Episode     ::= type: EPISODE_TYPE
                bars: POS_INT
                texture: TEXTURE
                phrases: [Phrase+]
                is_transition: BOOL

Phrase      ::= index: NAT
                bars: POS_INT
                tonal_target: ROMAN
                cadence: CADENCE | NULL
                treatment: TREATMENT
                surprise: SURPRISE | NULL
                is_climax: BOOL
                energy: ENERGY | NULL

MacroForm   ::= sections: [MacroSection+]
                climax_section: STRING
                total_bars: POS_INT

MacroSection ::= label: STRING
                 character: STRING
                 bars: POS_INT
                 texture: TEXTURE
                 key_area: ROMAN
                 energy_arc: STRING

TensionCurve ::= points: [TensionPoint+]
                 climax_position: FLOAT
                 climax_level: FLOAT

TensionPoint ::= position: FLOAT
                 level: FLOAT

RhetoricalStructure ::= archetype: ARCHETYPE
                        sections: [RhetoricalSection+]
                        climax_position: FLOAT
                        climax_bar: POS_INT

RhetoricalSection ::= name: RHETORIC_SECTION
                      start_bar: POS_INT
                      end_bar: POS_INT
                      function: STRING
                      proportion: FLOAT

HarmonicPlan ::= targets: [HarmonicTarget+]
                 modulations: [(POS_INT, ROMAN, ROMAN)+]

HarmonicTarget ::= key_area: ROMAN
                   cadence_type: CADENCE
                   bar: POS_INT

CoherencePlan ::= callbacks: [Callback*]
                  climax_bar: POS_INT
                  surprises: [Surprise*]
                  golden_ratio_bar: POS_INT
                  proportion_score: FLOAT

Callback    ::= target_bar: POS_INT
                source_bar: POS_INT
                transform: TRANSFORM
                voice: NAT
                material: MOTIF_SOURCE

Surprise    ::= bar: POS_INT
                beat: FLOAT
                type: SURPRISE_TYPE
                duration: FLOAT
```

## Terminal Symbols

### Core Types
```
AFFECT      ::= "Sehnsucht" | "Klage" | "Freudigkeit" | "Majestaet"
              | "Zaertlichkeit" | "Zorn" | "Verwunderung" | "Entschlossenheit"

GENRE       ::= "invention" | "fantasia" | "chorale" | "minuet"
              | "gavotte" | "bourree" | "sarabande" | "trio_sonata"

FORCES      ::= "keyboard" | "strings" | "ensemble"

KEY         ::= "C" | "D" | "E" | "F" | "G" | "A" | "B"
              | "Bb" | "Eb" | "Ab" | "F#" | "C#"

MODE        ::= "major" | "minor"

METRE       ::= "n/d" where n, d are POS_INT (e.g., "4/4", "3/4", "6/8")

TEMPO       ::= "grave" | "adagio" | "andante" | "moderato"
              | "allegro" | "vivace" | "presto"

FORM        ::= "binary" | "ternary" | "rondo" | "through_composed"

TEXTURE     ::= "polyphonic" | "homophonic" | "monophonic"
```

### Structure Types
```
LABEL       ::= "A" | "B" | "C" | ... | "Z"

ROMAN       ::= "I" | "II" | "III" | "IV" | "V" | "VI" | "VII"
              | "i" | "ii" | "iii" | "iv" | "v" | "vi" | "vii"
              | "#" prefix for chromatic variants

CADENCE     ::= "authentic" | "half" | "deceptive" | "plagal"

ARC         ::= "simple" | "invention_2voice" | "invention_3voice"
              | "dance_binary" | "fugue_3voice" | "fugue_4voice"
              | "chorale_standard" | "fantasia_free" | ...
              (see arcs.yaml for complete list)

TREATMENT   ::= "statement" | "imitation" | "imitation_cs" | "sequence"
              | "stretto" | "inversion" | "retrograde" | "augmentation"
              | "diminution" | "fragmentation" | "head_sequence"
              | "tail_development" | "dialogue" | "dialogue_invert"
              | "pedal_tonic" | "pedal_dominant" | "voice_exchange"
              | "bass_statement" | "bass_sequence" | "bass_development"
              | "melody_accompaniment" | "schema" | "repose" | "hold"
              | "interleaved"
              (see treatments.yaml for complete list)

EPISODE_TYPE ::= "exposition" | "development" | "recapitulation"
               | "episode" | "transition" | "coda" | "cadenza"
               | "sequence" | "stretto" | "pedal_point"
               (see episodes.yaml for complete list)

ENERGY      ::= "low" | "moderate" | "high" | "climactic"

SURPRISE    ::= "evaded_cadence" | "early_return" | "sudden_silence"
              | "register_shift" | "texture_change"
```

### Dramaturgy Types
```
ARCHETYPE   ::= "quest_to_discovery" | "lament_to_acceptance"
              | "playful_dialogue" | "assertion_confirmation"
              | "meditation_deepening" | "storm_to_calm"

RHETORIC_SECTION ::= "exordium" | "narratio" | "confutatio"
                   | "confirmatio" | "peroratio"

SURPRISE_TYPE ::= "pause" | "deceptive_cadence" | "sudden_piano"
                | "register_leap" | "texture_shift"
```

### Material Types
```
DEGREE      ::= 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7

MOTIF_SOURCE ::= "subject" | "counter_subject"

TRANSFORM   ::= "none" | "invert" | "retrograde" | "head" | "tail"
              | "augment" | "diminish" | "inv_retro"
```

### Execution Types
```
ARTICULATION ::= "legato" | "staccato" | "accent" | "tenuto"

RHYTHM      ::= "straight" | "dotted" | "lombardic" | "running"
              | "syncopated" | "hemiola"

DEVICE      ::= "stretto" | "augmentation" | "diminution"
              | "invertible_counterpoint" | "mirror" | "cancrizans"
```

### Primitives
```
POS_INT     ::= positive integer (1, 2, 3, ...)
NAT         ::= non-negative integer (0, 1, 2, ...)
FLOAT       ::= decimal number (0.0 to 1.0 for proportions)
FRACTION    ::= positive rational number (e.g., 1/4, 3/8)
BOOL        ::= true | false
NULL        ::= null
STRING      ::= UTF-8 string
```

## YAML File Grammar

YAML files define templates and defaults. Runtime types (Plan, Section, Phrase) are derived from these templates during planning.

### affects.yaml

```
affects     ::= { AFFECT: affect_def }+

affect_def  ::= description: STRING
                mode: MODE
                tempo: TEMPO
                key_character: KEY_CHAR
                archetype: ARCHETYPE
```

### archetypes.yaml

```
archetypes  ::= { ARCHETYPE: archetype_def }+

archetype_def ::= description: STRING
                  rhetoric_proportions: { RHETORIC_SECTION: FLOAT }+
                  tension_profile: STRING
                  climax_timing: FLOAT
```

### genres/*.yaml

```
genre       ::= voices: POS_INT
                metre: METRE
                form: FORM
                upbeat: FRACTION | NULL
                sections: [section_def+]
                treatment_sequence: [TREATMENT+] | NULL
                characteristic_rhythms: [RHYTHM*]

section_def ::= label: LABEL
                tonal_path: [ROMAN+]
                final_cadence: CADENCE
                bars_per_phrase: POS_INT
                energy_profile: STRING | NULL
```

### arcs.yaml

```
arcs        ::= { ARC: arc_def }+

arc_def     ::= voices: POS_INT
                treatments: [TREATMENT+]
                climax: POSITION | NULL
                surprise: POSITION | NULL
                surprise_type: SURPRISE | NULL
                voice_entries: { POS_INT: [voice_entry+] } | NULL

voice_entry ::= voice: STRING
                treatment: TREATMENT | "rest" | "chordal"
```

### treatments.yaml

```
treatments  ::= { TREATMENT: treatment_def }+

treatment_def ::= soprano_source: SOURCE | NULL
                  soprano_transform: TRANSFORM | NULL
                  soprano_transform_params: PARAMS | NULL
                  soprano_derivation: DERIVATION | NULL
                  soprano_derivation_params: PARAMS | NULL
                  soprano_delay: FRACTION | NULL
                  soprano_direct: BOOL | NULL
                  bass_source: SOURCE | NULL
                  bass_transform: TRANSFORM | NULL
                  bass_transform_params: PARAMS | NULL
                  bass_derivation: DERIVATION | NULL
                  bass_derivation_params: PARAMS | NULL
                  bass_delay: FRACTION | NULL
                  bass_direct: BOOL | NULL
                  pedal_type: PEDAL_TYPE | NULL
                  swap_at: FRACTION | NULL
                  schema: STRING | NULL

SOURCE      ::= "subject" | "counter_subject" | "sustained"
              | "pedal" | "schema" | "accompaniment"

DERIVATION  ::= "imitation"

PEDAL_TYPE  ::= "tonic" | "dominant"

PARAMS      ::= { STRING: VALUE }
```

### episodes.yaml

```
episodes    ::= { EPISODE_TYPE: episode_def }+

episode_def ::= description: STRING
                texture: TEXTURE
                energy: ENERGY
                treatments: [TREATMENT+] | NULL
                bars_range: [POS_INT, POS_INT]
```

### cadences.yaml

```
cadences    ::= internal: { CADENCE: cadence_def }+
                final: { CADENCE: cadence_def }+

cadence_def ::= approach: formula
                resolution: formula

formula     ::= soprano: [DEGREE+]
                bass: [DEGREE+]
                durations: [FRACTION+]
```

### schemas.yaml

```
schemas     ::= { SCHEMA_NAME: schema_def }+

schema_def  ::= soprano: [DEGREE+]
                bass: [DEGREE+]
                durations: [FRACTION+]
                description: STRING
```

### counterpoint_rules.yaml

```
rules       ::= hard_constraints: [constraint+]
                soft_constraints: [constraint+]
                rewards: [reward+]

constraint  ::= name: STRING
                description: STRING
                weight: FLOAT | NULL

reward      ::= name: STRING
                description: STRING
                weight: FLOAT
```

### predicates.yaml

```
predicates  ::= consonances: { INTERVAL: CONSONANCE_TYPE }+
                voice_ranges: { VOICE: { low: POS_INT, high: POS_INT } }+
                ornament_triggers: [trigger+]
                ...

INTERVAL    ::= 0 | 1 | 2 | ... | 12
CONSONANCE_TYPE ::= "perfect" | "imperfect" | "dissonant"
VOICE       ::= "soprano" | "alto" | "tenor" | "bass"
```

### figurae.yaml

```
figurae     ::= { FIGURA_NAME: figura_def }+

figura_def  ::= category: FIGURA_CATEGORY
                affects: [AFFECT+]
                description: STRING
                constraints: constraint_set

FIGURA_CATEGORY ::= "melodic" | "harmonic" | "rhythmic" | "textural"

constraint_set ::= direction: "ascending" | "descending" | NULL
                   motion: "stepwise" | "leaping" | NULL
                   chromatic: BOOL | NULL
                   ...
```

## Constraints

### Structural

- `Plan.structure.sections` must be non-empty
- `Section.episodes` must be non-empty
- `Episode.phrases` must be non-empty
- `Section.label` must be unique within structure
- `Section.tonal_path` must be non-empty
- `Motif.degrees` and `Motif.durations` must have same length
- `Motif.degrees` must have at least one element
- `Motif.durations` must sum to > 0
- `Motif.durations` sum must equal `Motif.bars` x bar_duration(metre)
- `Phrase.index` values must be unique and sequential starting from 0
- Total phrase bars must match `Plan.actual_bars`

### Semantic

- `Section.final_cadence` of last section must be `authentic`
- `Phrase.surprise` can only be non-null if `Phrase.index > 0`
- `Phrase.surprise` cannot be placed on the last phrase of any section
- Last phrase of each section must have `cadence` equal to `Section.final_cadence`
- If `Phrase.surprise` = `evaded_cadence`, then `Phrase.cadence` must be `deceptive`
- Climax phrase derived from `arc.climax` position
- Arc `treatments` count must match phrase count (or use voice_entries)

### Referential

- `Brief.affect` must exist in affects.yaml
- `Brief.genre` must exist as a genre YAML file
- `Brief.forces` must exist in vocabulary/forces
- `Structure.arc` must exist in arcs.yaml
- `Phrase.treatment` must exist in treatments.yaml
- `Episode.type` must exist in episodes.yaml
- All cross-file references must resolve

### YAML Schema

- All YAML files must parse without syntax errors
- All YAML files must conform to their grammar in this document
- All string values must be UTF-8 encoded
- All cross-references must resolve (no dangling references)

---

*Last updated: 2026-01-14*
