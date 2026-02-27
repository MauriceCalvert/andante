# Continue — SUB-1: Fix tonal answer generation

## Status: task.md issued, Claude Code running.

## Context

EPI-2b complete. All 5 episodes render via fragen (zero fallbacks). Bars 28–30
still have sparse parallel-octave texture (7 notes/voice vs 13–14 elsewhere) —
this is a fragment quality issue for EPI-2c, not a retry issue.

SUB-1 is a code-fix task, not a musical design task. The answer generator has
two bugs:
1. TONIC_TRANSPOSITION and DOMINANT_TRANSPOSITION constants are swapped.
2. `answer_midi()` renders at tonic+7, double-transposing (degrees already
   encode the shift).

## What SUB-1 does

- Swaps constants in `motifs/answer_generator.py` (TONIC=4, DOMINANT=3)
- Removes +7 from `answer_midi()` in `motifs/subject_loader.py`
- Updates stale comment in `builder/thematic_renderer.py:66`
- Regenerates all .subject files (output/ and library/)

## What to do next

1. Read `workflow/result.md`
2. Verify: for any subject, tonic-region notes should be P5 (7 semitones)
   above subject, dominant-region notes P4 (5 semitones) above.
3. Run pipeline, listen to MIDI — answer entries should sound like a proper
   tonal answer (5→1 mapping at mutation point), not a mangled real answer.
4. `_fit_shift` in imitation.py may now apply smaller octave corrections
   (or none) since raw pitches are closer to correct register.

## After SUB-1

EPI-2c: episode character arc — position-aware selection + minimum note
density filter + octave-doubling rejection in FragenProvider. Addresses
the bars 28–30 sparsity/parallel-octave issue.
