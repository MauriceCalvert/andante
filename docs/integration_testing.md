# Integration Testing Design

Specifies layer interfaces and contract tests for the redesigned Andante
pipeline. Every layer boundary has a typed interface and a set of
postconditions. Tests verify postconditions in isolation using fixtures,
without invoking adjacent layers.

---

## Test Pyramid

```
Level 0  Unit tests           function-level correctness (existing)
Level 1  Layer contract tests  one layer's output satisfies all postconditions
Level 2  Boundary tests        output of layer N is valid input for layer N+1
Level 3  System tests          full pipeline produces valid .note file
```

Level 1 is the new tier. Each test takes a single layer's output (from a
fixture or from calling only that layer) and checks every postcondition.
No other layer runs.

---

## Layer Inventory

| Layer | Module | Input interface | Output interface |
|-------|--------|-----------------|------------------|
| L1 Rhetorical | `planner/rhetorical.py` | `GenreConfig` | `L1Output` |
| L2 Tonal | `planner/tonal.py` | `AffectConfig, GenreConfig` | `TonalPlan` |
| L3 Schematic | `planner/schematic.py` | `TonalPlan, GenreConfig, FormConfig, schemas` | `SchemaChain` |
| L4 Metric | `planner/metric/layer.py` | `SchemaChain, GenreConfig, FormConfig, KeyConfig, schemas, TonalPlan` | `MetricOutput` |
| L5 Phrase Planning | `builder/phrase_planner.py` (new) | `MetricOutput, GenreConfig, schemas` | `tuple[PhrasePlan, ...]` |
| L6 Phrase Writing | `builder/phrase_writer.py` (new) | `PhrasePlan, PhraseContext` | `PhraseResult` |
| L7 Compose | `builder/compose.py` (revised) | `tuple[PhraseResult, ...], metre, upbeat` | `Composition` |
| Fault scan | `builder/faults.py` (unchanged) | `Composition` | `list[Fault]` |

---

## Interfaces

### Existing types (unchanged)

These are defined in `shared/` and `builder/types.py`. Listed here for
reference so each layer's contract can be stated precisely.

```
GenreConfig         builder/types.py    frozen dataclass
AffectConfig        builder/types.py    frozen dataclass
FormConfig          builder/types.py    frozen dataclass
KeyConfig           builder/types.py    frozen dataclass
SchemaConfig        builder/types.py    frozen dataclass
TonalPlan           builder/types.py    frozen dataclass
SectionTonalPlan    builder/types.py    frozen dataclass
SchemaChain         builder/types.py    frozen dataclass
Anchor              builder/types.py    frozen dataclass
Note                builder/types.py    frozen dataclass
Composition         builder/types.py    frozen dataclass
Fault               builder/faults.py   frozen dataclass
Key                 shared/key.py       frozen dataclass
DiatonicPitch       shared/diatonic_pitch.py  frozen dataclass
Range               shared/voice_types.py     frozen dataclass
Role                shared/voice_types.py     enum
```

### L1Output (formalise existing return tuple)

```python
@dataclass(frozen=True)
class L1Output:
    trajectory: tuple[str, ...]     # section names in order
    rhythm_vocab: dict[str, str]    # at minimum {"rhythmic_unit": "1/16"}
    tempo: int                      # BPM
```

Currently returned as a bare tuple. Wrapping it gives a testable contract.

### MetricOutput (formalise existing return tuple)

```python
@dataclass(frozen=True)
class MetricOutput:
    bar_assignments: dict[str, tuple[int, int]]   # section_name -> (start_bar, end_bar)
    anchors: tuple[Anchor, ...]
    total_bars: int
```

Currently returned as a bare tuple. Same rationale.

### New types

#### BeatPosition

```python
@dataclass(frozen=True)
class BeatPosition:
    bar: int        # 1-based bar number relative to phrase start
    beat: int       # 1-based beat within bar
```

Maps each schema degree to where it must appear in the phrase.

#### PhrasePlan

```python
@dataclass(frozen=True)
class PhrasePlan:
    schema_name: str
    degrees_upper: tuple[int, ...]          # soprano schema degrees (1-7)
    degrees_lower: tuple[int, ...]          # bass schema degrees (1-7)
    degree_positions: tuple[BeatPosition, ...]  # one per degree stage
    local_key: Key
    bar_span: int                           # how many bars this phrase covers
    start_bar: int                          # absolute bar number (1-based)
    start_offset: Fraction                  # absolute offset in whole notes
    phrase_duration: Fraction               # total duration in whole notes
    metre: str
    rhythm_profile: str                     # genre rhythm vocabulary name
    is_cadential: bool                      # True for cadential schemas
    cadence_type: str | None                # "authentic", "half", etc. or None
    prev_exit_upper: int | None             # MIDI pitch, None for first phrase
    prev_exit_lower: int | None             # MIDI pitch, None for first phrase
    section_name: str                       # which genre section this belongs to
    upper_range: Range                      # soprano actuator range
    lower_range: Range                      # bass actuator range
    upper_median: int                       # soprano tessitura median (MIDI)
    lower_median: int                       # bass tessitura median (MIDI)
```

One per schema in the chain. Fully specifies what the phrase writer needs.

#### PhraseContext

```python
@dataclass(frozen=True)
class PhraseContext:
    home_key: Key
    completed_upper: tuple[Note, ...]       # all soprano notes so far
    completed_lower: tuple[Note, ...]       # all bass notes so far
```

Running context passed to phrase writer. Enables counterpoint checking
against previously composed phrases.

#### PhraseResult

```python
@dataclass(frozen=True)
class PhraseResult:
    upper_notes: tuple[Note, ...]
    lower_notes: tuple[Note, ...]
    exit_upper: int                         # final soprano MIDI pitch
    exit_lower: int                         # final bass MIDI pitch
    schema_name: str
    faults: tuple[str, ...]                 # any internal warnings
```

Output of phrase writer. One per phrase. Compose concatenates these.

---

## Layer Contracts and Tests

Each subsection states the postconditions and lists every test.
Test names are final — they become `def test_<name>()` in the test file.

### L1 Rhetorical

**File**: `tests/test_L1_rhetorical.py`
**Fixture input**: `GenreConfig` for each genre in `data/genres/`
**Execution**: call `layer_1_rhetorical(genre_config)` directly

#### Postconditions

| ID | Condition |
|----|-----------|
| L1-01 | tempo is int > 0 |
| L1-02 | tempo is within 40..200 |
| L1-03 | rhythm_vocab is non-empty dict |
| L1-04 | rhythm_vocab["rhythmic_unit"] is a string parseable as a Fraction |
| L1-05 | trajectory length == len(genre_config.sections) |
| L1-06 | every trajectory entry matches its genre section name |

#### Tests

```
test_tempo_positive                  L1-01
test_tempo_plausible_range           L1-02
test_rhythm_vocab_nonempty           L1-03
test_rhythmic_unit_valid_fraction    L1-04
test_trajectory_length               L1-05
test_trajectory_matches_sections     L1-06
```

All parametrised over every genre YAML.

---

### L2 Tonal

**File**: `tests/test_L2_tonal.py`
**Fixture input**: `AffectConfig`, `GenreConfig` per genre
**Execution**: call `layer_2_tonal(affect_config, genre_config)` directly

#### Postconditions

| ID | Condition |
|----|-----------|
| L2-01 | output is TonalPlan |
| L2-02 | len(sections) == len(genre_config.sections) |
| L2-03 | every section.name matches corresponding genre section name |
| L2-04 | every section.key_area is in VALID_KEY_AREAS |
| L2-05 | every section.cadence_type is in TONAL_CADENCE_TYPES |
| L2-06 | final section.cadence_type == "authentic" |
| L2-07 | first section.key_area == "I" |
| L2-08 | final section.key_area == "I" |
| L2-09 | no two consecutive identical non-tonic key areas |
| L2-10 | no two consecutive half cadences |
| L2-11 | at most one interior authentic cadence |
| L2-12 | density is in {"low", "medium", "high"} |
| L2-13 | modality is in {"diatonic", "chromatic"} |

#### Tests

```
test_output_type                     L2-01
test_section_count                   L2-02
test_section_names_match             L2-03
test_key_areas_valid                 L2-04
test_cadence_types_valid             L2-05
test_final_cadence_authentic         L2-06
test_first_key_tonic                 L2-07
test_final_key_tonic                 L2-08
test_no_consecutive_nontonic         L2-09
test_no_consecutive_half_cadences    L2-10
test_interior_authentic_limit        L2-11
test_density_valid                   L2-12
test_modality_valid                  L2-13
```

Parametrised over genre x affect combinations.

---

### L3 Schematic

**File**: `tests/test_L3_schematic.py`
**Fixture input**: `TonalPlan, GenreConfig, FormConfig, schemas` per genre
**Execution**: call `layer_3_schematic(...)` directly

#### Postconditions

| ID | Condition |
|----|-----------|
| L3-01 | output is SchemaChain |
| L3-02 | len(schemas) >= 1 |
| L3-03 | every schema name exists in the schema catalogue |
| L3-04 | len(section_boundaries) == len(genre_config.sections) |
| L3-05 | section_boundaries are strictly monotonically increasing |
| L3-06 | section_boundaries[-1] == len(schemas) |
| L3-07 | section_boundaries[0] >= 1 (first section has at least one schema) |
| L3-08 | len(key_areas) == len(schemas) |
| L3-09 | len(cadences) == len(schemas) |
| L3-10 | no two adjacent schemas are identical |
| L3-11 | first schema in the chain has position == "opening" or first section is not "exordium" |
| L3-12 | last schema in any section whose cadence_type is "authentic" has cadential_state in {"closed", "cadential"} |
| L3-13 | every cadence entry is None (non-terminal) or a valid cadence type string |
| L3-14 | exactly one non-None cadence per section (the last schema in that section) |

#### Tests

```
test_output_type                         L3-01
test_chain_nonempty                      L3-02
test_all_schemas_in_catalogue            L3-03
test_boundary_count                      L3-04
test_boundaries_monotonic                L3-05
test_boundaries_tile_chain               L3-06
test_first_section_nonempty              L3-07
test_key_areas_length                    L3-08
test_cadences_length                     L3-09
test_no_adjacent_repetition              L3-10
test_opening_schema_placement            L3-11
test_cadential_schema_at_section_end     L3-12
test_cadence_entries_valid               L3-13
test_one_cadence_per_section             L3-14
```

---

### L4 Metric

**File**: `tests/test_L4_metric.py`
**Fixture input**: all L4 inputs per genre (SchemaChain from L3, etc.)
**Execution**: call `layer_4_metric(...)` directly

#### Postconditions

| ID | Condition |
|----|-----------|
| L4-01 | bar_assignments has one entry per genre section |
| L4-02 | bar_assignments ranges tile 1..total_bars contiguously (no gaps, no overlaps) |
| L4-03 | total_bars >= 1 |
| L4-04 | anchors is a list of Anchor |
| L4-05 | len(anchors) >= 2 (at least start and end) |
| L4-06 | anchors sorted by bar_beat (numerically) |
| L4-07 | no duplicate bar_beat values |
| L4-08 | every anchor.upper_degree in 1..7 |
| L4-09 | every anchor.lower_degree in 1..7 |
| L4-10 | every anchor.local_key is a Key instance |
| L4-11 | first anchor has upper_degree==1, lower_degree==1 |
| L4-12 | last anchor has upper_degree==1, lower_degree==1 |
| L4-13 | first anchor.local_key == home_key |
| L4-14 | last anchor.local_key == home_key |
| L4-15 | every bar number in bar_beat is within 0..total_bars |
| L4-16 | every beat number is >= 1 and <= beats_per_bar for the metre |
| L4-17 | for schemas named "cadenza_semplice" or "cadenza_composta": their final-stage anchor has upper_degree==1, lower_degree==1 |
| L4-18 | for schemas named "half_cadence": their final-stage anchor has lower_degree==5 |

#### Tests

```
test_bar_assignments_complete            L4-01
test_bar_assignments_contiguous          L4-02
test_total_bars_positive                 L4-03
test_anchors_are_anchors                 L4-04
test_anchor_count_minimum                L4-05
test_anchors_sorted                      L4-06
test_anchors_no_duplicates               L4-07
test_upper_degrees_valid                 L4-08
test_lower_degrees_valid                 L4-09
test_local_keys_valid                    L4-10
test_first_anchor_tonic                  L4-11
test_last_anchor_tonic                   L4-12
test_first_anchor_home_key               L4-13
test_last_anchor_home_key                L4-14
test_bar_numbers_in_range                L4-15
test_beat_numbers_valid                  L4-16
test_authentic_cadence_degrees           L4-17
test_half_cadence_bass_degree            L4-18
```

---

### L5 Phrase Planning (new)

**File**: `tests/test_L5_phrase_planner.py`
**Fixture input**: `MetricOutput, GenreConfig, schemas` per genre
**Execution**: call `build_phrase_plans(...)` directly

#### Postconditions

| ID | Condition |
|----|-----------|
| P-01 | output is a tuple of PhrasePlan |
| P-02 | len(phrase_plans) >= 1 |
| P-03 | every phrase_plan.schema_name exists in the schema catalogue |
| P-04 | every phrase_plan.degrees_upper matches the schema's soprano_degrees |
| P-05 | every phrase_plan.degrees_lower matches the schema's bass_degrees |
| P-06 | len(degree_positions) == len(degrees_upper) |
| P-07 | every BeatPosition.bar is in 1..bar_span |
| P-08 | every BeatPosition.beat is in 1..beats_per_bar |
| P-09 | degree_positions are in chronological order |
| P-10 | phrase_plan.bar_span >= 1 |
| P-11 | phrase_plan.phrase_duration == bar_span * bar_length (from metre) |
| P-12 | phrase_plans tile exactly: plan[i+1].start_offset == plan[i].start_offset + plan[i].phrase_duration |
| P-13 | first phrase start_offset == 0 (or == -upbeat for upbeat genres) |
| P-14 | sum of all phrase_duration == total_bars * bar_length |
| P-15 | prev_exit_upper is None only for the first phrase |
| P-16 | prev_exit_lower is None only for the first phrase |
| P-17 | is_cadential == True iff schema has cadential_state in {"closed", "half"} |
| P-18 | cadence_type is not None iff is_cadential is True |
| P-19 | local_key is a valid Key instance |
| P-20 | upper_range.low < upper_range.high |
| P-21 | lower_range.low < lower_range.high |
| P-22 | upper_median is within upper_range |
| P-23 | lower_median is within lower_range |
| P-24 | rhythm_profile is a non-empty string |
| P-25 | section_name matches one of the genre's section names |
| P-26 | start_bar is within 1..total_bars (or 0 for upbeat) |

#### Tests

```
test_output_type                         P-01
test_plans_nonempty                      P-02
test_schema_names_valid                  P-03
test_upper_degrees_match_schema          P-04
test_lower_degrees_match_schema          P-05
test_positions_count                     P-06
test_position_bars_in_range              P-07
test_position_beats_in_range             P-08
test_positions_chronological             P-09
test_bar_span_positive                   P-10
test_phrase_duration_consistent          P-11
test_phrases_tile_exactly                P-12
test_first_phrase_offset                 P-13
test_total_duration_matches_bars         P-14
test_prev_exit_upper_first_only_none     P-15
test_prev_exit_lower_first_only_none     P-16
test_cadential_flag_consistent           P-17
test_cadence_type_consistent             P-18
test_local_key_valid                     P-19
test_upper_range_valid                   P-20
test_lower_range_valid                   P-21
test_upper_median_in_range               P-22
test_lower_median_in_range               P-23
test_rhythm_profile_nonempty             P-24
test_section_name_valid                  P-25
test_start_bar_in_range                  P-26
```

---

### L6 Phrase Writer (new)

**File**: `tests/test_L6_phrase_writer.py`
**Fixture input**: `PhrasePlan` + `PhraseContext` per schema type

The phrase writer is tested per phrase, not per piece. Fixtures provide
individual PhrasePlans for representative schemas: one opening (do_re_mi),
one continuation (prinner), one sequential (fonte), one cadential
(cadenza_semplice), one with upbeat.

#### Soprano postconditions

| ID | Condition |
|----|-----------|
| S-01 | output upper_notes is a tuple of Note |
| S-02 | len(upper_notes) >= 1 |
| S-03 | all pitches within upper_range |
| S-04 | all durations in VALID_DURATIONS |
| S-05 | durations sum to exactly phrase_duration |
| S-06 | notes are sorted by offset |
| S-07 | no gaps: note[i].offset + note[i].duration == note[i+1].offset |
| S-08 | no overlaps: note[i].offset + note[i].duration <= note[i+1].offset |
| S-09 | first note offset == phrase_plan.start_offset |
| S-10 | at each degree_position offset, the note's pitch resolves to the correct schema degree (via local_key.midi_to_degree) |
| S-11 | no repeated MIDI pitch across bar boundaries (D007): if note N is the last in bar B and note N+1 is the first in bar B+1, their MIDI pitches differ |
| S-12 | no melodic interval > 12 semitones between consecutive notes |
| S-13 | after a leap (> 4 semitones), the next note moves by step (1-2 semitones) in the contrary direction. Exception: final note of phrase. |
| S-14 | if is_cadential and cadence_type in {"authentic"}: final note's degree == 1 |
| S-15 | if is_cadential and cadence_type == "half": final note's degree == 2 or degree == 7 |
| S-16 | all Note.voice values == soprano track index |

#### Bass postconditions

| ID | Condition |
|----|-----------|
| B-01 | output lower_notes is a tuple of Note |
| B-02 | len(lower_notes) >= 1 |
| B-03 | all pitches within lower_range |
| B-04 | all durations in VALID_DURATIONS |
| B-05 | durations sum to exactly phrase_duration |
| B-06 | notes sorted by offset |
| B-07 | no gaps between consecutive notes |
| B-08 | no overlaps between consecutive notes |
| B-09 | first note offset == phrase_plan.start_offset |
| B-10 | at each degree_position offset, the note's pitch resolves to the correct bass schema degree |
| B-11 | if is_cadential and cadence_type == "authentic": final bass note's degree == 1 |
| B-12 | if is_cadential and cadence_type == "half": final bass note's degree == 5 |
| B-13 | all Note.voice values == bass track index |

#### Counterpoint postconditions (soprano vs bass within this phrase)

| ID | Condition |
|----|-----------|
| CP-01 | no parallel fifths on strong beats: if two consecutive strong-beat offsets have soprano and bass, the interval class must not be 7 at both |
| CP-02 | no parallel octaves on strong beats (same as CP-01 for interval class 0) |
| CP-03 | no parallel unisons on strong beats |
| CP-04 | on every strong beat where both voices sound: interval class (mod 12) is not in STRONG_BEAT_DISSONANT |
| CP-05 | no voice overlap: at no offset does soprano pitch < bass pitch at the same or immediately preceding offset |

#### Result postconditions

| ID | Condition |
|----|-----------|
| R-01 | exit_upper == upper_notes[-1].pitch |
| R-02 | exit_lower == lower_notes[-1].pitch |
| R-03 | schema_name == phrase_plan.schema_name |

#### Tests

```
# Soprano — parametrised over fixture schemas
test_soprano_type                        S-01
test_soprano_nonempty                    S-02
test_soprano_pitches_in_range            S-03
test_soprano_durations_valid             S-04
test_soprano_duration_sum                S-05
test_soprano_sorted                      S-06
test_soprano_no_gaps                     S-07
test_soprano_no_overlaps                 S-08
test_soprano_start_offset                S-09
test_soprano_hits_schema_degrees         S-10
test_soprano_no_cross_bar_repetition     S-11
test_soprano_max_interval                S-12
test_soprano_leap_then_step              S-13
test_soprano_cadential_final_degree      S-14
test_soprano_half_cadence_degree         S-15
test_soprano_voice_index                 S-16

# Bass — parametrised over fixture schemas
test_bass_type                           B-01
test_bass_nonempty                       B-02
test_bass_pitches_in_range               B-03
test_bass_durations_valid                B-04
test_bass_duration_sum                   B-05
test_bass_sorted                         B-06
test_bass_no_gaps                        B-07
test_bass_no_overlaps                    B-08
test_bass_start_offset                   B-09
test_bass_hits_schema_degrees            B-10
test_bass_cadential_final_degree         B-11
test_bass_half_cadence_degree            B-12
test_bass_voice_index                    B-13

# Counterpoint — parametrised over fixture schemas
test_no_parallel_fifths                  CP-01
test_no_parallel_octaves                 CP-02
test_no_parallel_unisons                 CP-03
test_strong_beat_consonance              CP-04
test_no_voice_overlap                    CP-05

# Result — parametrised over fixture schemas
test_exit_upper_matches_last_note        R-01
test_exit_lower_matches_last_note        R-02
test_schema_name_matches                 R-03
```

---

### L7 Compose (revised)

**File**: `tests/test_L7_compose.py`
**Fixture input**: `tuple[PhraseResult, ...]` + metre + upbeat per genre
**Execution**: call `compose_phrases(...)` directly

#### Postconditions

| ID | Condition |
|----|-----------|
| C-01 | output is Composition |
| C-02 | exactly 2 voices in voices dict (for 2-voice genres) |
| C-03 | both voices have len > 0 |
| C-04 | every note has offset >= 0 (or >= -upbeat) |
| C-05 | no note's offset + duration > total_duration |
| C-06 | total_duration == total_bars * bar_length |
| C-07 | notes within each voice sorted by offset |
| C-08 | no overlapping notes within same voice |
| C-09 | no gaps within same voice (note[i] end == note[i+1] start) |
| C-10 | final note offset + duration == total_duration in each voice |
| C-11 | first note offset == -upbeat (or 0 if no upbeat) |
| C-12 | metre matches genre config |
| C-13 | tempo > 0 |
| C-14 | last soprano note degree == 1 in home key |
| C-15 | last bass note degree == 1 in home key |
| C-16 | last soprano pitch == last bass pitch (mod 12) — unison or octave at final |

#### Tests

```
test_output_type                         C-01
test_voice_count                         C-02
test_voices_nonempty                     C-03
test_offsets_nonnegative                 C-04
test_notes_within_duration               C-05
test_total_duration                      C-06
test_voices_sorted                       C-07
test_no_intra_voice_overlap              C-08
test_no_intra_voice_gaps                 C-09
test_final_note_at_end                   C-10
test_first_note_offset                   C-11
test_metre_correct                       C-12
test_tempo_positive                      C-13
test_final_soprano_tonic                 C-14
test_final_bass_tonic                    C-15
test_final_unison_or_octave              C-16
```

---

### Cross-phrase counterpoint

**File**: `tests/test_cross_phrase_counterpoint.py`
**Fixture input**: `Composition` per genre (from full pipeline)

These tests check counterpoint invariants that span phrase boundaries —
things the per-phrase L6 tests cannot catch.

| ID | Condition |
|----|-----------|
| XP-01 | no parallel fifths on any strong beat across the entire piece |
| XP-02 | no parallel octaves on any strong beat across the entire piece |
| XP-03 | no voice overlap at any offset across the entire piece |
| XP-04 | no soprano pitch repeated across any bar boundary (D007, whole piece) |
| XP-05 | no grotesque leaps (> 19 semitones) in either voice |
| XP-06 | no melodic interval > octave at phrase joins (last note of phrase N to first note of phrase N+1) |

#### Tests

```
test_whole_piece_no_parallel_fifths      XP-01
test_whole_piece_no_parallel_octaves     XP-02
test_whole_piece_no_voice_overlap        XP-03
test_whole_piece_no_cross_bar_repeat     XP-04
test_whole_piece_no_grotesque_leaps      XP-05
test_phrase_join_intervals               XP-06
```

---

## Boundary Tests (Level 2)

Boundary tests verify that layer N's output is accepted as valid input by
layer N+1. They run both layers in sequence for a given genre and check
that no assertion fires.

**File**: `tests/test_boundaries.py`

```
test_L1_to_L2          L1 output provides valid GenreConfig context for L2
test_L2_to_L3          L2 TonalPlan accepted by L3
test_L3_to_L4          L3 SchemaChain accepted by L4
test_L4_to_L5          L4 MetricOutput accepted by L5 phrase planner
test_L5_to_L6          L5 PhrasePlans accepted by L6 phrase writer (first phrase)
test_L6_to_L7          L6 PhraseResults accepted by L7 compose
test_L7_to_faults      L7 Composition accepted by fault scanner
```

Each parametrised over every genre.

---

## System Tests (Level 3)

**File**: `tests/test_system.py`

Full pipeline: genre + affect -> .note file. Verifiable properties only.

```
test_generates_output[genre]             both voices non-empty
test_correct_final_degree[genre]         last notes are tonic
test_zero_parallel_perfects[genre]       fault scan: 0 parallel 5ths/8ves
test_zero_grotesque_leaps[genre]         fault scan: 0 grotesque leaps
test_limited_faults[genre]               total faults < threshold (e.g. 10)
test_duration_integrity[genre]           no gaps or overlaps in either voice
test_genre_rhythmic_character[minuet]    >50% of soprano notes are crotchets
test_genre_rhythmic_character[gavotte]   >30% of soprano notes are quaver pairs
test_genre_rhythmic_character[invention] voices not homorhythmic >70% of the time
```

---

## Fixture Strategy

### Capture fixtures

Each layer test has a helper that runs the pipeline up to that layer and
serialises the output as JSON in `tests/fixtures/`. File naming:

```
tests/fixtures/L2_minuet.json       TonalPlan for minuet
tests/fixtures/L3_minuet.json       SchemaChain for minuet
tests/fixtures/L4_minuet.json       MetricOutput for minuet
tests/fixtures/L5_minuet.json       tuple[PhrasePlan] for minuet
tests/fixtures/L6_do_re_mi.json     PhraseResult for do_re_mi in C major 3/4
tests/fixtures/L6_cadenza_semplice.json  PhraseResult for cadenza_semplice
```

### Fixture generation script

`scripts/generate_fixtures.py` — runs the pipeline for each genre, captures
each layer's output, writes fixtures. Run once after any planner change.

### Fixture freshness

Contract tests have two modes:
1. **Fixture mode** (default): load fixture, check postconditions. Fast, no
   pipeline dependency. Used in CI.
2. **Live mode** (`--live` flag): run the actual layer, check postconditions.
   Slower, catches regressions that fixtures mask.

---

## Regression Protocol

When a system test fails:

1. Identify which layer's postcondition is violated (run contract tests).
2. Capture the failing layer's input as a new fixture in
   `tests/fixtures/regression/`.
3. Add a contract test that reproduces the specific violation.
4. Fix the layer.
5. Verify the contract test passes.
6. Verify the system test passes.
7. Commit the regression fixture — it stays permanently.

---

## Test Parametrisation

### Genres

All contract tests for L1-L5 and L7 are parametrised over:

```python
GENRES: tuple[str, ...] = ("bourree", "gavotte", "invention", "minuet", "sarabande")
```

Genres without working output (chorale, fantasia, trio_sonata) are excluded
until their genre configs are complete. The list lives in
`tests/conftest.py` and is updated as genres come online.

### Affects

L2 tests are additionally parametrised over a representative affect set:

```python
AFFECTS: tuple[str, ...] = ("Zierlich", "Zaertlichkeit", "Freudigkeit", "Dolore")
```

### Schema fixtures for L6

L6 phrase writer tests are parametrised over representative schema types:

```python
SCHEMA_FIXTURES: tuple[str, ...] = (
    "do_re_mi",           # opening, 2-bar, stepwise ascent
    "prinner",            # riposte, 2-bar, stepwise descent
    "fonte",              # sequential, 2-segment
    "cadenza_semplice",   # cadential, 1-bar
    "half_cadence",       # half cadence, 1-bar
    "romanesca",          # long opening, 4-bar
)
```

Each in both 4/4 and 3/4 metres.

---

## Invariant Helper Functions

Shared test utilities in `tests/helpers.py`:

```python
def bar_of(offset: Fraction, metre: str, upbeat: Fraction) -> int
    """Convert offset to bar number."""

def beat_of(offset: Fraction, metre: str, upbeat: Fraction) -> int
    """Convert offset to beat within bar."""

def is_strong_beat(offset: Fraction, metre: str) -> bool
    """True if offset falls on beat 1."""

def degree_at(midi: int, key: Key) -> int
    """Convert MIDI to scale degree 1-7."""

def interval_class(a: int, b: int) -> int
    """abs(a - b) % 12"""

def check_no_parallel(
    upper: tuple[Note, ...],
    lower: tuple[Note, ...],
    metre: str,
    forbidden_ic: frozenset[int],
) -> list[str]
    """Return list of violation descriptions."""

def check_no_voice_overlap(
    upper: tuple[Note, ...],
    lower: tuple[Note, ...],
) -> list[str]
    """Return list of violation descriptions."""

def notes_at_offsets(
    notes: tuple[Note, ...],
) -> dict[Fraction, Note]
    """Index notes by offset for lookup."""
```

---

## Execution Order

```
pytest tests/test_L1_rhetorical.py      # must pass first
pytest tests/test_L2_tonal.py
pytest tests/test_L3_schematic.py
pytest tests/test_L4_metric.py
pytest tests/test_L5_phrase_planner.py
pytest tests/test_L6_phrase_writer.py
pytest tests/test_L7_compose.py
pytest tests/test_cross_phrase_counterpoint.py
pytest tests/test_boundaries.py
pytest tests/test_system.py
```

CI runs in this order with `--fail-fast`. If L4 contract tests fail, L5+
are skipped. There is no value in running downstream tests when an upstream
contract is broken.
