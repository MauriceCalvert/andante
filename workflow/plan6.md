# Plan 6 — Motivic Return

## Problem

Currently every phrase generates its figuration independently via the
diminution table. The result is varied but amnesiac — no melodic idea
from the opening reappears later. The piece sounds like a sequence of
competent but unrelated phrases.

In real baroque music, motivic return is how the listener knows they
are hearing a single piece rather than a medley. The opening gesture
recurs — sometimes literally, sometimes varied, sometimes in the other
voice — and this recurrence is what gives the piece coherence. A binary
dance repeats its opening idea at the start of the B section (often in
the dominant). An invention states its subject and then works it
throughout.

## Musical Goal

- The opening soprano figure (the first figuration applied in the
  first phrase) should recur at least once later in the piece.
- The recurrence should be recognisable but not necessarily literal:
  same contour and rhythm, possibly transposed to the local key.
- Recurrence should happen at structurally significant points: start
  of the B section, return to the home key, final phrase.
- The bass is not expected to carry motivic material at this stage
  (it may in inventions later, but not in dances).

## Prerequisite

This plan depends on the figuration system producing named,
retrievable figures. Currently `figurate_soprano_span` returns a
figure name alongside the notes. Plan 6 requires that a figure can
be *requested* by name for a given span, not only randomly selected.

## Phases

### Phase 6.1 — Capture the opening motif

**What to do:** After the first non-cadential phrase is composed,
extract the "head motif": the interval sequence and rhythm of the
soprano's first figuration span (from the first structural tone to
the second). Store this as a lightweight descriptor:
- Interval sequence (signed semitone deltas between consecutive
  notes).
- Duration sequence.
- The figure name that produced it.

This is a read-only extraction — no change to how the first phrase
is composed. Store the descriptor on the `Composition` or pass it
through `compose_phrases` so later phrases can access it.

**Scope:** `builder/compose.py` — extract after the first phrase
result. Define a small frozen dataclass for the motif descriptor.

**Acceptance:** The head motif descriptor is correctly extracted for
minuet and gavotte test cases. Print it to trace output for
verification.

### Phase 6.2 — Motif recall in figuration selection

**What to do:** In the figuration selection system, add a mechanism
to request a specific figure by name. When the phrase plan indicates
"recall opening motif," the soprano figuration for the first span of
that phrase should use the same figure name as the head motif, rather
than selecting from the diminution table freely.

This requires:
1. A flag on `PhrasePlan` or a parameter to the figuration call
   indicating "use this figure name for the first span."
2. The figuration selector honouring that request: look up the named
   figure, transpose its interval pattern to the current key and
   starting pitch, and realise it.

**Scope:** `builder/figuration/selection.py` (add recall path),
`builder/soprano_writer.py` (pass the recall flag),
`builder/compose.py` (decide which phrases get the recall flag).

**Acceptance:** When recall is requested, the soprano's first
figuration span uses the same contour and rhythm as the opening.
The pitches are transposed to the local key. The result is
recognisable as the opening gesture.

### Phase 6.3 — Placement policy

**What to do:** Define where motivic recall occurs. For binary
dances, the policy is:
- First phrase of section B: recall the opening motif (transposed
  to the local key, which is typically the dominant).
- Final phrase before the last cadence: recall the opening motif
  in the home key.

This is a planning-level decision. The schematic or phrase-planning
layer should mark these phrases with a recall flag based on the
section structure in the genre config.

**Scope:** `builder/phrase_planner.py` or `planner/schematic.py`
— add recall marking based on section boundaries.
`builder/compose.py` — thread the recall flag to the figuration
system.

**Acceptance:** In a binary gavotte or minuet, the opening soprano
gesture is audibly recognisable at the start of the B section and
near the final cadence.

## Validation Scope

All phases validated against gavotte and minuet only. Additional genres
are not tested until Plan 7.

## Out of Scope

- Bass motivic work (inventions, fugal entries). Parked for later.
- Motivic development (augmentation, diminution, inversion of the
  motif). This plan covers literal and transposed recall only.
- Imitative entries (one voice echoing the other's motif). This
  requires the imitative voice role, which is defined but not yet
  wired.
- Motif variation across the A section (e.g. using the motif at
  different pitch levels within the same section). The opening
  section generates freely; recall is for structural return points.
