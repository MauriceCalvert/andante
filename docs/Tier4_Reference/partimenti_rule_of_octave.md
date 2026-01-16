# Partimenti.org: Rule of the Octave

**Source:** https://partimenti.org/partimenti/about_parti/rule_of_the_octave.pdf  
**Author:** Robert Gjerdingen

---

## Fundamental Principle

The harmony of a given bass note is determined by the notes preceding and following it, not by the note in isolation.

---

## Scale Degree Stability

| Degree | Symbol | Stability | Basic Chord |
|--------|--------|-----------|-------------|
| 1 | ① | **Stable** | 5/3 |
| 2 | ② | Unstable | 6/3 |
| 3 | ③ | Semi-stable | 6/3 |
| 4 | ④ | Unstable | 6/3 or 6/5/3 |
| 5 | ⑤ | **Stable** | 5/3 |
| 6 | ⑥ | Unstable | 6/3 |
| 7 | ⑦ | Unstable | 6/3 or 6/5/3 |
| 8 | ⑧ | **Stable** | 5/3 |

**Key insight:** Stable positions (①, ⑤, ⑧) receive 5/3 chords. Unstable positions receive 6/3 chords. Dissonances are added to degrees that **precede** stable positions.

---

## Ascending Rule of the Octave

| Degree | Chord | Notes |
|--------|-------|-------|
| ① | 5/3 | Tonic |
| ② | 6/3 | Optional 4 (→ 6/4/3) |
| ③ | 6/3 | Semi-stable |
| ④ | **6/5/3** | Dissonance before ⑤ |
| ⑤ | 5/3 | Dominant |
| ⑥ | 6/3 | |
| ⑦ | **6/5/3** | Dissonance before ⑧ |
| ⑧ | 5/3 | Tonic |

---

## Descending Rule of the Octave

| Degree | Chord | Notes |
|--------|-------|-------|
| ⑧ | 5/3 | Tonic |
| ⑦ | 6/3 | |
| ⑥ | **#6/4/3** | Raised 6th = leading tone to ⑤ |
| ⑤ | 5/3 | Dominant |
| ④ | **6/4/2** | Strong dissonance descending from ⑤ |
| ③ | 6/3 | Semi-stable |
| ② | 6/4/3 | Same as ascending |
| ① | 5/3 | Tonic |

---

## Context-Dependent Departures (Furno)

The Rule of the Octave is a norm, not an absolute. Common departures:

| Context | Departure |
|---------|-----------|
| ④ NOT descending from ⑤ | Simple triad allowed |
| ⑥ left by leap | Simple triad allowed |
| Bass leaps | Use "Bass Motions" rules instead |

---

## Three Hand Positions (Fenaroli)

The Rule can be realised in three positions of the right hand:

| Position | Voicing (low→high) | Example on ① |
|----------|-------------------|--------------|
| First | 3-5-8 | E-G-C |
| Second | 5-8-3 | G-C-E |
| Third | 8-3-5 | C-E-G |

Students must practice scales in all three positions and all keys.

---

## Implementation Notes for Andante

### Data Structure

```yaml
rule_of_octave:
  ascending:
    1: { chord: "5/3", stability: "stable" }
    2: { chord: "6/4/3", stability: "unstable", optional_4: true }
    3: { chord: "6/3", stability: "semi_stable" }
    4: { chord: "6/5/3", stability: "unstable", dissonance_before: 5 }
    5: { chord: "5/3", stability: "stable" }
    6: { chord: "6/3", stability: "unstable" }
    7: { chord: "6/5/3", stability: "unstable", dissonance_before: 8 }
    8: { chord: "5/3", stability: "stable" }
  descending:
    8: { chord: "5/3", stability: "stable" }
    7: { chord: "6/3", stability: "unstable" }
    6: { chord: "#6/4/3", stability: "unstable", raised_6: true }
    5: { chord: "5/3", stability: "stable" }
    4: { chord: "6/4/2", stability: "unstable", from_5: true }
    3: { chord: "6/3", stability: "semi_stable" }
    2: { chord: "6/4/3", stability: "unstable" }
    1: { chord: "5/3", stability: "stable" }
```

### Algorithm

1. Identify local key and scale degrees
2. Determine direction (ascending/descending)
3. Check for leap context (use bass motions instead)
4. Apply appropriate chord from table
5. Check position preference for voice-leading

### Integration with Existing Code

Current `figures.yaml` has basic figured bass. Rule of the Octave provides:
- Context-dependent chord selection
- Direction-aware harmonisation
- Stability-based phrasing decisions
