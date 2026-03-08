# Completed Work Log

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
were adjacent. `_anchor_entry()` was a band-aid that could only correct
by ±12 and was blocked by the same range constraint. The architecture
was backwards — generate then shoehorn, rather than place relative to
where you are.

**Fix**: Replaced `_apply_octave_shift` + `_anchor_entry` (~100 lines)
with `_place_near` (~10 lines). Each iteration is placed at the octave
multiple whose first note is nearest to the previous exit pitch:
`shift = round(delta / 12) * 12`. No range consultation — stepwise
transposition within the episode keeps register natural, and range is
a soft hint (L003). Assertions enforce that prior pitches are always
provided (episodes never start a piece).

**Also fixed**:
- Removed `EPISODE_BREATH_REST` — a forced crotchet of silence at episode
  end that created unidiomatic gaps. Episodes now fill allocated duration;
  assembly layer handles section joins via contiguous bar boundaries.
- Wired `-v` flag to set DEBUG on `motifs.episode_dialogue` and
  `builder.phrase_writer` (previously all debug logging was silenced).
- Fallback path now logs at WARNING level (visible without `-v`).

**Files**: `motifs/episode_dialogue.py`, `builder/phrase_writer.py`,
`scripts/run_pipeline.py`.

## EPI-5b — Episode parallel fix + Viterbi strong-beat parallel check (2026-02-28 late)

53 faults → 10 faults (−43).

**`motifs/episode_dialogue.py`**:
- Head-fragment trimmed to 3 semiquavers (was 4). Follower sustains at degree −2 instead of −3; ascending inter-iteration gaps reduce from potential tritone (4 diatonic steps) to P4 or smaller (3 diatonic steps). Oblique motion preserved.
- Ascending-aware start_degree: cross-phrase prior applied freely for ascending episodes, and for descending episodes only when nearest ≥ default (4). Prevents descending sequences from starting too low and generating grotesque register leaps.
- Entry anchor range check: the ±12 octave correction at i=0 is now only applied if all corrected notes remain within the voice range.

**`builder/phrase_writer.py`**:
- Cross-phrase prior fallback: when soprano_notes is empty (episode starts a new phrase plan), prior_upper_midi falls back to prior_upper[-1].pitch from the previous phrase.

**`viterbi/costs.py` + `viterbi/pathfinder.py`** (from earlier session):
- HC7 hard constraint: catches parallel perfects on consecutive strong/moderate beats separated by exactly one weak-beat note.

**Remaining 10 faults**: 3 parallel octaves at bars 24-25 (CS structural, HC3 can't avoid), 1 inter-iteration tritone at bar 12 (F-major structural Bb–E), 1 unprepared dissonance (pre-existing), 1 cross-relation (key-planning scope), 4 pre-existing cadence/stretto/rhythm faults.

## EPI-5 — Imitative dialogue episodes (2026-02-28)

Replaced the episode generation system entirely.

**Created** `motifs/episode_dialogue.py`:
- `EpisodeDialogue` class: extracts a 1-bar fragment from the subject (head + tail)
  and a half-fragment (first 2 beats). `generate()` produces both voices in
  close imitation (lower 10th, 1-beat offset) with stepwise sequential
  transposition, fragment compression in the last `min(2, bar_count//3)`
  iterations, and voice exchange at midpoint for 6+ bar episodes.
- `_adapt_to_available()`: fixes zero-duration bug when fragment last note
  exactly equals the follower's delay shortfall — removes rather than zeroing.

**Modified** `builder/phrase_writer.py`:
- EPISODE branch: replaced kernel + Viterbi companion with `EpisodeDialogue.generate()`.
- Updated `EpisodeKernelSource` → `EpisodeDialogue` in type annotations.

**Modified** `builder/compose.py`:
- Import and instantiation: `EpisodeKernelSource` → `EpisodeDialogue`.

**Deleted dead code**:
- `motifs/episode_kernel.py`
- `scripts/episode_kernel_demo2.py`
- `Kernel` dataclass, `extract_kernels`, `sequence_kernel`, `sequence_kernels`,
  `_kernel_subsequences`, `_invert_kernel`, `_dedup_kernels` from `motifs/fragen.py`.

**Remaining known issues** (future tasks):
- Parallel octaves in crotchet tails (structural — both voices use same fragment
  at fixed 10th offset; oblique motion in tail needed).
- Bass register excursion in flat keys (global octave shift too coarse).
- Ugly leaps at episode entry (octave shift applied after note generation).
