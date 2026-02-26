# TODO

Conductor reads at chat start.

---

## Now: CLR-2

Internal section cadences (half cadences at section boundaries).

---

## Roadmap: Invention → Fugue + SATB

### Phase A — Complete 2-voice quality

Everything here strengthens the musical language before adding voices.
Order matters: cadences and harmony feed into everything downstream.

1. **CLR — Cadence reform**
   - ~~CLR-1: Dynamic cadence type from YAML~~ _(done)_
   - CLR-2: Internal section cadences (half cadences at section boundaries)
   - CLR-3: New templates (grand cadence, cadenza doppia) — 4/4 only, 3/4 covered by galant
   - CLR-4: Cadence breath rests (non-final phrases)

2. **HRL — Harmonic language** (Phases 2–6)
   - Harmonic interpolation (fill between structural chords)
   - Cadential acceleration (harmonic rhythm speeds near cadence)
   - Chord inversions (6/3, 6/4 passing)
   - Secondary dominants (V/V, V/vi)
   - Note writer enrichment (figured bass numerals)

3. **SUB — Subject generator reform**
   - Tonal answers (currently real only)
   - Rhythmic drama (more varied cell sequences)
   - Algorithmic answer_offset_beats

4. **MEL — Melodic quality**
   - Melodic inversion (mirror subjects)
   - Viterbi cost: motivic coherence, suspension prep discount, period-3 suppression
   - Figuration strong-beat consonance / metric alignment
   - Mixed-rhythm semiquaver templates
   - Mechanical figuration (invention bars 11–16, fantasia 1–13)

5. **ORN — Compositional ornaments**
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

## Housekeeping (do anytime, no dependencies)

- ~~M001–M005 violations~~ _(done — all 34 items resolved)_
- VG4: rewrite phrase_writer (unified generate_voice dispatch)
- VG5: style as weights from YAML
- Figurenlehre labelling
- Exordium answer gap (prinner is cadential)
- Thematic cadence bass (3/4)

---

## Completed

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
