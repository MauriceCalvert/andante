# Walkthrough 1: Two-Part Invention in C Major

## Status

REVISED — follows architecture.md scrupulously.

---

## Given

- **Genre:** Two-part invention
- **Key:** C major
- **Affect:** Confident, direct
- **Metre:** 4/4 (common time)

---

## Layer 1: Rhetorical

**Input:** Genre = invention

**Output:** Fixed trajectory:
```
Exordium → Narratio → Confirmatio → Peroratio
```

**Decision:** None required. Genre determines this.

✓ Complete

---

## Layer 2: Tonal

**Input:** Affect = confident, direct

**Output:** From lookup table:

| Section | Key area | Cadence type |
|---------|----------|--------------|
| Exordium | I (C major) | Open |
| Narratio | I → V | Authentic in V |
| Confirmatio | V → I | Open |
| Peroratio | I (C major) | Perfect authentic in I |

✓ Complete

---

## Layer 3: Schematic

**Input:** Tonal plan above

**Output:** Schema chain with transition verification

### Transition Rules (from architecture.md)

Schema B can follow schema A if bass connection is:
1. Identity: same pitch
2. Step: semitone or whole tone
3. Dominant: degree 5 resolving to degree 1

If none apply: **free passage required**.

For sequential schemas (Monte, Fonte): degrees are pitches in local tonicisation.

---

### Schema Chain Construction

#### Exordium: Do-Re-Mi (C major)

| Stage | Soprano | Bass | Arrival |
|-------|---------|------|---------|
| 1 | 1 = C4 | 1 = C3 | (1,1) ✓ consonant P8 |
| 2 | 2 = D4 | 7 = B2 | (2,7) ✓ consonant m10 |
| 3 | 3 = E4 | 1 = C3 | (3,1) ✓ consonant M10 |

**Exit:** 3/1 in C = E4/C3

---

#### Transition: Do-Re-Mi → Monte

- Exit pitch: C3 (bass)
- Monte entry: 4/7 in IV (F major) = Bb3/E3
- Bass: C3 → E3 = major 3rd (4 semitones)
- **Not identity, not step, not dominant**
- **FREE PASSAGE REQUIRED**

Free passage: C3 → D3 → E3 (stepwise, 2 beats)

---

#### Narratio: Monte (IV → V)

**Segment 1 (F major tonicisation):**

| Stage | Soprano | Bass | Interval |
|-------|---------|------|----------|
| Entry | 4 = Bb4 | 7 = E3 | (4,7) = dim12 — prepared dissonance |
| Exit | 3 = A4 | 1 = F3 | (3,1) = M10 ✓ consonant |

**Segment 2 (G major tonicisation):**

| Stage | Soprano | Bass | Interval |
|-------|---------|------|----------|
| Entry | 4 = C5 | 7 = F#3 | (4,7) = dim12 — prepared dissonance |
| Exit | 3 = B4 | 1 = G3 | (3,1) = M10 ✓ consonant |

**Chromatic notes:** E natural (leading tone of F), F# (leading tone of G)

**Exit:** 3/1 in G = B4/G3

---

#### Transition: Monte → Cadenza composta

- Exit pitch: G3 (bass)
- Cadenza entry: 4/4 in G = C4/C3
- Bass: G3 → C3 = perfect 4th (5 semitones)
- **Not identity, not step, not dominant**
- **FREE PASSAGE REQUIRED**

Free passage: G3 → F3 → E3 → D3 → C3 (stepwise descent, 2 beats)

---

#### Narratio: Cadenza composta (G major)

| Stage | Soprano | Bass | Interval |
|-------|---------|------|----------|
| 1 | 4 = C5 | 4 = C3 | (4,4) = P15 ✓ |
| 2 | 3 = B4 | 5 = D3 | (3,5) = M13 ✓ |
| 3 | 2 = A4 | 5 = D3 | (2,5) = P12 ✓ |
| 4 | 1 = G4 | 1 = G2 | (1,1) = P15 ✓ PAC in V |

**Exit:** 1/1 in G = G4/G2

---

#### Transition: Cadenza composta → Fonte

- Exit pitch: G2 (bass)
- Fonte entry: 4/7 in ii of C (A minor) = D4/G#2
- Bass: G2 → G#2 = chromatic semitone
- **STEP ✓ DIRECT CONNECTION**

---

#### Confirmatio: Fonte (ii → I)

**Segment 1 (A minor tonicisation):**

| Stage | Soprano | Bass | Interval |
|-------|---------|------|----------|
| Entry | 4 = D4 | 7 = G#2 | (4,7) = dim12 — prepared dissonance |
| Exit | 3 = C4 | 1 = A2 | (3,1) = m10 ✓ consonant |

**Segment 2 (C major):**

| Stage | Soprano | Bass | Interval |
|-------|---------|------|----------|
| Entry | 4 = F4 | 7 = B2 | (4,7) = dim12 — prepared dissonance |
| Exit | 3 = E4 | 1 = C3 | (3,1) = M10 ✓ consonant |

**Chromatic notes:** G# (leading tone of A minor)

**Exit:** 3/1 in C = E4/C3

---

#### Transition: Fonte → Passo Indietro

- Exit pitch: C3 (bass)
- Passo entry: 6/4 in C = A3/F3
- Bass: C3 → F3 = perfect 4th (5 semitones)
- **Not identity, not step, not dominant**
- **FREE PASSAGE REQUIRED**

Free passage: C3 → D3 → E3 → F3 (stepwise ascent, 2 beats)

---

#### Confirmatio: Passo Indietro (C major)

| Stage | Soprano | Bass | Interval |
|-------|---------|------|----------|
| 1 | 6 = A4 | 4 = F3 | (6,4) = M10 ✓ |
| 2 | 5 = G4 | #4 = F#3 | chromatic — passing |
| 3 | 5 = G4 | 5 = G3 | (5,5) = P8 ✓ |

**Chromatic notes:** F# (raised 4)

**Exit:** 5/5 in C = G4/G3

---

#### Transition: Passo Indietro → Cadenza composta

- Exit pitch: G3 (bass)
- Cadenza entry: 4/4 in C = F3/F3
- Bass: G3 → F3 = whole tone
- **STEP ✓ DIRECT CONNECTION**

---

#### Peroratio: Cadenza composta (C major)

| Stage | Soprano | Bass | Interval |
|-------|---------|------|----------|
| 1 | 4 = F4 | 4 = F3 | (4,4) = P8 ✓ |
| 2 | 3 = E4 | 5 = G3 | (3,5) = m13 ✓ |
| 3 | 2 = D4 | 5 = G3 | (2,5) = P12 ✓ |
| 4 | 1 = C4 | 1 = C3 | (1,1) = P8 ✓ PAC in I |

**Exit:** 1/1 in C = C4/C3

---

## Complete Schema Chain

| Section | Schema | Key | Exit | Connection to next |
|---------|--------|-----|------|-------------------|
| Exordium | Do-Re-Mi | C | E/C | free (C→E, M3) |
| | *free passage* | — | —/E | 2 beats |
| Narratio | Monte seg.1 | F | A/F | internal |
| | Monte seg.2 | G | B/G | free (G→C, P4) |
| | *free passage* | — | —/C | 2 beats |
| | Cadenza composta | G | G/G | **direct** (G→G#, step) |
| Confirmatio | Fonte seg.1 | Am | C/A | internal |
| | Fonte seg.2 | C | E/C | free (C→F, P4) |
| | *free passage* | — | —/F | 2 beats |
| | Passo Indietro | C | G/G | **direct** (G→F, step) |
| Peroratio | Cadenza composta | C | C/C | — |

**Direct connections:** 2
**Free passages:** 3

---

## Layer 4: Metric

**Input:** Schema chain with stage counts

**Constraint:** assigned_beats ≥ schema_stages

| Schema | Stages | Assigned bars | Beats |
|--------|--------|---------------|-------|
| Do-Re-Mi | 3 | 2 | 8 ✓ |
| Free passage | — | 0.5 | 2 |
| Monte (2 seg) | 4 | 2 | 8 ✓ |
| Free passage | — | 0.5 | 2 |
| Cadenza composta | 4 | 1.5 | 6 ✓ |
| Fonte (2 seg) | 4 | 2 | 8 ✓ |
| Free passage | — | 0.5 | 2 |
| Passo Indietro | 3 | 1 | 4 ✓ |
| Cadenza composta | 4 | 1.5 | 6 ✓ |

**Total: 11.5 bars** — compact invention

---

## Layer 5: Thematic

**Input:** Opening schema = Do-Re-Mi + bar assignments from Layer 4

**Subject:** Must hit soprano degrees 1–2–3 at arrival beats.

Example subject (2 bars):
```
Bar 1                      Bar 2
Beat: 1    2    3    4  |  1    2    3    4  |
Sop:  C    D    E    D  |  E    F    E    D  | → continues
Deg:  1         2       |  3                 |
Bass: C              B  |  C              B  | (simplified)
Deg:  1              7  |  1                 |
```

✓ Subject satisfies Do-Re-Mi arrivals

---

## Layer 6: Textural

**Input:** Genre = invention

**Output:** Treatment sequence:

| Section | Bars | Treatment |
|---------|------|-----------|
| Exordium | 1–2 | Subject (soprano) |
| Narratio | 2.5–6.5 | Episode (sequences) + Cadence in V |
| Confirmatio | 6.5–10 | Episode (sequences) + approach |
| Peroratio | 10–11.5 | Final cadence |

---

## Realisation Checklist

Before generating notes, verify:

- [ ] All arrivals use consonant intervals (P1, m3, M3, P5, m6, M6, P8, compounds)
- [ ] Dissonances (4,7) prepared by previous beat, resolved by step
- [ ] No parallel P5 or P8 between consecutive beats
- [ ] Chromatic notes: G# in Fonte seg.1, F# in Monte seg.2 and Passo Indietro
- [ ] Free passages use stepwise motion, counterpoint rules only

---

## Document History

| Date | Change |
|------|--------|
| 2025-01-20 | Initial draft |
| 2025-01-20 | Complete rewrite following architecture.md |
