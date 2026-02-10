## Task: Phase 12 — Algorithmic Figuration, Harmony Threading, Register Floor

Read these files first:
- `builder/figuration/soprano.py`
- `builder/figuration/selection.py`
- `builder/figuration/rhythm_calc.py`
- `builder/figuration/loader.py`
- `builder/figuration/types.py`
- `builder/soprano_writer.py` (lines 200-460, the figuration call and bar loop)
- `builder/phrase_types.py` (PhrasePlan fields: degrees_lower, degree_positions, degree_keys)
- `data/figuration/diminutions.yaml` (current figure vocabulary)
- `shared/constants.py` (DENSITY_RHYTHMIC_UNIT)
- `shared/pitch.py` (degree_to_nearest_midi)

### Musical Goal

Three connected improvements to soprano melodic content:

**A. Figuration density.** Currently, when a rhythm cell demands more notes
than the selected figure provides, `_fit_degrees_to_count` pads with
neighbour-tone oscillation — a mechanical filler that sounds like a stuck
ornament. Bars with 8 quavers over a step interval get 2 real degrees and
6 padding notes. The listener hears repetitive oscillation where they should
hear directed melodic motion. This violates Principles 1 (no tension arc
within the figure), 5 (same behaviour regardless of context), and 9 (no
faults but no music).

**B. Semiquaver runs.** Rhythm cells for `sixteen_semiquavers` and
`eight_quavers` exist but the figuration system cannot fill them musically.
Invention episodes and energetic sections need scalar runs, decorated
passages, and sequential patterns at sixteenth-note density. Without them,
the invention sounds plodding — every bar at the same rhythmic density
regardless of genre character.

**C. Low soprano register.** Gavottes place soprano structural tones in the
E4-D4 area (bars 3-5), well below the idiomatic gavotte tessitura. The cause:
`degree_to_nearest_midi` chases `prev_midi` downward. Once one structural tone
lands low, the next follows. A gavotte soprano should sit in the G4-C5 range
for most of its phrases, reaching D5-E5 at climactic points. The current
output sounds like an alto line, not a soprano melody.

### Idiomatic Model

**What the listener hears** when figuration is done well: each bar has
directed melodic motion that arrives somewhere. A descending scale run builds
momentum into a cadence. A circling figure decorates a held harmony with
purposeful oscillation. An arpeggiated leap outlines the chord before
stepping to the next tone. The figures are varied — a plain step here, a
decorated passage there — and the density increases as the phrase approaches
its cadence. No bar sounds like padding.

**What a competent musician does** when filling the gap between two structural
tones:

1. *Knows the interval and the note count.* These determine the generation
   principle. A step with 4 notes is a circolo (neighbour decoration). A step
   with 8 notes is a double circolo or a decorated walk. A third with 6 notes
   is stepwise filling with a passing neighbour. A fifth with 8 notes is
   arpeggiation through chord tones with stepwise connections between them.

2. *Knows the harmony.* The bass degree at each structural position implies a
   chord. A soprano filling a fourth over a tonic bass passes through the
   third and fifth (chord tones). Over a dominant bass, the passing tones are
   different. The chord tones are safe landing points; non-chord tones are
   passing or neighbour decorations between them.

3. *Knows the phrase position.* At phrase opening: plainer figures, fewer
   ornaments, establishing the line. At mid-phrase: denser, more decorated,
   building energy. At cadential approach: directed motion, tighter intervals,
   scalar runs converging on the cadence. A musician does not use the same
   figuration density throughout.

4. *Knows the genre.* A gavotte is graceful — moderate density, some dotted
   figures, not perpetual motion. An invention episode is energetic —
   continuous quavers or semiquavers, sequential patterns, scalar runs.
   A sarabande is sustained — long notes, sparse decoration, ornamental
   weight on beat 2. The figuration density matches the genre character.

**Rhythm** (Principle 6): The rhythm cells already provide genre-appropriate
note counts per bar. The problem is that the figuration system cannot fill
those counts musically. This phase does not change rhythm cell selection —
it makes the pitch content worthy of the rhythmic structure the cells provide.

**Genre character** (Principle 5): The `character` field in PhrasePlan
("plain", "expressive", "energetic", "ornate", "bold") already varies per
section. The algorithmic generator should use this to bias toward plainer
or denser generation principles. Gavotte section A (expressive) gets moderate
decoration. Invention narratio (energetic) gets continuous-motion figures.

**Phrase arc** (Principle 5): The `position` parameter already distinguishes
"passing" from "cadential". The generator should produce plainer figures for
early spans in a phrase and more directed/decorated figures for later spans.
The existing `bar_num` rotation provides variation within a position category.

### What Bad Sounds Like

- **Padding oscillation**: the soprano repeats a neighbour-tone pattern
  ([+1, 0, -1, 0]) for 6+ notes because the figure had only 2 degrees.
  Sounds like a stuck ornament. Violates Principle 1 (no tension, no
  direction) and Principle 9 (technically legal, musically dead).

- **Scale exercise**: every filled gap is stepwise with no decoration,
  because the generator only knows start pitch, end pitch, and step count.
  Sounds like a student practising scales between anchor points. Violates
  Principle 5 (no idiom, no vocabulary of choices).

- **Harmony-blind arpeggiation**: a fourth filled by stepping through
  scale degrees that clash with the implied bass harmony. The soprano
  passes through the 4th degree over a tonic chord where a 3rd or 5th
  would be consonant. Violates Principle 4 (bass implies harmony; ignoring
  it produces scale exercises, not voice-leading).

- **Alto gavotte**: soprano structural tones at E4-D4, the whole melody
  sitting in the lower half of the soprano range. Sounds subdued and
  misplaced. Violates Principle 5 (genre character — a gavotte soprano
  should be graceful and light, not heavy and low).

- **Uniform density**: every bar in every section filled with the same
  figuration principle regardless of phrase position or genre. Destroys
  the phrase arc (Principle 5) and makes the piece sound mechanical
  (Principle 9).

### Known Limitations

1. **Harmony inference is approximate.** The bass degree implies a chord,
   but not uniquely. Degree 1 is usually tonic (1-3-5), but could be vi
   in first inversion. This phase uses the simplest mapping: degree →
   triad built on that degree in the current key. A musician would use
   figured bass or harmonic context. The gap is acceptable because even
   approximate chord tones are better than scale-degree-only filling, and
   the system lacks figured bass data. Known limitation, not a bug.

2. **Cross-relation risk with generated chromatic tones.** The algorithmic
   generator produces diatonic degrees only. It does not introduce chromatic
   approach tones (those are a future phase). Therefore no new cross-relation
   risk. If chromatic generation is added later, it must pass through the
   existing `prevent_cross_relation` filter.

3. **Motivic recall is preserved but not enhanced.** The existing
   `recall_figure_name` parameter passes through to the generator. The
   generator will not produce recalled figures (those are YAML-defined named
   figures). Motivic recall for algorithmically generated passages is a
   future concern (Figurenlehre labelling).

4. **Cadential figuration unchanged.** Cadential schemas use
   `cadence_writer.py` with fixed clausula templates. This phase does not
   touch cadential writing. The `position="cadential"` flag in the generator
   biases toward directed, convergent figures — it does not override the
   cadence writer.

5. **Strong-beat consonance not individually checked.** The algorithmic
   generator produces degree sequences without knowing which degree falls
   on a strong beat. Structural tones are consonant with the bass (the schema
   guarantees this). Generated passing tones between structural tones may
   land on strong or weak beats depending on rhythm cell timing. Weak-beat
   dissonance is idiomatic (Principle 3 — passing 7ths and 2nds on weak
   beats are part of the style). Strong-beat dissonance between generated
   tones and bass is possible but rare: most figuration notes are stepwise
   neighbours of consonant structural tones. A future phase could coordinate
   degree sequences with rhythm cell accent patterns.

6. **Metric alignment of chord tones.** When the generator arpeggiates
   through chord tones on large intervals, it does not know which degree
   falls on a metrically accented position. A musician would place chord
   roots on strong beats and passing tones on weak beats. The generator
   produces a linear degree sequence; the rhythm cell assigns timing. This
   means chord tones may land on weak beats. Acceptable for this phase —
   the result is harmonically aware (correct pitches) but not metrically
   aligned (correct pitches on correct beats). Metric alignment requires
   the generator to know the accent pattern, which is a future refinement.

### Implementation

#### 12a: Algorithmic figuration generator

Create `builder/figuration/generator.py` — a new module that generates
degree sequences algorithmically, replacing the lookup-then-pad flow for
non-recalled, non-cadential spans.

The generator is a pure function:
```
generate_degrees(
    interval: str,          # "unison", "step_up", "third_down", etc.
    note_count: int,        # exact number of degrees to produce
    character: str,         # "plain", "expressive", "energetic", etc.
    position: str,          # "passing" or "cadential"
    chord_tones: tuple[int, ...],  # diatonic offsets of chord tones from start
    bar_num: int,           # for V001 deterministic variation
) -> tuple[int, ...]       # exactly note_count degree offsets from start
```

Generation rules by interval class:

**Unison (interval distance 0):**
- note_count 2: `[0, 0]` (repeated tone)
- note_count 3: `[0, -1, 0]` or `[0, 1, 0]` (mordent / upper neighbour) — alternate by bar_num
- note_count 4: `[0, 1, 0, -1]` or `[0, -1, 0, 1]` (turn / inverted turn) — alternate by bar_num
- note_count 5+: tile the 4-note turn pattern, vary direction by bar_num parity
- If character is "plain" and count >= 4, prefer `[0, 0, ...]` with single neighbour at midpoint

**Step up (interval distance +1):**
- note_count 2: `[0, 1]` (plain step)
- note_count 3: `[0, -1, 1]` (lower neighbour approach) or `[0, 1, 1]` when chord_tones favour it
- note_count 4: `[-1, 0, -1, 1]` (circolo_mezzo_up pattern) or `[0, -1, 0, 1]` (turn then step)
- note_count 8: `[-1, 0, -1, 1, 0, -1, 0, 1]` (double circolo) or stepwise walk with neighbour decoration every 2 notes
- General for N: interpolate between start(0) and end(1), inserting neighbour decorations at regular intervals. For chord_tone-aware filling: prefer chord tones as passing landmarks.

**Step down (interval distance -1):** mirror of step up with negated offsets.

**Third up/down (interval distance ±2):**
- note_count 2: `[0, 2]` (direct — rare, only for plain character)
- note_count 3: `[0, 1, 2]` (stepwise fill)
- note_count 4: `[0, 1, 0, 2]` (neighbour then step) or `[0, -1, 1, 2]` (undershoot approach)
- note_count 6+: stepwise fill (0→2) with neighbour decorations on intermediate degrees
- Chord-tone aware: if chord has a tone at offset 1, use it as passing tone; otherwise neighbour-decorate the endpoints

**Fourth/fifth (interval distance ±3, ±4):**
- note_count 2-3: direct or with single passing tone
- note_count 4: arpeggiate through chord tones. E.g., fourth up with I chord: `[0, 2, 1, 3]` (broken third) or `[0, 2, 4, 3]` if 4 is a chord tone
- note_count 8+: arpeggiate chord tones as skeleton, fill stepwise between each pair. E.g., fifth up (0→4) with chord tones at 0,2,4: skeleton [0,2,4], fill [0,1,2,3,2,3,4,4]
- Chord-tone aware: this is where `chord_tones` matters most. Without chord tones, fall back to stepwise filling (still better than padding).

**Sixth and larger (interval distance ±5+):**
- Tirata (scale run): `[0, 1, 2, ..., N]` or `[0, -1, -2, ..., -N]` to fill count
- For counts larger than the interval, decorate with neighbour tones at midpoint
- Chord-tone aware: use chord tones as accent points in the run

**Variation by bar_num (V001):** Where alternatives exist (e.g., upper vs lower neighbour, circolo vs turn), select by `bar_num % len(alternatives)`. This is deterministic and provides bar-to-bar variety.

**Variation by character:**
- "plain": prefer shorter decorations, more repeated tones, fewer neighbours
- "expressive": prefer neighbours and turns, moderate decoration
- "energetic": prefer continuous motion, more passing tones, longer runs
- "ornate"/"bold": prefer decorated runs, double circolo patterns

**Variation by position:**
- "passing": full range of figures, varied by character
- "cadential": prefer directed motion toward the final degree, fewer diversions, tighter intervals in last 2-3 notes

The existing YAML `diminutions.yaml` figures are still loaded and used when:
1. `recall_figure_name` is set (motivic recall — unchanged)
2. The interval/count combination has a high-weight named figure that matches exactly

Priority order in `select_figure` (modify `builder/figuration/selection.py`):
1. Motivic recall (existing, unchanged)
2. Exact match from diminutions.yaml with weight >= 2.0 (preserves strong named figures)
3. Algorithmic generation via `generate_degrees`
4. Fallback: `_fit_degrees_to_count` with warning (should be rare)

#### 12b: Thread bass harmony to figuration

Wire the bass degree at each structural position from `PhrasePlan` into
`figurate_soprano_span`, so the generator knows the implied chord.

Changes to `builder/soprano_writer.py`:
- In the figuration span loop (around line 233), for each span between
  structural tones at index `si`, read `plan.degrees_lower[si]` (the bass
  degree at that position).
- Compute chord tones from bass degree + key:
  ```
  bass_deg = plan.degrees_lower[si]
  chord_tones = _implied_chord_tones(bass_degree=bass_deg, key=a_key)
  ```
  where `_implied_chord_tones` returns diatonic offsets of the triad built
  on that bass degree, relative to the soprano's start pitch for this span.
- Pass `chord_tones` to `figurate_soprano_span`.

Add helper function `_implied_chord_tones` to `builder/soprano_writer.py`:
```
def _implied_chord_tones(bass_degree: int, key: Key, soprano_start_degree: int) -> tuple[int, ...]:
    """Compute diatonic offsets of chord tones relative to soprano start.

    Bass degree implies a triad: root, third, fifth built on that degree.
    Returns offsets from soprano_start_degree to each chord member.
    """
```
The offsets are computed as `(chord_degree - soprano_start_degree) % 7` mapped
to signed offsets within ±6 of zero. This gives the generator knowledge of
which scale degrees are consonant with the current harmony.

Changes to `builder/figuration/soprano.py`:
- Add `chord_tones: tuple[int, ...] = ()` parameter to `figurate_soprano_span`.
- Pass `chord_tones` to `select_figure` and to `generate_degrees`.

Changes to `builder/figuration/selection.py`:
- Add `chord_tones` parameter to `select_figure`.
- Pass through to `generate_degrees` when algorithmic path is taken.

#### 12c: Soprano register floor

The problem: `degree_to_nearest_midi` places structural tones nearest to
`prev_midi`. If a phrase exits at D4, the next phrase's first structural tone
lands near D4 even though the genre's tessitura should be higher.

Fix in `builder/soprano_writer.py`, structural tone placement loop (around
line 160):

After computing `midi` via `degree_to_nearest_midi`, add a genre-aware
floor check. If the placed pitch is more than a fourth below
`biased_upper_median`, and an octave-up placement is within range, prefer
the higher octave:

```python
# Genre-aware register floor: prevent downward drift
register_floor: int = biased_upper_median - 5  # perfect fourth (5 semitones) below median
if midi < register_floor:
    octave_up: int = midi + 12
    if octave_up <= plan.upper_range.high:
        midi = octave_up
```

This is a soft floor (L003 forbids hard range clamps). It only fires when
the pitch is significantly below the genre's natural tessitura and the
octave-up alternative is valid. The `-5` threshold (a fourth) allows natural
descent below the median without triggering correction — only drift beyond
a fourth is corrected.

Exception: if the bass anchor at this position is known and the octave-up
soprano would cross the bass (violating L004), keep the lower placement.
Since bass structural tones are in `plan.degrees_lower`, compute the bass
MIDI at this position and verify `octave_up > bass_midi` before applying.

Wait — soprano is voice 0, bass is voice 3. Soprano above bass is always
the case. The check is: does `octave_up` remain in the soprano range? That's
already handled by `octave_up <= plan.upper_range.high`.

### Constraints

- Do not modify `builder/cadence_writer.py`. Cadential figuration is out of scope.
- Do not modify rhythm cell selection (`builder/rhythm_cells.py`). The rhythm
  cells already provide correct note counts; this phase fills them better.
- Do not modify `builder/bass_writer.py`. Bass generation is unchanged.
- Do not invent new rhythm cells or modify `data/rhythm_cells/cells.yaml`.
- Do not introduce chromatic tones in the algorithmic generator. Diatonic only
  for this phase.
- Do not remove `diminutions.yaml` or `figurations.yaml`. They remain as named
  figure vocabulary for motivic recall and high-weight exact matches.
- Do not remove `_fit_degrees_to_count`. Keep it as last-resort fallback with
  a logger.warning when it fires.
- Before proposing any new mechanism, grep for existing code first.
- `generate_degrees` must be a pure function: no state, no side effects, no
  RNG (A005 — deterministic in executor). Variation via `bar_num` only.

### Checkpoint (mandatory)

After implementation, run the pipeline for all 8 genre/key combinations
(invention C/Am, minuet C, gavotte C/Am, sarabande C/Am, bourree C).

Bob:
1. Does the soprano have more varied melodic content? Cite specific bars
   where figuration changed from padding to directed motion.
2. Are there any bars where the soprano still oscillates mechanically
   (the old padding pattern)? Count them.
3. In gavottes: where does the soprano sit registrally? Is it in the G4-C5
   range for most bars, or still drifting to E4-D4?
4. In inventions: are there semiquaver passages? Do they sound like runs
   or like random fast notes?
5. Does the soprano relate to the bass harmony? In bars with large soprano
   intervals, do the passing tones outline the chord or clash with it?
6. What's still wrong?

Chaz:
For each of Bob's complaints, trace to a code location and propose a
minimal fix (wire before invent). Specifically:
- How many times did `_fit_degrees_to_count` fire? (It should be near zero.)
- Did `generate_degrees` produce correct note counts for all spans?
- Are chord_tones correctly computed from bass degrees?
- Did the register floor fire in gavottes? Which bars?

### Acceptance Criteria

1. Zero `_fit_degrees_to_count` padding warnings for note counts ≤ 16
   (proxy: the generator handles all standard rhythm cell counts)
2. Gavotte soprano: ≥ 80% of structural tones at or above G4 (MIDI 67)
   (proxy: Bob's ear is the real test — does it sound like a soprano, not alto?)
3. Invention: at least one passage with semiquaver density per piece
   (proxy: `sixteen_semiquavers` cell filled musically, not padded)
4. Zero new faults in any genre
5. Non-cadential figuration uses chord tones for leaps of a fourth or larger
   (proxy: Bob hears arpeggiation outlining harmony, not scale runs)
6. All existing tests pass without modification
