# Figuration Design

## Problem

Anchors (one per bar, beat 1) converted directly to whole notes produce chorale-like block chords. Baroque music requires idiomatic melodic motion between structural points.

## Core Insight

Baroque melody is **figure-driven, not rule-driven**. Composers internalised a small vocabulary of stock figures selected by interval and context. Rules filter; figures generate. Style is the distribution of figures, not their legality.

**Caution:** Figures are fuzzy categories, not rigid templates. Boundaries between "neighbour", "turn", "cambiata" are porous. The system must allow controlled violation to avoid over-regular, textbook surfaces.

---

## Architecture

```
Anchors → Phrase Structure → Figure Selection → Rhythmic Realisation → Pitch Mapping → Notes
                                    ↓
                            Junction Check
                                    ↓
                         Counterpoint Validation
```

---

## 1. Phrase Structure

Determines selection mode based on bar position and schema type.

| Position | Bars (8-bar phrase) | Logic | Character |
|----------|---------------------|-------|-----------|
| Opening | 1–2 | Independent selection | plain, expressive |
| Continuation | 3–6 | Sequential (Fortspinnung) | energetic |
| Cadence | 7–8 | Cadential table | cadential |

**Schema override:** Monte, Fonte, Meyer, Ponte force sequential transposition.

**Rule of Three:** Sequence maximum twice, then break via fragmentation (not random selection).

**Phrase deformation:** Occasionally triggered (seeded) to break galant regularity:
- `early_cadence` — cadential figure appears bar 6
- `extended_continuation` — sequence continues into bar 7
- `none` — standard structure

**Hemiola block:** When hemiola flag is set, bars 6–7 are treated as a single rhythmic unit, not separate phrase positions.

---

## 2. Diminution Table

Indexed by interval: unison, step_up, step_down, third_up, third_down, fourth_up, fourth_down, fifth_up, fifth_down, sixth_up, sixth_down, octave_up, octave_down.

Each figure has:

```yaml
step_up:
  - degrees: [0, -1, 1]           # relative to start; final = interval
    contour: lower_neighbor        # descriptive name
    polarity: lower                # upper | lower | balanced
    arrival: stepwise              # direct | stepwise | accented
    placement: end                 # start | end | span
    character: expressive          # plain | expressive | energetic | ornate | bold
    harmonic_tension: low          # low | medium | high
    max_density: medium            # low | medium | high
    cadential_safe: true           # usable near cadences
    repeatable: true               # can sequence multiple times
    requires_compensation: false   # leap needs stepwise recovery
    compensation_direction: null   # up | down (if required)
    is_compound: false             # implies two-voice texture
    minor_safe: true               # works with melodic minor inflections
    requires_leading_tone: false   # needs raised 7 in minor
    weight: 1.0                    # selection probability (historical frequency)
```

**Harmonic tension** is set by schema type, bass degree, and bar function. Figures are filtered to match target tension.

**Compound melody:** If a compound figure is chosen for bar 1, prefer compound figures throughout that phrase section.

---

## 3. Cadential Table

Separate from diminution table. Indexed by target degree (1 or 5) and approach interval.

```yaml
target_1:  # Perfect Authentic Cadence
  step_down:  # degree 2 → 1
    - degrees: [0, 1, 0, -1]
      contour: trill
      trill_position: 0            # which degree gets trill
      hemiola: false
      
target_5:  # Half Cadence
  step_up:  # degree 4 → 5
    - degrees: [0, 1, 2, 1]
      contour: double_appoggiatura
      hemiola: true
```

**Cadential understatement:** With low probability (seeded), allow non-cadential figures at weak cadences (half cadences, inner phrases) to avoid over-perfect endings.

---

## 4. Rhythmic Realisation

Inputs:
- Figure (degree sequence)
- Gap duration (beats)
- Metre (beat hierarchy)
- Bar function (passing | preparatory | cadential | schema_arrival)
- Rhythmic unit (genre's characteristic note value)
- Next bar anchor strength (weak | strong)

**Templates by note-count and metre (3/4):**

| Notes | Standard | Overdotted (ornate) |
|-------|----------|---------------------|
| 2 | [2.0, 1.0] | [2.5, 0.5] |
| 3 | [1.5, 0.5, 1.0] | [1.75, 0.25, 1.0] |
| 4 | [1.0, 1.0, 0.5, 0.5] | [1.0, 1.0, 0.75, 0.25] |
| 5 | [1.0, 0.5, 0.5, 0.5, 0.5] | — |
| 6 | [0.5, 0.5, 0.5, 0.5, 0.5, 0.5] | — |

**Beat 3 as anacrusis:** When `next_bar_anchor_strength: strong`, beat 3 is lighter (preparation). When weak, beat 3 can carry more weight.

**Augmentation/Diminution:** Figures play at natural speed, half speed (×2), or double speed (×0.5). No arbitrary scaling.

**Hemiola realisation:** Bars 6–7 become [2, 1, 2, 1] in minims/crotchets, not [1, 1, 1, 1, 1, 1].

---

## 5. Melodic Minor Mapper

Wraps `Key` class for direction-aware pitch realisation in minor mode.

| Direction | Degree 6 | Degree 7 | Reason |
|-----------|----------|----------|--------|
| Ascending to 8 | Raised | Raised | Pull to tonic, avoid augmented 2nd |
| Descending to 5 | Natural | Natural | Follow dominant gravity |
| Static/turning | Natural | Natural | Unless neighbour to 8 |

**Augmented 2nd prohibition:** If degree 7 is raised, degree 6 must also be raised.

**Tritone prohibition:** Melodic motion from degree 4 to raised degree 7 (augmented 4th) is avoided unless part of dominant-seventh arpeggio. Filter such figures or alter path.

**Upstream awareness:** Figures marked `minor_safe: false` or `requires_leading_tone: true` are filtered before selection in minor keys, not vetoed after pitch mapping.

---

## 6. Sequencer (Fortspinnung)

Handles motivic coherence across bars:

1. Select figure for bar 1
2. Transpose same figure shape to bar 2 anchors
3. Transpose to bar 3 anchors (if not breaking)
4. **Fragmentation** for break: take first motif of figure, repeat at higher frequency, accelerate into cadence
5. Select cadential figure

**Melodic rhyme:** Bar 5 (second half) often restates bar 1 figure transposed to dominant (Ponte schema).

---

## 7. Junction Filter

The final note of bar N must connect idiomatically to anchor N+1.

**Check:** After figure selection, verify that the penultimate note of the figure:
- Approaches next anchor by step, or
- Shares a common tone, or
- Is part of an acceptable leap pattern

If junction fails, try next candidate figure.

---

## 8. Controlled Misbehaviour

To avoid over-regular output:

- Small probability to ignore `cadential_safe` filter
- Allow `placement` mismatches when density is low
- Permit figures outside their "character" bucket when phrase pressure is high
- Allow non-cadential figures at weak cadences

All violations are seeded and deterministic.

---

## Scope

**Soprano only.** Bass uses accompaniment patterns from `accompaniments.yaml`, not melodic figuration. In homophonic textures, bass repeats a rhythmic pattern (e.g., oom-pah-pah) with root adapted to each anchor's bass degree.

**Counterpoint validation** occurs after figuration generates pitch sequences — parallel 5ths/8ves, voice range, consonance checks.

---

## Selection Pipeline

1. Compute interval (anchor A to anchor B)
2. Filter by interval
3. Filter by direction (ascending/descending/static)
4. Filter by harmonic tension (from schema + bass + bar function)
5. Filter by character (from phrase position)
6. Filter by density (from affect)
7. Filter by minor safety (if minor key)
8. Filter by compensation need (if previous figure leaped)
9. Apply controlled misbehaviour (small probability to relax filters)
10. Sort by weight (historical frequency)
11. Select via seeded RNG
12. Check junction to next anchor
13. If junction fails, try next candidate

---

## Files

| File | Purpose |
|------|---------|
| `data/figuration/diminutions.yaml` | Interval-indexed figure vocabulary |
| `data/figuration/cadential.yaml` | Cadential figures by target degree |
| `data/figuration/rhythm_templates.yaml` | Note-count × metre → durations |
| `builder/figuration/selector.py` | Phrase-aware figure selection |
| `builder/figuration/realiser.py` | Rhythmic realisation |
| `builder/figuration/melodic_minor.py` | Direction-aware pitch mapper |
| `builder/figuration/sequencer.py` | Fortspinnung + fragmentation |
| `builder/figuration/junction.py` | Bar-to-bar connection validation |

---

## Determinism

All selection is deterministic given a seed in the brief:
1. Candidate figures sorted by weight (descending), then name (alphabetical)
2. Seeded RNG selects from filtered candidates
3. Same seed + same anchors = same output

---

## Known Risks

| Risk | Mitigation |
|------|------------|
| Over-regular surfaces | Controlled misbehaviour, phrase deformation |
| Cadences too perfect | Cadential understatement at weak cadences |
| Harmony under-modelled | Harmonic tension tag, schema-aware filtering |
| Junction failures | Explicit junction check with fallback |
| Minor mode errors | Upstream filtering, tritone prohibition |
| Mechanical sequences | Rule of Three + fragmentation |

---

## References

- Quantz, *Versuch einer Anweisung die Flöte traversiere zu spielen* (1752)
- CPE Bach, *Versuch über die wahre Art das Clavier zu spielen* (1753)
- Gjerdingen, *Music in the Galant Style* (2007)
- Sanguinetti, *The Art of Partimento* (2012)
