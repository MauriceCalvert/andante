# Andante Architecture

## Purpose

Andante is a baroque music composition system with a symmetric Planner/Executor architecture. The **Planner** transforms intent into a structured YAML specification. The **Executor** transforms that specification into playable notes. YAML is the contract between them.

The Planner decides *what* to compose (form, material, structure, treatments). The Executor decides *how* to realise it (pitches, durations, voice leading). Neither leaks into the other's domain.

---

## Pipeline Overview

```
PLANNER                           EXECUTOR
───────                           ────────
P1 Frame       → Frame
P2 Dramaturgy  → RhetoricalStructure, TensionCurve
P3 Material    → Material (subject, counter_subject)
P4 Structure   → Structure (sections, episodes, phrases)
P5 Harmony     → HarmonicPlan (key scheme, cadences)
P6 Devices     → Figurenlehre assignment
P7 Coherence   → CoherencePlan (callbacks, surprises)
        ↓
      YAML ─────────────────────→ E1 Parse    → PieceAST
                                  E2 Texture  → VoiceArrangement
                                  E3 Expand   → ExpandedPhrase
                                  E4 Realise  → RealisedPhrase
                                  E5 Format   → Note → .midi/.musicxml
```

Each layer boundary is a frozen dataclass. You can enter at any layer if you have the right type. You can exit at any layer for inspection.

### Planner Stages (P1-P7)

| Stage | Input | Output | Concern |
|-------|-------|--------|---------|
| P1 Frame | Brief | Frame | key, mode, metre, tempo, voices, form |
| P2 Dramaturgy | Brief, Frame | RhetoricalStructure, TensionCurve | archetype, rhetoric, tension |
| P3 Material | Brief, Frame | Material | subject generation/loading, counter-subject |
| P4 Structure | Brief, Frame, arc | Structure | sections, episodes, phrases |
| P5 Harmony | Structure | HarmonicPlan | key scheme, cadence targets |
| P6 Devices | Structure, Material | (assignments) | Figurenlehre device placement |
| P7 Coherence | all | CoherencePlan | callbacks, surprises, proportions |

### Executor Layers (E1-E5)

| Layer | Input | Output | Concern |
|-------|-------|--------|---------|
| E1 Parse | YAML | PieceAST | syntax, structural validation |
| E2 Texture | PieceAST | VoiceArrangement | voice roles, timing relationships |
| E3 Expand | VoiceArrangement | ExpandedPhrase | phrases → bar-level pitches |
| E4 Realise | ExpandedPhrase | RealisedPhrase | degrees → MIDI pitches |
| E5 Format | RealisedPhrase | Note | track/bar/beat → MIDI/MusicXML |

---

## Layered Architecture (Ports & Adapters)

Andante follows the Ports and Adapters pattern (hexagonal architecture) to separate business logic from external systems.

### Layer Structure

```
domain/         ← pure logic, no I/O, no external dependencies
ports/          ← interfaces (Protocol classes)
adapters/       ← implementations (YAML, MIDI, filesystem)
application/    ← orchestration (planner, builder)
```

### Dependency Direction

All dependencies point inward toward domain:

```
adapters → ports → application → domain
                        ↓
                     domain
```

- **Domain** depends on nothing
- **Application** depends on domain only
- **Ports** define interfaces domain needs
- **Adapters** implement ports for specific technologies

### Ports (Interfaces)

```python
class MidiWriter(Protocol):
    def write(self, notes: Sequence[Note], path: Path) -> None: ...

class YamlLoader(Protocol):
    def load(self, path: Path) -> dict: ...

class SubjectRepository(Protocol):
    def get(self, name: str) -> Subject: ...
```

### Adapters (Implementations)

```python
class MidoMidiWriter:
    """MIDI output using mido library."""
    def write(self, notes: Sequence[Note], path: Path) -> None:
        # mido-specific implementation

class PyYamlLoader:
    """YAML loading using PyYAML."""
    def load(self, path: Path) -> dict:
        # pyyaml-specific implementation
```

### Benefits

- **Testability** — inject mock adapters for unit tests
- **Swappability** — change MIDI library without touching domain
- **Isolation** — external dependencies confined to adapters
- **Clear boundaries** — explicit contracts between layers

---

## Structural Hierarchy

```
PIECE                           One complete composition
  │
  ├── BRIEF ──────────────────  User intent: affect, genre, forces, bars
  │
  ├── FRAME ──────────────────  Derived constants: key, mode, metre, tempo
  │
  ├── MATERIAL ───────────────  Thematic content
  │     ├── subject             Primary motif (degrees + durations)
  │     └── counter_subject     Secondary motif (optional)
  │
  └── STRUCTURE ──────────────  Formal organisation
        │
        └── SECTION ──────────  Major formal division (A, B, C...)
              │                 Has: label, tonal_path, final_cadence
              │
              └── EPISODE ────  Dramatic function (statement, turbulent, cadential...)
                    │           Has: type, bars, texture
                    │
                    └── PHRASE   Musical unit within episode
                          │      Has: bars, treatment, texture, cadence, energy
                          │
                          └── BAR    Metric unit
                                │
                                └── NOTE   Concrete pitch + duration + articulation
```

### Containment Rules

| Container | Contains | Constraint |
|-----------|----------|------------|
| Piece | 1 Structure | exactly one |
| Structure | 1+ Sections | non-empty, ordered |
| Section | 1+ Episodes | non-empty, ordered |
| Episode | 1+ Phrases | non-empty, ordered |
| Phrase | N Bars | derived from phrase.bars |
| Bar | N Notes | generated by executor |

---

## Types

### Value Objects over Primitives

Use domain types instead of raw primitives:

```python
# Instead of
def transpose(pitch: int, interval: int) -> int

# Use
def transpose(pitch: Pitch, interval: Interval) -> Pitch
```

Benefits:
- Catches type errors at boundaries
- Self-documenting code
- Impossible to confuse MIDI pitch with scale degree

### Brief (user input)

| Field | Type | Constraint |
|-------|------|------------|
| affect | str | see vocabulary/affects |
| genre | str | see vocabulary/genres |
| forces | str | see vocabulary/forces |
| bars | POS_INT | target, not constraint |

### Frame (derived from Brief)

| Field | Type | Constraint |
|-------|------|------------|
| key | str | see vocabulary/keys |
| mode | str | see vocabulary/modes |
| metre | str | see vocabulary/metres |
| tempo | str | see vocabulary/tempi |
| voices | POS_INT | |

### Material

| Field | Type | Constraint |
|-------|------|------------|
| subject | Motif | required |
| counter_subject | Motif | optional |

### Motif

| Field | Type | Constraint |
|-------|------|------------|
| degrees | [DEGREE] | see vocabulary/degrees |
| durations | [Fraction] | each > 0 |
| bars | POS_INT | |

### Section

| Field | Type | Constraint |
|-------|------|------------|
| label | str | unique within structure |
| tonal_path | [str] | see vocabulary/roman |
| final_cadence | str | see vocabulary/cadences |
| episodes | [Episode] | non-empty |

### Episode

| Field | Type | Constraint |
|-------|------|------------|
| type | str | see vocabulary/episodes |
| bars | POS_INT | |
| texture | str | polyphonic, homophonic, interleaved, etc. |
| phrases | [Phrase] | non-empty |
| is_transition | bool | |

### Phrase

| Field | Type | Constraint |
|-------|------|------------|
| index | NAT | global, 0-based |
| bars | POS_INT | |
| tonal_target | str | see vocabulary/roman |
| cadence | str? | see vocabulary/cadences |
| treatment | str | see vocabulary/treatments |
| texture | str | see vocabulary/textures |
| surprise | str? | see vocabulary/surprises |
| is_climax | bool | |
| energy | str? | low, moderate, high, climactic |
| harmony | [str]? | one Roman numeral per bar |

### Pitch Types

Three pitch representations, used at different pipeline stages:

```python
@dataclass(frozen=True)
class FloatingNote:
    """Scale degree without octave. Realiser chooses placement."""
    degree: int  # 1-7

@dataclass(frozen=True)
class MidiPitch:
    """Concrete MIDI pitch. Bypasses octave selection."""
    value: int  # 0-127

@dataclass(frozen=True)
class Rest:
    """Silence marker."""
    pass
```

| Type | Octave | Use Case |
|------|--------|----------|
| FloatingNote | Realiser chooses | Motifs, outer voice expansion |
| MidiPitch | Direct MIDI value | Inner voices, post-resolution |
| Rest | N/A | Silence marker |

Type alias: `Pitch = FloatingNote | MidiPitch | Rest`

### RealisedNote (output)

```python
@dataclass(frozen=True)
class RealisedNote:
    midi: int          # MIDI pitch (0-127)
    offset: Fraction   # Start time in semibreves from piece start
    duration: Fraction # Length in semibreves
    voice: str         # "soprano", "alto", "tenor", "bass"
```

---

## Three-Way Split: Source × Treatment × Texture

The executor separates three orthogonal concerns:

| Layer | Question | Examples |
|-------|----------|----------|
| **Source** | Where does raw material come from? | subject, schema, figures |
| **Treatment** | How is material transformed? | invert, fragment, augment |
| **Texture** | How do voices relate? | polyphonic, canon, hocket |

This enables clean combination:
```yaml
- {treatment: inversion, texture: interleaved}   # inverted subject, Goldberg-style voicing
- {treatment: fragmentation, texture: canon}     # head motif in canon
- {source: schema, texture: stratified}          # figured bass realisation
```

### Treatment (What Notes?)

Melodic transformations applied to source material:

| Treatment | Effect |
|-----------|--------|
| statement | Material unchanged |
| inversion | Flip intervals around first note |
| retrograde | Reverse order |
| fragmentation | Head or tail portion |
| augmentation | Double durations |
| diminution | Halve durations |
| sequence | Repeat at different pitch level |

### Texture (How Do Voices Interact?)

Voice relationships across time and pitch:

| Texture | Time Relation | Pitch Relation | Use |
|---------|---------------|----------------|-----|
| polyphonic | independent | independent | Standard counterpoint |
| homophonic | synchronized | harmonic | Chordal passages |
| interleaved | offset | independent | Goldberg-style |
| canon | offset | transposed | Imitative entries |
| hocket | interlocking | independent | Rhythmic alternation |
| stratified | independent | independent | Melody + accompaniment |

### Voice Roles

Textures assign abstract roles that map to concrete voices:

| Role | Typical Behaviour |
|------|-------------------|
| leader | Primary melodic voice |
| follower | Derives from leader |
| dux | Canon leader (states theme first) |
| comes | Canon follower (imitates dux) |
| accompaniment | Harmonic support |
| pedal | Sustained reference pitch |
| filler | Completes harmonic texture |

---

## Six Primitives

The executor uses six orthogonal primitives to transform abstract material into concrete notes:

| Primitive | Purpose | Layer |
|-----------|---------|-------|
| **transform** | Alter motif (invert, retrograde, shift, fragment) | E3 |
| **sequence** | Create/break repetition | E3 |
| **embellish** | Add ornamental notes to skeleton | E4 |
| **shape** | Ensure interval mix (leaps vs steps) | E4 |
| **voice** | Enforce voice relationships (filter only) | E4 |
| **articulate** | Adjust timing/duration | E4 |

E3 primitives operate on abstract degrees. E4 primitives operate on concrete MIDI pitches.

---

## Guards & Backtracking

### Guard System

Guards enforce rules from lessons.yaml at multiple levels:

```yaml
piece:
  guards: [tex_004, tex_011]  # universal — apply to all phrases

sections:
  A:
    guards: [form_001]        # section-level
    phrase_1:
      soprano:
        guards: [tex_009]     # voice-level
      phrase_guards: [mech_001]  # phrase-level
```

### Guard Scopes

| Scope | When Checked |
|-------|--------------|
| note | Every note (rare, expensive) |
| bar | After each bar realised |
| phrase | After both voices for phrase |
| section | After all phrases in section |
| piece | Once at end |

Voice checks (parallel fifths, etc.) run at **phrase end**, not continuously.

### Validation Modes

| Mode | blocker | major | minor |
|------|---------|-------|-------|
| debug | log | log | log |
| warn | fail | log | log |
| strict | fail | fail | fail |

### Backtracking

Seed-based backtracking on guard failure:

```python
seed: int = 0
for phrase in all_phrases:
    while True:
        exp = expand_phrase(..., seed)
        violations = check_candidate_guards(exp, key, offset)
        if len(violations) == 0:
            break
        seed += 1
    accept_candidate(exp)
    seed += 1
```

Backtracking scope is **per-phrase**. If a phrase fails after exhausting choices, it's a spec error.

---

## Voice Configuration

### Voice Roles

```python
class VoiceRole(Enum):
    MELODIC = "melodic"      # Full counterpoint rules
    HARMONIC = "harmonic"    # Relaxed parallel rules with other harmonic
    CONTINUO = "continuo"    # Bass-line rules, check only against melodic
    FILL = "fill"            # Inner voice padding, most relaxed

@dataclass(frozen=True)
class VoiceConfig:
    index: int              # 0 = highest, N-1 = lowest (score order)
    role: VoiceRole
    range_low: int          # MIDI floor
    range_high: int         # MIDI ceiling
    median: int             # Default center pitch
    name: str               # "soprano", "alto", "tenor", "bass"
```

### Role-Based Constraint Relaxation

| Role | Parallels with Same | Parallels with Melodic | Spacing Rules |
|------|---------------------|------------------------|---------------|
| MELODIC | Forbidden | Forbidden | Strict |
| HARMONIC | Allowed | Forbidden | Normal |
| CONTINUO | N/A | Forbidden | Relaxed |
| FILL | Allowed | Allowed (weak beat) | Relaxed |

---

## Error Handling

### Explicit Error Types

Use domain-specific exceptions, not bare `assert` or generic `ValueError`:

```python
class AndanteError(Exception):
    """Base for all Andante errors."""
    pass

class HarmonyError(AndanteError):
    """Harmonic rule violation."""
    pass

class VoiceLeadingError(HarmonyError):
    """Voice leading constraint violated."""
    pass

class ValidationError(AndanteError):
    """Input validation failed."""
    pass
```

### Fail Fast at Boundaries

Validate all external input immediately on entry:

```python
def load_subject(path: Path) -> Subject:
    """Load and validate subject from YAML."""
    data = yaml.safe_load(path.read_text())
    # Validate immediately
    if 'degrees' not in data and 'pitches' not in data:
        raise ValidationError(f"Subject missing degrees/pitches: {path}")
    if 'durations' not in data:
        raise ValidationError(f"Subject missing durations: {path}")
    # Domain code assumes valid data from here
    return Subject.from_dict(data)
```

Domain code should never encounter invalid data — all validation happens at adapter boundaries.

---

## Current Status

### Two-Voice Path (Complete)

The 2-voice path is mature with extensive musical intelligence:

| Feature | Implementation |
|---------|----------------|
| Schemas | romanesca, fonte, monte, prinner, rule_of_octave |
| Pedal points | tonic pedal, dominant pedal |
| Rhythms | straight, dotted, lombardic, running |
| Cadences | half, authentic, deceptive with proper approach |
| Surprises | evaded_cadence, early_return |
| Ornaments | trill, mordent, turn (sparse) |
| Devices | stretto, augmentation, diminution |

### N-Voice Extension (Complete)

Unified constraint-satisfaction approach for any texture:

| Component | Purpose | Status |
|-----------|---------|--------|
| VoiceConfig, VoiceSet | Voice role definitions | ✓ |
| VerticalSlice, SliceSequence | Alignment model | ✓ |
| CP-SAT solver | Primary inner voice resolution | ✓ |
| Branch-and-bound fallback | When CP-SAT times out | ✓ |
| Harmonic context inference | Chord tones from outer voices | ✓ |

---

## Principles

### Core Design

1. **Single source of truth** — Each fact defined in exactly one place
2. **One way to do things** — No alternative mechanisms for same outcome
3. **Simplify whenever possible** — Remove redundancy; prefer fewer concepts
4. **Separation of concerns** — Planner decides *what*, Executor decides *how*
5. **Data-driven** — Musical knowledge in YAML; code is generic
6. **Symbolic** — No magic numbers; values resolved via lookup

### Types & Data

7. **Immutability** — Use `frozen=True` dataclasses; return `tuple` not `list`
8. **Value objects over primitives** — `Pitch` not `int`, `Interval` not `int`
9. **Fractions for music, integers for counts** — Durations are `Fraction`; counts use `int`
10. **Pitch type enforced** — Scale degrees use `Pitch`, never raw `int`
11. **No magic strings** — Use `Enum` for fixed vocabularies

### Code Organisation

12. **Dependency direction** — All dependencies point inward toward domain
13. **Ports and adapters** — Interfaces in ports/, implementations in adapters/
14. **Avoid circular imports** — Extract shared types if A imports B and B imports A
15. **One class per file** — Methods sorted alphabetically
16. **Fail fast at boundaries** — Validate external input on entry; domain assumes valid

### Naming & Style

17. **Consistent naming** — `_private`, `CONSTANT`, `verb_noun` for functions
18. **Logging over print** — Use `logging` module; can filter by level/module
19. **Docstrings where interface matters** — Essential for ports; skip obvious privates

### Testing & Development

20. **Tests next to code** — `bass.py` and `bass_test.py` in same directory
21. **Small commits, often** — One logical change per commit
22. **Vocabulary enforced** — Every term defined in vocabulary.md
23. **Document consistency** — All docs must remain consistent
24. **No downstream fixes** — 'Fix' indicates upstream design failure

### Expandability

25. **Minimal** — Two choices at each decision point during development
26. **Expandable** — New affects, genres, arcs added via data, not code
27. **Factory functions for construction** — Keep `__init__` simple; validation in `from_yaml`

---

## Related Documents

| Document | Purpose |
|----------|---------|
| structuring_strategy.md | Code organisation, size limits, naming conventions |
| test_strategy.md | Testing approach, module categories, coverage |
| vocabulary.md | Normative keyword/value definitions |
| grammar.md | Formal BNF grammar, constraints |
| lessons.md | Coding rules, design rules, anti-patterns |

---

*Document version: 5.0*
*Last updated: 2026-01-18*
