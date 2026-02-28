## EPI-6 — Paired-kernel episode variety

### Code changes

**motifs/extract_kernels.py** — complete rewrite:
- `Kernel` dataclass removed; replaced with `PairedKernel` (7 fields: name,
  upper_degrees, upper_durations, lower_degrees, lower_durations,
  total_duration, source).
- `extract_kernels()` removed; replaced with `extract_paired_kernels(fugue)`.
- Shared-onset slicing algorithm: builds onset lists for both voices, finds
  intersection (+ boundary at shorter_total), extracts notes per slice.
- Sub-pair extraction: for kernels with 3+ notes in longer voice, extracts
  first-2 and last-2 sub-pairs.
- Inversion (negate all degrees, re-normalise) and deduplication by content.

**motifs/episode_kernel.py** — complete rewrite:
- Removed all dead code (generate_leader, _to_builder_notes, fragen imports).
- New `EpisodeKernelSource`: calls `extract_paired_kernels`, builds pool
  (half-bar cap, 3 per source family), DFS chain solver.
- `generate(bar_count)` → flat list of PairedKernels or None.
- `_solve()`: simplified DFS, no distance/finish_degree constraint.
- Fragmentation ordering: segments sorted so last has shortest duration.

**motifs/episode_dialogue.py** — restructured:
- `EpisodeKernelSource` instantiated in `__init__`.
- Fallback (EPI-5b) moved to `_init_fallback()`.
- `generate()` tries paired-kernel path first; falls back when pool < 2 or
  no chain found.
- New `_generate_paired()`: voice exchange, sequential transposition,
  consonance check via `CONSONANT_INTERVALS_ABOVE_BASS`, per-iteration
  octave shift, entry anchoring — all EPI-5b fixes wired in.
- `_apply_consonance_check()`: at shared attacks, adjusts lower by ±1
  diatonic if transposition turned a consonance dissonant.
- `_generate_fallback()`: EPI-5b imitative dialogue, unchanged.

---

### Bob's assessment

**1. Do the 5 episodes sound different from each other?**

No. All 5 episodes use the same fallback fragment — the EPI-5b single-voice
imitative approach. The paired-kernel path was not activated.

Root cause: subject09_2bar's CS starts with a crotchet (duration 1/4)
while the answer starts with 4 semiquavers then crotchets. The shared-onset
slicing algorithm finds shared attack points every quarter note, but each
slice contains only 1 CS note (the crotchet) or only 1 answer note. The
rejection rule "fewer than 2 notes in either voice" eliminates all slices.
`extract_paired_kernels` returns an empty list → `EpisodeKernelSource.pool`
is empty → `generate()` returns None → fallback always used.

**2. Do both voices have independent rhythmic profiles?**

In fallback mode: leader plays the full 1-bar fragment (4 semiquavers + 3
crotchets); follower plays a 3-semiquaver head then sustains. There is
rhythmic asymmetry between leader and follower, but both derive from the
same subject material, not from independent CS/answer fragments.

**3. Audible compression/urgency in final iterations?**

For 2-bar episodes: frag_count = min(2, 2//3) = 0 — no compression (the
episode is too short to split). For 3-bar episodes: frag_count = 1 — last
iteration uses half-fragment. Compression is audible in longer episodes.

**4. Vertical consonance?**

10 faults — identical to pre-EPI-6. No new dissonance introduced. The
consonance check in `_apply_consonance_check` was never reached (fallback
path uses the old `_emit_voice_notes` without a consonance check, same
as EPI-5b). Pre-existing faults: bar 12.1 tritone, bars 25.1-25.3 parallel
octaves, bar 29.2 cross-relation, bar 40.1 ugly leap.

**5. Does each episode drive toward its cadential arrival?**

Yes — same EPI-5b stepwise sequential behaviour. Each episode sequences
the fragment one diatonic step per iteration, ascending or descending toward
the target key. No change here.

**6. What's still wrong?**

The primary goal — variety across episodes — is not met for subject09_2bar.
The paired-kernel architecture is structurally correct but silent for this
subject. All 5 episodes repeat the same texture.

---

### Chaz's diagnosis

Bob's complaint traces to one place: `extract_kernels.py:_extract_slices()`.

The CS for subject09_2bar has 15 notes with durations [1/4, 1/8×14]. The
answer has 11 notes [1/16×4, 1/4×7]. Shared onsets (intersection) = every
quarter-note boundary: {0, 1/4, 1/2, 3/4, 1, 5/4, 3/2, 7/4}. Each
consecutive slice spans exactly one quarter note.

In each slice:
- [0, 1/4): CS has 1 note (the opening crotchet) → rejected (< 2)
- [1/4, 1/2) onwards: answer has 1 note (one crotchet) → rejected (< 2)

The _KERNEL_MIN_NOTES = 2 check on BOTH voices in the same slice is never
satisfied simultaneously for this rhythmic pairing.

**Pool log** (via DEBUG): "0 raw slices from 3 pairings" → "0 total after
dedup". Pool size = 0. generate() returns None immediately.

The architecture will activate correctly for subjects where CS and answer
have two or more note onsets in the same shared-onset window — for example,
a subject in quavers against a CS in quavers, or a CS in semiquavers
against an answer in quavers.

**Minimal fix options**:

1. **Widen the minimum window**: instead of requiring 2 notes in BOTH voices
   within a shared-onset slice, require 2 notes in AT LEAST ONE voice. The
   second voice could have 1 note (a drone-like ground) — the spec rejects
   this as "pedal", but a compromise would allow 1 note in one voice only
   if that voice has a longer note that spans the full slice duration.

2. **Cross-slice windows**: allow overlapping windows by not restricting to
   consecutive shared-onset pairs. Try all pairs (t_start, t_end) from the
   shared-onset set, not just consecutive ones. This would find windows like
   [0, 1/2) where both voices have 2+ notes.

3. **Union-based slicing**: use ALL onset points from both voices as slice
   boundaries (union instead of intersection). This produces much smaller
   slices but more of them, increasing the chance of 2+ notes per voice.

Option 2 is the most compatible with the spec's existing language and would
immediately produce kernels for subject09_2bar. For example, [0, 1/2) has
CS = 1+2 = 3 notes, answer = 4 semiquavers = 4 notes → valid.

The fix is in `_extract_slices()`: replace consecutive-pair iteration with
all-pairs iteration, adding a cap on the maximum window width (e.g., ≤
bar_length) to avoid full-subject quotations.

---

**Acceptance criteria status**:
1. Variety (3 of 5 different): ✗ (all 5 fallback)
2. Independence (different rhythms): ✗ (fallback, same fragment)
3. Consonance (no new faults): ✓ (10 faults, same as EPI-5b)
4. Compression: partial (only in 3+ bar episodes)
5. No regression: ✓ (10 faults ≤ 10)
6. Pipeline stability: ✓ (clean run, no crashes)

Please listen to the MIDI and let me know what you hear.
