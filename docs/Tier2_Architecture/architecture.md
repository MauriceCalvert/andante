# Andante Architecture

## Status

v2.0.0 | Phrase-based composition architecture

---

## Project Scope
Andante is a system to produce Baroque music scores. Anything related to performance is out-of-scope.

---

## Related Documents

- **voices.md**: Voice and instrument entity model (canonical)
- **figuration.md**: Diminution data reference (historical gap-based system superseded by phrase writer)
- **solver_specs.md**: Greedy solver reference (historical, replaced by phrase writer)
- **laws.md**: Normative coding rules
- **test_strategy.md**: Test strategy including layer contract tests

---

## Implementation Guide

This architecture is designed for ~80% YAML configuration, ~20% code. Adding new genres (minuet, gavotte) should require only YAML changes. Fugue requires minor code additions for multi-voice parallel checking.

### Directory Structure

```
andante/
├── engine/                    # Code (rarely changes)
│   ├── counterpoint.py        # Hard rules checker
│   ├── solver.py              # CP-SAT wrapper
│   ├── cost.py                # Weight evaluator
│   ├── realisation.py         # Fills decoration
│   └── io.py                  # MIDI/note output
│
├── config/                    # YAML (changes per genre)
│   ├── genres/
│   │   ├── invention.yaml     # Includes voice tessituras
│   │   ├── minuet.yaml
│   │   ├── fugue.yaml
│   │   └── gavotte.yaml
│   ├── affects/
│   │   ├── confident.yaml
│   │   ├── lyrical.yaml
│   │   └── grounded.yaml
│   └── forms/
│       ├── through_composed.yaml
│       ├── binary.yaml
│       └── fugue_exposition.yaml
│
├── shared/
│   └── key.py                 # Key class with computed pitch sets
```

Note: No keys/ directory. Keys are computed from (tonic, mode) parameters.
Note: Schema definitions live in data/schemas.yaml (authoritative source per L017).

### What is Code vs YAML

| Component | Location | Reusable? |
|-----------|----------|----------|
| Counterpoint rules (parallels, consonance) | Code | ✓ Universal |
| CP-SAT solver infrastructure | Code | ✓ Universal |
| Cost function evaluator | Code | ✓ Universal |
| MIDI/note file I/O | Code | ✓ Universal |
| Key pitch sets (diatonic, pentatonic) | Code | ✓ Computed from tonic+mode |
| Schema definitions | data/schemas.yaml | ✓ Universal |
| Tonal paths | YAML | Per-affect |
| Rhythmic profiles | YAML | Per-genre/affect |
| Proportion allocations | YAML | Per-genre |
| Voice tessituras | YAML | Per-genre |
| Form templates | YAML | Per-genre |

### YAML Examples

**genres/invention.yaml:**
```yaml
name: invention
voices: 2
form: through_composed
metre: 4/4
primary_value: 1/16
imitation: mandatory
sections:
  - name: exordium
    bars: [1, 4]
    schema_sequence: [do_re_mi, do_re_mi]  # S then A
    texture: imitative
  - name: narratio
    bars: [5, 12]
    schema_sequence: [episode, monte, monte, monte]
    texture: free
  - name: confirmatio
    bars: [13, 16]
    schema_sequence: [prinner]
    texture: schematic
  - name: peroratio
    bars: [17, 20]
    schema_sequence: [episode, cadenza_semplice]
    texture: cadential
```

**genres/minuet.yaml:**
```yaml
name: minuet
voices: 2
form: binary
metre: 3/4
primary_value: 1/4
imitation: none
sections:
  - name: A
    bars: [1, 8]
    cadence: HC_or_PAC_in_V
    repeat: true
  - name: B
    bars: [9, 16]
    cadence: PAC_in_I
    repeat: true
texture: homophonic
bass_pattern: oom-pah-pah
```

**affects/confident.yaml:**
```yaml
name: confident
density: high
articulation: detached
tempo_modifier: +5
tonal_path:
  narratio: [I, V, vi]
  confirmatio: [vi, IV, I]
answer_interval: 5
anacrusis: false
motive_weights:
  step: 0.2
  skip: 0.4
  leap: 0.8
  large_leap: 1.5
direction_limit: 4
```

**Key specification:**

Keys are specified by tonic and mode (e.g., "c_major", "g_minor"). Pitch sets are computed:

```python
# Major scale intervals from tonic
major_intervals = (0, 2, 4, 5, 7, 9, 11)
# Pentatonic subset for bridges (omits 4th and 7th degrees)
major_pentatonic = (0, 2, 4, 7, 9)

# For any key, compute pitch class sets:
pitch_class_set = {(tonic_pc + i) % 12 for i in major_intervals}
bridge_pitch_set = {(tonic_pc + i) % 12 for i in major_pentatonic}
```

No key YAML files exist. Voice tessituras are defined per genre, not per key.

### Code Interface

```python
def generate(
    genre: str,      # "invention" -> loads genres/invention.yaml
    key: str,        # "c_major" -> computes pitch sets
    affect: str,     # "confident" -> loads affects/confident.yaml
) -> NoteFile:
    config = load_configs(genre, key, affect)
    form = get_form(config.form)
    texture = get_texture(config.texture)
    
    chain = form.build_schema_chain(config)
    arrivals = config.get_arrivals()
    solution = solver.solve(
        slots=config.total_slots,
        anchors=arrivals,
        pitch_set=config.pitch_set,
        weights=config.motive_weights,
        voice_count=config.voices,
    )
    return realise(solution, texture, config)
```

### Genre Expansion Effort

| New Genre | YAML changes | Code changes |
|-----------|--------------|-------------|
| Minuet | New genre file, binary form, rhythm cells | Bass pattern generator (small) |
| Gavotte | Same as minuet + upbeat rule | None |
| 3-voice Fugue | New genre file, voice config | Multi-voice parallel checker |
| 4-voice Fugue | Same as 3-voice | None (parameterised) |
| G Major | None (computed) | None |
| A minor | None (computed) | Raised 7th logic (small) |

### Implementation Principles

1. **Parameterise voice count** — use `voices[0]`, `voices[1]`, not hardcoded soprano/bass
2. **Load all constraints from YAML** — no magic numbers in code
3. **Form as plugin** — common interface for through-composed, binary, fugue exposition
4. **Texture as strategy** — imitative, homophonic patterns as interchangeable modules
5. **Bass patterns as library** — YAML definitions, code reads and applies

---

## Core Principle

**Valid by construction.** Every layer draws from pre-validated options. No layer can make a choice that breaks a downstream layer. If no valid solution exists, abort. Fallback is forbidden.

---

## The Seven Layers

Composition proceeds through seven layers. Each layer:

- Takes input from higher layers
- Produces output for lower layers
- Uses a specific mechanism (lookup, enumeration, or phrase generation)

| Layer | Module | Input | Output |
|-------|--------|-------|--------|
| 1. Rhetorical | `planner/rhetorical.py` | GenreConfig | trajectory, rhythm_vocab, tempo |
| 2. Tonal | `planner/tonal.py` | AffectConfig | tonal_plan, density, modality |
| 3. Schematic | `planner/schematic.py` | tonal_plan, GenreConfig, FormConfig, schemas | SchemaChain (schemas, key_areas, free_passages) |
| 4. Metric | `planner/metric/layer.py` | SchemaChain, configs, tonal_plan | bar_assignments, anchors, total_bars |
| 5. Phrase Planning | `builder/phrase_planner.py` | SchemaChain, anchors, GenreConfig, schemas | tuple[PhrasePlan, ...] |
| 6. Phrase Writing | `builder/phrase_writer.py` | PhrasePlan, PhraseContext | PhraseResult (upper_notes, lower_notes) |
| 7. Composition | `builder/compose.py` | PhrasePlans, home_key, metre, tempo, upbeat | Composition (voices, notes) |

Orchestrator: `planner/planner.py` calls layers 1-4, then phrase planning + `compose_phrases()`.
After composition: `builder/faults.py` scans for counterpoint faults.

---

## Layer Details

### Layer 1: Rhetorical

**Input:** Genre (e.g., invention, minuet, fugue)

**Output:** Rhetorical trajectory + rhythmic vocabulary + tempo

**Mechanism:** Fixed per genre

For two-voice invention, exactly one trajectory:

```
Exordium → Narratio → Confirmatio → Peroratio
```

**Rhythmic vocabulary by genre:**

| Genre | Primary value | Characteristic figure | Tempo |
|-------|---------------|----------------------|-------|
| Invention | semiquaver | running scales, turns | ♩= 72–88 (Allegretto) |
| Fugue | quaver/crotchet | subject entry, stretto | ♩= 60–80 (Moderato) |
| Minuet | crotchet | 3/4 dance pulse | ♩. = 40–50 (Tempo di minuetto) |
| Gavotte | quaver | half-bar upbeat | ♩= 60–72 (Allegro moderato) |

No enumeration needed. Genre determines trajectory and rhythmic vocabulary.

### Layer 2: Tonal

**Input:** Affect (e.g., confident, lyrical, grounded)

**Output:** Tonal plan (sequence of key areas with cadence types) + rhythmic density + modality

**Mechanism:** Lookup table, expandable

**Modality flag:**

| Modality | Meaning |
|----------|--------|
| Diatonic | All pitches remain within the global key signature of the current section. Sequential schemas use global scale degrees, not local leading tones. |
| Chromatic | Local tonicisation permitted. Sequential schemas raise degree 7 of the local key (original behaviour). |

Default: Diatonic. The flag propagates to Layer 3 and Realisation.

| Affect | Narratio path | Confirmatio path |
|--------|--------------|-----------------|
| Confident, direct | I → V → vi | vi → IV → I |
| Lyrical, expressive | I → vi → V | V → vi → I |
| Grounded, sturdy | I → IV → V | V → IV → I |

**Tonal complexity:** Each key area in the path requires at least one schema to establish it and a cadential gesture to confirm it. The Confident affect traverses four distinct key areas (I → V → vi → IV → I), forcing the Schematic Layer to generate bridge schemas and intermediate cadences for each transition.

**Global pitch-class set (Modality = Diatonic):**

For C Major, the piece is restricted to:

```
S_global = {0, 2, 4, 5, 7, 9, 11}  # C, D, E, F, G, A, B
```

All pitches in both voices must belong to this set. No chromatic alterations permitted.

**Voice tessitura (per L003 - no range constraints):**

| Voice | Tessitura median | Typical span |
|-------|------------------|-------------|
| Soprano | Bb4 (70) | 9th around median |
| Bass | C3 (48) | 9th around median |

The pitch resolver uses tessitura medians as gravity centres. Pitches gravitate toward the median; no hard floor/ceiling. Extreme pitches are penalised by distance from median, not forbidden.

**Rhythmic density by affect:**

| Affect | Density | Articulation | Tempo modifier |
|--------|---------|--------------|----------------|
| Confident, direct | high | detached, crisp | +5–10 BPM |
| Lyrical, expressive | medium | legato, sustained | −5–10 BPM |
| Grounded, sturdy | medium | marcato, weighted | base tempo |

Density modifies how many notes per beat (high = subdivide primary value; medium = mix primary and longer). Tempo modifier adjusts the genre base tempo.

Currently one tonal plan per affect. Expandable to multiple options later.

### Layer 3: Schematic

**Input:** Tonal plan

**Output:** Schema chain

**Mechanism:** Enumerate all valid chains from rules

**Schema format:**

```yaml
do_re_mi:
  description: Opening gambit with stepwise soprano ascent
  soprano_degrees: [1, 2, 3]
  bass_degrees: [1, 7, 1]
  bass_alt: [1, 5, 1]  # Optional alternative harmonisation
  entry: {soprano: 1, bass: 1}
  exit: {soprano: 3, bass: 1}
  bars: [1, 2]  # [min, max]
  cadential_state: open
  position: opening
  source: "Gjerdingen Ch.6"
```

**Required fields:**

| Field | Type | Purpose |
|-------|------|--------|
| `soprano_degrees` | list[int] | Scale degrees at each stage |
| `bass_degrees` | list[int] | Scale degrees at each stage |
| `entry` | {soprano, bass} | First arrival (for connection checking) |
| `exit` | {soprano, bass} | Last arrival (for connection checking) |
| `bars` | [min, max] | Bar range |
| `position` | string | opening, riposte, continuation, pre_cadential, cadential, post_cadential |

**Optional fields:**

| Field | Type | Purpose |
|-------|------|--------|
| `bass_alt` | list[int] | Alternative bass harmonisation |
| `pedal` | string | dominant, tonic, subdominant — sustained bass |
| `chromatic` | bool | Schema has chromatic alterations (♯4, ♭7, etc.) |
| `sequential` | bool | Schema repeats in sequence (Monte, Fonte) |
| `direction` | string | ascending or descending (for sequential) |
| `segments` | list[int] | Permitted segment counts (for sequential), e.g., [2, 3, 4] |
| `description` | string | Human-readable explanation |
| `source` | string | Literature reference |

**Arrivals vs degrees:**

`soprano_degrees` and `bass_degrees` define all stages. `entry` and `exit` are derived from first and last pairs. Stage count = len(soprano_degrees).

At realisation, arrivals (strong-beat consonances) are placed at stages. Decoration between arrivals is free, subject to counterpoint.

**Rules for valid chain:**

1. Exit degrees of schema N match entry degrees of schema N+1
2. Tonal effect sequence reaches key areas in tonal plan
3. Cadential schema placed where tonal plan requires cadence
4. If no direct connection exists, a free passage bridges the gap

**Fortspinnung (spinning-out) principle:**

A rhetorical section (e.g., Narratio) may contain multiple schemas before reaching its cadential goal. This enables expansion beyond minimal 8-bar structures:

| Section | Minimal chain | Expanded chain (Fortspinnung) |
|---------|--------------|------------------------------|
| Narratio | Do-Re-Mi → Monte → Cadenza | Do-Re-Mi → Monte → Prinner → Monte → Cadenza |
| Confirmatio | Fonte → Prinner → Cadenza | Fonte → Monte → Fonte → Prinner → Cadenza |

**Segment scaling:** Sequential schemas (Monte, Fonte) may scale to 2, 3, or 4 segments to gain length. A 2-segment Monte spans ~2 bars; a 4-segment Monte spans ~4 bars. The generator selects segment count based on available duration and tonal distance to the next key area.

**Recurrence rules:**
- Sequential schemas (Monte, Fonte) may appear multiple times within a single rhetorical section
- Each recurrence must target a different key area or serve a different tonal function (e.g., Monte to V, then Monte to vi)
- Multiple sequential schemas are explicitly permitted when the tonal plan requires traversing several key areas
- No immediate repetition of identical schema (Monte → Monte forbidden; Monte → Prinner → Monte permitted)

**Sequential schemas (Monte, Fonte):**

Sequential schemas have degrees that can be interpreted two ways, controlled by the **Modality flag** from Layer 2:

| Modality | Degree interpretation | Example: Monte segment targeting G, global key C major |
|----------|----------------------|-------------------------------------------------------|
| Chromatic | Degrees relative to local key. Degree 7 = local leading tone, always raised. | Degree 7 = F♯ (leading tone of G) |
| Diatonic | Degrees mapped to global scale. Degree 7 of target = degree 4 of global key. | Degree 7 → global degree 4 = F♮ |

**Transition checking:**

- Entry/exit degrees are pitches (in whichever interpretation the Modality selects)
- A "step" in transition rules means a step in pitch (semitone or whole tone), not abstract degree distance
- Example: Do-Re-Mi exit 1/1 in C (C/C) to Monte entry 4/7 in F — bass C to E is not a step; free passage required

**Diatonic mode consequence:** The clausula cantizans approach (4→3 over 7→1) uses the global scale's degree 4 instead of a raised leading tone. The resolution is softer but avoids chromatic "strangeness."

**Clausula cantizans voice-leading:**

Monte and Fonte use clausula cantizans (singer's cadence) for each segment: soprano 4–3 over bass 7–1. This is **not** a simultaneous (4,7) vertical:

1. Bass 7 (leading tone) sounds on a weak beat or as a passing note
2. Bass resolves to 1 on the strong beat
3. Soprano 4 may overlap with bass 7 briefly, but moves to 3
4. The strong-beat arrival is **(3,1)**, which is consonant (M10 or m10)

The schema's "entry: 4/7" indicates the *approach* degrees, not a sustained dissonance. The actual metric arrival is (3,1). The vertical (4,7) = dim5/dim12 is never sustained; it passes through in voice-leading.

```
Clausula cantizans rhythm:

Beat:     2.75   3 (strong)
Soprano:  Bb     A       (4 → 3)
Bass:     E      F       (7 → 1)
Interval: dim5   M3
          |
          passing
```

**Consequence for arrival timing:** Monte/Fonte segments have ONE arrival per segment: (3,1). The approach (4,7) is decoration, not a schema arrival.

**Minimal schema set:**

| Schema | Entry (S/B) | Exit (S/B) | Arrivals | Tonal effect |
|--------|-------------|------------|----------|--------------|
| Do-Re-Mi | 1/1 | 3/1 | (1,1), (2,7), (3,1) | Stabilise |
| Prinner | 6/4 | 3/1 | (6,4), (5,3), (4,2), (3,1) | Stabilise/cadential |
| Monte | 3/1 (prev) | 3/1 (local) | (3,1) per segment | Depart |
| Fonte | 3/1 (prev) | 3/1 (local) | (3,1) per segment | Arrive |
| Cadenza semplice | 2/5 | 1/1 | (2,5), (7,5), (1,1) | Cadential |

**Segment count selection:** Sequential schemas (Monte, Fonte) have variable segment counts: [2, 3, 4]. The generator chooses based on available duration and tonal distance. More segments = more bars = greater key displacement. A 4-segment Monte spans approximately 4 bars; a 2-segment Monte spans 2 bars.

Five schemas. Expandable later.

**Schema-specific pitch-pair constraints (C Major, Confident affect):**

*Note: This table is illustrative. Arrival pitches are computed by a pitch resolver from schema degrees, key, and voice registers - not hardcoded.*

For the I → V → vi → IV → I path, example arrival pitches:

| Section | Schema | Bar.Beat | Soprano MIDI | Bass MIDI | Tonal Target |
|---------|--------|----------|--------------|-----------|-------------|
| Exordium | Do-Re-Mi (1,1) | 1.1 | 60 (C4) | 48 (C3) | I |
| Exordium | Do-Re-Mi (2,7) | 1.3 | 62 (D4) | 59 (B3) | I |
| Exordium | Do-Re-Mi (3,1) | 2.1 | 64 (E4) | 48 (C3) | I |
| Exordium | Answer (1,1) | 3.1 | 67 (G4) | 55 (G3) | V |
| Exordium | Answer (2,7) | 3.3 | 69 (A4) | 54 (F#3)* | V |
| Exordium | Answer (3,1) | 4.1 | 71 (B4) | 55 (G3) | V |
| Narratio | Monte seg 1 | 9.1 | 69 (A4) | 53 (F3) | IV |
| Narratio | Monte seg 2 | 10.1 | 71 (B4) | 55 (G3) | V |
| Narratio | Monte seg 3 | 11.1 | 72 (C5) | 57 (A3) | vi |
| Confirmatio | Prinner (6,4) | 13.1 | 69 (A4) | 53 (F3) | → I |
| Confirmatio | Prinner (5,3) | 14.1 | 67 (G4) | 52 (E3) | |
| Confirmatio | Prinner (4,2) | 15.1 | 65 (F4) | 50 (D3) | |
| Confirmatio | Prinner (3,1) | 16.1 | 64 (E4) | 48 (C3) | |
| Peroratio | Cadenza (2,5) | 19.1 | 62 (D4) | 55 (G3) | I |
| Peroratio | Cadenza (7,5) | 19.3 | 59 (B3) | 55 (G3) | I |
| Peroratio | Cadenza (1,1) | 20.1 | 60 (C4) | 48 (C3) | PAC |

*Note: Answer bar 3.3 uses F#3 (54) for tonal answer in dominant. This is the only chromatic pitch, permitted because it is local to the V tonicisation during the Answer.

These MIDI values are absolute. The solver anchors these pitches at the specified bar.beat positions.

**Transition constraints (no teleporting):**

| Boundary | Constraint |
|----------|------------|
| Last note bar N → first note bar N+1 | Interval ≤ major 3rd (4 semitones) |
| Narratio → Confirmatio (bar 12 → 13) | Leap must resolve by stepwise contrary motion |
| General | Minimise Σ|P_t - P_{t-1}| across all consecutive notes |

**Note on Monte/Fonte entries:** These schemas begin with clausula cantizans approach (4/7), but this is passing motion, not an arrival. The free passage delivers to a consonance; the schema's first sounding arrival is (3,1). For transition checking, use the *previous* schema's exit or a consonant free passage ending.

**Connection analysis:**

The minimal set prioritises theoretical coverage (opening, riposte, continuation, cadential) over connection efficiency. Checking all entry/exit pairs:

| From (exit) | To | Bass motion | Connection |
|-------------|------------|-------------|------------|
| Do-Re-Mi (3/1) | Prinner (6/4) | 1→4 | free |
| Do-Re-Mi (3/1) | Monte (3/1 local) | C→F (to local 1) | free |
| Do-Re-Mi (3/1) | Fonte (3/1 local) | C→D (to local 1) | step ✓ |
| Do-Re-Mi (3/1) | Cad.semp (2/5) | 1→5 | free |
| Prinner (3/1) | same as Do-Re-Mi | | |
| Monte (3/1) | Cad.semp (2/5) | 1→5 | free |
| Fonte (3/1) | Cad.semp (2/5) | 1→5 | free |
| Cad.semp (1/1) | Do-Re-Mi (1/1) | identity | **direct** |
| Cad.semp (1/1) | Monte (3/1 local) | G→F (step to IV:1) | step ✓ |

**Direct connections in minimal set:**
1. Cadenza semplice (exit 1/1) → Do-Re-Mi (entry 1/1) — bass identity
2. Exit on 1 → Monte/Fonte — bass steps to local 1

**Consequence:** With clausula cantizans properly understood, Monte/Fonte become easier to approach. The free passage targets the consonant arrival (3/1), not the dissonant approach (4/7). Gjerdingen's "islands" connect through their consonant endpoints.

### Layer 4: Metric

**Input:** Schema chain (each schema has min/max bars, stage count)

**Output:** Bar assignments + phrase-grouped anchors

**Mechanism:** Enumerate all valid assignments

**Constraints:**

- Total duration fits genre expectation
- Phrase boundaries at cadential schemas
- Koch proportions (4-bar phrases normative)
- Balance between sections
- Assigned beats >= schema stages (minimum 1 beat per stage)

**Minimum duration by genre:**

| Genre | Minimum bars | Typical range |
|-------|-------------|---------------|
| Invention | 20 | 20–32 |
| Fugue | 30 | 30–60 |
| Minuet | 16 | 16–24 |
| Gavotte | 16 | 16–24 |

The generator must produce a schema chain whose total bar count meets or exceeds the minimum.

**Proportion allocator (20-bar invention):**

Fixed bar allocation for Confident affect:

| Section | Bars | Schema allocation |
|---------|------|------------------|
| Exordium | 1–4 | Do-Re-Mi × 2 (S + A) |
| Episode 1 | 5–8 | Free passage (subject fragments) |
| Narratio | 9–12 | Monte (3 segments) + transition |
| Confirmatio | 13–16 | Prinner (4 stages) |
| Episode 2 | 17–18 | Free passage |
| Peroratio | 19–20 | Cadenza semplice |

**Phrase output:**

Layer 4 groups anchors by phrase (typically 2–4 bars each, aligned with section boundaries). Each phrase contains:

| Field | Type | Purpose |
|-------|------|--------|
| `section` | str | Section name (exordium, narratio, etc.) |
| `start_bar` | int | First bar of phrase |
| `end_bar` | int | Last bar of phrase |
| `anchors` | list[Anchor] | Anchors within this phrase |

This grouping enables Layer 5 to solve each phrase independently rather than the entire piece at once.

**Stretching trigger:**

| Condition | Action |
|-----------|--------|
| Schema stages < available beats | Stretch final stage |
| Available beats ≥ 2 × stages | Stretch all stages equally |
| Imitation active | Stretch to accommodate voice overlap |

**Stage count:**

A schema's stage count equals the length of its soprano_degrees array in schemas.yaml. Each stage corresponds to one arrival.

**Stage/beat mapping:**

Multi-stage schemas (e.g., Romanesca with 6 stages) require sufficient beats to accommodate all stages. If a schema has N stages and is assigned M beats, then M >= N. Stages may span multiple beats, but no stage may be shorter than 1 beat.

**Arrival timing:**

Arrivals fall on strong beats, distributed as evenly as metre permits:

1. In 4/4: strong beats are 1 and 3; beat 1 is strongest
2. In 3/4: strong beat is 1 only
3. First arrival falls on bar 1 beat 1
4. Final arrival falls on last bar beat 1 (or beat 3/4 for cadential schemas)
5. Intermediate arrivals distribute evenly across remaining strong beats

**Arrival stretching:**

A single schema stage may occupy multiple beats or full bars when the Melodic Layer provides sufficient decorative figuration:

| Condition | Stretch permitted |
|-----------|------------------|
| Running semiquaver figuration | Stage may span 2–4 beats |
| High-density figuration or imitation active | Stage may span 1–2 full bars |
| Sequence or imitation active | Stage may span 1–2 bars |
| Cadential approach | Final stage may span 2 bars |

Stretching increases total duration without adding schema stages. The arrival pitch remains constant; decoration fills the expanded duration.

**Arrival distribution examples:**

| Stages | Bars | Metre | Arrival beats |
|--------|------|-------|---------------|
| 3 | 2 | 4/4 | 1.1, 1.3, 2.1 |
| 3 | 1 | 4/4 | 1.1, 1.3, 1.4 |
| 4 | 2 | 4/4 | 1.1, 1.3, 2.1, 2.3 |
| 2 | 1 | 4/4 | 1.1, 1.3 |
| 3 | 1 | 3/4 | 1.1, 1.2, 1.3 |

### Layer 5: Phrase Planning

**Input:** SchemaChain, anchors, GenreConfig, schemas

**Output:** tuple[PhrasePlan, ...]

**Mechanism:** Deterministic conversion

The phrase planner converts anchors and genre configuration into PhrasePlans. One PhrasePlan per schema in the chain. The phrase is the unit of composition — one complete schema, not individual gaps between degrees.

**PhrasePlan type:**

```python
@dataclass(frozen=True)
class PhrasePlan:
    schema_name: str
    schema_degrees_upper: tuple[int, ...]
    schema_degrees_lower: tuple[int, ...]
    degree_placements: tuple[BeatPosition, ...]
    local_key: Key
    bar_span: int
    start_offset: Fraction
    rhythm_profile: str           # genre-specific rhythm vocabulary name
    bass_texture: str             # pillar, walking, arpeggiated
    is_cadential: bool
    prev_exit_pitch_upper: int | None
    prev_exit_pitch_lower: int | None
```

**Invariants:**

- One PhrasePlan per schema in the chain
- PhrasePlan.schema_degrees_upper matches schema definition
- PhrasePlan.schema_degrees_lower matches schema definition
- degree_placements length == number of schema degrees
- Every placement falls within the phrase's bar span
- Placements are in chronological order
- rhythm_profile exists in the genre's rhythm cell vocabulary
- is_cadential == True iff schema is cadential type
- start_offset of phrase N+1 == start_offset of phrase N + phrase N's total duration (phrases tile exactly, no gaps)
- prev_exit_pitch is None only for the first phrase

### Layer 6: Phrase Writing

**Input:** PhrasePlan, PhraseContext (exit pitches from previous phrase)

**Output:** PhraseResult (upper_notes, lower_notes)

**Mechanism:** Phrase-level generation with inline counterpoint checking

The phrase writer (`builder/phrase_writer.py`) generates complete soprano and bass phrases for each PhrasePlan. The soprano is generated first as a coherent phrase, then the bass is fitted to it — matching baroque compositional practice (cantus first, bass fitted).

**Soprano generation** checks only self-consistency (range, melodic intervals, no repeated notes across bars). Full counterpoint checks (parallels, dissonance, overlap) happen during bass generation where each bass note is validated against the completed soprano.

**Cadential schemas** (cadenza_semplice, cadenza_composta, half_cadence, comma) use a dedicated cadence writer (`builder/cadence_writer.py`) with fixed voice-leading templates rather than the phrase generation algorithm. Templates guarantee correct resolution.

**Genre-specific rhythm cells** (`builder/rhythm_cells.py`) define the rhythmic vocabulary. Each genre provides a small set of idiomatic cells. The phrase generator selects and chains these cells per bar, not a universal diminution table.

### Layer 7: Composition

**Input:** PhrasePlans, home_key, metre, tempo, upbeat

**Output:** Composition (voices, notes)

**Mechanism:** Phrase concatenation and assembly

`compose_phrases()` iterates over PhrasePlans in order. Each phrase is dispatched to `write_phrase()` (Layer 6) which produces upper and lower notes. Exit pitches thread between consecutive phrases for voice continuity.

```
for each schema:
    write_phrase() -> PhraseResult (soprano + bass)
    concatenate notes with offset
    thread exit pitches to next phrase
-> Composition
```

After assembly, `builder/faults.py` scans the complete Composition for counterpoint faults.

---

## Imitation and Countersubject

The following rules apply to imitative genres (invention, fugue). This information was previously in Layer 6 but is now reference material used by multiple layers.

**Exordium requirement (mandatory imitation):**

The Exordium must present the opening schema twice in strict imitation:

1. **S (Statement 1)** - Subject in soprano over simple bass accompaniment. The soprano realises the opening schema's soprano degrees; bass provides harmonic support without thematic material.
2. **A (Statement 2)** - Subject in bass with countersubject in soprano. The bass now realises the opening schema's soprano degrees (transposed); soprano provides a newly-composed countersubject that satisfies invertible counterpoint.

This doubles the Exordium duration (typically 4-8 bars total). The opening schema is stated twice, once per voice, before Narratio begins.

**Countersubject generation template:**

The countersubject (soprano during Answer) is generated by:

1. **Contrary motion skeleton** - when subject ascends, countersubject descends (and vice versa)
2. **Rhythmic complement** - countersubject uses longer values where subject has runs, runs where subject holds
3. **Invertible at 10th** - all intervals must remain consonant when voices swap (avoid 5ths, which become 4ths)
4. **Arrival synchronisation** - countersubject arrivals align with subject arrivals on strong beats

| Subject motion | Countersubject response |
|----------------|------------------------|
| Ascending run | Descending step or hold |
| Descending run | Ascending step or hold |
| Held note | Running decoration |
| Leap | Contrary step |

**Answer handling:**

The Answer is a textural overlay, not a separate schema in the chain:

1. While soprano continues after opening schema, bass enters with the subject transposed to V
2. The Answer occupies the same or next bars as the free passage following the opening schema
3. Answer arrivals follow the same schema degrees, transposed
4. Both voices must satisfy counterpoint constraints throughout

**Answer transposition rule:**

| Affect | Answer interval | Rationale |
|--------|----------------|----------|
| Confident | 5th above (tonal) | Strong dominant relationship |
| Lyrical | Unison/octave (real) | Gentler, no key change |
| Grounded | 4th above | Subdominant colouring |

For Confident affect, the Answer transposes the subject up a 5th.

---

## Free Passages

When no direct connection exists between two schemas (bass not identity, step, or dominant resolution), a **free passage** bridges the gap.

**Definition:** A free passage is a segment governed only by counterpoint rules, with no schema arrivals.

**Duration by function:**

| Function | Duration | Content |
|----------|----------|--------|
| Bridge | 1–4 beats | Voice-leading connection between schemas |
| Episode | 2–4 bars | Development of subject fragments, sequences, motivic play |

Episodes are extended free passages that provide structural weight between schema groups. They use subject material but are not bound to schema arrivals.

**Free passage pitch-set constraint:**

To avoid premature tonicisation, bridges use a reduced pitch set:

| Context | Pitch-set | Rationale |
|---------|-----------|----------|
| Bridge in C Major | {0, 2, 4, 7, 9} (C, D, E, G, A) | Tonic pentatonic — omits F (subdominant) and B (leading tone) to "clear the palate" |
| Episode | Full diatonic | Episodes may explore, bridges must neutralise |

**Lead-in motion rule:**

The final beat of a section must prepare the first note of the next:

| Constraint | Formula |
|------------|--------|
| Final note | P_{exit} = P_{entry} - 1 (diatonic step below) |
| Final 4 semiquavers | Directional scalar run toward entry pitch |
| Example | Exordium ends G4, Narratio begins A4 |

**Sequential breaking logic:**

At section boundaries, reset texture to prepare the ear:

| Condition | Action |
|-----------|--------|
| Previous section ended in bass (Answer) | Shift density to soprano for bridge |
| Previous section ended in soprano | Shift density to bass for bridge |

Texture swap timing:
- First half of bridge bar: previous voice maintains semiquavers
- Second half of bridge bar: other voice takes semiquavers, previous voice drops to quarters

**Exordium → Narratio transition (bars 7–9):**

| Segment | Offset | Logic | Output |
|---------|--------|-------|--------|
| Exordium exit | 7.0 | PAC in C | C4 (S) / C3 (B) |
| Bridge 1 | 7.5 | Arpeggiation | Outline I chord in semiquavers |
| Bridge 2 | 8.5 | Stepwise run | Ascend E4 → G4 (pentatonic only) |
| Narratio entry | 9.0 | Monte arrival | A4 (S) / F3 (B) |

**What applies:**

- All hard counterpoint rules (no parallel 5ths/8ves, consonance on strong beats, dissonance preparation/resolution)
- Chromatic consistency with surrounding keys

**What does not apply:**

- Schema arrival constraints (no required soprano/bass degree pairs)
- Schema-specific voice-leading patterns

**Purpose:** Voice-leading bridge between schemas. The free passage must:

1. Begin from the exit degrees of the preceding schema
2. End on the entry degrees of the following schema
3. Use stepwise or small-leap motion to connect smoothly
4. Maintain rhythmic continuity with surrounding material

**Approaching Monte/Fonte:**

Since Monte/Fonte arrivals are (3,1) — consonant — the free passage simply delivers to a consonance that voice-leads into the clausula cantizans:

1. Free passage ends on a consonant sonority
2. Bass steps to local degree 1 (the target of the clausula)
3. The clausula's 7→1 bass motion happens within the schema, as passing motion
4. Soprano 4→3 resolves simultaneously or slightly after

**Example:** Free passage into Monte segment in F major:
- Free passage ends: A4/F3 (M10, consonant)
- Monte clausula: Bb4/E3 (passing) → A4/F3 (arrival)
- The dim12 (Bb/E) lasts a semiquaver, resolves immediately

**Generation:** Free passages are generated at Realisation time using counterpoint constraints only. They are not enumerated at Layer 3; the schema chain simply marks "free passage required" between incompatible schemas.

---

## Realisation

Realisation is handled by the phrase writer (`builder/phrase_writer.py`) and cadence writer (`builder/cadence_writer.py`). These modules turn PhrasePlans into concrete notes with inline counterpoint checking.

### Hard Constraints (checked on every note)

**1. Vertical intervals on strong beats**

Only consonances permitted: P1, m3, M3, P5, m6, M6, P8, compound equivalents.

Dissonances (m2, M2, P4, tritone, m7, M7, m9) require preparation and stepwise resolution. A dissonance on a strong beat must be:
- Prepared: the dissonant note present in the previous beat
- Resolved: the dissonant note moves by step on the next beat

**2. Chromatic consistency**

When a schema specifies a raised or lowered degree, both voices must respect it:
- Passo Indietro: bass has ♯4; soprano must not sound natural 4 against it
- Monte/Fonte segments: if Modality == Chromatic, local leading tone (degree 7) is raised; soprano must not contradict
- General rule: if bass has accidental X on degree N, soprano cannot have natural N at the same time

**3. Diatonic constraint (if Modality == Diatonic)**

No pitch may fall outside the global key signature of the current section. This overrides any schema-internal chromatic alterations:
- Sequential schemas (Monte, Fonte) use global scale degrees, not local leading tones
- A realisation that would require F♯ in C major is rejected
- The constraint applies to both arrivals and figuration

This rule is checked *before* chromatic consistency — if Diatonic mode is active, there are no chromatic alterations to propagate.

**4. Parallel motion**

Consecutive perfect consonances forbidden:
- P5 → P5 (parallel fifths)
- P8 → P8 (parallel octaves)
- P1 → P1 (parallel unisons)

Checked between every pair of adjacent beats, both voices moving.

**5. Schema arrival enforcement**

At each schema arrival beat, the soprano/bass degree pair must exactly match one of the defined arrivals in the schema. The arrivals field in schemas.yaml is exhaustive — no other combinations permitted at arrival positions.

Example: Do-Re-Mi has arrivals at degrees (1,1), (2,7), (3,1). A strong beat with soprano=2, bass=1 violates this constraint.

### Process

For each PhrasePlan:

1. **Soprano generation:** Place structural tones at degree placements. Select rhythm cells from genre vocabulary. Fill melodic content between structural tones with stepwise motion. Validate self-consistency (range, intervals, D007).
2. **Bass generation:** Place structural bass tones. Select bass texture (pillar, walking, arpeggiated). Check each bass note against completed soprano using candidate filter (range, consonance, no parallels, no overlap).
3. **Cadential schemas:** Use cadence writer templates instead of generation algorithm. Fixed voice-leading guarantees correct resolution.
4. **Concatenation:** Exit pitches thread to next phrase's entry. First note placed in nearest octave to previous exit pitch.

**Key distinction:** Schema arrivals are hard constraints. Melodic content between arrivals is generated from genre-specific rhythm cells subject to counterpoint. All hard constraints apply to both arrivals and fill notes.

---

## Two Tiers of Rules

### Hard Rules (validity)

Violations abort generation:

- Parallel fifths/octaves/unisons forbidden (checked at realisation, every consecutive beat pair)
- Dissonances on strong beats must be prepared and resolved by step
- Vertical intervals on strong beats must be consonant (unless prepared dissonance)
- Schema arrivals must use defined soprano/bass degree pairs from schema definition
- Chromatic alterations from sequential schemas propagate to both voices; contradictions forbidden
- Cadence points must be reached

### Soft Rules (quality)

Violations penalised, not forbidden:

- Prefer voice tessitura (distance from median penalised per L003)
- Prefer melodic variety
- Prefer balance of steps and leaps
- Prefer rhythmic interest
- Prefer voice independence
- Prefer contrary motion

**Ranking:** Generate multiple valid solutions, rank by soft rule satisfaction, return highest-ranked.

**Success criteria:**

- **Competent** = satisfies all hard rules
- **Good** = also scores well on soft rules
- **Brilliant** = out of scope

---

## Source Hierarchy

When rules conflict or sources are silent, apply this precedence:

1. **Counterpoint (Fux)**: Always applies. Never overridden.
2. **Phrase structure (Koch)**: Where relevant.
3. **Schema (Gjerdingen)**: Where a schema is active.
4. **Genre conventions**: Where genre is specified.

More specific overrides more general. Counterpoint is the floor.

If no guidance after all sources, choice is free (counterpoint still applies).

---

## Guarantees

1. **Valid by construction** — every option in every layer is valid
2. **No fallback** — if no solution, abort with clear message
3. **No constraint relaxation** — hard rules are never weakened
4. **Traceable** — every note traces to layer decisions
5. **Deterministic** — same inputs produce same outputs (given same random seed for selection)

---

## Design Principles

1. **The phrase is the unit of composition.** One schema = one phrase. The soprano and bass are each generated as complete phrases, not assembled from independent gap fragments.

2. **Genre defines rhythmic vocabulary.** Each genre provides a small set of idiomatic rhythmic cells. The phrase generator selects and chains these cells, not a universal diminution table.

3. **Counterpoint is checked inline, not post-hoc.** Generate-and-test loops are forbidden (X002). The bass is generated with awareness of the soprano, note by note, using the existing candidate filter. The soprano is generated as a coherent phrase first.

4. **Cadences are formulaic.** Cadential schemas use hardcoded clausula voice-leading templates, not strategy lookups. The template guarantees correct resolution.

5. **Incremental migration, not big-bang rewrite.** The planner stays. The anchor system stays. The counterpoint checks stay. The builder's gap-dispatch loop is replaced by a phrase-dispatch loop.

---

## Phrase Composition Types

```
PhrasePlan:
    schema_name: str
    schema_degrees_upper: tuple[int, ...]
    schema_degrees_lower: tuple[int, ...]
    degree_placements: tuple[BeatPosition, ...]
    local_key: Key
    bar_span: int
    start_offset: Fraction
    rhythm_profile: str
    bass_texture: str
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

---

## Soprano Phrase Generation Algorithm

For one schema (e.g., do_re_mi: degrees 1->2->3, 2 bars, minuet 3/4):

1. **Place structural tones.** Map each schema degree to its bar/beat from the degree placement map. These are the fixed points the melody must hit. For do_re_mi in 3/4: degree 1 on bar 1 beat 1, degree 2 on bar 2 beat 1, degree 3 on bar 3 beat 1 (or wherever the next schema begins).

2. **Select rhythm cells.** For each bar, pick a rhythm cell from the genre vocabulary. The cell must start with a duration that covers the strong beat (where the structural tone sits). Cells are selected with variety constraints: no immediate repetition, cadence-approach bars prefer longer values.

3. **Fill melodic content.** Between structural tones, fill with stepwise motion (seconds) or occasional thirds, preferring the direction that connects to the next structural tone. Constrained by:
   - Range (actuator_range)
   - No repeated pitch across bar boundaries (D007)
   - Leaps followed by contrary step
   - Melodic intervals <= octave

4. **Validate.** Check the complete phrase for self-consistency. If invalid, retry with a different cell selection (max 3 attempts, then assert fail).

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

1. **Place structural bass tones.** Schema bass degrees on the same bar/beat positions as soprano. Place in nearest octave to previous bass exit pitch, respecting bass range.

2. **Select bass texture.** From genre config: pillar, walking, or arpeggiated.
   - **Pillar**: hold each bass degree for the full bar. One note per bar.
   - **Walking**: stepwise motion between bass degrees, one note per beat.
   - **Arpeggiated**: broken chord pattern (root-third-fifth or similar).

3. **Check each bass note against soprano.** Using the existing candidate filter: range, consonance on strong beats, no parallels, no voice overlap. If a note fails, try the nearest consonant alternative.

---

## Cadence Writer

Cadential schemas are not generated — they use fixed templates.

### cadenza_semplice (soprano 2->1, bass 5->1)

```
4/4:  soprano: [2 as minim, 1 as minim]
      bass:    [5 as minim, 1 as minim]

3/4:  soprano: [2 as dotted minim] -> [1 as dotted minim]
      bass:    [5 as crotchet, 5 as crotchet, rest] -> [1 as dotted minim]
```

### cadenza_composta (soprano 4->3->2->1, bass 5->1)

```
4/4:  soprano: [4 as crotchet, 3 as crotchet, 2 as crotchet, 1 as crotchet]
      bass:    [5 as minim, 1 as minim]

3/4:  soprano: [4 as crotchet, 3 as crotchet, 2 as crotchet] -> [1 as dotted minim]
      bass:    [5 as dotted minim] -> [1 as dotted minim]
```

### half_cadence (soprano varies, bass ->5)

```
4/4:  soprano: last 2 notes descend by step to degree above 5
      bass:    [prev as minim, 5 as minim]
```

These templates are per-metre, stored in YAML. They guarantee correct resolution because there is nothing to select or filter — the voice-leading is predetermined.

---

## Module Architecture

### Composition flow

```
planner -> anchors -> phrase_planner -> PhrasePlans -> phrase_writer
                                                          |
                                                for each schema:
                                                  generate soprano phrase
                                                  generate bass phrase
                                                  (inline counterpoint check)
                                                -> notes
```

### New modules

| Module | Responsibility |
|--------|----------------|
| `builder/phrase_planner.py` | Convert anchors + genre config -> PhrasePlans |
| `builder/phrase_writer.py` | Generate soprano + bass phrases from PhrasePlan |
| `builder/cadence_writer.py` | Hardcoded cadential voice-leading templates |
| `builder/rhythm_cells.py` | Genre-indexed rhythmic cell vocabulary |

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
| `planner/rhetorical.py` | Genre -> trajectory, rhythm, tempo |
| `planner/tonal.py` | Affect -> tonal plan |
| `planner/schematic.py` | Schema chain selection |
| `planner/metric/layer.py` | Bar assignments + anchors |
| `planner/metric/schema_anchors.py` | Schema -> anchor expansion |
| `shared/*` | All shared infrastructure |
| `builder/faults.py` | Post-composition fault scan |
| `builder/io.py` | Output writers |
| `builder/compose.py` | Simplified: phrase loop replaces gap loop |

---

## Risks and Mitigations

### Phrase boundary discontinuity

**Risk**: independently generated phrases may not join smoothly.

**Mitigation**: the phrase generator receives the previous phrase's final pitch as input. The first note of the new phrase is the schema's entry degree, placed in the nearest octave to the previous exit pitch.

### Rhythmic monotony from small cell vocabulary

**Risk**: cycling through 3-5 rhythmic cells per genre could sound mechanical.

**Mitigation**: cells are selected per bar with variation rules — odd/even alternation, cadence-approach bars use longer values, opening bars use simpler cells, recent-cell tracking avoids immediate repetition. Cell vocabulary expandable per genre without architectural change.

### Schema degrees don't always fall on beat 1

**Risk**: the "one degree per bar on beat 1" model breaks for some schemas.

**Mitigation**: each schema definition specifies its degree count and bar span. The phrase generator uses a degree placement map derived from the schema YAML, not hardcoded.

### Cadences need specific voice-leading

**Risk**: "just place the degrees" doesn't produce proper cadential motion.

**Mitigation**: cadential schemas are handled by a dedicated cadence writer with fixed templates. These are not generated — they guarantee correct resolution.

### Counterpoint checking during soprano generation

**Risk**: soprano generated first, no bass to check against.

**Mitigation**: soprano checked only for self-consistency. Full counterpoint checks happen during bass generation where each bass note is validated against the completed soprano.

### Loss of the diminution data

**Risk**: the figure catalogue represents real baroque diminution practice.

**Mitigation**: the diminution data is not discarded — it is restructured. Figures are re-indexed by genre and schema position, selected per phrase rather than per gap.

---

## Success Criteria

A piece passes if:

1. **Correct tonal ending.** Final note is tonic in both voices.
2. **Genre-appropriate rhythm.** Minuet sounds like 3/4 dance, not continuous quavers. Gavotte has graceful paired quavers. Invention has contrapuntal activity.
3. **No D007 violations.** No repeated soprano pitch across bar boundaries.
4. **Melodic coherence.** No octave leaps except deliberate registral shifts. Predominant stepwise motion with occasional thirds.
5. **Proper cadences.** Section endings have correct voice-leading (2->1 over 5->1 for authentic, soprano to 5 for half cadence).
6. **No counterpoint faults.** No parallel fifths/octaves on strong beats. No voice overlap.
7. **Phrase shape.** Each schema produces an audibly distinct phrase with beginning, middle, and end.

---

## Migration Plan

### Phase 1: Minuet end-to-end

1. Implement rhythm_cells.py with minuet vocabulary
2. Implement phrase_planner.py (anchors -> PhrasePlans)
3. Implement phrase_writer.py (soprano generation)
4. Implement bass generation within phrase_writer
5. Implement cadence_writer.py with cadenza_semplice template
6. Wire into compose.py
7. Verify: minuet ends on tonic, has 3/4 character, no D007 violations

### Phase 2: Gavotte (binary dance with upbeat)

8. Add gavotte rhythm cells
9. Handle upbeat in phrase_planner
10. Verify: correct ending, graceful character, no octave leaps

### Phase 3: Invention (counterpoint)

11. Add invention rhythm cells (continuous quavers / semiquavers)
12. Implement subject statement + tonal answer copy
13. Handle contrapuntal bass (walking texture with real independence)
14. Verify: audible imitation, active counterpoint, correct ending

### Phase 4: Cleanup

15. Remove dead strategies and figuration loader
16. Remove textural.py and old voice_planning.py
17. Update documentation
18. Run all genres, compare output quality

Each phase produces a working system.

---

## Expansion Strategy

**General rule:** Minimal viable set first. Prove architecture works with smallest possible vocabulary. Expand only after proof.

**What expands:**

| Layer | Initial | Expansion |
|-------|---------|-----------|
| Tonal plans | 3 (one per affect) | More affects, multiple plans per affect |
| Schemas | 5 | Full Gjerdingen catalogue |
| Subject constraints | Core melodic rules | Genre-specific rules |
| Genres | Invention only | Minuet, fugue, gavotte |

**What doesn't expand:**

- Layer structure (always seven layers)
- Hard rules (validity is non-negotiable)
- Source hierarchy (counterpoint always floor)
- Phrase-as-unit principle

---

## Document History

| Date | Change |
|------|--------|
| 2025-01-20 | Complete rewrite based on valid-by-construction principle |
| 2025-01-20 | Expanded Realisation section: vertical intervals, chromatic consistency, parallel motion, arrival enforcement |
| 2025-01-20 | Layer 3: sequential schema local-key degrees, pitch-based transitions. Layer 5: stage/beat constraint. Added Free Passages section |
| 2025-01-20 | Added rhythm: L1 outputs rhythmic vocabulary + tempo; L2 outputs density; L4 generates subject with durations; Realisation includes surface rhythm |
| 2025-01-20 | Fixed gaps: L5 arrival timing/distribution; L6 imitation mapping; L3 connection analysis; Cadenza semplice entry corrected to 2/5 |
| 2025-01-20 | Clausula cantizans: Monte/Fonte (4,7) is passing motion, not arrival; arrival is consonant (3,1); updated connection analysis and free passage rules |
| 2025-01-20 | Added Modality flag (Diatonic/Chromatic) to Layer 2; updated Layer 3 sequential schema interpretation; added diatonic constraint to Realisation hard rules |
| 2025-01-20 | Expansion for 20+ bars: L2 tonal complexity (3 key areas); L3 Fortspinnung principle and variable segment counts; L5 minimum duration and arrival stretching; L6 mandatory imitation and extended treatment sequence; Free passages as episodes (2–4 bars) |
| 2025-01-20 | v1.3.0: Refined tonal path (I→V→vi→IV→I); explicit segment scaling (2/3/4); arrival stretching for high-density figuration; mandatory Exordium imitation (S then A with countersubject) |
| 2025-01-20 | v1.3.1 (100% spec): Global pitch-class set; schema-specific pitch-pair constraints with bar numbers; transition constraints (no teleporting); motive weights and directional constraints; counter-decoration rules; proportion allocator; countersubject generation template |
| 2025-01-20 | Free passage formalisation: pentatonic pitch-set for bridges; lead-in motion rule (step below entry); sequential breaking logic (texture swap); Exordium→Narratio transition table |
| 2025-01-20 | Final 100% determinism: voice tessitura medians (Bb4 soprano, C3 bass); exact MIDI numbers in pitch-pair table; anacrusis rule (beat 1 start); bass rhythm specification; answer transposition rule by affect; solver determinism rules (tie-breaking, search order, no randomisation) |
| 2025-01-20 | Added Implementation Guide preface: directory structure, code vs YAML breakdown, YAML examples, code interface, genre expansion effort table, implementation principles |
| 2025-01-20 | Schema format: updated to match schemas.yaml with soprano/bass_degrees, entry/exit, bars[min,max], position, and optional fields |
| 2025-01-21 | Keys computed from (tonic, mode) - no keys/ directory; registers→tessitura (medians per L003); key comment fixed in code interface |
| 2025-01-21 | Tessitura medians corrected: soprano 70 (Bb4), bass 48 (C3) - midpoints of original ranges; previous values (64, 43) pulled pitches too low |
| 2025-01-22 | v1.4.0: Swapped Layers 4/5 (Metric now L4, Thematic now L5) for logical data flow. Removed incoherent Layer 4.5. Added phrase-level solving to L5. Moved solver config to appendix. |
| 2025-01-22 | v1.5.0: Expanded to 7-layer architecture. L5 Textural outputs treatment assignments (voice roles per bar). New L6 Rhythmic outputs active slots and durations per voice. L8 Melodic (was Thematic) uses greedy solver, processes only active slots. Moved Imitation/Countersubject to reference section. Solver config moved to solver_specs.md. |
| 2025-01-25 | v1.6.0: Added L7 Figuration layer (was L6.5). Replaces solver with authentic baroque patterns (Quantz/CPE Bach). Gap filling via ornament+diminution chaining. Cadential detection via final stage + cadence_approach flag. Bass uses accompaniments.yaml when role is accompaniment. L8 Melodic orphaned (kept for future). Validation via counterpoint.py. |
| 2025-01-28 | v1.7.0: Added voices.md defining canonical voice/instrument entity model. Brief now requires voices, instruments, scoring, tracks. Anchor fields renamed soprano_degree->upper_degree, bass_degree->lower_degree. Range flows from actuator, not hardcoded. Realisation order from dependency graph, not array index. MIDI track assignment explicit. |
| 2026-02-06 | v2.0.0: Phrase-based redesign. Replaced Layers 5-7 (Textural, Rhythmic, Figuration, Melodic) with Layer 5 Phrase Planning + Layer 6 Composition. Phrase is the unit of composition, not the gap. Genre-specific rhythm cells replace universal diminution table. Cadence writer with fixed templates replaces cadential strategy. Inline counterpoint checking. Added design principles, algorithms, module architecture, risks/mitigations, success criteria, migration plan. Integrated from redesign.md. |

---

*This document is normative once stabilised. All implementation must trace to this architecture.*
