# FRAGEN — Fragment Episode Generator

## Purpose

Generate two-voice sequential episodes and hold-exchange bars from
subject-derived motivic cells. Replace Viterbi fill in all
non-thematic bars.

## The Problem

Viterbi finds consonant stepwise paths between knots but has no
motivic identity. Every filled bar sounds the same. In BWV 772,
nearly nothing is generic fill — episodes, hold-exchange bars and
free counterpoint are all built from subject fragments.

## Core Concepts

### Leader and Follower

Every episode bar has a **leader** voice and a **follower** voice.

The **leader** carries the recognisable motivic material — typically
the faster-moving voice (sixteenths, mixed rhythms). The leader's
cell chain is chosen first and determines the bar's rhythmic
character.

The **follower** provides consonant harmonic support — typically
slower notes (crotchets, minims, held pitches). The follower adapts
to the leader, not the other way round.

The leader/follower assignment can change between episodes. Episode 1
might have soprano leading; Episode 2 might have bass leading. This
creates textural variety.

### Cells

A **cell** is a contiguous subsequence of the subject (or its
inversion), defined by its degree tuple and duration tuple. Two notes
minimum.

---

## Step 1 — Build the Cell Vocabulary

### 1a. Extract Head and Tail

Split the subject at the first bar boundary using
`fragment_catalogue.py`:

    Subject: 4 2 0 | 0 1 2 3 4 5 4
    Head: (4,2,0) durs [1/4, 1/4, 1/2]       = 1 bar
    Tail: (0,1,2,3,4,5,4) durs [1/16 x4, 1/8 x2, 1/2] = 1 bar

### 1b. Generate Sub-Cells

For each of head and tail, extract every contiguous sub-sequence of
2 or more notes. This is all `fragment[start:end]` with
`end - start >= 2`.

From a 3-note head: 3 sub-cells (including the full head).
From a 7-note tail: 21 sub-cells (including the full tail).
Total: ~24 raw sub-cells.

Examples from the call_response subject:

    tail[0:4]  (0,1,2,3)     [1/16 x4]      dur = 1/4
    tail[0:6]  (0,1,2,3,4,5) [1/16 x4, 1/8 x2] dur = 1/2
    tail[4:6]  (4,5)         [1/8, 1/8]     dur = 1/4
    head[0:2]  (4,2)         [1/4, 1/4]     dur = 1/2

### 1c. Tonal Inversion

Invert every sub-cell diatonically around its first degree. A cell
with degrees `(0, 1, 2, 3)` becomes `(0, -1, -2, -3)`. Durations
are unchanged. This roughly doubles the cell count.

### 1d. Deduplication

Remove cells that are identical in both degree-offsets (relative to
first degree) and durations. Two cells from different source
positions that have the same shape are the same cell.

### 1e. Summary

Expected yield for a typical invention subject: **30–40 cells**
after sub-cells + inversions + dedup. Each cell carries:
- `name`: derivation tag (e.g. `tail[0:4]`, `head_inv[1:3]`)
- `degrees`: tuple of scale degrees (relative, first = 0)
- `durations`: tuple of Fraction values
- `total_duration`: sum of durations (in whole-note fractions)

---

## Step 2 — Build Leader Lines

A **leader line** fills exactly 1 or 2 bars by chaining one or
more cells end-to-end. The cells in a chain need not be the same
cell — a bar could be `tail[0:4]` + `tail[0:4]` + `head[0:2]`
(1/4 + 1/4 + 1/2 = 1 bar).

### 2a. Find All Chains

For a target of N bars (N = 1 or 2), find all ordered sequences of
cells from the vocabulary whose durations sum to exactly N × bar_length.

This is a bounded partition problem. Constraints to keep it tractable:

- **Maximum chain length**: 4 cells per bar (longer chains lose
  motivic identity — they become generic filler).
- **Minimum cell duration**: 1/8 whole note (two semiquavers). 
  Shorter cells are too small to carry meaning.
- **No immediate repetition of the same cell** unless the chain is
  a uniform sequence (i.e. all cells identical). A chain like
  A-A-B is fine (uniform A run + coda); A-B-A feels arbitrary.
  Actually — drop this rule if it kills too many options. Keep it
  simple: allow any ordering.

### 2b. Sequencing

Each cell in the chain is transposed diatonically from the previous.
The transposition step is uniform across the episode: typically −1
(descending sequence) or +1 (ascending).

Within a single iteration of the chain, the cells are at their
original relative pitches. At the next iteration, the entire chain
shifts by `step` degrees.

### 2c. Deduplication

Two leader lines are equivalent if they have:
- The same **rhythm profile** (sequence of durations)
- The same **contour direction** (ascending vs descending degree
  movement)

Remove duplicates. The surviving set represents genuinely different
rhythmic textures.

---

## Step 3 — Build Follower Lines

For each leader line, find follower material for the opposite voice.

### 3a. Rhythmic Contrast

The follower should have a **different rhythmic density** from the
leader:
- If the leader is mostly sixteenths → follower uses crotchets,
  minims, or a held pedal
- If the leader is mostly crotchets → follower can use quavers
  or sixteenths
- Avoid matching rhythmic density — that's imitative counterpoint,
  which is a different texture (stretto, not episode)

Enforce this with a simple rule: the follower's average note
duration must be at least 2× the leader's average note duration,
or vice versa.

### 3b. Follower Cell Selection

The follower line is also built from the cell vocabulary, using the
same chain mechanism as the leader. But the follower chain need not
fill the bar completely — gaps are filled with held notes (the last
sounding pitch sustains).

Alternatively, the follower can be a single held note for the entire
span (hold-exchange texture). This is the simplest follower type and
is always available as a fallback.

### 3c. Time Shifting

The follower chain can start at an offset from the leader:
- Offset 0: voices start together
- Offset +1/8 or +1/4: follower enters after the leader (dovetail)
- Offset −1/8 or −1/4: follower anticipates the leader

Dovetailed entries are characteristic of Bach's episodes. Try
offsets of 0, ±1/8, ±1/4 of the bar length.

### 3d. Consonance Checking

At every **strong beat** within the overlap region (beat 1 and beat 3
in 4/4), compute the vertical interval between leader and follower:

- Must be consonant per `CONSONANT_INTERVALS_ABOVE_BASS`
- No parallel perfect 5ths/octaves on consecutive strong beats
- Weak-beat dissonance is tolerated if the dissonant note is
  approached and left by step (passing tone pattern)

### 3e. Scoring and Ranking

Score each (leader, follower, offset) triple by:

1. **Strong-beat consonance rate** (higher = better, minimum 80%)
2. **Proportion of imperfect consonances** (3rds and 6ths preferred
   over 5ths and octaves — more = better)
3. **Rhythmic contrast ratio** (follower avg duration / leader avg
   duration — further from 1.0 = better)
4. **Voice-leading smoothness** at cell boundaries (penalty for
   leaps > 3 scale steps)
5. **Small bonus for dovetail offsets** (non-zero offset)

---

## Step 4 — Assemble Models

A **Model** is a fully specified (leader_chain, follower_chain,
offset, leader_voice) tuple that has passed consonance checking.

### 4a. Deduplicate Models

Two models are equivalent if, when normalised to the same starting
pitch, they produce:
- The same rhythm profile pair (leader + follower durations)
- The same interval column (vertical intervals at each note onset)

This catches transpositional mirrors that cell-name dedup misses.

### 4b. Select for Demo

Pick 6 diverse models:
- Alternate leader voice: soprano, bass, soprano, bass, ...
- Alternate direction: descending, ascending, descending, ...
- Alternate length: 1 bar, 2 bars, 1 bar, 2 bars, ...
- Maximise variety in rhythm profile pairs (no two episodes should
  have the same leader rhythm)

---

## Step 5 — Hold-Exchange

A hold-exchange is a leader/follower pair where the follower is a
single held pitch for the entire span. It is the simplest follower
type and deserves special treatment because it's a distinctive
Bach texture.

### Construction

1. Pick a leader cell from the vocabulary — prefer the full tail
   or full head (most recognisable) over small sub-cells.
2. Pick the running voice (soprano or bass).
3. Search for a (hold_degree, running_start) pair that gives:
   - 100% strong-beat consonance
   - Minimum 5 semitones voice separation
   - All notes within voice ranges
4. The two hold-exchange sections in the demo must differ in:
   - Leader cell (e.g. tail for one, head for the other)
   - Running voice (soprano for one, bass for the other)

---

## Step 6 — Sequence, Truncate, Write MIDI

### Sequencing

`sequence_model` generates iterations of the leader chain,
transposing by `step` degrees each time. Enough iterations are
generated to exceed the target bar count.

### Truncation

The output is truncated to exact bar boundaries. Notes that start
before the boundary but extend past it are shortened. Notes that
start at or after the boundary are dropped. This allows models
whose duration doesn't divide bars evenly to still produce
bar-aligned output — partial final iterations are normal in Bach.

### Start Degree Selection

For each model, search candidate start degrees (−3 to +15) and
pick the one that keeps all iterations of both voices within
`VOICE_RANGES` with maximum margin.

### MIDI Output

Degrees → MIDI via `degrees_to_midi`. One bar of silence between
sections. Each section starts at a bar boundary.

---

## Constraints

- Every episode fills exactly 1 or 2 bars. No fractional bars.
- Leader cells must be contiguous sub-sequences of the subject
  (or its inversion) — recognisably derived.
- Leader voice has faster average note duration than follower.
- Strong-beat consonance ≥ 80% in every episode.
- All notes within `VOICE_RANGES` (soprano index 0, bass index 3).
- No two episodes share the same rhythm profile pair + interval
  column.
- Hold-exchange sections use different cells and different voices.
- 1-bar silence between sections; each starts at bar boundary.

## Known Limitations

1. **No harmonic sequence model.** Episodes use uniform diatonic
   step, not circle-of-5ths bass motion.
2. **No modulation.** All iterations stay in the home key.
3. **No ornament.** Mordents, trills, turns are deferred.
4. **No genre character.** Generic episodes; genre shaping deferred
   to pipeline integration.
5. **Cell chains are uniform within an iteration.** The chain
   repeats identically at each transposition. Bach sometimes
   varies the chain between iterations.

---

## Validation Target

### Primary: `call_response.subject`

C major, 4/4, subject degrees `4 2 0 0 1 2 3 4 5 4`.

Expected cell vocabulary: ~30–40 cells.
Expected leader lines (1-bar + 2-bar): hundreds, reduced to ~20–30
distinct rhythm profiles after dedup.
Expected models after consonance filtering: 10–50.
Demo output: 6 episodes + 2 hold-exchange in `output/fragen_poc.mid`.

### Success Criteria

- ≥ 25 cells extracted (sub-cells + inversions + dedup).
- ≥ 10 distinct models survive consonance checking.
- 6 episodes, each with a unique rhythm profile pair.
- Mix of 1-bar and 2-bar episodes.
- Leader voice has faster notes than follower in every episode.
- Hold-exchange uses recognisable head/tail cells, not bare runs.
- Strong-beat consonance ≥ 80% across all episodes.
- All notes within voice ranges.

---

## File Layout

```
motifs/fragen.py          — Cell, Model, Episode types + generation logic
scripts/run_fragen.py     — standalone test + MIDI output
workflow/fragen.md        — this specification
```

## Dependencies

- `shared.constants` (MAJOR_SCALE, MINOR_SCALE,
  CONSONANT_INTERVALS_ABOVE_BASS, VOICE_RANGES)
- `motifs.head_generator.degrees_to_midi`
- `motifs.fragment_catalogue` (extract_head, extract_tail)
- `motifs.subject_loader` (SubjectTriple, load_triple)
- `midiutil` (MIDI output in test script only)
