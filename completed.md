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
