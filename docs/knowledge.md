# Andante — Machine Knowledge

Dense reference for Claude. No rationale. For "why", see conductor.md.

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

## Module Layout

### builder/galant/ — galant-only modules
- bass_writer.py: greedy bass between structural tones
- soprano_writer.py: build_structural_soprano (schema degree skeleton)
- harmony.py: HarmonicGrid from schema Roman numerals

### builder/ — shared + orchestration
- soprano_viterbi.py: place_structural_tones, generate_soprano_viterbi (both paths)
- bass_viterbi.py: generate_bass_viterbi (walking bass; both paths)
- phrase_writer.py: three-way dispatcher
- phrase_planner.py: L4 output -> PhrasePlans
- compose.py: phrase-by-phrase composition entry
- cadence_writer.py: clausula templates
- thematic_renderer.py: render subject/answer/CS/episode/stretto
- entry_renderer.py: imitative entry rendering
- cs_writer.py: countersubject writing
- knot_builder.py: knot construction
- hold_writer.py: held-note writing
- free_fill.py: free-texture fill
- imitation.py: subject_to_voice_notes
- rhythm_cells.py: genre rhythm cells
- faults.py: post-composition fault scan
- voice_writer.py: validate_voice, audit_voice
- voice_types.py: VoiceConfig, VoiceContext
- phrase_types.py: PhrasePlan, PhraseResult (frozen dataclasses)
- types.py: Note, Composition, SchemaConfig, GenreConfig, FormConfig
- config_loader.py: load all YAML configs
- io.py: MIDI/MusicXML output, note helpers
- note_writer.py: enriched .note CSV
- musicxml_writer.py: MusicXML output
- figuration/: diminution tables, bass patterns, rhythm calc

### planner/
- planner.py: orchestrator, generate() entry
- rhetorical.py, tonal.py, schematic.py: L1-L3
- schema_loader.py: parse schemas.yaml
- metric/: L4 (layer.py, pitch.py, schema_anchors.py, constants.py)
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
- fragen.py (episode fragment generation), episode_kernel.py

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
data/figuration/   diminutions, patterns, profiles, rhythms
data/forms/        binary, strophic, through_composed
data/genres/       per-genre configs + _default
data/humanisation/ timing/velocity variation
data/instruments/  instrument definitions
data/rhetoric/     affects, archetypes, figurae, tension
data/rules/        constraints, counterpoint_rules
data/schemas/      schemas, transitions
data/treatments/   treatments.yaml
```

## Laws (complete)

Architecture:
- A001 No if-chains, use declarative rules
- A002 Same engine for all transforms
- A003 Rules are data (YAML)
- A004 Repeats are performance, not composition
- A005 RNG in planner, determinism in builder
- A006 Domain logic independent of infrastructure (ports/adapters)

Defence:
- D001 Validate, don't fix
- D002 Constraints propagate upward
- D003 Trace must debug without source
- D004 Separate melodic approach from harmonic formula
- D005 Compute patterns from budget, don't predefine variants
- D006 Motifs must be asymmetric
- D008 No downstream fixes
- D009 Generators must use phrase_index
- D010 Guards detect, generators prevent
- D011 Voice-agnostic generation: no soprano/bass branching in generators

Code:
- L001 Try blocks forbidden
- L002 Magic numbers forbidden, use constants
- L003 Hard range constraints forbidden, soft hints only
- L004 Voice crossing allowed only if intentional (invertible counterpoint)
- L005 Duration arithmetic forbidden, use music_math
- L006 Durations must be in VALID_DURATIONS
- L007 Natural minor for melody, raised 6/7 cadential only
- L008 Tonal targets = harmonic functions, not scale selection
- L009 Tonal targets = functions not modulations, use home_key
- L010 Leading tone in cadential context only
- L011 While loops need guards and max_iterations
- L012 Quantization forbidden, fix upstream
- L013 MIDI gate time 95%
- L014 Clone before modify, never mutate parameters
- L015 NamedTuple/dataclass, not tuples
- L016 Logging only, no print
- L017 Single source of truth, inherit not repeat
- L018 __init__.py must be empty, no re-exports
- L019 ASCII only, no UTF8 symbols
- L020 All arguments passed by keyword, no positional calls
- L021 Brief fallback warning: YAML/brief impossibilities get sarcastic-but-kind warning

Scope:
- S001 Performance practice out of scope; score notation only

Variety:
- V001 Generators vary via phrase_index, bar_idx, segment offsets
- V002 Tremolo max 6 notes

Anti-patterns:
- X001 No post-realisation pitch adjustment
- X002 No iterative fix loops
- X003 No global signature tracking at MIDI level
- X004 No separate bar-fix and sequence-fix passes
- X005 No rep counter starting at 0 each phrase

Modularity:
- M001 Bundle 3+ optional params that travel through 2+ call layers into frozen dataclass
- M002 Function signatures max 10 params; bundle related groups into context dataclass
- M003 Pass the source object, not its extracted fields, when callee has access to both
- M004 Frozen dataclasses with >15 fields must decompose into named sub-objects
- M005 When same extraction pattern appears at 3+ call sites, promote to method on source object

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
