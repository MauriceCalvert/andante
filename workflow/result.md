# Result: Phase I4e+I7 — Re-enable CS in answer phrase + episode assignment

## Status: COMPLETE

## Changes

| File | Change |
|------|--------|
| `builder/imitation.py` | Added `countersubject_to_voice_notes()` — places CS in any voice/key/range, following `subject_to_voice_notes` pattern |
| `builder/phrase_writer.py` | `_write_answer_phrase` lead_voice==0 branch: soprano now gets CS via `countersubject_to_voice_notes` at tonic key, with tail generation if CS < phrase. Import added. |
| `builder/phrase_planner.py` | `_assign_imitation_roles`: answer assignment gated by `sec_idx == 0`. Only exordium gets subject+answer; later sections get one subject, rest are episodes. |

## Verification

| Test | Result |
|------|--------|
| Invention C major | 0 faults, CS in exordium answer phrase (8 notes, matching subject rhythm) |
| Invention A minor | Completed, no answer phrase (exordium has only 1 non-cadential phrase) |
| Minuet C major | Completed, no regression |

## Phase 1: Bob

### Invention C major
The exordium has a proper two-voice entry: solo subject in soprano (bars 1-2), then bass enters with the theme at bar 4 while the soprano continues with a complementary line (the countersubject). Strong beats between the two voices are all imperfect consonances — sixths throughout. The CS has the same rhythm as the subject but a distinct melodic contour.

Later sections breathe: narratio states the subject once in the bass (bars 8-9), then bars 10-12 are free sequential counterpoint. Confirmatio has one soprano subject entry (bars 13-14) followed by freer material with running eighths in the bass. Peroratio states the subject in the bass (bars 20-21) then resolves to the PAC.

The piece alternates between thematic identity and episodic development. It's an invention, not a subject catalogue.

### Invention A minor
The exordium is truncated — solo subject then immediate half cadence. No second-voice entry, no CS. The rest of the piece breathes correctly: one subject per section with episodes between.

### Minuet C major
Unchanged. Standard galant dance, no imitation paths exercised.

## Phase 2: Chaz

```
Bob says: "soprano continues with a complementary line (the countersubject)"
Cause:    _write_answer_phrase lead_voice==0 branch now calls
          countersubject_to_voice_notes with target_key=plan.local_key,
          target_track=TRACK_SOPRANO, target_range=plan.upper_range.
          First note labelled lyric="cs".
Location: builder/phrase_writer.py:_write_answer_phrase, lead_voice==0 branch
Fix:      None needed. Working as designed.

Bob says: "strong beats are all imperfect consonances — sixths throughout"
Cause:    CS was dual-validated by CP-SAT (Phase I4d) against both subject
          and answer. Interval mod 7 constrained to {0, 2, 5} on strong beats.
          countersubject_to_voice_notes preserves these intervals via degree-
          based MIDI conversion and octave shifting.
Location: motifs/countersubject_generator.py (constraints), builder/imitation.py:countersubject_to_voice_notes
Fix:      None needed.

Bob says: "bars 10-12 are free sequential counterpoint"
Cause:    _assign_imitation_roles now gates answer assignment with sec_idx==0.
          Narratio phrase 3 gets imitation_role=None, falls through to normal
          galant pipeline in write_phrase.
Location: builder/phrase_planner.py:_assign_imitation_roles
Fix:      None needed.

Bob says: "exordium is truncated [A minor] — no second-voice entry"
Cause:    A minor schema chain has only 2 exordium phrases: 1 non-cadential
          (subject) + 1 cadential (HC). _assign_imitation_roles only assigns
          answer to non-cadential phrases, so no answer slot exists.
Location: Schema chain construction (planner), not builder code.
Fix:      Not a code bug. Would require longer exordium in schema selection.
```

## Acceptance Criteria

- [x] **CS playback**: C major answer phrase has CS in soprano (8 notes, lyric="cs" on first). A minor: no answer phrase (known limitation).
- [x] **Consonance**: All strong-beat intervals M6 or m6. Verified numerically.
- [x] **Episodes exist**: C major phrase 3 (narratio [F]), A minor phrase 3 (narratio [E]) have imitation_role=None.
- [x] **Subject entries reduced**: C major 5 thematic (was 6 non-cadential). A minor 4 (was 6).
- [x] **Regression**: Minuet 0 faults, unchanged.
