# Andante Lessons

## Coding Rules

| ID | Rule |
|----|------|
| L001 | Try blocks forbidden — use membership test or let it raise |
| L002 | No magic numbers — named constants or data-driven |
| L003 | No range constraints — floors, ceilings, tessituras forbidden; fix upstream |
| L004 | Voice crossing allowed — Bach crosses freely in counterpoint |
| L005 | Arithmetic on durations forbidden — use music_math functions |
| L006 | All durations must be in VALID_DURATIONS — no division |
| L007 | Natural minor for melodic content — raised 6/7 only in cadential contexts, not throughout phrases |
| L008 | Tonal targets are harmonic functions — they indicate phrase destination, not scale selection |
| L009 | Tonal targets are functions, not modulations — realiser uses home_key for all melodic content; modulating creates chromatic accidents (e.g., D# in A major targeting V) |
| L010 | Leading tone reserved for subject cadences — counter-subject and bass voice must not use degree 7; sequence expansion can create degree 7 from transposition, so bass uses avoid_leading_tone filter |
| L011 | While loops must have guards — assert preconditions (e.g., dur > 0) and throw if max_iterations exceeded; no silent infinite loops |
| L012 | No quantization — if durations need rounding to valid values, the upstream source is wrong; patterns must use valid durations from the start |
| L013 | MIDI gate time 95% — notes must be shortened to 95% of notated duration to avoid legato/slur rendering in players |
| L014 | No side effects on parameters — functions must clone data before modification; never mutate passed arguments; validation functions like realise_phrase must be pure |

## Design Rules

| ID | Rule |
|----|------|
| D001 | Validate, don't fix — warn on anomalies, don't silently correct |
| D002 | Constraints propagate upward — if executor needs valid budget, planner must provide it |
| D003 | Trace must support debugging without source code |
| D004 | Separate melodic approach (stepwise descent) from harmonic formula (bass motion) |
| D005 | Compute patterns from budget, don't predefine all variants |
| D006 | Motifs must be asymmetric — symmetric patterns sound mechanical |
| D007 | Literal soprano repetition forbidden — consecutive bars and phrases must differ melodically |
| D008 | No downstream fixes — anything identified as a 'fix' indicates upstream design failure |
| D009 | Generators must use phrase_index — all pattern generators must vary output based on phrase position |
| D010 | Guards detect, generators prevent — guards report violations; generators must produce correct output |

## Architectural Rules

| ID | Rule |
|----|------|
| A001 | If-chains are a code smell — declarative rules instead |
| A002 | Same engine for all transforms — planner and executor share architecture |
| A003 | Rules are data — YAML, not code |
| A004 | Repeats are performance — composition produces the music once; repeats are a performer's choice |
| A005 | RNG in planner, determinism in executor — randomness creates variety during planning; executor must be deterministic given a plan |

## Variety Rules

Variety issues (var_001 bar duplication, var_002 sequence duplication) must be solved at the source, not by post-hoc correction.

| ID | Rule |
|----|------|
| V001 | Accompaniment patterns must vary per bar — use bar_idx offset into variation cycle |
| V002 | Accompaniment patterns must vary per phrase — use phrase_index to offset bar variations |
| V003 | Passage generators must vary per phrase — phrase_index offsets direction cycles, root shifts, pattern selection |
| V004 | Passage generators must vary per segment — internal segment variation prevents within-phrase repetition |
| V005 | Tremolo segments must be short — limit alternations to 6 notes to avoid endless_trill detection |

## Anti-Patterns (What NOT to Do)

| ID | Anti-Pattern | Why It Fails |
|----|--------------|--------------|
| X001 | Post-realization pitch adjustment | Operates on different data than guards (ornaments add notes after) |
| X002 | Iterative fix loops | May not converge; fixes for one constraint can violate another |
| X003 | Global signature tracking at MIDI level | Dichotomy between tracking point and guard check point |
| X004 | Separate bar-fix and sequence-fix passes | Can oscillate — fixing sequences reintroduces bar duplicates |
| X005 | rep counter starting at 0 for each phrase | Adjacent phrases produce identical patterns |
| X006 | Mutating function parameters | Causes invisible coupling; validation functions silently corrupt input; clone before modifying |

## Root Cause Analysis Protocol

When guards report violations:

1. **Identify the guard** — which constraint is violated (var_001, var_002, etc.)
2. **Trace to source** — which generator produced the violating material
3. **Find the invariant failure** — what property should the generator maintain but doesn't
4. **Fix the generator** — add variation parameters (phrase_index, bar_idx, segment offsets)
5. **Verify with guards** — guards should now report no violations

Never add code that "fixes" output after generation. If you find yourself writing a fix function, stop and trace upstream.
