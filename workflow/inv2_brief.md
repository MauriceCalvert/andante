# Task: INV-2 — Episodes from Subject Fragments

Read these files first:
- `builder/phrase_writer.py`
- `builder/imitation.py`
- `builder/phrase_planner.py` (specifically `_assign_imitation_roles`)
- `builder/phrase_types.py`
- `motifs/fugue_loader.py`
- `data/genres/invention.yaml`
- `data/schemas/schemas.yaml` (fonte, monte entries — sequential schemas)

## Musical Goal

Between subject entries, Bach invention episodes sound like
developmental passages — fragments of the subject tossed between the
two voices in descending or ascending sequences. Currently, these
phrases fall through to the galant path: schema knots → Viterbi fill.
The result is generic stepwise counterpoint with no motivic connection
to the subject. The listener hears a subject entry, then amnesia, then
another subject entry. The episodes should sound like the subject's
material being explored in new keys — a musical conversation about the
subject, not a digression from it.

This addresses Principle 7 (structure serves expression — episodes
develop the argument, not fill space) and Principle 2 (the voices
respond to each other by exchanging the same material).

## Idiomatic Model

**What the listener hears:** A descending (fonte) or ascending (monte)
sequence where each step echoes the subject's opening gesture. One
voice states a 1-bar fragment, then the other voice takes it a step
lower (or higher), while the first voice plays free counterpoint
against it. The exchange creates momentum — a sense of directed motion
through key areas, not static texture.

**What a competent musician does:** Extracts the first bar of the
subject (the "head") as a 1-bar fragment. Places it in alternating
voices at each step of the sequence, transposed to the local key of
that step. The free voice either plays the tail fragment or
free counterpoint. The sequential schemas (fonte, monte) already encode
the key sequence — each segment position has its own key.

In a typical Bach invention fonte episode (4 bars):
- Bar 1: soprano states head fragment in key of segment 1
- Bar 2: bass states head fragment in key of segment 2
- Bar 3: soprano states head fragment in key of segment 3
- Bar 4: bass states head fragment in key of segment 4

The fragment is always the same rhythmic/intervallic shape, transposed.
The free voice moves in complementary rhythm — when the fragment has
short notes, the free voice has longer values, and vice versa.

**Rhythm:** The fragment carries the subject's rhythm. No new rhythm
generation needed — the fragment's rhythm is a slice of the
pre-composed subject. The free voice uses Viterbi generation with its
existing rhythm infrastructure.

**Genre character:** Invention — continuous motivic development. Episodes
are not "filler between entries" but developmental passages that propel
the music forward through key areas. The sequential descent/ascent
creates harmonic momentum.

**Phrase arc:** Each sequence step is one bar. The overall episode
descends (fonte) or ascends (monte) through key areas, creating
directed harmonic motion. Individual steps are self-contained
(fragment statement + free counterpoint); the arc is the key
trajectory, not the individual step.

## What Bad Sounds Like

- **"Amnesia"** — subject entries are clearly motivic, but everything
  between them is generic stepwise fill. No connection between subject
  material and episode material. Principles 2, 7 violated.
- **"Two solos"** — each voice wanders independently in the episode,
  no exchange of material, no sense of dialogue. Principle 2 violated.
- **"Static"** — the episode stays in one key area with no harmonic
  direction. Sounds like the music stalled between entries. Principle 7
  violated: no forward motion.
- **"Mechanical sequence"** — the fragment is placed correctly but the
  free voice is inert (held notes, repeated pitches). Principle 9:
  absence of error, not presence of music.

## Known Limitations

1. **Only the head fragment is used.** A musician might also use the
   tail, inverted fragments, or combinations. The code extracts only
   the first bar. Acceptable for this phase — head-based episodes are
   the most common type.

2. **Free voice is Viterbi, not motivic.** The voice not carrying the
   fragment is Viterbi-generated, not derived from subject material. A
   musician would often derive it from the tail or CS. Acceptable —
   the Viterbi solver produces competent counterpoint, and the fragment
   placement already gives motivic identity to the episode.

3. **Fragment alignment assumes 1 fragment per degree position.** If the
   schema has fewer degree positions than bars, some bars may lack
   fragment placement. The code handles this by Viterbi-filling
   unassigned bars.

4. **No harmonic grid for episode phrases.** Episode phrases bypass
   HarmonicGrid (same limitation as subject entries). The fragment is
   pre-composed with correct harmony; the free Viterbi voice lacks
   harmonic guidance. Acceptable for this phase.

## Implementation

### New file: `builder/episode_writer.py`

**`extract_head_fragment`**`(fugue: LoadedFugue, metre: str) -> tuple[tuple[int, ...], tuple[float, ...]]`

Returns (degrees, durations) for the first bar of the subject.
- Parse metre to get bar_length as Fraction.
- Walk through `fugue.subject.durations`, accumulating total duration.
- Stop when accumulated duration reaches bar_length.
- Return the corresponding slices of degrees and durations.
- Assert the fragment has at least 2 notes.

**`fragment_to_voice_notes`**`(degrees, durations, start_offset, target_key, target_track, target_range, mode) -> tuple[Note, ...]`

Places a fragment in a specific voice at a specific key.
- Convert degrees to MIDI via `degrees_to_midi` (from `motifs.head_generator`).
- Octave-shift into target_range (same algorithm as `subject_to_voice_notes`).
- Build Note tuples with correct offset, pitch, duration, voice.

**`write_episode`**`(plan: PhrasePlan, fugue: LoadedFugue, prior_upper, prior_lower) -> PhraseResult`

Core episode writer:
1. Extract head fragment via `extract_head_fragment`.
2. Determine sequence steps from `plan.degree_positions` (one step per
   degree position).
3. Determine starting voice from `plan.lead_voice` (0=soprano first,
   1=bass first).
4. For each step:
   a. Compute the step's offset from `degree_positions[step]`.
   b. Get the step's key from `plan.degree_keys[step]`.
   c. Place fragment in the current voice via `fragment_to_voice_notes`.
   d. Tag the first note with `lyric="episode"`.
   e. Alternate voice for the next step.
5. Collect all pre-composed fragment notes by voice.
6. For bars/beats NOT covered by a fragment:
   - If soprano has fragment, generate bass via Viterbi against it.
   - If bass has fragment, generate soprano via Viterbi against it.
   - If neither has fragment (shouldn't happen normally), fall through
     to galant path.
7. Assemble full soprano_notes and bass_notes in chronological order.
8. Return PhraseResult.

**Simplification for this phase:** Rather than interleaving fragment
placement with per-step Viterbi, a simpler approach:
- Place all fragments first (building a sparse timeline of pre-composed
  notes per voice).
- Then generate the free voice for each step as a mini-phrase using
  generate_voice (or generate_soprano_viterbi / _bass_for_plan) with
  the fragment notes as the "existing voice."

If this interleaving proves too complex for one session, an acceptable
fallback: place the fragment in the lead voice only (no alternation)
for the full episode, and Viterbi-generate the other voice against it.
This is less idiomatic but still better than no motivic content.

### Modified: `builder/phrase_planner.py`

In `_assign_imitation_roles`:
- After assigning "subject" and "answer", any remaining non-cadential
  phrase in a section with `lead_voice` gets `imitation_role="episode"`.
- Currently these phrases have `imitation_role=None` and fall through
  to the galant path.

Change the loop: after `assigned >= 1` (or `>= 2` in exordium), set:
```
plans[i] = replace(plans[i], imitation_role="episode")
```

### Modified: `builder/phrase_writer.py`

In `write_phrase`, add a dispatch case for `"episode"`:
```python
if plan.imitation_role == "episode":
    from builder.episode_writer import write_episode
    return write_episode(
        plan=plan,
        fugue=fugue,
        prior_upper=prior_upper,
        prior_lower=prior_lower,
    )
```

Place this after the "subject" and "answer" cases, before the assert.

### Files to modify
- `builder/phrase_planner.py` — `_assign_imitation_roles` (~5 lines)
- `builder/phrase_writer.py` — `write_phrase` dispatch (~8 lines)

### New files
- `builder/episode_writer.py` — fragment extraction + episode generation

## Constraints

- Do NOT modify `imitation.py` — the existing API is sufficient, and
  `fragment_to_voice_notes` in episode_writer is a simpler variant
  specialised for 1-bar fragments.
- Do NOT modify the subject or answer paths — they are correct.
- Do NOT modify cadence writing — cadential phrases are unchanged.
- Use `degrees_to_midi` from `motifs.head_generator` for pitch conversion
  (same function used by fugue_loader).
- If the schema has no `degree_keys` (edge case), fall through to the
  galant path for that phrase (no fragment placement without key data).
- Before proposing any new mechanism, grep for existing code first.

## Checkpoint (mandatory)

Run: `python -m scripts.run_pipeline invention default c_major -o output`

Bob:
1. In narratio and confirmatio episodes: does each voice take turns
   stating a recognisable fragment of the subject?
2. Do the fragment statements descend through keys (fonte) or ascend
   (monte)? Is there a sense of harmonic direction? (Principle 7)
3. Does the free voice (the one not carrying the fragment) sound like
   counterpoint against the fragment, or like unrelated filler?
   (Principle 2)
4. Compare an episode phrase to a subject-entry phrase: are they
   texturally distinct? The episode should sound developmental, the
   entry should sound thematic. (Principle 8)
5. What's still wrong?

Chaz:
For each of Bob's complaints, trace to a code location and propose a
minimal fix (wire before invent).

## Acceptance Criteria

- Episode phrases have `lyric="episode"` on fragment-entry notes
  (CC-measurable proxy).
- Fragment pitches in the .note file reflect transposition to the
  degree key of each sequence step (not home key).
- At least 2 of the 4 non-cadential non-subject phrases in a typical
  invention are assigned `imitation_role="episode"`.
- All 8 genres run without error.
- Bob hears subject-derived material in episodes, not generic fill
  (the real test).
