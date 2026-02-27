# Result: HRL-7 — Note writer figured bass enrichment

## Code Changes

### 1. `builder/galant/harmony.py`
Added `_INVERSION_SUFFIX` dict and `chord_display_label(label)` function after
`bass_pc`. Returns numeral + inversion suffix (e.g. "IV6", "ii64") unless the
numeral already ends with the suffix.

### 2. `builder/types.py`
Added `harmony: str = ""` field to the `Note` dataclass after `creator`.
Default empty string preserves backward compatibility.

### 3. `builder/bass_viterbi.py`
- Added `import dataclasses` and `from builder.galant.harmony import chord_display_label`
- After `validate_bass_notes` and before `return notes_tuple`, stamps
  grid-derived harmony labels on all notes when `harmonic_grid is not None`.

### 4. `builder/soprano_viterbi.py`
- Added `import dataclasses` and `from builder.galant.harmony import chord_display_label`
- After `audit_voice` and before `return notes_tuple, ()`, stamps grid-derived
  harmony labels on all notes when `harmonic_grid is not None`.

### 5. `builder/note_writer.py`
Rewrote `_build_harmony_map` with two-pass logic:
- Pass 1: collect grid-derived labels from `note.harmony`
- Pass 2: bass-pitch inference for remaining offsets
- Merge: grid labels take priority, fill gaps with bass inference
- Change-detection preserved (only writes label when it differs from previous)

---

## Bob's Assessment

### Pass 1 — What do I hear?

This is a diagnostic-only change. No audible difference. The MIDI output is
byte-identical to pre-HRL-7. The .note file is the only affected artefact, and
it is a text annotation file — not an audio file.

Looking at the .note output for this invention (seed 42, C major):

The harmony column reads as before — bass-inferred Roman numerals throughout.
I see "I", "IV", "V", "vi", "ii", "viio", "V/V" at appropriate bass pitch
transitions. No new labels appear. No labels disappeared. The change-detection
logic is clean: harmony labels only appear on the first note at each offset
where the harmony changes. No label spam.

This is expected. The invention genre at this seed has no FREE-fill bars. All
42 bars are covered by subject entries, countersubjects, stretto, fragen
episodes, pedal, and cadence templates — none of which use Viterbi with a
harmonic grid. The figured bass enrichment will first appear in compositions
that route through `generate_bass_viterbi` or `generate_soprano_viterbi` with
a non-None `harmonic_grid` (galant genres or longer free-fill episodes).

### Pass 2 — Theory

The harmony column at subject/CS bars shows bass-inferred Roman numerals
derived from the lowest pitch at each onset. At bar 2 beat 4, the V/V label
(F#3 in C major) is correct — F#3 is a tritone above tonic, the standard
bass-inference mapping for #4. At cadential bars (9, 20, 31), the half-cadence
harmonies (V at the final beat) are accurate since cadential bass notes are
chord roots.

### Checkpoint Answers

1. **Do FREE-fill bars show figured bass?** — No FREE-fill bars exist in this
   invention. All episodes are fragen-rendered thematic material. The enrichment
   code is structurally in place but not exercised by this seed/genre.

2. **Do subject/CS/stretto bars still show bass-inferred harmony?** — Yes,
   unchanged. These bars have no harmonic grid; `note.harmony` is empty; the
   fallback bass-inference path runs identically to pre-HRL-7.

3. **Are figured bass labels consistent with bass pitches?** — N/A for this
   seed (no grid-derived labels present). The bass-inferred labels remain
   consistent.

4. **Is change-detection logic correct?** — Yes. Harmony labels appear only
   when the label changes from the previous one. Verified by visual scan of
   the .note file: no consecutive duplicate labels at adjacent offsets.

---

## Chaz's Diagnosis

Bob reports no musical complaints — this is a diagnostic-only change with no
audible effect. No faults to trace.

**Structural verification:**

The code path is correct. `chord_display_label` produces:
- `"I"` for `ChordLabel(numeral="I", inversion=0)` → suffix "" → returns "I"
- `"IV6"` for `ChordLabel(numeral="IV", inversion=1)` → suffix "6" → "IV" does
  not end with "6" → returns "IV6"
- `"V/V"` for secondary dominant (already has no inversion suffix) → returns "V/V"

The `dataclasses.replace` call in both Viterbi files creates new Note instances
with the `harmony` field set, preserving all other fields. The import of
`dataclasses` module (separate from `from dataclasses import dataclass`) is
required for `dataclasses.replace`.

`_build_harmony_map` in note_writer.py now iterates `all_offsets` (union of
bass_at_offset and grid_labels keys) rather than just bass_at_offset, ensuring
that grid-only onsets (if a grid-derived note exists at an offset with no bass
note) are not dropped.

**Fault count unchanged:** 15 faults, all pre-existing (cross_relation,
ugly_leap, direct_fifth/octave, unprepared_dissonance, parallel_rhythm). None
introduced by HRL-7.

**Note count unchanged:** 227 soprano + 164 bass = 391 total, identical to
pre-HRL-7.

---

Please listen to the MIDI and let me know what you hear.
