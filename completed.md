# Completed

## Phase I4e+I7: Re-enable CS in answer phrase + episode assignment (2026-02-10)

### Changes
- `builder/imitation.py`: Added `countersubject_to_voice_notes()` — places CS in
  any voice/key/range following `subject_to_voice_notes` pattern. Computes
  tonic_midi from target_key, gets MIDI via countersubject_midi, octave-shifts.
- `builder/phrase_writer.py`: `_write_answer_phrase` lead_voice==0 branch now
  places CS in soprano via `countersubject_to_voice_notes` at tonic key (not
  dominant). Handles tail generation if CS < phrase duration. First CS note
  labelled lyric="cs".
- `builder/phrase_planner.py`: `_assign_imitation_roles` gates answer assignment
  with `sec_idx == 0`. Only the exordium gets both subject + answer. Later
  sections get one subject entry; remaining non-cadential phrases are episodes
  (imitation_role=None), falling through to normal galant pipeline.

### Verification
- C major invention: CS in exordium answer phrase (8 notes, matching subject
  rhythm). All strong-beat intervals consonant (M6/m6). Episodes in narratio.
- A minor invention: No answer phrase (exordium has 1 non-cadential phrase).
  Episodes present in later sections.
- Minuet: 0 faults, unchanged.

### Open Issues
- A minor exordium too short for answer+CS (schema chain issue, not builder)
- Cross-relation risk persists (soprano unaware of chromatic bass alterations)

## Phase I4d: Invertible countersubject — dual validation (2026-02-10)

### Changes
- `motifs/countersubject_generator.py`: Added `answer_degrees` parameter to
  `generate_countersubject()`. When provided, creates parallel CP-SAT variables
  for CS-vs-answer intervals (answer_imod7), adds hard consonance constraints
  on strong beats ({0, 2, 5}) and weak beats ({0, 1, 2, 4, 5, 6}), and adds
  soft penalty terms mirroring the subject penalties. Existing behaviour
  unchanged when answer_degrees is None.
- `motifs/subject_generator.py`: `generate_fugue_triple()` now passes
  `answer_degrees=answer.scale_indices` to `generate_countersubject()`.
- `motifs/countersubject_generator.py` `__main__`: Updated test to generate
  answers and pass answer_degrees for dual validation.

### Verification
- __main__ test: 5/5 subjects with dual validation (unchanged from subject-only).
- Invention C major pipeline: 0 faults, completed.
- Invention A minor pipeline: completed.
- Minuet C major: completed, no regression.

### Notes
- Pipeline used cached .fugue files; CS not yet wired into output. This phase
  adds the solver constraint. Wiring CS into the pipeline is a future phase.
- Solver found OPTIMAL for all 5 test seeds within timeout.

## Phase I5c+I6: Verify tail fix and audit episodes (2026-02-10)

### Audit (no code changes)
- Regenerated C major and A minor inventions (seed 42) + minuet regression check.
- C major: 0 faults, 70 soprano + 64 bass notes.
- A minor: 1 fault (cross-relation bar 5.1: F4 vs F#3), 70 soprano + 64 bass notes.
- Minuet: 0 faults. No regression.

### Findings
1. **Tail bar repeated pitch persists:** do_re_mi bar 3 and romanesca bar 16
   both show 3x repeated pitch in both keys. Root cause: soprano_writer
   end-of-phrase filling when one structural degree exists with no next target.
   The make_tail_plan I5c injection codepath is NOT triggered (tails have
   degrees in range). Issue is in soprano_writer, not make_tail_plan.
2. **Zero episode phrases:** _assign_imitation_roles assigns subject/answer to
   ALL non-cadential phrases with lead_voice. No free counterpoint between
   entries. Invention is wall-to-wall thematic statements + cadences.
3. **Cross-relation (A minor):** Pre-existing. Soprano unaware of answer bass.

### Open Issues
- Soprano writer end-of-phrase repeated pitch (bars 3, 16)
- Need episode phrases for invention genre
- Soprano-bass awareness for cross-relation avoidance

## Phase I5b: Subject tail generation (2026-02-10)

### Changes
- `builder/phrase_types.py`: Added `make_tail_plan()` -- builds a PhrasePlan for
  bars after a subject entry. Filters degrees/positions to tail range, remaps bars.
- `builder/phrase_writer.py`: Replaced `_extend_to_fill` with tail generation.
  Subject/answer phrases now generate schema-based continuation after the subject
  ends, instead of holding the last note. Added `_pad_to_offset` for subject-to-tail
  boundary alignment.
- Both `_write_subject_phrase` and `_write_answer_phrase` handle all cases:
  soprano-leads, bass-leads, monophonic opening, with and without tails.

### Verification
- C major invention: 0 faults, 2 of 4 entries have tails, no held notes > 1 bar.
- A minor invention: 0 faults, 2 of 4 entries have tails, no held notes > 1 bar.
- Minuet: 0 faults, unchanged.

### Known Limitations
- Tail bars with no schema degrees produce static pitch (soprano writer fallback).
- Soprano unaware of pre-composed bass (pre-existing).

## Phase I5: Voice swap + key transposition across sections (2026-02-10)

### Changes
- `builder/phrase_planner.py`: `_assign_imitation_roles` now assigns
  subject/answer roles in ALL sections, not just exordium.
- `builder/imitation.py`: Added `subject_to_voice_notes()` — transposes
  subject to any key/voice/range via tonic_midi computation + octave shift.
- `builder/phrase_writer.py`: Rewrote `_write_subject_phrase` and
  `_write_answer_phrase` to dispatch on `lead_voice`. lead_voice=0:
  soprano leads; lead_voice=1: bass leads. Non-leading voice generates.

### Verification
- C major: 5 subject entries across 4 sections, 3 keys (C, G, F). 1 fault.
- A minor: 4 entries across 4 sections. 1 fault.
- Minuet: 0 faults, unchanged.

### Open
- Extended last note when subject < phrase duration (4+ bars held).
- Soprano unaware of pre-composed bass (occasional parallel octaves).
- A minor exordium has no answer (only 1 non-cadential phrase).

## Phase I4c: Fix tracks, restrict scope, drop pre-composed CS (2026-02-10)

### Changes
- `builder/imitation.py`: Removed `voice` parameter, use TRACK_SOPRANO/
  TRACK_BASS constants directly.
- `builder/phrase_planner.py`: `_assign_imitation_roles` restricted to
  first section (exordium) only.
- `builder/phrase_writer.py`: `_write_answer_phrase` generates soprano via
  `generate_soprano_phrase` instead of pre-composed CS.

### Verification
- Two tracks only (0 and 3). Subject stated once (exordium).
- Answer in bass with generated soprano above.
- Later sections use normal schema generation. Non-invention unchanged.

### Open
- Bass held long in answer phrase (answer < phrase length).
- Soprano writer unaware of fixed bass notes.

## Phase I4b: Answer entry + countersubject dispatch (2026-02-10)

### Changes
- `builder/imitation.py`: Added `answer_to_notes()` (octave-shift into
  bass range), `countersubject_to_notes()`.
- `builder/phrase_writer.py`: Dispatch on `imitation_role`. Extracted
  `_write_subject_phrase()`, added `_write_answer_phrase()`, shared
  `_extend_to_fill()`.

### Bugs found (fixed in I4c)
1. voice=1 in answer notes → 3 staves in MIDI.
2. imitation_role assigned to all sections → subject repeated 4 times.
3. Pre-composed CS dissonant against answer (CP-SAT validated against
   subject, not answer — intervals change when only one voice transposes).

## Phase I4a: Add imitation_role to PhrasePlan (2026-02-10)

### Changes
- `builder/phrase_types.py`: Added `imitation_role: str | None = None`.
- `builder/phrase_planner.py`: Added `_assign_imitation_roles()` — first
  non-cadential plan per section → "subject", second → "answer".

### Verification
- Correct roles per section. Cadential phrases None. Non-invention None.
- Zero audible change.

## Phase I3b: Subject-to-Notes + monophonic opening (2026-02-10)

### Changes
- New `builder/imitation.py`: `subject_to_notes()`, `subject_bar_count()`.
- `builder/phrase_writer.py`: Dispatch branch for monophonic subject entry
  (lead_voice set, fugue available, first phrase). Subject as soprano,
  empty bass. Last note extended to fill phrase.

### Verification
- Invention opens with subject (rhythmically varied, not schema figuration).
- Bass silent during subject. Minuet unchanged.
- Known limitation: last subject note held to fill phrase.

## Phase I3a: Thread fugue parameter to phrase writer (2026-02-10)

### Changes
- `planner/planner.py`: Pass `fugue` into `compose_phrases()`.
- `builder/compose.py`: Accept and forward `fugue` parameter.
- `builder/phrase_writer.py`: Accept `fugue` parameter (unused in logic).

### Verification
- Zero audible change. Pure plumbing.

## Phase I2: Wire lead_voice through PhrasePlan (2026-02-10)

### Changes
- `builder/phrase_types.py`: Added `lead_voice: int | None = None`.
- `builder/phrase_planner.py`: Added `_get_section_lead_voice()` helper,
  wired into `_build_single_plan()`.

### Verification
- Invention: lead_voice 0 or 1 per section. Minuet: all None.
- Zero audible change.

## Phase I1: Generate and cache FugueTriple (2026-02-10)

### Changes
- `motifs/fugue_loader.py`: Extracted `_parse_fugue_data(data)` helper.
  Added `load_fugue_path(path)` for loading from arbitrary paths.
- `planner/planner.py`: Added `_parse_key_string(key)` → (mode, tonic_midi).
  Modified `generate_to_files()` to generate or load cached .fugue for
  invention genre.

### Verification
- .fugue created on first run, reused on second, regenerated if deleted.
- Non-invention genres unaffected. Zero audible change.
