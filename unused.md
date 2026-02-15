# Dead Code Analysis

Analysis of unused/dead code across builder, motifs, planner, shared, and viterbi directories.

---

## builder/ Directory

### builder/types.py
**Unused Classes:**
- `CollectedNote` (line 127) - Never imported or used
- `Solution` (line 180) - Never imported or used
- `RhythmState` (line 190) - Never imported or used
- `FigureRejection` (line 15) - Only used internally by FigureRejectionError but never instantiated

### builder/soprano_writer.py
**Unused Functions:**
- `generate_soprano_phrase` (lines 96-197) - Replaced by generate_soprano_viterbi and build_structural_soprano

### builder/episode_writer.py
**Entire File Appears Dead:**
- `write_episode` (lines 110-216) - Replaced by phrase_writer._write_thematic
- `extract_head_fragment` (lines 26-56) - Only called by write_episode
- `fragment_to_voice_notes` (lines 59-107) - Only called by write_episode

### builder/imitation.py
**Unused Functions:**
- `subject_to_notes` (lines 13-35) - Replaced by subject_to_voice_notes
- `answer_to_notes` (lines 38-71) - Replaced by answer_to_voice_notes
- `countersubject_to_notes` (lines 74-96) - Replaced by countersubject_to_voice_notes
- `subject_bar_count` (lines 233-235) - Never called

### builder/phrase_writer.py
**Unused Private Functions:**
- `_pad_to_offset` (lines 26-37)
- `_is_walking` (lines 40-46)

---

## motifs/ Directory

### Completely Unused Files (~1,437 lines total)

**motifs/enumerator.py** (344 lines)
- Early/experimental exhaustive enumeration approach
- All functions: enumerate_rhythm_patterns, enumerate_pitch_sequences, enumerate_all_candidates, count_candidates
- All constants: VALID_DURATIONS, BAR_DURATION, MIN_NOTES, MAX_NOTES, MAX_INTERVAL

**motifs/extract_melodies.py** (228 lines)
- Standalone analysis script for extracting melodies from baroque corpus
- All functions: get_config, parse_note_file, extract_melody, notes_to_midi_and_note, analyze_melody, main
- Constant: PIECE_CONFIG

**motifs/frequencies/analyse_intervals.py** (242 lines)
- Standalone corpus analysis script
- All functions: load_notes, compute_intervals, compute_intervals_per_voice, interval_name, classify_interval, find_highest_track, compute_tessitura_deviations, analyse_file, print_distribution, print_tessitura_distribution, main

**motifs/melodic_features.py** (603 lines)
- Research-based melodic feature extraction system
- All functions including: pitch_entropy, interval_entropy, strong_beat_alignment, syncopation_score, triadic_content, triadic_content_minor, opens_with_triad, interval_distribution, unusual_interval_density, step_leap_ratio, contour_parsimony, classify_contour, contour_string, tessitura_leap_interaction, range_utilization, phrase_length_regularity, is_power_of_two_phrasing, extract_all_features
- MelodicFeatureScorer class and all methods

### motifs/figurae.py
**Unused Methods:**
- `Figurae.all_names()`
- `Figurae.by_category()`
- `Figurae.by_affect()`

---

## planner/ Directory

### planner/koch_rules.py
**ENTIRE MODULE UNUSED** (10 items)
- Historical artifact from earlier phase
- All items: KochViolation (class), load_koch_config, classify_phrase, check_phrase_sequence, validate_caesura, check_all_caesurae, check_period_structure, check_modulation_rules, check_phrase_length, validate_koch

### planner/arc.py
**Unused Functions:**
- `select_tension_curve()` (lines 48-57)
- `build_tension_curve()` (lines 60-79)
- `get_tension_at_position()` (lines 82-94)

**Unused Constants:**
- `TENSION_TO_ENERGY` (lines 9-15)

### planner/dramaturgy.py
**Unused Constants** (implementation details, only used internally):
- `MATTHESON_KEYS` (lines 10-26)
- `AFFECT_TO_KEYS` (lines 29-52)
- `KEY_SUGGESTIONS` (lines 55-60)

### planner/schema_loader.py
**Unused Helper Functions** (12 items):
- `get_opening_schemas()` (lines 126-128)
- `get_riposte_schemas()` (lines 131-133)
- `get_continuation_schemas()` (lines 136-138)
- `get_pre_cadential_schemas()` (lines 141-143)
- `get_cadential_schemas()` (lines 146-148)
- `get_sequential_schemas()` (lines 151-154)
- `get_typical_position()` (lines 157-160)
- `schema_fits_bars()` (lines 163-170)
- `get_schema_figuration_profile()` (lines 216-219)
- `get_schema_profiles()` (lines 222-225)
- `get_arrival_beats()` (lines 228-259)
- `load_yaml()` (lines 18-24) - Only used within arc.py

### planner/plannertypes.py
**Unused Classes:**
- `Brief` (lines 5-16) - Only used in unused arc.py functions
- `MacroSection` (lines 20-27) - Only used to define MacroForm
- `MacroForm` (lines 31-35) - Only used in unused arc.py functions

---

## shared/ Directory

### shared/diatonic_pitch.py
**Entire DiatonicPitch Class Appears Unused:**
- Only used internally by Key.diatonic_to_midi() and Key.midi_to_diatonic(), which are themselves only used in tests
- Methods: interval_to(), transpose() - never called

### shared/voice_types.py
**Unused Classes:**
- `InstrumentDef` - Never instantiated
- `Actuator` - Never instantiated
- `ScoringAssignment` - Never instantiated
- `TrackAssignment` - Never instantiated
- `Instrument` - Only used in viterbi/generate.py (external to main pipeline)

### shared/key.py
**Unused Methods:**
- `Key.get_scale_for_context()` - Never called
- `Key.bridge_pitch_set` property - Only used in dead code paths
- `Key.midi_to_floating()` - Only in tests, not production
- `Key.floating_to_midi()` - Only in tests, not production

### shared/pitch.py
**Unused FloatingNote Methods:**
- `FloatingNote.shift()`
- `FloatingNote.as_exempt()`
- `FloatingNote.with_alter()`
- `FloatingNote.flatten()`
- `FloatingNote.sharpen()`

**Unused Classes:**
- `Rest` - Never instantiated
- `MidiPitch` - Never instantiated

### shared/counterpoint.py
**Limited Use Functions:**
- `find_non_parallel_pitch()` - Only used in tests
- `prevent_cross_relation()` - Only used in builder/bass_writer.py (1 location)

### shared/errors.py
**All Exception Classes - Defined But Never Raised:**
- `AndanteError` (base exception)
- `ValidationError`
- `InvalidDurationError`
- `InvalidPitchError`
- `InvalidRomanNumeralError`
- `SolverTimeoutError`
- `SolverInfeasibleError`

### shared/constants.py
**Unused Constants (~15+):**
- `CADENTIAL_TARGET_DEGREE`
- `STACCATO_DURATION_THRESHOLD`
- `MISBEHAVIOUR_PROBABILITY`
- `CONSONANT_PITCH_OFFSETS`
- `STABLE_DEGREES`
- `LEAP_THRESHOLD`
- `SECTION_CLIMAX_POSITION`
- `SMALL_INTERVAL_NOTE_REDUCTION`
- `DISSONANT_INTERVALS`
- `CADENCE_TYPES`
- `ANCHOR_DEPARTURE_HEADROOM`
- `VALID_DENOMINATORS`
- `VALID_DENSITY_TRAJECTORIES`
- `VALID_DEVELOPMENT_PLANS`
- `GROTESQUE_LEAP_SEMITONES` - Used only in builder/faults.py and tests
- `MINOR_SCALE` - Alias for NATURAL_MINOR_SCALE
- `NOTE_NAMES` - Alias for NOTE_NAMES_SHARP

---

## viterbi/ Directory

### Completely Unused Files (Standalone Scripts)

**viterbi/demo.py**
- Demo/example script with 14 example functions
- Only has `__main__` entry point, never imported

**viterbi/test_brute.py**
- Brute-force optimality testing script
- Only has `__main__` entry point, never imported by production code

**viterbi/bach_compare.py**
- Bach comparison analysis script
- All functions and constants
- Only has `__main__` entry point, never imported

**viterbi/midi_out.py**
- Only used by demo.py (which is itself unused)
- Function: write_midi
- Constants: TICKS_PER_BEAT, DEFAULT_TEMPO, DEFAULT_VELOCITY

### Unused Definitions in Active Files

**viterbi/scale.py:**
- `CMAJ_OFFSETS` - Deprecated constant (comment says "deprecated: use KeyInfo")

**viterbi/mtypes.py:**
- `MIDI_C3`, `MIDI_C4`, `MIDI_C5` - Never used
- `NOTE_NAMES` - Duplicated in shared/constants.py (shared version is used everywhere)

**viterbi/corridors.py:**
- `FOLLOWER_LOW`, `FOLLOWER_HIGH` - Only as default parameter values, always overridden

**viterbi/pathfinder.py:**
- `_print_path` - Only used when verbose=True, but production always uses verbose=False
- Private constants: MAX_RUN, BEAM_WIDTH, INF, State (only used internally)

**viterbi/pipeline.py:**
- `_validate_knots` - Private function only used within solve_phrase
- `_print_phrase_summary` - Only called when verbose=True (never in production)

**viterbi/costs.py:**
- All individual cost functions (only called by transition_cost, never imported directly)
- All COST_* weight constants (private to module)
- `_CROSS_RELATION_PAIRS` (private constant)

---

## Summary Statistics

**Total Estimated Dead Code:**
- **motifs/**: ~1,437 lines (4 complete files)
- **planner/**: koch_rules.py (entire module) + ~16 other items
- **builder/**: episode_writer.py (mostly dead) + ~10 other items
- **shared/**: DiatonicPitch class + voice_types classes + ~20 other items
- **viterbi/**: 4 complete files (demo.py, test_brute.py, bach_compare.py, midi_out.py)

**High-Priority Removal Candidates:**
1. motifs/enumerator.py, extract_melodies.py, frequencies/analyse_intervals.py, melodic_features.py
2. planner/koch_rules.py
3. builder/episode_writer.py
4. viterbi/demo.py, test_brute.py, bach_compare.py, midi_out.py
5. shared/errors.py exception classes
6. shared/diatonic_pitch.py DiatonicPitch class
7. shared/voice_types.py unused classes
