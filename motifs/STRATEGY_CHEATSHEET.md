# Memorable Melody Strategy Cheat Sheet

## Quick Reference Table

| Piece         | Pitch      | Rhythm      | Contour     | Character                    |
|---------------|------------|-------------|-------------|------------------------------|
| Canon         | stepwise   | isochronous | descending  | ground_compatible            |
| Dido bass     | stepwise   | long_short  | descending  | chromatic, ground_compatible |
| Dido vocal    | stepwise   | long_short  | arch        | chromatic                    |
| Toccata       | stepwise   | ornamental  | descending  | mordent_identity, silence    |
| Little Fugue  | leap_fill  | long_short  | arch        | triad_skeleton               |
| Primavera     | repetition | ornamental  | oscillating | phrase_repeat                |
| Hallelujah    | repetition | isochronous | ascending   | obsessive                    |
| Brandenburg   | stepwise   | ornamental  | oscillating | mordent_identity             |
| Tambourin     | stepwise   | dance       | oscillating | mordent_identity             |
| La Folia      | stepwise   | dance       | descending  | ground_compatible            |

---

## AXIS 1: Pitch Strategy

| Strategy    | Description                           | Interval Character                  | Examples                |
|-------------|---------------------------------------|-------------------------------------|-------------------------|
| `stepwise`  | Conjunct motion dominates             | 73% m2/M2, rare leaps resolve       | Canon, Dido, Toccata    |
| `repetition`| Repeated notes as foundation          | 35% unison, leaps punctuate         | Hallelujah, Primavera   |
| `leap_fill` | Large interval + stepwise fill        | Opens with P4/P5, then steps down   | Little Fugue            |

### Interval Weights Summary

```
stepwise:    0=12%, ±1=46%, ±2=30%, ±3=7%, ±4=4%, ±5=1%
repetition:  0=35%, ±1=26%, ±2=22%, ±3=10%, ±4=6%, ±7=1%
leap_fill:   First: P5=27%, P4=24%, M3=20%, m3=16%
             Then:  ±1=52%, ±2=34%, ±3=5%
```

---

## AXIS 2: Rhythm Strategy

| Strategy      | Description                    | Note Values                  | Meter | Examples              |
|---------------|--------------------------------|------------------------------|-------|-----------------------|
| `isochronous` | Equal values, steady pulse     | Mostly 0.25                  | 4/4   | Canon, Hallelujah     |
| `long_short`  | Dotted rhythms, agogic accent  | 0.375+0.125, 0.5+0.125+0.125 | 4/4   | Little Fugue, Dido    |
| `ornamental`  | Mordents, turns, figuration    | 0.0625 groups, 0.125         | 4/4   | Toccata, Brandenburg  |
| `dance`       | Strong pulse, phrase regularity| Bar-filling patterns         | 3/4   | Tambourin, La Folia   |

### Typical Groupings

```
isochronous: [.25 .25 .25 .25]  [.125 .125 .125 .125]
long_short:  [.375 .125]  [.5 .125 .125]  [.1875 .0625]
ornamental:  [.0625 .0625 .125]  [.0625 .0625 .0625 .0625]
dance:       [.25 .25 .25]  [.25 .125 .125 .25]  [.125 .125 .25 .25]
```

---

## AXIS 3: Contour Strategy

| Strategy      | Shape                        | Direction Bias | Climax Position | Examples              |
|---------------|------------------------------|----------------|-----------------|----------------------|
| `descending`  | High → Low                   | -60%           | First 25%       | Canon, Dido, Toccata |
| `arch`        | Mid → High → Mid             | 0%             | Middle 40-60%   | Dido vocal, Fugue    |
| `ascending`   | Low → High                   | +50%           | Last 25%        | Hallelujah           |
| `oscillating` | Wave-like neighbour motion   | 0%             | None (multiple) | Primavera, Tambourin |

### Visual Contours

```
descending:   ╲___      Start high, fall to end
arch:         _/‾\_     Rise to middle peak, fall back
ascending:    ___/      Start low, climb to end
oscillating:  ~/\/~     Multiple small peaks, no single climax
```

---

## CHARACTER BONUSES

| Character          | What It Does                              | Bonus  | Best With                    |
|--------------------|-------------------------------------------|--------|------------------------------|
| `chromatic`        | 2+ semitone steps (expressive)            | +12%   | stepwise + descending/arch   |
| `mordent_identity` | Ornament IS the motif (N-N±1-N)           | +15%   | ornamental/dance + osc/desc  |
| `obsessive`        | 3+ same pitch in a row                    | +10%   | repetition + isochronous     |
| `silence`          | Rest as structural element                | +8%    | ornamental + descending      |
| `ground_compatible`| Works over repeating bass                 | +10%   | stepwise + descending/arch   |
| `triad_skeleton`   | Opens with triad arpeggio                 | +12%   | leap_fill + arch             |
| `phrase_repeat`    | Immediate exact restatement               | +10%   | repetition + orn/iso         |

### Compatibility Matrix

```
                     Pitch          Rhythm              Contour
chromatic         → stepwise     | any               | descending, arch
mordent_identity  → any          | ornamental, dance | descending, oscillating
obsessive         → repetition   | isochronous       | any
silence           → any          | ornamental        | descending
ground_compatible → stepwise     | any               | descending, arch
triad_skeleton    → leap_fill    | any               | arch
phrase_repeat     → repetition   | ornamental, iso   | any
```

---

## INVALID COMBINATIONS

Characters have strict compatibility rules. The generator will raise `ValueError` for these:

### chromatic
| Pitch | Rhythm | Contour | Valid? |
|-------|--------|---------|--------|
| stepwise | any | descending | YES |
| stepwise | any | arch | YES |
| stepwise | any | ascending | NO |
| stepwise | any | oscillating | NO |
| repetition | any | any | NO |
| leap_fill | any | any | NO |

### mordent_identity
| Pitch | Rhythm | Contour | Valid? |
|-------|--------|---------|--------|
| any | ornamental | descending | YES |
| any | ornamental | oscillating | YES |
| any | dance | descending | YES |
| any | dance | oscillating | YES |
| any | isochronous | any | NO |
| any | long_short | any | NO |
| any | any | arch | NO |
| any | any | ascending | NO |

### obsessive
| Pitch | Rhythm | Contour | Valid? |
|-------|--------|---------|--------|
| repetition | isochronous | any | YES |
| stepwise | any | any | NO |
| leap_fill | any | any | NO |
| repetition | long_short | any | NO |
| repetition | ornamental | any | NO |
| repetition | dance | any | NO |

### silence
| Pitch | Rhythm | Contour | Valid? |
|-------|--------|---------|--------|
| any | ornamental | descending | YES |
| any | isochronous | any | NO |
| any | long_short | any | NO |
| any | dance | any | NO |
| any | ornamental | arch | NO |
| any | ornamental | ascending | NO |
| any | ornamental | oscillating | NO |

### ground_compatible
| Pitch | Rhythm | Contour | Valid? |
|-------|--------|---------|--------|
| stepwise | any | descending | YES |
| stepwise | any | arch | YES |
| stepwise | any | ascending | NO |
| stepwise | any | oscillating | NO |
| repetition | any | any | NO |
| leap_fill | any | any | NO |

### triad_skeleton
| Pitch | Rhythm | Contour | Valid? |
|-------|--------|---------|--------|
| leap_fill | any | arch | YES |
| stepwise | any | any | NO |
| repetition | any | any | NO |
| leap_fill | any | descending | NO |
| leap_fill | any | ascending | NO |
| leap_fill | any | oscillating | NO |

### phrase_repeat
| Pitch | Rhythm | Contour | Valid? |
|-------|--------|---------|--------|
| repetition | ornamental | any | YES |
| repetition | isochronous | any | YES |
| stepwise | any | any | NO |
| leap_fill | any | any | NO |
| repetition | long_short | any | NO |
| repetition | dance | any | NO |

### Quick Invalid Checks

**Never use these combinations:**
- `chromatic` + `repetition` or `leap_fill` pitch
- `chromatic` + `ascending` or `oscillating` contour
- `obsessive` + anything except `repetition` + `isochronous`
- `silence` + anything except `ornamental` + `descending`
- `triad_skeleton` + anything except `leap_fill` + `arch`
- `ground_compatible` + `repetition` or `leap_fill` pitch
- `phrase_repeat` + `stepwise` or `leap_fill` pitch

---

## BASE CONSTRAINTS (All Melodies)

| Constraint          | Value                                |
|---------------------|--------------------------------------|
| Range               | ≤12 semitones (P8)                   |
| Stepwise %          | ≥70% of intervals                    |
| Triad outline       | First 4 notes hit ≥2 triad tones     |
| Climax              | Single peak, single trough           |
| Gap fill            | Leaps ≥m3 followed by contrary step  |
| Duration            | 2-4 beats (half bar to one bar)      |
| Note count          | 4-8 notes                            |

---

## RECIPE EXAMPLES

### Canon-style (Pachelbel)
```yaml
pitch: stepwise
rhythm: isochronous
contour: descending
character: [ground_compatible]
```
*Steady falling steps, hypnotic simplicity*

### Toccata-style (Bach BWV 565)
```yaml
pitch: stepwise
rhythm: ornamental
contour: descending
character: [mordent_identity, silence]
```
*Dramatic mordent, pause, resolution*

### Little Fugue-style (Bach BWV 578)
```yaml
pitch: leap_fill
rhythm: long_short
contour: arch
character: [triad_skeleton]
```
*Big opening 5th, stepwise fill, dotted rhythm*

### Hallelujah-style (Handel)
```yaml
pitch: repetition
rhythm: isochronous
contour: ascending
character: [obsessive]
```
*Hammered repeated notes, building upward*

### Primavera-style (Vivaldi)
```yaml
pitch: repetition
rhythm: ornamental
contour: oscillating
character: [phrase_repeat]
```
*Rapid figures, wave motion, exact repeats*

---

## SCORING FORMULA

```
score = structure_score × (1 + Σ character_bonuses)

structure_score = (pitch_score × rhythm_score × contour_score)^(1/3)
```

Each axis scores 0-1 based on alignment. Characters add 8-15% each.

There are 48 valid combinations of strategies.
