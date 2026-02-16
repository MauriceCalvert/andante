# Completed

## F4 -- Signature-based fragment diversity (2026-02-16)

**Problem:** FragenProvider selected fragments by usage count alone (unused → least-used), treating all fragments as interchangeable. Even with multiple fragments in the catalogue, selection was arbitrary within usage tiers. Result: episodes could use perceptually similar fragments (same melodic contour, same rhythm) just because both were unused, missing opportunities for variety.

**Solution:** Added `_fragment_signature()` helper using **full interval sequence** as melodic fingerprint. Initially tried coarse features (interval count, leap count, opening move) but this created signature collisions: 17 bass-led fragments collapsed to only 9 unique signatures, with one signature covering 5 fragments. Upgraded to use complete melodic contour: `(intervals, offset, separation)` where intervals is the full tuple of degree steps. This gives each unique melodic shape a unique signature.

Modified `FragenProvider.get_fragment()` to track chronological history (`_history: list[Fragment]`) and compare candidates against all previously-used signatures (infinite history window). Selection prioritizes:
1. Unused fragments with novel signatures (melodic shape never used before)
2. Unused fragments (any signature)
3. Used fragments with novel signatures
4. Least-used fragments (fallback)

**Implementation:** Added `_fragment_signature()` function returning `tuple[tuple[int, ...], Fraction, int]`, `_history` field to `__init__`, and `_mark_used()` helper. Refactored selection logic to build `all_used_sigs` set from entire composition history and partition candidates by usage and signature novelty. Infinite history ensures signatures never repeat until all available signatures in the catalogue are exhausted.

**Results:** Seed 42 invention with enhanced signatures: 17 bass-led fragments → 16 unique signatures (1 genuine duplicate). Episode bass patterns now show full variety: 13, 12, 8 notes with distinct melodic shapes. Soprano patterns (follower voice in bass-led episodes) share cells where the catalogue genuinely pairs different bass patterns with the same soprano cell. All 8 genres pass test suite.

**Files modified:** motifs/fragen.py

## TRACE-1 -- Function-specific schema names in imitative traces (2026-02-16)

**Problem:** All non-cadential imitative phrase plans were labeled "subject_entry" in trace output, making it impossible to distinguish actual subject entries from episodes, hold exchanges, pedal points, and stretto sections. The computed function ("entry", "episode", "hold_exchange", "pedal", "stretto") was discarded after grouping.

**Solution:** Modified `planner/imitative/entry_layout.py:192-218` to map the computed `function` value to appropriate schema names. Entry function maps to "subject_entry" (preserves existing name), while episode/hold_exchange/pedal/stretto use their function names directly as schema_name.

**Results:** Trace output (L5 Phrases) now shows:
- "subject_entry" for actual subject/answer entries
- "episode" for episodic sections
- "hold_exchange" for hold-exchange passages
- "pedal" for pedal points
- "stretto" for stretto sections
- "cadenza_composta" for cadences (unchanged)

Test invention trace (seed 42): 12 plans across 24 bars with 6 distinct schema types (was 11× "subject_entry" + 1× "cadenza_composta"). All 8 genres pass test suite.

**Files modified:** planner/imitative/entry_layout.py

## F3 -- Fragen as a stateful class (2026-02-16)

**Problem:** All three episodes in invention used identical fragment (same two bars pasted three times). No variety, no development. Episodes should use different fragments or voicings. Additionally, three bugs: (1) `_find_start` prioritised range margin over proximity, causing large leaps into episodes. (2) Cross-relations not checked at episode boundaries. (3) Beat-1 gaps in follower voice at iteration boundaries when `fragment.offset > 0`.

**Solution:** Created `FragenProvider` class in `motifs/fragen.py` with per-composition fragment tracking (`_used_indices`, `_use_count`). Provider selects unused fragments first, then least-used. Threaded through `compose.py` → `write_phrase` → `_write_thematic`. Fixed `_find_start` to threshold-gate margin (`_MIN_RANGE_MARGIN = 3`), then select by proximity when `prefer_upper/lower_pitch` given. Added cross-relation rejection for all four boundary pairs (upper→upper, lower→lower, upper→lower, lower→upper). Added gap-fill pass in `_emit_notes` to extend last note before gap.

**Results:** All 8 genres pass test suite. Seed 42: 3 episodes (bars 7, 13, 19), zero cross-relations, zero beat-1 gaps. Episode entry leaps: 7st, 7st, 2st (acceptable fifths, then smooth step). Bob: episodes still repetitive (same fragment three times) — this is a data issue. The `call_response` subject produces only 1 distinct soprano-led fragment after deduplication. FragenProvider correctly selects unused/least-used fragments; the variety just isn't in the catalogue. Known Limitation §3.1 acknowledged in task spec: "Soprano-led fragments may not exist... fragment extraction would need reform, which is out of scope." Code is correct; data is limited.

## CP4 -- Fix answer transposition and mode propagation (2026-02-16)

**Problem:** Two bugs made every fugue entry sound wrong. (1) Real answer double-transposed: answer degrees shifted +4 scale degrees AND converted against dominant_midi (+7 semitones), producing wrong starting pitch and dissonant harmony. (2) Minor-key entries used major scale: subject_midi/countersubject_midi hardcoded self.subject.mode, ignoring target key mode. Result: A minor entries (bars 5-6) had C# and G# where C♮ and G♮ belonged.

**Solution:** Fixed answer_generator.py to use answer_degrees = subject_degrees for real answers (transposition happens entirely in degrees_to_midi via dominant_midi parameter). Added optional mode parameter to subject_midi() and countersubject_midi() in fugue_loader.py. Threaded target_key.mode through call chain in imitation.py and cs_writer.py (cs_writer.py line 115 was the actual code path being used for invention CS rendering, not imitation.py as initially assumed).

**Results:** Bob checkpoint (seed 42): Answer bars 2-4 bass = D3-B2-G2 (correct G major 5-3-1), strong-beat consonance 100% (4ths, 6ths, octaves). A minor bars 5-6 bass CS = G2-D3-C3-B2-A2-G2-A2 (all natural, no sharps). All 8 genres pass test suite without assertion errors.

**Files modified:** answer_generator.py, call_response.fugue, fugue_loader.py, imitation.py, cs_writer.py.

**Open issues:** Tonal answer mutation logic untested (no tonal-answer subject in library). Harmonic minor not addressed (natural minor used throughout, even in cadential contexts where raised 7th would be idiomatic per L007).

## F2 -- Episode Integration via Fragen (2026-02-16)

**Problem:** Episode bars were rendered as two independent monologues (soprano
gets head, bass gets tail, no cross-voice checking). No rhythmic contrast,
frequent strong-beat dissonances.

**Solution:** Added EPISODE branch in `_write_thematic` (builder/phrase_writer.py)
that intercepts when both voices have ThematicRole.EPISODE. Builds fragen
fragment catalogue lazily, selects fragment matching planner's leader voice,
calls `realise_to_notes` to produce paired two-voice episode texture with
consonance guaranteed by fragen's filter. Falls through to per-voice rendering
if `realise_to_notes` returns None (logged as warning, never triggered in
10 seeds).

Also fixed pre-existing fragility in cadence_writer.py where octave-shift
search for thematic cadence cell required both range-fit AND distance<=6 from
prior pitch simultaneously, causing assertion failure when episode exit
pitches moved the target window.

**Results:** All 10 seeds (1-10) produce output without errors. 0 fragen
fallbacks. Episodes show clear rhythmic contrast (slow soprano thirds over
fast bass sixteenths). Strong-beat consonance maintained (sixths, fifths).

**Open issues (not F2 scope):**
- Fragment variety: all 3 episodes use same fragment (used_fragen_indices
  resets per phrase). Needs cross-phrase state persistence.
- Leader voice diversity: catalogue has no soprano-led fragments for
  call_response subject. All episodes bass-led despite planner alternation.
- Bass leaps ~10st at episode entries (fragen proximity is tie-break only).
- Beat-1 gap in bar 2 of each episode (Fragment.offset = 1/4).
- Cross-relation at episode boundaries (bar 14 A/Bb).

## F1 -- Fragen Consonance Hardening + Pipeline Adapter (2026-02-16)

**Problem:** Fragen's consonance checking only inspected half-bar positions,
missing parallel 5ths/8ves, cross-relations, and unprepared weak-beat dissonance.
No pipeline adapter existed to convert fragen output to builder.types.Note.

**Solution:** All changes in `motifs/fragen.py`:

1. **`_consonance_score`** replaces `_strong_beat_check`: checks at crotchet grid
   (bar_length/4), distinguishes strong/weak beats via STRONG_BEAT_OFFSETS, detects
   parallel perfect intervals on consecutive strong beats, cross-relations within
   and across check points, and tolerates weak-beat dissonance only when step-
   approached and step-left. Hard rejection (0.0) for any fault.

2. **`validate_realisation`** upgraded with same logic: crotchet grid, parallel
   perfect detection, cross-relation detection, passing-tone tolerance.

3. **Chain boundary scoring:** `_chain_boundary_penalty` counts cell joins with
   leap > 3 steps. `build_chains` sorts by ascending penalty, keeps top 200.

4. **`realise_to_notes`** pipeline adapter: converts fragen Notes to
   builder.types.Note with MIDI pitch, absolute offset, track assignment.
   `realise()` and `_find_start()` accept optional `prefer_upper/lower_pitch`
   for smooth voice-leading connection.

**Results:** 130 cells, 54 chains, 70 deduped fragments (28 regular + 42 hold),
57 written sections (13 caught by validation). Zero parallel perfects, zero
cross-relations. All 8 genres pass test suite.

## CP3 -- Musical hold-exchange (2026-02-16)

**Problem:** Hold-exchange bars had random oscillation ("sewing machine") — running
voice bounced between 2–3 adjacent pitches with no motivic identity, no descending
sequence, no subject material. Held pitch was identical in both bars (no harmonic
motion across the exchange).

**Solution:** Modified `builder/hold_writer.py`:
- Added `_find_consonant_near()` helper for consonance-filtered pitch search.
- Extended `_generate_running_voice_bar()` with `cell_degrees`, `cell_iteration`,
  `material_key`, `subject_mode` parameters. When cell data present, builds
  structural knots from diatonic transposition of the subject's sixteenth cell,
  one knot per cell repetition, using a unified octave shift from the first cell
  degree to preserve intervallic descent. Each knot is consonance-checked.
- Improved held-pitch selection: bar 0 uses previous pitch (existing), exchange
  bar uses last running voice's arrival pitch, creating voice-leading continuity.
- Imported `degrees_to_midi` from `motifs.head_generator`.

**Result:** Bass bar shows clear descending spine F3→E3→D#3→C3 (subject cell
sequenced down). Soprano bar descends E5→E5→D5→C5 at knot positions. Held pitch
changes from C5 to G3 across exchange. All 8 genres pass, all checkpoint seeds pass.

**Known limitation:** Dispatcher sends hold-exchange as two separate 1-bar entries,
so cross-bar descent continuation (cell_iteration>0) does not activate. Each bar
independently sequences from cell degree 0. Soprano fill between knots is uniform
oscillation (Viterbi solver limitation, not modifiable per task scope).

## CP2 -- Context-aware countersubject (2026-02-16)

**Problem:** CS was pre-composed in isolation (CP-SAT in abstract degree space) and
stamped in verbatim regardless of companion voice. Result: strong-beat 9ths,
unprepared tritones, two monologues instead of dialogue.

**Solution:** New module `builder/cs_writer.py` with `generate_cs_viterbi()` that
generates CS pitches via the Viterbi solver against the already-rendered companion
voice. The CS rhythm (from the CP-SAT generator) is preserved as the Viterbi grid;
the CS contour provides structural knots on strong beats (dropped if dissonant
against the companion). Boundary knots use consonance-adjusted pitches to satisfy
solver constraints.

**Files changed:**
- `builder/cs_writer.py` (new): Viterbi-based CS generation
- `builder/phrase_writer.py`: CS+companion detection in `_write_thematic` — renders
  companion first, then generates CS via Viterbi. Fallback to stamp-in if companion
  has no notes.
- `data/genres/invention.yaml`: Fixed hold_exchange bars: 1 -> 2 (pre-existing
  validation failure)

**Results:**
- 15/16 strong-beat CS intervals consonant (93.75%, threshold 80%)
- Contrary motion confirmed in bars 5-6 and 15-16 (subject ascends, CS descends)
- All 10 seeds (1-10) produce output without assertion errors
- All 8 genres pass test suite

**Open complaints:**
- Bar 4 beat 1: unprepared m7 (C5/D3) — Viterbi solver's cost function doesn't
  penalize strong-beat dissonance heavily enough when no knot is placed (Known
  Limitation 1). Fix: increase consonance cost weight on strong beats in
  viterbi/costs.py (future refinement, not CP2 scope).
- Hold-exchange (bars 11-12) still mechanical oscillation (CP3 scope)
- Pedal (bars 21-22) still static repetition (CP3 scope)
- Episode dissonances at bars 19-20 (not CS, out of scope)

## CP1 -- Fix thematic plumbing (2026-02-16)

Three bugs fixed in `planner/imitative/subject_planner.py` and `builder/free_fill.py`:

1. **Phantom bass in solo entries.** Changed `texture="plain"` to `texture="silent"` for
   `slot=="none"` voice assignments. Added silent-voice guard in `free_fill.py` to mark
   silent bars as occupied, preventing Viterbi companion generation.

2. **Missing episodes at section boundaries.** Relaxed `prev_is_special`/`curr_is_special`
   guard to only block cadences (not pedal/stretto/hold_exchange). Extended
   `_extract_lead_voice_and_key` to extract keys from hold_exchange, stretto, and pedal
   entries so episodes can bridge from these to the next subject entry.

3. **Episode bar duplication.** Changed episode iteration from `bar_offset` to
   `bar_offset + 1`, so the first episode bar starts at iteration +/-1 (already transposed)
   instead of iteration 0 (verbatim copy of preceding bar).

Verified: bar 1 bass silent, 3 episodes auto-inserted, no verbatim episode duplication,
seeds 1-10 clean, full 8-genre test suite passes.
