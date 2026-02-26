# TODO

Conductor reads at chat start.

---

## Now: BM — Baroque melody generation (harmonic-grid subject pitch engine)

Replaces head enumeration + CP-SAT tail generation + melodic validation
with harmonically-grounded pitch generation per `docs/baroque_melody.md`.

Four phases:
- **BM-1**: Harmonic grid data module (`harmonic_grid.py`) — progressions,
  chord tones, lookups.  Brief: `workflow/bm-1-brief.md`
- **BM-2**: Melody generator (`melody_generator.py`) — C/P grid, skeleton
  enumeration, P-slot fill, validation.  Brief: `workflow/bm-2-brief.md`
- **BM-3a**: Wire into pipeline — rewrite pitch_generator.py, update
  duration_generator.py return type, update selector.py loop.
  Brief: `workflow/bm-3a-brief.md`
- **BM-3b**: Scoring extension + dead code removal — harmonic variety
  score, delete head_enumerator/cpsat_generator/cpsat_prototype.
  Brief: `workflow/bm-3b-brief.md`

---

## Parked

### Must-do (after TB sequence)

- Invertible counterpoint enforcement: CS is optimised per-entry by Viterbi, not composed once to work both above and below the subject. True double counterpoint requires a single CS that is consonant in both orientations, then placed by register at render time.
- Hold-exchange cross-bar descent: dispatcher sends hold-exchange as two separate 1-bar entries, so cell_iteration>0 never activates. Each bar sequences independently.
- Final cadence bass formula: cadenza_composta bass is three repeated dominants then bare tonic. No cadential formula (IV–V–I, ii6–V–I).
- Cadence length reform (remaining): semplice, half, comma in 4/4; all in 3/4; hemiola; grand cadence
- Structural knot consonance: tritones between voice knots from degree + octave selection

### Later

- M001–M005 violations: fix all items in `mviolations.md` (34 violations; worst: viterbi/costs.py transition_cost at 20 params)
- Algorithmic answer_offset_beats
- Subject generator reform (rhythmic drama), must generate tonal rather than real answers.
- VG4: rewrite phrase_writer (unified generate_voice dispatch)
- VG5: style as weights from YAML
- Cadence breath rests (non-final)
- HRL Phases 2–6 (harmonic interpolation, cadential acceleration, inversions, secondary dominants, note writer)
- Viterbi cost: motivic coherence, suspension prep discount, period-3 suppression
- Exordium answer gap (prinner is cadential)
- Bass stasis in chorale bars 1–3
- Sarabande spacing bar 5
- Mechanical figuration (invention 11–16, fantasia 1–13)
- Whole-note held structural tones (gavotte bar 18)
- Mixed-rhythm semiquaver templates
- Restore validate_voice melodic interval assert
- Inner voices
- Multiple countersubjects: generate 2nd (3rd, 4th) CS against subject + all prior CSs in invertible counterpoint. Coordination in generate_subjects.py; countersubject_generator needs mutual-consonance constraint.
- Figurenlehre labelling
- Figuration strong-beat consonance / metric alignment
- Thematic cadence 3/4
- Thematic cadence bass
- Compositional ornaments: mordents, trills, turns, appoggiaturas placed
  by structural context (downbeat emphasis, cadential trill, neighbour-tone
  decoration). Not performance ornaments — these are ink-on-paper
  compositional decisions (cf. Bach's Explication table). The vocabulary
  exists in figurations.yaml / diminutions.yaml but is currently dead
  code. Wire after counterpoint and episode texture are structurally sound.

---

## Completed

### Pedal + cleanup (2026-02-24)

PED-1, DUP-1, BUG-1, DBG-1, code review refactor. See completed.md.

### Texture failures (2026-02-24)

F3 (Fragen class), F4 (canonic episode texture).

### Pitch bugs (2026-02-23/24)

CP1–CP4, F1–F2. Subject generator reforms: SUBPOOL, SUBDUR, SUBSCORE.

### Bach Invention Targets (2026-02-15/16)

B1–B8 infrastructure. Musical quality gated by CP sequence.

### IMP — Imitative Composition Path (2026-02-15)

IMP-1 through IMP-7. Listening gate passed.

### Earlier work

HRL-1/2, TD-1–3, TD-1t, INV-1/2/3, VG1/2/3, BV1, V9, Phases 10–12.
