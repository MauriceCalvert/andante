# Andante Redesign

## Diagnosis

Three output pieces (gavotte, invention, minuet) were assessed. Two end on the
wrong scale degree. All three produce texturally identical quaver runs regardless
of genre. The invention has no audible imitation. These are not isolated bugs —
they are consequences of the current architecture.

### Root cause: the gap is the wrong unit of work

The builder composes music **one gap at a time** — the interval between two
adjacent schema degrees, typically spanning one bar. Each gap is filled
independently by selecting a diminution figure from a lookup table.

This produces:
- Stepwise runs (because each gap spans a second or third)
- No melodic coherence across gaps (each composed in isolation)
- Genre-indifferent texture (same figure table serves all genres)
- Unreliable cadential resolution (figure selection may not reach the target)

The musical unit should be the **phrase** (one complete schema), not the gap.

### What works

- The galant schema model is musicologically sound
- Schema YAML data is well-researched and correctly structured
- Planner layers 1–4 (rhetorical → tonal → schematic → metric) produce a
  valid structural skeleton
- The anchor system correctly identifies structural pitches
- Counterpoint checking logic (parallels, dissonance, overlap) is correct
- Range management and pitch placement are solid
- Duration arithmetic and offset calculations are reliable

### What doesn't work

- **Figuration strategy**: selects single-gap diminution figures from a
  universal table. No awareness of genre, phrase shape, or adjacent gaps.
- **Cadential strategy**: looks up cadential figures by interval. When no
  figure passes the filter cascade, the cadence fails silently.
- **Pillar/arpeggiated strategies**: too simple. Bass lines are either
  sustained notes or mechanical broken chords with no phrase awareness.
- **Voice writer gap dispatch**: each gap composed independently with only
  prev_exit_pitch connecting them. No phrase-level melodic planning.
- **Writing mode assignment**: voice_planning assigns FIGURATION to almost
  everything. The five-strategy dispatch adds complexity without variety.
- **Rhythmic uniformity**: rhythm templates are selected by note count and
  metre, not by genre character. A minuet gets the same rhythms as an
  invention.

---

## Design Principles for the Redesign

1. **The phrase is the unit of composition.** One schema = one phrase. The
   soprano and bass are each generated as complete phrases, not assembled
   from independent gap fragments.

2. **Genre defines rhythmic vocabulary.** Each genre provides a small set of
   idiomatic rhythmic cells. The phrase generator selects and chains these
   cells, not a universal diminution table.

3. **Counterpoint is checked inline, not post-hoc.** Generate-and-test loops
   are forbidden (X002). The bass is generated with awareness of the soprano,
   note by note, using the existing candidate filter. But the soprano is
   generated as a coherent phrase first.

4. **Cadences are formulaic.** The final schema in each section uses a
   hardcoded cadential voice-leading formula (clausula), not a strategy
   lookup. The formula guarantees correct resolution.

5. **Incremental migration, not big-bang rewrite.** The planner stays. The
   anchor system stays. The counterpoint checks stay. The builder's
   gap-dispatch loop is replaced by a phrase-dispatch loop. One genre is
   made to work end-to-end before touching the others.

---

## Risks and Mitigations

### Phrase boundary discontinuity

**Risk**: independently generated phrases may not join smoothly — register
leaps, awkward intervals at schema boundaries.

**Mitigation**: the phrase generator receives the previous phrase's final
pitch as input. The first note of the new phrase is the schema's entry
degree, placed in the nearest octave to the previous exit pitch (exactly as
the current anchor resolution does). This is a solved problem in the
existing code.

### Rhythmic monotony from small cell vocabulary

**Risk**: cycling through 3–5 rhythmic cells per genre could sound more
mechanical than the current system, not less.

**Mitigation**: cells are not cycled — they are selected per bar with
variation rules:
- Odd/even bar alternation
- Cadence-approach bars use longer note values
- Opening bars use simpler cells; continuation bars elaborate
- The phrase generator tracks which cells it has used recently and avoids
  immediate repetition (D007 extended to rhythm)

If this proves insufficient, the cell vocabulary can be expanded per genre
without architectural change.

### Schema degrees don't always fall on beat 1

**Risk**: the "one degree per bar on beat 1" model breaks for schemas like
meyer (two_dyads structure) or schemas with upbeat entries.

**Mitigation**: each schema definition already specifies its degree count
and bar span. The phrase generator uses a **degree placement map** that
assigns each degree to a specific bar and beat. For most schemas this is
bar N beat 1. For two_dyad schemas, degrees alternate between beat 1 and
beat 3 (or equivalent). The placement map is derived from the schema YAML,
not hardcoded.

### Cadences need specific voice-leading

**Risk**: "just place the degrees" doesn't produce proper cadential motion
(leading tone resolution, suspensions, clausula formulae).

**Mitigation**: cadential schemas (cadenza_semplice, cadenza_composta,
half_cadence, comma) are handled by a dedicated **cadence writer** that
produces fixed voice-leading patterns. These are not generated — they are
templates with rhythm adapted to the metre. Example for cadenza_semplice in
3/4: soprano 2→1 as dotted minim resolving on beat 1, bass 5→1 as minim +
crotchet. This is simpler and more reliable than the current CadentialStrategy.

### Counterpoint checking during soprano generation

**Risk**: if the soprano is generated first as a complete phrase, the bass
hasn't been composed yet, so there's nothing to check against.

**Mitigation**: the soprano phrase is checked only for self-consistency
(range, melodic interval, no repeated notes across bars). Full counterpoint
checks (parallels, dissonance, overlap) happen during bass generation, where
each bass note is validated against the completed soprano. This matches
baroque compositional practice: the soprano (cantus) is composed first, then
the bass is fitted to it.

### Imitation is more than copy-transpose

**Risk**: real inventions need tonal answers (modified intervals at the
fifth), episodes derived from subject fragments, and stretto.

**Mitigation**: phase 1 handles inventions as simple imitation — the subject
is stated in one voice and copied to the other at the fifth with tonal
answer adjustments (the existing answer_generator handles this). Episodes
and stretto are explicitly out of scope for phase 1. The architecture
supports adding them later because the phrase generator is called per schema
— an episode schema would invoke a different generation path.

### Loss of the diminution data

**Risk**: the figure catalogue (data/figuration/) represents real baroque
diminution practice. Discarding it loses musical authenticity.

**Mitigation**: the diminution data is not discarded. It is restructured.
Currently, figures are indexed by interval (unison, second_up, third_down,
etc.) and selected per gap. In the new model, figures are indexed by genre
and schema position, and selected per phrase. A "do_re_mi opening figure for
minuet" is a specific 2-bar melodic pattern, not two independent gap fills.
The existing figure degrees can be recombined into phrase-level patterns.

### Second system syndrome

**Risk**: 23k lines of Python + 8k lines of YAML. A rewrite risks losing
hard-won edge-case handling (offset arithmetic, range management, key
modulation).

**Mitigation**: the rewrite is scoped to the builder only. Shared modules
(key.py, diatonic_pitch.py, music_math.py, pitch.py, constants.py) are
unchanged. The planner is unchanged. The counterpoint checks (voice_checks.py,
faults.py) are unchanged. The phrase generator is a new module that calls
existing infrastructure. Estimated scope: replace ~2500 lines in
voice_writer.py + strategies with ~800 lines in a new phrase_writer.py.

---

## Architecture

### Current flow (broken)

```
planner → anchors → voice_planning → GapPlans → voice_writer
                                                    ↓
                                          for each gap:
                                            select strategy
                                            strategy.fill_gap()
                                            candidate_filter per note
                                          → notes
```

### Proposed flow

```
planner → anchors → phrase_planner → PhrasePlans → phrase_writer
                                                       ↓
                                             for each schema:
                                               generate soprano phrase
                                               generate bass phrase
                                               (inline counterpoint check)
                                             → notes
```

### New types

```
PhrasePlan:
    schema_name: str
    schema_degrees_upper: tuple[int, ...]
    schema_degrees_lower: tuple[int, ...]
    degree_placements: tuple[BeatPosition, ...]  # which bar/beat each degree lands on
    local_key: Key
    bar_span: int
    start_offset: Fraction
    rhythm_profile: str           # genre-specific rhythm vocabulary name
    is_cadential: bool
    prev_exit_pitch_upper: int | None
    prev_exit_pitch_lower: int | None

BeatPosition:
    bar: int          # relative to phrase start
    beat: int         # beat within bar

RhythmCell:
    durations: tuple[Fraction, ...]
    accent_pattern: tuple[bool, ...]   # which notes are metrically strong
    character: str                      # "plain", "dotted", "syncopated"
    genre_tags: frozenset[str]         # which genres use this cell
```

### New modules

| Module | Responsibility |
|--------|----------------|
| `builder/phrase_planner.py` | Convert anchors + genre config → PhrasePlans |
| `builder/phrase_writer.py` | Generate soprano + bass phrases from PhrasePlan |
| `builder/cadence_writer.py` | Hardcoded cadential voice-leading templates |
| `builder/rhythm_cells.py` | Genre-indexed rhythmic cell vocabulary |
| `data/rhythm_cells/` | YAML rhythm cell definitions per genre |

### Modules removed

| Module | Reason |
|--------|--------|
| `builder/figuration_strategy.py` | Replaced by phrase_writer |
| `builder/cadential_strategy.py` | Replaced by cadence_writer |
| `builder/pillar_strategy.py` | Absorbed into phrase_writer bass generation |
| `builder/staggered_strategy.py` | Absorbed into phrase_writer |
| `builder/arpeggiated_strategy.py` | Absorbed into phrase_writer bass generation |
| `builder/writing_strategy.py` | ABC no longer needed |
| `builder/figuration/loader.py` | Figure data restructured |
| `builder/figuration/rhythm_calc.py` | Replaced by rhythm_cells |
| `builder/figuration/types.py` | Replaced by new types |
| `planner/textural.py` | Texture encoded in genre rhythm profile |
| `planner/voice_planning.py` | Replaced by phrase_planner |

### Modules unchanged

| Module | Why |
|--------|-----|
| `planner/planner.py` | Orchestrator adapts to new interface |
| `planner/rhetorical.py` | Genre → trajectory, rhythm, tempo |
| `planner/tonal.py` | Affect → tonal plan |
| `planner/schematic.py` | Schema chain selection |
| `planner/metric/layer.py` | Bar assignments + anchors |
| `planner/metric/schema_anchors.py` | Schema → anchor expansion |
| `shared/*` | All shared infrastructure |
| `builder/voice_checks.py` | Counterpoint rules |
| `builder/faults.py` | Post-composition fault scan |
| `builder/io.py` | Output writers |
| `builder/compose.py` | Simplified: phrase loop replaces gap loop |

---

## Soprano Phrase Generation Algorithm

For one schema (e.g., do_re_mi: degrees 1→2→3, 2 bars, minuet 3/4):

1. **Place structural tones.** Map each schema degree to its bar/beat from
   the degree placement map. These are the fixed points the melody must hit.
   For do_re_mi in 3/4: degree 1 on bar 1 beat 1, degree 2 on bar 2 beat 1,
   degree 3 on bar 3 beat 1 (or wherever the next schema begins).

2. **Select rhythm cells.** For each bar, pick a rhythm cell from the genre
   vocabulary. The cell must start with a duration that covers the strong
   beat (where the structural tone sits). Cells are selected with variety
   constraints: no immediate repetition, cadence-approach bars prefer longer
   values.

3. **Fill melodic content.** Between structural tones, fill with stepwise
   motion (seconds) or occasional thirds, preferring the direction that
   connects to the next structural tone. The fill is constrained by:
   - Range (actuator_range)
   - No repeated pitch across bar boundaries (D007)
   - Leaps followed by contrary step
   - Melodic intervals ≤ octave

4. **Validate.** Check the complete phrase for self-consistency. If invalid,
   retry with a different cell selection (max 3 attempts, then assert fail).

### Example: do_re_mi in D major, minuet 3/4

```
Structural tones:  D4 (bar 1, beat 1)  E4 (bar 2, beat 1)
Target exit:       F#4 (degree 3, first beat of next schema)

Bar 1: Cell = [crotchet, crotchet, crotchet]
  D4 (structural) - C#4 (lower neighbour) - D4 (return)

Bar 2: Cell = [dotted crotchet, quaver, crotchet]  
  E4 (structural) - D4 (passing) - F#4 (approach target)
```

The exit pitch F#4 becomes prev_exit_pitch for the next schema.

---

## Bass Phrase Generation Algorithm

For one schema, given the completed soprano phrase:

1. **Place structural bass tones.** Schema bass degrees on the same
   bar/beat positions as soprano. Place in nearest octave to previous
   bass exit pitch, respecting bass range.

2. **Select bass texture.** From genre config: pillar, walking, or
   arpeggiated.
   - **Pillar**: hold each bass degree for the full bar. One note per bar.
   - **Walking**: stepwise motion between bass degrees, one note per beat.
   - **Arpeggiated**: broken chord pattern (root-third-fifth or similar).

3. **Check each bass note against soprano.** Using the existing
   candidate_filter: range, consonance on strong beats, no parallels,
   no voice overlap. If a note fails, try the nearest consonant
   alternative (existing _adjust_for_consonance logic).

---

## Cadence Writer

Cadential schemas are not generated — they use fixed templates.

### cadenza_semplice (soprano 2→1, bass 5→1)

```
4/4:  soprano: [2 as minim, 1 as minim]
      bass:    [5 as minim, 1 as minim]

3/4:  soprano: [2 as dotted minim]  → [1 as dotted minim]
      bass:    [5 as crotchet, 5 as crotchet, rest] → [1 as dotted minim]
```

### cadenza_composta (soprano 4→3→2→1, bass 5→1)

```
4/4:  soprano: [4 as crotchet, 3 as crotchet, 2 as crotchet, 1 as crotchet]
      bass:    [5 as minim, 1 as minim]

3/4:  soprano: [4 as crotchet, 3 as crotchet, 2 as crotchet] → [1 as dotted minim]
      bass:    [5 as dotted minim] → [1 as dotted minim]
```

### half_cadence (soprano varies, bass →5)

```
4/4:  soprano: last 2 notes descend by step to degree above 5
      bass:    [prev as minim, 5 as minim]
```

These templates are per-metre, stored in YAML.
They guarantee correct resolution because there is nothing to select or
filter — the voice-leading is predetermined.

---

## Migration Plan

### Phase 1: Minuet end-to-end (target: correct output)

1. Implement rhythm_cells.py with minuet vocabulary
2. Implement phrase_planner.py (anchors → PhrasePlans)
3. Implement phrase_writer.py (soprano generation)
4. Implement bass generation within phrase_writer
5. Implement cadence_writer.py with cadenza_semplice template
6. Wire into compose.py, bypassing old voice_writer for minuet
7. Verify: minuet ends on tonic, has 3/4 character, no D007 violations

### Phase 2: Gavotte (binary dance with upbeat)

8. Add gavotte rhythm cells
9. Handle upbeat in phrase_planner (existing upbeat logic reused)
10. Verify: correct ending, graceful character, no octave leaps

### Phase 3: Invention (counterpoint)

11. Add invention rhythm cells (continuous quavers / semiquavers)
12. Implement subject statement + tonal answer copy
13. Handle contrapuntal bass (walking texture with real independence)
14. Verify: audible imitation, active counterpoint, correct ending

### Phase 4: Cleanup

15. Remove dead strategies and figuration loader
16. Remove textural.py and old voice_planning.py
17. Update knowledge.md and laws.md
18. Run all genres, compare output quality

Each phase produces a working system. If phase 1 fails, the old path
still works for other genres.

---

## Success Criteria

A piece passes if:

1. **Correct tonal ending.** Final note is tonic in both voices.
2. **Genre-appropriate rhythm.** Minuet sounds like 3/4 dance, not
   continuous quavers. Gavotte has graceful paired quavers, not
   mechanical runs. Invention has contrapuntal activity.
3. **No D007 violations.** No repeated soprano pitch across bar boundaries.
4. **Melodic coherence.** No octave leaps except deliberate registral
   shifts. Predominant stepwise motion with occasional thirds.
5. **Proper cadences.** Section endings have correct voice-leading
   (2→1 over 5→1 for authentic, soprano to 5 for half cadence).
6. **No counterpoint faults.** No parallel fifths/octaves on strong beats.
   No voice overlap.
7. **Phrase shape.** Each schema produces an audibly distinct phrase with
   beginning, middle, and end — not a continuous undifferentiated stream.

---

## Layer Contract Tests

There is a testing gap between unit tests (individual functions) and system
tests (run pipeline, listen to MIDI). When the output is wrong, there is no
way to identify which layer broke.

Every layer must have a **contract test** that takes the layer's output in
isolation and verifies all invariants. These run without invoking any other
layer — the input is either a fixture or the output of the previous layer
captured as test data.

### Test architecture

```
Unit tests          →  function-level correctness
Layer contract tests →  each layer's output satisfies its postconditions
Integration tests    →  adjacent layers compose correctly
System tests         →  full pipeline produces valid .note output
```

Layer contract tests are the missing middle. They answer: "assuming this
layer received valid input, did it produce valid output?"

### Layer 1: Rhetorical

**Input**: GenreConfig  
**Output**: trajectory, rhythm_vocab, tempo  
**Invariants**:
- tempo > 0 and within genre's plausible range
- rhythm_vocab is non-empty
- trajectory length == number of sections in genre config
- all trajectory values are valid affect terms

### Layer 2: Tonal

**Input**: AffectConfig, GenreConfig  
**Output**: TonalPlan  
**Invariants**:
- every section in genre config has a corresponding TonalPlan section
- every key_area is a valid Roman numeral (I, IV, V, vi, etc.)
- every cadence_type is one of: authentic, half, deceptive, plagal
- final section cadence_type == "authentic"
- density and modality are valid enum values

### Layer 3: Schematic

**Input**: TonalPlan, GenreConfig, FormConfig, schemas  
**Output**: SchemaChain  
**Invariants**:
- every schema name in the chain exists in the schema catalogue
- section_boundaries length == number of genre sections
- boundaries are monotonically increasing
- boundaries tile the chain exactly: boundary[-1] == len(schemas)
- first schema in first section has position == "opening"
- last schema in each section has cadential_state appropriate to
  the section's cadence type ("closed" for authentic, "half" for half)
- no two adjacent schemas are identical (no immediate repetition)

### Layer 4: Metric

**Input**: SchemaChain, GenreConfig, FormConfig, KeyConfig, schemas, TonalPlan  
**Output**: bar_assignments, anchors, total_bars  
**Invariants**:
- bar_assignments: every genre section has an entry
- bar_assignments: ranges tile 1..total_bars with no gaps or overlaps
- anchors: sorted by bar_beat
- anchors: no duplicate bar_beat values
- anchors: every degree is 1–7
- anchors: every local_key is a valid Key
- anchors: first anchor has upper_degree==1, lower_degree==1 in home key
- anchors: last anchor has upper_degree==1, lower_degree==1 in home key
- anchors: anchor count >= 2 (at least start and end)
- anchors: for cadential schemas (cadenza_semplice, cadenza_composta),
  the final stage has the correct terminal degrees (soprano 1, bass 1)
- anchors: for half_cadence, the final stage has bass degree 5
- anchors: bar numbers in bar_beat are within 0..total_bars
- anchors: beat numbers are valid for the metre

### Phrase Planner (new)

**Input**: anchors, genre_config, schemas  
**Output**: tuple[PhrasePlan, ...]  
**Invariants**:
- one PhrasePlan per schema in the chain
- PhrasePlan.schema_degrees_upper matches schema definition
- PhrasePlan.schema_degrees_lower matches schema definition
- degree_placements length == number of schema degrees
- every placement falls within the phrase's bar span
- placements are in chronological order
- rhythm_profile exists in the genre's rhythm cell vocabulary
- is_cadential == True iff schema is cadential type
- start_offset of phrase N+1 == start_offset of phrase N + phrase N's
  total duration (phrases tile exactly, no gaps)
- prev_exit_pitch is None only for the first phrase

### Phrase Writer — Soprano (new)

**Input**: PhrasePlan  
**Output**: tuple[Note, ...]  
**Invariants**:
- note count >= 1
- all pitches within actuator_range
- all durations are in VALID_DURATIONS
- durations sum to exactly the phrase's total bar span
- no timing gaps between consecutive notes
- no timing overlaps between consecutive notes
- the note at each degree_placement offset has the correct scale degree
  (verified by converting MIDI back to degree via local_key)
- no repeated pitch across bar boundaries (D007)
- no melodic interval > octave (12 semitones)
- leaps (> 4 semitones) are followed by step in contrary direction,
  except at phrase boundaries
- if is_cadential: final note is degree 1 in local_key

### Phrase Writer — Bass (new)

**Input**: PhrasePlan, completed soprano notes  
**Output**: tuple[Note, ...]  
**Invariants**:
- all pitches within bass actuator_range
- all durations are in VALID_DURATIONS
- durations sum to exactly the phrase's total bar span
- no timing gaps or overlaps
- bass note at each degree_placement offset has the correct bass degree
- if is_cadential: final bass note is degree 1 in local_key
- no parallel fifths or octaves on strong beats (checked against soprano)
- no voice overlap with soprano at any offset
- strong-beat notes are consonant with soprano (no seconds, tritones)

### Compose (integration)

**Input**: all phrase outputs concatenated  
**Output**: Composition  
**Invariants**:
- exactly 2 voices present (for current genres)
- total duration == total_bars * bar_length
- no note in either voice exceeds total duration
- no note has negative offset
- notes within each voice are sorted by offset
- no overlapping notes within the same voice
- first note offset == 0 (or -upbeat for upbeat pieces)
- last note offset + duration == total duration

### Fault scan (existing, unchanged)

**Input**: Composition  
**Output**: list of faults  
**Invariants**:
- zero faults is the target, but faults are advisory
- every fault has: type, bar, beat, voice, description
- fault types are from a known enum

---

### Test implementation rules

1. **One test file per layer.** `tests/test_layer1_rhetorical.py`, etc.
   Not mixed into other test files.

2. **Fixtures are frozen layer outputs.** Each test file includes a
   fixture (or loads one from `tests/fixtures/`) that provides the
   layer's input. The fixture is the known-good output of the previous
   layer for a specific genre (e.g., minuet).

3. **Tests are exhaustive on invariants.** Every invariant listed above
   becomes one test function (or one parametrised case). No invariant is
   tested "implicitly" by another test.

4. **Tests are genre-parametrised.** Each contract test runs for every
   genre in the `data/genres/` directory. A new genre automatically gets
   tested.

5. **Contract tests run in CI before system tests.** If a layer contract
   test fails, system tests are skipped — there is no point generating
   a .note file from broken intermediate output.

6. **Regression fixtures.** When a bug is found via system test, the
   failing layer's input is captured as a new fixture and a contract
   test is added for the specific invariant that was violated. This
   prevents the same class of bug from recurring.
