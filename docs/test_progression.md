# Test Progression: 10 Pieces from Easy to Virtuosic

A systematic test suite progressing from Anna Magdalena-level simplicity to toccata-level virtuosity.

## Complexity Dimensions Used

| Dimension | Easy | Hard |
|-----------|------|------|
| Bars | 16 | 150+ |
| Sections | 1 | 5+ |
| Treatments | statement, sequence | stretto, diminution, augmentation |
| Tonal path | I, V | I, V, vi, IV, ii |
| Rhythms | straight | dotted, lombardic, running |
| Texture | polyphonic only | texture switching |
| Energy | stable | full arc (low→peak→resolving) |
| Surprises | none | multiple types |
| Episodes | none | scalar, arpeggiated, cadenza |
| Arc | simple | virtuosic_display |

---

## Level 1: Minuet in G (Anna Magdalena style)

**Reference:** BWV Anh. 114 — 16 bars, simple binary, pedagogical

```yaml
Brief:
  affect: grazioso
  genre: minuet
  forces: keyboard
  bars: 16
```

**Expected characteristics:**
- Key: bright (C, G, or A)
- Mode: major
- Tempo: andante
- Metre: 3/4
- Arc: dance_balanced
- Sections: 2 (A, B with repeats)
- Phrases: 4 total (2 per section)
- Treatments: statement, sequence only
- Tonal path: [I, V], [V, I]
- No surprises
- No texture switching

**Validation criteria:**
- actual_bars ≈ 16
- Simple stepwise subject
- Half cadence end of A, authentic end of B

---

## Level 2: March in D (Anna Magdalena style)

**Reference:** BWV Anh. 122 — sturdier, slightly more active

```yaml
Brief:
  affect: maestoso
  genre: gavotte
  forces: keyboard
  bars: 24
```

**Expected characteristics:**
- Key: dark (Bb, D, or F)
- Mode: major
- Tempo: allegro (gavotte default)
- Metre: 4/4
- Upbeat: 1/2 beat
- Arc: dance_stately
- Sections: 2 (A, B with repeats)
- Phrases: 4-6
- Treatments: statement, sequence, statement
- Tonal path: [I, V], [V, I]
- No surprises yet

**Validation criteria:**
- actual_bars ≈ 24
- Proper half-bar upbeat
- More rhythmic variety than Level 1

---

## Level 3: Bourree in E minor

**Reference:** BWV 996 Bourree — binary dance with character

```yaml
Brief:
  affect: dolore
  genre: bourree
  forces: keyboard
  bars: 24
```

**Expected characteristics:**
- Key: dark
- Mode: minor
- Tempo: adagio (dolore default)
- Metre: 4/4
- Upbeat: 1/4 beat
- Arc: dance_contrast
- Sections: 2
- Phrases: 4-6
- Treatments: statement, sequence, inversion
- Tonal path: [i, III], [III, i] or [i, V], [V, i]

**Validation criteria:**
- Minor mode execution
- Proper quarter-beat upbeat
- More expressive subject (adagio tempo)

---

## Level 4: Two-Part Invention (Simple)

**Reference:** BWV 784 (A minor) — clear, pedagogical invention

```yaml
Brief:
  affect: giocoso
  genre: invention
  forces: keyboard
  bars: 24
```

**Expected characteristics:**
- Key: bright (C, G, or A)
- Mode: major
- Tempo: allegro
- Metre: 4/4
- Arc: simple
- Sections: 2 (A, B)
- Phrases: 4
- Treatments: [statement, sequence, statement, sequence]
- Tonal path: [I, V], [V, I]
- No surprises

**Validation criteria:**
- 2-bar subject
- Clear imitative texture
- Through-composed (no repeats in invention)

---

## Level 5: Two-Part Invention (Standard)

**Reference:** BWV 772 (C major) — the classic model

```yaml
Brief:
  affect: maestoso
  genre: invention
  forces: keyboard
  bars: 32
```

**Expected characteristics:**
- Key: dark (Bb, D, or F)
- Mode: major
- Tempo: adagio
- Metre: 4/4
- Arc: standard
- Sections: 2
- Phrases: 4
- Treatments: [statement, sequence, fragmentation, inversion]
- Tonal path: [I, V], [V, I]
- Surprise: evaded_cadence at mid-point

**Validation criteria:**
- More sophisticated treatment arc
- One surprise element
- Fragmentation and inversion present

---

## Level 6: Two-Part Invention (Imitative)

**Reference:** BWV 779 (F major) — more contrapuntal

```yaml
Brief:
  affect: giocoso
  genre: invention
  forces: keyboard
  bars: 40
```

**Expected characteristics:**
- Key: bright
- Mode: major
- Tempo: allegro
- Arc: imitative
- Sections: 2
- Phrases: 6
- Treatments: [statement, imitation, sequence, imitation, fragmentation, statement]
- Tonal path: [I, I, V], [V, vi, I]
- Extended tonal journey (touch vi)
- Gesture: drive on climax phrase

**Validation criteria:**
- Imitation treatment used
- 3 tonal targets per section
- ~40 bars actual

---

## Level 7: Fantasia (Short)

**Reference:** BWV 906 — episodic but contained

```yaml
Brief:
  affect: furioso
  genre: fantasia
  forces: keyboard
  bars: 60
```

**Expected characteristics:**
- Key: dark
- Mode: minor
- Tempo: presto
- Arc: stormy_lyrical_triumphant
- Sections: 3 (A, B, C)
- Phrases: 12+
- Treatments: full range including stretto
- Tonal path: Section A [i, i, i], B [III, III, V], C [i, i, i]
- Texture switching: polyphonic ↔ melody_accompaniment
- Energy progression: moderate → peak → resolving
- Episodes: statement, scalar, arpeggiated

**Validation criteria:**
- 3 distinct sections
- Minor mode throughout
- Texture changes between sections
- Energy arc present

---

## Level 8: Fantasia (Extended)

**Reference:** BWV 903 Chromatic Fantasia — dramatic, episodic

```yaml
Brief:
  affect: dolore
  genre: fantasia
  forces: keyboard
  bars: 90
```

**Expected characteristics:**
- Key: dark
- Mode: minor
- Tempo: adagio
- Arc: arch_form
- Sections: 4 (A, B, C, D)
- Phrases: 20+
- Treatments: statement, sequence, stretto, fragmentation, diminution, augmentation
- Tonal path: Extended journey (i → III → V → iv → i)
- Energy: low → rising → peak → falling → resolving
- Surprises: registral_displacement, subito_piano
- Episodes: scalar, arpeggiated, intensification, cadenza

**Validation criteria:**
- 4 sections with return to tonic
- Cadenza episode present
- Multiple surprise types
- ~90 bars

---

## Level 9: Toccata (Virtuosic)

**Reference:** BWV 912 (D major) — display piece

```yaml
Brief:
  affect: giocoso
  genre: fantasia
  forces: keyboard
  bars: 120
```

**Expected characteristics:**
- Key: bright
- Mode: major
- Tempo: allegro
- Arc: virtuosic_display
- Sections: 5 (A, B, C, D, E)
- Phrases: 30+
- Treatments: full vocabulary
- Tonal path: I → V → vi → IV → I
- Texture: frequent switching
- Energy: moderate → rising → peak → peak → resolving
- All episode types
- Multiple surprises: sequence_break, hemiola

**Validation criteria:**
- 5 sections
- Counter-subject present
- 30+ phrases
- ~120 bars

---

## Level 10: Toccata and Fugue (Magnum Opus)

**Reference:** BWV 565 (D minor) — the summit

```yaml
Brief:
  affect: furioso
  genre: fantasia
  forces: keyboard
  bars: 150
```

**Expected characteristics:**
- Key: dark
- Mode: minor
- Tempo: presto
- Arc: tempestuous
- Sections: 5+ (with potential sub-sections)
- Phrases: 34+
- Treatments: every available treatment
- Tonal path: i → III → V → iv → VI → V → i
- Texture: polyphonic dominates with melody_accompaniment episodes
- Energy: full dramatic arc with multiple peaks
- All surprise types deployed
- All episode types
- Counter-subject with independent character

**Validation criteria:**
- 5+ sections
- 150+ bars
- Counter-subject present
- Full treatment vocabulary used
- Complex tonal journey with 6+ targets
- Multiple energy peaks

---

## Execution Script

```python
# scripts/run_progression.py
BRIEFS = [
    {"affect": "grazioso", "genre": "minuet", "bars": 16},
    {"affect": "maestoso", "genre": "gavotte", "bars": 24},
    {"affect": "dolore", "genre": "bourree", "bars": 24},
    {"affect": "giocoso", "genre": "invention", "bars": 24},
    {"affect": "maestoso", "genre": "invention", "bars": 32},
    {"affect": "giocoso", "genre": "invention", "bars": 40},
    {"affect": "furioso", "genre": "fantasia", "bars": 60},
    {"affect": "dolore", "genre": "fantasia", "bars": 90},
    {"affect": "giocoso", "genre": "fantasia", "bars": 120},
    {"affect": "furioso", "genre": "fantasia", "bars": 150},
]
```

## Validation Checklist

For each piece, verify:

1. **Structural integrity**
   - [ ] All sections have phrases
   - [ ] Phrase indices sequential
   - [ ] Tonal path matches phrase count

2. **Musical coherence**
   - [ ] Final cadence is authentic
   - [ ] Surprises not on final phrase
   - [ ] Energy arc makes musical sense

3. **Complexity scaling**
   - [ ] Bars increase monotonically
   - [ ] Treatment variety increases
   - [ ] Tonal complexity increases

4. **Execution success**
   - [ ] YAML parses without error
   - [ ] MIDI generates successfully
   - [ ] MusicXML validates
   - [ ] No guard violations (parallel fifths/octaves)

## Success Metrics

| Level | Min Bars | Max Bars | Sections | Treatments Used |
|-------|----------|----------|----------|-----------------|
| 1 | 14 | 20 | 2 | 2 |
| 2 | 20 | 28 | 2 | 3 |
| 3 | 20 | 28 | 2 | 3 |
| 4 | 20 | 28 | 2 | 2 |
| 5 | 28 | 36 | 2 | 4 |
| 6 | 36 | 44 | 2 | 5 |
| 7 | 50 | 70 | 3 | 6 |
| 8 | 80 | 100 | 4 | 8 |
| 9 | 110 | 130 | 5 | 10 |
| 10 | 140 | 160 | 5+ | all |
