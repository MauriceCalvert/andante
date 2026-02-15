# Dead Code Cleanup

All items verified dead by grep — no production imports, no production callers.

---

## Delete Entire Files

| File | Lines | Status |
|---|---|---|
| `motifs/enumerator.py` | 344 | ✅ DONE |
| `motifs/extract_melodies.py` | 228 | ✅ DONE |
| `motifs/frequencies/analyse_intervals.py` | 242 | ✅ DONE |
| `motifs/melodic_features.py` | 603 | ✅ DONE |
| `planner/koch_rules.py` | ~380 | ✅ DONE |
| `builder/episode_writer.py` | ~216 | ✅ DONE |
| `viterbi/demo.py` | — | ✅ DONE |
| `viterbi/test_brute.py` | — | ✅ DONE |
| `viterbi/bach_compare.py` | — | ✅ DONE |
| `viterbi/midi_out.py` | — | ✅ DONE |
| `shared/errors.py` | ~30 | ✅ DONE |

---

## Delete Dead Items From Live Files

### builder/types.py ✅ DONE (already clean)

### builder/soprano_writer.py ✅ DONE (already clean, only a comment ref remains)

### builder/imitation.py ✅ DONE (already clean)

### builder/phrase_writer.py
- ~~Delete `_pad_to_offset`~~ ✅ already gone
- Delete `_is_walking` — SKIP: still called on line 42 by `_bass_for_plan`

### planner/arc.py
- ~~Delete `select_tension_curve`, `build_tension_curve`~~ ✅ already gone
- ~~Delete `get_tension_at_position`~~ SKIP: called by kept `get_energy_for_bar`
- ~~Delete `TENSION_TO_ENERGY`~~ SKIP: doesn't exist (it's function `tension_to_energy`, which is kept)
- ~~Delete `load_yaml`~~ SKIP: called by kept `load_named_curve`
- ~~Remove `Brief` and `MacroForm` imports~~ ✅ already gone

### planner/plannertypes.py ✅ DONE (already clean)

### planner/schema_loader.py ✅ DONE (already clean)

### motifs/figurae.py ✅ DONE
- Deleted `all_names`, `by_affect`, `_by_affect` dict. Kept `by_category` (called by `melodic_figurae` → `select_for_motif`)

### shared/voice_types.py ✅ DONE
- Deleted `Role`, `Actuator`, `InstrumentDef`, `Voice`, `Instrument`, `ScoringAssignment`, `TrackAssignment`. Kept `Range` only.

### shared/key.py ✅ DONE
- Deleted `get_scale_for_context`, `midi_to_floating`, `floating_to_midi`, `FloatingNote` import
- Deleted 2 test functions + FloatingNote import from tests/shared/test_key.py

### shared/pitch.py ✅ DONE
- Deleted `FloatingNote` class, `Rest`, `MidiPitch`, `Pitch` alias, `wrap_degree`. Kept `degree_to_nearest_midi`, `place_degree`, `select_octave` only.

### shared/counterpoint.py ✅ DONE
- Deleted `find_non_parallel_pitch`, its test class, and stale Key import from test file

### shared/constants.py ✅ DONE
- Deleted 41 dead constants (original estimate was 14; full grep found 41)

### viterbi/scale.py ✅ DONE
- Deleted `CMAJ_OFFSETS`

### viterbi/mtypes.py ✅ DONE
- Deleted `MIDI_C3`, `MIDI_C4`, `MIDI_C5`

---

## After All Deletions ✅ DONE

All imports pass. No dangling references found.
