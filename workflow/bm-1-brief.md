# BM-1 — Harmonic grid data module

Read these files first:
- `docs/baroque_melody.md` (the full spec — sections 1, 2, 4)
- `motifs/subject_gen/rhythm_cells.py` (Cell dataclass, cell names)
- `motifs/subject_gen/constants.py` (DURATION_TICKS, ranges)
- `shared/constants.py` (MAJOR_SCALE, NATURAL_MINOR_SCALE)

## Goal

Create `motifs/subject_gen/harmonic_grid.py` — a pure data + lookup
module providing everything the melody generator (BM-2) will need to
place chord tones and validate harmonic context.  No generation logic.
No dependencies on the existing pitch pipeline.

## What to create

### File: `motifs/subject_gen/harmonic_grid.py`

**1. Stock progressions (§1.2–1.4 of baroque_melody.md)**

Store as a dict keyed by `(level, pattern_id)` where level is
`"fast"`, `"medium"`, or `"slow"`, and pattern_id is `"A"`, `"B"`, etc.
Each value is a tuple of Roman numeral strings: `"I"`, `"V"`, `"IV"`,
`"ii"`, `"i"`, `"iv"`, `"iio"`.

Provide a lookup: `get_progressions(level: str) -> tuple[tuple[str, ...], ...]`
returning all patterns for that level.

**2. Chord-tone sets (§1.6)**

Dict keyed by `(mode, chord_name)` where mode is `"major"` or `"minor"`,
chord_name is the Roman numeral string.  Value is a `frozenset[int]` of
scale degrees (0-based mod 7).

For minor mode V, degree 6 is the raised 7th — store it as degree 6
in the frozenset, but provide a separate flag or helper indicating this
degree requires chromatic raising.  The degree-to-MIDI conversion needs
to know.

Provide: `chord_tones(mode: str, chord: str) -> frozenset[int]`

**3. Minor equivalents (§1.5)**

Provide: `minor_equivalent(major_chord: str) -> str`
Maps `"I"->"i"`, `"IV"->"iv"`, `"ii"->"iio"`, `"V"->"V"`.

The progression data should already store minor-mode progressions with
the correct chord names.  This function is for reference/assertion only.

**4. Harmonic rhythm selection (§1.1)**

Provide: `select_harmonic_level(cell_ticks: tuple[int, ...]) -> str`

Input: the flat tick sequence from a cell chain (e.g. for iamb+dactyl:
(1,2,2,1,1)).  Compute mean tick value.  Return `"fast"`, `"medium"`,
or `"slow"` per the thresholds in §1.1.

**5. Beat-to-chord lookup**

Provide: `chord_at_tick(progression: tuple[str, ...], tick_offset: int, bar_ticks: int) -> str`

Given a progression tuple (one entry per harmonic slot), a note's tick
offset from bar 0, and the bar_ticks value, return the active chord name
at that position.  The slot width = `(n_bars * bar_ticks) / len(progression)`.

Preconditions to assert:
- tick_offset >= 0
- total ticks divides evenly by len(progression)

**6. Cross-relation check (§4)**

Provide: `is_cross_relation(degree_a: int, degree_b: int, raised_a: bool, raised_b: bool) -> bool`

Two adjacent notes are a cross-relation if they share the same scale
degree (mod 7) but differ in chromatic alteration.  This only matters
in minor mode at chord boundaries involving V (where degree 6 is
raised).

**7. Melodic minor helpers (§2)**

Provide: `degree_to_semitone(degree: int, mode: str, raised: bool = False) -> int`

Convert a 0-based scale degree to semitone offset from tonic.
- In major mode, `raised` is ignored.
- In minor mode, if `raised=True` and degree % 7 is 5 or 6 (the 6th
  and 7th scale steps), return the raised semitone (natural + 1).
- Assert that raised is only True for degrees 5 and 6 (mod 7) in minor.

Provide: `should_raise(degree_mod7: int, direction: str) -> bool`

Returns True if the degree should use the raised form given the fill
direction.  Only degrees 5 and 6 in minor ascending context return True.
`direction` is `"ascending"` or `"descending"`.

## Constraints

- No imports from the existing pitch pipeline (head_enumerator,
  cpsat_generator, pitch_generator, validator, head_generator).
- May import from `shared/constants.py` for MAJOR_SCALE,
  NATURAL_MINOR_SCALE.
- May import from `motifs/subject_gen/constants.py`.
- All data as module-level frozen structures (tuples, frozensets, dicts
  of immutable values).
- Functions sorted alphabetically.
- One parameter per line.  Type-hint everything.
- Assert preconditions.
- Single-line docstrings on public functions.
- L002: no magic numbers — name thresholds as constants (e.g.
  `FAST_THRESHOLD = 3.0`, `MEDIUM_THRESHOLD = 1.5`).
- L016: logging only.
- L019: ASCII only.
- L020: keyword args only in calls.

## Checkpoint

After creating the file, verify it imports cleanly:

```
python -c "from motifs.subject_gen.harmonic_grid import chord_tones, select_harmonic_level, get_progressions, chord_at_tick, is_cross_relation, degree_to_semitone, should_raise; print('OK')"
```

Then verify data correctness:

```python
from motifs.subject_gen.harmonic_grid import chord_tones, get_progressions, select_harmonic_level

# Major I = {0, 2, 4}
assert chord_tones(mode="major", chord="I") == frozenset({0, 2, 4})
# Minor V contains raised 7th (degree 6)
assert 6 in chord_tones(mode="minor", chord="V")
# Fast level has 6 patterns
assert len(get_progressions(level="fast")) == 6
# Mean tick 4.0 -> fast
assert select_harmonic_level(cell_ticks=(4, 4, 4, 4)) == "fast"
# Mean tick 2.0 -> medium
assert select_harmonic_level(cell_ticks=(2, 2, 2, 2)) == "medium"
# Mean tick 1.0 -> slow
assert select_harmonic_level(cell_ticks=(1, 1, 1, 1)) == "slow"
print("All checks passed")
```

Report any design decisions not covered by the spec.
