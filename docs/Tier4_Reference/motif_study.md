# Motif Study: Bach's Techniques for Motivic Variety

Analysis of Bach's Two-Part Inventions, Three-Part Sinfonias, and Well-Tempered Clavier fugues to address Andante's duplication problem.

## The Problem

Andante generates two-voice inventions from a single 8-note subject. Despite phrase-aware variation (inversion, retrograde, augmentation, diminution, fragmentation), the same intervallic patterns recur throughout, causing audible duplication.

**Root cause:** All melodic material derives from one source through mechanical transformations.

---

## 1. Counter-Subjects

### Bach's Technique

A counter-subject is counterpoint that **consistently accompanies** each occurrence of the subject. It differs from free counterpoint, which changes each time.

**Key construction principles:**

| Aspect | Subject | Counter-subject |
|--------|---------|-----------------|
| Rhythm | If slow | Then fast |
| Motion | If ascending | Then descending |
| Activity | If pausing | Then moving |
| Accent | If strong | Then weak |

Bach designs counter-subjects for **invertible counterpoint**: either voice can serve as bass without breaking dissonance conventions. This requires avoiding parallel fifths that become fourths when inverted.

### Examples

**BWV 772 (C major Invention):** The counter-subject uses augmented values of the subject's first four notes as the bass, while the soprano presents the inverted subject. This economy means just three motifs build the entire piece.

**BWV 847 (C minor Fugue, WTC I):** Has two regular counter-subjects (CS1 and CS2). The bass plays the subject while CS1 appears in treble and CS2 in the middle voice. Both counter-subjects derive from subject fragments but have independent character.

### Design Recommendation for Andante

Add a `counter_subject` field to the material section, generated with these constraints:

```yaml
counter_subject:
  pitches: [5, 4, 3, 2, 1, 7, 6, 5]  # Contrary motion to subject
  durations: ["1/8", "1/8", "1/4", "1/8", "1/8", "1/8", "1/8", "1/4"]
  derivation: contrary  # or: independent, rhythmic_complement
```

**Generation rules:**
1. **Rhythmic complement:** Where subject has long notes, use short; where short, use long
2. **Contrary motion preferred:** Ascending subject intervals become descending
3. **Invertible:** Test that CS works as bass (avoid parallel 5ths that become 4ths)
4. **Use when:** Subject is in other voice (imitation, statement with voice exchange)

---

## 2. Head Motif Extraction

### Bach's Technique

The **head motif (Kopfmotiv)** is the first 3-4 notes of the subject, extracted and developed independently. It appears in:

- **False entries:** Begin the subject but do not complete it
- **Episodes:** Sequenced independently while full subject is dormant
- **Links:** Connect subject entries seamlessly (if link uses head, next entry flows naturally)

The head is the most recognizable part of the subject. Its brevity allows rapid sequencing and greater flexibility than the full subject.

### Examples

**BWV 775 (D minor Invention):** The subject is essentially a D harmonic minor scale with displaced leading tone, plus broken chords. The "head" (scale fragment) and "tail" (broken chords) are developed separately in episodes.

**BWV 847 (C minor Fugue):** Episodes use "motivic fragmentation of the subject head" in one voice while another voice sequences a different fragment.

### Design Recommendation for Andante

Current `fragmentation` treatment already extracts 4 notes via `head` transform:

```yaml
fragmentation:
  soprano_transform: head
  soprano_transform_params: { size: 4 }
```

**Enhance to:**

1. **Auto-derive head:** Extract first 3-4 notes based on rhythmic grouping (first beat or first complete gesture)
2. **Separate head treatment:** Allow head to be sequenced independently, not just as truncated subject
3. **Tail motif:** Also extract tail (final 3-4 notes) for contrast material

```yaml
# In material section
subject:
  pitches: [1, 2, 3, 4, 5, 4, 3, 2]
  durations: ["1/8", "1/8", "1/8", "1/8", "1/8", "1/8", "1/8", "1/8"]
  head_size: 4  # First 4 notes = head
  tail_size: 3  # Last 3 notes = tail

# New treatment using head only
head_sequence:
  source: head  # Use head, not full subject
  soprano_fill: sequence
  soprano_fill_params: { reps: 6, step: -1 }
```

---

## 3. Episode Material

### Bach's Technique

Episodes are sections between subject statements. They modulate and provide contrast. Bach uses two types of material:

| Type | Description | Proportion |
|------|-------------|------------|
| **Subject-derived** | Fragments of subject/CS sequenced | ~70-80% |
| **Free material** | Scales, arpeggios, passagework | ~20-30% |

**Episode characteristics:**
- 2-4 measures long
- Almost always sequential
- Thinner texture than expositions
- Move through circle of fifths

Even "free" episodes often relate motivically to subject or counter-subject. True novelty is rare.

### Examples

**BWV 779 (F major Invention):** Uses canon technique extensively. Episodes contain scalar passages and broken chord figures derived from the subject's initial arpeggio rise.

**BWV 784 (A minor Invention):** Structure "similar to a fugue" with clear episodes connecting subject statements. Episode material derives from fragmented subject with sequential treatment.

**Art of Fugue (Contrapunctus V):** "Although there is no counter-subject, several motives from the subject are constantly used as free counterpoint and as material for developing the episodes."

### Design Recommendation for Andante

Current implementation has `passage.py` generating scalar/arpeggiated material, but it's not integrated with subject.

**Enhance to:**

1. **Derive episode patterns from subject:** Extract intervals/contour from subject, use as basis for scalar passages
2. **Allow free passages:** But constrain to 20-30% of total; mark as `episode: free_scalar`
3. **Sequential episodes:** Enforce sequential structure (current `sequence` fill does this)

```yaml
# Episode types
episode_material:
  derived_scalar:
    source: subject_intervals  # Use subject's interval sequence
    type: scalar
    sequential: true
  derived_arpeggio:
    source: subject_chord_outline  # Extract chord tones from subject
    type: arpeggiated
  free_scalar:
    source: scale  # Not subject-derived
    type: scalar
    max_proportion: 0.2  # Limit usage
```

---

## 4. Derived Motifs

### Bach's Technique

Derived motifs are secondary themes created by transforming the subject. Unlike mechanical application of a transform, they become **independent material** that can be developed separately.

**Transformation chains:**
1. Subject → Inversion → New melodic profile
2. Subject → Fragmentation → Head as independent motif
3. Subject → Augmentation → Stately contrasting character
4. Subject head + inversion → Hybrid motif

The key insight: transformations are not just "variations of the subject" but can create **genuinely new thematic material** with its own identity.

### Examples

**BWV 772 (C major Invention):** Three motifs, all derived from one subject:
- Motif A: Subject itself
- Motif B: Subject in augmentation (doubles as bass)
- Motif C: Derived from part of Motif B, used at cadences

This economy (one source, three distinct usable motifs) is Bach's hallmark.

### Design Recommendation for Andante

**Precompute derived motifs at material generation:**

```yaml
material:
  subject:
    pitches: [1, 2, 3, 4, 5, 4, 3, 2]
    durations: ["1/8", "1/8", "1/8", "1/8", "1/8", "1/8", "1/8", "1/8"]

  derived:
    motif_A:  # Subject as-is
      source: subject
      transform: none
    motif_B:  # Inverted subject
      source: subject
      transform: invert
    motif_C:  # Augmented head
      source: head
      transform: augment
    motif_D:  # Retrograde tail
      source: tail
      transform: retrograde
```

**Use in treatments:**

```yaml
# Use derived motif, not subject
phrase_3:
  material: motif_C  # Not subject
  treatment: sequence
```

This allows variety without introducing unrelated material.

---

## 5. Multiple Subjects (Double/Triple Fugue Techniques)

### Bach's Technique

In double and triple fugues, multiple subjects coexist:

| Type | Structure |
|------|-----------|
| **Double fugue (type 1)** | Both subjects introduced together from start |
| **Double fugue (type 2)** | Subject 1 developed alone, then Subject 2 with its own exposition, then combined |
| **Triple fugue** | Three subjects with independent expositions, later combined |

**Art of Fugue examples:**
- **Contrapunctus VIII:** Triple fugue. Theme I developed alone, then Theme I+II as double fugue, then all three combined.
- **Contrapunctus IX:** New theme introduced, later combined with main Art of Fugue theme.
- **Contrapunctus XI:** Uses three subjects in both upright and inverted forms.

The critical rule: subjects must work in **invertible counterpoint** (can exchange bass/treble roles).

### Application to Two-Part Inventions

Bach's two-part inventions are generally **mono-thematic** (one subject). New material mid-piece is rare. However:

- Counter-subjects provide secondary material
- Derived motifs (head, tail, inversions) function as quasi-independent themes
- Episodes use fragmentary material that contrasts with full subject

For two-voice texture, true double-subject writing is uncommon because contrapuntal options are limited.

### Design Recommendation for Andante

**For v3, do not implement full double-subject.** Instead:

1. Counter-subject (see section 1) provides secondary material
2. Derived motifs (see section 4) create variety from single source
3. Keep mono-thematic constraint for two voices

**For future (v4+ with 3+ voices):**

```yaml
material:
  subject_1:
    pitches: [...]
    durations: [...]
  subject_2:
    pitches: [...]
    durations: [...]
    invertible_with: subject_1  # Must pass invertibility check
```

---

## Priority Ranking

Ranked by value (variety gained) vs. complexity (implementation effort):

| Rank | Technique | Value | Complexity | Recommendation |
|------|-----------|-------|------------|----------------|
| 1 | **Counter-subject** | High | Medium | v3 priority. Solves core problem of melodic monotony when subject is in bass. |
| 2 | **Head extraction** | High | Low | v3 priority. Already partly implemented. Enhance to use head as independent material. |
| 3 | **Derived motifs** | Medium | Low | v3. Precompute 2-3 derived motifs from subject for phrase variety. |
| 4 | **Episode integration** | Medium | Medium | v3. Link passage.py patterns to subject intervals/contour. |
| 5 | **Tail extraction** | Low | Low | v3. Minor addition to head extraction. |
| 6 | **Multiple subjects** | Low | High | Defer to v4 (3+ voices). Two-voice texture limits contrapuntal options. |

---

## Implementation Plan

### Phase 1: Counter-Subject (v3)

1. Add `counter_subject` to material section
2. Generate CS with contrary motion and rhythmic complement
3. Validate invertibility (no parallel 5ths becoming 4ths)
4. Use CS in `imitation` treatment when subject is in bass
5. New treatment: `voice_exchange` (subject and CS swap voices)

### Phase 2: Enhanced Fragmentation (v3)

1. Auto-derive `head` and `tail` from subject based on rhythmic grouping
2. New treatment: `head_sequence` (sequences head only, 6+ reps)
3. New treatment: `tail_development` (tail with inversion/sequence)
4. Allow mixing head/tail in single phrase

### Phase 3: Derived Motifs (v3)

1. Precompute 3-4 derived motifs at plan time
2. Store in material section with transform chain documented
3. Allow phrase to reference derived motif instead of subject
4. Arc system selects which derived motif for each phrase

### Phase 4: Episode Integration (v3)

1. Extract interval sequence from subject
2. Generate scalar passages following subject intervals (not mechanical scale)
3. Generate arpeggio passages from subject chord outline
4. Track proportion of subject-derived vs. free episodes

---

## Sources

- [Analysis of the C Major Invention (BWV 772)](https://www.teoria.com/en/articles/BWV772/)
- [Bach's Invention 1: A Step-by-step Analysis](https://www.schoolofcomposition.com/bach-invention-1-analysis/)
- [Inventions and Sinfonias - Wikipedia](https://en.wikipedia.org/wiki/Inventions_and_Sinfonias)
- [Fugue Analysis - Music Theory](https://musictheory.pugetsound.edu/mt21c/FugueAnalysis.html)
- [The Art of Fugue - Wikipedia](https://en.wikipedia.org/wiki/The_Art_of_Fugue)
- [High Baroque Fugal Exposition](https://viva.pressbooks.pub/openmusictheory/chapter/high-baroque-fugal-exposition/)
- [Fugue - Britannica](https://www.britannica.com/art/fugue/Varieties-of-the-fugue)
- [Countersubject Definition](https://www.earsense.org/Earsense/WTC/Vocabulary/countersubject.html)
- [Invention No. 4 BWV 775 Analysis](https://www.teoria.com/en/articles/2020/bach-inventio/04/index.php)
- [Invention No. 8 BWV 779 Analysis](https://www.teoria.com/en/articles/2020/bach-inventio/08/index.php)
- [Invention No. 13 BWV 784 Analysis](https://www.teoria.com/en/articles/2020/bach-inventio/13/index.php)
