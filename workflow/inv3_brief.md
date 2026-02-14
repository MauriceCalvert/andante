# Task: INV-3 — Stretto

Read these files first:
- `builder/phrase_writer.py`
- `builder/imitation.py`
- `builder/phrase_planner.py` (specifically `_assign_imitation_roles`)
- `builder/phrase_types.py`
- `motifs/fugue_loader.py`
- `data/genres/invention.yaml`

## Musical Goal

The peroratio (final section) should climax with both voices stating
the subject simultaneously, offset by a short delay. This is stretto —
the most intense form of imitative counterpoint, where the subject
entries overlap. Currently the peroratio's non-cadential phrase is
either a subject entry (one voice thematic, the other Viterbi filler)
or an episode. Neither creates the rhetorical climax a peroratio
demands.

Stretto creates urgency because the second voice enters before the
first has finished, compressing the subject's material into a tighter
space. The listener hears the subject piling on itself — tension that
resolves at the final cadence. This addresses Principle 1 (tension and
release at the section scale) and Principle 7 (structure serves
expression — the peroratio IS the climax).

## Idiomatic Model

**What the listener hears:** The subject begins in one voice. Before
it finishes, the second voice enters with the same subject (or its
tonal answer), creating a dense overlap where both voices carry
thematic material simultaneously. The texture thickens audibly. After
the overlap, the music drives toward the final cadence. The effect is
compression and intensification — the musical argument reaching its
tightest point before the resolution.

**What a competent musician does:** Places the subject in voice A at
the phrase start. After a delay (typically 1-2 beats, or half a bar),
places the subject (transposed to the answer key or at the unison) in
voice B. The two entries overlap. During the overlap, both voices are
pre-composed — no improvised counterpoint needed, because the subject
is designed to work against itself at this interval and delay.

The delay determines intensity:
- Close stretto (1 beat): maximum compression, very intense
- Moderate stretto (half a bar, 2 beats in 4/4): balanced
- Loose stretto (1 bar): gentle overlap, less intense

For a 2-bar subject in 4/4, a 2-beat delay gives 6 beats of overlap
(1.5 bars), which is substantial and effective.

Before voice B enters: voice B either rests or holds its exit pitch
from the previous phrase. After both voices finish the subject: the
remaining bars (if any) are free counterpoint toward the cadence,
generated via the existing tail mechanism.

**Rhythm:** Both voices carry the subject's rhythm simultaneously.
Where they overlap, the rhythmic density doubles. No new rhythm
generation — both parts are pre-composed.

**Genre character:** Invention peroratio — the climactic section. The
stretto should be the densest, most intense texture in the piece.
Everything after it (the final cadence) is resolution.

**Phrase arc:** Anticipation (voice B waiting) → overlap entry (sudden
textural thickening) → simultaneous subjects (maximum density) →
cadential approach (tail bars). The arc within the stretto phrase moves
from tension (overlap) to resolution (cadence).

## What Bad Sounds Like

- **"No climax"** — the peroratio sounds like any other section. The
  final cadence arrives without rhetorical preparation. Principle 1
  violated: no tension for the release to resolve.
- **"Collision"** — both voices enter simultaneously at unison or
  octave with no offset, producing doubling rather than counterpoint.
  Principle 2 violated: the voices aren't relating, they're duplicating.
- **"Harmonic wreck"** — the overlapping subjects produce dissonances
  that don't resolve. Principle 3 violated: uncontrolled dissonance.
  This is the main risk. Mitigation: use the tonal answer (at the 5th)
  for voice B, which produces consonant intervals. Or use the original
  subject at the octave.
- **"Premature"** — stretto appears in the middle of the piece, not at
  the climax. Principle 7 violated: structure not serving expression.
  This is prevented by placing stretto only in the peroratio.

## Known Limitations

1. **Fixed delay, not optimised.** The stretto delay is a configuration
   constant (e.g. 2 beats), not computed from the subject's
   self-compatibility at different offsets. A musician would test
   multiple delays and choose the one that produces the best
   counterpoint. Acceptable for this phase — a half-bar delay is a safe
   default for most 2-bar subjects.

2. **No verification of overlap consonance.** The overlapping subjects
   are placed without checking whether the vertical intervals produce
   acceptable counterpoint. The fault scanner will detect problems
   post-hoc, but the stretto writer does not avoid them. Acceptable
   because: (a) subjects designed for invertible counterpoint tend to
   work in stretto, (b) the fault log will flag issues for future
   refinement.

3. **Voice B always gets the subject at the same pitch level.** A
   musician might use the tonal answer, the subject at the octave, or
   the subject inverted. This phase uses the subject transposed to the
   local key and octave-shifted into range — the simplest option.

4. **No harmonic grid.** Same limitation as INV-1: stretto phrases
   bypass HarmonicGrid. The subjects are pre-composed; tail bars lack
   harmonic guidance.

5. **The delay must not exceed the subject length.** If
   `delay >= subject_duration`, there is no overlap, and the stretto
   degenerates into a normal entry + entry. The implementation asserts
   `delay < subject_duration`.

## Implementation

### Modified: `builder/phrase_planner.py`

In `_assign_imitation_roles`:
- In the last section (peroratio), assign `imitation_role="stretto"` to
  the first non-cadential phrase with `lead_voice`, instead of "subject".
- All other sections: unchanged (subject, answer, episode as before).

Detection: the last section is `sec_idx == len(section_starts) - 1`.
In that section, the first non-cadential phrase with lead_voice gets
"stretto" instead of "subject".

### Modified: `builder/phrase_writer.py`

Add `_write_stretto_phrase` function and dispatch case.

**`_write_stretto_phrase(plan, fugue, prior_upper, prior_lower)`:**

1. Determine `lead_voice` (0 or 1) and `follow_voice` (the other).
2. Compute `bar_length` from metre.
3. Set `delay = bar_length` (1 bar delay — moderate stretto for 2-bar
   subject). Store as a constant `STRETTO_DELAY_BARS = 1`.
4. Compute `delay_offset = delay * bar_length` as Fraction.
5. Compute `subject_duration` from the sum of `fugue.subject.durations`.
6. Assert `delay_offset < subject_duration` (otherwise no overlap).

**Place voice A (lead):**
- Subject in lead voice at `plan.start_offset`, local key, lead range.
- Use `subject_to_voice_notes(fugue, plan.start_offset, plan.local_key,
  lead_track, lead_range)`.

**Place voice B (follower):**
- Subject in follow voice at `plan.start_offset + delay_offset`, local
  key (or dominant key for tonal contrast — use local key for simplicity
  this phase), follow range.
- Use `subject_to_voice_notes(fugue, plan.start_offset + delay_offset,
  plan.local_key, follow_track, follow_range)`.

**Before voice B's entry (bars 1 to delay):**
- Voice B holds the exit pitch from `prior_upper` or `prior_lower`
  (depending on which voice B is) as a single held note from
  `plan.start_offset` to `plan.start_offset + delay_offset`.
- If no prior notes exist, use a rest.

**After both subjects end:**
- Compute `voice_a_end = plan.start_offset + subject_duration`.
- Compute `voice_b_end = plan.start_offset + delay_offset + subject_duration`.
- The later of the two is `stretto_end = max(voice_a_end, voice_b_end)`.
- If `stretto_end < plan.start_offset + plan.phrase_duration`:
  tail bars remain. Build tail_plan, generate via Viterbi.

**Between voice A's end and voice B's end (gap zone):**
- Voice A's subject has finished, voice B's is still going.
- Voice A needs notes in this gap. Generate via Viterbi against voice B's
  subject notes in this region.
- This is a mini-tail for voice A only.

**Tag first notes:** `lyric="stretto"` on voice A's first note,
`lyric="stretto-2"` on voice B's first note.

**Assemble:** Concatenate held/rest + subject + gap fill + tail for each
voice in chronological order.

Add dispatch in `write_phrase`:
```python
if plan.imitation_role == "stretto":
    return _write_stretto_phrase(
        plan=plan,
        fugue=fugue,
        prior_upper=prior_upper,
        prior_lower=prior_lower,
    )
```

### Files to modify
- `builder/phrase_planner.py` — `_assign_imitation_roles` (~5 lines)
- `builder/phrase_writer.py` — new `_write_stretto_phrase` + dispatch

### No new files

## Constraints

- Do NOT modify `imitation.py` — use `subject_to_voice_notes` as-is.
- Do NOT modify subject/answer/episode paths.
- Do NOT place stretto outside the peroratio.
- The stretto delay must be positive and less than the subject duration.
- If the phrase's `bar_span` is too short to accommodate the stretto
  (delay + subject > phrase_duration), fall back to a normal subject
  entry and log a warning. Do not crash.
- Before proposing any new mechanism, grep for existing code first.

## Checkpoint (mandatory)

Run: `python -m scripts.run_pipeline invention default c_major -o output`

Bob:
1. In the peroratio: does the second voice enter before the first has
   finished the subject? Is there a clear overlap?
2. Does the stretto create a sense of climax — denser texture, higher
   intensity than the preceding sections? (Principle 1)
3. During the overlap: do the two subjects produce acceptable
   counterpoint, or are there harsh unresolved dissonances?
   (Principle 3)
4. Does the stretto resolve convincingly into the final cadence?
   (Principle 1: tension must release)
5. Compare the peroratio to the narratio: is the peroratio clearly more
   intense? (Principle 8: emphasis requires contrast)
6. What's still wrong?

Chaz:
For each of Bob's complaints, trace to a code location and propose a
minimal fix (wire before invent).

## Acceptance Criteria

- The peroratio's non-cadential phrase has `lyric="stretto"` and
  `lyric="stretto-2"` on the two entry points (CC-measurable proxy).
- The second entry begins exactly `STRETTO_DELAY_BARS` bars after the
  first (verify in .note file: offset difference matches).
- Both voices carry recognisable subject material during the overlap
  (inspect .note pitches against subject degrees).
- All 8 genres run without error.
- Bob hears the peroratio as the climactic section of the piece (the
  real test).
