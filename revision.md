# Revision Plan: Wire Figuration System into Phrase Writer

## Problem

The planning layers (L1–L5) produce excellent schema chains, key areas, and
structural anchors. The realisation layer (L6 phrase writer) fills between
anchors with:
- **Soprano**: diatonic steps toward the next target — no ornament, no motivic identity.
- **Bass pillar**: repeats the last structural pitch → drone.
- **Bass walking**: diatonic steps toward the next target → lifeless.

A complete, unused figuration system sits in `builder/figuration/`:
diminutions.yaml (60+ figures), bass_patterns.yaml (20+ patterns),
rhythm_templates.yaml, figuration_profiles.yaml — all loaded, validated,
cached, and never called.

## Strategy

**Minuet first, then gavotte.** Invention (contrapuntal bass) is a separate,
harder problem — out of scope for this revision.

Each phase is self-contained: it compiles, passes its own test, and does not
break existing tests. Phases build on each other sequentially.

---

## Phase 0: Plumb `bass_pattern` into PhrasePlan

**Goal**: PhrasePlan carries the genre's declared `bass_pattern` name so the
phrase writer can look it up without needing the full GenreConfig.

**Changes**:
1. `builder/phrase_types.py` — add field `bass_pattern: str | None = None`
   to PhrasePlan.
2. `builder/phrase_planner.py` — in `_build_single_phrase_plan()`, pass
   `bass_pattern=genre_config.bass_pattern` when constructing PhrasePlan.

**Test**: Run `pytest tests/builder/test_L5_phrase_planner.py` — all existing
tests pass. Add one assertion in a minuet test that verifies
`plan.bass_pattern == "arpeggiated_3_4"`.

---

## Phase 1: Figure Selection Engine

**Goal**: A pure function `select_figure()` that, given an interval between
two structural tones plus context, returns one `Figure` from the diminution
table — deterministically.

**New file**: `builder/figuration/selection.py`

**Functions**:
```python
def classify_interval(from_midi: int, to_midi: int, key: Key) -> str:
    """Map a MIDI interval to a FIGURATION_INTERVALS key."""
    # Count diatonic steps, map to unison/step_up/third_down/etc.

def select_figure(
    interval: str,
    note_count: int,
    character: str,
    position: str,          # "passing" | "cadential" | "schema_arrival"
    is_minor: bool,
    bar_num: int,           # for deterministic rotation (V001)
    prev_figure_name: str | None,  # avoid immediate repetition
) -> Figure:
    """Deterministic figure selection from diminution table."""
    # 1. get_diminutions()[interval] → candidate list
    # 2. Filter: note_count match (or chainable), character compat,
    #    minor_safe, cadential_safe if position == "cadential"
    # 3. Sort by weight descending
    # 4. Rotate by bar_num % len(candidates)  (V001 determinism)
    # 5. Skip prev_figure_name if possible
```

**Test**: `tests/builder/test_figuration_selection.py`
- `test_classify_interval_step_up`: C4→D4 in C major → "step_up"
- `test_classify_interval_third_down`: E4→C4 in C major → "third_down"
- `test_classify_interval_unison`: same pitch → "unison"
- `test_select_figure_returns_figure`: returns Figure with matching interval
- `test_select_figure_deterministic`: same inputs → same output
- `test_select_figure_avoids_repeat`: with prev_figure_name set, picks different
- `test_select_figure_cadential_filter`: position="cadential" → only cadential_safe figures

---

## Phase 2: Figurate Span — Soprano

**Goal**: A function `figurate_soprano_span()` that takes two anchor
(offset, midi) pairs and a duration budget, selects a figure, picks a
rhythm template, and returns `list[tuple[Fraction, int, Fraction]]`
(offset, midi, duration) — the notes that fill the gap.

**New file**: `builder/figuration/soprano.py`

**Functions**:
```python
def figurate_soprano_span(
    start_offset: Fraction,
    start_midi: int,
    end_offset: Fraction,
    end_midi: int,
    key: Key,
    metre: str,
    character: str,
    position: str,
    is_minor: bool,
    bar_num: int,
    midi_range: tuple[int, int],
    prev_figure_name: str | None,
) -> tuple[list[tuple[Fraction, int, Fraction]], str]:
    """Fill gap between two structural tones with a figured diminution.

    Returns (notes, figure_name) where notes is [(offset, midi, duration), ...].
    """
    # 1. gap = end_offset - start_offset
    # 2. classify_interval(start_midi, end_midi, key)
    # 3. compute_rhythmic_distribution(gap, density) → (note_count, unit_dur)
    #    OR: look up rhythm_templates for (note_count, metre)
    # 4. select_figure(interval, note_count, ...)
    # 5. Realise figure degrees as MIDI pitches:
    #    - anchor_midi = start_midi
    #    - for each degree offset in figure.degrees:
    #        pitch = key.diatonic_step(anchor_midi, degree_offset)
    #        clamp to midi_range
    # 6. Pair pitches with durations from rhythm template
    # 7. Return [(offset, pitch, dur), ...], figure_name
```

**Key decisions**:
- If `note_count` doesn't match any figure exactly, try chainable figures
  or fall back to the closest available note_count, adjusting rhythm template.
- If no rhythm template exists for `(note_count, metre)`, use equal subdivision.
- First note always lands on `start_offset` with `start_midi`.
- Last note's pitch need not be `end_midi` — the next structural tone handles
  arrival. But it should be close (within a step).

**Test**: `tests/builder/test_figurate_soprano.py`
- `test_figurate_span_step_up_3_4`: C4→D4 in 3/4 → 3 notes filling one bar
- `test_figurate_span_third_down_3_4`: E4→C4 → ornamental fill, 3–4 notes
- `test_figurate_span_unison`: same pitch → mordent or turn
- `test_all_pitches_in_range`: no note outside midi_range
- `test_durations_sum_to_gap`: total duration == end_offset - start_offset
- `test_deterministic`: same inputs → same outputs
- `test_first_note_is_anchor`: first pitch == start_midi

---

## Phase 3: Wire Soprano Figuration into phrase_writer

**Goal**: Replace the stepwise fill in `generate_soprano_phrase()` with calls
to `figurate_soprano_span()`. Structural tones remain anchored; only the fill
between them changes.

**Changes to `builder/phrase_writer.py`**:

1. Import `figurate_soprano_span` from `builder.figuration.soprano`.
2. Refactor the inner loop of `generate_soprano_phrase()`:
   - Keep: structural tone computation (lines 301–337) — unchanged.
   - Keep: rhythm cell selection per bar — but use it only to determine
     note_count and accent pattern, NOT for pitch computation.
   - Replace: the pitch-decision block (lines 376–488) with:
     ```
     For each span between consecutive structural tones:
       notes, fig_name = figurate_soprano_span(
           start=structural_tones[i],
           end=structural_tones[i+1],
           ...
       )
       Append notes, preserving all existing guards (D007, ugly interval,
       range check, max melodic interval).
     ```
   - Keep: all validation (_validate_soprano_notes).
3. The existing guards (D007 cross-bar repetition, ugly interval deflection,
   range assertion) run as post-filters on the figured output. If a guard
   triggers, it deflects the offending pitch by one diatonic step — same logic
   as today, but now acting on figured pitches rather than stepwise pitches.

**Test**: Run full `pytest tests/builder/test_L6_phrase_writer.py`.
Then generate a minuet (via `tests/integration/test_system.py` or equivalent)
and inspect the trace: soprano should show figure names in diagnostics and
varied intervallic content.

Specific new test: `test_soprano_figuration_varied` — generate 3 different
phrase plans for minuet, verify that soprano intervals include at least one
skip (interval > 2 semitones) in each phrase. This proves we're not just
stepping anymore.

---

## Phase 4: Wire Bass Pattern into phrase_writer

**Goal**: When `plan.bass_texture` is `"pillar"` AND `plan.bass_pattern` is
set, replace the drone-pillar logic with `realise_bass_pattern()`. The
existing walking texture stays for now.

**Changes to `builder/phrase_writer.py`**:

1. Import `get_bass_pattern`, `realise_bass_pattern` from
   `builder.figuration.bass`.
2. In `generate_bass_phrase()`, at the `if texture == "pillar":` branch:
   - If `plan.bass_pattern` is not None:
     - Look up pattern: `pattern = get_bass_pattern(plan.bass_pattern)`
     - Per bar, call `realise_bass_pattern(pattern, bass_degree, key, ...)`.
     - Convert returned `(offset, midi, dur)` tuples to `Note` objects.
     - Run all existing counterpoint checks: voice overlap, parallels,
       consonance on accented beats.
   - Else: keep existing pillar logic (backward compat for genres without
     a declared bass_pattern).
3. Soprano-ceiling check: for each bass note from the pattern, look up the
   soprano pitch at that offset. If bass > soprano, try octave below. If
   still crossing, assert.

**Test**: Run `pytest tests/builder/test_L6_phrase_writer.py`.
New test: `test_bass_pattern_arpeggiated_minuet` — build a minuet PhrasePlan,
generate bass, verify:
- Bass has at least 3 distinct pitches per bar (not a drone).
- No pitch repetition across consecutive notes in the same bar (arpeggio moves).
- All notes within lower_range.
- No voice crossing with soprano.

---

## Phase 5: End-to-End Minuet Generation + Listening Test

**Goal**: Generate a full minuet, write MIDI, listen.

**Changes**: None (code is already wired). This phase is purely validation.

**Test steps**:
1. Run the full pipeline for the minuet genre.
2. Inspect the .trace file: every non-cadential phrase should show figure
   names for soprano and pattern name for bass.
3. Play the MIDI output. Verify:
   - Soprano has melodic interest: turns, passing tones, skips — not just
     linear interpolation.
   - Bass arpeggiates (root-3rd-5th in each bar) — not a drone.
   - No counterpoint violations audible (parallel fifths/octaves, voice
     crossing, unprepared dissonance on strong beats).
4. Compare before/after MIDI files.

**Success criteria**: "Bob doesn't throw it across the room."

---

## Phase 6: Gavotte Bass Pattern

**Goal**: The gavotte uses `bass_pattern: half_bar` (root + fifth per bar).
After Phase 4, this should already work. This phase just validates it.

**Changes**: Possibly none — if the half_bar pattern's beat positions use
the sentinel `"half"`, verify that `realise_bass_pattern` resolves them
correctly for 4/4.

**Test**:
1. Generate a gavotte, inspect trace.
2. Verify bass has 2 notes per bar (half-note pulse), alternating root/fifth.
3. Run `pytest tests/builder/test_L6_phrase_writer.py` — all pass.
4. Play MIDI. Section A (pillar+pattern) should have half-bar bass.
   Section B (walking) should remain stepwise — walking is unaffected.

---

## Phase 7: Tracing & Diagnostics

**Goal**: The trace file shows what figures and patterns were selected, so
future debugging is possible.

**Changes**:
1. In `figurate_soprano_span()`, return the figure name alongside notes
   (already in Phase 2 signature).
2. In `generate_soprano_phrase()`, collect figure names per span and log
   them to the trace: `"soprano_figures": ["mordent_static", "groppo_down", ...]`.
3. In `generate_bass_phrase()`, log the pattern name:
   `"bass_pattern": "arpeggiated_3_4"`.
4. Wire these into the existing trace infrastructure (whatever format
   `builder/L7_compose.py` uses for per-phrase diagnostics).

**Test**: Generate a piece, read the .trace file, assert it contains
`soprano_figures` and `bass_pattern` keys for non-cadential phrases.

---

## Out of Scope (Future Work)

- **Invention / contrapuntal bass**: Requires imitative counterpoint engine.
  Separate project.
- **Cadential figuration**: cadence_writer uses fixed templates. Wiring
  cadential.yaml figures into it is a later refinement.
- **Figuration profiles**: The profile→schema mapping (figuration_profiles.yaml)
  is nice-to-have for context-sensitive selection. Phase 1 uses simpler
  filtering. Profiles can be layered in later.
- **Rhythm inequality / overdotting** (S001): Performance practice, not
  composition. Out of scope.
- **Sarabande, bourrée, trio sonata**: Once minuet + gavotte work, extending
  to other patterned genres is mechanical.
