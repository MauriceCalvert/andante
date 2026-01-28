# Andante Architecture

## Status

v1.7.0 | 100% Deterministic Specification (2-voice Invention, C Major, Confident)

---

## Related Documents

- **voices.md**: Voice and instrument entity model (canonical)
- **figuration.md**: Layer 6.5 figuration system
- **laws.md**: Normative coding rules

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
- Uses a specific mechanism (lookup, enumeration, or solver)

| Layer | Input | Output | Mechanism |
|-------|-------|--------|-----------|
| 1. Rhetorical | Genre | Trajectory + rhythm vocab + tempo | Fixed per genre |
| 2. Tonal | Affect | Tonal plan + density + modality | Lookup (expandable) |
| 3. Schematic | Tonal plan | Schema chain | Enumerate from rules |
| 4. Metric | Schema chain | Bar assignments + anchors | Enumerate from rules |
| 5. Textural | Genre + sections | Treatment assignments (voice roles per bar) | Lookup by convention |
| 6. Rhythmic | Anchors + treatments + density | Active slots + durations per voice | Rule-based activation |
| 6.5 Figuration | Anchors + texture roles | Pitch sequences from patterns | Selection + chaining |
| 7. Melodic | *(orphaned)* | *(was: pitches via solver)* | *(kept for future)* |

After L6.5: **counterpoint.py** validates pitch sequences. **Realisation** assembles final notes.

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

### Layer 5: Textural

**Input:** Genre + form config (sections with bar ranges)

**Output:** Treatment assignments (voice roles per bar range)

**Mechanism:** Lookup by genre convention

Textural planning determines which voice carries the thematic material (subject) at each point in the piece. This must happen before rhythm and pitch generation because:

1. The subject voice needs dense rhythmic activity (semiquaver runs)
2. The accompaniment voice needs sparse rhythmic activity (longer values)
3. Voice roles swap at structural boundaries (S → A handoff)

**Output type:**

```python
@dataclass(frozen=True)
class TreatmentAssignment:
    start_bar: int
    end_bar: int
    treatment: str  # "subject", "answer", "episode", "cadential"
    subject_voice: int | None  # 0=soprano, 1=bass, None=both
```

**Treatment assignments for invention:**

| Treatment | Bars | Subject voice | Accompaniment |
|-----------|------|---------------|---------------|
| S (Subject) | 1–2 | 0 (soprano) | bass sparse |
| A (Answer) | 3–4 | 1 (bass) | soprano countersubject |
| episode₁ | 5–8 | None (both moderate) | — |
| development | 9–12 | None | — |
| S' (Return) | 13–16 | 0 (soprano) | bass sparse |
| coda | 17–20 | None (cadential) | — |

**Genre conventions:**

| Genre | Treatment sequence |
|-------|-------------------|
| Invention | S → A → episode₁ → S'/A' → episode₂ → S'' → coda |
| Fugue | exposition → episodes → entries → stretto |
| Minuet | N/A (melody/bass, no imitation) |
| Gavotte | N/A (same) |

For imitative genres, treatment sequence is fixed by convention. For homophonic genres, soprano always carries melody (subject_voice=0 throughout).

### Layer 6: Rhythmic

**Input:** Anchors (from L4) + treatment assignments (from L5) + density (from L2) + metre

**Output:** RhythmPlan (active slots and durations per voice)

**Mechanism:** Rule-based slot activation

Rhythmic planning determines which slots are active for each voice and what duration each note should have. This creates voice independence: when soprano runs in semiquavers, bass holds longer values.

**Output type:**

```python
@dataclass(frozen=True)
class RhythmPlan:
    soprano_active: frozenset[int]  # slot indices (0 to total_slots-1)
    bass_active: frozenset[int]
    soprano_durations: dict[int, Fraction]  # slot index -> duration
    bass_durations: dict[int, Fraction]
```

**Activation rules:**

| Slot type | Subject voice | Accompaniment voice |
|-----------|---------------|---------------------|
| Anchor | Active, 1/8 duration | Active, 1/8 duration |
| Strong beat (1, 3) | Active, 1/16 | Active, 1/8 |
| Weak beat | Active, 1/16 (high density) | Inactive |
| Weak beat | Active, 1/16 (medium density) | Active, 1/8 (50% chance) |

**Density mapping:**

| Density | Subject voice slots | Accompaniment voice slots |
|---------|--------------------|--------------------------|
| high | 75% active (12/16 per bar) | 25% active (4/16 per bar) |
| medium | 50% active (8/16 per bar) | 50% active (8/16 per bar) |
| sparse | 25% active (4/16 per bar) | 25% active (4/16 per bar) |

**Episode handling:**

When subject_voice=None (episodes, cadential sections), both voices use medium density with complementary rhythms — when one voice is active, the other tends to hold.

**Cadential lengthening:**

In the final 2 bars, durations increase: anchors get 1/4, other active slots get 1/8.

### Layer 6.5: Figuration

**Input:** Anchors (from L4) + texture roles (from L5)

**Output:** Pitch sequences for soprano and bass

**Mechanism:** Pattern selection + chaining

Figuration replaces the CP-SAT solver's arbitrary pitch selection with authentic baroque patterns from Quantz and CPE Bach treatises.

**Pattern sources by voice role:**

| Voice | Role | Pattern source |
|-------|------|----------------|
| Soprano | always | `figurations.yaml` via profile |
| Bass | thematic/leader | `figurations.yaml` via profile |
| Bass | accompaniment | `accompaniments.yaml` |

**Gap filling model:**

Anchor spacing is integer beats (2 in 4/4, 3 in 3/4). Patterns are shorter (1-1.5 beats). Gaps decompose into chained patterns:

```
[hold A (leftover)] → [ornament on A] → [diminution to B] → [anchor B]
```

**Selection process:**

1. Calculate gap duration (anchor_B - anchor_A)
2. Select diminution arriving at B (filter: duration ≤ gap)
3. Select ornament on A (filter: duration ≤ remaining)
4. Leftover time: hold anchor A pitch

**Filter order:**

1. Direction (ascending/descending/static)
2. Approach (step_above, step_below, etc.)
3. Duration (pattern fits gap)
4. Metric (strong/weak/across)
5. Energy (low/medium/high)
6. Function (ornament/diminution/cadential)

**Cadential detection:**

Use `cadential` pattern list when:
- Schema has `cadence_approach: true`
- AND connection is final (stage N-1 to stage N)

**Validation:**

After figuration produces pitch sequences, `counterpoint.validate_passage()` checks:
- Parallel fifths/octaves/unisons
- Strong-beat consonance
- Pitch-class membership
- Voice range

If violations: reject pattern, try next candidate. If all fail: fall back to hold.

See `figuration.md` for full specification.

### Layer 7: Melodic (Orphaned)

**Status:** This layer is orphaned — code remains but is not called. Figuration (L6.5) now provides pitch sequences.

**Kept for:** Potential future use as fallback or for genres where figuration doesn't apply.

**Original design (reference only):**

**Input:** Anchors (from L4) + RhythmPlan (from L6)

**Output:** Pitches for active slots per voice

**Mechanism:** Greedy solver with look-ahead

The Thematic layer generates pitches only for the slots marked active by the RhythmPlan. Each voice is filled independently, respecting its own active slot set.

**Greedy solver algorithm:**

For each active slot in order:
1. Find domain (pitches in key within tessitura)
2. Score each candidate by:
   - Motion cost (step preferred over leap)
   - Direction toward next anchor (look-ahead)
   - Distance from tessitura median
   - Oscillation penalty (A-B-A patterns)
3. Select lowest-cost pitch
4. Check for parallel 5ths/8ves with other voice

**Anchors as constraints:**

Anchors (from L4) are pre-placed pitches at schema arrival points. The solver does not choose pitches for anchor slots - it fills only the slots between anchors.

**Per-voice iteration:**

Unlike the old CP-SAT approach that processed all slots for all voices, the greedy solver processes each voice's active slots independently:

```python
for voice in [0, 1]:
    active_slots = rhythm_plan.get_active(voice)
    for slot in sorted(active_slots):
        if slot in anchors:
            pitches[slot, voice] = anchors[slot, voice]
        else:
            pitches[slot, voice] = find_best_pitch(slot, voice, ...)
```

**Look-ahead:**

The solver looks ahead to the next anchor in the same voice to guide pitch selection. If the next anchor is 5 slots away at MIDI 72, and current pitch is 65, the solver prefers upward motion.

**Tessitura:**

| Voice | Median | Span |
|-------|--------|------|
| Soprano | 70 (Bb4) | +/-18 semitones |
| Bass | 48 (C3) | +/-18 semitones |

Pitches outside the span are excluded from the domain. Pitches far from the median are penalised but permitted.

**Motion costs:**

| Motion | Semitones | Cost |
|--------|-----------|------|
| Repetition | 0 | 1.0 |
| Step | 1-2 | 0.1 |
| Skip | 3-4 | 0.3 |
| Leap | 5-7 | 0.6 |
| Large leap | 8+ | 1.2 |

**Boundary stitching:**

At phrase boundaries, the solver ensures smooth connection by constraining the first pitch of the new phrase to be within a step of the last pitch of the previous phrase.

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

Not a layer. The final step that turns abstract structure into notes.

### Inputs

- Schema arrivals (soprano/bass degree pairs at strong beats)
- Bar assignments (when)
- Solution pitches (from L7 Melodic)
- Durations (from L6 Rhythmic)
- Metre (strong/weak beat positions)
- Local key per schema (including chromatic alterations for sequential schemas)
- Affect (how much ornamentation)
- Texture (melody vs accompaniment)

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

1. Determine arrival beats from bar assignments and metre
2. Place schema arrivals at designated strong beats
3. Verify vertical consonance at each arrival
4. Fill weak beats with decoration (passing tones, neighbours, arpeggios)
5. If subject active: subject provides soprano decoration (still subject to all interval checks)
6. Verify no parallel 5ths/8ves across all consecutive beat pairs
7. Verify chromatic consistency throughout

**Key distinction:** Schema arrivals are hard constraints. Figuration between arrivals is free (subject to counterpoint). All hard constraints apply to both arrivals and figuration.

### Surface Rhythm

Decoration notes receive durations from the rhythmic vocabulary:

1. **Arrivals** — hold for quaver or crotchet (longer = more weight)
2. **Running passages** — use primary value (semiquaver for invention)
3. **Approach to arrival** — may use shorter values (semiquavers accelerating into arrival)
4. **Cadential points** — lengthen final arrivals (crotchet or minim)

**Rhythmic counterpoint:**

When one voice has running semiquavers, the other voice typically:
- Moves in longer values (quavers, crotchets) for contrast
- Or imitates the running figure in stretto

Both voices in continuous semiquavers is rare and creates textural climax.

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
- Mechanism types (lookup, enumerate, CP-SAT)
- Hard rules (validity is non-negotiable)
- Source hierarchy (counterpoint always floor)

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
| 2025-01-22 | v1.5.0: Expanded to 7-layer architecture. L5 Textural outputs treatment assignments (voice roles per bar). New L6 Rhythmic outputs active slots and durations per voice. L7 Melodic (was Thematic) uses greedy solver, processes only active slots. Moved Imitation/Countersubject to reference section. Solver config moved to solver_specs.md. |
| 2025-01-25 | v1.6.0: Added L6.5 Figuration layer. Replaces solver with authentic baroque patterns (Quantz/CPE Bach). Gap filling via ornament+diminution chaining. Cadential detection via final stage + cadence_approach flag. Bass uses accompaniments.yaml when role is accompaniment. L7 Melodic orphaned (kept for future). Validation via counterpoint.py. |
| 2025-01-28 | v1.7.0: Added voices.md defining canonical voice/instrument entity model. Brief now requires voices, instruments, scoring, tracks. Anchor fields renamed soprano_degree→upper_degree, bass_degree→lower_degree. Range flows from actuator, not hardcoded. Realisation order from dependency graph, not array index. MIDI track assignment explicit. |

---

*This document is normative once stabilised. All implementation must trace to this architecture.*
