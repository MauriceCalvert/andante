# Completed

## STR-1: Stretto overflow bars become episodes (2026-02-27)

Modified stretto stamping loop in `planner/imitative/subject_planner.py` so that
only `subject_bars` (2) get SUBJECT+STRETTO stamping. Overflow bars are now stamped
as EPISODE+EPISODE with head/tail fragment assignments and direction derived from
the next episode's key journey. Peroration strettos default to descending.

**Bob's verdict:** Bar 12 (F major) succeeds — staggered semiquaver descents in
both voices, genuine dialogic handoff after stretto. Bars 34/37 (peroration) serve
as adequate breath marks with bass-led ascending motion. Bar 23 (D minor) fails —
crotchet oscillation in bass, near-silence in soprano (2 notes). Fragen's fragment
cells are too short to fill the bar.

**Open:** Bar 23 sparse output needs Fragen minimum note density filter.
Soprano enters late in peroration bars (beats 3-4 only) — acceptable for
breath marks but not ideal.

## SUB-2b: Density trajectory tuning (2026-02-27)

Filtered equal note-count splits (MIN_NOTE_COUNT_DIFFERENCE=2) in
`_valid_note_splits` to eliminate 6+6 splits producing zero trajectory.
Increased W_DENSITY_TRAJECTORY from 2.0 to 3.0. All 10 generated subjects
now have nonzero density trajectory; 5/10 above 30%, 5/10 at ~29%.
Both sparse->dense and dense->sparse directions represented.

## SUB-2: Segment-level rhythmic density (2026-02-27)

Moved density from SubjectVocabulary to SegmentSpec so head and tail
segments get independent density settings. Plan generator now enumerates
contrasting (head_density, tail_density) pairs. Added _density_trajectory
scoring criterion (W=2.0) rewarding measurable density shift between
segments. Threaded head_n through score_subject and subject_features.
Reduced W_REPETITION_PENALTY from 1.0 to 0.5 (interim, pending SUB-3).
Deleted legacy flat-enumeration selector code; selector.py now delegates
to planned_selector.py.

**Bob's verdict:** 5 of 10 subjects show audible density shift (3
sparse-to-dense, 2 dense-to-sparse). Both trajectory directions present.
3 subjects have zero trajectory due to equal head/tail note counts.

**Open:** W_DENSITY_TRAJECTORY needs tuning upward (3.5-4.0) to exclude
zero-trajectory subjects. All subjects converge to 12 notes (variety
issue, not SUB-2 regression).

## SUB-1: Fix tonal answer generation (2026-02-27)

Fixed double-transposition bug in tonal answer generator. Swapped
TONIC_TRANSPOSITION (3->4) and DOMINANT_TRANSPOSITION (4->3) in
`motifs/answer_generator.py`. Removed +7 from `answer_midi()` in
`motifs/subject_loader.py` — answer degrees already encode the tonal
transposition, so rendering at tonic+7 was double-transposing. Updated
stale comment in `builder/thematic_renderer.py:66`. Added
`patch_library_answers()` to `scripts/generate_subjects.py` with
`--patch-answers` CLI flag. Regenerated all output and library .subject
files. Tonic-region notes now answered at P5 (7 semitones), dominant-region
at P4 (5 semitones) — textbook tonal answer.

## EPI-2b: Fragen fallback retry (2026-02-27)

Added `_FRAGEN_MAX_RETRIES = 3` and retry loop to `builder/phrase_writer.py`.
On realisation failure, the code tries up to 3 alternative fragments before
falling through to per-voice episode rendering. With seed 42: all 5 episodes
render via fragen on first attempt (zero retries, zero fallbacks). Bars 28-30
(previously static half-notes from per-voice fallback) now have canonic
staggered texture matching the other episodes. Fault count unchanged (15).

## EPI-2a: Cell vocabulary expansion (2026-02-27)

Added rhythmic diminution and cross-source pairing to `motifs/fragen.py`.
New `_diminish` halves all durations (discards if any < 1/16). New
`_source_family` strips _inv/_dim suffixes for family grouping. `extract_cells`
now produces diminished variants of raw+inverted cells (309 -> 526 cells).
`build_fragments` now pairs chains from different source families sorted by
rhythmic contrast ratio (capped at 200 pairs). Result: 24 diminished-cell
fragments and 22 cross-source fragments survive consonance checking. Pipeline
fault count unchanged (15). Rhythm profile count increased modestly (10->11)
due to aggressive dedup; raw catalogue increased 7.2x.

## HRL-7: Note writer figured bass enrichment (2026-02-27)

Added `chord_display_label` to harmony.py (numeral + inversion suffix).
Added `harmony: str = ""` field to Note dataclass. Stamped grid-derived
harmony labels on Viterbi notes in bass_viterbi.py and soprano_viterbi.py
(only when harmonic_grid is not None). Rewrote `_build_harmony_map` in
note_writer.py with two-pass logic: grid-derived labels take priority,
bass-pitch inference fills gaps. Diagnostic only, no audible change.
Not exercised in current invention seed (no FREE-fill bars); will appear
in galant genres or longer free-fill episodes.

## EPI-1: Inter-entry episodes (variable length) (2026-02-27)

Replaced fixed 2-bar `_EPISODE_BARS` with `_episode_bars_for_distance()`: 2/3/4 bars
based on semitone distance (<=3/4-5/6+). `generate_entry_sequence()` now appends an
episode dict after every development entry. `plan_subject()` step 1 computes episode
bar costs via the new function. Step 2b stripped of auto-episode insertion (half-cadences
retained). Step 3 stamps episode BarAssignments with ascending/descending iteration.
Dead `_auto_episode` handler deleted. `_extract_lead_voice_and_key()` handles episode
type for HC key extraction. Pipeline: 42 bars, 5 episodes (3,2,3,2,3 bars), 15 faults
(all pre-existing). Entry/episode ratio ~50/31 vs old ~85/15.

## HRL-6: Secondary dominants V/V, V/vi (2026-02-27)

`ChordLabel` gains `secondary_target: int | None = None`. `parse_roman` handles
slash notation (`V/vi`, `V/V`) with early return. `chord_pcs` computes chromatic
triad PCs from target MIDI (P5 above target, major 3rd, perfect 5th).
`build_stock_harmonic_grid`: V/V replaces ii/iv in cadential acceleration (≥3 bars),
V/vi→vi at bars 2–3 for runs ≥5 bars. Pipeline clean, 13 faults (all pre-existing).
Invention free fills are all ≤2 bars — code verified by inspection, not audibly
exercised in this seed.

## HRL-5: Passing 6/3 chords in stock harmonic grid (2026-02-27)

`ChordLabel` gains `inversion: int = 0`. `parse_roman` strips `"64"`/`"6"` inversion
suffixes before quality/seventh, fully backward-compatible. New module-level functions
`bass_degree(label)` and `bass_pc(label, key)` resolve the bass pitch-class for inverted
chords. `HarmonicGrid.to_bass_beat_list(beat_grid)` returns singleton frozensets at
inverted positions (exploiting the existing 5.0 `chord_tone_cost` penalty). In
`build_stock_harmonic_grid`, after HRL-4 cadential acceleration, consecutive entry pairs
≥ one bar apart receive a passing 6/3 chord at half-bar offset — diatonic triad via
shortest-path direction, `dataclasses.replace(..., inversion=1)`. Bass Viterbi switched
from `to_beat_list` to `to_bass_beat_list`. Pipeline clean: 199+141 notes, 13 faults
(all pre-existing). Episodes show predominantly stepwise bass approach to harmonies.

## HRL-4: Cadential acceleration (2026-02-27)

In `build_stock_harmonic_grid` (`builder/galant/harmony.py`), for runs of 3+ bars
the final bar now splits: pre-dominant (first half) → V (second half). Major uses
ii→V, minor uses iv→V. Creates harmonic urgency approaching cadences. 9 lines,
one file. No new limitations.

