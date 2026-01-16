# Partimenti.org: Regole (Rules)

**Sources:**  
- Giacomo Insanguine, *Regole con moti di Basso* (c. 1785)
- Fedele Fenaroli, *Regole Musicali* (Naples, 1775)

Both from https://partimenti.org

---

## Part 1: Fundamentals

### Consonances and Dissonances

| Type | Intervals | Properties |
|------|-----------|------------|
| Perfect consonances | 5th, 8ve | Immutable, cannot be altered |
| Imperfect consonances | 3rd, 6th | Mutable (major/minor) |
| Dissonances | 2nd, 4th, 7th, 9th | Must be prepared and resolved |

### Prohibition

> "There is a prohibition against two octaves or two fifths moving in parallel because, due to their perfection, they create no variation in harmony."

### Contrapuntal Motions

| Motion | Description | Usage |
|--------|-------------|-------|
| Direct | Both hands rise or fall together | **Avoid** (causes parallels) |
| Oblique | One hand holds, other moves | Safe |
| Contrary | Hands move in opposite directions | Best |

---

## Part 2: Rule of the Octave (Scale Harmonisation)

### Major Mode

| Degree | Ascending | Descending |
|--------|-----------|------------|
| ① | 3, 5, 8 | 3, 5, 8 |
| ② | 3, 6 (maj) | 3, 4, 6 (maj) |
| ③ | 3, 6 | 3, 6 |
| ④ | 3, 5 (asc) / 3, 5, 6 (→⑤) | 2, 4# (aug), 6 |
| ⑤ | 3 (maj), 5 | 3 (maj), 5 |
| ⑥ | 3, 6 | 6 (maj), 3, 4 |
| ⑦ | 3, 5 (dim), 6 (→⑧) / 3, 6 | 3, 6 |

### Special Cases

**④ descending from ⑤ to ③:**
- Takes 2nd, augmented 4th (produces ⑦-①-②-③ in key of ⑤)

**⑦ ascending to ⑧:**
- Takes 3rd, diminished 5th, 6th (leading tone function)

**⑥ descending:**
- Takes major 6th (leading tone to ⑤)
- In minor: takes augmented 6th

### Minor Mode Adjustments

- Ascending: ⑥ becomes major
- Descending: ⑦ becomes minor
- Reason: avoid augmented 2nd between ♭⑥ and ♮⑦

---

## Part 3: Cadences

### Simple Cadence

```
①  →  ⑤  →  ①
5/3    5/3#   5/3
```

Bass from tonic to dominant and back. Both take simple consonances.

### Compound Cadence

```
①  →  ⑤  →  ①
5/3   4-3    5/3
```

Suspension of 4th above ⑤, prepared by 8ve of ①, resolved to major 3rd.

### Double Cadence

```
⑤  →  ⑤  →  ⑤  →  ①
5/3   6/4   5/4   5/3#
```

Extended dominant with 6/4 passing chord.

### Interrupted (Deceptive) Cadence

```
⑤  →  ⑥
5/3   6/3
```

Cadence that "leaves the key" - dominant resolves to ⑥ instead of ①.

---

## Part 4: Dissonance Treatment

### Suspension of the 4th

The 4th can be prepared by **any consonance**:

| Preparation | Bass Motion | Example |
|-------------|-------------|---------|
| 8ve | Rise 5th or fall 4th | ①→⑤ |
| 3rd | Descend by step | ⑥→⑤ or ②→① |
| 5th | Ascend by step | ④→⑤ or ①→② |
| 6th | Rise by 3rd | ③→⑤ |
| Minor 7th | Rise by 4th | ⑤→① |
| Diminished 5th | Rise by semitone | ⑦→① |

**Rule:** The 4th must always be accompanied by the 5th. Cannot appear above notes that don't take 5th.

### Suspension of the 7th

The 7th can be prepared by **any consonance**:

| Preparation | Bass Motion |
|-------------|-------------|
| 8ve | Rise by step |
| 3rd | Rise 4th or fall 5th |
| 5th | Rise 6th or fall 3rd |
| 6th | Descend by step |

**Resolution:** Always with 3rd. Resolves to 3rd (bass rises 4th/falls 5th) or 6th (bass holds).

### Suspension of the 9th

The 9th can be prepared by **3rd or 5th**:

| Preparation | Bass Motion |
|-------------|-------------|
| 3rd | Rise by step |
| 5th | Rise 4th or fall 5th |

**Rule:** 9th always accompanied by 10th (3rd). Resolves to 8ve (bass holds), 3rd (bass falls 3rd), or 6th (bass rises 3rd).

---

## Part 5: Tied Bass (Bass Suspensions)

### Returns to Same Key

```
[tied note] → [semitone descent]
   2, 4         3, (5dim)
```

When bass is tied and returns to same key: take major 2nd and perfect 4th. The 4th becomes 3rd when bass descends semitone.

### Changes Key (Modulation)

```
[tied note] → [semitone descent]
   2, 4#, 6       6
```

When bass is tied and changes key: take major 2nd, augmented 4th, and major 6th. The augmented 4th rises to 6th.

**Effect:** Passes harmony from current key to key of its 5th.

### Chain of Ties

When bass has series of ties:
- Can use either perfect or augmented 4th
- **Last 4th must be augmented** (to effect modulation)

---

## Part 6: Bass Motions (Moti di Basso)

### Ascending Motions

| Interval | Accompaniment | Dissonant Version |
|----------|---------------|-------------------|
| Up 3rd | First note only | - |
| Up 4th | 3, 5 on each | 4-3 suspension |
| Up 5th | 3, 5 on each | 7-6 or 9-8 |
| Up 6th | 3, 6 / 3, 5 alternating | 7-6 |
| Up 7th | 3, 5 on each | - |

### Descending Motions

| Pattern | Accompaniment |
|---------|---------------|
| Down 3rd, up step | 5, 6 on descent; 3, 5 on ascent |
| Down 4th, up step | 3, 5 or 4-3 suspension |
| Down 5th, up 4th | 3, 5 or 7-6 chain |

### Sequential Patterns (Fenaroli)

**Up 3rd, down step:**
```
①-③-②-④-③-⑤-④-⑥-⑤
5/3 6/3 6 6/5 6/3 ...
```

Three accompaniment options:
1. Alternating 5/3 and 6/3
2. 4-3 suspensions on each "down step"
3. 7-6 suspensions throughout

**Down 3rd, up step:**
```
①-⑥-⑦-⑤-⑥-④-⑤-③
5/3 6/3 5/3 6/5/3 ...
```

Options:
1. Alternating 5/3 and 6/3
2. 5/3 and 6/5/3 alternating
3. 7-6, 9-8 suspensions

**Up 4th, down 3rd:**
```
①-④-②-⑤-③-⑥-④-⑦
5/3 5/3 5/3 ...
```

Options:
1. All 5/3
2. 9-8 on ascending 4ths
3. 7-4-3 pattern (major mode only)

**Down 4th, up step:**
```
①-⑤-⑥-③-④-①
5/3 5/3 5/3 ...
```

Options:
1. All 5/3
2. 4-3, 9-8 alternating

**Up 5th, down 4th:**
```
①-⑤-②-⑥-③-⑦
5/3 5/3 ...
```

Options:
1. All 5/3
2. 4-3 suspensions (except first note)

**Up 4th, down 5th (Circle of 5ths):**
```
①-④-⑦-③-⑥-②-⑤-①
```

Options:
1. All 5/3
2. 9-8 suspensions
3. 7ths (7-3-7-3...)

**Up 6th, down 5th:**
```
①-⑥-②-⑦-③
5/3 6/3 5/3 6/3 ...
```

Options:
1. Alternating 5/3 and 6/3
2. 7-6 suspensions on 6th ascents

---

## Part 7: Chromatic Motion

### Ascending Chromatic (Major Mode)

Starting from ③, can ascend by semitone to ⑥:

```
③ - #③ - ④ - #④ - ⑤ - #⑤ - ⑥
6/5  5/3  6/5  5/3  6/5  5/3  ...
```

Each chromatic note treated as ⑦→① in local key.

### Ascending Chromatic (Minor Mode)

Starting from ⑤, can ascend by semitone to ⑧:

**Option 1 (7-6 chain):**
```
⑤ - ♭⑥ - ♮⑥ - ♭⑦ - ♮⑦ - ⑧
5/3  7    6    7    6   5/3
```

**Option 2 (Contrary motion):**
```
⑤ - ♭⑥ - ♮⑥ - ♭⑦ - ♮⑦ - ⑧
3    3    4#   6    6#   8
```

### Descending Chromatic (Minor Mode)

From ① to ⑤:

**Option 1 (7-6 chain):**
```
① - ⑦ - ♭⑦ - ⑥ - ♭⑥ - ⑤
5/3-6 7   6   7   6#   5/3
```

**Option 2 (Contrary motion):**
```
① - ⑦ - ♭⑦ - ⑥ - ♭⑥ - ⑤
3    3   4#   6   6#   8
```

---

## Part 8: Tied Descending Bass

When partimento descends by step in ties:

```
① - ⑦ - ⑥ - ⑤ - ④ - ③
4/2  6   4/2  6   4/2# 6
```

- Each tied note takes 4th and 2nd
- Last 4th must be augmented (modulation)
- Cannot descend below ④ with this pattern

---

## Implementation Notes for Andante

### Data Structures

```yaml
bass_motions:
  up_3rd_down_step:
    pattern: [+3, -1]
    options:
      - basic: [5/3, 6/3]
      - suspension_4_3: true
      - suspension_7_6: true
  
  down_4th_up_step:
    pattern: [-4, +1]
    options:
      - basic: [5/3, 5/3]
      - suspension_4_3_9_8: true
  
  circle_of_fifths:
    pattern: [+4, -5]
    options:
      - basic: [5/3, 5/3]
      - suspension_9_8: true
      - chain_7: true
```

### Algorithm

```python
def harmonise_bass_motion(bass: List[int]) -> List[Chord]:
    """Detect pattern and select accompaniment."""
    pattern = detect_motion_pattern(bass)
    if pattern:
        options = BASS_MOTIONS[pattern].options
        return select_option(options, context)
    else:
        return rule_of_octave(bass)
```

### Priority Order

1. Check for sequential bass pattern (bass motions)
2. Check for tied bass
3. Check for chromatic motion
4. Fall back to Rule of the Octave
5. Apply dissonance treatment based on phrase position
