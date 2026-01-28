# Clausulae Reference

Compact, machine-usable table of clausula arrivals by mode, with schema mappings.
Distilled from Zarlino → Fux → early 18th-c. practice.

**Status:** Reference for future multi-voice and modal work. Not used in 2-voice generation.

---

## 1. Clausula arrivals by mode

### Major (Ionian)

| Clausula   | Voice role      | Approach → Arrival | Notes                        |
|------------|-----------------|-------------------|------------------------------|
| Cantizans  | Soprano / upper | 7 → 1             | Raised leading tone required |
| Tenorizans | Tenor / inner   | 2 → 1             | May double tonic             |
| Bassizans  | Bass            | 5 → 1             | Sometimes 4 → 5 → 1          |
| Altizans   | Alto / inner    | 4 → 3             | Often with suspension        |

**Strong cadence**: cantizans + bassizans
**Complete cadence**: add tenorizans and/or altizans

---

### Minor (Aeolian, tonal minor)

| Clausula   | Voice role      | Approach → Arrival | Notes                       |
|------------|-----------------|-------------------|------------------------------|
| Cantizans  | Soprano / upper | ♯7 → 1            | Harmonic/melodic inflection  |
| Tenorizans | Tenor / inner   | 2 → 1             | Natural 2                    |
| Bassizans  | Bass            | 5 → 1             | Dominant usually major       |
| Altizans   | Alto / inner    | 4 → ♭3            | Modal color preserved        |

**Important**: minor cadence is *defined* by altered 7, not harmony labels.

---

### Dorian (example: D)

| Clausula   | Approach → Arrival |
|------------|-------------------|
| Cantizans  | C♯ → D            |
| Tenorizans | E → D             |
| Bassizans  | A → D             |
| Altizans   | G → F             |

Rule: **leading tone may be raised locally only at the cadence**.

---

### Phrygian (special case)

| Clausula   | Approach → Arrival |
|------------|-------------------|
| Cantizans  | 7 → 1 (optional)  |
| Tenorizans | ♭2 → 1            |
| Bassizans  | 1 → ♭2 → 1        |

This is the **Phrygian cadence**: closure is driven by the *tenorizans*, not the bass.

---

## 2. Clausula combinations → cadence strength

| Combination present                | Effect                    |
|------------------------------------|---------------------------|
| Cantizans only                     | Weak / rhetorical pause   |
| Bassizans only                     | Harmonic stop, no closure |
| Cantizans + Tenorizans             | Clear melodic closure     |
| Cantizans + Bassizans              | Authentic cadence         |
| Cantizans + Bassizans + Tenorizans | Full cadence              |
| Add Altizans (4–3)                 | Heightened, learned style |

---

## 3. Mapping to common schemata

### Prinner (➏–➎–➍–➌)

- Ends with **tenorizans 2 → 1**
- Often paired with **altizans 4 → 3**
- Bass may *avoid* bassizans → weaker arrival

### Meyer (upper-neighbor figure)

- Arrival typically **cantizans 7 → 1**
- Bass may sustain or move late
- Cadential strength adjustable by bassizans inclusion

### Romanesca

- Cadence often **cantizans + bassizans**
- Tenorizans optional
- Frequently expanded with suspensions

### Fonte / Monte

- Intermediate arrivals: **clausula-like motions without bassizans**
- Final cadence restores full set

---

## 4. Algorithmic application

For CP-SAT / constraint-based generation:

1. Treat **each clausula as a unary voice constraint**
2. Cadence validity = allowed **sets of simultaneous arrivals**
3. Strength = weighted by:
   - presence of cantizans
   - bassizans alignment
   - metric strength
   - suspension resolution before arrival

No Roman numerals required.

---

## 5. Future integration points

| Feature | Clausula application |
|---------|---------------------|
| 3-4 voice textures | Voice-specific clausula constraints |
| Cadence strength API | Weighted scoring from combination table |
| Modal schemas | Phrygian/Dorian clausula sets |
| Suspension generation | Altizans 4-3 as template |

---

*Document version: 1.0*
*Last updated: 2025-01-28*
