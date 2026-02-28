# Completed Work Log

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
