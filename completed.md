# Deferred MIDI Resolution: Completion Report

## What Changed

The refactoring defers octave selection from planning time to fill time. Anchors
now carry degrees (1-7) and direction hints instead of absolute MIDI values.
The voice writer resolves degrees to MIDI at composition time, when the previous
pitch is known and the correct octave can be chosen.

## Files Modified

### builder/voice_writer.py

**Removed `_interval_from_steps`** — interval recomputation after resolution
was removed entirely. The planner's interval (computed from degrees) is the
harmonic intent and matches the figure vocabulary. Recomputing from resolved
steps produced intervals that strategies had no figures for, or picked
suboptimal figures.

**`_place_degree_with_direction`** — safe-zone enforcement. When following a
direction hint would push the pitch into the margin zone (within 10 semitones
of range edges), falls back to the nearest safe-zone candidate instead. Prevents
cumulative pitch drift across bars that caused cadential figures to exceed
the instrument range.

Fallback priority:
1. Safe candidate in the requested direction
2. Nearest safe-zone candidate to prev_midi
3. Nearest candidate to prev_midi (last resort, margin allowed)

**`_check_candidate`** — added `check_consonance` parameter (default True).
Allows callers to skip strong-beat consonance checks for internal figuration
notes, which are passing tones and may be dissonant on beat 3 in Baroque style.

**`_compose_gap` candidate filter** — for non-PILLAR modes, internal figuration
notes (not the first note) skip both melodic and consonance checks. The first
note is the anchor pitch (mandatory, bypasses all checks). PILLAR mode keeps
full checks since it has consonant-alternative fallback.

**`_compose_independent` / `_compose_sequenced`** — removed interval
recomputation blocks. Gaps use the planner's interval directly.

### planner/voice_planning.py

**`_compute_interval`** — same-degree anchors now always return `"unison"`
regardless of direction hint. Previously, same-degree with direction "down"
produced `"octave_down"`, which had insufficient figures. The direction hint
affects octave placement (handled by the voice writer), not the harmonic
interval between degrees.

### revision/test_counterpoint.py

**`test_dissonant_anchor_uses_consonant_alternative`** — rewrote to check
interval consonance of the output instead of matching log messages. Removed
unused imports.

## Root Causes Fixed

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Cadential bar 27: 0 figures for "ascending 6th" | Interval recomputation changed planned "step_down" to "sixth_up" | Removed interval recomputation — planner's interval is the harmonic intent |
| Figuration bar 3: dissonance on beat 3 (ic=1) | Strong-beat consonance check rejected passing tone | Skip consonance for internal figuration notes (passing tones) |
| Figuration bar 8: 0 figures for "octave_down" | Same-degree + "down" direction produced "octave_down" | Same-degree anchors always produce "unison" in planner |
| Figuration bar 13: pitch above range | Direction hints accumulated upward drift | Safe-zone fallback in `_place_degree_with_direction` |
| Cadential bar 27: all figures below range | Direction hints accumulated downward drift | Safe-zone fallback in `_place_degree_with_direction` |

## Test Results

37/37 tests pass (7 counterpoint, 6 integration, 15 pitch, 4 sequencing, 5 smoke pillar).

---

# Sixth Interval Vocabulary Gap

## Symptom

Gavotte generation crashed at bar 18 with `FigureRejectionError`: 0 figures
attempted for `sixth_up` in FIGURATION mode.

## Root Cause

The planner hardcodes `harmonic_tension="low"` for all gaps. The `sixth_up`
vocabulary had only three figures, none viable at low tension for small note
counts:

| Notes | Figure | Tension | Passes low? |
|-------|--------|---------|-------------|
| 2 | direct_sixth_up | high | No |
| 4 | arpeggiated_sixth_up | medium | No |
| 6 | filled_sixth_up | low | Yes |

When `max_count < 6` (common for medium-density gaps), every figure was
rejected by the tension filter. The note-count loop found zero candidates
at every count from `max_count` down to 2.

## Fix

### data/figuration/diminutions.yaml

Expanded `sixth_up` and `sixth_down` vocabulary to cover all note counts 2-6
at low tension:

| Notes | Figure | Change |
|-------|--------|--------|
| 2 | direct_sixth | tension high → low (consonant interval, consistent with 4ths/5ths) |
| 3 | broken_chord_sixth (new) | degrees [0, 2, 5] — triad skeleton, plain character |
| 4 | arpeggiated_sixth | tension medium → low, character bold → plain |
| 5 | partial_fill_sixth (new) | degrees [0, 1, 2, 4, 5] — lower scalar with skip |
| 6 | filled_sixth (unchanged) | already low tension |

All new/changed figures: cadential_safe=true, minor_safe=true, is_compound=false.

---

# Upbeat Offset Fix: Negative Offsets and Soprano Polyphony

## Symptom

Gavotte output had two defects at bar 1 (the upbeat):

1. **Polyphonic soprano**: two simultaneous track-0 notes at offset -0.5
   (A4 from anacrusis + D5 from gap 0 figuration).
2. **Negative offsets**: all upbeat notes had negative offset values in
   the .note output file.

## Root Cause

The planner places anchor[0] at bar 0 beat 3 for pieces with an upbeat.
`_bar_beat_to_offset("0.3", "4/4")` returns -0.5. Two problems follow:

1. The anacrusis and gap 0 both cover the same time span [anchor0, anchor1).
   `compose_section` runs both without checking for overlap, producing
   polyphonic output in what should be a monophonic voice.

2. All notes in the upbeat region get negative offsets, which are illegal.

## Fix

### builder/voice_writer.py

**`__init__`** — accepts `upbeat: Fraction` parameter. Stored as
`self._upbeat` and passed to all `_bar_beat_to_offset` calls.

**`_bar_beat_to_offset`** — adds `upbeat` to the result, shifting all
offsets so the piece starts at offset 0. Asserts `result >= 0`.

**`_compose_anacrusis`** — `start_offset = Fraction(0)` instead of
`-ana.duration`. With the shift, anchor[0] is at offset 0, so the
anacrusis starts there.

**`_compose_independent` / `_compose_sequenced`** — when `anchor_idx == 0`
and `self._anacrusis_composed`, skip the gap (resolve anchor pitch for
state continuity, then continue). The anacrusis already filled that time.

### builder/compose.py

Pass `plan.upbeat` to `VoiceWriter()`.

### builder/io.py

**`bar_beat()`** — subtracts upbeat before computing bar/beat columns:
`total_beats = (offset - upbeat) * 4`. Bar labels match the musical score
(bar 0 = anacrusis, bar 1 = first full bar).

---

# BUG-003 Fix: Bass Patterns Not Applied

## Symptom

Genre configs specify `bass_treatment: patterned` with `bass_pattern` names
(e.g. `arpeggiated_3_4` for minuet, `half_bar` for gavotte) but the bass
voice always produced whole-bar sustained notes identical to PILLAR mode.

## Root Cause

`voice_planning.py` ignored `GenreConfig.bass_treatment` and
`GenreConfig.bass_pattern`. The function `_get_writing_mode()` always
assigned `WritingMode.PILLAR` to non-lead lower voice gaps. The
`realise_bass_pattern()` and `realise_bass_schema()` functions in
`builder/figuration/bass.py` were never called.

## Fix

### shared/plan_types.py

Added `bass_pattern: str | None = None` field to `VoicePlan`. Carries the
pattern name from planner to voice writer.

### planner/voice_planning.py

- `build_composition_plan()` sets `bass_pattern` on the lower `VoicePlan`
  when `bass_treatment == "patterned"`.
- `_build_sections()` and `_build_gaps_for_range()` accept `bass_treatment`
  parameter, passed through to `_get_writing_mode()`.
- `_get_writing_mode()` returns `WritingMode.ARPEGGIATED` instead of
  `WritingMode.PILLAR` when `bass_treatment == "patterned"` and
  `is_upper == False`. Cadential mode still takes priority.

### builder/arpeggiated_strategy.py (new)

`ArpeggiatedStrategy` implements `WritingStrategy.fill_gap()`. Auto-detects
whether the named pattern is a `BassPattern` (degree offsets from root,
from `bass_patterns.yaml`) or `RhythmPattern` (schema-driven pitches, from
`rhythm_patterns.yaml`).

- BassPattern: transposes source_pitch by each beat's `degree_offset`.
- RhythmPattern: uses `source_pitch` or `target_pitch` per beat's `use_next`.
- Duration tokens `bar`/`half`/beats resolved from gap duration and metre.
- Candidate filter applied per note; falls back to root on rejection.

### builder/voice_writer.py

- Added `WritingMode.ARPEGGIATED` to `_IMPLEMENTED_MODES`.
- Creates `ArpeggiatedStrategy` in `__init__` when `plan.bass_pattern` is set.
- `_strategy_for_mode()` dispatches ARPEGGIATED to the strategy.
- `_compose_gap()` treats ARPEGGIATED like PILLAR for candidate filtering
  (no melodic interval checks between pattern notes).

## Affected Genres

| Genre | bass_pattern | Effect |
|-------|-------------|--------|
| minuet | arpeggiated_3_4 | Root-third-fifth broken chord per bar |
| gavotte | half_bar | Two notes per bar (current + next degree) |
| sarabande | continuo_sustained | Sustained root (same as before, explicit) |
| bourree | continuo_walking | Stepwise quarter notes through bar |

---

# BUG-004 Fix: Rhythm Templates Not Varied Across Gaps

## Symptom

Every bar in a minuet had uniform rhythmic density — unbroken quavers
(6 eighth notes per bar) throughout. No variation in note counts or
rhythmic profiles between bars regardless of interval or phrase position.

## Root Cause

`_build_gaps_for_range()` in `voice_planning.py` set
`required_note_count=None` for all figuration gaps. This delegated to
`compute_rhythmic_distribution()` which computes count from `gap_duration`
and `density` alone. For a minuet with no passage assignments, all gaps
had density="medium" (function always "subject") and gap_duration=3/4,
producing exactly 6 eighth notes for every bar.

## Fix

### shared/constants.py

Added three constants:
- `MIN_FIGURATION_NOTES = 2`: minimum notes for a figuration gap
- `INTERVAL_DIATONIC_SIZE`: maps interval names to diatonic step count
- `DENSITY_RHYTHMIC_UNIT`: preferred rhythmic unit per density level
  (moved from `rhythm_calc.py` for L017 single source of truth)
- `SMALL_INTERVAL_NOTE_REDUCTION`: reduction from base count by interval
  size — unison (-4), step (-3), third (-2); large intervals keep full base

### builder/figuration/rhythm_calc.py

Replaced local `DENSITY_TO_UNIT` with import of `DENSITY_RHYTHMIC_UNIT`
from shared constants.

### planner/voice_planning.py

Added `_base_note_count()`: computes base note count from gap duration
and density (same arithmetic as `compute_rhythmic_distribution` but
planner-side, avoiding cross-layer import).

Added `_compute_note_count()`: reduces base count for small intervals
using `SMALL_INTERVAL_NOTE_REDUCTION`. Large intervals (fourth+) keep
full base count because their figure vocabulary only has low-tension fills
at specific note counts.

Wired into `_build_gaps_for_range()`: sets `required_note_count` for
`WritingMode.FIGURATION` gaps; other modes keep `None`.

## Result

Minuet note counts (3/4, medium density):

| Interval | Before | After |
|----------|--------|-------|
| unison   | 6      | 2     |
| step     | 6      | 3     |
| third    | 6      | 4     |
| fourth+  | 6      | 6     |

---

# Cadential Figure Rejection Fix

## Symptom

Minuet generation (G major, zierlich) crashed at bar 20 with
`FigureRejectionError`: all 4 cadential figures for `step_up` /
`target_5` rejected with "direct (similar) motion to P5".

## Root Cause

Two issues combined:

1. **Hemiola filter discarded fallbacks.** When `use_hemiola=True`,
   `cadential_strategy.py` replaced the figure list with only hemiola
   figures. If the single hemiola figure failed, no non-hemiola fallback
   was available.

2. **Stale `_prev_candidate_midi` during figure expansion.** The
   candidate filter for FIGURATION/CADENTIAL modes skips checks for the
   first note (anchor pitch) but does NOT update `_prev_candidate_midi`.
   Subsequent notes measure their "leap" from the previous gap's exit
   pitch rather than from the anchor. A stepwise cadential figure
   (degrees [0, 1]) appeared to leap when measured from the distant
   exit pitch, triggering the direct motion rule.

## Fix

### builder/cadential_strategy.py

Changed hemiola handling from exclusive filter to preference sort:
hemiola figures tried first, non-hemiola figures available as fallback.

### builder/voice_writer.py

The `candidate_filter` for non-PILLAR modes now updates
`_prev_candidate_midi` and `_prev_candidate_offset` when processing
the first (anchor) note. Subsequent notes correctly measure motion
from the anchor, not from the previous gap's exit.

---

# FEAT-001: Imitation Implementation

## Summary

Wired up `Role.IMITATIVE` and `_compose_imitative_section()` so the
invention genre produces imitative counterpoint. The planner now creates
IMITATIVE sections when the genre YAML specifies `follow_voice`,
`follow_delay`, and `follow_interval` on a section.

In the invention, the exordium and confirmatio sections use imitation:
upper voice leads, lower voice enters one bar later transposed an octave
below. Narratio and peroratio keep their existing textures.

## Files Modified

### data/genres/invention.yaml

Added `follow_voice: 1`, `follow_delay: "1/1"`, `follow_interval: -7`
to exordium and confirmatio sections. Removed `accompany_texture` from
those sections (imitation replaces accompaniment).

### builder/types.py

Added three optional fields to `PassageAssignment`: `follow_voice`,
`follow_delay`, `follow_interval`.

### planner/textural.py

`layer_5_textural()` reads the three new fields from genre section dicts.
Validates that `follow_delay` and `follow_interval` are present when
`follow_voice` is set, and that `follow_delay` is positive.

### planner/voice_planning.py

- Decoupled VOICE_RANGES lookup indices from composition_order: added
  `_SOPRANO_RANGE_IDX` (0) and `_BASS_RANGE_IDX` (3) for range lookups,
  changed `TRACK_BASS` from 3 to 1 for composition_order.
- Added `_VOICE_INDEX_TO_ID` mapping (0→"upper", 1→"lower").
- Added `_get_imitation_config()`: checks if a voice should imitate in a
  given schema section by matching passage assignments with follow_voice.
- `_build_sections()` accepts `voice_id` parameter and creates
  `Role.IMITATIVE` sections with `follows`, `follow_interval`, and
  `follow_delay` when imitation config is found.

### builder/compose.py

`_section_is_lead()` returns False for `Role.IMITATIVE` sections,
ensuring the lead voice composes first so its notes are available.

### builder/voice_writer.py

`_compose_imitative_section()` now updates `_current_voice_notes` and
`_prev_exit_pitch` after the imitation loop, so subsequent non-imitative
sections have correct state for melodic continuity.

### shared/plan_types.py

`_check_follows_order()` replaced static composition_order check with
circular-follows detection. The old check prevented upper (order 0) from
ever following lower (order 1). The scheduler in compose.py guarantees
correct ordering per time span via `_section_is_lead()`.

## Verification

All 6 integration tests pass. Imitation verified: lower voice notes are
upper voice notes delayed by 1 bar and transposed exactly 12 semitones
down (diatonic octave). Zero parallel fifths/octaves.

---

# Keyword Argument Refactoring

## Summary

Converted all project-internal function calls from positional to keyword
argument format across 64 non-test Python files. External, stdlib, and
third-party calls left unchanged.

## Scope

| Directory | Files Modified |
|-----------|---------------|
| shared/ | 6 (key, midi_writer, music_math, pitch, plan_types, tracer) |
| builder/ | 14 (all root files + figuration/bass, loader, rhythm_calc) |
| motifs/ | 8 (enumerator, extract_melodies, figurae, head_generator, melodic_features, subject_generator, tail_generator, frequencies/analyse_intervals) |
| planner/ | 24 (all except plannertypes, rhetorical, structure, textural, tonal) |
| planner/metric/ | 4 (distribution, layer, pitch, schema_anchors) |
| scripts/ | 6 (midi_to_note, note_to_midi, note_to_subject, run_pipeline, yaml_validator) |
| root | 1 (LinesOfCode.py) |

17 files needed no changes (empty __init__.py, no project-internal calls,
or already using keyword format).

---

# FEAT-001 Bug Fix: Imitation Offset Filtering

## Symptom

In invention generation, the lower (imitating) voice had roughly half the
notes of the upper (lead) voice. The final bar of each imitative section
was lost.

## Root Cause

`_compose_imitative_section()` in `voice_writer.py` filtered source notes
using shifted bounds `[section_start - delay, section_end - delay)`. Lead
notes exist in `[section_start, section_end)`, so the filter excluded
notes in the final `delay`-sized window.

Example: exordium bars 1-4, delay = 1 bar. Filter selected offsets
`[-1, 2)` instead of `[0, 3)`, losing bar 3's notes entirely.

## Fix

### builder/voice_writer.py

Changed the source note filter from shifted bounds to actual section bounds:
`section_start` and `section_end` instead of `section_start - delay` and
`section_end - delay`. The delay is applied when placing the copied note
(line 385: `new_offset = note.offset + delay`), not when selecting source
notes.

## Verification

All 6 integration tests pass. Invention generation produces comparable
note counts: upper=90, lower=85 (6% difference vs ~50% before fix).

---

# FEAT-001 Deferred: Imitation Reverted to Walking Texture

## Summary

Reverted invention genre from imitative counterpoint back to
`accompany_texture: walking`. Naive transposition of lead material
creates guaranteed dissonances; proper Baroque imitation requires
pre-composed subjects, tonal answers, and countersubjects.

## Changes

### data/genres/invention.yaml

Removed `follow_voice`, `follow_delay`, `follow_interval` from exordium
and confirmatio sections. Replaced with `accompany_texture: walking`.

### builder/voice_writer.py

Hardened `_compose_imitative_section()` for future use:
- Added `used_offsets` set to prevent duplicate notes at the same offset
- Moved `new_offset` computation before transposition to enable early
  dedup check
- Relaxed candidate checks: `check_melodic=False, check_consonance=False`
  since imitated material follows the lead voice's melodic logic
- Removed `is_first` flag (redundant with relaxed checks)

### bugs_and_todos.md

Updated FEAT-001 status to "Deferred". Documented why naive copying fails
and outlined proper implementation plan (subject integration, tonal answer
generation, countersubject composition, section assembly).

## 2026-02-04: FigureRejectionError at bar 18 (ascending 5th)

### Root cause

The diminution vocabulary lacked flexible 2-note figures for larger intervals
(fourth, fifth, sixth, octave). The existing "direct_*" figures had:
- `character: bold` (rank 4) - filtered when gap requests `plain` (rank 0)
- `harmonic_tension: medium` - filtered when gap has `low` tension
- `cadential_safe: false` - filtered near cadences
- `minor_safe: false` (sixths) - filtered in minor keys

When a gap required note_count=2 with low tension and plain character, no
figures passed filter_figures(), causing 0 attempts.

### Fix

Added `simple_*` variants for all leap intervals in diminutions.yaml:
- `simple_fourth_up`, `simple_fourth_down`
- `simple_fifth_up`, `simple_fifth_down`
- `simple_sixth_up`, `simple_sixth_down`
- `simple_octave_up`, `simple_octave_down`

These have `character: plain`, `harmonic_tension: low`, `cadential_safe: true`,
`minor_safe: true`, and `weight: 1.0` (highest priority for plain contexts).

### Also: L017 compliance - unified interval naming

Merged duplicate definitions:
- `FIGURATION_INTERVALS` in constants.py (tuple of keys)
- `_INTERVAL_NAMES` in types.py (dict with display names)

Into single source of truth:
- `INTERVAL_DISPLAY_NAMES` in constants.py (dict: key -> readable name)
- `FIGURATION_INTERVALS` now derived from its keys

Updated types.py to import `INTERVAL_DISPLAY_NAMES` from constants.

## Constants Centralisation

Unified all scattered interval, degree, and music-theory constants into
`shared/constants.py`, organised into 15 alphabetical sections with constants
sorted alphabetically within each section.

### Constants moved (35 new entries)

| Constant | Source file(s) | Notes |
|---|---|---|
| `ALL_CONSONANCES` | `planner/cs_generator.py` | Derived: `PERFECT_INTERVALS \| IMPERFECT_CONSONANCES` |
| `BASS_CLEF_THRESHOLD` | `builder/musicxml_writer.py` | |
| `BASS_VOICE_IDX` | `planner/voice_planning.py` | Was `_SOPRANO_RANGE_IDX` (renamed) |
| `CADENTIAL_INTERVALS` | `planner/voice_planning.py` | Was `_CADENTIAL_INTERVALS` |
| `CADENTIAL_TARGET_DEGREE` | `builder/cadential_strategy.py` | Was `_CADENTIAL_TARGET_DEGREE` |
| `CLAUSULA_*` (4 constants) | `planner/metric/constants.py` | |
| `CONSONANT_DEGREES_WITH_TONIC` | `planner/subject_validator.py` | Was `CONSONANT_WITH_TONIC` |
| `CONSONANT_INTERVALS_WITH_OCTAVE` | `planner/subject_validator.py` | Was local `CONSONANT_INTERVALS` (includes 12) |
| `CONSONANT_PITCH_OFFSETS` | `builder/pillar_strategy.py` | Was `_CONSONANT_OFFSETS` |
| `CROSS_RELATION_PAIRS` | `builder/faults.py` | |
| `DIATONIC_DEGREES` | `planner/subject_validator.py` | Unified `MAJOR_DEGREES`/`MINOR_DEGREES` |
| `IMPERFECT_CONSONANCES` | `planner/cs_generator.py` | |
| `INTERVAL_EXIT_DEGREES` | `builder/figuration_strategy.py` | Was `_INTERVAL_EXIT` |
| `INTERVAL_NAMES_SHORT` | `builder/voice_checks.py` | Was `_INTERVAL_NAMES` |
| `INVERTIBLE_CONSONANCES` | `planner/cs_generator.py` | Alias for `IMPERFECT_CONSONANCES` |
| `KEY_AREA_SEMITONES` | `planner/metric/constants.py` | |
| `MAX_BASS_LEAP` | `builder/figuration/bass.py` | |
| `MAX_LEAP_SEMITONES` | `builder/junction.py` | Was `_MAX_LEAP_SEMITONES` |
| `MIN_BASS_MIDI` | `builder/figuration/bass.py` | |
| `SOPRANO_VOICE_IDX` | `planner/voice_planning.py` | Was `_BASS_RANGE_IDX` (renamed) |
| `STABLE_DEGREES` | `motifs/tail_generator.py` | |
| `TONIC_TO_MIDI` | `scripts/subject_to_midi.py` | |
| `TONIC_TRIAD_DEGREES` | `motifs/enumerator.py`, `motifs/head_generator.py` | Was duplicate `START_DEGREES` |
| `TRACK_BASS`, `TRACK_SOPRANO` | `planner/voice_planning.py` | |
| `TRITONE_SEMITONES` | `builder/figuration/bass.py` | |
| `UGLY_INTERVALS` | `builder/junction.py`, `builder/voice_checks.py` | Was `_UGLY_INTERVALS` in 3 files |
| `VALID_BASS_MODES` | `builder/figuration/bass.py` | |
| `VALID_BASS_TREATMENTS` | `builder/figuration/bass.py` | |
| `VALID_DENOMINATORS` | `planner/motif_loader.py` | |
| `VALID_DIRECTIONS` | `builder/config_loader.py` | |
| `VALID_HARMONIC_RHYTHMS` | `builder/figuration/bass.py` | |
| `VALID_TEXTURES` | `builder/figuration/bass.py` | |

### Duplicates eliminated

- `_UGLY_INTERVALS` defined in 3 places → single `UGLY_INTERVALS`
- `START_DEGREES` defined in 2 places → single `TONIC_TRIAD_DEGREES`
- `INTERVAL_NAMES` duplicate in `analyse_intervals.py` → import from constants
- `MAJOR_INTERVALS`/`MINOR_INTERVALS` in `subject_to_midi.py` → use `MAJOR_SCALE`/`NATURAL_MINOR_SCALE`
- `MAJOR_DEGREES`/`MINOR_DEGREES` (identical sets) → single `DIATONIC_DEGREES`
- `_DISSONANT_ICS` in `voice_writer.py` → use existing `STRONG_BEAT_DISSONANT`
- `PERFECT_CONSONANCES` in `cs_generator.py` → use existing `PERFECT_INTERVALS`
- `MIN_NOTE_COUNT` in `figuration_strategy.py` → use existing `MIN_FIGURATION_NOTES`

### Files updated (20 files)

`builder/cadential_strategy.py`, `builder/config_loader.py`, `builder/faults.py`,
`builder/figuration/bass.py`, `builder/figuration_strategy.py`, `builder/junction.py`,
`builder/musicxml_writer.py`, `builder/pillar_strategy.py`, `builder/voice_checks.py`,
`builder/voice_writer.py`, `motifs/enumerator.py`, `motifs/frequencies/analyse_intervals.py`,
`motifs/head_generator.py`, `motifs/subject_generator.py`, `motifs/tail_generator.py`,
`planner/cs_generator.py`, `planner/metric/constants.py`, `planner/motif_loader.py`,
`planner/subject_validator.py`, `planner/voice_planning.py`

---

## 2025-02-04: Tonal Answer Mutation Fix

### Root cause

`_apply_tonal_mutation()` in `answer_generator.py` used interval arithmetic
with accumulated offsets that was never applied. The function tracked
`accumulated_offset` after each mutation but subsequent notes used interval
preservation from the previous answer note, causing register drift.

Example: Little Fugue subject (0, 4, 2, 0, ...) produced answer
(4, 0, -2, -4, ...) instead of (4, 7, 6, 4, ...).

### Fix

Rewrote `_apply_tonal_mutation()` to use direct transposition with single-degree
adjustments at mutation points:

- Every note: `real_transposed = deg + REAL_TRANSPOSITION` (+4 degrees)
- At mutation point (note following boundary crossing):
  - 1->5 mutation: subtract 1 (contracts 5th to 4th)
  - 5->1 mutation: add 1 (expands 4th to 5th)

Result: subject interval +4 becomes answer interval +3 at mutation points,
remaining intervals preserved exactly.

### Also: L019 compliance

Replaced Unicode arrow characters in test output with ASCII equivalents.

### Also: L018 compliance

Emptied `motifs/__init__.py` which had re-exports violating the empty __init__ rule.

---

## Phase 2 Design: Countersubject Generator

Designed minimal CP-SAT constraint set for invertible countersubject generation.

### Key insight

Work entirely in scale degrees (mod 7), not semitones. Eliminates mode-dependent
interval calculation.

### Degree interval classification

| (cs - subj) % 7 | Interval class | Invertible consonance? |
|-----------------|----------------|------------------------|
| 0 | unison/octave | Yes |
| 1 | second | No (dissonant) |
| 2 | third | Yes |
| 3 | fourth | No (dissonant) |
| 4 | fifth | No (becomes 4th) |
| 5 | sixth | Yes |
| 6 | seventh | No (dissonant) |

### Constraint set

| Type | Constraint | Notes |
|------|------------|-------|
| Hard | Strong-beat: `(cs - subj) % 7 in {0, 2, 5}` | Invertible consonances |
| Hard | Weak-beat: `(cs - subj) % 7 in {0, 1, 2, 4, 5, 6}` | Allow passing tones + 5ths |
| Hard | No consecutive unisons | Standard |
| Hard | No direct motion to unison | Hidden unisons |
| Hard | `min_deg <= cs[i] <= max_deg` | Range |
| Soft | Weak-beat 5th penalty (20) | Prefer other consonances |
| Soft | Weak-beat dissonance penalty (10) | Prefer consonances |
| Soft | Contrary motion reward (15) | Independence |
| Soft | Leap > 4 penalty (30) | Singability |
| Soft | Repeated pitch penalty (25) | Interest |

### Design decisions

1. Same rhythm as subject (pitch-only optimisation)
2. Answer verification post-hoc (optimise against subject only)
3. Voice crossing allowed (L004)
4. Natural minor throughout (L007 - raised 7th is subject's cadential responsibility)
5. Weak-beat 5ths allowed (become passing 4ths when inverted - acceptable Baroque practice)

---

## Phase 2 Implementation: Countersubject Generator

Implemented `motifs/countersubject_generator.py` using CP-SAT optimisation per the design.

### Key features

- Hard constraints enforced via `AddAllowedAssignments` for strong/weak beat intervals
- Soft constraints as weighted penalties/rewards in objective function
- 5-second solver timeout, returns best feasible solution
- Verification function to check constraints post-generation

### Test results

50/50 seeds produced valid countersubjects with no constraint violations.

---

## Fugue Triple Generation

Added `generate_fugue_triple()` to `motifs/subject_generator.py` that coordinates:
1. Subject generation
2. Answer generation (tonal or real)
3. Countersubject generation (CP-SAT optimised)

### Output formats

- `.fugue` YAML file containing degrees, durations, and metadata
- `.midi` demonstration file with:
  - Subject alone
  - 1 bar rest
  - Answer alone  
  - 1 bar rest
  - Countersubject alone
  - 1 bar rest
  - Subject + CS (bass)
  - 1 bar rest
  - Answer + CS (bass)
  - 1 bar rest
  - CS (bass) + Subject

### New files

- `motifs/fugue_loader.py` - Loads `.fugue` files into `LoadedFugue` dataclass

---

## Fugue Integration into Pipeline

Wired fugue material through the composition pipeline so `.brief` files can specify
a pre-composed subject.

### Changes

**briefs/builder/invention.brief**
- Fixed `subject: fugue1` to `subject: fugue2` (correct filename)

**scripts/run_pipeline.py**
- `run_from_brief()` loads fugue when `subject` field present in brief
- Passes `LoadedFugue` through to `generate()` and `generate_to_files()`

**planner/planner.py**
- `generate()` and `generate_to_files()` accept optional `fugue` parameter
- Passes fugue to `build_composition_plan()`

**planner/voice_planning.py**
- `build_composition_plan()` accepts optional `fugue` parameter
- Includes fugue in returned `CompositionPlan`

**shared/plan_types.py**
- Added `fugue: LoadedFugue | None = None` field to `CompositionPlan`

**builder/compose.py**
- Passes `plan.fugue` to `VoiceWriter`

**builder/voice_writer.py**
- `__init__` accepts optional `fugue` parameter
- `_get_fugue_material_for_section()` determines which fugue element to use:
  - Section 0: upper=subject, lower=countersubject
  - Section 1: upper=countersubject, lower=answer
  - Section 2+: falls back to normal composition
- `_compose_fugue_thematic()` inserts literal MIDI pitches from fugue

### Result

When invention.brief specifies `subject: fugue2`, the first two sections use
the pre-composed subject, answer, and countersubject pitches instead of
generating figuration.

---

## 2026-02-04: Duplicate Fugue Material in Schema Sections

### Symptom

Bar 4 crash with `FigureRejectionError`: all figures rejected for `descending 2nd`
in FIGURATION mode with "parallel motion to unison".

### Root cause

`_build_sections()` in `voice_planning.py` creates a `SectionPlan` for each
*schema section* (e.g., do_re_mi, prinner), not each *form section* (exordium,
narratio). When a form section contains multiple schemas, each schema section
received fugue material assignment.

Example in exordium (form section 0):
- do_re_mi schema section: `lead_material="subject"` -> soprano plays subject bars 1-2
- prinner schema section: `lead_material="subject"` -> soprano plays subject AGAIN at bar 4

This caused the subject to repeat within a single form section, creating
voice-leading conflicts as the subject's opening clashed with prior notes.

### Fix

Added `form_sections_with_material` tracking set to `_build_sections()`. Fugue
material (`lead_material`, `accompany_material`) is only assigned to the **first**
schema section within each form section. Subsequent schema sections within the
same form section get `None` and use normal figuration.

### Files modified

**planner/voice_planning.py**
- Added `form_sections_with_material: set[str]` to track which form sections
  have already received fugue material
- Added `is_first_in_form_section` check before assigning material
- Only first schema section in each form section gets fugue material
- Updated docstring to document the behaviour

### Result

Invention pipeline completes successfully. Remaining faults are unrelated
voice-leading issues (parallel rhythm, parallel octaves) that need separate fixes.

---

## 2026-02-04: Brief Sections Override Not Applied

### Symptom

Brief files with custom `sections` definitions (like demo_fantasia.brief) were
ignored. The planner always used the genre YAML's sections instead.

### Root cause

`run_from_brief()` in `run_pipeline.py` only extracted basic fields (genre, key,
affect, tempo, subject) from the brief. The `sections` field was never passed
through the pipeline to override the genre config.

### Fix

**briefs/builder/demo_fantasia.brief**
- Changed `label:` to `name:` in all 5 sections to match genre YAML format

**scripts/run_pipeline.py**
- Added `_convert_brief_sections()` to convert brief section format to genre format:
  - Extract `schema` from each phrase in `phrases` -> `schema_sequence`
  - Preserve `lead_voice`, `accompany_texture`, `tonal_path`, `final_cadence`
- `run_from_brief()` extracts sections from brief and calls conversion
- `run_from_args()` accepts `sections_override` parameter

**planner/planner.py**
- Added `_with_sections_override()` helper using `dataclasses.replace()`
- `generate()` accepts `sections_override` parameter and applies it to genre_config
- `generate_to_files()` passes through `sections_override`

### Result

demo_fantasia.brief now uses its 5 custom sections (295 notes) instead of
fantasia.yaml's single section. invention.brief continues to work correctly.

---

## 2026-02-04: MusicXML Lyric Labels and YAML Unknown Key Validation

### Issue 1: Fugue material lyrics all showing 'fugue'

MusicXML lyric labels were hardcoded to 'fugue' for all fugue material instead
of showing specific material type (subject, answer, countersubject).

**Fix** in `builder/voice_writer.py`:
- Added `_MATERIAL_LYRICS` dict mapping material names to concise labels:
  `subject` → `S`, `answer` → `A`, `countersubject` → `CS`
- Added `_material_to_lyric()` helper function
- `_get_fugue_material_for_section()` now returns 3-tuple including material name
- `_compose_fugue_thematic()` accepts `material_name` and uses it for lyric

### Issue 2: YAML validator not catching unknown keys

**Fix** in `scripts/yaml_validator.py`:
- Added `VALID_GENRE_KEYS`, `VALID_GENRE_SECTION_KEYS` frozensets
- Added `VALID_BRIEF_KEYS`, `VALID_BRIEF_SECTION_KEYS`, `VALID_BRIEF_PHRASE_KEYS`
- Added `validate_unknown_keys()` function checking genre and brief files
- Integrated into `validate_all()` as step 3

### Issue 3: Lyric labels on every note instead of first only

**Fix** in `builder/voice_writer.py`:
- `_compose_fugue_thematic()` now only sets lyric on first note (`i == 0`)

### Issue 4: Fantasia bass mostly semibreves

`bass_treatment: contrapuntal` was falling through to PILLAR mode because
`_get_writing_mode()` only checked for "patterned" bass, not "contrapuntal".

**Fix** in `planner/voice_planning.py`:
- Added `bass_contrapuntal` flag in `_get_writing_mode()`
- Contrapuntal bass now returns `WritingMode.FIGURATION` instead of PILLAR

### Issue 5: FigureRejectionError with contrapuntal bass

With both voices doing FIGURATION, voice-leading conflicts (direct motion
to unison) caused all figures to be rejected.

**Root cause**: Parallels/direct motion checks applied to every note, but
baroque practice only enforces these on strong beats. Off-beat figuration
has more freedom.

**Fix 1** - Gap-by-gap interleaved composition in `builder/compose.py`:
- Replaced section-level scheduling with `GapTask` gap-level scheduling
- After each gap, other voice's `prior_at_offset` is updated
- Both voices see each other's intermediate figuration notes
- Enables invertible counterpoint

**Fix 2** - Added `compose_single_gap()` in `builder/voice_writer.py`:
- Composes one gap at a time for interleaved scheduling
- Tracks `_gaps_composed`, `_section_initialized`, `_prev_anchor_midi`
- IMITATIVE and fugue-thematic sections still compose atomically

**Fix 3** - Strong-beat-only voice-leading checks in `_check_candidate()`:
- Added `_is_strong_beat()` helper (beat 1 of bar)
- Parallels/direct motion only checked on strong beats
- Off-beat figuration notes have freedom per baroque practice

### Issue 6: Human-readable FigureRejectionError messages

Pitch displayed as "DiatonicPitch(step=37)" instead of note name.

**Fix** in `builder/figuration_strategy.py`:
- Added `_midi_to_note_name()` helper converting MIDI to "C4", "F#3" etc
- `_expand_and_check()` now reports pitch as note name

### Issue 7: Anchor placement too high for ascending figures

Ascending gaps need headroom above source anchor for figuration.
Source anchor was placed without considering departure direction.

**Fix** in `builder/voice_writer.py`:
- Added `departure_ascending` parameter to `_resolve_anchor_pitch()`
- Added `_adjust_for_departure()` method: shifts anchor down an octave
  if ascending gap and anchor is within 12 semitones of range top
- Updated all source anchor resolution calls to pass `gap.ascending`

### Issue 7 (revised): Anchor placement departure headroom - proper fix

The previous `_adjust_for_departure()` violated D008 (no downstream fixes).
It adjusted anchor octave AFTER initial placement - wrong approach.

**Proper fix** in `builder/voice_writer.py` and `shared/constants.py`:
- Added `ANCHOR_DEPARTURE_HEADROOM = 12` constant
- Added `_filter_for_departure_headroom()` method: filters candidate octaves
  during initial selection, not as post-hoc adjustment
- Modified `_place_degree_near_median()` and `_place_degree_with_direction()`
  to accept `departure_ascending` parameter and apply headroom filter
- Removed `_adjust_for_departure()` entirely
- Constraint now propagates upward per D002: placement considers departure
  direction from the start, not as a fix afterward

---

## 2026-02-04: Rhythmic and Tonal Planning Specifications

### Problem

demo_fantasia.note exhibited monotonous rhythm: approximately 80% of soprano
bars used identical 5/8 + 1/8 + 1/4 pattern (dotted crotchet, quaver, crotchet).

### Root cause analysis

1. **No rhythmic planning layer**: Tonal planning decides anchors (pitch targets),
   but nothing plans rhythm at phrase level.

2. **Gap filling is mechanical**: `voice_planning.py` sets `overdotted=True` when
   `affect_config.density == "high"` (line 524). This causes all gaps to use the
   same overdotted template.

3. **"Density" is a proxy, not rhythm**: High density means more notes, but the
   *pattern* of those notes is fixed. A 3-note fill in 4/4 always uses template
   `[5/2, 1/2, 1]` beats when overdotted.

4. **No phrase-level motif development**: Each gap independently queries the
   template table with identical parameters. No rhythmic continuity or variation.

### Documentation created

Created two specification documents in `docs/Tier1_Normative/`:

**tonal_planning.md**
- Documents existing schema-based anchor planning
- Theoretical foundation: Gjerdingen schemas, GTTM hierarchical structure
- Schema transition rules and validation
- Tonal region planning (modulation vs tonicization)
- Cadence planning and variety constraints
- Interface contract with gap filling

**rhythmic_planning.md** (NEW SYSTEM)
- Documents missing rhythmic planning layer
- Theoretical foundation:
  - Cooper & Meyer: rhythm vs metre distinction
  - GTTM: grouping structure, metrical structure
  - Baroque conventions: notes inégales, overdotting, lombardic rhythm, hemiola
  - Mattheson Affektenlehre: rhythm-affect correspondence
- Three-level architecture:
  - Section profile (affect → rhythmic character)
  - Phrase motif (rhythmic cell selection and development)
  - Gap template (exact durations from motif slice)
- Motif vocabulary (14 foundational cells for 4/4)
- Development techniques (diminution, augmentation, displacement, fragmentation)
- Variety rules (V-R001 through V-R005)
- Implementation requirements (new components, data files)
- Anti-patterns (X-R001 through X-R004)

### References consulted

1. Gjerdingen (2007) - *Music in the Galant Style*
2. Lerdahl & Jackendoff (1983) - *A Generative Theory of Tonal Music*
3. Cooper & Meyer (1960) - *The Rhythmic Structure of Music*
4. Mattheson (1739) - *Der vollkommene Capellmeister*
5. Quantz (1752) - *Versuch einer Anweisung die Flöte traversiere zu spielen*
6. Hefling (1993) - *Rhythmic Alteration in Seventeenth- and Eighteenth-Century Music*
7. Hotteterre (1719) - *L'art de préluder sur la flûte traversière*
8. Caplin (1998) - *Classical Form*
9. Hasty (1997) - *Meter as Rhythm*
10. London (2012) - *Hearing in Time*

## Tonal Planning Upgrade (completed)

- Phase 1: Added `SectionTonalPlan`, `TonalPlan` to builder/types.py; `CADENCE_DEGREES` to constants; extended `SchemaChain` with cadences and section_boundaries.
- Phase 2: Created planner/variety.py with V-T001 (no adjacent schema repetition), V-T002 (opening schemas at section starts only), V-T003 (cadence variety), V-T004 (tonal path variety).
- Phase 3: Rewrote planner/tonal.py with key area assignment, cadence assignment, seeded RNG, variety validation.
- Phase 4: Rewrote planner/schematic.py with graph-walk schema selection, affect weighting, bass continuity, free passage marking, V-T001/V-T002 validation.
- Phase 5: Added hierarchical anchors to metric/layer.py — piece-level (start/end), section-level (cadence targets), phrase-level (schema stages), with deduplication and sort.
- Phase 6: Integrated into planner.py (L2 feeds L3, L3 feeds L4 with TonalPlan). Fixed missing `_deduplicate_anchors`. Fixed V-T002 violation in `_select_next_schema` (opening schemas excluded from mid-section graph walk). End-to-end tested: invention, minuet, bourree, gavotte, sarabande all pass.

## Rhythmic Planning Upgrade (completed)

Hierarchical rhythmic planning: section profile -> phrase motif -> gap rhythm, replacing flat slot-activation system.

- Phase 1: Replaced old RhythmPlan (slot-based) with RhythmicProfile, RhythmicMotif, GapRhythm, and new RhythmPlan in builder/types.py. Added GapPlan.gap_rhythm field to shared/plan_types.py. Added INEQUALITY_RATIOS, OVERDOTTING_FACTORS, and related constants to shared/constants.py.
- Phase 2: Created data/rhythm/motif_vocabulary.yaml (foundational cells for 4/4, 3/4, cadential cells) and data/rhythm/affect_profiles.yaml (Mattheson affect-to-rhythm mappings with section function modifiers).
- Phase 3: Implemented planner/rhythmic_profile.py — loads affect profiles from YAML, computes section profiles with density trajectory, climax bar, hemiola zones, and tonal density coordination.
- Phase 4: Implemented planner/rhythmic_motif.py — loads motif vocabulary from YAML, selects motifs filtered by phrase position/character/metre with V-R001 consecutive-identical prevention, and applies development operations (diminute, augment, fragment, invert, displace).
- Phase 5: Implemented planner/rhythmic_gap.py — derives gap rhythms from phrase motifs by extracting slices scaled to gap duration, with inequality and overdotting application per section profile.
- Phase 6: Implemented planner/rhythmic_variety.py — validators for V-R001 (no consecutive identical rhythms), V-R002 (phrase motif variation), V-R003 (cadential rhythmic change), V-R004 (section density arc), V-R005 (cross-phrase continuity).
- Phase 7: Rewrote planner/rhythmic.py as orchestrator: detects phrase boundaries from passage assignments, computes section profiles, selects/develops motifs per phrase, derives gap rhythms, outputs RhythmPlan.
- Phase 8: Integrated into pipeline. voice_planning.py accepts RhythmPlan and populates GapPlan.gap_rhythm. planner.py calls layer_6_rhythmic between L5 (textural) and L7 (voice planning), passing RhythmPlan through. Added L7 tracer method.
- BUG FIX: Final cadence missing from gavotte, invention, minuet. In voice_planning.py _build_sections, is_final was computed as idx == num_sections - 1, but single-anchor trailing sections (section_cadence_authentic) were skipped by start_idx >= end_idx guard, stealing the final designation. Changed is_final to end_idx == len(plan_anchors) - 1 so the last section with actual gaps gets the final pillar note appended.


## Rhythm Bug Fix (Phase 1) — 4 fixes applied

### Bug 1: Default density forced `high` globally
- Changed `default` density from `high` to `medium` in `data/rhetoric/affects.yaml`
- Added explicit `density` field to all 10 named affects (mapped from rhythm_density: sparse→low, moderate→medium, dense→high)

### Bug 3b: Small-interval note reduction inverted
- Zeroed out `SMALL_INTERVAL_NOTE_REDUCTION` dict in `shared/constants.py` (was removing 2-4 notes for unison/step/third gaps, collapsing note counts to minimum)

### Bug 3a: Non-lead voices unconditionally got density="low"
- Modified `_get_density()` in `planner/voice_planning.py` to accept `is_upper` and `bass_treatment` parameters
- Contrapuntal bass now gets function-based density (same as lead voices) instead of hard-coded "low"
- Patterned bass and non-lead upper voices still default to "low"

### Bug 2 (partial): `overdotted` was density-driven (always True)
- Added `OVERDOTTED_CHARACTERS` constant in `shared/constants.py`: {"bold", "energetic"}
- Changed `overdotted` assignment in `voice_planning.py` from `affect_config.density == "high"` to `character in OVERDOTTED_CHARACTERS`
- Overdotting now only applies to bold/energetic character gaps, not globally

### Bug 2 (full): Template vocabulary expansion — deferred to Phase 2

## Overdotting Removal (S001: performance practice out of scope)

Added law S001: "Performance practice out of scope; score notation only."

Removed all overdotting infrastructure:
- `OVERDOTTED_CHARACTERS`, `OVERDOTTING_FACTORS`, `VALID_OVERDOTTING_LEVELS` from `shared/constants.py`
- `overdotted: bool` field from `GapPlan` in `shared/plan_types.py`
- `overdotted: bool` field from `RhythmTemplate` in `builder/figuration/types.py`
- `overdotting: str` field from `RhythmicProfile` in `builder/types.py`
- `OVERDOTTED_CHARACTERS` import and usage from `planner/voice_planning.py`
- Overdotted template lookup and fallback from `builder/figuration_strategy.py` and `builder/cadential_strategy.py` (key now `(note_count, metre)`)
- `apply_overdotting()` function and `OVERDOTTING_FACTORS` import from `planner/rhythmic_gap.py`
- Overdotting validation/loading from `planner/rhythmic_profile.py`
- All `overdotted:` variant blocks from `data/figuration/rhythm_templates.yaml`
- All `overdotting:` fields from `data/rhythm/affect_profiles.yaml`
- `overdotted=False` from test files in `revision/`
- Loader now skips overdotted YAML variants with comment referencing S001

## Inequality (notes inegales) Removal (S001)

Removed all inequality infrastructure from the score pipeline:
- `INEQUALITY_RATIOS`, `VALID_INEQUALITY_LEVELS` from `shared/constants.py`
- `inequality: str` from `RhythmicProfile` in `builder/types.py`
- `inequality_ratio: Fraction` from `GapRhythm` in `builder/types.py`
- `apply_inequality()` function, `_MAX_INEQUALITY_VALUE`, `INEQUALITY_RATIOS` import from `planner/rhythmic_gap.py`
- `is_stepwise` parameter from `derive_gap_rhythm()` (was only used for inequality)
- `_is_stepwise_gap()` helper from `planner/rhythmic.py` (now dead code)
- Inequality validation/loading from `planner/rhythmic_profile.py`
- All `inequality:` fields from `data/rhythm/affect_profiles.yaml`
- Left `data/humanisation/` untouched (humanisation is performance output, separate from score)
