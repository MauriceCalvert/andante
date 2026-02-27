# Result: SUB-1 — Fix tonal answer generation

## Code Changes

### 1. `motifs/answer_generator.py`
- Swapped constants: `TONIC_TRANSPOSITION = 4` (was 3), `DOMINANT_TRANSPOSITION = 3` (was 4)
- Updated module docstring to match: tonic region +5th (+4 degrees), dominant region +4th (+3 degrees)

### 2. `motifs/subject_loader.py`
- `answer_midi()`: removed `+7` from tonic_midi — degrees already encode the tonal transposition, render at tonic not dominant
- Updated docstring accordingly

### 3. `builder/thematic_renderer.py`
- Line 66: comment updated from "internally transposes to dominant (+7)" to "renders at tonic -- degrees already encode tonal transposition"

### 4. `scripts/generate_subjects.py`
- Added `patch_library_answers()` function and `--patch-answers` CLI flag
- Loads each library .subject, rebuilds answer via `generate_answer()`, overwrites answer degrees and mutation_points

### 5. Regenerated .subject files
- Deleted and regenerated `motifs/output/*.subject` (10 files, `--batch 10`)
- Patched all 6 library .subject files with corrected answer degrees

## Verification

Subject04 (C major, tonic_midi=72):
```
Subject degrees: (4, 3, 2, 1, 2, 4, 3, 0, -2, 0)
Answer degrees:  (7, 7, 6, 5, 6, 7, 7, 4,  1, 4)

Tonic-region notes (degrees 0,1,2,3):    interval = 7 semitones (P5)
Dominant-region notes (degrees 4,5,6):   interval = 5 semitones (P4)
```

Classic tonal answer: subject 5->4 (G->F) answered as 1->1 (C->C, P4), subject 4->3 (F->E) answered as 1->7 (C->B, P5). The mutation point shrinks the 5th to a 4th at the dominant/tonic boundary.

## Bob's Assessment

### Pass 1: What do I hear?

The subject enters alone in bar 1 — a zigzag figure starting on the dominant, descending four steps then rebounding. Recognisable, purposeful opening.

The answer enters in bar 2 in the bass. It begins on the tonic (C), mirrors the subject's shape but with a subtle narrowing at the first note — the opening fifth G-F becomes a unison C-C before the stepwise descent resumes. This is the tonal mutation at work and it sounds right: the answer belongs to the same family as the subject but with the expected harmonic adjustment at the 5-1 boundary.

The countersubject enters simultaneously with the answer, weaving eighth-note running motion against the subject's sixteenths. Two distinct voices, two distinct rhythmic characters. The texture opens up properly at the second entry.

Third entry (bar 4, A minor) brings the subject to the soprano in the relative minor — the colour shift is audible. The bass takes a countersubject variant. The piece is building momentum through key contrast.

Episodes (bars 6-8, 13-14, 17-19, 24-25, 28-30) use sequential descending fragments derived from the subject head. They provide breathing room between entries but share a similar descending-sequence character throughout — not much variety in episode texture.

Strettos (bars 10-12, 21-23, 32-37) are tight. The overlapping entries create genuine intensity. However, bars 32-34 and 35-37 appear to be identical strettos — the same notes repeated verbatim. That repetition flattens the build toward the final cadence rather than intensifying it.

The pedal point (bars 38-39) over dominant G has rapid sixteenth-note figuration above — a proper pre-cadential toccata effect. The final cadence (bars 40-42) lands on C with parallel-rhythm whole- and half-notes, descending stepwise in both voices. The lockstep motion in the cadence (6 simultaneous attacks) sounds blocky rather than contrapuntal.

Key journey: C major -> A minor -> F major -> G major -> D minor -> E minor -> C major. Wide and purposeful, touching all the near-related keys.

### Pass 2: Why does it sound that way?

The tonal answer mutation is textbook: dominant-region degree 5 (G) answered by tonic degree 1 (C), up a P4 (5 semitones). Tonic-region degrees answered up a P5 (7 semitones). The mutation point at degree 4/3 produces the characteristic C-C unison that signals the key change from I to V.

The identical strettos in bars 32-37 are a structural repetition, not a musical intensification. Bach would vary the second stretto — invertible counterpoint, different voice assignment, tighter delay, augmentation.

Faults noted: 3 ugly leaps (including a tritone at 15.1 and a minor 9th at 32.1), cross-relations at bars 13-14, unprepared dissonances at bars 22.1/33.1/36.1, direct octaves/fifths at several points, and the parallel rhythm in the final cadence.

## Chaz's Diagnosis

Bob says: "The answer enters in bar 2... begins on the tonic (C), mirrors the subject's shape but with a subtle narrowing at the first note."
Cause: `answer_generator.py:TONIC_TRANSPOSITION=4, DOMINANT_TRANSPOSITION=3` now correctly map dominant-region notes up a P4 and tonic-region notes up a P5. `subject_loader.py:answer_midi()` renders at tonic (not tonic+7), eliminating the double-transposition. The answer degrees `(7,7,6,5,6,7,7,4,1,4)` are correct.
Location: `motifs/answer_generator.py:24-25`, `motifs/subject_loader.py:97-104`
Fix: Applied — this was the SUB-1 task.

Bob says: "Bars 32-34 and 35-37 appear to be identical strettos."
Cause: `planner/imitative/entry_layout.py` emits two consecutive stretto phrases in the peroratio with identical parameters (same key, same delay). Known limitation logged under EPI-1.
Location: `planner/imitative/entry_layout.py`
Fix: Future — stretto variety in peroratio (roadmap item).

Bob says: "The lockstep motion in the cadence sounds blocky."
Cause: `builder/cadence_writer.py` cadenza_grande template uses parallel whole-note/half-note motion. 6 consecutive simultaneous attacks triggers `parallel_rhythm` fault.
Location: `builder/cadence_writer.py`
Fix: Future — cadence template refinement.

Bob says: "Episode texture shares a similar descending-sequence character throughout."
Cause: All episodes draw from the same FragenProvider cell catalogue (subject head/tail fragments). Known limitation — EPI-2c addresses position-aware selection.
Location: `motifs/fragen.py`
Fix: Roadmap EPI-2c.

## Summary

SUB-1 complete. The tonal answer is now musically correct — tonic-region notes up a P5, dominant-region notes up a P4, rendering at tonic with no double transposition. All .subject files regenerated. Pipeline runs clean. 16 faults remain (all pre-existing, none introduced by this change).

Please listen to the MIDI and let me know what you hear.
