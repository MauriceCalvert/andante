# Subject Generator Redesign — Generation Chain

## Problem

The current generator (`motifs/subject_generator.py`) uses random search
with post-hoc filtering. It generates random pitch sequences, checks for
leap+fill, appends random tails, and scores against affect figurae.
The result is musically arbitrary: every subject has a leap because the
filter demands one, but no subject has a *character* because the
generator has no model of what makes subjects sound different from each
other.

The archetype catalogue (`docs/subject_archetypes.md`) defines six
subject types distilled from WTC I/II, Handel, Corelli, Vivaldi, and
Telemann. The redesign replaces random search with archetype-driven
generation: the archetype constrains the contour, interval vocabulary,
and rhythmic profile, so the generator produces subjects that belong
to a recognisable family.

## Design Principles

1. **Archetype first, randomness second.** The archetype determines
   the contour shape, interval vocabulary, and rhythmic character.
   The RNG fills in the degrees within those constraints. This is
   the opposite of the current design, which generates freely and
   filters.

2. **Three-part structure is mandatory.** Every subject has a
   Kopfmotiv (head), Fortspinnung (continuation), and Kadenz
   (cadential close). The archetype defines rules for each part
   independently.

3. **Rhythm and pitch are generated together.** The current design
   picks a rhythm cell, then fills pitches into it. The new design
   generates pitch-rhythm pairs from the archetype's profile,
   because archetype character is inseparable from rhythm
   (Principle 6).

4. **Answer viability is checked during generation, not after.** A
   subject that cannot produce a good tonal answer is rejected
   before scoring, not discovered downstream.

5. **Fragment viability is checked during generation.** A subject
   whose head does not make a usable episode cell is penalised.

## Generation Chain

```
affect + genre + mode + metre + seed
    │
    ▼
┌─────────────────────────┐
│ 1. Archetype Selection  │  affect→archetype map, filtered by
│                         │  genre and mode constraints
└────────────┬────────────┘
             │ archetype + direction
             ▼
┌─────────────────────────┐
│ 2. Kopfmotiv Generation │  Archetype-specific pitch+rhythm
│                         │  rules. Start on triad member.
└────────────┬────────────┘
             │ head (degrees + durations)
             ▼
┌─────────────────────────┐
│ 3. Fortspinnung         │  Continues head energy.
│    Generation           │  Archetype-specific: gap-fill
│                         │  (triadic), continuation (scalar),
│                         │  kinetic half (compound), etc.
└────────────┬────────────┘
             │ head + continuation
             ▼
┌─────────────────────────┐
│ 4. Kadenz Generation    │  Resolves to stable degree.
│                         │  May slow rhythmically.
│                         │  Ensures total = integer bars.
└────────────┬────────────┘
             │ full subject (degrees + durations)
             ▼
┌─────────────────────────┐
│ 5. Melodic Validation   │  No 7th leaps, no tritone outlines,
│                         │  no consecutive same-dir leaps,
│                         │  no unresolved leading tones.
│                         │  (Keep existing filters.)
└────────────┬────────────┘
             │ valid subject
             ▼
┌─────────────────────────┐
│ 6. Answer Analysis      │  Locate tonic-dominant boundary.
│                         │  Determine tonal vs real answer.
│                         │  Reject if no clean answer exists.
└────────────┬────────────┘
             │ subject + answer type
             ▼
┌─────────────────────────┐
│ 7. Fragment Analysis    │  Identify natural break points.
│                         │  Score head as episode cell.
│                         │  Check inversion viability.
└────────────┬────────────┘
             │ subject + fragment catalogue
             ▼
┌─────────────────────────┐
│ 8. Scoring              │  Affect-figurae match (existing).
│                         │  Archetype fidelity score.
│                         │  Fragment quality score.
└────────────┬────────────┘
             │ scored subject
             ▼
┌─────────────────────────┐
│ 9. Batch Selection      │  Generate N candidates.
│                         │  Return best by composite score.
└─────────────────────────┘
```

## Step Details

### 1. Archetype Selection

Input: affect, genre, mode, metre.

Use the affect→archetype map from `subject_archetypes.md`. Filter by:
- Genre compatibility (genre→archetype map)
- Mode bias (major favours triadic/scalar/dance; minor favours
  chromatic/compound/scalar)
- Metre compatibility (dance archetype requires matching dance metre)

If multiple archetypes pass, the RNG chooses one, weighted by
primary (P) vs secondary (S) affinity.

Also choose **direction** (ascending or descending) from the affect's
contour profile. Ascending = energy/joy; descending = gravity/lament.
This is a tendency, not absolute — the RNG may override with lower
probability.

Output: `(archetype: str, direction: str)`.

### 2. Kopfmotiv Generation

**Duration budget.** The Kopfmotiv receives `total_beats` (from target
bars × bar duration) and consumes a fraction of it. The fraction is
archetype-specific:
- Scalar, Triadic, Chromatic, Rhythmic: ~0.4–0.5 of total
- Compound: ~0.25–0.33 (the static half is short)
- Dance: ~0.5 (periodic phrasing)

The remaining beats pass to the Fortspinnung, which reserves
`min_kadenz_beats` (1–2 beats depending on metre) for the Kadenz.
This prevents the Kadenz from being crammed or stretched.

Each archetype has its own head-generation logic:

**Scalar:** Choose a starting triad degree (1, 3, or 5). Step in
the chosen direction for 4–8 notes. All intervals are ±1 (stepwise).
Rhythm: even values from metre's note vocabulary (crotchets for grave,
quavers for allegro — tempo/density from affect).

**Triadic:** Choose a starting triad degree. Arpeggiate: intervals
of ±2, ±3, ±4 (thirds and their compounds). 3–5 notes. Rhythm:
longer values on chord tones.

**Chromatic:** Choose a starting degree. Diatonic stepwise motion
with 1–2 chromatic inflections (half-step where a whole step is
diatonic). 4–6 notes. Rhythm: long values for gravity. The chromatic
inflection is either: (a) descending lamento (b4→b3→3), (b) chromatic
neighbour (3→#3→4 or 3→b3→2), (c) chromatic approach (→#4→5).

**Rhythmic:** Choose a starting triad degree. Narrow pitch range
(4th–5th). The defining rhythmic figure is chosen from a vocabulary:
dotted (French), repeated-note, syncopated. Pitches are chord tones
and neighbours — secondary to rhythm.

**Compound:** Two sub-generations. Static half: 2–3 notes, long
values, narrow range (held note, repeated note, or slow arpeggio).
Then separately generate the kinetic half under step 3.

**Dance:** Head generation follows the dance metre's characteristic
pattern. Gigue: wide leaps in compound groups. Minuet: stepwise,
weighted on beat 1. Bourrée: sturdy upbeat.

The head always starts on a triad member (degree 0, 2, or 4).

Output: `(degrees: tuple[int, ...], durations: tuple[float, ...],
beats_used: float)`.

### 3. Fortspinnung Generation

**Duration budget.** Receives `remaining_beats - min_kadenz_beats`.
Must not exceed this budget. If the archetype's continuation logic
would overshoot, it truncates at the nearest rhythmic grouping
boundary.

Continues the head's energy, archetype-specific:

**Scalar:** Continue stepping. May introduce one change of direction
(the "turn" point). If ascending head, the continuation may keep
ascending or begin descent. Total range: 5th to octave.

**Triadic:** Gap-fill. After the arpeggiated head, step back in
contrary motion, filling the gap the arpeggio left. Shorter note
values than the head.

**Chromatic:** Continue the chromatic motion or resolve toward
diatonic stability. The continuation should not add more chromatic
notes than the head — the chromaticism is concentrated in the head.

**Rhythmic:** Maintain the rhythmic figure while the pitch moves
more freely (wider steps, direction changes). The rhythm stays
consistent; the pitch gains range.

**Compound:** This IS the kinetic half. Scale run, sequential
figuration, or virtuosic passage. Short note values. Covers
more pitch distance than the static head. **Must start on the
last pitch of the static head** — no gap, no re-anchoring. The
melodic continuity across the static→kinetic boundary is what
makes the compound subject a single gesture rather than two
fragments glued together.

**Dance:** Continues the dance pattern. Periodic: complete the
2-bar or 4-bar phrase unit inherent in the dance.

Constraint: the continuation must not introduce a new leap larger
than the head's largest interval (the head "owns" the dramatic
gesture).

Output: append to head's degrees and durations.

### 4. Kadenz Generation

Close the subject on a stable degree (1, 3, or 5). Rules:

- If the subject has been ascending, approach the final note from
  below (stepwise).
- If descending, approach from above.
- May augment the last 1–2 notes (longer values = rhetorical weight).
- Total duration must sum to an integer number of bars.

If the current total is close to N bars but slightly short/long,
adjust the Kadenz's final note duration to make it exact. If the
overshoot is more than a quaver, reject and retry.

Output: complete subject `(degrees, durations, n_bars)`.

### 5. Melodic Validation

Keep the existing filters from `subject_generator.py`:
- No 7th leaps (10–11 semitones)
- No tritone leaps (6 semitones)
- No tritone outlines in any 4-note span
- No consecutive leaps in the same direction
- No unresolved leading tones

These are independent of archetype.

### 6. Answer Analysis

Locate the tonic–dominant boundary: the first note on degree 4
that meets BOTH conditions:
- **Metrically strong**: beat 1 or beat 3 in 4/4, beat 1 in 3/4,
  beat 1 or beat 4 in 6/8. A degree 4 on a weak beat (passing
  between 3 and 5) is not a modulation point.
- **Contextually confirmed**: followed by movement that stays in
  the dominant area (degrees 3–5 region), not immediately
  returning to the tonic area.

Common cases:

- Scalar ascending 1→5: boundary at the strong-beat degree 4.
  Tonal answer.
- Triadic 1-3-5: boundary at degree 4 if on a strong beat.
  Tonal answer, mutation at 5.
- Chromatic: boundary at the first chromatic inflection point
  that falls on a strong beat.
- Rhythmic (narrow range): may not cross the boundary → real answer.
- Compound: boundary typically between the two halves.

If no clean answer can be derived (ambiguous boundary, ugly
mutation), reject the candidate. The answer generator
(`motifs/answer_generator.py`) handles the actual computation;
this step just checks feasibility.

### 7. Fragment Analysis

Identify natural fragmentation points:
- Head/continuation boundary (always a valid break)
- Rhythmic grouping boundaries (after a long note)
- Metric boundaries (barlines)

Score the head as an episode cell:
- Length: 2–4 beats is ideal for sequential treatment
- Rhythmic distinctiveness: how recognisable is the head in isolation?
- Sequential viability: does the head transpose cleanly through
  the scale (no awkward augmented steps)?

Check inversion viability: negate all intervals, check melodic
validity of the inverted form.

### 8. Scoring

Composite score from:
- **Affect-figurae match** (existing `score_motif_figurae` +
  `score_subject_affect`). Weight: 0.3
- **Archetype fidelity**: how well does the subject match its
  archetype's constraints? Penalise deviations (e.g. a "scalar"
  subject with a large leap in the continuation). Weight: 0.3
- **Fragment quality**: head episode-cell score + inversion
  viability. Weight: 0.2
- **Rhythmic interest**: number of distinct durations, presence
  of the archetype's characteristic rhythm. Weight: 0.2

### 9. Batch Selection

Generate N candidates (default 50) across the eligible archetypes.
Return the top candidate by composite score.

Diversity: if all top candidates are the same archetype, keep the
best of each archetype that appears in the top 10.

## Module Structure

```
motifs/
    subject_generator.py     — public API: generate_subject(),
                               generate_fugue_triple()
                               (rewritten, keeps same interface)
    archetype_selector.py    — step 1: select archetype + direction
    kopfmotiv.py             — step 2: archetype-specific head gen
    fortspinnung.py          — step 3: archetype-specific continuation
    kadenz.py                — step 4: cadential close + bar alignment
    answer_analyser.py       — step 6: tonic-dominant boundary + feasibility
    fragment_analyser.py     — step 7: break points + episode cell scoring
    subject_scorer.py        — step 8: composite scoring
    archetype_types.py       — dataclasses: ArchetypeSpec, ArchetypeConstraints
    head_generator.py        — DELETED (replaced by kopfmotiv.py)
    tail_generator.py        — DELETED (replaced by fortspinnung.py + kadenz.py)
    answer_generator.py      — KEPT (called by answer_analyser)
    countersubject_generator.py — KEPT
    affect_loader.py         — KEPT
    figurae.py               — KEPT
```

## Data

```
data/archetypes/
    scalar.yaml       — contour constraints, interval vocab, rhythm profile
    triadic.yaml       — "
    chromatic.yaml     — "
    rhythmic.yaml      — "
    compound.yaml      — "
    dance.yaml         — "
```

Each YAML file defines:
```yaml
name: scalar
head:
  min_notes: 4
  max_notes: 8
  intervals: [-1, 1]        # stepwise only
  start_degrees: [0, 2, 4]  # triad members
  range_min: 4               # 4th
  range_max: 7               # octave (in scale degrees)
continuation:
  rule: "continue_or_reverse"
  max_new_interval: 2        # no larger leap than head
  range_extension: 2         # may extend head range by 2 degrees
kadenz:
  approach: "stepwise_from_direction"
  stable_degrees: [0, 2, 4]
  may_augment: true
rhythm:
  profile: "even"            # even | long_short | short_long | bipartite | dance
  density_from_affect: true  # affect tempo maps to note values
affect_affinity:
  primary: [maestoso, energetico]
  secondary: [serioso]
genre_affinity:
  primary: [invention, fugue_keyboard]
  secondary: [sonata_da_chiesa]
mode_bias:
  major: 1.0
  minor: 0.8
metre_filter: null           # no metre restriction (dance has one)
direction_bias:
  ascending: 0.5
  descending: 0.5
```

## Migration Path

1. Write `archetype_types.py` — dataclasses and YAML loader.
2. Write the six archetype YAML files.
3. Write `archetype_selector.py` (step 1).
4. Write `kopfmotiv.py` (step 2) — one function per archetype.
5. Write `fortspinnung.py` (step 3) — one function per archetype.
6. Write `kadenz.py` (step 4).
7. Write `answer_analyser.py` (step 6) — wraps existing answer_generator.
8. Write `fragment_analyser.py` (step 7).
9. Write `subject_scorer.py` (step 8).
10. Rewrite `subject_generator.py` to use the chain.
11. **Listening gate: SG-LISTEN.** For each of the six archetypes,
    generate a fugue triple in a suitable affect/mode/metre. Write
    per-archetype MIDI files (`samples/scalar_Majestaet_major.mid`,
    etc.) and a combined sampler MIDI that plays all six back-to-back
    with a bar of silence between each. Human listens. If archetypes
    do not sound distinct, diagnose before proceeding.
12. Delete `head_generator.py` and `tail_generator.py`.
13. Verify: generate_fugue_triple still works, invention pipeline
    still runs.

Steps 1–6 are the core. Steps 7–9 are scoring refinements that can
be simplified initially (e.g. fragment analysis returns a flat score
of 1.0) and improved later.

## Task Phases

Mapping from migration path steps to task brief IDs:

| Phase      | Migration steps | Content                                          | Status    |
|------------|-----------------|--------------------------------------------------|-----------|
| SG1        | 1–3             | archetype_types.py, YAML files, archetype_selector.py | Done      |
| SG2        | 4               | kopfmotiv.py                                     | Done      |
| SG3        | 5               | fortspinnung.py                                  | Done      |
| SG4        | 6               | kadenz.py                                        | Done      |
| SG5        | chain step 5    | melodic_validator.py                             | Done      |
| SG6        | 7               | answer_analyser.py                               | Done      |
| SG7        | 8               | fragment_analyser.py                             | Done      |
| SG8        | 9               | subject_scorer.py                                | Done      |
| SG9        | 10              | Rewrite subject_generator.py to use the chain    | Done      |
| SG-LISTEN  | 11              | Listening gate: per-archetype MIDI samples        | Pending   |
| SG-CLEAN   | 12–13           | Delete old generators, verify pipeline            | Pending   |

## Open Questions

**Q1: Should archetype YAML files also define rhythm cells, or should
rhythm cells stay in code?**

Current: rhythm cells are hard-coded in `head_generator.py` by metre.
Option A: Move to YAML per archetype (each archetype has its own
rhythm vocabulary). Option B: Keep a shared rhythm cell pool, but let
the archetype specify which cells are eligible via tags (e.g.
"even", "dotted", "syncopated").

Recommendation: **B**. The rhythm cells are metre-dependent and
shared across archetypes. The archetype selects from them by profile
tag.

**Q2: How many candidates should we generate per call?**

Current: 50 with affect, 5 without. With archetype constraints the
search space is much smaller (most random sequences will match the
archetype). Suggest: 30 candidates, with a max_attempts of 200.
If the archetype is very constrained (dance in 6/8), fewer attempts
will be needed.

**Q3: Should the generator handle multi-subject fugues?**

Not now. The archetype catalogue is for single subjects. Double/triple
fugue subjects are a future extension. For now, one subject per call.

**Q4: What about the existing `FugueTriple` and the invention
pipeline?**

`generate_subject()` keeps its current signature. The invention
pipeline calls it exactly as before. The only visible change is that
subjects will have an `archetype` field on `GeneratedSubject`.
`generate_fugue_triple()` likewise unchanged in interface.

## Not In Scope

- Thematic planner (separate design, depends on subject catalogue)
- Three-voice fugue infrastructure (separate, `fugue_scoping.md`)
- Countersubject generation changes (CS generator is adequate)
- Answer generator changes (existing logic is correct)
