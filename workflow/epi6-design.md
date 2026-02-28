# EPI-6 — Paired-kernel episode variety

## Problem

All 5 episodes use the same single fragment (subject head+tail). The piece
sounds like one idea repeated. Bach's episodes use different thematic
fragments in each episode, drawn from subject and countersubject material.

## Core idea

Episodes are built from **paired kernels** — frozen two-voice units where
soprano degrees+durations and bass degrees+durations were extracted from
the exposition, where subject and countersubject sound simultaneously.
Vertical consonance is inherited from the original counterpoint, not
solved per-episode.

This is what Bach does: the subject and countersubject are composed as an
invertible pair. Episodes take fragments of that pre-tested pair and
sequence them. The verticals are pre-guaranteed.

## Paired kernel extraction

### Source material

The subject/CS overlap in the exposition. Both voices are sounding; the
vertical intervals are already proven.

### Slice points

Paired fragments are sliced at **shared onsets** — time points where both
voices have a note attack. In a typical invention (subject in crotchets,
CS in quavers or vice versa), shared onsets fall on every crotchet beat.

### Rules

1. Start of pair: must be a shared onset (both voices attack).
2. End of pair: must be a shared onset. If a note extends past the slice
   point, truncate to fit. Chain is gapless: second pair starts where
   first ends.
3. **Minimum 2 notes per voice** within the pair. If either voice
   contributes fewer than 2 onsets, reject the pair. A single sustained
   note is a drone, not a fragment.
4. Maximum 4 notes in the longer voice (same as current _KERNEL_MAX_NOTES).
   Longer fragments sound like subject quotations.
5. Normalise: shift soprano degrees so first = 0; shift bass degrees by
   the same amount (preserving the interval between voices).
6. Inversion: invert both voices (negate all degrees in both).
7. Dedup by (soprano_degrees, soprano_durations, bass_degrees, bass_durations).

### Additional source pairs

- Subject (soprano) against CS (bass) — the primary pairing
- Answer (soprano) against CS (bass) — if answer differs from subject,
  gives additional material
- CS (soprano) against subject (bass) — invertible counterpoint: swap
  voices, adjust by inversion distance

### Data type

```python
@dataclass(frozen=True)
class PairedKernel:
    name: str                            # e.g. "subj_cs[0:4]"
    upper_degrees: tuple[int, ...]       # soprano, relative (first = 0)
    upper_durations: tuple[Fraction, ...]
    lower_degrees: tuple[int, ...]       # bass, relative to same base
    lower_durations: tuple[Fraction, ...]
    total_duration: Fraction              # shared onset to shared onset
    source: str                          # "subj_cs", "ans_cs", "cs_subj"
```

## Episode generation (revised EpisodeDialogue)

### Init

Build a pool of PairedKernels via the extraction above. Track which
combinations have been used (same `_used` set concept from the old
EpisodeKernelSource).

### generate() per episode

1. **Chain paired kernels** to fill the episode's bar count. Different
   combination each call. The chain solver picks kernels whose total
   durations sum to the target, similar to the old `_solve` DFS but
   now each atom is a PairedKernel.

2. **Sequential transposition**: each iteration (bar) transposes both
   voices by one diatonic step, same as current. The vertical intervals
   are preserved because both voices shift together.

3. **Fragmentation** in final iterations: use shorter kernels (2-note
   pairs) to build urgency toward the cadence.

4. **Voice exchange** at midpoint for long episodes: swap which voice
   gets upper_degrees vs lower_degrees. This is free because the pairs
   are from invertible counterpoint.

5. Per-iteration octave shift, entry anchoring, range checks — all
   carried forward from EPI-5b.

### Follower independence

Both voices are thematically derived but **genuinely independent** —
different rhythms, different melodic contours. The soprano kernel might
be semiquavers while the bass kernel is quavers. This is real two-voice
texture, not one line at a 10th.

## Why this scales to SATB

The outer voices (soprano + bass) carry the structural counterpoint via
paired kernels. Inner voices (alto + tenor) fill harmony between them —
same as everywhere else. Bach's 4-voice fugue episodes typically have
two active thematic voices and two voices providing harmonic fill or
resting. The paired kernel design doesn't need reworking for SATB.

## Existing code to keep

- `extract_kernels.py` — rewrite to produce PairedKernels instead of
  single-voice Kernels. The subsequence extraction and inversion logic
  are the right shape, just need to operate on pairs.
- `episode_dialogue.py` — rewrite generate() to chain paired kernels
  instead of repeating one fragment. Keep the octave shift, entry
  anchoring, range checking, fragmentation, voice exchange.
- `episode_kernel.py` — the `_solve` DFS and `_used` tracking are
  the right approach for chain assembly. Adapt to PairedKernels.

## Existing code to discard

- `_build_bar_fragment` and `_build_half_fragment` in episode_dialogue.py
  (single fixed fragment — the thing that makes it boring)
- The "same fragment at a 10th" approach entirely

## Implementation phases

**EPI-6a**: Paired kernel extraction. Rewrite extract_kernels.py to
produce PairedKernels from the subject/CS overlap. Unit: standalone
module, testable without pipeline.

**EPI-6b**: Chain solver. Adapt the _solve DFS from episode_kernel.py
to work with PairedKernels, filling target durations. Integrate _used
tracking for cross-episode variety.

**EPI-6c**: Wire into EpisodeDialogue.generate(). Replace single-fragment
iteration with paired-kernel chains. Keep all EPI-5b fixes (octave shift,
entry anchor, range check). Update phrase_writer.py and compose.py as
needed.

## Known limitations (to name in the brief)

- Paired kernels inherit verticals from the exposition in the home key.
  After diatonic transposition, some intervals change quality (e.g.
  perfect 5th becomes diminished 5th when the sequence lands on scale
  degree 7). This is a fault, not an acceptable approximation — Bach
  adjusts these cases rather than blindly transposing. After shifting
  both voices by a diatonic step, each vertical interval must be
  checked. If a consonance has become dissonant, the offending note
  is adjusted by the minimum diatonic step to restore consonance.
- Kernel chains may not land exactly on the target degree for the next
  section. The old _solve addressed this with distance/finish_degree
  constraints. The new solver needs the same.
- Episode harmony: each sequential iteration implies a local chord
  (e.g. descending step: I→vii°→vi→V). This feeds into the
  HarmonicGrid infrastructure via harmony_projection.py, same as
  entry phrases. See "Episode Harmony" in docs/imitative_design.md.
