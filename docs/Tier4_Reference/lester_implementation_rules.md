# Lester: Compositional Theory in the Eighteenth Century
## Implementation-Relevant Rules Extracted

Source: Joel Lester, *Compositional Theory in the Eighteenth Century* (Harvard, 1992)
OCR: D:/projects/Barok/barok/source/andante/docs/Tier4_Reference/compositional-theory-in-the-eighteenth-century.txt

---

## 1. Voice-Leading Rules (Zarlino/Fux tradition)

### Parallel Motion
- **Parallel 5ths/8ves forbidden** — loss of voice independence, no harmonic variety
- **Hidden (direct) 5ths/8ves** — Zarlino selectively approves in two-voice writing (p.29); Fux more restrictive
- **Consecutive major 3rds** — Zarlino bans; consecutive minor 6ths also banned
- **Consecutive minor 3rds/major 6ths** — Zarlino barely tolerates

### Approach to Perfect Consonances
- Imperfect consonance → perfect consonance: use closest imperfect interval
- Major 6th → octave (standard cadential motion)
- Minor 3rd → unison (with chromatic alteration if needed)
- Similar motion into perfect consonances requires caution (varies by theorist)

### Suspension Resolution
- Resolution of suspension may NOT be held to become a perfect consonance (Zarlino, p.28)
- Suspended 4th: prepared by preceding consonance, resolves down to 3rd
- Suspended 7th: prepared, resolves down; always with 3rd present
- Suspended 9th: prepared by 3rd or 5th; resolves to 8ve, 3rd, or 6th
- 5th in 6/5 chord: treated as suspension, must resolve (p.11)

### Thoroughbass Dissonance Categories
- **9 vs 2 distinction**: 9 = upper voice resolves; 2 = bass resolves (p.56)
- **Regular 4th**: prepared, resolves by stepwise descent (4-3)
- **Irregular 4th**: not prepared, need not resolve stepwise (4/3 chords)
- Dissonances figured as 6-5, 9-8, 4-3 indicate voice that moves

---

## 2. Cadence Formulas

### Two-Voice Cadences (Zarlino)
- Final unison: preceded by minor 3rd (chromatic alteration permitted)
- Final octave: preceded by major 6th
- Cadences are formulas where penultimate must move to final — functional requirement

### Evaded Cadences (fuggir la cadenza)
- Cadential figuration implies goal but one voice moves differently
- Creates intermediate divisions rather than full stops
- May terminate on 3rd, 5th, or 6th instead of unison/octave
- Rameau made this principal explanation for mid-phrase continuity

### Cadence Types (general)
- Perfect cadence: concludes on unison/octave with proper approach
- Imperfect cadence: concludes on imperfect consonance (3rd, 5th, 6th)
- Half cadence: motion to dominant
- Deceptive: V→vi (bass rises step instead of falling 5th)

---

## 3. Phrase Structure (Riepel/Koch)

### Riepel's Expansion/Contraction Method
- Same material can be realized at different lengths
- Brief 2+2 bar version ↔ expanded 4+4+4 bar version
- Each version has its own integrity with balanced phrases
- Relationship like thoroughbass: same progression, different elaboration

### Hierarchical Levels
- Most abstract: letter names only (C-G-C = key scheme)
- At all levels above key scheme: actual compositions, not analyses
- Longer versions add:
  - Motivic parallelisms
  - Sequential extensions
  - Prefix/suffix material
  - Contrasting middle sections

### Phrase Transformations
- Reversed cadence order (tonic cadence → dominant cadence or vice versa)
- Repetition of closing material
- Insertion of contrasting phrase in parallel minor
- Sequential expansion of opening motives

---

## 4. Figured Bass Signatures

### Basic Chord Types
- 5/3 (or blank): root position triad
- 6 (or 6/3): first inversion
- 6/4: second inversion (treated as dissonance, resolves)
- 7: seventh chord
- 6/5: first inversion seventh
- 4/3: second inversion seventh
- 4/2 (or 2): third inversion seventh

### Dissonance Figures
- 9-8: upper voice suspension resolving
- 7-6: seventh resolving to sixth
- 4-3: fourth resolving to third
- 6-5: sixth moving to fifth (not always dissonance)
- 2: bass suspension (bass must resolve up)

### Context Rules (from Heinichen 1728)
- Same figuring can mean different harmonies depending on context
- 4/3 with prepared 4th → suspension pattern
- 4/3 without preparation → "irregular fourth" (passing)
- Mi in bass typically takes 6 (first inversion on 3rd/7th scale degrees)

---

## 5. Species Counterpoint (Fux) — Implementation Notes

### Structure
- Book 1: Two-voice counterpoint through five species
- Book 2: Three-voice counterpoint
- Book 3: Four-voice counterpoint
- Book 3 also: imitation, fugue, invertible counterpoint

### Five Species
1. **First species**: whole notes against whole notes (1:1)
2. **Second species**: two half notes per whole note (2:1)
3. **Third species**: four quarter notes per whole note (4:1)
4. **Fourth species**: tied half notes (syncopation/suspension)
5. **Fifth species**: mixed values (florid counterpoint)

### Key Limitations of Fux
- No discussion of modern dissonance types beyond simple passing/neighbor/suspension
- No seventh chords as entities
- No harmonic functionality mid-phrase
- Recitative dissonances treated as rhetorical figures, not systematic

---

## 6. Invertible Counterpoint

### Definition
- Counterpoint where voices can exchange registers while maintaining good voice-leading
- Most common: at the octave (voices swap)
- Also: at the 10th, 12th

### Interval Transformations at 8ve
- 1 ↔ 8 (unison ↔ octave)
- 2 ↔ 7 (second ↔ seventh)
- 3 ↔ 6 (third ↔ sixth)
- 4 ↔ 5 (fourth ↔ fifth)

### Restrictions
- Perfect 5th becomes perfect 4th when inverted — problematic
- Avoid 5ths in invertible counterpoint passages
- Use 3rds and 6ths freely
- Seconds/sevenths usable with proper preparation/resolution

---

## 7. Cross-References to Andante Implementation

### Already Documented Elsewhere
- Rule of Octave: see partimenti_rule_of_octave.md
- Galant schemas: see partimenti_schemas.md
- Bass motion patterns: see partimenti_regole.md
- CPE Bach ornaments: see cpe_bach_rules.yaml

### Implementation Priorities
1. **voice_checks.py**: Direct 5ths/8ves outer voices; hidden 5ths check; suspension resolution
2. **figured_bass.py**: 9 vs 2 distinction; irregular 4th handling
3. **planner/phrase_extension.py**: Riepel-style expansion/contraction
4. **engine/cadence.py**: Evaded cadence patterns

### Key Insight
Lester emphasizes that 18th-century theorists understood dissonances primarily through figured bass context, not through abstract chord theory. Implementation should:
- Track preparation and resolution at the figuring level
- Use context (preceding/following bass) to determine chord type
- Treat suspensions as voice-leading events, not as chord members

---

## Page Reference Guide

| Topic | Book Pages | OCR Lines (approx) |
|-------|------------|-------------------|
| Zarlino voice-leading | 26-30 | 992-1200 |
| Cadences | 28-29 | 1083-1140 |
| Fux species | 46-48 | 1700-1900 |
| Thoroughbass | 49-70 | 2100-3500 |
| Riepel phrases | 258-272 | 13000-13600 |
| Koch structure | 273-299 | 13600-14800 |
