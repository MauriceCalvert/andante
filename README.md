# Andante

Baroque music generator. Produces two-voice galant-schema compositions as MIDI/MusicXML. Python, no ML. Deterministic builder driven by stochastic planner.

## Pipeline

```
L1 Rhetorical  -> trajectory, rhythm_vocab, tempo
L2 Tonal       -> tonal_plan, density, modality
L3 Schematic   -> SchemaChain (schemas, key_areas, free_passages)
L4 Metric      -> bar_assignments, anchors, total_bars
L5 Phrase Plan -> tuple[PhrasePlan, ...]
L6 Phrase Write-> PhraseResult (upper_notes, lower_notes)
L7 Composition -> Composition (voices, notes, MIDI)
```

L1-L4 = planner (stochastic, `planner/`). L5-L7 = builder (deterministic, `builder/`). RNG forbidden in builder. Orchestrator: `planner/planner.py`.

## Schemas (Gjerdingen)

Named soprano+bass degree skeletons. Degrees signed for approach direction. First degree unsigned.

| Schema | Position | Soprano | Bass |
|--------|----------|---------|------|
| do_re_mi | opening | 1 +2 +3 | 1 -7 +1 |
| romanesca | opening | 3 +5 -1 +3 +6 -5 | 1 -7 -6 -5 -4 -3 |
| meyer | opening | 1 -7 -4 -3 | 1 +2 -7 +1 |
| sol_fa_mi | opening | 5 -4 -3 | 1 -2 -3 |
| prinner | continuation | 6 -5 -4 -3 | 4 -3 -2 -1 |
| fonte | continuation | sequential | sequential |
| monte | continuation | sequential | sequential |
| fenaroli | continuation | 7 -1 -4 -3 | 1 -7 -2 -1 |
| ponte | continuation | 2 2 | 5 5 |
| passo_indietro | pre-cadential | varies | varies |
| indugio | pre-cadential | 1 1 | 5 5 |
| cadenza_semplice | cadential | 2 -1 | 5 +1 |
| cadenza_composta | cadential | 4 -3 -2 -1 | 5 +1 |
| comma | cadential | 7 +1 | 4 -5 +1 |
| half_cadence | cadential | varies | -> 5 |
| quiescenza | post-cadential | 1 1 | 1 1 |

Cadential schemas use `builder/cadence_writer.py` with fixed clausula templates. All others use `builder/phrase_writer.py`.

## Pitch Representations

```
FloatingNote  (degree 1-7, no octave)  -- schema patterns
DiatonicPitch (linear step, unbounded) -- key-relative arithmetic
MidiPitch     (0-127)                  -- output
Key           (tonic + mode)           -- conversion hub
```

Resolution: FloatingNote -> DiatonicPitch -> MIDI (via Key). All in `shared/`.

## Duration System

All durations: `Fraction` of whole note. Valid: 1, 3/4, 1/2, 3/8, 1/4, 3/16, 1/8, 3/32, 1/16, 1/32. No floats. No quantisation. Arithmetic via `shared/music_math.py` only. MIDI gate: 95% (GATE_FACTOR = 19/20).

## Voice Model

Two schema voices: SCHEMA_UPPER (soprano, idx 0) and SCHEMA_LOWER (bass, idx 3). Ranges MIDI: soprano 55-84, bass 36-62. MIN_BASS_MIDI=40. Voice crossing soprano/bass forbidden. Additional roles: IMITATIVE, HARMONY_FILL.

Types in `shared/voice_types.py`: Voice, Actuator, Range, Role, InstrumentDef, ScoringAssignment, TrackAssignment.

## Key Types

| Type | Module | Contains |
|------|--------|----------|
| PhrasePlan | builder/phrase_types.py | schema, anchors, key, metre, genre refs |
| PhraseResult | builder/phrase_types.py | upper_notes, lower_notes |
| Schema | shared/schema_types.py | soprano/bass degrees, segments, position |
| Composition | builder/types.py | voices, notes, metadata |
| GenreConfig | builder/types.py | voices, instruments, form, metre, sections |
| Key | shared/key.py | tonic, mode, degree<->MIDI conversion |
| Note | builder/types.py | pitch, start, duration, voice |

## Design Principles

1. **Phrase is unit** -- one schema = one phrase, not assembled from fragments
2. **Genre defines rhythm** -- idiomatic cells per genre, not universal diminution
3. **Counterpoint inline** -- bass generated with soprano awareness, not post-hoc
4. **Cadences formulaic** -- fixed clausula templates, not strategy lookups
5. **Soprano first, bass fitted** -- matches baroque practice

## Genres

bourree, chorale, fantasia, gavotte, invention, minuet, sarabande, trio_sonata. Configs in `data/genres/*.yaml`. Fields: voices, metre, form, upbeat, sections[], characteristic_rhythms[].

## Laws (40+ rules)

Architecture: A001 no if-chains, A002 same engine, A003 rules=YAML, A004 repeats=performance, A005 RNG planner only, A006 ports/adapters.

Design: D001 validate don't fix, D002 constraints up, D003 trace without source, D004 separate melodic/harmonic, D005 compute from budget, D006 asymmetric motifs, D008 no downstream fixes, D009 use phrase_index, D010 guards detect generators prevent.

Code: L001 no try/except, L002 no magic numbers, L003 no hard range, L004 crossing soprano/bass forbidden, L005 duration via music_math, L006 valid durations only, L007 natural minor (raised 6/7 cadential only), L008-L009 tonal targets=functions, L010 leading tone cadences only, L011 while needs guards, L012 no quantisation, L013 gate 95%, L014 clone before modify, L015 dataclass not tuple, L016 logging not print, L017 single source of truth, L018 empty __init__.py, L019 ASCII only, L020 kwargs only.

Anti-patterns: X001-X005 no post-hoc pitch adjustment, no fix loops, no global sig tracking, no separate fix passes, no rep counter reset.

## Guard System

| Module | Scope |
|--------|-------|
| builder/faults.py | Post-composition: parallels, dissonance, leaps, cross-relations, tessitura, spacing, overlap |
| builder/junction.py | Gap boundary checks |
| builder/phrase_writer.py | Inline counterpoint during generation |

Guards detect, never fix (D010). Faults report only.

## Source Map

```
planner/
  planner.py          orchestrator, generate()
  rhetorical.py       L1
  tonal.py            L2
  schematic.py         L3
  metric/layer.py     L4
  metric/pitch.py     anchor pitch assignment
  metric/schema_anchors.py  schema->anchor expansion
  metric/distribution.py    bar distribution
  plannertypes.py     planner-internal types
  harmony.py          harmonic helpers
  constraints.py      planning constraints

builder/
  compose.py          L7: phrase-by-phrase composition
  phrase_planner.py   L5: build PhrasePlans
  phrase_writer.py    L6: per-phrase note generation
  phrase_types.py     PhrasePlan, PhraseResult
  cadence_writer.py   cadential voice-leading templates
  rhythm_cells.py     rhythm cell patterns
  config_loader.py    YAML config loading
  figuration/         bass figuration (loader, bass, rhythm_calc, types)
  faults.py           post-composition fault scan
  junction.py         gap boundary validation
  types.py            Note, Composition, GenreConfig, SchemaConfig
  io.py               MIDI/MusicXML/.note output
  musicxml_writer.py  MusicXML serialization

shared/
  constants.py        all symbolic constants
  key.py              Key class
  pitch.py            FloatingNote, MidiPitch, place_degree, select_octave
  diatonic_pitch.py   DiatonicPitch
  voice_types.py      Voice, Actuator, Role, Range
  music_math.py       duration arithmetic, fill_slot
  schema_types.py     unified Schema type
  yaml_parsing.py     parse_signed_degree, parse_typical_keys
  midi_writer.py      low-level MIDI
  tracer.py           debug trace

motifs/
  subject_loader.py   .subject file loading
  subject_generator.py subject generation
  answer_generator.py tonal/real answers
  countersubject_generator.py
  melodic_features.py feature extraction
  figurae.py          rhetorical figures

scripts/
  run_pipeline.py     CLI entry point
  run_showcase.py     batch generation
  yaml_validator.py   YAML validation

data/
  schemas/            schema definitions + transitions
  genres/             per-genre configs
  figuration/         diminutions, patterns, profiles, rhythms
  forms/              binary, strophic, through_composed
  rhetoric/           affects, archetypes, figurae, tension
  rules/              counterpoint_rules, constraints
  instruments/        instrument definitions
  treatments/         schema slot treatments
  humanisation/       timing/velocity variation
```

## YAML Data

All rules are data (A003). Schema definitions: `data/schemas/schemas.yaml`. Genre configs: `data/genres/{name}.yaml`. Counterpoint rules: `data/rules/counterpoint_rules.yaml`. Diminution patterns: `data/figuration/`. Form structures: `data/forms/`. Rhetorical affects: `data/rhetoric/affects.yaml`.

## Consonance Constants

Perfect: {0, 7} (unison, P5). Imperfect: {3, 4, 8, 9} (3rds, 6ths). Dissonant: {1, 11} (m2, M7). Strong-beat forbidden: {1, 2, 6, 10, 11}. Parallel motion on perfect intervals forbidden. P4 dissonant above bass.

## Gotchas

- Schema degrees 1-7; DiatonicPitch.step 0-based. Convert via `.degree`.
- Schema.segments is always `tuple[int, ...]`, never int. Use `max(segments)` for bar count.
- `_motion_type` returns "similar"/"oblique"/"contrary"/"static", never "parallel".
- GenreConfig.upbeat defaults to Fraction(0).
- Phrase start_offset from cumulative bar_spans, never anchor bar_beats.
- Natural minor for melody; raised 6th/7th only at cadences (L007).
- Leading tone for cadences only; bass avoids degree 7 (L010).
- All arguments by keyword (L020). All durations Fraction. All constants in shared/constants.py.
