# Andante Machine Knowledge

_Claude: read at chat start. Dense reference — no rationale. For "why", see human docs._

---

## Pipeline

| Layer | Module | Input | Output |
|-------|--------|-------|--------|
| 1 Rhetorical | `planner/rhetorical.py` | GenreConfig | trajectory, rhythm_vocab, tempo |
| 2 Tonal | `planner/tonal.py` | AffectConfig | tonal_plan, density, modality |
| 3 Schematic | `planner/schematic.py` | tonal_plan, GenreConfig, FormConfig, schemas | SchemaChain (schemas, key_areas, free_passages) |
| 4 Metric | `planner/metric/layer.py` | SchemaChain, configs, tonal_plan | bar_assignments, anchors, total_bars |
| 5 Phrase Planning | `builder/phrase_planner.py` | SchemaChain, anchors, GenreConfig, schemas | tuple[PhrasePlan, ...] |
| 6 Phrase Writing | `builder/phrase_writer.py` | PhrasePlan, PhraseContext | PhraseResult (upper_notes, lower_notes) |
| 7 Composition | `builder/compose.py` | PhrasePlans, home_key, metre, tempo, upbeat | Composition (voices, notes) |

Orchestrator: `planner/planner.py` — calls layers 1-4, then phrase planning + `compose_phrases()`.

---

## Design Principles

1. **Phrase is the unit of composition** — one schema = one phrase, not assembled from gap fragments
2. **Genre defines rhythmic vocabulary** — idiomatic rhythm cells per genre, not a universal diminution table
3. **Counterpoint checked inline** — bass generated with soprano awareness, not post-hoc
4. **Cadences are formulaic** — fixed clausula templates in cadence_writer, not strategy lookups
5. **Soprano first, bass fitted** — matches baroque compositional practice

---

## Execution Model

`compose_phrases()` iterates over PhrasePlans in order.
Each phrase dispatched to `write_phrase()` which produces upper and lower notes.
Exit pitches thread between consecutive phrases for voice continuity.

The phrase writer (`builder/phrase_writer.py`) realises each phrase from its schema anchors,
generating notes for soprano and bass voices with inline counterpoint checking.

Cadential schemas (cadenza_semplice, cadenza_composta, half_cadence, comma) use
`builder/cadence_writer.py` with fixed voice-leading templates instead of the phrase
generation algorithm.

---

## Voice Model

| Type | Module | Role |
|------|--------|------|
| `Voice` | `shared/voice_types.py` | id, Role enum, follows/delay/interval |
| `Actuator` | `shared/voice_types.py` | id, Range(low, high) MIDI |
| `InstrumentDef` | `shared/voice_types.py` | id, tuple[Actuator] |
| `ScoringAssignment` | `shared/voice_types.py` | voice_id -> instrument_id.actuator_id |
| `TrackAssignment` | `shared/voice_types.py` | voice_id -> MIDI channel + program |

### Role Enum

| Role | Meaning |
|------|---------|
| SCHEMA_UPPER | Upper voice realises schema soprano degrees |
| SCHEMA_LOWER | Lower voice realises schema bass degrees |
| IMITATIVE | Follows another voice (requires follows, follow_interval, follow_delay) |
| HARMONY_FILL | Inner voice filling harmony |

### Voice Ranges (MIDI)

| Index | Voice | Low | High | Default Median |
|-------|-------|-----|------|----------------|
| 0 | Soprano | 55 (G3) | 84 (C6) | 70 (Bb4) |
| 1 | Alto | 50 (D3) | 74 (D5) | 60 (C4) |
| 2 | Tenor | 45 (A2) | 69 (A4) | 54 (F#3) |
| 3 | Bass | 36 (C2) | 62 (D4) | 48 (C3) |

---

## Pitch Representations

| Type | Module | Space | Use |
|------|--------|-------|-----|
| `FloatingNote` | `shared/pitch.py` | degree 1-7, no octave | Schema degrees, figuration patterns |
| `DiatonicPitch` | `shared/diatonic_pitch.py` | linear step count, unbounded | Key-relative pitch |
| `MidiPitch` | `shared/pitch.py` | MIDI 0-127 | Direct MIDI, external import |
| `Key` | `shared/key.py` | tonic + mode | Conversion hub: degree <-> MIDI <-> diatonic |

Resolution chain: FloatingNote -> DiatonicPitch -> MIDI (via Key).

---

## Plan Types

### Planner -> Builder contract

Phrase plans in `builder/phrase_types.py`. Frozen dataclasses.

| Type | Contains |
|------|----------|
| `PhrasePlan` | schema, anchors, key, metre, genre config references |
| `PhraseResult` | upper_notes, lower_notes |

### Planner-internal types

In `planner/plannertypes.py`. Used within planning layers only.

---

## Schemas (data/schemas/schemas.yaml)

| Schema | Position | Cadential | Soprano | Bass |
|--------|----------|-----------|---------|------|
| do_re_mi | opening | open | 1 +2 +3 | 1 -7 +1 |
| romanesca | opening | open | 3 +5 -1 +3 +6 -5 | 1 -7 -6 -5 -4 -3 |
| meyer | opening | open | 1 -7 -4 -3 | 1 +2 -7 +1 |
| sol_fa_mi | opening | open | 5 -4 -3 | 1 -2 -3 |
| prinner | continuation | open | 6 -5 -4 -3 | 4 -3 -2 -1 |
| fonte | continuation | open | sequential | sequential |
| monte | continuation | open | sequential | sequential |
| fenaroli | continuation | open | 7 -1 -4 -3 | 1 -7 -2 -1 |
| ponte | continuation | open | 2 2 | 5 5 |
| passo_indietro | pre-cadential | preparing | varies | varies |
| indugio | pre-cadential | preparing | 1 1 | 5 5 |
| cadenza_semplice | cadential | closed | 2 -1 | 5 +1 |
| cadenza_composta | cadential | closed | 4 -3 -2 -1 | 5 +1 |
| comma | cadential | closed | 7 +1 | 4 -5 +1 |
| half_cadence | cadential | half | varies | -> 5 |
| quiescenza | post-cadential | closed | 1 1 | 1 1 |

Degrees: signed = approach direction. Sequential schemas transpose per segment.

---

## Genre Config (data/genres/*.yaml)

Fields: name, voices[], instruments[], scoring{}, tracks{}, form, metre, rhythmic_unit, tempo, bass_treatment, sections[].
Each section: name, schema_sequence[], lead_voice, accompany_texture.
Available genres: bourree, chorale, fantasia, gavotte, invention, minuet, sarabande, trio_sonata.

---

## YAML Data Map

| Directory | Files | Drives |
|-----------|-------|--------|
| `data/figuration/` | diminutions, patterns, profiles, rhythms | phrase_writer, bass |
| `data/forms/` | binary, strophic, through_composed | Layer 3 structure |
| `data/genres/` | per-genre configs + _default | Layer 1, config_loader |
| `data/humanisation/` | timing/velocity variation | MIDI output |
| `data/instruments/` | instrument definitions | genre config |
| `data/rhetoric/` | affects, archetypes, figurae, tension | Layers 1-2 |
| `data/rules/` | constraints, counterpoint_rules | faults |
| `data/schemas/` | schemas, transitions | Layer 3-4 |
| `data/treatments/` | treatments.yaml | schema slot treatments |

---

## Guard System

| Module | Scope |
|--------|-------|
| `builder/faults.py` | Post-composition fault scan (parallels, dissonance, leaps, cross-relations, tessitura, spacing, overlap) |
| `builder/junction.py` | Gap boundary checks |
| `builder/soprano_writer.py` | Inline soprano counterpoint checks |
| `builder/bass_writer.py` | Inline bass counterpoint checks (parallels, cross-relations, leaps) |

Guards detect, generators prevent (D010). Faults report; never fix.

---

## Source File Map

### planner/
| File | Responsibility |
|------|---------------|
| `planner.py` | Orchestrator, generate() entry point |
| `rhetorical.py` | L1: genre -> trajectory, rhythm, tempo |
| `tonal.py` | L2: affect -> tonal plan, density, modality |
| `schematic.py` | L3: tonal plan -> schema chain |
| `schema_loader.py` | Parse schemas.yaml into SchemaConfig |
| `metric/layer.py` | L4: schemas -> bar assignments + anchors |
| `metric/pitch.py` | Anchor pitch assignment |
| `metric/schema_anchors.py` | Schema -> anchor expansion |
| `metric/distribution.py` | Bar distribution across schemas |
| `metric/constants.py` | Metric layer constants |
| `phrase_harmony.py` | Phrase-level harmony |
| `arc.py` | Trajectory arc |
| `dramaturgy.py` | Key suggestion from affect |
| `frame.py` | Frame-level planning |
| `material.py` | Material assignments |
| `variety.py` | Variety/variation helpers |
| `subject.py` | Subject handling in planning |
| `subject_deriver.py` | Subject derivation |
| `subject_validator.py` | Subject validation |
| `cs_generator.py` | Counter-subject generation |
| `devices.py` | Compositional devices |
| `koch_rules.py` | Koch's phrase rules |
| `serializer.py` | Plan serialization |
| `plannertypes.py` | Planner-internal types |
| `motif_loader.py` | Load motifs for planning |

### builder/
| File | Responsibility |
|------|---------------|
| `compose.py` | Phrase-by-phrase composition entry point |
| `phrase_planner.py` | Build PhrasePlans from L4 output |
| `phrase_writer.py` | Thin orchestrator: dispatches to soprano_writer, bass_writer, cadence_writer |
| `soprano_writer.py` | Soprano note generation with inline counterpoint checks |
| `bass_writer.py` | Bass note generation (patterned, pillar, walking) with counterpoint |
| `cadence_writer.py` | Cadence note generation from clausula templates |
| `phrase_types.py` | PhrasePlan, PhraseResult types |
| `rhythm_cells.py` | Rhythm cell patterns |
| `config_loader.py` | Load all YAML configs |
| `figuration/loader.py` | Load diminution tables |
| `figuration/bass.py` | Bass figuration |
| `figuration/rhythm_calc.py` | Rhythm calculation for figurations |
| `figuration/types.py` | Figuration types |
| `faults.py` | Post-composition fault detection |
| `junction.py` | Gap boundary validation |
| `types.py` | Builder domain types (Note, Composition, SchemaConfig, GenreConfig, etc.) |
| `io.py` | Write MIDI, MusicXML; shared note helpers (all_notes_sorted, bar_beat, note_name) |
| `note_writer.py` | Write enriched .note CSV with degree/harmony/phrase/cadence |
| `musicxml_writer.py` | MusicXML output |

### shared/
| File | Responsibility |
|------|---------------|
| `constants.py` | All symbolic constants |
| `key.py` | Key class: degree/MIDI/diatonic conversion |
| `pitch.py` | FloatingNote, MidiPitch, Rest, place_degree, select_octave |
| `diatonic_pitch.py` | DiatonicPitch (linear step, key-relative) |
| `schema_types.py` | Schema-related shared types |
| `voice_types.py` | Voice, Actuator, Range, Role, Instrument, Scoring, Track |
| `music_math.py` | Duration arithmetic, fill_slot, valid durations |
| `midi_writer.py` | Low-level MIDI writing |
| `yaml_parsing.py` | YAML loading and parsing utilities |
| `errors.py` | Custom exceptions |
| `tracer.py` | Debug trace output |

### motifs/
| File | Responsibility |
|------|---------------|
| `fugue_loader.py` | Load .fugue files (LoadedFugue) |
| `subject_generator.py` | Generate fugue subjects |
| `answer_generator.py` | Generate tonal/real answers |
| `countersubject_generator.py` | Generate counter-subjects |
| `head_generator.py` | Subject head motifs |
| `tail_generator.py` | Subject tail motifs |
| `enumerator.py` | Enumerate motif variants |
| `melodic_features.py` | Feature extraction |
| `figurae.py` | Rhetorical figures |
| `affect_loader.py` | Load affect configs |
| `extract_melodies.py` | MIDI melody extraction |

### scripts/
| File | Purpose |
|------|---------|
| `run_pipeline.py` | Main CLI entry point |
| `run_showcase.py` | Generate showcase pieces |
| `run_pipeline_coverage.py` | Pipeline run with coverage reporting |
| `full_tests.py` | Run full test suite |
| `generate_subjects.py` | Batch subject generation |
| `generate_heads.py` | Batch head generation |
| `yaml_validator.py` | Validate YAML data files |
| `midi_to_note.py` | MIDI -> .note conversion |
| `note_to_midi.py` | .note -> MIDI conversion |
| `note_to_subject.py` | .note -> subject format |
| `subject_to_midi.py` | Subject -> MIDI rendering |

---

## Duration System

All durations: `Fraction` of a whole note. Arithmetic via `shared/music_math.py` only (L005).

Valid durations: 1, 3/4, 1/2, 3/8, 1/4, 3/16, 1/8, 3/32, 1/16, 1/32.
No quantisation (L012). No division to create durations (L006).
MIDI gate: 95% of notated duration (L013, GATE_FACTOR = 19/20).

---

## Key Constraints (from laws.md, as code assertions)

- Natural minor for melodic content; raised 6/7 only at cadences (L007)
- Tonal targets = harmonic functions, not modulations (L008, L009)
- Leading tone reserved for subject cadences; bass avoids degree 7 (L010)
- No try/except (L001), no magic numbers (L002), no hard range constraints (L003)
- Voice crossing allowed (L004)
- No downstream fixes (D008, X001-X006); fix at generator
- RNG in planner only; executor deterministic (A005)
- Rules are YAML data, not code (A003)
- Single source of truth (L017)
- Assert preconditions, not if/raise
- Empty `__init__.py` files (L018)
- ASCII only (L019)

---

## CLI

```
python -m scripts.run_pipeline <genre> <affect> [key] [-o DIR] [-trace]
```

Positional args, not flags. Examples:
- `python -m scripts.run_pipeline minuet default c_major -o output -trace`
- `python -m scripts.run_pipeline gavotte default g_major -o output -trace`

---

## Active Gotchas

1. **Degree indexing**: schemas use 1-7; DiatonicPitch.step is 0-based linear. Conversion via `.degree` property.
2. **Schema degrees are signed**: `+2` means "up to degree 2", `-7` means "down to degree 7". First degree unsigned.
3. **Key.diatonic_step()** counts scale steps, not semitones. For chromatic movement, use MIDI arithmetic.
4. **Fraction arithmetic**: always import from `fractions`. Never use float for durations.
5. **Bass MIN_BASS_MIDI = 40 (E2)**: floor for bass voice, but not a hard range clamp (L003).
