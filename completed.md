## Technique 6 — Compound melody implied-voice cost (2026-03-09)

Added `implied_voice_dissonance_cost` to `viterbi/costs.py`. On leaps >= 3
diatonic steps (4th or larger), penalises departure pitches that don't fit the
current chord (COST_COMPOUND_MELODY_DISSONANCE = 18.0). Uses chord_pcs when
available, falls back to is_consonant. Wired into `transition_cost` as
`"implied_v"`. Added `technique_6` pass-through in `builder/techniques.py` and
`"compound_melody"` dispatch in `builder/episode_dialogue.py`. Bug fix:
`is_consonant` fallback was called with two args instead of interval.
Minuet demo: 2/2 qualifying leaps consonant, no step distribution shift, no
new parallel 5ths/8ves.

## Technique 5 — Harmonic rhythm acceleration (2026-03-09)

Implemented `_generate_accelerating` in `builder/episode_dialogue.py`.
Final `ACCEL_BAR_COUNT` (= 2) bars emit the half-fragment twice per bar at
midpoint and endpoint transposition levels. Normal bars unchanged. Guard falls
back to `_generate_fallback` when `bar_count < ACCEL_BAR_COUNT + 1`.

**Listening result**: rhythmic acceleration audible and immediate. 1.82x note
density in bars 8–9 vs bars 4–7. Subject head (four falling semiquavers)
recognisable in both half-bar slots.

**Known limitation**: with flat register trajectory (−1 step over 6 bars),
midpoint = endpoint — both half-bar slots land on the same pitch. Harmonic
motion is a rhythmic proxy only. EPI-7 scope.

**Files**: `builder/episode_dialogue.py`, `builder/techniques.py`,
`briefs/builder/invention_t5_demo.brief`.

## Technique 3 dispatch fix (2026-03-09)

`technique_3` was absent from `_TECHNIQUE_DISPATCH`. Added `technique_3` to
`builder/techniques.py` as a pass-through to `_generate_fallback` (suspensions
act at Viterbi cost level globally). Wired `"suspensions"` into
`_TECHNIQUE_DISPATCH` in `builder/episode_dialogue.py`.

## Technique 4 — Circle-of-fifths sequence (2026-03-09)

See entry in completed.md above (written earlier this session).

## Technique 2 — Parallel-sixths episode texture (2026-03-08 T16:00)

Implemented `_generate_parallel` in `builder/episode_dialogue.py` and replaced
the `technique_2` stub in `builder/techniques.py`.

**What it does**: both voices emit the subject fragment at identical onsets
(no delay, no gap-fill), the lower voice at a diatonic sixth below (PARALLEL_SIXTH_OFFSET
= -5). Falls back to a tenth (PARALLEL_TENTH_OFFSET = -9) when the sixth pushes
any bass note outside `lower_range`. `_apply_consonance_check` called after
each interval selection to handle degree-7 dissonances.

**Listening result**: lockstep texture is immediately distinct from imitative
exposition (no chase, no delay). In this demo run, the register planner supplied
a near-flat schedule (actual prior C5 vs. planned E5 start), so all 6 bars
repeat at the same pitch -- no sequential transposition. Also, the subject
fragment's wide span (6 diatonic steps) produces a minor-7th inter-bar leap
that repeats 5 times. Both are documented Known Limitations (brief section 4).

**Open complaints (Bob)**: no sequential transposition in demo run; repeated
minor-7th inter-bar leap.

## Technique 1 — Fixed-fragment sequential episode (2026-03-08)

Implemented `technique_1` in `builder/techniques.py`.

**What it does**: replaces the front-loaded schedule from `generate()` with
a fixed-interval one. `_fixed_schedule` computes `steps_per_bar =
round(total_delta / bar_count)`, defaulting to −1 (descending step) when
that rounds to zero. Both voice schedules recomputed independently; imitation
offset, fragment, and fallback path unchanged.

**Listening result**: one fragment, descending one diatonic step per bar,
clearly audible as a sequence by the second repetition. 3-bar demo passes
listening gate. 4+ bars approaches monotony in isolation; correct in context
per roadmap rationale.

**Known limitation**: if the planner schedules a total descent exceeding the
soprano range, the backstop range warnings still fire (planner scope, not
technique_1 scope).

**Files**: `builder/techniques.py`.

## EPI-7 — Episode octave placement rewrite + breath rest removal (2026-02-28)

**Problem**: Jarring octave leaps (e.g. F4→F5) between consecutive episodes.

**Root cause**: Episodes were generated at a fixed abstract octave then
shifted into range via `_apply_octave_shift()`. When a fragment spanned
most of the voice range, only one octave-multiple shift fit strictly
within range, forcing 12-semitone leaps even when exit and entry pitches
were adjacent. The architecture was backwards — generate then shoehorn.

**Fix**: Replaced `_apply_octave_shift` + `_anchor_entry` (~100 lines)
with `_place_near` (~10 lines). Each iteration is placed at the octave
multiple whose first note is nearest to the previous exit pitch.
No range consultation — stepwise transposition within the episode keeps
register natural, and range is a soft hint (L003).

**Also fixed**: Removed `EPISODE_BREATH_REST`. Wired `-v` flag to set DEBUG
on `motifs.episode_dialogue` and `builder.phrase_writer`. Fallback path now
logs at WARNING level.

**Files**: `motifs/episode_dialogue.py`, `builder/phrase_writer.py`,
`scripts/run_pipeline.py`.

## EPI-5b — Episode parallel fix + Viterbi strong-beat parallel check (2026-02-28 late)

53 faults → 10 faults (−43).

## EPI-5 — Imitative dialogue episodes (2026-02-28)

Replaced episode generation system entirely. Created `motifs/episode_dialogue.py`.
Deleted `motifs/episode_kernel.py`, dead kernel code from `motifs/fragen.py`.

## Earlier work

EPI-5, EPI-5b, EPI-7, M001–M005, CLR-1, ICP-2, PED-2, USI-3, USI-2,
CAD-1, FIX-1, USI-1, PSF-1, ICP-1, STV-1, BM, EXP-1, and all prior phases.
