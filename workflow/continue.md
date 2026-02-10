# Continue

## Current state

Plans 4–11 complete. Plan 12 in progress — brief is in workflow/task.md, ready for CC.

### Plans
- plan11.md — complete (small fixes batch)
- plan12.md — Algorithmic figuration + harmony threading + register floor (in progress)
  - 12a: Algorithmic figuration generator (replaces lookup-then-pad)
  - 12b: Thread bass harmony (chord tones) to figuration system
  - 12c: Soprano register floor (prevents downward drift in gavottes)
  - All three in single brief, single checkpoint at end

### What just happened
- Phase 11: Small fixes batch. Passed.
  - 11a: `min_non_cadential: 2` in invention exordium. Both keys show subject + answer before cadence.
  - 11b: Walking bass parallel prevention widened + lookahead. Gavotte bar 19.1 fixed.
  - 11c: Sarabande-specific rhythm cells with beat-2 accent. 57% crotchet-minim pattern.
  - All 8 genre/key combinations clean, zero new faults.

### Known test failures
- parallel_rhythm: gavotte_c_major (bar 15.3), gavotte_a_minor (bar 15.3),
  invention_c_major (bars 5.3, 9.3, 14.3), invention_a_minor (bars 5.3, 9.3, 14.3).

### bass_writer.py
1016 lines. generate_bass_phrase ~769 lines. Three texture branches
(patterned, pillar, walking) each with own bar loop and duplicated
guards. Defer refactor until inner voices or bass rewrite forces it.

### Deferred
- Subject development (inversion, augmentation, stretto)
- Episode derivation from subject fragments
- CS in later invention entries
- Inner voices
- Figurenlehre labelling for training data
- bass_writer refactor (three texture branches → three functions)

### Bob's open complaints (from Phase 11 result)
- Figuration padding warnings: figures with 2 degrees padded to 8 → Phase 12a
- Low soprano register in gavottes (E4-D4 area, bars 3-5) → Phase 12c
- Whole-note held structural tones (gavotte bar 18)

## Key files
- workflow/task.md — Plan 12 brief, ready for CC
- completed.md — full history
