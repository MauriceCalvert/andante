# Baroque Melody Generation

## Purpose

Define how pitch sequences are generated for fugue subjects by combining
a harmonic grid with the rhythm cell system defined in `baroque_rhythms.md`.
This replaces the current head enumeration + CP-SAT tail generation +
melodic validation pipeline entirely (Option A).

## Dependencies

- `baroque_rhythms.md` — cell definitions, transition table, generation.
  Rhythm is independent of pitch and is generated first.
- This document assumes 4/4 time, major and minor modes, 2-bar subjects.

## 1. Harmonic Grid

A fugue subject implies harmony.  The harmony only becomes explicit when
the countersubject arrives, but the subject must imply a clear, conventional
progression or the countersubject has nothing to work against.

### 1.1 Harmonic rhythm

Harmonic rhythm — how often the chord changes — is tied to surface rhythm.
Faster note motion requires slower harmonic change; slower note motion
permits faster harmonic change.  Bach's practice: the product of
harmonic activity and surface activity stays roughly constant.

The system supports three harmonic rhythm levels:

| Level     | Chord changes every | Slots in 2 bars | Typical surface rhythm      |
|-----------|--------------------|-----------------|-----------------------------|
| Fast      | beat (crotchet)    | 8               | Mostly crotchets/quavers    |
| Medium    | half-bar (minim)   | 4               | Mixed quavers/semiquavers   |
| Slow      | bar (semibreve)    | 2               | Mostly semiquavers          |

**Selection rule:** compute the mean tick value of the cell sequence.
- Mean ≥ 3.0 → fast harmonic rhythm (8 slots)
- 1.5 ≤ mean < 3.0 → medium harmonic rhythm (4 slots)
- Mean < 1.5 → slow harmonic rhythm (2 slots)

Each note's active chord is determined by which harmonic slot it falls
within.

### 1.2 Stock progressions — fast (8 slots, one chord per beat)

| Pattern | Slot 1 | Slot 2 | Slot 3 | Slot 4 | Slot 5 | Slot 6 | Slot 7 | Slot 8 |
|---------|--------|--------|--------|--------|--------|--------|--------|--------|
| F-A     | I      | I      | I      | V      | V      | V      | V      | I      |
| F-B     | I      | I      | IV     | IV     | V      | V      | V      | I      |
| F-C     | I      | I      | ii     | ii     | V      | V      | V      | I      |
| F-D     | I      | I      | I      | I      | V      | V      | I      | I      |
| F-E     | I      | I      | IV     | V      | V      | V      | V      | I      |
| F-F     | I      | I      | I      | V      | V      | V      | I      | I      |

### 1.3 Stock progressions — medium (4 slots, one chord per half-bar)

| Pattern | Slot 1 | Slot 2 | Slot 3 | Slot 4 |
|---------|--------|--------|--------|--------|
| M-A     | I      | V      | V      | I      |
| M-B     | I      | IV     | V      | I      |
| M-C     | I      | ii     | V      | I      |
| M-D     | I      | I      | V      | I      |

### 1.4 Stock progressions — slow (2 slots, one chord per bar)

| Pattern | Slot 1 | Slot 2 |
|---------|--------|--------|
| S-A     | I      | V      |
| S-B     | I      | I      |

### 1.5 Minor mode equivalents

| Major chord | Minor equivalent |
|-------------|-----------------|
| I           | i               |
| IV          | iv              |
| ii          | ii°             |
| V           | V (major — raised 7th) |

The minor V is major (contains the leading tone).  This is not optional
in baroque style; a minor V produces modal, not tonal, music.

### 1.6 Chord-tone sets

**Major mode:**

| Chord | Scale degrees (mod 7) | Notes in C major |
|-------|----------------------|------------------|
| I     | 0, 2, 4              | C, E, G          |
| IV    | 3, 5, 0              | F, A, C          |
| V     | 4, 6, 1              | G, B, D          |
| ii    | 1, 3, 5              | D, F, A          |

**Minor mode:**

| Chord | Scale degrees (mod 7) | Notes in A minor  |
|-------|----------------------|-------------------|
| i     | 0, 2, 4              | A, C, E           |
| iv    | 3, 5, 0              | D, F, A           |
| V     | 4, 6*, 1             | E, G#, B          |
| ii°   | 1, 3, 5              | B, D, F           |

*Degree 6 in minor V is the raised 7th of the scale (G# in A minor).

### 1.7 Degree numbering

Scale degrees are 0-based within the octave: 0 = tonic, 1 = supertonic,
2 = mediant, 3 = subdominant, 4 = dominant, 5 = submediant, 6 = leading
tone / subtonic.

Actual pitch uses signed integers where 0 = tonic, positive = ascending,
negative = descending, with octave wrapping at ±7.  A "scale degree" in
the chord-tone table is `pitch % 7`.

## 2. Melodic Minor in Minor Mode

In minor mode, the 6th and 7th scale degrees change depending on melodic
direction.  This is melodic minor:

- **Ascending through degrees 5–6–7–0:** use raised 6th and raised 7th
  (e.g. in A minor: F#, G#, A).
- **Descending through degrees 0–7–6–5:** use natural 7th and natural
  6th (e.g. in A minor: A, G, F).
- **Stationary or ambiguous context:** use natural (default).

This applies regardless of the active chord.  A melody ascending to the
tonic over a i chord still uses the raised 7th as a leading tone.

### 2.1 Implementation

When filling P-slots in minor mode, determine the fill direction
(ascending or descending) from the two anchor C-slots.  If ascending
and the fill passes through degree 6 or 7, use the raised form.  If
descending, use the natural form.

The raised 6th and 7th are chromatic alterations — they produce MIDI
pitches outside the natural minor scale.  The degree-to-MIDI conversion
must accept a "raised" flag for degrees 5 and 6 (0-indexed: these are
the 6th and 7th scale steps).

### 2.2 Raised degrees in chord context

The raised 7th already appears in chord V (§1.6).  The raised 6th does
not appear in any stock chord.  It is purely a melodic phenomenon — it
smooths the augmented 2nd between natural 6 and raised 7.

When filling C-slots:
- If the active chord is V in minor, degree 6 is already raised (it's
  the chord's 3rd = leading tone).
- If the active chord is i, iv, or ii° and the melody is ascending
  toward the tonic, C-slots still use the chord's natural tones.  Only
  P-slots between them use the raised forms.

This means the raised 6th and 7th affect P-slot filling only, never
C-slot selection (except degree 6 under chord V, which is already
raised in the chord-tone set).

## 3. C/P Grid

Every note is classified as:

- **C (chord tone required):** must be a member of the active chord's
  tone set at that beat position.
- **P (passing/neighbour):** must be stepwise (±1 diatonic step) from
  at least one adjacent note.  Need not be a chord tone.

The classification is determined by the rhythm cell:

| Cell      | Pattern     | Rationale                                          |
|-----------|-------------|----------------------------------------------------|
| Iamb      | P – C       | Short approaches, long arrives on chord tone.      |
| Trochee   | C – P       | Long states chord tone, short departs.             |
| Dotted    | C – P       | Dotted note carries weight, semiquaver passes.     |
| Dactyl    | C – P – P   | Long is chord tone, two shorts pass through.       |
| Anapaest  | P – P – C   | Two shorts approach, long arrives on chord tone.   |
| Tirata    | P – P – P – P | All passing motion between adjacent cells' C-tones.|

### 3.1 Boundary rule

The first note and last note of the subject are always C, regardless of
their cell's pattern.

- First note: must be a chord tone of the first slot's chord (= tonic).
  Conventional choices: degree 0 (tonic) or degree 4 (dominant).
- Last note: must be a chord tone of the final slot's chord.
  Must be degree 0 or degree 4.

If a cell's pattern says the first/last note is P (e.g. subject starts
with iamb or anapaest), the boundary rule overrides it to C.

### 3.2 Tirata anchoring

A tirata has no internal C-slot.  It is anchored by the last C-slot of
the preceding cell and the first C-slot of the following cell.  Its
notes form a stepwise path between these anchors.

If a tirata begins the subject (boundary rule forces note 1 to C), its
first note is C and the remaining 3 are P.

If a tirata ends the subject (boundary rule forces the last note to C),
its last note is C and the preceding 3 are P.

## 4. Cross-Relation Check

When the harmonic grid changes chord between two adjacent notes, check
for cross-relations: conflicting accidentals on the same pitch class.

In practice this only arises in minor mode at boundaries involving V:

- Natural 7th (G) under iv or i, followed by raised 7th (G#) under V.
- Raised 7th (G#) under V, followed by natural 7th (G) under i or iv.
- Natural 6th (F) under a chord, followed by raised 6th (F#) from
  melodic minor ascending.

**Rule:** at every chord boundary, if the two adjacent notes are
different chromatic alterations of the same scale degree, reject the
sequence.

This check is applied during validation (§6) and costs negligible time.

## 5. Fill Rules

### 5.1 C-slot filling

Each C-slot has a harmonic slot position (determined by the note's tick
offset from bar start and the harmonic rhythm level).  The active chord
is read from the grid.  The C-slot pitch must be one of that chord's
scale degrees, adjusted for octave to stay within range.

**Choices per C-slot:** typically 2–3 (chord has 3 tones, minus range
violations or forbidden intervals).

**C-slot interval constraints:**
- Adjacent C-slots ≤ 5th apart (interval ≤ 4 diatonic steps).
- No same-pitch repetition on adjacent C-slots unless a cell boundary
  creates a neighbour figure (trochee C–P then iamb P–C with same C
  pitch = neighbour tone figure, which is acceptable).
- First C-slot: degree 0 or 4.
- Last C-slot: degree 0 or 4.
- Overall range (max C-slot pitch minus min C-slot pitch) must be
  between RANGE_LO (4) and RANGE_HI (11) diatonic steps.

### 5.2 P-slot filling

Between two anchor pitches (the nearest C-slots on either side), compute
the diatonic step path.  Let the anchors be N steps apart with M P-slots
to fill.

- **M = N:** one step per P-slot, straight line.  Simplest case.
- **M > N:** more notes than steps.  Insert a neighbour-tone detour:
  step past the target and step back (or back then forward).  Prefer
  upper neighbour on strong metric positions, lower on weak.
- **M < N:** fewer notes than steps; the gap is too large for stepwise
  fill.  Reject this skeleton.
- **M = 0:** two adjacent C-slots, no P between them.  Interval must be
  ≤ 2 steps; larger is rejected.

In minor mode, apply melodic minor (§2): if ascending through degrees
5–6–7–0, use raised 6th and 7th.  If descending, use natural.

### 5.3 Dissonance classification

P-slot notes that aren't chord tones are dissonances.  Three types, all
legal:

- **Passing tone:** same-direction motion through the dissonance.
- **Neighbour tone:** step away and return (or near-return).
- **Anticipation:** early arrival on the next chord's tone.

No additional constraint beyond the stepwise rule — any dissonance
reached and left by step is valid baroque practice.

## 6. Validation

After filling all slots, validate the complete sequence:

### 6.1 Range
Total range (highest minus lowest pitch) between RANGE_LO (4) and
RANGE_HI (11) diatonic steps.

### 6.2 Forbidden intervals
No tritone between adjacent notes.  In major: degrees 3–6 (F–B in C).
In minor: degrees 1–5 (B–F in A minor, natural forms).  Also check any
pair involving a raised degree against a natural degree that produces an
augmented interval.

### 6.3 Cross-relations
Apply the check from §4 at every chord boundary.

### 6.4 Terminal degrees
First note: degree 0 or 4.  Last note: degree 0 or 4.

### 6.5 Repeated pitches
No pitch class more than MAX_PITCH_FREQ (2) times.

### 6.6 Monotonic runs
No more than MAX_SAME_SIGN_RUN (5) consecutive notes in the same
direction.

## 7. Generation Algorithm

### Input
- Mode (major or minor)
- Tonic MIDI pitch
- Cell sequence with tick values (from rhythm generator)
- Number of bars (2)
- Bar ticks (8 for 4/4 at x2-tick resolution)

### Step 1: Determine harmonic rhythm level

Compute mean tick value of the cell sequence.
- Mean ≥ 3.0 → fast (8 slots)
- 1.5 ≤ mean < 3.0 → medium (4 slots)
- Mean < 1.5 → slow (2 slots)

### Step 2: Iterate harmonic patterns

For the determined level and mode, iterate over the stock progressions.

### Step 3: Build C/P grid

From the cell sequence, assign C or P to each note position.  Apply
boundary rule.  Compute each note's harmonic slot and active chord.

### Step 4: Enumerate C-slot skeletons

For each C-slot, enumerate valid chord tones within range.  Generate all
combinations subject to:
- Adjacent C-slots ≤ 4 steps apart
- No adjacent same-pitch (unless neighbour figure)
- First/last degree 0 or 4
- Range within RANGE_LO–RANGE_HI

Typical count: 50–200 valid skeletons per harmonic pattern.

### Step 5: Fill P-slots

For each skeleton, fill P-slots deterministically (§5.2).  Apply melodic
minor in minor mode (§2).

### Step 6: Validate

Apply all checks from §6.  Reject invalid sequences.

### Step 7: Score

1. **Contour:** reward arch and directed shapes, penalise shapeless.
2. **Harmonic variety:** reward subjects touching multiple chords.
3. **Leap placement:** reward largest interval in the first half (head).

### Step 8: Output

Return scored pitch sequences as `_ScoredPitch` objects compatible with
the selector.

## 8. Search Space

For 12 notes in 2 bars:

- Harmonic patterns per level: 4–6
- C-slots per cell sequence: 4–6
- Chord-tone choices per C-slot: 2–3
- Valid skeletons per pattern: ~50–200
- P-slot fill: deterministic (1 path or rejected)
- Total per cell sequence: ~200–1,200
- Across ~1,000 cell sequences: 200K–1.2M before scoring

Cap at top-K per note count after scoring.  This is the same
`_cached_validated_pitch` interface, producing the same `_ScoredPitch`
list, but from harmonic first principles instead of brute-force
enumeration.

## 9. What This Replaces

| Current module          | Replaced by                              |
|-------------------------|------------------------------------------|
| `head_enumerator.py`    | C-slot skeleton enumeration (step 4)     |
| `cpsat_generator.py`    | P-slot deterministic fill (step 5)       |
| `pitch_generator.py`    | New generator incorporating steps 1–8    |
| `validator.py`          | §6 validation                            |
| `contour.py`            | Shape classification retained for output |

## 10. What Remains Unchanged

- `rhythm_cells.py` + `duration_generator.py` (rhythm system)
- `selector.py` (consumes `_ScoredPitch` as before)
- `scoring.py` (receives degrees and ivs as before; extend with
  harmonic variety score)
- `stretto_gpu.py`, `stretto_constraints.py`
- `constants.py` (beyond rhythm changes already made)
