# Imitative Composition Path — Design Document

## Scope

This document specifies a second composition path for subject-driven
genres: invention, fugue, toccata, sonata. It runs alongside the
galant path with no shared internal logic. Both paths produce the
same output contract (PhrasePlans) so the phrase_writer and compose.py
need minimal change.

The galant path is untouched. It stays in its current files. The
imitative path lives in its own folder.

---

## Branching Point

`planner/planner.py` currently runs Layers 1–4 sequentially. The
branch happens after Layer 2 (tonal), before Layer 3 (schematic):

```
L1 Rhetorical  →  trajectory, rhythm_vocab, tempo
L2 Tonal       →  tonal_plan, density, modality
                   │
         ┌─────────┴─────────┐
         │                   │
    composition_model:   composition_model:
       "galant"            "imitative"
         │                   │
    L3 Schematic         L3i Subject Planner
    L4 Metric            L4i Entry Layout
    L5 Phrase Planning   L5i Phrase Planning
         │                   │
         └─────────┬─────────┘
                   │
              PhrasePlans
                   │
           L6 Phrase Writer
           L7 Composition
```

Genre YAML declares `composition_model: galant` (default) or
`composition_model: imitative`. The single branch in planner.py:

```python
if genre_config.composition_model == "imitative":
    phrase_plans = plan_imitative(...)
else:
    phrase_plans = plan_galant(...)
```

Both return `tuple[PhrasePlan, ...]`. Everything downstream is shared.

---

## What the Galant Path Does (for contrast)

1. **L3 Schematic**: tonal_plan → schema chain (do_re_mi, prinner, ...).
   Schemas define soprano and bass degree sequences.
2. **L4 Metric**: schemas → bar assignments, anchor pitches per bar.
3. **L5 Phrase Planning**: schema chain → PhrasePlans with schema
   degrees, key areas, bass texture.
4. **L6 Phrase Writer**: Three-way dispatch — cadential (template),
   thematic (overlay), schematic (Viterbi from degrees).

The thematic overlay was the failed attempt to graft subject-driven
material onto a schema skeleton. In the imitative path, there is no
skeleton to graft onto. The subject IS the skeleton.

---

## Imitative Path: Input Contract

The imitative planner receives:

| Source | Data | Use |
|--------|------|-----|
| Genre YAML | `entry_sequence` | The form — who plays what, in what key |
| Genre YAML | `thematic.voice_count` | Number of voices (2 for invention, 3–4 for fugue) |
| Genre YAML | `sections[]` | Section names and characters (for L1/L2 arc) |
| Genre YAML | `metre`, `tempo`, `rhythmic_unit` | Time signature and tempo |
| Fugue file | Subject (notes, bars, key) | The DNA |
| Fugue file | Answer (tonal/real) | Derived from subject |
| Fugue file | Countersubject (if any) | Complementary material |
| L1 | Trajectory, tension arc | Rhetorical shape |
| L2 | Modality, density | Harmonic character |

It does NOT receive a schema chain, schema definitions, or anchors
derived from schema degrees. Those concepts do not exist in this path.

---

## L3i: Subject Planner

### Purpose

Convert the entry_sequence into a complete structural plan: what
material occupies every bar, in what key, with what function.

### The Three Dimensions

Every entry varies across three dimensions. A subject that sounds
identical every time it appears is not an invention — it's a loop.
Variety across entries is what makes the form musical.

| Dimension | Controls | Values |
|-----------|----------|--------|
| **Material** | What notes play | subject, answer, cs, head, tail, inversion, augmentation |
| **Pairing** | How voices relate | independent, parallel_10ths, contrary_motion, invertible |
| **Texture** | How notes are delivered | plain, bariolage_single, bariolage_double, bariolage_arpeggio, compound_melody, ostinato |

These are already fields in `BeatRole` (`material`, `pairing`,
`texture`) but the old thematic planner set them all to defaults.
The imitative path must vary them across entries.

In the entry_sequence YAML, each voice slot carries all three:

```yaml
# [material, key, texture, pairing]
- upper: [subject, I, plain, independent]    # exposition: simple
  lower: none
- upper: [cs, I, plain, parallel_10ths]      # answer entry: paired
  lower: [answer, V, plain, parallel_10ths]
- upper: [subject, vi, bariolage_single, contrary_motion]  # development: varied
  lower: [cs, vi, plain, contrary_motion]
```

Defaults (for backward compatibility and concise YAML):
- texture: `plain`
- pairing: `independent`

So `[subject, I]` is shorthand for `[subject, I, plain, independent]`.

The subject_planner stamps these values into VoiceAssignment. The
thematic_renderer reads them and adjusts rendering:
- `bariolage_single`: alternates subject notes with a pedal pitch
- `parallel_10ths`: transposes companion voice to a tenth above/below
- `contrary_motion`: inverts melodic direction of companion
- `compound_melody`: distributes subject across two registers

The renderer already has the `pairing` and `texture` fields — it
just needs implementations for each value. These can be phased in:
Phase 1 uses `plain`/`independent` only; later phases add textures.

### Pairing: How It Works Mechanically

Pairing controls the vertical relationship between voices. The
current Viterbi solver finds the cheapest path through a corridor
of diatonic pitches. It has no way to demand a specific interval
relationship. Pairing requires **corridor constraints**.

| Pairing | Mechanism | Implementation |
|---------|-----------|----------------|
| `independent` | Default Viterbi — any interval allowed | No change |
| `parallel_10ths` | Lock companion to leader ± 16 semitones | Corridor restricted to {leader_pitch + 15, +16, +17} (major/minor 10th ± 1 for passing tones) |
| `parallel_6ths` | Lock companion to leader ± 8–9 semitones | Corridor restricted to {leader_pitch + 8, +9} |
| `contrary_motion` | When leader rises, companion falls (and vice versa) | Cost modifier: same-direction motion gets COST_CONTRARY_VIOLATION; opposite-direction gets bonus |
| `invertible` | Voices can swap octave positions and remain correct | Corridor includes both above and below leader; cost penalises intervals that break under inversion (2nds, 7ths, 4ths above bass) |

The mechanism is a `pairing_constraint` parameter passed to
`generate_voice()`. It modifies the corridor builder:

```python
def build_corridors(
    ...,
    pairing_constraint: str = "independent",
) -> list[set[int]]:
```

For `parallel_10ths`: at each beat, the corridor contains only
pitches within ±1 semitone of (leader_pitch + 16). The solver
*must* land on a tenth; passing tones are the only freedom.

For `contrary_motion`: the corridor is unrestricted, but
`transition_cost()` applies a directional penalty. This is softer
— it biases toward contrary motion without forbidding parallel.

For `invertible`: the corridor is unrestricted, but `pairwise_cost()`
applies extra cost to intervals that produce faults under octave
inversion (P4 above bass → P5 below, which is fine; but P4 below
bass → P5 above, which creates a dissonance).

### Texture: How It Works Mechanically

Texture controls how a single voice's notes are elaborated. The
current system generates a plain melodic line. Texture transforms
that line into something richer.

| Texture | What the listener hears | Mechanism |
|---------|------------------------|-----------|
| `plain` | Simple melodic line | Default — no transformation |
| `bariolage_single` | Subject notes alternating with a held pedal pitch | Post-process: interleave subject notes with repeated anchor pitch. Anchor = local tonic or dominant. Doubles the note count, halves durations. |
| `bariolage_double` | Subject notes alternating between two pedal pitches | Same as single but two anchors (e.g. tonic + fifth). Three-note cycle. |
| `bariolage_arpeggio` | Subject notes woven into arpeggiated chord | Post-process: insert chord tones from harmonic grid between subject notes. |
| `compound_melody` | Single voice implies two voices via register leaps | Solver mode: invert leap cost (large leaps preferred, small steps penalised). Cost weights modified: `COST_LEAP` becomes negative bonus, `COST_STEP` becomes penalty. Alternating-register constraint forces notes to oscillate between high and low bands. |
| `ostinato` | Repeated short pattern underneath | Not a Viterbi output. Fixed pattern from fragment, repeated for N bars. Trivial. |

Two implementation strategies:

**Post-process (bariolage, ostinato):** Generate the subject line
normally, then transform it. A `TextureDecorator` takes plain notes
and returns elaborated notes. This is safe — it doesn't fight the
solver.

```python
def apply_texture(
    notes: tuple[Note, ...],
    texture: str,
    anchor_pitch: int | None,
    harmonic_grid: HarmonicGrid | None,
) -> tuple[Note, ...]:
```

**Solver mode (compound melody):** Modify cost weights before
calling `generate_voice()`. This is harder but necessary because
compound melody can't be post-processed — it changes which pitches
are chosen, not how they're decorated.

```python
def texture_cost_weights(texture: str) -> dict[str, float]:
    if texture == "compound_melody":
        return {"COST_LEAP": -5.0, "COST_STEP": 10.0, ...}
    return {}  # default weights
```

### Where Pairing and Texture Enter the Pipeline

```
L3i Subject Planner
  │ stamps material + pairing + texture into VoiceAssignment
  v
L4i Entry Layout
  │ builds PhrasePlan with pairing_constraint and texture per voice
  v
L6 Phrase Writer
  │
  ├─ thematic voice: render subject/answer/CS notes
  │   │
  │   ├─ if texture != plain: apply_texture(notes, texture, ...)
  │   └─ result: elaborated thematic notes
  │
  ├─ companion voice: Viterbi with constraints
  │   │
  │   ├─ pairing_constraint → corridor builder
  │   ├─ texture == compound_melody → modified cost weights
  │   └─ result: constrained counterpoint
  │
  └─ both voices assembled into PhraseResult
```

The pairing constraint applies to the **companion** voice (the one
Viterbi generates). The texture applies to the **thematic** voice
(the one with subject/answer material). They don't conflict because
they operate on different voices.

### Entry Types

The entry_sequence is a list. Each element is one of:

| Type | YAML | Meaning |
|------|------|---------|
| **Entry** | `{upper: [subject, I], lower: [cs, I]}` | Thematic material in one or both voices |
| **Cadence** | `{type: cadence, kind: half}` or `{type: cadence, kind: authentic}` | Cadential punctuation |
| **Stretto** | `{upper: [subject, I], lower: [subject, I], delay: 1}` | Overlapping entries |
| **Pedal** | `{type: pedal, degree: 5, bars: 4}` | Dominant or tonic pedal point |

**Episodes are NOT declared in the YAML.** They are auto-inserted by
the subject planner at section boundaries (see Episodes section below).
The YAML contains only thematic entries, cadences, stretto, and pedals.

Current YAML uses a simpler format. This extends it. The old format
(`upper: [subject, I], lower: none`) remains valid for plain entries.
New types are added for cadences, stretto, and pedals.

### Bar Count Derivation

Each entry type has a known bar cost:

| Type | Bars |
|------|------|
| Entry | `subject_bars` (from fugue data, typically 2) |
| Episode | computed by subject planner from key distance (2–4 bars) |
| Cadence | from cadence template (currently 1, will be 2 after reform) |
| Stretto | `subject_bars` (overlap means voices start at different times but the passage length = subject_bars) |
| Pedal | declared in YAML (`bars: N`) |

Total bars = sum of all declared entry bar costs + auto-inserted
episode bars + cadence bars. The piece length falls out of the data;
there is no hardcoded bar count.

### Key Plan Derivation

Each entry carries its own key. The sequence of keys across entries
IS the tonal plan for this piece. L2's tonal_plan (key area
suggestions per section) can influence the entry_sequence design,
but the entry_sequence is the single source of truth for what key
is active where.

### Output

`SubjectPlan`: a flat list of `BarAssignment` covering every bar:

```
BarAssignment:
    bar: int              # 1-based
    section: str          # "exordium", "narratio", etc.
    function: str         # "entry", "episode", "cadence", "stretto", "pedal"
    local_key: Key
    voices: dict[int, VoiceAssignment]

VoiceAssignment:
    role: ThematicRole    # SUBJECT, ANSWER, CS, EPISODE, FREE, CADENCE, PEDAL
    material_key: Key     # key for transposition
    fragment: str | None  # "head", "tail", None
    fragment_iteration: int  # for sequential descent in episodes
```

This replaces both SchemaChain and the thematic BeatRole overlay.
One structure, not two competing ones.

---

## Implied Harmonic Grid

### The Problem

The Viterbi solver depends on `chord_pcs` (pitch classes of the
active chord) to calculate `chord_tone_cost`. Without a harmonic
grid, the companion voice runs in scale-only mode — correct
intervals against the subject, but no sense of whether the subject
is currently implying tonic or dominant. The countersubject will
wander harmonically.

In the galant path, the harmonic grid comes from schema annotations
(HRL-1/HRL-2: `Schema.harmony` → `HarmonicGrid`). The imitative
path has no schemas, so it must derive harmony from the subject
itself.

### Solution: Subject-Projected Harmony

L4i must output TWO things per phrase:

1. **Thematic surface** — the notes of the subject/answer/CS/episode
2. **Implied harmonic grid** — the chords those notes represent

The harmonic grid is projected from subject data, not from schemas.

### Where Harmony Comes From

| Entry Type | Harmonic Source |
|------------|----------------|
| Subject entry | Subject's own harmonic annotation (see below) |
| Answer entry | Subject annotation transposed to answer key |
| CS entry | Same grid as the paired subject/answer entry |
| Episode | Sequential pattern (e.g. descending fifths: I→IV→viio→iii) |
| Cadence | Cadence template (already carries implicit harmony: V→I) |
| Pedal | Single chord (V or I) for duration of pedal |

### Subject Harmonic Annotation

The subject definition (fugue file or YAML) must carry an implied
harmony per bar or per beat. This is the harmonic interpretation of
the subject — what a continuo player would realise above the bass
notes.

For a 2-bar subject in C major:
```
subject_harmony: ["I", "V"]
```

For finer granularity (per beat):
```
subject_harmony: ["I", "I", "V", "V7", "I", "I", "IV", "V"]
```

When the subject is transposed to a new key (e.g. answer in G major),
the Roman numerals stay the same — they're relative to the local key.
The `HarmonicGrid` resolves them to pitch classes using the local
key, exactly as it does for galant schemas.

### Episode Harmony

Episodes are sequences. Each iteration implies a local harmony:

- **Descending step** (C→B→A→G): implies I→viio→vi→V in the home key
- **Circle of fifths** (C→F→Bb→Eb): implies I→IV→bVII→bIII
- **Descending third** (C→A→F→D): implies I→vi→IV→ii

The episode_planner generates a per-bar Roman numeral sequence from
the pattern type and starting key. This feeds into the same
`HarmonicGrid` infrastructure.

### Integration with Viterbi

The existing `generate_voice()` pipeline accepts
`harmonic_grid: HarmonicGrid | None`. The imitative path populates
this grid from subject-projected harmony instead of schema
annotations. No Viterbi code changes needed — the interface is
already correct.

Workflow:
1. L3i places subject notes (thematic surface)
2. L4i builds `HarmonicGrid` from subject_harmony + local key
3. L6 phrase_writer passes grid to Viterbi for companion voices
4. Viterbi reads subject as `existing_voices` (avoid collisions)
   AND reads grid for `chord_pcs` (find consonant notes)
5. Result: harmonically aware counterpoint

### Implementation

New file: `planner/imitative/harmony_projection.py`

- `project_entry_harmony(subject_harmony, local_key, bars)` →
  `HarmonicGrid`
- `project_episode_harmony(pattern, direction, start_key, bars)` →
  `HarmonicGrid`
- `project_pedal_harmony(degree, local_key, bars)` → `HarmonicGrid`

All return the same `HarmonicGrid` type from `builder/harmony.py`.
The grid infrastructure is shared between paths — only the source
of Roman numerals differs.

### Answer Logic (Real vs. Tonal)

Already implemented in `motifs/answer_generator.py`. Tonal mutation
handles the 1↔5 boundary crossing (if subject starts on 5, answer
starts on 1, not 2). Real transposition applies elsewhere. The
answer's harmonic annotation uses the same Roman numerals as the
subject, resolved in the answer's local key.

---

## L4i: Entry Layout

### Purpose

Convert SubjectPlan → PhrasePlans. This is the bridge to the shared
downstream pipeline.

### Phrase Boundaries

In galant, phrase boundaries align with schema boundaries. In
imitative music, phrase boundaries align with entry boundaries:

- Each entry (subject/answer) = one phrase
- Each episode = one phrase
- Each cadence = one phrase
- Stretto = one phrase (even though voices overlap)
- Pedal = one phrase

A phrase in this context is a rendering unit — the phrase_writer
processes one PhrasePlan at a time.

### PhrasePlan Population

For each phrase, the PhrasePlan contains:

| PhrasePlan field | Galant source | Imitative source |
|-----------------|---------------|------------------|
| `schema_name` | schema name | entry type (e.g. "subject_entry", "episode", "cadence") |
| `local_key` | schema chain key area | entry key from SubjectPlan |
| `start_offset` | metric layer | cumulative from entry bar costs |
| `phrase_duration` | schema bar count | entry bar count × bar_length |
| `anchors` | schema degree → pitch | not used (subject provides notes directly) |
| `thematic_roles` | overlay from thematic planner | directly from SubjectPlan.voices |
| `is_cadential` | schema.position == "cadential" | BarAssignment.function == "cadence" |
| `upper_range`, `lower_range` | genre config | genre config (shared) |
| `bass_texture`, `bass_pattern` | genre config | not used (bass is subject-driven or Viterbi) |

Key difference: galant PhrasePlans carry schema degrees as anchors,
and the phrase_writer interpolates between them. Imitative PhrasePlans
carry thematic_roles as the primary content, and the phrase_writer
renders subject/answer/CS material directly. Anchors are absent or
minimal (entry pitch, exit pitch for voice continuity).

---

## L6 Phrase Writer: Imitative Dispatch

The three-way dispatcher already exists (TD-3):

1. **Cadential** → cadence_writer templates (shared with galant)
2. **Thematic** → `_write_thematic` renders subject/answer/CS/episode
3. **Schematic** → galant Viterbi fill from schema degrees

For imitative genres, path 3 (schematic) is never reached. Every
phrase is either cadential or thematic. If a voice is FREE within a
thematic phrase (e.g. monophonic opening), the existing tail-fill
logic in `_write_thematic` generates Viterbi counterpoint.

The phrase_writer needs no structural change. It already does the
right thing when thematic_roles are populated — the problem was that
the galant pipeline underneath was fighting it.

### Episode Rendering

Episodes are currently rendered by `_render_episode_fragment` which
transposes the subject head down by step. This is correct in
principle but crude in execution. The imitative path improves this:

- Episodes are auto-inserted by the subject planner at section
  boundaries (not declared in YAML)
- Fragment, direction, and bar count are determined by the key
  distance between the last entry of one section and the first
  entry of the next
- The lead voice plays the fragment in sequence (descending or
  ascending through keys)
- The companion voice gets Viterbi counterpoint against the fragments
- Episode key sequence: each bar's fragment_iteration determines the
  transposition level (e.g. descending by step: C→B→A→G)

This uses the existing render infrastructure with parameters derived
from tonal context rather than heuristic placement.

### Stretto Rendering

Stretto entries have two voices starting the subject at different
times (delay specified in YAML). The renderer:

1. Renders voice 0 subject from bar start
2. Renders voice 1 subject from bar start + delay
3. Both are time-windowed to the phrase boundary
4. No Viterbi fill needed — both voices have material

The `delay` field means voice 1's subject starts N beats after
voice 0. For a 1-beat delay in 4/4, voice 1 enters on beat 2 of
bar 1. Voice 0 has beat 1 alone (monophonic moment).

### Pedal Point

The pedal voice holds a single pitch (dominant or tonic) for the
specified bars. The other voice plays freely above it — Viterbi with
the pedal as an existing voice. This creates the tension-building
zone described in Maurice's cadence research (the "grand cadence"
mechanism).

---

## Episodes: Auto-Inserted at Section Boundaries

Episodes are what make an invention sound like an invention rather
than a sequence of subject entries. They provide:

- **Directed motion** between key areas (sequence descending by step)
- **Rhythmic relief** (fragments are shorter than full subject)
- **Developmental interest** (the listener hears the subject's DNA
  in a new context)

Episodes are developmental passages. They exist because the ear has
heard the subject and now wants to hear what can be done with it.
They are NOT gap-fillers triggered mechanically by key distance.

### Where Episodes Go

Episodes are inserted at **section boundaries** only — the gaps
between exposition, development, and recapitulation. They are not
inserted between consecutive entries within the same section.

The entry_sequence YAML marks section boundaries with comments.
The subject planner identifies them by the section labels on
consecutive entries.

**Exposition exemption:** the transition from I to V within the
exposition is not an episode trigger. The tonal answer itself
handles this key shift — the 1↔5 mutation is built into the answer
material. Subject followed by its answer is one gesture (call and
response), not two entries needing a bridge. This is a definitional
property of the exposition, not a distance calculation.

### Episode Parameters

At each section boundary, the subject planner measures the key
distance between the last entry of one section and the first entry
of the next (tonic-to-tonic, in pitches not Roman numerals).

**Length:** proportional to key distance. Minimum 2 bars,
typically 2–4 bars. All section boundaries get an episode.

**Direction:** determined by the key relationship. If the next
section's tonic is lower, the sequence descends. If higher, it
ascends.

**Lead voice:** defaults to the opposite of the preceding entry's
lead voice (the voice that played subject or answer), so the
fragment hands off naturally to the next entry.

### Episode Construction

An episode takes one fragment of the subject (head or tail) and
sequences it through a pattern of keys or scale degrees. Common
baroque patterns:

| Pattern | Description | Example (C major) |
|---------|-------------|--------------------|
| Descending step | fragment descends diatonically | C→B→A→G |
| Descending third | fragment descends by thirds | C→A→F→D |
| Circle of fifths | fragment follows V→I progressions | C→F→Bb→Eb |
| Ascending step | fragment ascends (rarer, for climax) | G→A→B→C |

The companion voice provides counterpoint — either a second fragment
in contrary motion (double episode) or free counterpoint (Viterbi).

### Episode in SubjectPlan

Although episodes are not in the YAML, they appear in the SubjectPlan
after the subject planner inserts them. Each episode bar gets a
VoiceAssignment:

- Lead voice: `role=EPISODE, fragment="head", fragment_iteration=0,1,2,3`
- Companion voice: `role=FREE` (Viterbi fills against episode fragments)

For double episodes (both voices have fragments):
- Voice 0: `role=EPISODE, fragment="head", fragment_iteration=N`
- Voice 1: `role=EPISODE, fragment="tail", fragment_iteration=N`
---

## Cadence Placement

Cadences are explicit entries in the sequence, not inferred from
schema position. The entry_sequence specifies:

- **Where**: between entries, at section boundaries
- **What kind**: half, authentic (PAC), deceptive, plagal
- **How long**: determined by cadence template (currently 1 bar,
  2 bars after cadence reform)

A typical invention cadence plan:

| Location | Kind | Purpose |
|----------|------|---------|
| After exposition (entries 1–2) | Half cadence | Open the first section |
| After middle entries | Deceptive or half | Maintain momentum |
| Before final entry | Half cadence | Set up return to tonic |
| After final entry | Authentic (PAC) | Close the piece |

The cadence_writer is shared between galant and imitative paths.
It reads from the same templates.yaml. The cadence reform (expanding
to 2 bars) benefits both paths.

---

## Worked Example: C Major Invention

### Entry Sequence (YAML — what the composer writes)

```yaml
entry_sequence:
  # Exposition (I → V: answer handles transition, no episode)
  - upper: [subject, I]                              # bars 1-2: soprano solo
    lower: none
  - upper: [cs, I, plain, parallel_10ths]             # bars 3-4: answer at 10ths
    lower: [answer, V, plain, parallel_10ths]
  # --- section boundary: V → vi --- episode auto-inserted
  # Development — varied textures
  - upper: [subject, vi, bariolage_single, contrary_motion]  # varied entry
    lower: [cs, vi, plain, contrary_motion]
  - upper: [cs, IV, plain, invertible]                # invertible CP
    lower: [subject, IV, plain, invertible]
  # --- section boundary: IV → V --- episode auto-inserted
  # Recapitulation — intensifying
  - upper: [subject, V, compound_melody, independent] # compound melody
    lower: [cs, V]
  - upper: [cs, I, plain, parallel_10ths]             # return to 10ths
    lower: [subject, I, plain, parallel_10ths]
  - {type: pedal, degree: 5, bars: 2}                # dominant pedal
  - {type: cadence, kind: authentic}                  # final PAC
```

Note: no episodes in the YAML. The subject planner detects two
section boundaries (exposition→development, development→recap) and
inserts episodes automatically. Episode length and direction are
derived from the key distance at each boundary.

Note how the three dimensions vary across entries:
- Exposition: plain/independent (establishing)
- Development: bariolage + contrary motion (exploratory)
- Development: invertible counterpoint (intensifying)
- Recap: compound melody, then return to parallel 10ths (climax → resolution)

No two subject entries are identical in all three dimensions.

### Resulting Bar Map (after auto-insertion)

```
Bar  Section      Function    Upper           Lower           Key
  1  exposition   entry       SUBJECT         ---             C maj
  2  exposition   entry       SUBJECT         ---             C maj
  3  exposition   entry       CS              ANSWER          G maj
  4  exposition   entry       CS              ANSWER          G maj
     ---- auto-inserted episode: V → vi (G maj → A min, step up, 2 bars) ----
  5  episode      episode     FREE            EPISODE head.0  G maj
  6  episode      episode     FREE            EPISODE head.1  G maj
  7  development  entry       SUBJECT         CS              A min
  8  development  entry       SUBJECT         CS              A min
  9  development  entry       CS              SUBJECT         F maj
 10  development  entry       CS              SUBJECT         F maj
     ---- auto-inserted episode: IV → V (F maj → G maj, step up, 2 bars) ----
 11  episode      episode     EPISODE head.0  FREE            F maj
 12  episode      episode     EPISODE head.1  FREE            F maj
 13  recap        entry       SUBJECT         CS              G maj
 14  recap        entry       SUBJECT         CS              G maj
 15  recap        entry       CS              SUBJECT         C maj
 16  recap        entry       CS              SUBJECT         C maj
 17  recap        pedal       FREE            PEDAL (G)       C maj
 18  recap        pedal       FREE            PEDAL (G)       C maj
 19  recap        cadence     (authentic cadence template)    C maj
```

19 bars. The YAML declares 12 bars of entries + 2 pedal + 1 cadence =
15 bars. The planner adds 4 episode bars at section boundaries.
Every bar accounted for. No Viterbi wallpaper except the companion
voice in episodes — and there the Viterbi is writing counterpoint
against audible thematic material, which is what it's good at.

```
andante/
  planner/
    planner.py            # branch: galant or imitative
    rhetorical.py         # L1 (shared)
    tonal.py              # L2 (shared)
    schematic.py          # L3 galant only
    metric/               # L4 galant only
    galant/               # (future: move schematic + metric here)
    imitative/
      __init__.py         # empty
      subject_planner.py      # L3i: entry_sequence → SubjectPlan
      entry_layout.py          # L4i: SubjectPlan → PhrasePlans
      harmony_projection.py    # Subject/episode/pedal → HarmonicGrid
      types.py                 # BarAssignment, VoiceAssignment, SubjectPlan
      episode_planner.py       # Episode bar expansion + fragment iteration
  builder/
    phrase_writer.py      # shared (three-way dispatch already works)
    cadence_writer.py     # shared
    thematic_renderer.py  # shared (renders subject/answer/CS/episode)
    compose.py            # shared
```

The galant files stay where they are. Later, if desired,
`schematic.py` and `metric/` can move into a `galant/` subfolder
for symmetry, but that's cosmetic and not blocking.

---

## Implementation Phases

### Phase 1: Infrastructure
- Add `composition_model` field to GenreConfig
- Create `planner/imitative/` folder with types.py
- Add branch in planner.py (imitative path returns empty plans initially)
- Invention YAML: `composition_model: imitative`
- All galant genres unaffected

### Phase 2: Subject Planner
- `subject_planner.py`: parse extended entry_sequence → SubjectPlan
- Bar count derived from entries
- Key areas from entry keys
- Validate: every bar assigned, no gaps, no overlaps

### Phase 3: Entry Layout + Harmonic Projection
- `entry_layout.py`: SubjectPlan → PhrasePlans
- One PhrasePlan per entry/episode/cadence
- thematic_roles populated from SubjectPlan directly
- is_cadential set from function == "cadence"
- `harmony_projection.py`: subject_harmony → HarmonicGrid per phrase
- Subject entries project subject_harmony in local key
- Episodes project sequential harmony from pattern type
- Pedals project single chord
- HarmonicGrid passed to Viterbi for companion voices
- Requires: `subject_harmony` annotation in fugue/subject definition

### Phase 4: Episode Auto-Insertion
- Subject planner detects section boundaries in entry_sequence
- At each boundary, measures key distance (tonic-to-tonic)
- Inserts episode BarAssignments: length from distance, direction
  from key relationship, lead voice opposite preceding entry's lead
- Exposition exemption: subject→answer transition within exposition
  is not an episode trigger (the tonal answer handles it)
- Fragment extraction from fugue (head, tail — already exists in
  `motifs/fragment_catalogue.py`)
- Sequential transposition through intermediate scale degrees
- Companion voice: FREE for Viterbi or second fragment

### Phase 5: Extended Entry Types
- Stretto with delay
- Pedal point (held bass, free upper voice)
- Double episodes

### Phase 5b: Texture and Pairing Variety
- Implement pairing modes: parallel_10ths, contrary_motion, invertible
- Implement texture modes: bariolage_single, compound_melody
- Thematic renderer dispatches on pairing/texture fields
- Update entry_sequence YAML with varied textures across entries
- Later entries should differ from earlier ones in at least one dimension

### Phase 6: Cadence Reform
- Expand cadence templates to 2 bars (must-do, already in todo.md)
- Benefits both galant and imitative paths

### Phase 7: Listening Gate
- Generate invention from new path
- Maurice listens
- Iterate

---

## What Dies

When the imitative path is working:

- `planner/thematic.py` — the overlay planner. Its ThematicRole enum
  and BeatRole dataclass move to `planner/imitative/types.py`. The
  `plan_thematic_roles()` function and `_place_entry_sequence()` are
  deleted — the subject_planner replaces them entirely.
- The `thematic_roles` overlay concept — no more stamping roles onto
  schema-derived plans. The roles ARE the plan.
- `builder/phrase_planner.py` changes — imitative PhrasePlans are
  built by entry_layout.py, not by build_phrase_plans().
- Schema references in invention.yaml — `schema_sequence` lists in
  sections are removed. The entry_sequence is the form.

What survives:
- `builder/thematic_renderer.py` — renders subject/answer/CS/episode
  notes. This is the right tool; it was just being fed bad plans.
- `builder/cadence_writer.py` — shared.
- `motifs/fragment_catalogue.py` — episode fragments.
- `motifs/fugue_loader.py` — subject/answer data.
- The Viterbi solver — fills companion voices in episodes and free
  passages. This is its proper role: counterpoint against given
  material, not wallpaper over empty bars.

---

## Success Criteria

An invention generated via the imitative path should:

1. **Sound like an invention** — subject entries audible, episodes
   derived from subject, cadences punctuate sections
2. **Have no Viterbi wallpaper** — every bar contains either thematic
   material, episode fragments, pedal, or cadence. The only Viterbi
   is companion-voice counterpoint against real material
3. **Maintain voice continuity** — no abrupt register shifts between
   entries, exit pitch threads to next entry
4. **Rhythmic independence** — subject and CS should not move in
   lockstep (the parallel_rhythm fault from current output)
5. **Directed episodes** — listener hears the subject fragment
   stepping through a key sequence, not random fill
6. **Proper cadences** — 2-bar preparation + resolution, not 1-beat
   recitative closures

Maurice's ear is the final judge. Bob's score-reading is the proxy.
