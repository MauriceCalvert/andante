# Andante Vocabulary

## Overview

This document defines all permissible keywords and values in the Andante planning system. This document is **normative** — grammar.md and design.md must match these definitions exactly.

For musicological foundations underlying these terms, see grounding.md.

---

## Numeric Types

| Type | Values | Description |
|------|--------|-------------|
| `POS_INT` | 1, 2, 3, ... | Positive integer (bars, voices) |
| `NAT` | 0, 1, 2, ... | Non-negative integer (indices) |
| `FLOAT` | 0.0 to 1.0 | Decimal number (positions) |

---

## Affects

Emotional character governing the piece (German Affektenlehre).

| Value | Description |
|-------|-------------|
| `Sehnsucht` | Yearning, reaching, unresolved longing |
| `Klage` | Grief, lament, heavy sorrow |
| `Freudigkeit` | Joy, brightness, energetic happiness |
| `Majestaet` | Majesty, grandeur, ceremonial nobility |
| `Zaertlichkeit` | Tenderness, gentleness, intimate affection |
| `Zorn` | Anger, fury, violent agitation |
| `Verwunderung` | Wonder, amazement, questioning surprise |
| `Entschlossenheit` | Resolution, determination, firm decisiveness |

---

## Genres

Musical form type. See `data/genres/*.yaml`.

| Value | Description |
|-------|-------------|
| `invention` | Two-voice imitative piece in binary form |
| `fantasia` | Free-form virtuosic piece with contrasting sections |
| `chorale` | Hymn-like homophonic piece |
| `minuet` | Dance in 3/4 with graceful character |
| `gavotte` | Dance in 2/2 starting on half-bar |
| `bourree` | Dance in 2/2 with strong downbeats |
| `sarabande` | Slow dance in 3/4 with emphasis on beat 2 |
| `trio_sonata` | Three-voice chamber work |

---

## Forces

Available instruments.

| Value | Description |
|-------|-------------|
| `keyboard` | Harpsichord, clavichord, or organ |
| `strings` | String ensemble |
| `ensemble` | Mixed instrumental ensemble |

---

## Keys

Pitch class of tonic. All 15 major/minor keys supported.

| Value | Description |
|-------|-------------|
| `C` | C natural |
| `D` | D natural |
| `E` | E natural |
| `F` | F natural |
| `G` | G natural |
| `A` | A natural |
| `B` | B natural |
| `C#` | C sharp |
| `D#` | D sharp |
| `F#` | F sharp |
| `G#` | G sharp |
| `A#` | A sharp |
| `Db` | D flat |
| `Eb` | E flat |
| `Gb` | G flat |
| `Ab` | A flat |
| `Bb` | B flat |

---

## Key Characters

Rhetorical quality of key groups.

| Value | Keys | Description |
|-------|------|-------------|
| `dark` | D, F, Bb | Serious, weighty |
| `bright` | C, G, A | Clear, direct |

---

## Modes

Scale type.

| Value | Description |
|-------|-------------|
| `major` | Ionian mode |
| `minor` | Aeolian mode (with melodic/harmonic alterations) |

---

## Metres

Time signature as (numerator, denominator).

| Value | Description |
|-------|-------------|
| `4/4` | Common time (4 beats per bar, quarter note = 1 beat) |

Format: `n/d` where n = numerator, d = denominator.

---

## Tempi

Tempo marking.

| Value | Description |
|-------|-------------|
| `largo` | Very slow, broad |
| `adagio` | Slow, leisurely |
| `andante` | Walking pace, moderate |
| `moderato` | Moderate speed |
| `allegro` | Fast, lively |
| `vivace` | Lively, brisk |
| `presto` | Very fast |

---

## Degrees

Scale degree within current key.

| Value | Description |
|-------|-------------|
| `0` | Rest (no pitch) |
| `1` | Tonic |
| `2` | Supertonic |
| `3` | Mediant |
| `4` | Subdominant |
| `5` | Dominant |
| `6` | Submediant |
| `7` | Leading tone |

---

## Roman Numerals

Harmonic target as scale degree with quality. Uppercase = major, lowercase = minor.

| Value | Description |
|-------|-------------|
| `I` | Tonic major |
| `II` | Supertonic major |
| `III` | Mediant major (relative major in minor keys) |
| `IV` | Subdominant major |
| `V` | Dominant major |
| `VI` | Submediant major |
| `VII` | Leading tone major |
| `i` | Tonic minor |
| `ii` | Supertonic minor |
| `iii` | Mediant minor |
| `iv` | Subdominant minor |
| `v` | Dominant minor |
| `vi` | Submediant minor (relative minor in major keys) |
| `vii` | Leading tone diminished |

---

## Section Labels

Identifier for formal sections.

| Value | Description |
|-------|-------------|
| `A` - `Z` | Single uppercase letter. Invention uses A, B only. |

---

## Cadences

Phrase-ending harmonic formula.

| Value | Description |
|-------|-------------|
| `authentic` | Dominant to tonic; complete, final |
| `half` | Ends on dominant; incomplete, expectant |
| `deceptive` | Dominant to submediant; surprise, continuation |
| `plagal` | Subdominant to tonic; "Amen" cadence |
| `phrygian` | Stepwise descent to dominant; used in minor |

---

## Voice Generation Concepts

This section defines the vocabulary for how voices are generated. Three distinct concepts were previously conflated under "treatment":

### Passage Function

**Definition**: The compositional role of a passage within the musical form.

**Characteristics**:
- Describes WHAT the passage does in the form
- Does not specify HOW notes are generated
- A two-part invention has: subject entry, answer entry, episodes, development, final statement

| Value | Description |
|-------|-------------|
| `subject` | Initial statement of thematic material |
| `answer` | Imitative response to subject (typically at 4th/5th) |
| `episode` | Free passage connecting thematic entries |
| `development` | Subject/answer material in new keys |
| `cadential` | Passage driving toward cadence |
| `return` | Subject returns in tonic |
| `coda` | Final closing passage |

**Where defined**: Genre YAML → `passage_sequence[].function`


### Voice Expansion

**Definition**: Technical configuration specifying how each voice's notes are derived.

**Characteristics**:
- Describes HOW voices are generated
- Has parameters: source, transform, delay, derivation
- Multiple passage functions may use the same voice expansion

| Value | Description |
|-------|-------------|
| `statement` | Subject direct in lead voice, counter-subject in other |
| `imitation` | Lead voice direct, other voice derives by imitation with delay |
| `stretto` | Compressed imitation (short delay, typically 1/4 bar) |
| `augmentation` | Subject with doubled durations |
| `diminution` | Subject with halved durations |
| `fragmentation` | Subject head sequenced with short delay |
| `inversion` | Subject melodically inverted |
| `retrograde` | Subject reversed |
| `schema` | Both voices follow schema degrees directly |
| `repose` | Lead voice augmented, other sustained |
| `hold` | Both voices sustained |
| `dialogue` | Subject in both, second voice augmented with delay |
| `voice_exchange` | Voices swap material at midpoint |

**Where defined**: `data/treatments/treatments.yaml`


### Function Map

**Definition**: Mapping from passage function to voice expansion type.

**Purpose**: When the form says "this is an answer passage", look up which voice expansion to use.

| Passage Function | Default Voice Expansion |
|------------------|------------------------|
| `subject` | `statement` |
| `answer` | `imitation` |
| `episode` | `schema` |
| `development` | `fragmentation` |
| `cadential` | `repose` |
| `return` | `statement` |
| `coda` | `hold` |

**Where defined**: Genre YAML → `function_map:`


### Lead Voice

**Definition**: Which voice carries the primary thematic material in a passage.

| Value | Description |
|-------|-------------|
| `0` | Upper voice leads (soprano in keyboard) |
| `1` | Lower voice leads (bass in keyboard) |
| `null` | Both voices equal (no leader) |

**Where defined**: Genre YAML → `passage_sequence[].lead_voice`


### Expansion Source

**Definition**: Where a voice's melodic material originates.

| Value | Description |
|-------|-------------|
| `subject` | Use the subject/motif material |
| `counter_subject` | Use counter-subject material |
| `sustained` | Hold a single pitch |
| `pedal` | Repeat pedal tone (tonic or dominant) |
| `schema` | Follow schema degrees |
| `accompaniment` | Generate accompaniment pattern |

**Where defined**: `treatments.yaml` → `{voice}_source`


### Expansion Transform

**Definition**: Melodic transformation applied to source material.

| Value | Description |
|-------|-------------|
| `none` | No transformation |
| `invert` | Melodic inversion (intervals reversed) |
| `retrograde` | Reverse note order |
| `augment` | Double all durations |
| `diminish` | Halve all durations |
| `head` | Use first N notes only |
| `tail` | Use last N notes only |

**Where defined**: `treatments.yaml` → `{voice}_transform`


### Expansion Derivation

**Definition**: How one voice derives from another.

| Value | Description |
|-------|-------------|
| `null` | No derivation (independent) |
| `imitation` | Copy from other voice with delay and interval |

**Where defined**: `treatments.yaml` → `{voice}_derivation`

---

## Surprises

Planned deviation from expectation. See `data/surprises.yaml`.

| Value | Description |
|-------|-------------|
| `deceptive_cadence` | V resolves to vi instead of I |
| `evaded_cadence` | Cadence interrupted, phrase continues |
| `hemiola` | Metric grouping shift (half notes against quarters) |
| `registral_displacement` | Sudden leap to unexpected register |
| `sequence_break` | Sequential pattern breaks after 2 units |
| `subito_forte` | Sudden rise in register |
| `subito_piano` | Sudden drop in register |

---

## Arcs

Dramatic shape of the piece. See `data/arcs.yaml`.

| Value | Description |
|-------|-------------|
| `arch_form` | Symmetric 2-voice form |
| `chorale_4voice` | 4-voice homophonic statements |
| `dance_balanced` | Statement-sequence alternation |
| `dance_contrast` | Contrasting treatments with inversion |
| `dance_stately` | Augmented stately treatment |
| `dialogue` | 3-voice polyphonic call-response |
| `fugue_4voice` | 4-voice fugal exposition and development |
| `hymn` | 4-voice homophonic hymn style |
| `imitative` | 2-voice imitative with development |
| `inverted` | 2-voice with inversions and retrograde |
| `jubilant` | 2-voice celebratory |
| `simple` | 2-voice statement-sequence-statement |

---

## Positions

Location within piece as proportion.

| Value | Numeric | Description |
|-------|---------|-------------|
| `early` | 0.3 | First third |
| `mid` | 0.5 | Centre |
| `late` | 0.7 | Final third |

---

## Articulations

How notes are attacked and released. See `data/articulations.yaml`.

| Value | Description |
|-------|-------------|
| `legato` | Smooth, connected |
| `staccato` | Short, detached |
| `accent` | Emphasized attack |

---

## Rhythms

Durational patterns within a bar. See `data/rhythms.yaml`.

| Value | Description |
|-------|-------------|
| `straight` | Even quarter notes |
| `dotted` | Long-short pairs |
| `lombardic` | Short-long (Scotch snap) |
| `running` | Continuous eighth notes |
| `hemiola` | Half notes creating 2-against-3 metric shift |

---

## Devices

Contrapuntal devices for subject transformation. See `data/devices.yaml`.

| Value | Description |
|-------|-------------|
| `stretto` | Compressed imitation (entries overlap) |
| `augmentation` | Subject with doubled durations |
| `diminution` | Subject with halved durations |
| `invertible` | Double counterpoint at the octave |

---

## Gestures

Rhetorical gestures controlling note-level articulation. See `data/gestures.yaml`.

| Value | Description |
|-------|-------------|
| `statement_open` | Confident opening (accent first, legato downbeats) |
| `question` | Unresolved, expectant (staccato last) |
| `answer` | Resolved, conclusive (accent last) |
| `surprise` | Sudden contrast (accent first, staccato all) |
| `drive` | Building momentum (accent downbeats, staccato upbeats) |
| `rest` | Breathing space (staccato last) |

---

## Ornaments

Melodic decorations applied during realisation. See `data/ornaments.yaml`.

| Value | Description | Trigger |
|-------|-------------|---------|
| `trill` | Rapid alternation with upper neighbor | Cadential notes, long notes |
| `mordent` | Quick lower neighbor oscillation | Beat 1 attacks |
| `turn` | Upper-note-main-lower-main pattern | Descending stepwise motion |

---

## Bass Schemas

Harmonic foundation patterns (partimento style). See `data/bass_schemas.yaml`.

Bass is not derived from soprano — it provides independent harmonic structure. Schemas are keyed by `{tonal_target}_{treatment}`.

| Key Pattern | Description |
|-------------|-------------|
| `I_statement` | Tonic prolongation for statement |
| `I_sequence` | Tonic with passing motion |
| `V_statement` | Dominant arrival |
| `V_sequence` | Dominant with stepwise descent |
| `IV_statement` | Subdominant pattern |
| `IV_sequence` | Subdominant with passing motion |
| `vi_statement` | Relative minor pattern |
| `vi_sequence` | Relative minor with descent |

---

## Textures

Voice relationship patterns. See `data/textures.yaml`.

| Value | Description |
|-------|-------------|
| `polyphonic` | Two independent melodic voices |
| `homophonic` | Voices moving together rhythmically |
| `melody_accompaniment` | Soprano melody with basso continuo |

---

## Episodes

Functional units within sections. See `data/episodes.yaml`.

| Value | Description |
|-------|-------------|
| `statement` | Present thematic material clearly |
| `response` | Answer the statement in another voice |
| `response_cs` | Counter-subject response with subject in bass |
| `continuation` | Spin out from statement, build momentum |
| `sequential` | Sequential modulation |
| `cadential` | Achieve closure with repose |
| `climax` | Maximum tension point |
| `release` | Dissipate tension after climax |
| `coda` | Final closing passage |
| `dialogue` | Call and response between voices |
| `dialogue_invert` | Dialogue with inverted response |
| `exchange` | Subject and counter-subject swap voices |
| `head_motif` | Development using subject head only |
| `tail_motif` | Development using subject tail |
| `intensification` | Drive toward climax |
| `lyrical` | Singing melodic passage |
| `virtuosic` | Display passage requiring technical skill |
| `turbulent` | Agitated developmental passage |
| `triumphant` | Victorious closing passage |
| `cadenza` | Virtuosic quasi-improvisatory passage |
| `arpeggiated` | Arpeggio-based passage work |
| `scalar` | Scale-based passage work |
| `chromatic` | Chromatic approach (transition) |
| `transition` | Bridge between sections |
| `linking` | Brief melodic link |
| `pivot` | Pivot chord modulation |
| `dramatic` | Dramatic pause and restart |
| `retransition` | Prepare return to tonic |
| `bass_statement` | Bass presents theme while soprano holds |
| `bass_sequence` | Bass develops head motif in sequence |
| `bass_development` | Bass develops counter-subject |
| `drive` | Propulsive forward momentum |

---

## Keyword Summary

### Brief (user provides)

| Keyword | Permitted Values |
|---------|------------------|
| `affect` | See Affects section |
| `genre` | See Genres section |
| `forces` | See Forces section |
| `bars` | POS_INT |
| `virtuosic` | true, false (optional, default false) |
| `motif_source` | string or null (optional, e.g., "motif_002") |

### Frame (system derives)

| Keyword | Permitted Values |
|---------|------------------|
| `key` | See Keys section |
| `mode` | major, minor |
| `metre` | n/d format (e.g., 4/4, 3/4, 6/8) |
| `tempo` | See Tempi section |
| `voices` | 2, 3, 4 |
| `form` | through_composed, binary, ternary, rondo |
| `upbeat` | fraction (0 for no upbeat) |

### Section

| Keyword | Permitted Values |
|---------|------------------|
| `label` | A - Z |
| `tonal_path` | list of Roman numerals |
| `final_cadence` | See Cadences section |
| `episodes` | list of Episode |

### Episode

| Keyword | Permitted Values |
|---------|------------------|
| `type` | See Episodes section |
| `bars` | POS_INT |
| `texture` | polyphonic, homophonic, monophonic |
| `phrases` | list of Phrase |
| `is_transition` | true, false |

### Phrase

| Keyword | Permitted Values |
|---------|------------------|
| `index` | NAT |
| `bars` | POS_INT |
| `tonal_target` | See Roman Numerals section |
| `cadence` | See Cadences section, or null |
| `function` | See Passage Function section |
| `expansion` | See Voice Expansion section (optional, uses function_map if omitted) |
| `lead_voice` | 0, 1, or null |
| `surprise` | See Surprises section, or null |
| `is_climax` | true, false |
| `energy` | low, moderate, high, climactic, or null |

### Passage Sequence (in genre YAML)

| Keyword | Permitted Values |
|---------|------------------|
| `symbol` | Short identifier (S, A, E1, etc.) |
| `function` | See Passage Function section |
| `lead_voice` | 0, 1, or null |
| `description` | Human-readable description |

### Function Map (in genre YAML)

| Keyword | Permitted Values |
|---------|------------------|
| `subject` | Voice Expansion name |
| `answer` | Voice Expansion name |
| `episode` | Voice Expansion name |
| `development` | Voice Expansion name |
| `cadential` | Voice Expansion name |
| `return` | Voice Expansion name |
| `coda` | Voice Expansion name |

### Voice Expansion Config (in treatments.yaml)

| Keyword | Permitted Values |
|---------|------------------|
| `{voice}_source` | subject, counter_subject, sustained, pedal, schema, accompaniment |
| `{voice}_transform` | none, invert, retrograde, augment, diminish, head, tail |
| `{voice}_transform_params` | dict (e.g., `{ size: 4 }` for head/tail) |
| `{voice}_derivation` | null, imitation |
| `{voice}_derivation_params` | dict (e.g., `{ interval: -4 }`) |
| `{voice}_delay` | fraction (0, 1/4, 1/2, 1) |
| `{voice}_direct` | true, false |
| `interdictions` | list of disabled features |

### Structure

| Keyword | Permitted Values |
|---------|------------------|
| `arc` | See Arcs section |

### Motif

| Keyword | Permitted Values |
|---------|------------------|
| `degrees` | list of: 1, 2, 3, 4, 5, 6, 7 |
| `durations` | list of positive fractions |
| `bars` | POS_INT |
