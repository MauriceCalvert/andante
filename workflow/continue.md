# Continue

## Status: EPI-4a brief issued — waiting for "go" in Claude Code.

## What just happened

EPI-3 (parallel 3rds/6ths lockstep) was a failure — lockstep doubling
violated Principle 2 (voices in relation), sounded like an organ coupler.
Reverted to STR-1 commit (85fbbe7). Fault count back to pre-EPI-3 baseline.

Root cause analysis: the entire Fragen bar-length composite approach is
wrong. Bach's episodes use tiny kernels (2–4 notes) sequenced beat-by-beat
at stepping pitch levels. Our system chains cells into bar-length
Frankenstein composites, producing either lockstep or shuffled subject
recombinations.

## What's in progress

EPI-4a: standalone kernel episode demo (soprano only). New `extract_kernels`
and `sequence_kernel` functions in fragen.py, plus a demo script that
writes MIDI for human evaluation. No pipeline integration — hear it first.

After EPI-4a: EPI-4b will add the bass voice (countermelody kernel or
inversion at canonic offset), EPI-4c will wire into the planner (planner
selects kernel per episode, Fragen just realises). Dead code removal of
build_chains/build_fragments/get_fragment after integration.

## Also agreed

Subject (and tonal answer) may appear literally no more than 3 times total.
Inversions, augmentation, diminution, stretto do not count against the cap.
This constraint belongs in the planner and will be implemented after
episode rework is complete.

## Project state

- Pipeline runs clean on STR-1 baseline
- EPI-3 reverted (uncommitted changes were discarded)
- Minor script renames (midi_to_note, note_to_midi, generate_subjects)
  remain as uncommitted changes — unrelated to EPI-3
