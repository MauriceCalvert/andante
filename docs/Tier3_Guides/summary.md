# Andante Codebase Summary

**Purpose:** Enable rapid context acquisition for new sessions. Read this first.

---

## What Is Andante?

Baroque music composition system with symmetric Planner/Executor architecture:
- **Planner**: Brief → YAML plan (what to compose)
- **Executor**: YAML → MIDI/MusicXML (how to realise it)

---

## Directory Structure

```
andante/
├── engine/                 # Executor: YAML → playable notes
│   ├── guards/             # Voice-leading constraint checkers
│   ├── pipeline.py         # E1-E6 orchestrator
│   ├── plan_parser.py      # YAML → PieceAST
│   ├── expander.py         # Phrases → bar-level pitches (orchestrator)
│   ├── expand_phrase.py    # Single phrase expansion
│   ├── phrase_builder.py   # Budget-aware bar treatment concatenation
│   ├── voice_pipeline.py   # Data-driven voice generation from treatment config
│   ├── voice_expander.py   # N-voice expansion with figured bass, schemas
│   ├── n_voice_expander.py # N-voice with arc and voice_entries
│   ├── realiser.py         # Degrees → MIDI pitches with ornaments
│   ├── slice_solver.py     # Slice-based voice resolution (CP-SAT)
│   ├── cpsat_slice_solver.py # CP-SAT constraint satisfaction solver
│   ├── inner_voice.py      # Branch-and-bound inner voice search
│   ├── formatter.py        # Notes → track/bar/beat
│   └── output.py           # Export to MIDI/MusicXML/CSV
│
├── planner/                # Planner: Brief → YAML
│   ├── planner.py          # 7-stage pipeline orchestrator
│   ├── plannertypes.py     # Brief, Frame, Material, Plan, etc.
│   ├── frame.py            # Resolve key/mode/metre/tempo
│   ├── material.py         # Subject acquisition with affect-driven generation
│   ├── subject.py          # Subject with lazy counter-subject
│   ├── cs_generator.py     # CP-SAT counter-subject solver
│   ├── structure.py        # Build SectionSchema from schema chain
│   ├── cadence_planner.py  # Plan cadence points from frame/genre
│   ├── schema_generator.py # Generate schema chain from cadence plan
│   ├── schema_loader.py    # Load and query schema definitions
│   ├── subject_validator.py # Validate subject against opening schema
│   ├── subject_deriver.py  # Derive subject from opening schema
│   ├── dramaturgy.py       # Rhetorical structure & tension curves
│   ├── harmony.py          # Harmonic architecture planning
│   ├── devices.py          # Figurenlehre device assignment
│   ├── coherence.py        # Callbacks, surprises, golden ratio
│   ├── constraints.py      # Plan → bar-level constraint synthesis
│   ├── treatment_generator.py # Dynamic treatment sequences
│   ├── arc.py              # Tension curve management
│   ├── validator.py        # Plan structural validation
│   └── serializer.py       # Plan → YAML output
│
├── motifs/                 # Subject generation (music cognition research)
│   ├── subject_generator.py # 2-bar subjects via head+tail
│   ├── head_generator.py   # Leap + gap-fill heads (3-5 notes)
│   ├── tail_generator.py   # Contrary-motion tails (43 melodic cells)
│   ├── figurae.py          # Baroque rhetorical figures (Figurenlehre)
│   ├── melodic_features.py # 40+ research-backed melody features
│   ├── memorable_generator.py # 3-axis generation model
│   └── enumerator.py       # Exhaustive candidate enumeration
│
├── shared/                 # Cross-cutting types and utilities
│   ├── pitch.py            # FloatingNote, MidiPitch, Rest
│   ├── types.py            # VoiceMaterial, ExpandedVoices, Motif, Frame
│   ├── key.py              # Key class with scale conversion
│   ├── timed_material.py   # Budget-first duration handling
│   ├── parallels.py        # Parallel fifth/octave detection (canonical)
│   ├── music_math.py       # Exact fractional duration arithmetic
│   ├── constants.py        # Scales, note names, valid durations
│   ├── tracer.py           # Pipeline execution tracing
│   ├── constraint_validator.py # Brief/Frame YAML validation
│   └── midi_writer.py      # Standalone MIDI generation
│
├── data/                   # YAML configuration (all musical knowledge)
│   ├── genres/*.yaml       # invention, chorale, fantasia, minuet...
│   ├── affects.yaml        # Affektenlehre (8 baroque affects)
│   ├── archetypes.yaml     # Dramaturgical archetypes (6 types)
│   ├── figurae.yaml        # Rhetorical figures (20+ figures)
│   ├── arcs.yaml           # Tension curves and treatments (12 arcs)
│   ├── treatments.yaml     # Voice expansion specs (21 treatments)
│   ├── episodes.yaml       # Episode types (32+ types)
│   ├── cadences.yaml       # Cadential formulas
│   ├── schemas.yaml        # Partimento patterns (fonte, monte, prinner)
│   ├── counterpoint_rules.yaml  # Hard/soft constraints and rewards
│   └── predicates.yaml     # Intervals, registers, consonance
│
├── scripts/                # CLI entry points
│   ├── run_pipeline.py     # Full pipeline execution
│   ├── run_exercises.py    # Run test exercises
│   ├── generate_subjects.py # Subject generation
│   └── generate_heads.py   # Head enumeration
│
├── briefs/exercises/     # Test YAML files
├── output/                 # Generated MIDI/MusicXML
├── tests/                  # Pytest suites (2700+ tests)
└── docs/                   # Architecture and guides
    ├── Tier1_Normative/    # grammar.md, vocabulary.md, lessons.md
    ├── Tier2_Architecture/ # architecture.md
    ├── Tier3_Guides/       # walkthrough.md, learnings.md, bob.md
    ├── Tier4_Reference/    # grounding.md, motif_study.md, violin.md
    ├── Tier5_Roadmap/      # roadmap.md, TODO_period_styles.md
    ├── counterpoint_rules.md  # Treatise synthesis (Fux, Rameau, etc.)
    └── bugs.md             # Bug tracking
```

---

## Data Flow

```
Brief (affect, genre, forces, bars)
    ↓
╔═══════════ PLANNER ═══════════╗
║                               ║
║  Frame (key, mode, metre, tempo, voices)
║      ↓                        ║
║  Dramaturgy (archetype, rhetoric, tension curve)
║      ↓                        ║
║  Material (subject, counter-subject, derived motifs)
║      ↓                        ║
║  Structure (sections → episodes → phrases)
║      ↓                        ║
║  Harmony (key scheme, cadences)
║      ↓                        ║
║  Devices (Figurenlehre assignment)
║      ↓                        ║
║  Coherence (callbacks, surprises, proportions)
║                               ║
╚═══════════════════════════════╝
    ↓
YAML Plan
    ↓
╔═══════════ ENGINE ════════════╗
║                               ║
║  E1 Parse     → PieceAST      ║
║      ↓                        ║
║  E3 Expand    → ExpandedPhrase (bar-level FloatingNotes)
║      ↓                        ║
║  E4 Realise   → RealisedPhrase (MIDI pitches)
║      ↓                        ║
║  E6 Format    → Note (track/bar/beat)
║                               ║
╚═══════════════════════════════╝
    ↓
Export → .midi / .musicxml / .note
```

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
YAML degrees → FloatingNote → (slice solver) → MIDI int
```

---

## Slice-Based Voice Resolution (Core Algorithm)

**Location:** `engine/slice_solver.py` + `engine/inner_voice.py`

At each vertical slice where outer voices sound:

1. **Resolve outer voices** (soprano/bass) to MIDI
2. **Infer harmony** from outer voices (chord tones)
3. **For each inner voice**, left-to-right:
   - Generate candidates (texture-dependent)
   - Filter by constraints (parallels, crossing)
   - Select best by voice-leading cost
4. **Build solved voices** back to ExpandedVoices

**Candidate generation varies by texture:**
| Texture | Candidates |
|---------|------------|
| Polyphonic | Octave variants of thematic pitch, chord-tone fallback |
| Homophonic | Chord tones directly |

**Steps 2-3 are IDENTICAL for all textures.** This is the key invariant.

---

## Key Engine Functions

### slice_solver.py / cpsat_slice_solver.py
- `solve_phrase_cpsat()` - CP-SAT solver for inner voices
- `filter_candidates()` - Removes parallel fifths/octaves, voice crossing
- `rank_candidates()` - Voice-leading cost (unison, leaps, median distance)

### inner_voice.py
- `add_inner_voices_with_backtracking()` - Branch-and-bound search
- `add_inner_voices_cpsat()` - CP-SAT with branch-and-bound fallback
- `_score_phrase_combination()` - Holistic scoring across all slices

### realiser.py
- `realise_phrase()` - FloatingNote → MIDI with ornaments
- `realise_voice_against()` - Voice realisation checking parallels

### expander.py
- `expand_piece()` - Orchestrates guard-based backtracking
- Handles 2/3/4-voice expansion with inner voice insertion

---

## Key Planner Functions

### planner.py
- `build_plan()` - 7-stage pipeline: frame → dramaturgy → material → structure → harmony → devices → coherence

### cs_generator.py
- `generate_countersubject()` - CP-SAT solver with 7 constraint groups:
  - Vertical (consonance, no parallels)
  - Melodic (contrary motion, leap compensation)
  - Rhythmic (attack awareness)
  - Cadential (final note stability)
  - Motivic (duration vocabulary)
  - Invertibility (avoid inversely-dissonant intervals)
  - Climax (offset from subject peak)

### subject_generator.py (in motifs/)
- `generate_subject()` - Head + tail construction with figurae scoring
- Uses music cognition research (leap + gap-fill pattern)

---

## Guards System

**Location:** `engine/guards/`

Guards detect violations AFTER generation. Generators must PREVENT violations.

| Guard | Checks |
|-------|--------|
| `registry.py` | Orchestrates all guards, creates diagnostics |
| `spacing.py` | Voice spacing limits (adjacent, bass gap, outer) |
| `voice_checks.py` | Parallel fifths/octaves, bar duplication, endless trill |

**Backtracking:** If guards fail, increment seed and retry phrase expansion.

---

## Module Categories

### Engine Core (Pipeline)
```
pipeline.py        E1-E6 orchestrator, exports to MIDI/MusicXML/note
plan_parser.py     YAML → PieceAST with validation
validate.py        Validate YAML against normative vocabulary
engine_types.py    PieceAST, SectionAST, ExpandedPhrase, RealisedNote
```

### Engine Expansion
```
expander.py        Piece-level expansion with guard backtracking
expand_phrase.py   Single phrase expansion entry point
phrase_builder.py  Bar treatment concatenation with budget enforcement
phrase_expander.py Alternative expansion path with overrides
voice_pipeline.py  Data-driven voice generation from treatment specs
voice_expander.py  N-voice expansion (figured bass, pedal, schema, walking)
n_voice_expander.py N-voice with arc voice_entries
expander_util.py   Constants and helper functions
```

### Engine Voice System
```
slice_solver.py    Slice-based constraint solver (imported by inner_voice)
cpsat_slice_solver.py CP-SAT solver via OR-Tools
inner_voice.py     Branch-and-bound phrase-level inner voice search
voice_realiser.py  FloatingNote → MIDI with octave selection
voice_config.py    VoiceSet factory (2/3/4-voice configurations)
voice_material.py  VoiceMaterial, ExpandedVoices types
voice_pair.py      Voice pair enumeration for constraint checking
voice_entry.py     N-voice per-phrase specifications
voice_checks.py    Parallel motion, bar duplication, endless trill detection
subdivision.py     VerticalSlice extraction at attack points
octave.py          Octave placement heuristics
```

### Engine Musical Techniques
```
cadence.py         Cadential approach/resolution patterns
cadenza.py         Quasi-improvisatory virtuosic passages
schema.py          Partimento schemas (fonte, monte, prinner)
texture.py         Texture system (polyphonic, interleaved, canon, hocket)
transform.py       Melodic transforms (invert, retrograde, augment)
harmonic_context.py Infer chord tones from outer voices
ornament.py        Trill, mordent, turn application
figuration.py      Figuration patterns for melodic variation
sequence.py        Sequential repetition with transposition/variation
pedal.py           Pedal point bass generation
walking_bass.py    Pattern-based walking bass
figured_bass.py    Figured bass realisation
hemiola.py         Metric displacement for rhythmic tension
passage.py         Virtuosic passage patterns (scalar, arpeggiated, tremolo)
episode.py         Episode-specific treatment and rhythm overrides
```

### Engine Character & Expression
```
energy.py          Dynamic character effects on phrases
surprise.py        Strategic deviations from expectation
episode_registry.py Episode generator registry (decorator pattern)
arc_loader.py      Parse arcs.yaml with voice_entries
```

### Engine Realisation & Output
```
realiser.py        E4 Realiser (pitch types → MIDI pitches)
realiser_passes.py Bass-specific post-processing
realiser_guards.py Guard checking for realiser
formatter.py       RealisedPhrase → Note with track/bar/beat
output.py          Export to MIDI/MusicXML/CSV via music21
serializer.py      ExpandedPhrase list → Expanded YAML
```

### Engine Analysis
```
metrics.py         Thematic_ratio and variety_ratio calculation
annotate.py        Extract annotations from piece structure
```

### Planner Core
```
planner.py         Brief → Plan orchestrator (7 stages)
plannertypes.py    Brief, Frame, Material, Structure, Plan, etc.
types.py           Legacy alias for plannertypes.py
frame.py           Resolve key/mode/metre/tempo from genre/affect
material.py        Subject acquisition with affect-driven generation
subject.py         Subject class with lazy counter-subject
cs_generator.py    CP-SAT counter-subject solver
validator.py       Plan structural integrity checks
serializer.py      Plan → YAML with Fraction formatting
```

### Planner Structure (Schema-First)
```
structure.py       Build SectionSchema hierarchy from schema chain
cadence_planner.py Plan cadence points from frame and genre
schema_generator.py Generate schema chain from cadence plan
schema_loader.py   Load and query schema definitions
subject_validator.py Validate subject against opening schema
subject_deriver.py Derive subject from opening schema
treatment_generator.py Dynamic treatment sequences by genre
arc.py             Tension curve management
```

### Planner Dramaturgy
```
dramaturgy.py      Rhetorical structure & tension curves
harmony.py         Harmonic architecture (key scheme, cadences)
devices.py         Figurenlehre device assignment
coherence.py       Callbacks, surprises, golden ratio scoring
constraints.py     Plan → bar-level constraint synthesis
```

### Planner Utilities
```
motif_loader.py    Load .note files as motifs
```

### Motifs (Subject Generation)
```
subject_generator.py 2-bar subjects via head+tail with figurae
head_generator.py  Leap + gap-fill heads (music cognition)
tail_generator.py  Contrary-motion tails (43 melodic cells)
figurae.py         Baroque rhetorical figures (26+ constraints)
melodic_features.py 40+ research-backed melody features
memorable_generator.py 3-axis generation (pitch/rhythm/contour)
enumerator.py      Exhaustive candidate enumeration with caching
```

### Shared
```
pitch.py           FloatingNote, MidiPitch, Rest types
types.py           VoiceMaterial, ExpandedVoices, Motif, Frame
key.py             Key class with degree_to_midi, floating_to_midi
timed_material.py  Budget-first duration enforcement
parallels.py       Parallel fifth/octave detection (canonical source)
music_math.py      Fractional duration arithmetic, fill_slot
constants.py       Scales, note names, valid durations
tracer.py          Pipeline execution tracing
constraint_validator.py Brief/Frame YAML validation
yaml_validator.py  Cross-file type reference validation + usage report
midi_writer.py     Standalone MIDI generation
```

---

## Treatment vs Texture

Two orthogonal concerns that compose independently:

| Concept | Question | Examples |
|---------|----------|----------|
| **Treatment** | What notes? | inversion, fragmentation, augmentation |
| **Texture** | How do voices interact? | polyphonic, interleaved, canon, hocket |

In YAML plans:
```yaml
- {treatment: inversion, texture: interleaved}   # inverted subject, Goldberg-style
- {treatment: fragmentation, texture: canon}     # head motif in canon
```

Treatment applies melodic transformation to source material. Texture arranges voices.

**Key files:**
- `data/treatments.yaml` - melodic transforms
- `data/textures.yaml` - voice relationships
- `engine/texture.py` - TextureSpec and apply_texture()
- `docs/Tier2_Architecture/texture_design.md` - full design doc

---

## Key Invariants

1. **Budget-first:** `sum(durations) == budget` always
2. **Slice resolution:** All textures use same filter/select logic
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

1. **Two code paths = bugs.** If polyphonic/homophonic have different logic beyond candidate generation, that's wrong.

2. **MidiPitch bypasses octave selection.** If you see weird octaves, check if something is creating MidiPitch when it should be FloatingNote.

3. **Inner voices are solved left-to-right.** Voice 1 (alto) is constrained against soprano+bass. Voice 2 (tenor) is constrained against soprano+bass+alto.

4. **Backtracking is per-phrase.** If exhausted, it's a spec error, not a code bug.

5. **Arc voice_entries may be incomplete.** Check if all phrases have entries for all voices.

6. **Leading tone (degree 7) reserved for subject cadences only.** Don't use elsewhere.

7. **Tonal targets are functions, not modulations.** V means dominant function in home key.

8. **Natural minor for melodic content.** Only raise 6/7 at cadences.

---

## Running Commands

```bash
# Activate venv and run from andante/
cd /d/projects/Barok/barok && source .venv/Scripts/activate && cd source/andante

# Run tests
python -m pytest

# Run specific exercise
python -m scripts.run_exercises

# Run planner
python -m scripts.run_planner

# Run full pipeline
python -m scripts.run_pipeline

# Generate subjects
python -m scripts.generate_subjects
```

---

## Essential Reading Order

1. **This file** (summary.md)
2. **bugs.md** - Known issues and fixes
3. **docs/Tier1_Normative/lessons.md** - Coding rules and anti-patterns
4. **docs/Tier2_Architecture/architecture.md** - Full pipeline details
5. **engine/slice_solver.py** - The core algorithm
6. **counterpoint_rules.md** - Treatise-based rule catalog
7. **data/counterpoint_rules.yaml** - Machine-readable rules for solver

---

## YAML Data Files Quick Reference

| File | Purpose |
|------|---------|
| affects.yaml | 8 Affektenlehre affects (Sehnsucht, Klage, etc.) |
| archetypes.yaml | 6 dramaturgical archetypes with rhetoric proportions |
| figurae.yaml | 20+ baroque rhetorical figures by category |
| arcs.yaml | 12 arc templates (simple, invention, fugue, dance) |
| treatments.yaml | Voice expansion treatments (melodic transforms) |
| textures.yaml | Texture specs (polyphonic, interleaved, canon, hocket) |
| episodes.yaml | 32+ episode types with energy profiles |
| cadences.yaml | Internal (half-bar) and final (2-bar) formulas |
| schemas.yaml | Partimento patterns (fonte, monte, prinner) |
| counterpoint_rules.yaml | Hard/soft constraints and rewards (CP-SAT) |
| predicates.yaml | Intervals, registers, consonance classification |
| genres/*.yaml | Genre templates (invention, fantasia, minuet, etc.) |

---

## Test Coverage

- **2700+ tests** across engine, planner, and shared modules
- **95%+ coverage** on all production modules
- Tests follow specification-based methodology (validate against truths, not implementation)

---

*Last updated: 2026-01-14*
