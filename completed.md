# Completed

## SGv2 — Gesture-based subject generator (2026-02-17)

Complete rewrite of the baroque fugue subject generator. All musical data
(rhythms, interval shapes, cadence formulas) moved from hardcoded Python to
three YAML files. Generators become thin assembly layers.

**New files created:**
- `data/subject_gestures/head_gestures.yaml` — 22 head gestures (6 archetypes)
- `data/subject_gestures/tail_cells.yaml` — 22 tail cells (11 desc, 11 asc)
- `data/subject_gestures/kadenz_formulas.yaml` — 7 kadenz formulas
- `motifs/gesture_loader.py` — cached loaders with frozen dataclasses

**Files rewritten:**
- `motifs/kopfmotiv.py` — gesture instantiation (interval_type → concrete degree)
- `motifs/fortspinnung.py` — tail-cell chaining with range bounds
- `motifs/kadenz.py` — formula lookup with budget gap-filling

**Files extended:**
- `data/archetypes/*.yaml` (6 files) — added gestures/cells/formulas fields
- `motifs/archetype_types.py` — new fields in all three constraint dataclasses
- `motifs/head_generator.py` — `chromatic_offsets` param in `degrees_to_midi`
- `motifs/subject_generator.py` — min_kadenz=1/2, chromatic offset plumbing
- `scripts/archetype_sampler.py` — min_kadenz=1/2, multi-bar-count loop

**Bugs fixed during implementation:**
1. `compound_dotted_run`: interval_types/rhythm length mismatch fixed
2. `dance_gigue_leaps`: rhythm too short for 4-note gesture fixed
3. `range_min` check removed from `kopfmotiv._validate` (gestures span less)
4. `min_kadenz` raised from 1/4 to 1/2 (all formulas ≥ 3/8)
5. Sampler target-bars loop changed to [2, 1, 3, 4] (compound needs 4 bars)

## SG-FIX2 — Fix remaining triadic and validator failures (2026-02-17)

Three root causes found and fixed:

**1. IEEE 754 budget corruption:** `budget_fraction` values loaded from YAML as
Python floats produced irrational `Fraction` denominators (e.g. `Fraction(0.4)` =
`3602879701896397/4503599627370496`). After `_quantise_budget` floored to 1/32
multiples, triadic got `25/32` instead of `3/4`, forcing `_fit_durations` to
append tiny 1/32 fill notes. Fix: `limit_denominator(1024)` on `budget_fraction`
before arithmetic in `generate_kopfmotiv`. Also changed all non-clean budget
fractions in archetype YAMLs: triadic `0.4 → 0.375` (= 3/4), scalar/chromatic/
rhythmic `0.45 → 0.4375` (= 7/8).

**2. Over-strict leading-tone rule:** `_check_unresolved_leading_tone` fired on
degree 6 in any context. Triadic arpeggios passing through degree 6 are not
leading-tone function. Fix: only fire when degree 6 is approached by stepwise
ascent from below (approach interval = +1), indicating genuine leading-tone
function.

**3. Over-strict consecutive-leaps rule:** Threshold `> 4` semitones rejected
idiomatic triadic intervals (consecutive 4ths/5ths). Fix: raised to `> 7`
(only consecutive intervals larger than a perfect fifth in the same direction
are flagged).

Files modified: `motifs/melodic_validator.py`, `motifs/kopfmotiv.py`,
`motifs/test_melodic_validator.py`, `data/archetypes/{triadic,scalar,chromatic,
rhythmic}.yaml`. All 6 archetypes now generate successfully. All tests pass.

## SG-FIX — Fix triadic and compound archetype generation failures (2026-02-17)

**Problem 1 — Triadic 100% validation failure:**
`_check_consecutive_leaps` in `motifs/melodic_validator.py` fired on every
arpeggiated triad because the threshold was `abs(iv) > 2`. Changed to
`abs(iv) > 4` — consecutive thirds (3–4 semitones) are now permitted;
consecutive 4ths+ in the same direction still fail. Updated
`test_melodic_validator.py`: test 5 split into 5a (consecutive thirds →
PASS) and 5b (consecutive 4th+5th → FAIL).

**Problem 2 — Compound 1/32 crash in CS generator:**
Two-pronged fix: (a) `_kinetic_half` in `fortspinnung.py` — added
`_MIN_KINETIC_NOTE = Fraction(1, 16)`, clamped `note_val` to >= 1/16,
replaced candidates filter and break threshold with the new constant; also
added backstop in `_validate_fortspinnung` rejecting any kinetic_half result
with notes < 1/16. (b) `_generate_compound` in `kopfmotiv.py` — added
`_MIN_COMPOUND_NOTE = Fraction(1, 16)`, filtered both `long_val` and per-note
`val` selections to `>= 1/16`; added backstop in `_validate` rejecting
compound heads with notes < 1/16. No changes to `countersubject_generator.py`,
`VALID_DURATIONS`, or shared constants.

## SG-LISTEN — Per-archetype MIDI sampler (2026-02-17)

Created `scripts/archetype_sampler.py`. Calls the generation chain directly (kopfmotiv → fortspinnung → kadenz → validate_melody → analyse_answer) for each of the six archetypes using their natural affect/mode/metre/tonic/direction. Up to 50 attempts per archetype with independent `random.Random(42)`. Writes `samples/{name}_{affect}_{mode}.midi` + `.fugue` per archetype, and `samples/archetype_sampler.midi` (combined, back-to-back demo sequences with 2-bar silence between archetypes). No existing modules modified.

## SG9 — Rewrite subject_generator.py using archetype chain (2026-02-17)

Rewrote `motifs/subject_generator.py` to use the SG1–SG8 archetype chain. Updated `planner/planner.py` to pass `affect` and `genre` to `generate_fugue_triple`.

**`motifs/subject_generator.py`:**
- Deleted all private pitch/validation helpers (`_sample_valid_head`, `_random_pitch_sequence`, `_is_valid_pitch`, `_intervals`, `_midi_intervals`, `_has_*`, `_is_melodically_valid`, `_largest_leap_position`, `_is_filled`, `_crosses_barline`, `_combine_head_tail`).
- Deleted `generate_subject_batch` and `SUPPORTED_METRES`.
- `GeneratedSubject`: removed `satisfied_figurae`; added `archetype: str = ""` and `direction: str = ""` fields. `durations` remains `Tuple[float, ...]`; `scale_indices` unchanged.
- `generate_subject()`: new signature adds `genre: str = "invention"`, `n_candidates: int = 30`; `max_attempts` reduced to 200. Body runs the nine-step chain: `select_archetype` → `load_archetype` → (for each target_bars [2,1,3,4]) `generate_kopfmotiv` → `generate_fortspinnung` → `generate_kadenz` → `validate_melody` → `analyse_answer` → `analyse_fragments` → `score_subject`. Converts `Fraction` durations to `float` at the public boundary.
- `generate_fugue_triple()`: adds `affect` and `genre` parameters; passes both to `generate_subject`.
- `main()`: adds `--genre` (`-g`); removes `--batch` branch. Passes `affect` and `genre` to both generation functions.
- `write_fugue_file`, `write_fugue_demo_midi`, `write_note_file`, `write_midi_file`: unchanged.

**`planner/planner.py`:** Added `affect=affect` and `genre=genre` to the `generate_fugue_triple` call in `generate_to_files`.

## SG8 — Subject Scorer (2026-02-17)

Created `motifs/subject_scorer.py` and `motifs/test_subject_scorer.py`. No existing files modified.

**`motifs/subject_scorer.py`:** Public API `score_subject(...) -> SubjectScore`. `SubjectScore` is a frozen dataclass with `total`, `affect_figurae`, `archetype_fidelity`, `fragment_quality`, `rhythmic_interest` (all 0–1). Weights: affect=0.3, archetype=0.3, fragment=0.2, rhythm=0.2.

Four private helpers (alphabetical): `_score_affect_figurae` calls `get_affect_profile` + `score_subject_affect` (converting `Fraction` durations to `float`); returns 0.5 for `None`/unknown affect. `_score_archetype_fidelity` averages four binary checks: interval compliance (fraction of intervals ≤ max allowed), range compliance (1.0/0.5/0.0), start degree, answer feasibility. `_score_fragment_quality` uses `head_cell_score` + 0.1 inversion bonus (capped at 1.0). `_score_rhythmic_interest` averages duration variety and characteristic rhythm profile matching (even/long_short/bipartite/dance).

**`motifs/test_subject_scorer.py`:** Five cases — perfect match (total > 0.7), bad triadic match (archetype_fidelity < 0.5), no affect (affect_figurae == 0.5), infeasible answer (fidelity lowered), even profile (high char rhythm / low variety).

## SG7 — Fragment Analyser (2026-02-17)

Created `motifs/fragment_analyser.py` and `motifs/test_fragment_analyser.py`. Added four constants to `shared/constants.py`: `IDEAL_CELL_MIN_BEATS`, `IDEAL_CELL_MAX_BEATS`, `LONG_NOTE_MULTIPLIER`, `MAX_SEQUENTIAL_INTERVAL`.

**`motifs/fragment_analyser.py`:** Public API `analyse_fragments(degrees, durations, head_length, metre, mode) -> FragmentAnalysis`. `FragmentPoint(index, reason)` and `FragmentAnalysis(break_points, head_cell_score, inversion_viable, inversion_reasons)` are frozen dataclasses.

Break-point detection (priority order, deduplicated by index): (1) head_boundary always at `head_length`; (2) long_note: index after any note whose duration ≥ `LONG_NOTE_MULTIPLIER × median`; (3) barlines: notes whose onset is an exact multiple of bar_duration, skipping index 0 and indices already claimed.

Head cell score (mean of four 0–1 sub-scores): length fitness (linear ramp at 1–2 beats, plateau at 2–4, ramp-down at 4–6, zero otherwise); rhythmic distinctiveness (distinct duration count / head length); sequential viability (all degree intervals ≤ `MAX_SEQUENTIAL_INTERVAL`); contour distinctiveness (0.5 if monotonic, 1.0 if non-monotonic).

Inversion viability: negates each consecutive degree interval and reconstructs from the same start degree, then runs `validate_melody`.

**`motifs/test_fragment_analyser.py`:** 6 test cases — barline deduplication, long-note break point, high cell score, monotonic contour penalty (expected 0.6875), inversion viable, inversion fails (tritone in inverted form).

## SG6 — Answer Analyser (2026-02-17)

Created `motifs/answer_analyser.py` and `motifs/test_answer_analyser.py`.

**`motifs/answer_analyser.py`:** Public API `analyse_answer(degrees, durations, metre, mode) -> AnswerAnalysis`. `AnswerAnalysis` frozen dataclass (feasible, answer_type, boundary_index, mutation_indices, rejection_reason).

Boundary detection: `_find_boundary_index` walks notes, accumulating onset as `Fraction`. A degree-4 note qualifies as a boundary only if (1) its bar-relative onset is in `_STRONG_BEAT_OFFSETS[metre]` and (2) the immediately following note is in `_CONFIRMATION_DEGREES = {4,5,6}` mod 7 (or the note is the last in the sequence). Unrecognised metres fall back to `{Fraction(0)}`.

Mutation: `_mutation_indices_at_boundary` checks whether the pair (boundary_index−1, boundary_index) is a 0→4 crossing using `answer_generator._crosses_boundary`. Delegates actual mutation to `answer_generator._apply_tonal_mutation`. Validates the mutated degrees with `melodic_validator.validate_melody`; infeasible if validation fails.

No existing files modified. Imports `_apply_tonal_mutation` and `_crosses_boundary` from `answer_generator` (module-private, same package).

**`motifs/test_answer_analyser.py`:** 9 cases covering scalar strong/weak beat, passing tone, no-degree-4, end-on-4, 3/4 strong/weak, infeasible tritone-outline-after-mutation (major mode), BWV-578-pattern weak-beat, and 0→4 leap on strong beat with feasible mutation.

## SG5 — Melodic Validator (2026-02-17)

Created `motifs/melodic_validator.py` and `motifs/test_melodic_validator.py`.

**`motifs/melodic_validator.py`:** Public API `validate_melody(degrees, durations, mode) -> MelodyValidation`. `MelodyValidation` frozen dataclass (valid: bool, reasons: tuple[str, ...]).

Internal helpers:
- `_degree_to_semitone`: converts scale degree to semitone offset using `divmod(degree, 7)`; handles negative degrees and multi-octave degrees via Python's correct negative divmod.
- `_absolute_semitones`: maps degree tuple to semitone tuple.
- `_check_seventh_leap`: any |interval| ∈ {10, 11}.
- `_check_tritone_leap`: any |interval| == 6.
- `_check_tritone_outline`: any 4-note positional span where |s[i+3] - s[i]| == 6.
- `_check_consecutive_leaps`: two consecutive |interval| > 2 in same direction.
- `_check_unresolved_leading_tone`: any degree % 7 == 6 not followed by degree % 7 == 0.

Mode→scale via `_MODE_SCALES` dict; `durations` accepted for API consistency but currently unused.

**`motifs/test_melodic_validator.py`:** 9 test categories (10 cases total):
1. Clean scalar → PASS; 2. Tritone leap → FAIL; 3. Seventh leap → FAIL;
4. Tritone outline → FAIL; 5. Consecutive leaps → FAIL; 6. Unresolved LT → FAIL;
7. Resolved LT → PASS; 8a/8b. Minor/major mode sensitivity; 9. All 6 archetypes full pipeline.

## SG4 — Kadenz Generator (2026-02-17)

Created `motifs/kadenz.py` and `motifs/test_kadenz.py`.

**`motifs/kadenz.py`:** Public API `generate_kadenz(body, archetype, metre, affect, rng) -> KadenzResult | None`. `KadenzResult` frozen dataclass (degrees, durations, total_beats, n_bars, archetype_name) — includes full body (head + continuation) prepended.

Logic:
- `_bar_duration`: `Fraction(metre[0], metre[1])` (whole-note units)
- `_min_kadenz_beats`: 1/16 for (3,8), 1/4 otherwise
- **Bar count (N)**: ceiling of `(body.beats_used + min_kadenz) / bar_dur`; if `kadenz_budget > 2*bar_dur` → None (body too short); if `kadenz_budget < min_kadenz` → bump N
- **Landing degree**: `rng.choices` from `archetype.kadenz.stable_degrees` with weights {0:50, 4:30, 2:20}
- **Path step**: `sign(landing - body_final)` (1 if at landing already)
- **`_generate_approach_path`**: stepwise ±1 from body_final (exclusive) to landing (inclusive); overshoot guard snaps last entry to landing
- **`_fit_kadenz_durations`**: applies augmentation (double last 1-2 notes if `may_augment`); drops from front if over budget (preserving landing at end); extends landing note if under; inserts fill note(s) before landing as last resort
- **`_validate_kadenz`**: sum == budget, all valid durations, final degree in stable_degrees, all intervals ≤ ±1

No existing files modified.

## SG2 — Kopfmotiv Generator (2026-02-17)

Created `motifs/kopfmotiv.py` and `motifs/test_kopfmotiv.py`.

**`motifs/kopfmotiv.py`:** Public API `generate_kopfmotiv(archetype, direction, total_beats, mode, metre, affect, rng) -> KopfmotivResult | None`. `KopfmotivResult` frozen dataclass (degrees, durations, beats_used, direction, archetype_name). Six archetype-specific generators:
- `_generate_scalar`: even stepwise line, density from affect tempo × rhythm_density (min rank wins)
- `_generate_triadic`: arpeggiated with long first note (long_short profile), max one direction reversal
- `_generate_chromatic`: crotchet-per-note stepwise with 30% chance of ±2 wider step for colour
- `_generate_rhythmic`: repeating 2–3 note rhythmic cell; degrees from triad tones/neighbours
- `_generate_compound`: long-value static half; repeated notes via interval 0 (in compound.intervals)
- `_generate_dance`: strong/weak beat alternation, leaps on strong beats, steps on weak

Shared utilities: `_affect_density` (tempo × rhythm_density → min rank), `_fit_durations` (budget enforcement using `_fill_move` for archetype-valid fill intervals), `_quantise_budget` (floor to 1/32 multiple), `_validate` (sum check, valid durations, start degree, span, note count, all intervals in head.intervals).

**`motifs/test_kopfmotiv.py`:** Tests all 6 archetypes with seed 42 (up to 20 retries each), verifies: result not None, sum(durations) == expected_budget, all durations valid, start degree correct, span in range. Prints degrees/durations/beats_used, labels PASS/FAIL.

No existing files modified.

## SG3 — Fortspinnung Generator (2026-02-17)

Created `motifs/fortspinnung.py` and `motifs/test_fortspinnung.py`.

**`motifs/fortspinnung.py`:** Public API `generate_fortspinnung(head, archetype, continuation_budget, mode, metre, affect, rng) -> FortspinnungResult | None`. `FortspinnungResult` frozen dataclass (degrees, durations, beats_used, archetype_name) — includes head prepended. Six archetype-specific functions:
- `_continue_or_reverse` (scalar): step in head direction, reverse at 40–70% turn point; ±1 only; range_extension clamped
- `_gap_fill` (triadic): contrary motion, shorter note values (_LONG_SHORT_SHORT); 30% wider ±2 step
- `_chromatic_resolve` (chromatic): same note values as head (_most_common_duration); ±1; 30% gentle reversal
- `_maintain_rhythm` (rhythmic): _extract_rhythm_cell (period 2/3 detection); pitch moves up to max_new_interval=3; triad tones and neighbours preferred
- `_kinetic_half` (compound): starts on head.degrees[-1] (must_start_on_head_final); fast run at min(density_note, quaver); ±1/±2; reverses at range boundary
- `_periodic` (dance): strong/weak alternation via _dance_note_value; wider leaps on strong, steps on weak; max_new_interval=5

Shared helpers: `_fit_cont_durations`, `_allowed_intervals`, `_pick_fill_interval`, `_most_common_duration`, `_extract_rhythm_cell`, `_validate_fortspinnung`. Density helpers and `_dance_note_value` duplicated from kopfmotiv.

**`motifs/test_fortspinnung.py`:** TOTAL_BEATS=2, METRE=(4,4), MIN_KADENZ_BEATS=1/4. For each archetype: generates kopfmotiv then fortspinnung (up to 20 retries). Verifies: not None, beats_used == head_budget + cont_budget, all durations valid, compound cont_degrees[0] == head.degrees[-1]. Prints full head/cont degrees and durations.

No existing files modified.

## SG1 — Subject Archetype Types, Data, and Selector (2026-02-17)

Created the foundational data layer for archetype-driven subject generation (steps 1–3 of migration path).

**`motifs/archetype_types.py`:** Frozen dataclasses `HeadConstraints`, `ContinuationConstraints`, `KadenzConstraints`, `RhythmProfile`, `AffinityMap`, `ArchetypeSpec`. `load_archetype(name)` loads from `data/archetypes/{name}.yaml` with defensive parsing. `load_all_archetypes()` loads all six with module-level cache.

**`data/archetypes/*.yaml` (6 files):** scalar, triadic, chromatic, rhythmic, compound, dance. Values from `docs/subject_archetypes.md`. All German affect names from `affects.yaml`. Dance has metre_filter [[3,4],[6,8],[3,8]].

**`motifs/archetype_selector.py`:** `select_archetype(affect, genre, mode, metre, rng) → (name, direction)`. Metre filter → genre filter → affect+mode scoring (primary=3.0, secondary=1.0, absent=0.1) → weighted rng.choices → direction via direction_bias + affect contour ±0.3 bias.

**`motifs/test_archetypes.py`:** Five PASS/FAIL checks: 6 archetypes load; Klage→chromatic; Freudigkeit/invention→rhythmic; None→any; dance excluded at (4,4).

No existing files modified.

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