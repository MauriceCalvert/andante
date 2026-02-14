# Task: INV-1 — Countersubject in All Subject Entries

Read these files first:
- `builder/phrase_writer.py`
- `builder/imitation.py`
- `builder/phrase_types.py`
- `motifs/fugue_loader.py`
- `data/genres/invention.yaml`

## Musical Goal

Every subject entry after the exordium should sound like a two-part
dialogue, not a subject against wallpaper. Currently the answer phrase
in the exordium pairs subject with countersubject — two distinct
melodic characters responding to each other. All later subject entries
pair the subject with Viterbi-generated filler that has no motivic
identity. The listener hears the subject announce itself and the other
voice meander aimlessly beside it. This violates Principle 2 (every
voice exists in relation to every other voice) and Principle 9
(absence of error is not presence of music).

After this change, every subject entry — in narratio, confirmatio, and
peroratio — should sound like the exordium answer: two recognisable
melodic threads moving in counterpoint. The countersubject provides the
motivic identity the free voice currently lacks.

## Idiomatic Model

**What the listener hears:** Two interlocking melodies with distinct
rhythmic profiles. The subject moves in its characteristic pattern; the
countersubject answers with complementary motion — where one sustains,
the other moves; where one leaps, the other steps. The listener
recognises both threads across sections, even when they swap voices.
This is the defining texture of a Bach invention.

**What a competent musician does:** In a two-part invention, the
countersubject accompanies every subject entry after the first solo
exposition. It is transposed to the local key of the entry and placed
in whichever voice is not carrying the subject. The CS is composed to
be invertible — it works both above and below the subject. The
musician transposes it to the local key and octave-shifts it into the
free voice's range.

**Rhythm:** The CS has its own rhythmic profile, typically
complementary to the subject (when the subject has short notes, the CS
has longer ones, and vice versa). No new rhythm generation is needed —
the CS's rhythm is pre-composed in the .fugue file.

**Genre character:** Invention — continuous two-voice keyboard
counterpoint. Every bar should have purposeful melodic activity in both
voices. The CS ensures the non-leading voice is never inert.

**Phrase arc:** The CS spans the subject's duration. The tail bars
(after the subject/CS end) still use Viterbi generation against the
schema, which provides the cadential approach. The arc is: motivic
dialogue (subject+CS) → free counterpoint toward cadence.

## What Bad Sounds Like

- **"Subject against wallpaper"** — the subject enters clearly but the
  other voice drifts in stepwise motion with no identity. Principle 2
  violated: the voices don't relate.
- **"Scale exercise"** — the free voice fills intervals between schema
  knots with diatonic steps, sounding like a practice drill. Principle
  9: absence of error, not presence of music.
- **"Same texture everywhere"** — subject entries sound identical to
  episode/free phrases because the accompanying voice has no
  distinguishing character. Principle 8: the subject entry should be a
  recognisable event, not uniform texture.

## Known Limitations

1. **Invertible counterpoint not verified.** The CS was composed against
   the subject in the original key/register. When voice assignments flip
   (soprano CS below bass subject, or vice versa), the vertical intervals
   invert. The CS generator already designs for invertibility, but we do
   not verify interval quality after transposition. A musician would check
   for new dissonances introduced by inversion. Acceptable for this phase
   because the CS generator's invertibility design covers most cases.

2. **No harmonic grid for imitative phrases.** Subject+CS phrases bypass
   the HarmonicGrid (HRL-2 wired it into the galant path only). The
   subject and CS are pre-composed with correct harmony, so this gap is
   acceptable. The Viterbi tail does lack harmonic guidance.

3. **Tail bars use generic Viterbi.** After the CS ends, the free voice
   reverts to Viterbi fill against schema knots. A musician would
   continue the motivic dialogue. Acceptable — episodes (INV-2) will
   address motivic continuity in non-entry phrases.

## Implementation

Modify `_write_subject_phrase` in `builder/phrase_writer.py`:

**When the subject entry is NOT monophonic** (i.e. `is_monophonic` is
False — there is a prior lower voice), place the countersubject in the
free voice instead of Viterbi-generating the full phrase.

Specifically, in the `lead_voice == 0` branch (soprano leads):
1. After generating `soprano_subject`, generate `bass_cs` using
   `countersubject_to_voice_notes(fugue, start_offset, plan.local_key,
   TRACK_BASS, plan.lower_range)`.
2. Tag first note with `lyric="cs"`.
3. Pad the CS to the tail offset (same as the subject).
4. If `needs_tail`: build tail_plan with `prev_exit_lower=bass_cs[-1].pitch`,
   generate tail bass via `_bass_for_plan(tail_plan, ...)` against
   `prior_upper + soprano_notes`.
5. Full bass = `bass_cs + tail_bass`.
6. No soprano Viterbi needed — soprano is the subject + tail soprano
   (already generated).

In the `lead_voice == 1` branch (bass leads):
1. After generating `bass_subject`, generate `soprano_cs` using
   `countersubject_to_voice_notes(fugue, start_offset, plan.local_key,
   TRACK_SOPRANO, plan.upper_range)`.
2. Tag first note with `lyric="cs"`.
3. Pad the CS to the tail offset.
4. If `needs_tail`: generate tail soprano via `generate_soprano_viterbi`
   against `bass_subject + tail_bass`.
5. Full soprano = `soprano_cs + tail_soprano` (from Viterbi over the
   full phrase, then slice to tail region), OR generate tail soprano
   separately against the full bass.

**The monophonic path (exordium first subject, solo entry) is unchanged.**
When `is_monophonic` is True, no CS is placed — the subject enters alone.

**The answer path (`_write_answer_phrase`) is unchanged.** It already
places the CS.

### Files to modify
- `builder/phrase_writer.py` — `_write_subject_phrase` only

### Files to read (not modify)
- `builder/imitation.py` — `countersubject_to_voice_notes` API
- `motifs/fugue_loader.py` — `LoadedFugue` structure
- `builder/phrase_types.py` — `make_tail_plan` API

## Constraints

- Do NOT modify `_write_answer_phrase` — it already works correctly.
- Do NOT modify `imitation.py` — the API already supports key
  transposition, voice assignment, and range shifting.
- Do NOT modify the monophonic path (first subject entry, solo).
- Do NOT create new files or modules.
- Before writing, grep for `countersubject_to_voice_notes` to confirm
  the existing API signature.

## Checkpoint (mandatory)

Run: `python -m scripts.run_pipeline invention default c_major -o output`

Bob:
1. In narratio, confirmatio, and peroratio subject entries: does the
   non-leading voice now carry recognisable melodic material (the CS),
   or does it still sound like filler?
2. Do the two voices relate to each other — contrary motion, rhythmic
   complementarity? (Principle 2)
3. Does the CS entry create a sense of "arrival" — a recognisable
   texture shift from the preceding phrase? (Principle 8)
4. What's still wrong?

Chaz:
For each of Bob's complaints, trace to a code location and propose a
minimal fix (wire before invent).

## Acceptance Criteria

- Every non-monophonic subject entry has `lyric="cs"` on the first note
  of the countersubject voice (CC-measurable proxy).
- The CS notes are transposed to the local key of the entry, not the
  home key (verify in .note file: CS pitches should reflect the section's
  key area).
- No new files created, no new dependencies added.
- All 8 genres run without error (`python -m scripts.run_pipeline <genre>
  default c_major` for each genre).
- Bob hears two distinct melodic threads in subject entries, not subject
  against filler (the real test).
