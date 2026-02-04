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
