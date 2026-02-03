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
