# Continue

## Status: EPI-5 — Episode redesign from scratch

New chat starts here. The episode kernel system has been rejected.
Read this file, then `workflow/todo.md`, then `docs/Tier1_Normative/laws.md`,
then `docs/knowledge.md`, then `completed.md`.

---

## Context: what the invention looks like now

45 bars, 3 subject appearances (subject, answer, stretto), 5 episodes
of 6–7 bars each visiting keys vi→IV→V→ii→iii→I, one answer+CS
restatement at midpoint, one half-cadence before peroration, cadenza
grande at the end. Form planning is sound. Episode *content* is not.

Current output: every episode is mechanical transposition of 2–4 note
motifs with Viterbi fill in the other voice. No dialogue, no
fragmentation, no progressive compression, no voice exchange. Sounds
like wallpaper.

## What needs replacing

### Delete entirely
- `motifs/episode_kernel.py` — the kernel solver/chaining system
- `scripts/episode_kernel_demo2.py` — throwaway demo

### Replace the EPISODE branch in `builder/phrase_writer.py`
The section starting at the comment `# EPISODE: leader via episode kernel`
(around line 370) currently:
1. Calls `episode_source.generate_leader()` to get one voice
2. Generates the other voice via Viterbi with no knowledge of the fragment

This entire pattern (leader + independent fill) is wrong. Both voices
must state the same material in imitation.

### Rewrite `motifs/fragen.py` episode functions
`extract_kernels()` and `sequence_kernels()` are tied to the kernel
approach. The `extract_cells()` / `build_chains()` infrastructure may
be partially salvageable for fragment extraction but needs rethinking
in context of the new design.

### Keep (sound, do not change)
- `planner/imitative/subject_planner.py` — form planning, episode
  allocation, key journey. Episodes get bars and a from_key/to_key;
  the planner doesn't care how they're filled.
- `data/genres/invention.yaml` — brief settings
- `builder/imitation.py` — `_fit_shift()` is a clean octave-shift
  algorithm. `subject_to_voice_notes()` / `answer_to_voice_notes()`
  show the degree→MIDI→range pattern. Reusable for fragment placement.
- `builder/entry_renderer.py` — time-windowing logic for stretto is
  the same pattern needed for imitative overlap.

## What Bach episodes actually do

An episode is NOT a sequence of tiny atoms filling a bar count. It is
a **dialogue** between two voices built from recognisable thematic
material.

### The dialogue pair

1. **Fragment** — a recognisable 2–4 beat chunk extracted from the
   subject head, subject tail, CS, or (occasionally) a new sequential
   figure derived from thematic intervals. Must be long enough to be
   heard as "that's from the subject" — typically one bar in 4/4.

2. **Imitation** — the other voice states the same fragment, offset by
   1–2 beats, at the octave, 3rd, or 6th. The imitation can be strict
   (exact intervals) or tonal (adjusted to fit the local key).

### Sequencing

The dialogue pair is transposed diatonically (stepwise descent is most
common; ascent for building tension toward a structural event). Each
transposition = one iteration. Typically 2–4 iterations cover the
episode's key journey.

### Fragmentation (the critical missing piece)

On the last 1–2 iterations, the fragment is **halved** — only the first
half is stated, creating rhythmic compression and urgency toward the
next structural event. This is what makes episodes *go somewhere* rather
than repeating endlessly.

Example (Invention 1, bars 3–6):
- Iteration 1: full 1-bar fragment, descending by step
- Iteration 2: full 1-bar fragment, descending by step
- Iteration 3: first half only (2 beats), descending by step
- Iteration 4: first half only (2 beats) → arrives at next entry

### Voice exchange

In longer episodes (6+ bars), the leading voice swaps at the midpoint.
If soprano led iterations 1–2, bass leads iterations 3–4. This prevents
textural monotony.

## Available thematic material (subject09_2bar)

```
Subject: degrees (4,3,2,1,2,0,-2,-4,-2,-4,-3)
         durs    (1/16,1/16,1/16,1/16,1/4,1/4,1/4,1/4,1/4,1/4,1/4)
         ├─ HEAD: 4 semiquavers descending stepwise (degrees 4,3,2,1)
         └─ TAIL: crotchets (degrees 2,0,-2,-4,-2,-4,-3)

CS1:     degrees (-5,-3,-7,-5,-5,-4,-3,-2,-2,-4,-6,-2,-2,-5,-8)
         durs    (1/4,1/8,1/8,1/8,1/8,1/8,1/8,1/8,1/8,1/8,1/8,1/8,1/8,1/8,1/8)

Metre: 4/4, bar_length = 1 (Fraction)
Mode: major, tonic MIDI: 60
```

Natural fragments for episodes:
- **Subject head** (4 semiquavers, 1 beat): iconic descending scale run
- **Subject tail first half** (2 crotchets): degrees 2,0 — a 3rd drop
- **CS head** (crotchet + 2 quavers): degrees -5,-3,-7 — a leap-step
  figure

## Architectural proposal

### New module: `motifs/episode_dialogue.py`

Replaces `episode_kernel.py`. Single class `EpisodeDialogue`.

**Fragment extraction** (init-time):
- Extract 2–3 candidate fragments from subject head, subject tail, CS head
- Each fragment: tuple of (degree_offset, duration) pairs, 2–4 beats long
- Store as degree-relative patterns (transposable)

**Episode generation** (per-episode call):
- Inputs: bar_count, episode_key, start_offset, voice ranges, lead_voice,
  prior_midi for each voice
- Outputs: (soprano_notes, bass_notes) — both voices fully determined
- Algorithm:
  1. Choose fragment (rotate through candidates per episode)
  2. Compute iterations = bar_count ÷ fragment_bars (round)
  3. Compute step direction from key context (descending default)
  4. For each iteration:
     - Voice A states fragment at current transposition level
     - Voice B states same fragment, offset by imitation_delay beats,
       at imitation_interval (octave default)
     - Both converted to MIDI via degrees_to_midi + _fit_shift
  5. Last 1–2 iterations: fragment halved (fragmentation)
  6. Voice exchange at midpoint of longer episodes
  7. Return (soprano_notes, bass_notes)

**Vertical checks** (inline during generation):
- Strong-beat intervals between voices must be 3rds, 6ths, or octaves
- If a transposition level produces a strong-beat clash, shift the
  imitation interval (3rd→6th, 6th→3rd)

### Changes to `builder/phrase_writer.py`

Replace the EPISODE branch: instead of `episode_source.generate_leader()`
+ Viterbi fill, call `EpisodeDialogue.generate()` which returns both
voices.

### Changes to `builder/compose.py`

Replace `EpisodeKernelSource` instantiation with `EpisodeDialogue`.

## Key design decisions needed

1. **Imitation interval**: octave (safest), 3rd above/below (richer),
   6th? Should this be fixed or varied per episode?

2. **Imitation delay**: 1 beat (tight, invention-like) or 2 beats
   (looser, fugue-like)?

3. **Fragmentation rule**: halve on last N iterations? Or halve when
   remaining bars < fragment length?

4. **What fills the gaps?** When voice A finishes its fragment before
   voice B starts (or vice versa due to offset), what goes in the
   uncovered beats? Options: held note, free counterpoint, silence.

## Uncommitted changes from this session

All in working tree, not committed:

### Sound (commit these separately)
- `planner/imitative/subject_planner.py` — form planning (3-subject
  constraint, episodic development, HC reduction, episode bar lengths)
- `data/genres/invention.yaml` — pedal off

### To be replaced (don't commit)
- `motifs/episode_kernel.py` — will be deleted
- Episode branch in `builder/phrase_writer.py` — will be rewritten
- `motifs/fragen.py` — kernel-related functions will be replaced
- `scripts/episode_kernel_demo2.py` — will be deleted
