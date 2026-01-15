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

## Treatments

How subject material is presented. See `data/treatments.yaml`.

### Core Treatments

| Value | Description |
|-------|-------------|
| `statement` | Subject presented with imitative bass entry |
| `sequence` | Subject repeated at different pitch level |
| `imitation` | Staggered voice entry at the fourth |
| `imitation_cs` | Counter-subject in soprano, subject in bass |
| `inversion` | Subject mirrored around axis |
| `retrograde` | Subject reversed |
| `fragmentation` | Head of subject sequenced |
| `augmentation` | Subject augmented, bass diminished |
| `diminution` | Subject diminished (halved durations) |
| `stretto` | Compressed imitation at the octave |
| `repose` | Subject augmented for cadential approach |

### Independent Treatments

Soprano thematic, bass pattern-based.

| Value | Description |
|-------|-------------|
| `independent` | Subject in soprano, pattern bass |
| `independent_cs` | Counter-subject in soprano, pattern bass |
| `independent_head` | Subject head in soprano, pattern bass |
| `independent_invert` | Inverted subject in soprano, pattern bass |

### Bass-Featured Treatments

| Value | Description |
|-------|-------------|
| `bass_statement` | Subject in bass, sustained soprano |
| `bass_sequence` | Subject head sequenced in bass |
| `bass_development` | Counter-subject developed in bass |

### Dialogue Treatments

| Value | Description |
|-------|-------------|
| `dialogue` | Subject in both voices, bass augmented with delay |
| `dialogue_invert` | Subject in soprano, inverted subject in bass |
| `voice_exchange` | Soprano and bass swap material at midpoint |

### Head/Tail Treatments

| Value | Description |
|-------|-------------|
| `head_sequence` | Subject head sequenced |
| `tail_development` | Subject tail developed |

### Special Treatments

| Value | Description |
|-------|-------------|
| `melody_accompaniment` | Subject melody with accompaniment bass |
| `pedal_tonic` | Soprano melodic, bass sustained on degree 1 |
| `pedal_dominant` | Soprano melodic, bass sustained on degree 5 |
| `schema` | Schema-based soprano and bass |
| `hold` | Both voices sustained |

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
| `treatment` | See Treatments section |
| `surprise` | See Surprises section, or null |
| `is_climax` | true, false |
| `energy` | low, moderate, high, climactic, or null |

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
