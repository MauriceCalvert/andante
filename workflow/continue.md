# Continue

## Status: between tasks — listen and decide next priority.

## What just happened

SUB-1, SUB-2, SUB-2b complete. Subject generation now has:
- Tonal answers (fixed double-transposition bug)
- Per-segment density (head and tail have independent rhythmic density)
- Note-count asymmetry filter (no 6+6 splits)
- Cadential weight filter (final note ≥ penultimate, both subject and CS)
- W_REPETITION_PENALTY reduced to 0.5 (interim, pending SUB-3)

Additional fix: `write_subject_demo_midi` now includes CS solo between
inversion and subject+CS sections. Section order: subject → answer →
inversion → CS solo → subject+CS → stretto → inversion stretto.

## What to do next

Generate subjects (`python -m scripts.generate_subjects -v`), listen to
the MIDI demos, and decide which problem is most audible:

1. **SUB-3: Cell-group repetition (sequencing)** — tail reuses head's
   cell sequence at different pitch. The primary memorability device.
   Medium effort, high impact if subjects still sound "generated not
   composed."

2. **EPI-2c: Episode character arc** — position-aware fragment selection,
   minimum note density, octave-doubling rejection. Addresses bars 28–30
   sparsity in episodes.

3. **MEL: Melodic quality** — Viterbi cost improvements, figuration
   consonance, mixed-rhythm templates. Addresses smooth/predictable
   pitch fill.

4. **SUB housekeeping: algorithmic answer_offset_beats** — currently
   hardcoded. Low priority.

The ear decides priority order.

## Project state

- Pipeline runs clean on invention with seed 42, 16 faults (all pre-existing)
- Library subjects in motifs/library/ (6 files)
- Stretto caches will need regenerating after any subject changes
- todo.md is current
