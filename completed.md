# Completed

## Subject generator bug fixes and rhythm cell expansion
- `duration_generator.py`: added `_spans_barline()` rejecting notes crossing bar boundaries; `bar_ticks` threaded through `_generate_sequences`; cache key v6
- `melody_generator.py`: rule 6.4b rejects consecutive repeated final pitch; CP patterns for 4 new cells (pyrrhic, snap, tribrach, amphibrach)
- `pitch_generator.py`: cache key bumped to `melody_pitch_v2`
- `rhythm_cells.py`: added PYRRHIC (1,1), SNAP (1,3), TRIBRACH (1,1,1), AMPHIBRACH (1,2,1); `notes` field replaced with derived `@property`; transition table expanded 7×7 → 11×11

## BM-3b: Scoring extension and dead code removal
- `constants.py`: added `W_HARMONIC_VARIETY: float = 1.0`
- `scoring.py`: added `_harmonic_variety()` — counts how many of I/IV/V/ii are touched by the degree sequence (mod 7), scores (touched-1)/3.0 clamped to [0,1]; functions reordered alphabetically (D, H, I, Re, Rh, S); `score_subject` max raised from 5.0 to 6.0; `subject_features` extended from 6D to 7D with harmonic variety as 7th dimension
- Deleted dead files: `head_enumerator.py`, `cpsat_generator.py`, `cpsat_prototype.py` — no import references remain in source

## BM-3a: Wire melody generator into pipeline
- `duration_generator.py`: `_generate_sequences` now yields `(indices, cells, score)`; `_cached_scored_durations` returns `dict[int, list[tuple[tuple[int,...], tuple[Cell,...]]]]`; cache key changed to `cell_dur_v2_*` to avoid stale cache reads
- `pitch_generator.py`: full rewrite — old cpsat/head_enumerator path deleted; new `_cached_validated_pitch_for_cells` delegates to `generate_pitched_subjects` and caches by `(cell_key, mode, n_bars, bar_ticks)`
- `selector.py`: import updated to `_cached_validated_pitch_for_cells`; main loop restructured to iterate `(d_seq, cells)` per dur_option and call pitch gen per cell sequence; HEAD_SIZE/MIN_HEAD_FINAL_DUR_TICKS filters applied before pitch gen; `fixed_midi` branch updated to unpack `(d_seq, _cells)`; `Cell` import added for type annotation

## BM-2: Melody generator
- Created `motifs/subject_gen/melody_generator.py`: pitch generation engine (steps 1-7 of baroque_melody.md)
- NoteSlot dataclass, CP_PATTERNS table (data not if-chains), recursive skeleton enumeration with gap/freq/range pruning, deterministic P-slot fill with neighbour-tone detours, full section-6 validation including melodic minor raising, contour classification
- Checkpoint: major 1 result, minor 1 result for spec test sequence; DOTTED*4 produces 2 per mode
- Some cell patterns (DACTYL*4, TIRATA*4) produce 0 results due to structural constraint interaction

## BM-1: Harmonic grid data module
- Created `motifs/subject_gen/harmonic_grid.py`: stock progressions (12 patterns, 3 levels), chord-tone sets (major+minor), minor equivalents, harmonic level selection, chord_at_tick lookup, cross-relation check, melodic minor helpers (degree_to_semitone, should_raise, is_raised_chord_degree)
- Pure data + lookup, no generation logic, no pitch pipeline imports
- All checkpoint assertions pass

## Cell-based rhythm engine (replaces bar-fill duration enumerator)
- Created `motifs/subject_gen/rhythm_cells.py`: Cell dataclass, 6 baroque rhythm cells, CELLS_BY_SIZE, TRANSITION table, SCALES
- Rewrote `motifs/subject_gen/duration_generator.py`: partition-based cell sequence generation with transition filtering and scoring
- Updated `motifs/subject_gen/constants.py`: DURATION_TICKS expanded to (1,2,3,4,6) for dotted values; removed 5 dead bar-fill constants
- `_cached_scored_durations` signature unchanged; new cache key `cell_dur_*`
