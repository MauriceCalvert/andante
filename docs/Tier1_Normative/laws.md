# Laws

A001 If-chains forbidden, use declarative rules
A002 Same engine for all transforms
A003 Rules are data (YAML)
A004 Repeats are performance, not composition
A005 RNG in planner, determinism in executor
A006 Domain logic independent of infrastructure (ports/adapters)
D001 Validate, don't fix
D002 Constraints propagate upward
D003 Trace must debug without source
D004 Separate melodic approach from harmonic formula
D005 Compute patterns from budget, don't predefine variants
D006 Motifs must be asymmetric
D008 No downstream fixes
D009 Generators must use phrase_index
D010 Guards detect, generators prevent
D011 Voice-agnostic generation: no soprano/bass branching in generators. A voice is defined by its role and its pair, not its register name
L001 Try blocks forbidden
L002 Magic numbers forbidden, use constants
L003 Hard range constraints forbidden, soft hints only
L004 Voice crossing allowed only if intentional (e.g. invertible counterpoint)
L005 Duration arithmetic forbidden, use music_math
L006 Durations must be in VALID_DURATIONS
L007 Natural minor for melody, raised 6/7 cadential only
L008 Tonal targets = harmonic functions, not scale selection
L009 Tonal targets = functions not modulations, use home_key
L010 Leading tone in cadential context only (pre-cadential approach phrases in minor keys)
L011 While loops need guards and max_iterations
L012 Quantization forbidden, fix upstream
L013 MIDI gate time 95%
L014 Clone before modify, never mutate parameters
L015 NamedTuple/dataclass, not tuples
L016 Logging only, no print
L017 Single source of truth, inherit not repeat
L018 __init__.py must be empty, no re-exports
L019 ASCII only, no UTF8 symbols
L020 All arguments passed by keyword, no positional calls
L021 Brief fallback warning: when YAML/brief config makes something impossible, show warning (sarcastic but kind: what_failed, why, suggestion). Algorithmic fallbacks are normal runtime and do not use this.
S001 Performance practice out of scope; score notation only
V001 Generators vary via phrase_index, bar_idx, segment offsets
V002 Tremolo max 6 notes
X001 Anti: post-realization pitch adjustment
X002 Anti: iterative fix loops
X003 Anti: global signature tracking at MIDI level
X004 Anti: separate bar-fix and sequence-fix passes
X005 Anti: rep counter starting at 0 each phrase
M001 Bundle 3+ optional params that travel together through 2+ call layers into a frozen dataclass
M002 Function signatures max 10 params; bundle related groups into a context dataclass when exceeded
M003 Pass the source object, not its extracted fields, when the callee has access to both
M004 Frozen dataclasses with >15 fields must decompose into named sub-objects
M005 When the same extraction pattern appears at 3+ call sites, promote to a method on the source object
