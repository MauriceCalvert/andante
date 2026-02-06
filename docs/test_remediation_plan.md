# Test & Conformance Remediation Plan

Addresses all gaps identified in the audit of the redesign implementation
against the spec in `docs/redesign.md`.

---

## 1. Code Fixes (spec conformance)

### 1.1 BASS_VOICE constant — L002/L017 violation

`phrase_writer.py` defines `BASS_VOICE = 1` locally. `cadence_writer.py` hardcodes `voice=1` inline.
Meanwhile `TRACK_SOPRANO` is properly in `shared/constants.py`.

Fix: add `TRACK_BASS = 1` to `shared/constants.py`. Replace all local definitions and inline literals
in `phrase_writer.py` and `cadence_writer.py`.

### 1.2 Triple write_cadence call in phrase_writer

`write_phrase()` calls `write_cadence()` for cadential plans. But `generate_soprano_phrase()` and
`generate_bass_phrase()` also independently check `is_cadential` and call `write_cadence()`.
These are redundant code paths that would double-call if someone invoked the lower functions directly.

Fix: add `assert not plan.is_cadential` at the top of `generate_soprano_phrase` and
`generate_bass_phrase`. Remove the cadential guards from those functions. `write_phrase()` is
the sole entry point for cadential plans.

### 1.3 RhythmCell missing accent_pattern

The spec defines `accent_pattern: tuple[bool, ...]` on `RhythmCell`. The implementation and YAML
omit it entirely. The phrase writer only checks beat 1 of each bar for strong-beat logic.

Fix: add `accent_pattern` field to `RhythmCell` dataclass with a default derived from the cell's
position in the bar (first note = strong, rest = weak). Add `accent_pattern` to `cells.yaml` for
cells where the accent falls elsewhere (e.g. syncopated patterns). Update `_is_strong_beat` in
`phrase_writer.py` to consult the cell's accent pattern when available, falling back to beat-1
detection.

### 1.4 Sequential schema handling

`_build_single_plan` takes `schema_def.soprano_degrees` directly for sequential schemas (fonte, monte).
These have special degree patterns that transpose per segment. Tests P-04/P-05 skip them.

Fix: sequential schemas need segment-aware degree expansion in `_build_single_plan`. The degree
positions should reflect the repeated/transposed structure. Add a `_expand_sequential_degrees()`
helper. Remove the `if schema_def.sequential: continue` skip in P-04/P-05 once the expansion
is implemented.

---

## 2. Dead and Weakened Tests

### 2.1 S-13 leap-then-step is a no-op

The test body contains `continue` and `pass` where assertions should be. It can never fail.

Fix: replace with a proper assertion:

```python
if interval > 4:
    recovery = abs(notes[i + 2].pitch - notes[i + 1].pitch)
    assert recovery <= 2, (
        f"Leap of {interval} at offset {notes[i].offset} not followed by step (got {recovery})"
    )
    leap_dir = notes[i + 1].pitch - notes[i].pitch
    step_dir = notes[i + 2].pitch - notes[i + 1].pitch
    assert (leap_dir > 0) != (step_dir > 0) or step_dir == 0, (
        f"Leap at offset {notes[i].offset} not followed by contrary motion"
    )
```

If this causes failures, the fix belongs in `phrase_writer.py`'s soprano generation, not in
weakening the test.

### 2.2 S-05/B-05 weakened for cadential schemas

For cadential plans these only check `total > 0`. The cadential template duration is known —
it equals `template.bars * bar_length`. The test should verify the exact sum.

Fix: look up the template and assert `total == template.bars * METRE_BAR_LENGTH[plan.metre]`.

### 2.3 C-08/C-09 thresholds masking real bugs

C-08 allows 3 overlaps per voice. C-09 allows 8 gaps per voice. The spec says zero.

Fix: keep the current thresholds as a `@pytest.mark.xfail(strict=False)` or separate
`test_*_strict` variants that assert zero, so CI doesn't block but the gap is visible.
Add the strict variants now; fix the underlying phrase-boundary bugs separately.

---

## 3. Genre Coverage

### 3.1 Extend GENRES to all supported genres

`conftest.py` defines `GENRES = ("bourree", "gavotte", "invention", "minuet", "sarabande")`.
The spec says tests run for every genre in `data/genres/`. Missing: chorale, fantasia, trio_sonata.

Fix: scan `data/genres/` at import time, exclude `_default.yaml`, build GENRES dynamically:

```python
GENRES = tuple(
    p.stem for p in sorted(Path(DATA_DIR / "genres").glob("*.yaml"))
    if p.stem != "_default"
)
```

Genres that lack rhythm cells for the phrase path should be marked `xfail` or `skip` in
L5/L6/L7/system tests with a clear reason, not silently omitted.

### 3.2 PHRASE_GENRES should be derived, not hardcoded

`PHRASE_GENRES = ("gavotte", "minuet", "sarabande")` is repeated in three test files.
It should be computed: a genre is phrase-capable if `get_cells_for_genre(genre, metre)` is
non-empty for the genre's metre.

Fix: add a helper `get_phrase_genres()` in `tests/helpers.py` that loads all genre configs,
checks rhythm cell availability, and returns the tuple. Use it in L6/L7/system/cross-phrase tests.

---

## 4. Key and Affect Parametrisation

### 4.1 Add minor key testing

All pipeline calls use `key="c_major"`. Degree-to-MIDI conversion for minor keys exercises
different intervals, raised 6th/7th at cadences (L007), and enharmonic handling.

Fix: add `"a_minor"` to a `KEYS` tuple in conftest. Parametrise L5 and L7 tests over both keys.
L6 fixture tests can remain on C major (they test schema-level invariants, not key-dependent
behaviour). System tests should run both keys.

### 4.2 Extend affect parametrisation beyond L2

L5/L6/L7/system tests hardcode `affect="Zierlich"`. Different affects may produce different
tonal plans, which produce different schema chains, which produce different phrase plans.

Fix: parametrise L5 tests over at least 2 affects (Zierlich, Dolore). L6/L7/system can stay
on one affect — the affect primarily influences L2 output, and L5 is the first layer where
that feeds through.

---

## 5. YAML Cross-Validation Tests

### 5.1 Every genre+metre has rhythm cells

No test validates that every genre's metre has at least one matching rhythm cell in `cells.yaml`.

Fix: new test file `tests/test_yaml_integrity.py`. For each genre YAML, load its metre, then
assert `len(get_cells_for_genre(genre, metre)) > 0`.

### 5.2 Every cadential schema has templates for all supported metres

No test validates that every cadential schema in `schemas.yaml` has a template in
`templates.yaml` for every metre that any genre using that schema requires.

Fix: in `test_yaml_integrity.py`, load all schemas where `position == "cadential"`. For each,
determine which genres reference it (via their schema sequences). For each such genre's metre,
assert a template exists.

### 5.3 Rhythm cell durations sum to bar length

`_validate_cell` checks this at load time, but there is no test that forces load and catches
assertion errors as test failures.

Fix: add a test that calls `load_rhythm_cells()` and verifies every cell. This also serves as
a regression test for YAML edits.

### 5.4 Cadence template durations sum correctly

Same as above — `_validate_template` checks at load time. Add a test that forces load and
catches assertion errors.

### 5.5 Schema soprano/bass degree counts match

Some schemas (passo_indietro noted in completed.md) have mismatched soprano/bass degree counts.
The spec requires `len(soprano_degrees) == len(bass_degrees)` for non-sequential schemas.

Fix: add a test that loads all schemas and asserts this invariant. Known violations become
`xfail` with a ticket reference.

---

## 6. Missing Cross-Phrase Checks

### 6.1 PhraseContext is unused

`write_phrase` accepts `PhraseContext` but has a TODO saying it's not used for cross-phrase
parallel checking. The cross-phrase tests (XP-*) check the assembled composition, which is
correct, but `PhraseContext` is dead infrastructure.

Fix: either implement cross-phrase parallel detection in `write_phrase` using `PhraseContext`,
or remove the parameter and type entirely. Dead code is a liability. If removing, update
`compose_phrases` which currently builds and passes it.

### 6.2 notes_at_offsets drops duplicate offsets

`notes_at_offsets` returns `{n.offset: n.pitch for n in notes}`. If two notes from different
phrases have the same offset (phrase boundary overlap), only one is kept. This could cause
`check_no_parallel` to miss violations at phrase joins.

Fix: `notes_at_offsets` should return `list[tuple[Fraction, int]]` or handle duplicates.
Alternatively, `check_no_parallel` should iterate note pairs directly rather than building
an offset dict.

---

## 7. Execution Order

The work should proceed in dependency order. Each phase produces a testable result.

**Phase A — Foundations (no test changes)**
- [x] 1.1 PHRASE_VOICE_BASS constant (TRACK_BASS=3 already existed for 4-voice path; added PHRASE_VOICE_BASS=1 for 2-voice phrase path)
- [x] 1.2 Remove redundant cadential guards (asserts in generate_soprano/bass_phrase)
- [x] 6.1 Removed PhraseContext (dead infrastructure)

**Phase B — YAML integrity tests (new test file)**
- [x] 5.1 Genre+metre cell coverage (chorale/fantasia/trio_sonata xfail — no cells)
- [x] 5.2 Cadential template coverage
- [x] 5.3 Cell duration sums
- [x] 5.4 Template duration sums
- [x] 5.5 Schema degree count consistency

**Phase C — Fix dead/weak tests**
- [x] 2.1 S-13 leap-then-step (fix test, then fix code if it fails)
- [x] 2.2 S-05/B-05 cadential duration check
- [x] 2.3 C-08/C-09 strict variants
- [x] 6.2 notes_at_offsets duplicate handling

**Phase D — Extend parametrisation**
- [ ] 3.1 Dynamic GENRES from filesystem
- [ ] 3.2 Dynamic PHRASE_GENRES from cell availability
- [ ] 4.1 Minor key testing
- [ ] 4.2 Multi-affect L5 testing

**Phase E — Structural improvements**
- [ ] 1.3 RhythmCell accent_pattern
- [ ] 1.4 Sequential schema degree expansion

Phase E is the most invasive and can be deferred if the other phases surface enough issues
to keep busy.
