# Andante — Machine Knowledge

Dense reference for Claude. No rationale. For "why", see conductor.md.
For laws, see `docs/Tier1_Normative/laws.md`.

## What Andante Is

Baroque music generator. All genres (bourree, chorale, fantasia, gavotte, invention, minuet, sarabande, trio_sonata), not just inventions. Two voices: soprano + bass. Two compositional paths: galant (schema-driven) and imitative (fugal subjects/answers/countersubjects/episodes/stretto). Output: MIDI + MusicXML + enriched .note CSV.

## Pipeline

```
L1 rhetorical.py    GenreConfig -> trajectory, rhythm_vocab, tempo
L2 tonal.py         AffectConfig -> tonal_plan, density, modality
L3 schematic.py     tonal_plan + configs -> SchemaChain (schemas, keys, cadences)
L4 metric/layer.py  SchemaChain + configs -> bar_assignments, anchors, total_bars
L5 phrase_planner   SchemaChain + anchors -> tuple[PhrasePlan]
L6 phrase_writer    PhrasePlan -> PhraseResult (upper_notes, lower_notes)
L7 compose.py       PhrasePlans -> Composition (voices, notes)
```

Orchestrator: `planner/planner.py` calls L1-4, then phrase planning + compose_phrases().

## Phrase Writer Dispatch (builder/phrase_writer.py)

Three paths:
- **Cadential**: fixed clausula templates (cadence_writer.py)
- **Thematic**: subject/answer/CS/episode/stretto via thematic_renderer.py; FREE tail bars use galant order
- **Schematic (galant)**: structural soprano -> bass -> soprano Viterbi

Galant order: build_structural_soprano() -> bass (Viterbi or greedy) -> generate_soprano_viterbi()

Episode content: `motifs/episode_dialogue.py` built from **paired kernels** — frozen two-voice units (soprano degrees+durations, bass degrees+durations) extracted from the subject/countersubject overlap in the exposition. Vertical consonance is inherited from the original invertible counterpoint, not solved per-episode. Kernels are chained to fill episode bar counts, with sequential transposition applied to both voices together (preserving intervals). Different kernel combinations per episode provide variety. Each iteration carries a HarmonicGrid derived from the sequence pattern (e.g. descending step: I→vii°→vi→V), projected via `harmony_projection.py`. See "Episode Construction — Paired Kernels" in `docs/imitative_design.md` for full design.

## Module Layout

### builder/galant/ — galant-only modules
- bass_writer.py: greedy bass between structural tones
- soprano_writer.py: build_structural_soprano (schema degree skeleton)
- harmony.py: HarmonicGrid from schema Roman numerals, stock harmonic grid for thematic fills, cadential acceleration, passing 6/3 chords, secondary dominants (V/V, V/vi)

### builder/ — shared + orchestration
- soprano_viterbi.py: place_structural_tones, generate_soprano_viterbi (both paths)
- bass_viterbi.py: generate_bass_viterbi (walking bass; both paths)
- phrase_writer.py: three-way dispatcher
- phrase_planner.py: L4 output -> PhrasePlans
- compose.py: phrase-by-phrase composition entry
- cadence_writer.py: clausula templates (cadenza semplice, composta, doppia, grande, half cadence)
- thematic_renderer.py: render subject/answer/CS/episode/stretto
- entry_renderer.py: imitative entry rendering
- cs_writer.py: countersubject writing
- knot_builder.py: knot construction
- hold_writer.py: held-note writing
- free_fill.py: free-texture fill
- imitation.py: subject_to_voice_notes, _fit_shift
- rhythm_cells.py: genre rhythm cells
- faults.py: post-composition fault scan
- voice_writer.py: validate_voice, audit_voice
- voice_types.py: VoiceConfig, VoiceContext
- phrase_types.py: PhrasePlan, PhraseResult (frozen dataclasses)
- types.py: Note, Composition, SchemaConfig, GenreConfig, FormConfig
- config_loader.py: load all YAML configs
- io.py: MIDI/MusicXML output, note helpers
- note_writer.py: enriched .note CSV (with figured bass harmony labels)
- musicxml_writer.py: MusicXML output

### builder/figuration/ — diminution and bass patterns
- types.py: Figure, FigurationProfile (frozen dataclasses)
- loader.py: load diminution tables from YAML
- generator.py: figuration generation engine
- selection.py: figure selection logic
- bass.py: bass figuration patterns
- soprano.py: soprano figuration patterns
- rhythm_calc.py: rhythmic subdivision calculation

### planner/
- planner.py: orchestrator, generate() entry
- rhetorical.py, tonal.py, schematic.py: L1-L3
- schema_loader.py: parse schemas.yaml
- metric/: L4 (layer.py, schema_anchors.py, constants.py)
- thematic.py: BeatRole, ThematicRole enum
- imitative/: entry_layout.py, subject_planner.py, types.py
- arc.py, dramaturgy.py, variety.py, plannertypes.py

### shared/
- constants.py, key.py, pitch.py, diatonic_pitch.py, schema_types.py
- voice_types.py: Voice, Actuator, Range, Role enum
- music_math.py: duration arithmetic, parse_metre
- counterpoint.py: prevent_cross_relation
- pitch_selection.py
- midi_writer.py, yaml_parsing.py, tracer.py

### viterbi/ — Viterbi pathfinder engine
- generate.py: generate_voice (entry point)
- pathfinder.py, corridors.py, costs.py, scale.py, mtypes.py, pipeline.py

### motifs/
- subject_loader.py (SubjectTriple), subject_generator.py, answer_generator.py
- countersubject_generator.py, head_generator.py
- fragment_catalogue.py, catalogue.py
- stretto_analyser.py, stretto_constraints.py, thematic_transform.py
- fragen.py (fragment extraction, cell chaining)
- episode_dialogue.py (paired-kernel episode generation)
- episode_kernel.py (DFS solver and used-set tracking, adapted for PairedKernels)
- extract_kernels.py (PairedKernel extraction from subject/CS overlap)

### motifs/subject_gen/ — subject generation subsystem
- models.py: SubjectVocabulary, SegmentSpec, SubjectPlan (frozen dataclasses)
- subject_planner.py: plan enumeration with density/contour specs
- planned_selector.py: plan-driven subject selection and scoring
- selector.py: top-level selector entry point
- scoring.py: subject quality scoring (density trajectory, repetition penalty)
- melody_generator.py: full subject assembly from segments
- pitch_generator.py: pitch sequence generation
- duration_generator.py: rhythmic cell enumeration
- segment_rhythm.py: per-segment rhythm with independent density
- rhythm_cells.py: cell definitions (dactyl, tirata, etc.)
- contour.py: melodic contour shapes
- contour_filter.py: contour constraint filtering
- harmonic_grid.py: subject-level harmonic constraints
- validator.py: subject validation rules
- cache.py: generation cache
- constants.py: subject generation constants
- stretto_gpu.py: GPU-accelerated stretto analysis

## Pitch Types

```
FloatingNote (degree 1-7, no octave) -> DiatonicPitch (linear step) -> MIDI (via Key)
```

Key class: tonic + mode. Hub for degree <-> MIDI <-> diatonic conversion.

## Duration System

All durations: Fraction of whole note. Arithmetic via music_math only.
Valid: 1, 3/4, 1/2, 3/8, 1/4, 3/16, 1/8, 3/32, 1/16, 1/32.
MIDI gate: 95% (GATE_FACTOR = 19/20).

## Voice Ranges (MIDI)

```
0 Soprano  55-84  median 70
1 Alto     50-74  median 60
2 Tenor    45-69  median 54
3 Bass     36-62  median 48
```

## Schemas (data/schemas/schemas.yaml)

Opening: do_re_mi, romanesca, meyer, sol_fa_mi
Continuation: prinner, fonte(seq), monte(seq), fenaroli, ponte
Pre-cadential: passo_indietro, indugio
Cadential: cadenza_semplice, cadenza_composta, comma, half_cadence
Post-cadential: quiescenza

Degrees signed: +2 = up to 2, -7 = down to 7. First degree unsigned.
Sequential schemas transpose per segment.

## Genres (data/genres/*.yaml)

bourree, chorale, fantasia, gavotte, invention, minuet, sarabande, trio_sonata
Fields: name, voices, instruments, scoring, tracks, form, metre, rhythmic_unit, tempo, bass_treatment, sections (each: name, schema_sequence, lead_voice, accompany_texture).

## YAML Data

```
data/archetypes/       subject archetype definitions
data/cadences/         cadence type definitions
data/cadences/templates.yaml clausula patterns per cadence type
data/figuration/       diminutions, patterns, profiles, rhythms
data/forms/            binary, strophic, through_composed
data/genres/           per-genre configs + _default
data/humanisation/     timing/velocity variation
data/instruments/      instrument definitions
data/rhetoric/         affects, archetypes, figurae, tension
data/rhythm/           rhythm profiles
data/rhythm_cells/     genre-specific rhythm cell definitions
data/rules/            constraints, counterpoint_rules
data/schemas/          schemas, transitions
data/subject_gestures/ subject melodic gesture definitions
data/treatments/       treatments.yaml
data/voicing/          voice spacing/doubling rules
```

## Conventions

- Bars are 1-based. First note = bar 1, beat 1.
- Phrase is the unit of composition. One schema = one phrase.
- Soprano first, bass fitted (baroque practice).
- Counterpoint checked inline during generation, not post-hoc.
- Cadences use fixed clausula templates.

## CLI

```
python -m scripts.run_pipeline <brief_file> [-o DIR] [-v] [-trace] [-seed N]
python -m scripts.run_pipeline <genre> <affect> [key] [-o DIR] [-v] [-trace] [-seed N]
```

## Gotchas

1. Schema degrees 1-7; DiatonicPitch.step is 0-based. Convert via .degree.
2. Schema degrees signed: +2 = up to 2, -7 = down to 7.
3. Key.diatonic_step() = scale steps not semitones. Chromatic: use MIDI arithmetic.
4. Always Fraction for durations, never float.
5. MIN_BASS_MIDI = 40 (E2): floor, not hard clamp.
