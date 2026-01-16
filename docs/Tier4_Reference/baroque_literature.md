# Baroque Composition Theory Reference

Consolidated from: Fux, CPE Bach, Koch, Riepel, Mattheson, Kirnberger, Marpurg, Rameau, IJzerman, Gjerdingen, Lester, Sanguinetti, Caplin, Ratner.

---

## Part I: Voice Leading

### 1.1 Absolute Prohibitions (Hard Constraints)

These produce immediate rejection. No exceptions in strict style.

| Code | Rule | Source | Detection |
|------|------|--------|-----------|
| A1.1 | Parallel fifths | Fux I.14 | Both intervals = 7 (mod 12), same direction, neither stationary |
| A1.2 | Parallel octaves | Fux I.14 | Both intervals = 0 (mod 12), same direction |
| A1.3 | Parallel unisons | Fux I.14 | Both intervals = 0 (absolute), same direction |
| A2.1 | Direct fifth outer voices | Fux I.15 | Similar motion to fifth, soprano leaps |
| A2.2 | Direct octave outer voices | Fux I.15 | Similar motion to octave, soprano leaps |
| A3.1 | Unprepared dissonance on strong beat | Fux II.1 | Dissonance not held over from previous beat |
| A3.2 | Unresolved dissonance | Fux II.2 | Dissonance not followed by step descent |
| A3.3 | Dissonance by leap | Fux II.2 | Dissonance approached or left by leap |
| A3.4 | Dissonance resolved upward | Fux II.3 | Dissonance resolved by ascending step (except leading tone) |
| A4.1 | Voice overlap | Kirnberger II.5 | Current pitch crosses previous pitch of adjacent voice |

**Dissonant intervals**: minor 2nd (1), major 2nd (2), tritone (6), minor 7th (10), major 7th (11).

### 1.2 Legal Dissonances

| Type | Beat | Approach | Departure | Preparation |
|------|------|----------|-----------|-------------|
| Passing tone | Weak | Step | Step (same direction) | None |
| Neighbour tone | Weak | Step | Step (opposite direction) | None |
| Suspension | Strong | Held | Step down | Same pitch on previous weak beat |
| Anticipation | Weak | Any | Held (same pitch follows) | None |
| Appoggiatura | Strong | Leap | Step down | Expressive context |

### 1.3 Soft Constraints (Quality Penalties)

| Code | Rule | Source | Cost |
|------|------|--------|------|
| B1.1 | Hidden fifth inner voices | Kirnberger II.4 | 20 |
| B2.1 | Brief voice crossing (1-2 beats) | Marpurg III.2 | 5 |
| B2.2 | Sustained crossing (3+ beats) | Kirnberger II.5 | 40 |
| B3.1 | >Octave between soprano-alto | Kirnberger III.1 | 15 |
| B3.2 | >Octave between alto-tenor | Kirnberger III.1 | 10 |
| B3.3 | >12th between tenor-bass | Traditional | 5 |
| B4.1 | Augmented melodic interval | Fux I.10 | 30 |
| B4.2 | Melodic seventh | Fux I.10 | 25 |
| B4.3 | Two leaps same direction | Fux I.11 | 15 |
| B4.4 | Leap not compensated by contrary step | Fux I.11 | 10 |
| B4.5 | Tritone outline within 4 notes | Fux I.10 | 20 |
| B5.1 | Same pitch >3 times consecutively | Koch II.3 | 15 |
| B5.2 | Same rhythm >4 bars | Mattheson V.2 | 10 |
| C1.1 | All voices similar motion | Fux I.16 | 12 |
| C1.2 | Parallel thirds >3 beats | Kirnberger II.6 | 8 |
| C1.3 | All voices leap simultaneously | Fux I.17 | 15 |

### 1.4 Quality Rewards (Negative Cost)

| Code | Rule | Source | Reward |
|------|------|--------|--------|
| D1.1 | Contrary motion outer voices | Fux I.16 | -12 |
| D1.2 | Oblique motion | Fux I.16 | -4 |
| D1.3 | Stepwise motion | Fux I.9 | -10 |
| D1.4 | Complementary rhythm | Mattheson IV.3 | -8 |
| D2.1 | Leading tone resolution (up step) | Fux III.2 | -15 |
| D2.2 | 4-3 suspension at cadence | Fux III.3 | -12 |
| D2.3 | 7-6 suspension chain | Fux III.3 | -10 |
| D2.4 | Bass fifths at cadence | Rameau II.3 | -10 |
| D3.1 | Voice contains subject fragment | Marpurg II.4 | -20 |
| D3.2 | Sequential repetition | Mattheson V.4 | -10 |
| D3.3 | Imitation at octave/unison | Marpurg II.1 | -15 |
| D4.1 | Distinct rhythm per voice | Kirnberger IV.2 | -8 |
| D4.2 | Staggered entries | Marpurg II.3 | -6 |

### 1.5 Voice Ranges (MIDI)

| Voice | Comfortable | Extended |
|-------|-------------|----------|
| Soprano | C4-G5 (60-79) | A3-C6 (57-84) |
| Alto | G3-D5 (55-74) | E3-F5 (52-77) |
| Tenor | C3-G4 (48-67) | A2-C5 (45-72) |
| Bass | E2-C4 (40-60) | C2-E4 (36-64) |

---

## Part II: Harmonic Vocabulary

### 2.1 Rule of the Octave

Context-dependent harmonisation of scalar bass. Direction matters.

**Ascending (Major)**

| Degree | Chord | Stability | Notes |
|--------|-------|-----------|-------|
| ① | 5/3 | Stable | Tonic |
| ② | 6/3 or 6/4/3 | Unstable | Optional 4th |
| ③ | 6/3 | Semi-stable | |
| ④ | **6/5/3** | Unstable | Dissonance before ⑤ |
| ⑤ | 5/3 | Stable | Dominant |
| ⑥ | 6/3 | Unstable | |
| ⑦ | **6/5/3** | Unstable | Dissonance before ⑧ |
| ⑧ | 5/3 | Stable | Tonic |

**Descending (Major)**

| Degree | Chord | Notes |
|--------|-------|-------|
| ⑧ | 5/3 | Tonic |
| ⑦ | 6/3 | |
| ⑥ | **#6/4/3** | Raised 6th = leading tone to ⑤ |
| ⑤ | 5/3 | Dominant |
| ④ | **6/4/2** | Strong dissonance from ⑤ |
| ③ | 6/3 | |
| ② | 6/4/3 | |
| ① | 5/3 | Tonic |

**Minor Mode Adjustments**
- Ascending: ⑥ raised, ⑦ raised
- Descending: ⑦ natural, ⑥ natural
- Reason: avoid augmented 2nd between ♭⑥ and ♯⑦

### 2.2 Figured Bass Signatures

| Figure | Chord Type | Bass Position |
|--------|------------|---------------|
| 5/3 (blank) | Root position triad | Root |
| 6 or 6/3 | First inversion | Third |
| 6/4 | Second inversion (dissonant) | Fifth |
| 7 | Seventh chord | Root |
| 6/5 | First inversion seventh | Third |
| 4/3 | Second inversion seventh | Fifth |
| 4/2 (or 2) | Third inversion seventh | Seventh |

**Dissonance Figures**
| Figure | Voice | Resolution |
|--------|-------|------------|
| 9-8 | Upper | 9th resolves to 8ve |
| 7-6 | Upper | 7th resolves to 6th |
| 4-3 | Upper | 4th resolves to 3rd |
| 2-3 | Bass | Bass 2nd resolves up to 3rd |

**9 vs 2 Distinction** (Lester): Figure 9 = upper voice resolves; Figure 2 = bass resolves.

### 2.3 Suspension Patterns

**Two-Voice Suspensions**
| Pattern | Voice | Bass Motion | Preparation |
|---------|-------|-------------|-------------|
| 7-6 | Upper | Descending | Any consonance |
| 2-3 | Lower (bass) | Held | Upper consonance |
| 4-3 | Upper | Ascending or held | 8ve, 3rd, 5th, 6th, min 7th, dim 5th |

**Suspension of the 4th** (Partimenti): The 4th can be prepared by any consonance. Must always be accompanied by the 5th. Cannot appear above notes that don't take 5th.

**Suspension of the 7th**: Prepared by any consonance. Always resolved with 3rd present. Resolves to 3rd (bass 4th/5th) or 6th (bass holds).

**Suspension of the 9th**: Prepared by 3rd or 5th only. Always accompanied by 10th (3rd). Resolves to 8ve, 3rd, or 6th.

### 2.4 Bass Motion Patterns (Moti di Basso)

**Sequential Patterns**

| Pattern | Bass | Options |
|---------|------|---------|
| Up 3rd, down step | ①-③-②-④-③-⑤ | Alt 5/3-6/3; 4-3 suspensions; 7-6 chain |
| Down 3rd, up step | ①-⑥-⑦-⑤-⑥-④ | Alt 5/3-6/3; 5/3-6/5/3; 7-6, 9-8 |
| Up 4th, down 3rd | ①-④-②-⑤-③-⑥ | All 5/3; 9-8 on 4ths; 7-4-3 |
| Down 4th, up step | ①-⑤-⑥-③-④-① | All 5/3; 4-3, 9-8 alternating |
| Up 4th, down 5th (circle) | ①-④-⑦-③-⑥-② | All 5/3; 9-8 suspensions; 7-3-7-3 |
| Up 5th, down 4th | ①-⑤-②-⑥-③-⑦ | All 5/3; 4-3 suspensions |

**Tied Bass**

When bass tied descending by step:
- Each tied note: 4th and 2nd
- Last 4th must be augmented (modulation)
- Returns to same key: major 2nd, perfect 4th
- Changes key: major 2nd, augmented 4th, major 6th

---

## Part III: Galant Schemas

### 3.1 Opening Gambits

**Romanesca**
| Event | Metric | Melody | Bass | Chord |
|-------|--------|--------|------|-------|
| 1 | Strong | ❶/❺ | ① | 5/3 |
| 2 | Weak | variable | ⑦ | 6/3 |
| 3 | Strong | variable | ⑥ | 6/3 |
| 4 | Weak | ❶/❺ | ③ | 6/3 |

Variants: Leaping (5/3 throughout), Stepwise (alternating 5/3-6/3)

**Do-Re-Mi**
| Event | Metric | Melody | Bass | Chord |
|-------|--------|--------|------|-------|
| 1 | Strong | ❶ | ① | 5/3 |
| 2 | Weak | ❷ | ⑦/⑤ | 6/3 |
| 3 | Strong | ❸ | ① | 5/3 |

Easily inverted. Favourite for imitative openings.

### 3.2 Ripostes

**Prinner**
| Event | Metric | Melody | Bass | Chord |
|-------|--------|--------|------|-------|
| 1 | Strong | ❻ | ④ | 5/3 |
| 2 | Weak | ❺ | ③ | 6/3 |
| 3 | Strong | ❹ | ② | 6/3 |
| 4 | Weak | ❸ | ① | 5/3 |

Function: Relaxing response to energetic opening. Ends with weak cadence.

### 3.3 Sequences

**Fonte** (Digression and return)
| Half | Mode | Bass | Function |
|------|------|------|----------|
| 1 | Minor | ⑦-① | Local cadence |
| 2 | Major (step lower) | ⑦-① | Return cadence |

**Monte** (Ascending sequence)
| Section | Bass | Chord |
|---------|------|-------|
| 1 | ⑦-① | 6/5/3 → 5/3 |
| 2 | (step higher) ⑦-① | 6/5/3 → 5/3 |

### 3.4 Thematic Schemas

**Meyer**
| Event | Metric | Melody | Bass | Chord |
|-------|--------|--------|------|-------|
| 1 | Strong | ❶ | ① | 5/3 |
| 2 | Weak | ❼ | ② | 6/3 |
| 3 | Strong | ❹ | ⑦/⑤ | 6/5/3 |
| 4 | Weak | ❸ | ① | 5/3 |

**Sol-Fa-Mi** (Adagio character)
| Event | Metric | Melody | Bass |
|-------|--------|--------|------|
| 1 | Strong | ❺ | ① |
| 2 | Weak | ❹ | ② |
| 3 | Strong | ❹ | ⑦/⑤ |
| 4 | Weak | ❸ | ① |

**Fenaroli** (Second theme)
| Event | Melody | Bass |
|-------|--------|------|
| 1 | ❹/❷ | ⑦ |
| 2 | ❸ | ① |
| 3 | ❼ | ② |
| 4 | ❶ | ③ |

### 3.5 Framing Schemas

**Quiescenza** (Post-cadence)
| Event | Metric | Melody | Bass | Chord |
|-------|--------|--------|------|-------|
| 1 | Weak | ♭❼ | ① | ♭7/3 |
| 2 | Strong | ❻ | ① | 6/4 |
| 3 | Weak | ♮❼ | ① | 7/4/2 |
| 4 | Strong | ❶ | ① | 5/3 |

Bass pedal on ①. Usually played twice.

**Ponte** (Dominant bridge)
- Extended dominant pedal
- Rising melodic contour
- Delays expected resolution

**Indugio** (Teasing delay)
- Iterations on ④
- Often with ♯④ approach
- Leads to converging cadence

---

## Part IV: Phrase Structure

### 4.1 Definitions (Koch)

| Term | German | Definition |
|------|--------|------------|
| Basic phrase | Enger Satz | Minimum content for completeness |
| Extended phrase | Erweiterter Satz | Basic phrase + clarification |
| Compound phrase | Zusammengeschobener Satz | Two+ phrases combined |
| I-phrase | Grundabsatz | Caesura on tonic triad |
| V-phrase | Quintabsatz | Caesura on dominant triad |
| Closing phrase | Schlußsatz | Contains formal cadence |
| Incise | Einschnitt | Incomplete segment of phrase |

### 4.2 Phrase Lengths

| Length | Name | Origin |
|--------|------|--------|
| 4 bars | Vierer | Most common, most pleasing |
| 5 bars | Fünfer | Extended from 4, or unequal segments |
| 6 bars | Sechser | Extended from 4 by 2 measures |
| 7 bars | Siebener | Rare, from extending 5-bar phrases |

### 4.3 Phrase Sequence Rules (Critical)

| First Phrase | Second Phrase | Allowed? | Notes |
|--------------|---------------|----------|-------|
| I-phrase | V-phrase | YES | Most common |
| I-phrase | I-phrase | **NO** | Unpleasant effect |
| V-phrase | I-phrase | **NO** | Not at composition start |
| V-phrase | V-phrase | **NO** (same key) | YES in different keys |
| V-phrase | Cadence | YES | Closes period |
| I-phrase | Cadence | YES | If first cadence in main key |

**Critical**: Neither two I-phrases nor two V-phrases may follow directly in same key with different melodic content.

### 4.4 Caesura Rules

1. Caesuras MUST fall on strong beat
2. Root of caesura chord in bass (except incises may use 6th chord)
3. Decorated caesuras: subsidiary notes, appoggiatura, filled space
4. Fermatas allowed at phrase caesuras (temporarily suspends metre)

### 4.5 Period Structure

**Standard 16-bar Form**
```
First Period (8 bars):
  Phrase 1: I-phrase or V-phrase (4 bars)
  Phrase 2: Cadence in I or V (4 bars)

Second Period (8 bars):
  Phrase 3: Modulation/development (4 bars)
  Phrase 4: Cadence in I (4 bars)
```

**Modulation Rules**
- Major key first period: cadence in V (dominant)
- Minor key first period: cadence in v (minor dominant) OR III (relative major)
- Second period: return to tonic via passing modulations
- Related keys: V, vi, IV, ii for major; III, v, iv, VII for minor

### 4.6 Extension Methods

| Method | Description | Minimum | Rule |
|--------|-------------|---------|------|
| Repetition | Repeat phrase/segment | 1 bar (same key), 2 bars (any key) | If incomplete incises repeated, repeat BOTH |
| Appendix | Clarifying segment after phrase-ending | 1-2 bars | Doesn't change rhythmic value |
| Sequence | Repeat on different scale degrees | 2 bars per segment | MUST maintain segment equality |
| Parenthesis | Insert incidental material | 1 bar after incomplete, 2+ after complete | Preserve segment balance |

**Sequence Warning**: Breaking segment equality produces unpleasant effect. Final segment must equal previous segments.

### 4.7 Compound Phrase Formation

1. **Suppression** (Tacterstickung): Overlap caesura of first phrase with downbeat of second
2. **Entanglement**: Mix segments of two phrases
3. **Interpolation**: Insert complete phrase between segments of another

---

## Part V: Cadences

### 5.1 Cadence Types

| Type | Definition | Strength |
|------|------------|----------|
| Perfect authentic | Bass V-I, soprano to ① | Full stop |
| Imperfect authentic | Bass V-I, soprano to ③ or ⑤ | Weaker stop |
| Half | Ends on V | Comma |
| Deceptive | V-vi | Interrupted |
| Plagal | IV-I | Supplementary |
| Phrygian | iv⁶-V in minor | Baroque slow movement |

### 5.2 Cadence Formulas (Koch)

**Three-Note Formula**
1. Preparation note (strong beat, decorated with passing/neighbour)
2. Cadential note proper
3. Caesura note

**Augmented**: Each note = full measure
**Diminished**: Compressed to fewer beats

### 5.3 Cadence Rules

- Fifth must NEVER appear in soprano at authentic cadence (CPE Bach §36)
- Leading tone MUST resolve up by step
- Bass moves by fifth at cadence (4-1 or 5-1)
- Cadence appendix may repeat closing material or add new segment

### 5.4 Evaded Cadence (Fuggir la Cadenza)

Cadential figuration implies goal but one voice moves differently:
- Terminates on 3rd, 5th, or 6th instead of octave
- Creates intermediate division rather than full stop
- Mid-phrase continuity device

---

## Part VI: Ornamentation

### 6.1 Appoggiatura

**Duration Rules** (CPE Bach)
| Time | Duration |
|------|----------|
| Duple | Half of principal note |
| Triple | Two-thirds of principal |
| Before cadence (fermata) | Long (variable) |
| Before trill | Short or omitted |

**Execution**
- Louder than resolution
- Slurred to following note
- Held until released

### 6.2 Trill

**Rules**
- Always from upper note (CPE Bach §5)
- Practice slowly first, then faster but always evenly (§8)
- Suffix as fast as trill proper (§15)
- No trills on augmented 2nd intervals (§19)
- Short separation between suffix and following note when dotted (§14)

**Types**
| Type | Context |
|------|---------|
| Standard | Long notes, cadences |
| Short (Prall) | Quick notes |
| With suffix | Cadential |
| Ascending | After stepwise rise |

### 6.3 Mordent

**Rules**
- Never on descending seconds (CPE Bach §4)
- Appropriate for short notes, detached passages, bass notes
- Use trill instead for long notes
- May be shortened in very slow tempos (§8)

### 6.4 Turn

**Positions**
| Position | Context |
|----------|---------|
| Over note | Sustained notes |
| After note | Before rest/tie |
| Over dot | Dotted rhythms |
| Snapped | Quick passages |

**Avoid**: Rapid descending passages; congested textures.

### 6.5 Notes Inégales (Dotted Shortening)

Short notes following dotted ones are always shorter in execution than notated (CPE Bach §23).

---

## Part VII: Motif Development

### 7.1 Counter-Subject Design

Counter-subject = counterpoint that consistently accompanies subject.

| Aspect | Subject | Counter-Subject |
|--------|---------|-----------------|
| Rhythm | Slow | Fast |
| Motion | Ascending | Descending |
| Activity | Pausing | Moving |
| Accent | Strong | Weak |

**Constraint**: Must work in invertible counterpoint (either voice can serve as bass).

### 7.2 Motivic Fragmentation

**Head motif** (Kopfmotiv): First 3-4 notes
- Used in false entries, episodes, links
- Most recognizable part
- Brevity allows rapid sequencing

**Tail motif**: Final 3-4 notes
- Contrast material
- Cadential function

### 7.3 Derived Motifs

Transformations create independent material:
- Subject → Inversion → New melodic profile
- Subject → Augmentation → Stately character
- Head + Inversion → Hybrid motif

### 7.4 Episode Material

| Type | Proportion | Source |
|------|------------|--------|
| Subject-derived | 70-80% | Fragments sequenced |
| Free | 20-30% | Scales, arpeggios |

**Episode characteristics**
- 2-4 measures long
- Almost always sequential
- Thinner texture than expositions
- Circle of fifths motion

### 7.5 Invertible Counterpoint

**At the Octave**
| Original | Inverted |
|----------|----------|
| Unison | Octave |
| 2nd | 7th |
| 3rd | 6th |
| 4th | 5th |
| 5th | 4th |

**Restriction**: 5ths become 4ths when inverted. Avoid 5ths in invertible passages.

---

## Part VIII: Affect and Expression

### 8.1 Affektenlehre (Mattheson)

Music expresses specific emotions. Compositional choices flow from intended affect.

**Key Characteristics**
| Key | Character |
|-----|-----------|
| C major | Pure, innocent |
| D major | Sharp, obstinate, martial |
| E major | Piercing, sorrowful |
| F major | Tender, calm |
| G major | Persuading, brilliant |
| A major | Affecting, radiant |
| B♭ major | Magnificent, diversions |
| C minor | Sweet, sad |
| D minor | Devout, tranquil, grand |
| E minor | Pensive, profound |
| G minor | Serious, magnificent |
| A minor | Tender, plaintive |

### 8.2 Expression Rules (CPE Bach)

1. Performer must feel all affects they hope to arouse
2. Every step to remove accompanying parts from melody hand
3. Use variation: caressing ornament, then brilliant, then plain
4. More tones in ornament = longer principal note required
5. Strong outbursts of passion often in recitative, not aria

### 8.3 Slow Movement Character

| Element | Principle |
|---------|-----------|
| Touch | Broad, sustained, never sticky |
| Ornaments | Sustain tone; conceal keyboard decay |
| Dynamics | Express affect; soften resolutions |
| Tempo | Avoid dragging; don't rush |
| Character | Cantabile; from the soul |
| Space | Fill empty gaps without excess |

---

## Part IX: Species Counterpoint

### 9.1 Five Species (Fux)

| Species | Description | Dissonance |
|---------|-------------|------------|
| 1st | Note against note | None |
| 2nd | Two notes per CF note | Weak beat passing |
| 3rd | Four notes per CF note | Beats 2,4 passing/neighbour |
| 4th | Syncopation/ties | Strong beat suspension |
| 5th | Mixed values (florid) | All legal types |

### 9.2 Species-Specific Rules

**First Species**
- Only consonances
- Begin and end on perfect consonance
- Contrary motion preferred

**Second Species**
- Strong beat: consonance only
- Weak beat: consonance or passing
- No repeated notes on consecutive strong beats

**Third Species**
- First note each bar: consonance
- Cambiata figure allowed (leap from dissonance)

**Fourth Species**
- Dissonance on strong beat prepared and resolved
- 7-6, 4-3, 9-8 suspensions preferred
- Forbidden: unison→2nd, 8ve→9th (parallel motion)

**Fifth Species**
- Combines all previous
- Variety of rhythm essential
- Avoid two crotchets at bar start without syncopation

---

## Part X: Fugue Structure

### 10.1 Subject Design (Marpurg)

- Clear tonal answer (real or tonal)
- Outline key (begin/end on tonic or dominant)
- Characteristic rhythm (memorable, not too complex)
- Singable range (usually within tenth)

### 10.2 Answer Types

| Type | When | Adjustment |
|------|------|------------|
| Real | Subject stays in key | Exact transposition at fifth |
| Tonal | Subject outlines I-V | V becomes I, I becomes V at boundary |

### 10.3 Counter-Subject Requirements

- Invertible at octave
- Contrasting rhythm (fill gaps)
- Complementary contour (contrary to subject)

### 10.4 Entry Rules

- Begin only on key-defining intervals: unison, fifth, octave
- If subject spans fifth → answer confined to fourth
- If subject spans fourth → answer confined to fifth

### 10.5 Fugue Cadence Placement

1. First cadence: fifth of key
2. Resume subject in different interval
3. Second cadence: third of key
4. Stretto (closer imitation)
5. Final cadence: tonic

---

## Appendix A: Source Bibliography

### Primary Sources
| Author | Title | Year | Focus |
|--------|-------|------|-------|
| Fux | Gradus ad Parnassum | 1725 | Species counterpoint |
| Rameau | Traité de l'harmonie | 1722 | Chord theory |
| CPE Bach | Versuch (Essay) | 1753-62 | Galant style, ornaments |
| Kirnberger | Art of Strict Musical Composition | 1771-79 | Voice leading synthesis |
| Koch | Versuch einer Anleitung | 1782-93 | Phrase structure |
| Marpurg | Abhandlung von der Fuge | 1753-54 | Fugue, imitation |
| Mattheson | Der vollkommene Capellmeister | 1739 | Affect, rhetoric |
| Niedt | Musicalische Handleitung | 1700-17 | Early partimento |
| Heinichen | Der General-Bass | 1728 | Thorough-bass |
| Quantz | Versuch (flute) | 1752 | Tempo, articulation |
| Türk | Klavierschule | 1789 | Ornament tables |

### Modern Scholarship
| Author | Title | Year | Focus |
|--------|-------|------|-------|
| Gjerdingen | Music in the Galant Style | 2007 | Schema theory |
| Sanguinetti | Art of Partimento | 2012 | Partimento pedagogy |
| IJzerman | Harmony, Counterpoint, Partimento | 2018 | Modern synthesis |
| Lester | Compositional Theory | 1992 | 18th-century theory |
| Caplin | Classical Form | 1998 | Formal function |
| Ratner | Classic Music | 1980 | Topic theory |

---

## Appendix B: Quick Reference Tables

### Interval Classification
| Interval | Semitones | Type |
|----------|-----------|------|
| Unison | 0 | Perfect |
| Minor 2nd | 1 | Dissonant |
| Major 2nd | 2 | Dissonant |
| Minor 3rd | 3 | Imperfect |
| Major 3rd | 4 | Imperfect |
| Perfect 4th | 5 | Dissonant (against bass) |
| Tritone | 6 | Dissonant |
| Perfect 5th | 7 | Perfect |
| Minor 6th | 8 | Imperfect |
| Major 6th | 9 | Imperfect |
| Minor 7th | 10 | Dissonant |
| Major 7th | 11 | Dissonant |
| Octave | 12 | Perfect |

### Doubling Priority
1. Double the bass (if root)
2. Double the root (if bass is not root)
3. Double the fifth
4. Never double leading tone
5. Never double chromatically altered tone
6. Never double seventh

### Motion Priority
1. Contrary (best)
2. Oblique (safe)
3. Similar (careful)
4. Parallel (forbidden for perfect intervals)

---

*Document consolidated: 2026-01-16*
*Sources: Tier4_Reference collection*
