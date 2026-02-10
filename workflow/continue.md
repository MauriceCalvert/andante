# Continue

## Current state

Plans 4–11 complete. Plan 12 complete (partial — register floor + chord tones work, generator re-enabled in Phase 13). Phase 14 brief in workflow/task.md, ready for CC.

### Plans
- plan12.md — complete (algorithmic figuration + harmony threading + register floor)
- Phase 13 — complete (re-enabled generator + density threading, but no semiquavers due to character overwrite)
- Phase 14 — Character floor + voice-leading clamp (in progress, brief ready)
  - 14a: Section character from genre YAML as floor for tension-curve character
  - 14b: Voice-leading-aware octave selection in _realise_pitches (replaces _clamp_to_range)

### What just happened
- Phase 13: Generator re-enabled, density parameter threaded. Zero new faults.
  - BUT: no semiquavers produced because tension curve overwrites genre YAML section characters
  - Root cause: build_phrase_plans always derives character from ENERGY_TO_CHARACTER, ignoring _get_section_character output already set in _build_single_plan
  - Also identified: _clamp_to_range causes interval-14 leaps in A minor (pre-existing)

### Known test failures
- invention_a_minor: "Melodic interval 14 exceeds octave at offset 27/2" (pre-existing, Phase 14b target)
- sarabande_a_minor: "Leap of 10 at offset 33/4 not followed by step" (pre-existing, Phase 14b target)
- parallel_rhythm: gavotte_c_major (bar 15.3), gavotte_a_minor (bar 15.3),
  invention_c_major (bars 5.3, 9.3, 14.3), invention_a_minor (bars 5.3, 9.3, 14.3).

### Genre YAML characters (Phase 14 includes YAML fixes)
- invention: exordium=plain, narratio=energetic, confirmatio=expressive, peroratio=ornate (unchanged)
- bourree: A=energetic, B=bold (unchanged — semiquavers idiomatic)
- fantasia: A=bold (unchanged)
- gavotte: A=expressive, B=expressive (B changed from energetic — no semiquavers)
- minuet: A=expressive, B=expressive (B changed from energetic — no semiquavers)
- sarabande: A=expressive, B=expressive (B changed from ornate — no semiquavers)

### bass_writer.py
1016 lines. generate_bass_phrase ~769 lines. Defer refactor.

### Bob's open complaints (from Phase 13 result)
- No semiquaver content in inventions → Phase 14a
- Interval-14 leaps in A minor → Phase 14b
- Sarabande A minor leap-step fault → Phase 14b

## Key files
- workflow/task.md — Phase 14 brief, ready for CC
- workflow/todo.md — deferred work and done items
- completed.md — full history
