# TODO

Conductor reads at chat start.

---

## Now: EPI-6 — Paired-kernel episode variety

EPI-5b done. Listening review: all 5 episodes use the same fragment = boring.
Design in `workflow/epi6-design.md`. Three phases:
- EPI-6a: Paired kernel extraction (rewrite extract_kernels.py)
- EPI-6b: Chain solver (adapt _solve DFS from episode_kernel.py)
- EPI-6c: Wire into EpisodeDialogue.generate()

---

## Roadmap: Invention → Fugue + SATB

### Phase A — Complete 2-voice quality

Everything here strengthens the musical language before adding voices.
Order matters: cadences and harmony feed into everything downstream.

1. **CLR — Cadence reform** _(done)_
   - ~~CLR-1: Dynamic cadence type from YAML~~ _(done)_
   - ~~CLR-2: Internal section cadences~~ _(done)_
   - ~~CLR-3: New templates (grand cadence, cadenza doppia)~~ _(done)_
   - ~~CLR-4: Cadence breath rests~~ _(already implemented in cadence_writer.py)_

2. **HRL — Harmonic language** _(done)_
   - ~~HRL-3: Stock harmonic grid for thematic fills~~ _(done)_
   - ~~HRL-4: Cadential acceleration (ii→V in final bar)~~ _(done)_
   - ~~Chord inversions (6/3 passing)~~ _(done — HRL-5)_
   - ~~Secondary dominants (V/V, V/vi)~~ _(done — HRL-6)_
   - ~~Note writer enrichment (figured bass numerals)~~ _(done — HRL-7)_

3. **SUB — Subject generator reform**
   - ~~Tonal answers (currently real only)~~ _(done)_
   - Rhythmic drama (more varied cell sequences)
   - Algorithmic answer_offset_beats

4. **MEL — Melodic quality**
   - Melodic inversion (mirror subjects)
   - Viterbi cost: motivic coherence, suspension prep discount, period-3 suppression
   - Figuration strong-beat consonance / metric alignment
   - Mixed-rhythm semiquaver templates
   - Mechanical figuration (invention bars 11–16, fantasia 1–13)

5. **EPI-5 — Episode redesign** _(supersedes EPI-2, EPI-4)_
   - ~~EPI-2a: Cell vocabulary expansion~~ _(done, superseded)_
   - ~~EPI-2b: Fragen fallback retry~~ _(done, superseded)_
   - ~~EPI-4a: Kernel episode demo~~ _(done, architecture rejected)_
   - ~~EPI-5: Imitative dialogue episodes~~ _(done)_
   - ~~EPI-5b: Parallel fix (oblique tail, per-iteration shift, entry
     anchor) + Viterbi HC7 strong-beat parallel check~~ _(done)_

6. **ORN — Compositional ornaments**
   Mordents, trills, turns, appoggiaturas placed by structural context
   (downbeat emphasis, cadential trill, neighbour-tone decoration).
   Not performance ornaments — ink-on-paper decisions (cf. Bach's
   Explication table). Wire after counterpoint and episode texture
   are structurally sound.

### Phase B — Inner voices (alto + tenor)

Prerequisite for fugue. The 2-voice system must be musically solid
before adding voices — every fault in 2 voices becomes four faults
in 4 voices.

1. **IV-1: Voice infrastructure**
   - Alto and tenor voice generation (Viterbi against existing outer voices)
   - Range management for 4 voices (crossing rules, spacing)
   - Chord completion (fill implied harmony from bass + soprano)

2. **IV-2: 4-voice counterpoint**
   - Parallel/hidden 5th/8ve checking across all voice pairs
   - Voice-leading rules generalised from 2 to N voices
   - Restore validate_voice melodic interval assert

3. **ICP-3: CS permutation**
   Simultaneous CS permutation in 3+ voices. Parked until inner
   voices exist.

### Phase C — Fugue form

Full 4-voice fugue with SATB exposition, episodes, stretto.

1. **FUG-1: 4-voice exposition**
   - SATB entry order (S→A→T→B or variants)
   - Counter-exposition
   - Redundant entry handling

2. **FUG-2: 4-voice episodes**
   - Sequential episodes across 4 voices
   - Paired voices in parallel 3rds/6ths

3. **FUG-3: 4-voice stretto**
   - Stretto across all voice pairs
   - Augmentation / diminution

4. **FUG-4: Fugal rhetoric**
   - Barré (long pedal with activity above)
   - False entries
   - Tonal answer in 4-voice context

---

## Known Limitations (from briefs)

Accumulated unresolved limitations. Cross-referenced to roadmap where applicable.
Updated after each phase completes.

### From HRL-3 (stock harmonic grid)
- Stock progressions are generic (I→IV→V / i→iv→V) regardless of subject contour → future: harmonic analysis of fugal subjects
- No section sensitivity — same stock progression in exposition, development, peroration → future: section-aware harmony
- ~~No cadential acceleration~~ _(addressed by HRL-4)_
- ~~No chord inversions — root position only~~ _(addressed by HRL-5)_
- Cross-relation penalty in Viterbi too low — iv (B♭) in bass against A♮ in soprano at bars 18–19 → future: raise cross-relation cost weight in viterbi evaluator
- Stretto bars have no harmonic grid (by design) — unprepared dissonances at bars 15, 23, 26 remain → future: harmonic-aware stretto rendering

### From HRL-5 (passing 6/3 chords)
- Only one passing chord per bar transition; 4th-apart roots still leave a 3rd gap → future: double passing chords
- No passing 6/4 chords → future: HRL second-inversion passing chords
- No chromaticism in passing chords → roadmap: HRL-6 secondary dominants
- Same passing chords in all sections → future: section-aware harmony
- Soprano sees full chord tones, not inversion-aware voicing → future: soprano inversion awareness

### From HRL-6 (secondary dominants)
- V/V and V/vi code paths not exercised in invention layout — all free fills are 1–2 bars, below the 3-bar threshold for V/V and 5-bar threshold for V/vi → will first be audible in genres with longer free-fill episodes, or after EPI-1 lengthens episodes
- No secondary dominants beyond V/V and V/vi → future: V/ii, V/IV etc.

### From EPI-2a (cell vocabulary expansion)
- Dedup by rhythm class is very coarse (4 bins) — cross-source and diminished fragments collapse against existing same-source fragments, limiting perceptual variety → future: finer-grained dedup or position-aware selection (EPI-2c)
- No position-aware selection — provider deploys material by novelty, not episode position → roadmap: EPI-2c
- Diminished cells that chain into bars may dedup against original-speed chains with same rhythm profile → future: dedup refinement

### From EPI-5 (imitative dialogue episodes)
- Cross-relations in flat-key episodes (bars 11, 14, 28, 29) — Bb adjacent to B-natural from surrounding material → key-planning interaction, not episode_dialogue bug; requires key-transition awareness in planner
- No harmonic grid in episodes — vertical intervals controlled by imitation offset (10th) and oblique motion, not harmonic function → future: harmonic-aware episode generation
- Fixed imitation offset (diatonic 10th) — a musician might vary offset for timbral variety → future: variable imitation intervals
- Half-fragment iterations produce simultaneous sustain in both voices (beats 3–4) — static but not parallel; intended compression effect → acceptable

### From EPI-5b (episode parallel fix + HC7)
- Bar 12.1 descending tritone (A#4→E4) at iteration boundary in F-major episodes — structural: Bb–E tritone native to F major under octave shift. Net-neutral to fix (trades for m7 entry leap). Requires registral-aware start_degree selection → future: detect octave-shift tritone and prefer diatonic octave offset
- Bars 25.1–25.3 parallel octaves in CS answer (bars 24–25) — HC3 active but no better Viterbi path exists; CS degrees structurally constrained → requires CS degree relaxation or chromatic passing tone → planner scope
- HC7 correct but did not eliminate any faults in this piece — the residual parallels are adjacent-step (HC3 scope), not strong-beat-separated. HC7 may help in other key/register combinations

### From EPI-1 (inter-entry episodes)
- Fragen fallback at bars 28–30: `realise_to_notes` returned None in E minor, producing static half-notes instead of sequential fragments → future: widen fragen start search or add fallback sequential generator
- Episode variety limited: all episodes draw from same subject head/tail cells, sounding repetitive despite FragenProvider diversity tracking → future: EPI-2 episode variety (melodic inversion, free sequential material, rhythmic diminution)
- No 4-bar episodes exercised: no key pair in current invention journey exceeds 5 semitones → will appear in genres with wider key journeys
- Duplicate peroration strettos (bars 32–37): pre-existing, not introduced by EPI-1 → future: stretto variety in peroration

### From earlier phases (recovered)
- Surface inference assumes soprano/bass pitch = chord root (wrong on 3rds/5ths) → partially addressed by HRL-3 for free_fill; schematic path already has schema harmony
- CS writer has no harmonic grid — CS Viterbi operates without chord awareness → future: wire harmonic grid into cs_writer
- Thematic renderer episodes (fragen) have no harmonic constraint → future: harmonic-aware episode generation
- Pedal harmony is hardcoded for 2-bar 4/4 only; other bar spans/metres fall back to single-knot behaviour → future: generalise pedal harmony
- Stretto entries share delay values, limiting rhetorical variety in peroration → future: stretto delay diversification
- Mechanical figuration in invention bars 11–16, fantasia 1–13 → roadmap: MEL
- (USI-3) 3 ugly_leap faults remain at stretto entries (bars 23/28 beat 1) and peroratio (bar 29 beat 1) — root causes outside sequence_cell_knots → future: stretto voice-leading or entry pitch selection
- (BM-2) Subject generator: cell patterns DACTYL×4, TIRATA×4 produce 0 results due to structural constraint interaction → future: relax constraints or add intermediate cells
- (CLR-3) Cadence templates are 4/4 only; 3/4 thematic cadences use galant path → housekeeping: "Thematic cadence bass (3/4)"
- (ICP-1) Inversion distances limited to 7, 9, 11 — no free-choice distance → minor; sufficient for standard baroque practice

---

## Housekeeping (do anytime, no dependencies)

- ~~M001–M005 violations~~ _(done — all 34 items resolved)_
- VG4: rewrite phrase_writer (unified generate_voice dispatch)
- VG5: style as weights from YAML
- Figurenlehre labelling
- Exordium answer gap (prinner is cadential)
- Thematic cadence bass (3/4)

---

## Completed

### EPI-5b — Episode parallel fix + HC7 (2026-02-28)

53 → 10 faults. Oblique tail (3-semiQ head, follower sustains), ascending-aware
start_degree, entry anchor range check, cross-phrase prior fallback, HC7
strong-beat parallel constraint. Remaining 10 are pre-existing or structural.

### EPI-5 — Imitative dialogue episodes (2026-02-28)

Replaced episode kernel system with imitative dialogue. Both voices trade
a subject-derived fragment in close imitation (1-beat offset, lower 10th),
sequencing stepwise, with progressive fragmentation and voice exchange.
Deleted episode_kernel.py + demo. 49 faults remain (parallels, register,
entry leaps) → EPI-5b.

### M001–M005 violations + CLR-1 (2026-02-26)

M002 oversized signatures (transition_cost 20→5, 12 functions), M001 param bundles
(AnchorGenerationContext, etc.), M003 object passing (6 sites), M005 extraction
promotion (catalogue Fragment dispatch, single-pass annotation maps, Schema.bar_count,
Anchor.sort_key(), KeyConfig.mode property, test pipeline consolidation).
CLR-1: dynamic cadence type read from genre YAML.

### ICP-2: Second countersubject (2026-02-26)

ICP-2a data layer, ICP-2b scheduling + rendering, ICP-2c labels.
CS2 at inversion distance 9 alternates with CS1 through development.

### PED-2, USI-3, USI-2, CAD-1, FIX-1, USI-1, PSF-1, ICP-1 (2026-02-26)

Pedal contour knots, cell knot leap guard, companion seed pitch,
cadenza composta bass, hold-exchange grouping, structural knot tritones,
companion knot enrichment, peroration stretto fix, true double invertible
counterpoint. Invention passes listening gate.

### STV-1 — Stretto variety and form extension (2026-02-26)

### BM — Baroque melody generation (2026-02-26)

### EXP-1: Exposition overlap voice-leading (2026-02-26)

### Earlier work

PED-1, DUP-1, BUG-1, DBG-1, code review refactor, F3/F4 texture,
CP1-CP4/F1-F2 pitch bugs, B1-B8 infrastructure, IMP-1 through IMP-7,
HRL-1/2, TD-1-3, TD-1t, INV-1/2/3, VG1/2/3, BV1, V9, Phases 10-12.
