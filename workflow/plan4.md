# Plan 4 — Rhythm Repair

## Problem

Walking bass currently inherits rhythm cells from the generic cell
selection system. A walking bass should move in even note values —
quarter notes in 4/4, quarter notes in 3/4 — because that is what
"walking" means. The rhythm cell mechanism was designed for patterned
and pillar textures; applying it to walking bass gives it rhythmic
variety it should not have.

Separately, patterned and pillar bass textures select rhythm cells
without knowing what the soprano's rhythm is doing. Two voices
moving in lockstep eighth notes sound like a keyboard exercise, not
counterpoint. The cell selection system already has `soprano_onsets`
awareness (see `select_cell`), but it is unclear whether all callers
pass it.

## Musical Goal

- Walking bass: even, steady pulse. The ear hears a reliable
  harmonic rhythm underneath the soprano's figuration. No dotted
  rhythms, no rests, no syncopation in the walking voice.
- Patterned bass: rhythmic independence from the soprano. When the
  soprano moves in quavers, the bass should prefer crotchets or
  dotted patterns, and vice versa. Rhythmic complementarity, not
  rhythmic unison.
- The result should sound like two musicians playing together, each
  with their own rhythmic life, not one instrument doubled.

## Phases

### Phase 4.1 — Walking bass: even note values

**What to fix:** The walking bass generator should not call
`select_cell` at all. Its rhythm is definitional: every note is the
same duration, equal to the beat unit (quarter note for 3/4 and 4/4).
If the walking bass currently uses cell-derived rhythms, replace that
mechanism with a fixed duration per note equal to `beat_unit`.

**Scope:** `builder/bass_writer.py`, specifically the walking-bass
texture function. Verify that the walking bass path does not route
through `select_cell`. If it does, remove that dependency. If it
already uses even values, this phase is a no-op — verify and document.

**Acceptance:** Every note in a walking bass phrase has identical
duration. No dotted values, no sub-beat values, no rests.

### Phase 4.2 — Patterned bass: soprano-aware cell selection

**What to fix:** Verify that all callers of `select_cell` for
patterned bass pass `soprano_onsets` so the onset-independence
ranking in `select_cell` is active. If callers omit it, wire it.

**Scope:** Trace every call site of `select_cell` in the bass
generation path. For each, confirm `soprano_onsets` is passed.
Where it is not, compute soprano onsets per bar from the soprano
notes already available in the bass generator and pass them.

**Acceptance:** For any bar where both soprano and bass use rhythm
cells, the bass cell is chosen to minimise onset overlap with the
soprano (excluding downbeats). The `parallel_rhythm` fault count
should not increase.

### Phase 4.3 — Pillar bass: rhythm matches texture intent

**What to fix:** Pillar bass should sound grounded — long values on
strong beats, occasional shorter values to approach the next
structural tone. Currently pillar bass may select flowing or
energetic cells that contradict the sustained character. Pillar
should prefer `cadential` or `plain` character cells and avoid
`energetic` or `flowing`.

**Scope:** The pillar-bass texture function in `builder/bass_writer.py`.
Ensure `prefer_character` is set to `"cadential"` or `"plain"` and
that `"energetic"` cells are never selected for pillar texture.

**Acceptance:** No pillar-texture bar uses an energetic or flowing
rhythm cell. Pillar bars sound sustained and stable beneath the
soprano.

## Validation Scope

All phases validated against gavotte and minuet only. Additional genres
are not tested until Plan 7.

## Out of Scope

- Soprano rhythm (already handled by figuration system).
- Cadence rhythm (handled by cadence_writer templates).
- Genre-specific bass rhythm characters beyond the three textures
  above (future: sarabande beat-2 weight, gigue leaping patterns).
- Rest insertion (baroque bass lines do not rest mid-phrase).
