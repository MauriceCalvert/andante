# Andante Codebase Summary

**Purpose:** Enable rapid context acquisition for new sessions. Read this first.

---

## What Is Andante?

Baroque music composition system with a 7-layer architecture:
- **Planner**: Brief → YAML plan (what to compose)
- **Builder**: YAML → MIDI/MusicXML (how to realise it)

---

## Directory Structure

```
andante/
├── builder/                # Builder: Anchors → playable notes
│   ├── figuration/         # Baroque melodic patterns (L6.5)
│   │   ├── bass.py         # Bass pattern realisation
│   │   ├── figurate.py     # Main figuration engine
│   │   ├── loader.py       # Load figures from YAML
│   │   ├── melodic_minor.py # Melodic minor handling
│   │   ├── junction.py     # Transitions between figures
│   │   ├── realiser.py     # Figures → note sequences
│   │   ├── selector.py     # Context-aware figure selection
│   │   ├── sequencer.py    # Order figures into sequences
│   │   └── types.py        # Figure, CadentialFigure, PhrasePosition
│   ├── config_loader.py    # Load YAML configs (genres, schemas, affects)
│   ├── constraints.py      # Hard constraint definitions
│   ├── costs.py            # Soft constraint cost functions
│   ├── counterpoint.py     # Two-part counterpoint rules
│   ├── faults.py           # 11+ fault categories detection
│   ├── greedy_solver.py    # Greedy solving approach
│   ├── io.py               # .note, MIDI, MusicXML output
│   ├── musicxml_writer.py  # MusicXML export
│   ├── realisation.py      # Anchors → Note objects
│   ├── slice.py            # Interval/motion analysis
│   ├── solver.py           # CP-SAT solver entry point
│   └── types.py            # Note, Anchor, Solution, etc.
│
├── planner/                # Planner: Brief → YAML plan
│   ├── metric/             # Layer 4: Metric planning
│   │   ├── layer.py        # Metric orchestration
│   │   ├── distribution.py # Bar/beat distribution
│   │   ├── schema_anchors.py # Schema anchor generation
│   │   ├── pitch.py        # Pitch calculation utilities
│   │   └── constants.py    # Metric constants
│   ├── planner.py          # 7-layer pipeline orchestrator
│   ├── plannertypes.py     # Brief, Frame, Material, Plan, etc.
│   ├── rhetorical.py       # L1: Trajectory, rhythm vocab, tempo
│   ├── tonal.py            # L2: Key areas, density, modality
│   ├── schematic.py        # L3: Schema chain generation
│   ├── textural.py         # L5: Treatment assignments
│   ├── rhythmic.py         # L6: Active slots, durations
│   ├── melodic.py          # L7: Greedy pitch solver (orphaned)
│   ├── frame.py            # Resolve key/mode/metre/tempo
│   ├── material.py         # Subject acquisition
│   ├── subject.py          # Subject with counter-subjects
│   ├── cs_generator.py     # CP-SAT counter-subject solver
│   ├── structure.py        # SectionSchema hierarchy
│   ├── harmony.py          # Key scheme, modulations, cadences
│   ├── phrase_harmony.py   # Bar-level chord progressions
│   ├── dramaturgy.py       # Rhetorical structure, tension
│   ├── coherence.py        # Callbacks, surprises, proportions
│   ├── arc.py              # Tension curve management
│   ├── schema_loader.py    # Load schema definitions
│   ├── schema_generator.py # Schema chain from cadence plan
│   ├── subject_validator.py # Validate against opening schema
│   ├── subject_deriver.py  # Derive subject from schema
│   ├── treatment_generator.py # Dynamic treatment sequences
│   ├── devices.py          # Figurenlehre assignment
│   ├── constraints.py      # Plan → constraint synthesis
│   ├── koch_rules.py       # Koch mechanical rules
│   ├── plan_validator.py   # Plan structural validation
│   ├── serializer.py       # Plan → YAML output
│   ├── motif_loader.py     # Load .note files as motifs
│   └── types.py            # Legacy alias for plannertypes
│
├── motifs/                 # Subject generation (music cognition)
│   ├── frequencies/        # Corpus analysis
│   │   └── analyse_intervals.py # Interval/tessitura distributions
│   ├── subject_generator.py # 2-bar subjects via head+tail
│   ├── head_generator.py   # Leap + gap-fill heads (3-5 notes)
│   ├── tail_generator.py   # Contrary-motion tails (43 cells)
│   ├── figurae.py          # Baroque rhetorical figures
│   ├── melodic_features.py # 40+ melody features
│   ├── enumerator.py       # Exhaustive candidate enumeration
│   └── affect_loader.py    # Load affects, score subjects
│
├── shared/                 # Cross-cutting types and utilities
│   ├── pitch.py            # FloatingNote (scale degree without octave)
│   ├── typedefs.py         # Motif and shared data structures
│   ├── key.py              # Key class with scale conversion
│   ├── voice_role.py       # TOP, BOTTOM, INNER_1, INNER_2
│   ├── timed_material.py   # Budget-first duration handling
│   ├── parallels.py        # Parallel fifth/octave detection
│   ├── dissonance.py       # Harsh interval detection
│   ├── music_math.py       # Exact fractional duration arithmetic
│   ├── constants.py        # Scales, note names, valid durations
│   ├── tracer.py           # Pipeline execution tracing
│   ├── validate.py         # Typed validation exceptions
│   ├── errors.py           # AndanteError exception hierarchy
│   ├── constraint_validator.py # Brief/Frame validation
│   ├── yaml_validator.py   # Cross-file YAML validation
│   └── midi_writer.py      # Standalone MIDI generation
│
├── data/                   # YAML configuration (all musical knowledge)
│   ├── genres/             # Genre templates
│   │   ├── _default.yaml   # Default genre settings
│   │   ├── invention.yaml
│   │   ├── chorale.yaml
│   │   ├── fantasia.yaml
│   │   ├── minuet.yaml
│   │   ├── gavotte.yaml
│   │   ├── bourree.yaml
│   │   ├── sarabande.yaml
│   │   └── trio_sonata.yaml
│   ├── rhetoric/           # Rhetorical system
│   │   ├── affects.yaml    # 8 Affektenlehre affects
│   │   ├── archetypes.yaml # 6 dramaturgical archetypes
│   │   ├── figurae.yaml    # 20+ rhetorical figures
│   │   ├── episodes.yaml   # Episode types
│   │   └── tension_curves.yaml
│   ├── schemas/            # Partimento patterns
│   │   ├── schemas.yaml    # fonte, monte, prinner, etc.
│   │   └── schema_transitions.yaml
│   ├── figuration/         # Melodic ornamentation
│   │   ├── figurations.yaml
│   │   ├── figuration_profiles.yaml
│   │   ├── accompaniments.yaml
│   │   ├── diminutions.yaml
│   │   ├── cadential.yaml
│   │   ├── rhythm_templates.yaml
│   │   └── bass_patterns.yaml
│   ├── instruments/        # Instrument definitions
│   │   ├── violin.yaml
│   │   ├── piano.yaml
│   │   ├── flute_concert.yaml
│   │   └── recorder_*.yaml # soprano, alto, tenor, bass
│   ├── rules/              # Counterpoint constraints
│   │   ├── counterpoint_rules.yaml
│   │   └── constraints.yaml
│   ├── treatments/         # Voice expansion specs
│   │   └── treatments.yaml
│   ├── cadences/           # Cadential formulas
│   │   └── cadences.yaml
│   ├── voicing/            # Texture definitions
│   │   └── textures.yaml
│   ├── forms/              # Form templates
│   │   ├── binary.yaml
│   │   ├── strophic.yaml
│   │   └── through_composed.yaml
│   ├── humanisation/       # Performance nuance
│   │   ├── metric_weights.yaml
│   │   ├── performance/    # harpsichord, piano, clavichord
│   │   └── styles/         # baroque
│   └── yaml_types.yaml     # Type registry
│
├── scripts/                # CLI entry points
│   ├── run_pipeline.py     # Full pipeline execution
│   ├── run_showcase.py     # Generate showcase piece
│   ├── note_to_subject.py  # .note → .subject YAML
│   ├── subject_to_midi.py  # .subject → MIDI
│   ├── note_to_midi.py     # .note CSV → MIDI
│   ├── midi_to_note.py     # MIDI → .note CSV
│   ├── generate_subjects.py # DEPRECATED
│   └── generate_heads.py   # DEPRECATED
│
├── briefs/                 # Test YAML brief files
├── output/                 # Generated MIDI/MusicXML
├── tests/                  # Pytest suites
├── UI/                     # User interface components
└── docs/                   # Architecture and guides
    ├── Tier1_Normative/    # laws.md, grammar.md, vocabulary.md, ontology.md
    ├── Tier2_Architecture/ # architecture.md, figuration.md, solver_specs.md
    ├── Tier3_Guides/       # summary.md, bob.md, learnings.md, composerguide.md
    ├── Tier4_Reference/    # counterpoint_rules.md, grounding.md, motif_study.md
    ├── Instruments/        # violin.md
    └── bugs.md             # Bug tracking
```

---

## Data Flow

```
Brief (affect, genre, forces, bars)
    │
╔═══════════ PLANNER (7 Layers) ════════════╗
║                                           ║
║  L1 Rhetorical → trajectory, rhythm, tempo║
║      │                                    ║
║  L2 Tonal → key areas, density, modality  ║
║      │                                    ║
║  L3 Schematic → schema chain              ║
║      │                                    ║
║  L4 Metric → bar assignments, anchors     ║
║      │                                    ║
║  L5 Textural → treatment assignments      ║
║      │                                    ║
║  L6 Rhythmic → active slots, durations    ║
║      │                                    ║
║  L6.5 Figuration → pitch sequences        ║
║      │                                    ║
║  L7 Melodic → (orphaned, kept for future) ║
║                                           ║
╚═══════════════════════════════════════════╝
    │
YAML Plan
    │
╔═══════════ BUILDER ══════════════════════╗
║                                          ║
║  config_loader → Load genres, schemas    ║
║      │                                   ║
║  solver/greedy_solver → Constraint solving║
║      │                                   ║
║  realisation → Anchors → Notes           ║
║      │                                   ║
║  figuration/ → Baroque ornaments         ║
║      │                                   ║
║  counterpoint → Rule validation          ║
║      │                                   ║
║  faults → 11+ fault detection            ║
║      │                                   ║
║  io → Format output                      ║
║                                          ║
╚══════════════════════════════════════════╝
    │
Export → .midi / .musicxml / .note
```

---

## The Seven Layers

| Layer | Input | Output | Mechanism |
|-------|-------|--------|-----------|
| 1. Rhetorical | Genre | Trajectory + rhythm vocab + tempo | Fixed per genre |
| 2. Tonal | Affect | Tonal plan + density + modality | Lookup |
| 3. Schematic | Tonal plan | Schema chain | Enumerate from rules |
| 4. Metric | Schema chain | Bar assignments + anchors | Enumerate from rules |
| 5. Textural | Genre + sections | Treatment assignments | Lookup by convention |
| 6. Rhythmic | Anchors + treatments + density | Active slots + durations | Rule-based |
| 6.5 Figuration | Anchors + texture roles | Pitch sequences | Selection + chaining |
| 7. Melodic | *(orphaned)* | *(was: pitches via solver)* | *(kept for future)* |

---

## Pitch Types (Critical!)

| Type | Octave | When Used |
|------|--------|-----------|
| `FloatingNote` | Realiser chooses | Motifs, outer voice expansion |
| `MidiPitch` | Direct MIDI value | Bypasses octave selection |
| `Rest` | N/A | Silence marker |

**Union:** `Pitch = FloatingNote | MidiPitch | Rest`

**Conversion flow:**
```
YAML degrees → FloatingNote → (realisation) → MIDI int
```

---

## Key Builder Functions

### solver.py / greedy_solver.py
- CP-SAT and greedy solving for pitch selection
- Uses constraints.py for hard rules, costs.py for soft rules

### counterpoint.py
- `is_consonant()` - Interval consonance check
- `is_perfect()` - Perfect consonance check
- `check_parallels()` - Parallel motion detection
- `check_voice_range()` - Tessitura validation

### realisation.py
- `realise_with_figuration()` - Anchors → Notes with baroque patterns
- `select_octave()` - Tessitura-centered octave placement

### faults.py
- `find_faults()` - Detect 11+ fault categories
- `print_faults()` - Human-readable fault reports
- Categories: parallel_fifth, parallel_octave, unprepared_dissonance, grotesque_leap, tessitura_excursion, voice_overlap, spacing_error, cross_relation, ugly_leap, direct_motion, consecutive_leaps

### figuration/figurate.py
- Main figuration engine for baroque melodic patterns
- Gap filling via ornament + diminution chaining

---

## Key Planner Functions

### planner.py
- `build_plan()` - 7-layer pipeline orchestrator

### cs_generator.py
- `generate_countersubject()` - CP-SAT solver with 7 constraint groups:
  - Vertical (consonance, no parallels)
  - Melodic (contrary motion, leap compensation)
  - Rhythmic (attack awareness)
  - Cadential (final note stability)
  - Motivic (duration vocabulary)
  - Invertibility (avoid inversely-dissonant intervals)
  - Climax (offset from subject peak)

### Layer modules
- `rhetorical.py` - L1: Genre → trajectory, rhythm vocab, tempo
- `tonal.py` - L2: Affect → key areas, density, modality
- `schematic.py` - L3: Tonal plan → schema chain
- `metric/layer.py` - L4: Schema chain → bar assignments, anchors
- `textural.py` - L5: Genre → treatment assignments
- `rhythmic.py` - L6: Active slots, durations per voice

---

## Module Categories

### Builder Core
```
config_loader.py   Load YAML configs (genres, schemas, affects, forms)
types.py           Note, Anchor, Solution, RhythmState, etc.
io.py              Export to .note CSV, MIDI, MusicXML
musicxml_writer.py MusicXML-specific export
```

### Builder Solver
```
solver.py          CP-SAT solver entry point
greedy_solver.py   Greedy alternative solver
constraints.py     Hard constraint definitions
costs.py           Soft constraint cost functions
counterpoint.py    Two-part rule checker
slice.py           Interval/motion analysis utilities
```

### Builder Figuration
```
figuration/figurate.py     Main figuration engine
figuration/loader.py       Load figures from YAML
figuration/realiser.py     Figures → note sequences
figuration/selector.py     Context-aware figure selection
figuration/sequencer.py    Order figures into coherent sequences
figuration/bass.py         Bass pattern realisation
figuration/melodic_minor.py Melodic minor handling
figuration/junction.py     Figure transitions
figuration/types.py        Figure, CadentialFigure, PhrasePosition
```

### Builder Quality
```
realisation.py     Anchors → Note objects
faults.py          11+ fault category detection
```

### Planner Core
```
planner.py         Brief → Plan orchestrator (7 layers)
plannertypes.py    Brief, Frame, Material, Structure, Plan
frame.py           Resolve key/mode/metre/tempo
serializer.py      Plan → YAML with Fraction formatting
plan_validator.py  Plan structural integrity checks
```

### Planner Layers
```
rhetorical.py      L1: Trajectory, rhythm vocab, tempo
tonal.py           L2: Key areas, density, modality
schematic.py       L3: Schema chain generation
metric/layer.py    L4: Metric orchestration
metric/distribution.py Bar/beat distribution
metric/schema_anchors.py Schema anchor generation
textural.py        L5: Treatment assignments
rhythmic.py        L6: Active slots, durations
melodic.py         L7: Greedy pitch solver (orphaned)
```

### Planner Structure
```
structure.py       SectionSchema hierarchy from schema chain
schema_loader.py   Load and query schema definitions
schema_generator.py Schema chain from cadence plan
subject_validator.py Validate subject against opening schema
subject_deriver.py Derive subject from opening schema
treatment_generator.py Dynamic treatment sequences
arc.py             Tension curve management
```

### Planner Material
```
material.py        Subject acquisition with affect-driven generation
subject.py         Subject class with N counter-subjects
cs_generator.py    CP-SAT counter-subject solver
motif_loader.py    Load .note files as motifs
```

### Planner Harmony
```
harmony.py         Key scheme, modulations, cadences
phrase_harmony.py  Bar-level chord progressions
dramaturgy.py      Rhetorical structure, tension curves
devices.py         Figurenlehre device assignment
coherence.py       Callbacks, surprises, proportions
constraints.py     Plan → bar-level constraint synthesis
koch_rules.py      Koch's mechanical rules
```

### Motifs (Subject Generation)
```
subject_generator.py 2-bar subjects via head+tail
head_generator.py  Leap + gap-fill heads (music cognition)
tail_generator.py  Contrary-motion tails (43 melodic cells)
figurae.py         Baroque rhetorical figures
melodic_features.py 40+ research-backed melody features
enumerator.py      Exhaustive candidate enumeration
affect_loader.py   Load affects, score subjects
frequencies/analyse_intervals.py Corpus interval analysis
```

### Shared
```
pitch.py           FloatingNote (scale degree without octave)
typedefs.py        Motif and shared data structures
key.py             Key class with degree_to_midi, floating_to_midi
voice_role.py      TOP, BOTTOM, INNER_1, INNER_2 roles
timed_material.py  Budget-first duration enforcement
parallels.py       Parallel fifth/octave detection (canonical)
dissonance.py      Harsh interval detection
music_math.py      Fractional duration arithmetic
constants.py       Scales, note names, valid durations
tracer.py          Pipeline execution tracing
validate.py        Typed validation exceptions
errors.py          AndanteError exception hierarchy
constraint_validator.py Brief/Frame YAML validation
yaml_validator.py  Cross-file type reference validation
midi_writer.py     Standalone MIDI generation
```

---

## Key Invariants

1. **Budget-first:** `sum(durations) == budget` always
2. **Valid by construction:** Every layer draws from pre-validated options
3. **Guards detect, generators prevent:** Don't fix downstream
4. **Vocabulary is normative:** Terms must match vocabulary.md
5. **Fractions for music, integers for counts**
6. **One class per file, methods alphabetical**
7. **Frozen dataclasses everywhere**
8. **Parallel detection canonical:** Only in `shared/parallels.py`
9. **No try blocks:** Use membership test or let it raise
10. **MIDI gate time:** Always 95% to avoid legato issues

---

## Common Gotchas

1. **MidiPitch bypasses octave selection.** If you see weird octaves, check if something is creating MidiPitch when it should be FloatingNote.

2. **Layer 7 Melodic is orphaned.** Figuration (L6.5) now provides pitch sequences. L7 code exists but is not called.

3. **Backtracking is per-phrase.** If exhausted, it's a spec error, not a code bug.

4. **Leading tone (degree 7) reserved for subject cadences only.** Don't use elsewhere.

5. **Tonal targets are functions, not modulations.** V means dominant function in home key.

6. **Natural minor for melodic content.** Only raise 6/7 at cadences.

7. **Diatonic vs Chromatic modality.** The flag propagates from L2 to realisation.

8. **Schema arrivals vs degrees.** `entry`/`exit` are derived from first/last of `soprano_degrees`/`bass_degrees`.

---

## Running Commands

```bash
# Activate venv and run from andante/
cd /d/projects/Barok/barok && source .venv/Scripts/activate && cd source/andante

# Run tests
python -m pytest

# Run full pipeline
python -m scripts.run_pipeline

# Run showcase
python -m scripts.run_showcase

# Convert formats
python -m scripts.midi_to_note input.mid
python -m scripts.note_to_midi input.note
python -m scripts.note_to_subject input.note
python -m scripts.subject_to_midi input.subject
```

---

## Essential Reading Order

1. **This file** (summary.md)
2. **bugs.md** - Known issues and fixes
3. **docs/Tier1_Normative/laws.md** - Coding rules and anti-patterns
4. **docs/Tier2_Architecture/architecture.md** - 7-layer pipeline details
5. **docs/Tier2_Architecture/figuration.md** - L6.5 figuration spec
6. **docs/Tier4_Reference/counterpoint_rules.md** - Treatise-based rule catalog
7. **data/rules/counterpoint_rules.yaml** - Machine-readable rules

---

## YAML Data Files Quick Reference

| Directory | Files | Purpose |
|-----------|-------|---------|
| genres/ | 9 files | Genre templates (invention, minuet, gavotte, etc.) |
| rhetoric/ | 5 files | affects, archetypes, figurae, episodes, tension_curves |
| schemas/ | 2 files | Partimento patterns, transitions |
| figuration/ | 7 files | Ornaments, diminutions, accompaniments, bass patterns |
| instruments/ | 7 files | Violin, piano, recorders, flute |
| rules/ | 2 files | Counterpoint rules, constraints |
| treatments/ | 1 file | Voice expansion treatments |
| cadences/ | 1 file | Cadential formulas |
| voicing/ | 1 file | Texture specs |
| forms/ | 3 files | binary, strophic, through_composed |
| humanisation/ | 4+ files | Metric weights, performance styles |

---

*Last updated: 2026-01-28*
