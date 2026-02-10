# Plan 12 — Algorithmic Figuration, Harmony Threading, Register Floor

## Problem

Three connected figuration/registration issues:

A. **Padding.** Rhythm cells demand N notes but the YAML figure table has
   only 2-3 degree figures for many interval classes. `_fit_degrees_to_count`
   pads with mechanical neighbour oscillation. Sounds like a stuck ornament.

B. **No semiquaver content.** Rhythm cells `sixteen_semiquavers` and
   `eight_quavers` exist but nothing fills them musically. Invention episodes
   need continuous 16th-note motion.

C. **Low gavotte register.** `degree_to_nearest_midi` chases `prev_midi`
   downward. Gavottes land soprano structural tones at E4-D4 instead of
   the idiomatic G4-C5.

## Solution

A+B: Replace the lookup-then-pad architecture with an algorithmic degree
generator that produces exactly N degrees for any interval/count combination.
Rules per interval class (unison, step, third, fourth+, sixth+) use
neighbour decoration, stepwise filling, and chord-tone arpeggiation. The
chord tones come from the bass degree at each structural position, already
available in PhrasePlan.degrees_lower (thread via 12b).

C: Soft register floor in soprano_writer. If a structural tone lands more
than a perfect fourth below biased_upper_median and an octave-up placement
is in range, prefer the higher octave.

## Scope

- New module: `builder/figuration/generator.py`
- Modified: `builder/figuration/soprano.py`, `builder/figuration/selection.py`,
  `builder/soprano_writer.py`
- Unchanged: cadence_writer, bass_writer, rhythm_cells, diminutions.yaml

## Status: Brief in task.md, ready for CC.
