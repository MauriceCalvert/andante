# Plan 5 — Phrase Boundary Register Smoothing

## Problem

Each phrase is composed independently, constrained only by the exit
pitch of the previous phrase. This means phrase boundaries can produce
audible seams: a soprano ending high in one phrase and starting low in
the next, or a bass leaping an octave between the last note of one
schema and the first of the next. The listener hears a "gear change"
at every phrase join.

In real baroque music, a competent player makes phrase transitions
inaudible. The end of one phrase sets up the beginning of the next —
registrally, directionally, and harmonically. The join should sound
like a breath, not a splice.

## Musical Goal

- Phrase boundaries should not produce register jumps larger than a
  fifth in either voice, unless the genre or section change demands
  a deliberate registral shift.
- The directional momentum at the end of a phrase should be
  compatible with the start of the next: if the soprano descends
  to a cadence, the next phrase's opening should not require an
  immediate large upward leap.
- Both voices should be smoothed, not just one. A smooth soprano
  over a lurching bass still sounds broken.

## Phases

### Phase 5.1 — Audit current phrase-boundary intervals

**What to do:** For each test genre (minuet, gavotte), run the
pipeline and measure the interval between the last note of each
phrase and the first note of the next, in both voices. Report:
- How many boundaries exceed a fifth (7 semitones).
- How many exceed an octave.
- The average boundary interval per voice.
- Any cases where both voices leap simultaneously at the same
  boundary (worst case — the texture rips apart).

This is analysis only, no code change. The numbers determine
whether Phase 5.2 is needed and how aggressive it must be.

**Acceptance:** A table of boundary intervals for each voice and
each phrase join, with the above statistics.

### Phase 5.2 — Entry-pitch constraint for phrase planning

**What to fix:** The phrase planning stage (metric layer pitch
assignment in `planner/metric/pitch.py`) assigns anchor pitches
to each schema's degrees. Currently the first degree of each
schema is placed near the voice's median, without regard for where
the previous phrase ended.

Add a constraint: when assigning the first anchor pitch of a
non-opening phrase, prefer the octave placement that minimises
the interval from the previous phrase's last anchor pitch, subject
to range constraints. This is not post-hoc pitch shifting (X001) —
it is a planning-time preference in the pitch assignment algorithm.

**Scope:** `planner/metric/pitch.py`. The exit pitch of the
previous phrase's last anchor must be threaded into the pitch
assignment for the next phrase's first anchor.

**Acceptance:** Boundary intervals exceeding a fifth drop by at
least 50% compared to the Phase 5.1 audit. No new range
violations or voice-crossing introduced.

### Phase 5.3 — Directional continuity at boundaries

**What to fix:** Even with register proximity, a phrase ending in
a descending line followed by a phrase starting with a large
ascending leap sounds awkward. Add a soft preference: when the
exit direction of the previous phrase is descending, prefer an
entry pitch at or below the exit pitch (and vice versa). This is
a tie-breaker when two octave placements are equally close to the
exit pitch.

**Scope:** Same as 5.2 — `planner/metric/pitch.py`. This refines
the octave selection heuristic, not the note generation.

**Acceptance:** Listening test. Phrase boundaries should sound
like breaths, not splices. No new faults.

## Validation Scope

All phases validated against gavotte and minuet only. Additional genres
are not tested until Plan 7.

## Out of Scope

- Harmonic continuity at phrase boundaries (the key already threads
  through via tonal_plan).
- Overlapping phrases (one voice sustaining while the other starts
  the new phrase) — this is a performance/arrangement technique,
  not a compositional one at Andante's current level.
- Inner voice smoothing (no inner voices yet).
