# Completed

## I5+I8 — Rhythmic Independence + Beat-1 Continuity (2026-02-17)

**I5 — Soprano Viterbi rhythmic independence (`builder/soprano_viterbi.py`, `builder/free_fill.py`):**
Added `avoid_onsets_by_bar` parameter to `generate_soprano_viterbi`. When provided, Step 2 uses bar-by-bar `select_cell` (matching `bass_viterbi.py` pattern) instead of `compute_rhythmic_distribution`. Computes bar-relative structural soprano offsets as `required_onsets` for cell selection. In `free_fill.py`, soprano companion branch (`free_voice_idx == 0`) now computes bar-relative bass onset sets and passes them as `avoid_onsets_by_bar`. When `avoid_onsets_by_bar` is None, existing span-based rhythm grid logic is unchanged.

**I8 — Beat-1 continuity validation (`builder/compose.py`):**
Added `_ensure_beat1_coverage` function. Per phrase result, checks every bar for beat-1 note coverage across both voices (including prior accumulated notes). If uncovered, extends latest-ending note before bar_start (prefers bass). Called after every `write_phrase` in `compose_phrases`. Seed 42 invention Klage produced no beat-1 gaps (safety net ready but not triggered).

**Evaluation (seed 42, invention Klage):** All bars have beat-1 coverage. Rhythmic independence good in bars with density contrast (bars 2, 5-6, 11-12, 17-18, 19-20). Lockstep fault at bars 7-8 (7 consecutive simultaneous attacks) is thematic CS+subject overlap, not FREE companion — out of scope. I5 soprano companion path not exercised by this seed (all soprano bars are thematic).

## Group E — I7: Rhythmic displacement in episodes (2026-02-17)

**I7 — Beat displacement for episode fragments (`motifs/fragen.py`):**
Added `beat_displacement: Fraction = Fraction(0)` to `Fragment` dataclass. Added module-level `_BEAT_DISPLACEMENTS = (Fraction(1,4), Fraction(1,2))`. Extended `_consonance_score` with `cell_displacement` parameter; strong-beat determination now uses `(t + cell_displacement) % bar_length`. `build_fragments` and `build_hold_fragments` each generate displaced variants for every valid base fragment, keeping only those passing the consonance threshold. `realise()` extends `model_dur` to include `beat_displacement` for the leader voice. `_emit_notes()` emits a gap-fill held note at the leader's first degree from the iteration base to `beat_displacement`, then starts the leader cell at `beat_displacement` offset within each iteration. `dedup_fragments` now includes `beat_displacement` in its dedup key so displaced variants survive deduplication. `_fragment_signature` includes `beat_displacement` so the diversity mechanism treats displaced fragments as perceptually distinct and rotates through them. No changes to `phrase_writer.py` or `entry_layout.py`.

## Group D — Parametric contour + pedal descent (2026-02-17)

**D1 — Parametric three-point contour (`viterbi/mtypes.py`, `viterbi/costs.py`, `viterbi/pathfinder.py`, `viterbi/pipeline.py`, `viterbi/generate.py`):**
Replaced the Gaussian arc contour with a piecewise-linear three-point `ContourShape(start, apex, apex_pos, end)` dataclass. Removed `ARC_PEAK_POSITION`, `ARC_SIGMA`, `ARC_REACH` from `costs.py`. Replaced `compute_contour_targets` with a piecewise-linear interpolator that converts degree offsets to semitones via `avg_step = 12 / len(key.pitch_class_set)`. Threaded `contour: ContourShape | None = None` through `find_path`, `solve_phrase`, `generate_voice`. Default `ContourShape()` approximates the old Gaussian (rise to +4 degrees at p=0.65, return to 0). All existing callers unchanged.

**D2 — Pedal descending ramp (`builder/soprano_viterbi.py`, `builder/phrase_writer.py`):**
Added `contour` parameter to `generate_soprano_viterbi`. In `_write_pedal`, created `ContourShape(start=3.0, apex=3.0, apex_pos=0.0, end=-3.0)` — a pure linear descent from +3 to −3 degrees relative to range midpoint (≈10 semitone swing). Passed as `contour=pedal_contour` to `generate_soprano_viterbi`. Contour targets are monotonically non-increasing; acceptance criterion (≥4 st end-to-start descent) satisfied analytically.

## Group C — I1a + I1b: Pedal Soprano Tension + Cadential Bass Formula (2026-02-17)

**I1a — Pedal soprano (`_write_pedal` in `builder/phrase_writer.py`):**
Replaced the old two-knot plan (tonic at bar 1 and bar N) with a per-beat descending sequence. For a 2-bar 4/4 pedal, 8 structural knots are placed at beats 1–4 of each bar with degrees `[5,5,4,4,3,3,2,2]` (descent rate = one degree per half-bar). Added `density_override="high"` to `generate_soprano_viterbi` for semiquaver motion throughout. Set `cadential_approach=True` on `pedal_plan`. Updated soprano hint MIDI to use degree 5. Captured `beat_unit` from `parse_metre`. The structural descent G→F→E→D is audible at the half-bar level; ascending Viterbi fills between knots are a known cost-function limitation.

**I1b — Cadential bass formula (`data/cadence_templates/templates.yaml`):**
4/4 cadenza_composta bass: `[5,5,5,1]` → `[4,5,5,1]`. 3/4 cadenza_composta bass: `[5,1]` with durations `["3/4","3/4"]` → `[4,5,1]` with `["1/4","1/2","3/4"]`. Both changes introduce a subdominant pre-dominant before V→I. Pipeline confirms `B(4,5,5,1)` for the invention cadence.

**Known limitation:** The final 4 semiquavers of the pedal soprano ascend from D4 back to G4 (net descent = 0 from phrase start). This is Viterbi cost-function behavior: after the last structural knot at beat 4 of bar 2, the Viterbi ascends in the 4-note span to the auto-final knot, which is extended rather than sounding as a new pitch. Fixing this requires Viterbi cost changes (deferred).

## Group B — Viterbi Cost Fixes: I2 + I4 + I6 (2026-02-17)

**I2 — Direct perfect penalty:** Added `direct_perfect_cost()` to `viterbi/costs.py`. Fires when both voices move in the same direction (similar motion) and the arrival interval is a perfect consonance (P1/P5/P8). Cost: 60.0. Wired into `pairwise_cost` (new `"direct_perf"` key) and accumulated in `transition_cost`. Also increased `BEAM_WIDTH` from 300 to 500 in `viterbi/pathfinder.py` so non-parallel alternatives survive pruning before HC3 fires. Added `dp=` field to `-trace` output.

**I4 — Graduated spacing cost:** Replaced flat `spacing_cost` (8.0 below P5, 4.0 above 2 octaves) with a graduated ramp. Below 7st (voices merged): steep 25.0/st ramp stacked on 10.0/st base. Between 7–10st: moderate 10.0/st ramp. Between 10–12st: mild 2.0/st. Ideal zone 12–24st: 0.0. Above 24st: 3.0/st. Above 28st: 6.0/st additional. Removed old constants; added new SPACING_CRITICAL/TIGHT/WIDE and per-semitone rates.

**I6 — Stronger contrary motion:** `COST_CONTRARY_BONUS` −2.0 → −4.0; `COST_OBLIQUE_BONUS` −0.5 → 0.0; `COST_SIMILAR_PENALTY` 1.0 → 2.5. Net swing from similar to contrary is now 6.5 (was 3.0). Target: contrary motion ≥ 28%.

## I3 + I12 — MusicXML overflow fix and answer entry timing (2026-02-17)

**I3:** Removed `part.makeRests(fillGaps=True, inPlace=True)` and `part.makeMeasures(inPlace=True)` from `_build_part()` in `builder/musicxml_writer.py`. These calls were redundant (superseded by `makeNotation=True` on `score.write()`) and harmful: `makeRests` created a 6-quarter rest spanning the pre-answer gap, then `makeMeasures` stuffed that rest plus bar-2 notes into one measure — producing 6 beats in a 4/4 bar.

**I12:** Changed `answer_offset_beats: 2` to `answer_offset_beats: 4` in `data/genres/invention.yaml`. Answer now enters at bar 2 beat 1 (one-bar delay, as in BWV 772) instead of bar 2 beat 3.

**Result:** Answer head (D–B–G descending thirds) enters on bar 2 beat 1, immediately recognisable as the subject transposed to the dominant. MusicXML bars sum to exactly 4 beats. All 8 genres pass.

**Open:** Peroratio (bars 19–21) is melodically flat — deferred.

## CP3.1 -- Unified hold-exchange entries for cross-bar descent (2026-02-16)