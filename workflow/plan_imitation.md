# Plan: Invention Imitation

## The architectural gap

The invention genre currently runs the galant pipeline: schema degrees
→ soprano figuration → bass counterpoint. This produces competent
two-part counterpoint with no thematic identity. Both voices generate
independently from the tonal plan.

A real invention is subject-driven. One voice states a pre-composed
subject; the other enters with the answer (the subject transposed to
the dominant, with tonal mutations at the 1–5 boundary). While the
answer sounds, the first voice continues with a counter-subject. In
later sections, the roles swap. The subject is the identity of the
piece.

The `motifs/` package already has everything needed to produce the
thematic material:

| Generator | Output | Status |
|---|---|---|
| `subject_generator.py` | `GeneratedSubject` (degrees, durations, MIDI, bars) | Working |
| `answer_generator.py` | `GeneratedAnswer` (tonal transposition, mutation points) | Working |
| `countersubject_generator.py` | `GeneratedCountersubject` (CP-SAT optimised) | Working |
| `generate_fugue_triple()` | `FugueTriple` (all three coordinated) | Working |

None of this is wired into the builder pipeline. The builder has never
been asked to play pre-composed notes — it always generates from schema
degrees. That is the gap.

## What changes architecturally

**Galant flow** (minuet, gavotte, bourree — unchanged):
```
tonal_plan → schema_chain → phrase_plans → soprano_writer(degrees) → bass_writer(soprano)
```

**Invention flow** (new):
```
tonal_plan → schema_chain → phrase_plans
                               ↑
FugueTriple (subject, answer, countersubject)
                               ↓
phrase_writer dispatches: subject/answer/CS notes → free voice generates against them
```

The schema chain still exists for inventions — it provides key areas,
phrase boundaries, and cadence points. But for non-cadential phrases,
the actual notes come from the FugueTriple, not from soprano_writer
figuration.

## Data format bridge

Motifs generators produce:
- `scale_indices`: 0-based degree indices (int tuple)
- `durations`: float fractions of a whole note
- `midi_pitches`: absolute MIDI (int tuple)

Builder expects:
- `Note(offset=Fraction, pitch=int, duration=Fraction, voice=int)`

Conversion: place the subject/answer/CS at a specific offset, convert
float durations to Fraction, use midi_pitches. Straightforward, but
needs a dedicated function.

## Phased plan

### Phase I1: Generate and cache FugueTriple

**What changes**:
1. In `generate_to_files()`, when genre is invention and no fugue was
   passed in: check whether `{output_dir}/{name}.fugue` exists.
   - If it exists, load it via `load_fugue()` (path variant, not
     library lookup).
   - If it doesn't exist, call `generate_fugue_triple()` with mode,
     metre, tonic_midi derived from the key, affect, and seed. Save
     the result to `{output_dir}/{name}.fugue` via `write_fugue_file()`.
   - Either way, thread the resulting LoadedFugue into `generate()`.
2. `fugue_loader.load_fugue()` currently only loads from the library
   directory. Add a `load_fugue_path(path: Path)` function (or extend
   `load_fugue` to accept a Path) so it can load from any location.
3. The .fugue file sits alongside the .note and .midi output. To
   regenerate, the user deletes the .fugue and reruns. This makes
   testing deterministic: same .fugue → same subject material every
   run, even if the seed changes.
4. No change to phrase writing yet — this just makes the triple
   available and cached.

**Acceptance**: Pipeline runs for invention, prints subject info,
writes .fugue alongside .note/.midi. Second run reuses the .fugue.
Deleting .fugue causes regeneration. All existing genres unaffected.

---

### Phase I2: Wire lead_voice through PhrasePlan

**What changes**:
1. `PhrasePlan` gets `lead_voice: int | None` field (default None).
2. `phrase_planner._build_single_plan` reads `lead_voice` from the
   genre section config (same pattern as `accompany_texture`,
   `character`).
3. Invention sections already declare lead_voice (0 or 1). This
   makes it visible in PhrasePlans.

**Acceptance**: Invention PhrasePlans carry lead_voice values. No
audible change. Other genres get None.

---

### Phase I3: Subject-to-Notes conversion + monophonic opening

**Musical goal**: The invention opens with the subject stated alone
in one voice. The listener hears a recognisable theme, unaccompanied.

**What changes**:
1. New module `builder/imitation.py` with function:
   ```
   def subject_to_notes(
       subject: GeneratedSubject | GeneratedAnswer | GeneratedCountersubject,
       start_offset: Fraction,
       voice: int,
       transpose_semitones: int = 0,
   ) -> tuple[Note, ...]
   ```
   Converts motifs output to builder Notes. Float durations → Fraction.
   MIDI pitches + transpose. Offsets computed cumulatively from
   start_offset.

2. `phrase_writer.write_phrase`, when it receives a PhrasePlan with
   `lead_voice=0` and a FugueTriple, places the subject as the upper
   voice's notes instead of calling `generate_soprano_phrase`. The
   lower voice is silent (rests or no notes) for the subject's
   duration.

3. Subject duration may not fill the entire phrase. If subject.bars <
   plan.bar_span, the remaining bars in the lead voice revert to
   normal schema-degree generation. If subject.bars > plan.bar_span,
   that's a planning error (subject must fit within the first phrase).

**Known limitation**: Only handles lead_voice=0 (soprano leads) for
now. Bass-lead (lead_voice=1) in Phase I5.

**Acceptance**: Invention MIDI opens with a solo melody for the
duration of the subject. The melody has the subject's characteristic
leap-and-fill shape and rhythmic variety, not the even-note schema
figuration.

---

### Phase I4: Answer entry + countersubject

**Musical goal**: After the subject, the second voice enters with
the answer while the first voice continues with the counter-subject.
The listener hears the same theme in the bass, a fifth lower, while
the soprano continues with complementary material.

**What changes**:
1. In the second phrase (or after `delay_bars`), the following voice
   enters with the answer. `subject_to_notes` converts the
   GeneratedAnswer, transposed to the appropriate octave for the
   bass range.

2. Simultaneously, the lead voice plays the counter-subject (from
   the FugueTriple). The CS was generated to form invertible
   counterpoint with the subject, so it works naturally against the
   answer.

3. `phrase_writer` dispatches based on which phrase we're in:
   - Phrase 0 (exordium start, lead_voice=0): soprano = subject,
     bass = rest
   - Phrase 1 (exordium continued, lead_voice=0): soprano = CS,
     bass = answer
   - Later phrases in exordium: revert to normal schema generation

4. The answer's key is the dominant (from the schema chain's
   key_areas). The motifs answer_generator already handles tonal
   mutation. The MIDI pitches need to be placed in the bass range.

**Design decision — voice range placement**:
The FugueTriple generates all three parts at a fixed tonic_midi.
When placing the answer in the bass, we need to shift it into the
bass range. Options:
- (a) Octave transpose until it fits Range(low=36, high=62)
- (b) Regenerate with a different tonic_midi for the bass register

Option (a) is simpler and preserves the tonal mutation. Preferred.

**Acceptance**: The listener hears: solo subject → both voices enter
(answer in bass, counter-subject in soprano) → the two voices have
recognisably related material. The vertical intervals are consonant
on strong beats (guaranteed by the CP-SAT countersubject generator).

---

### Phase I5: Voice swap in later sections

**Musical goal**: In narratio (lead_voice=1), the bass states the
subject and soprano accompanies. In confirmatio (lead_voice=0),
soprano states it again. The subject passes between voices.

**What changes**:
1. When lead_voice=1, the roles reverse: bass carries the subject
   (transposed to the section's local key), soprano generates the
   counter-subject or free counterpoint above it.

2. This requires `phrase_writer` to handle the reversed generation
   order: bass notes given, soprano generated against them. The
   existing `generate_soprano_phrase` needs bass notes as context
   for counterpoint checking.

3. The subject is transposed to each section's local key (available
   from the schema chain's key_areas). The transposition is in
   semitones from the original tonic.

4. Subsequent entries may use just the subject (without formal
   answer/CS pairing). In development sections, the subject re-enters
   in new keys.

**This is the hardest phase** because it reverses the generation
order. Current flow: soprano first, bass against soprano. New flow
for bass-lead: bass first (pre-composed), soprano against bass.

**Approach**: Option (b) from the original plan — the existing
soprano_writer generates from schema degrees with figuration, but
needs to check against given bass notes. Thread the pre-composed
bass notes into soprano generation as "lower_context" for the
counterpoint checks that currently only run in bass_writer.

**Acceptance**: The subject is audible in different voices across
sections. When bass leads, soprano doesn't double it or clash with
it. The dialogue character — voices trading the subject — is the
genre's identity.

---

### Phase I6: Free episodes (continuation schemas)

**Musical goal**: Between subject entries, continuation schemas
(fonte, monte, prinner) provide harmonic progression. These
"episodes" revert to normal schema-based generation but should
eventually derive from subject fragments.

**What changes**:
1. Phrases with no subject/answer/CS assignment fall through to
   the normal galant pipeline (soprano_writer + bass_writer).
2. This is already the default — no code change needed for basic
   function. The schema chain handles it.

**Future refinement** (not this plan): Episodes should use motivic
fragments from the subject. The existing HeadMotif recall mechanism
could be extended for this. But generic schema-based episodes are
acceptable as a first pass.

**Acceptance**: Episodes sound like competent counterpoint (they
already do). Subject entries sound thematically unified. The
alternation between subject entries and free episodes creates the
sectional character of an invention.

---

## Phase ordering and dependencies

```
I1 (generate FugueTriple) → I2 (wire lead_voice) → I3 (subject as notes)
                                                          ↓
                                                    I4 (answer + CS entry)
                                                          ↓
                                                    I5 (voice swap / bass-lead)
                                                          ↓
                                                    I6 (episodes — minimal change)
```

I1–I2 are plumbing with no audible change. I3 is where the subject
becomes audible. I4 is where imitation appears. I5 completes the
dialogue. I6 is mainly verification that episodes still work.

## Subject–schema alignment

A key design question: how does the subject's duration relate to the
phrase plan's bar_span?

The subject generator produces subjects of 1–4 bars. The schema chain
allocates bar_span per schema. These must align. Options:

- (a) **Subject fits within first schema's bar_span**. If the first
  schema (do_re_mi) gets 4 bars and the subject is 2 bars, the
  subject occupies bars 1–2 and bars 3–4 revert to normal generation.
- (b) **Schema bar_span adapts to subject**. The metric layer adjusts
  the first schema's bar allocation to match the subject's length.
- (c) **Subject replaces the first N bars regardless of schema
  boundaries**. The subject may span multiple schemas.

Option (a) is safest: the subject fits within a single phrase and the
schema chain is untouched. The subject generator can be constrained to
match the first schema's bar_span (it already accepts `target_bars`).

If mismatch is unavoidable, option (b) is next — the metric layer
already distributes bars across schemas and can be told "first schema
gets N bars."

## Assignment table

For the exordium (lead_voice=0):

| Phrase | Schema | Upper voice | Lower voice |
|--------|--------|-------------|-------------|
| 0 | do_re_mi | Subject | Rest (monophonic) |
| 1 | prinner | Counter-subject | Answer |

For narratio (lead_voice=1):

| Phrase | Schema | Upper voice | Lower voice |
|--------|--------|-------------|-------------|
| 2 | fonte | Free (schema-based) | Subject (in new key) |
| 3 | monte | Free (schema-based) | Free (schema-based) |

For confirmatio (lead_voice=0):

| Phrase | Schema | Upper voice | Lower voice |
|--------|--------|-------------|-------------|
| 4 | romanesca | Subject (in home key) | Counter-subject |
| 5 | fenaroli | Free (schema-based) | Free (schema-based) |

For peroratio (lead_voice=1):

| Phrase | Schema | Upper voice | Lower voice |
|--------|--------|-------------|-------------|
| 6 | passo_indietro | Free (schema-based) | Subject fragment? |
| 7 | cadenza_composta | Cadence template | Cadence template |

## What this plan does NOT address

- **Subject development** (inversion, augmentation, stretto,
  diminution). These transform the subject shape. Future plan.
- **Episode derivation from subject fragments**. Episodes use generic
  schema-based generation. Future refinement.
- **Inner voices**. Inventions are two-voice. No change needed.
- **Subject as input** (user-supplied or loaded from .fugue file).
  This plan generates subjects internally. Loading from file is a
  minor extension.
- **Countersubject in later entries**. Phase I5 uses free counterpoint
  for the non-subject voice in later sections. Using the CS everywhere
  the subject appears is a refinement.

## Risk assessment

| Risk | Mitigation |
|---|---|
| Subject duration doesn't match schema bar_span | Constrain subject generator's target_bars; or adapt metric layer |
| FugueTriple generation slow (CP-SAT) | countersubject_generator has 5s timeout; typically < 1s |
| Answer out of bass range after transposition | Octave-shift into range; assert range bounds |
| Bass-lead soprano generation (I5) breaks counterpoint | Thread bass notes as context; reuse existing counterpoint checks |
| Float↔Fraction conversion loses precision | Subject durations are simple fractions (1/4, 1/8 etc.); Fraction(float).limit_denominator(64) safe |
| Other genres affected | All branching gated on `lead_voice is not None` and/or genre name. Non-invention genres untouched. |
| Subject sounds mechanical vs figurated soprano | Subject generator already uses head+tail with leap/fill and rhythmic variety. Quality comparable to figuration. |
