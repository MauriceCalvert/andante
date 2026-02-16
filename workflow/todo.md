# TODO

Conductor reads at chat start.

---

## Bach Invention Targets (from BWV 772 analysis)

See `viterbi/bachsamples/bwv0772_analysis.md` for full analysis.
Priority order by audible impact.

- [x] **B1 — Texture rotation** — Hold-exchange (B2 impl) + density contrast (B1 impl). Done 2026-02-15. Remaining: run/slow episode texture, dense-both.
- [x] **B2 — Contrary-motion episodes** — Done 2026-02-15. Episode voices now move in opposite directions (convergent funnel). Remaining: downbeat dissonances in episode bars (unprepared 4ths/9ths from mechanical transposition).
- [x] **B3 — Rhythmic independence** — CS rhythm aggregated (10→8 notes for call_response). Done 2026-02-15.
- [x] **B4 — Thematically-derived free counterpoint** — Hold-exchange running voice uses subject cell. Done 2026-02-15. Superseded by B9 (Viterbi counterpoint). Remaining: other FREE bars still Viterbi.
- [ ] **B5 — Chromatic approach tones** — Secondary leading tones (raised 7th of each new key area) before cadential arrivals. Constrained by L007. Needs L007 relaxation or secondary-dominant infrastructure.
- [x] **B6 — Variable note density** — Largely addressed by B1/B2 (density contrast + hold-exchange). Done 2026-02-15.
- [ ] **B7 — Cadence grows from material** — Bach weaves subject fragments into the cadential descent. Our cadence is a formulaic template with no thematic connection.
- [x] **B8 — Mid-bar answer entry** — Bach's answer enters at beat 3 of bar 2, during the subject. Our entries are aligned to bar boundaries. ✓ Done 2026-02-15.

## Must-do

- [ ] **Cadence length reform (remaining)** — cadenza_composta 4/4 done (IMP-6). Still needed: cadenza_semplice, half_cadence, comma in 4/4; all types in 3/4 (except cadenza_composta 3/4 already 2 bars). Hemiola variant for sarabande/courante. Grand cadence (4+ bars) for invention peroratio and fantasia.
- [ ] **Structural knot consonance** — schema degree + octave selection produces tritones between voice knots. Affects gavotte (6), minuet (5), chorale (3), sarabande (3), trio_sonata (3), invention (3), fantasia (2). Upstream of solver.

## Later

- [ ] **Algorithmic answer_offset_beats** — currently a fixed YAML value per genre. Should analyse the subject's rhythm at the candidate overlap beat and choose the entry point where the subject is rhythmically calm (held note, slow figure). Avoids muddy overlap when subject has busy material at beat 3.
- [ ] **Subject generator reform** — current generator produces rhythmically flat subjects (uniform eighths/quarters). Needs rhythmic and pitch drama: long notes, sixteenth bursts, dotted rhythms.
- [ ] **Viterbi fallback warning improvement** — report which constraints fired, against which voice/pitch, and upstream cause.
- [ ] **VG4 — Rewrite phrase_writer** — call `generate_voice()` in genre-determined composition order. Delete bass_writer.py, soprano_writer.py, bass_viterbi.py.
- [ ] **VG5 — Style as weights from YAML** — cost weights externalised, weight envelopes from phrase position / affect / genre.
- [ ] Cadence breath rests (non-final): arrival note shorter with rest, so phrases have audible silence between them.
- [ ] HRL Phase 2: Harmonic interpolation — densify_grid for gaps exceeding one bar.
- [ ] HRL Phase 3: Cadential acceleration — one chord per beat in cadential approach.
- [ ] HRL Phase 4: Bass inversion preference — derive inversion from bass degree vs chord root.
- [ ] HRL Phase 5: Secondary dominants — V/x for sequential schemas with local tonicisations.
- [ ] HRL Phase 6: Note writer integration — chord + chord_role columns in .note file.
- [ ] Viterbi cost function: motivic coherence, suspension preparation discount, period-3 oscillation suppression.
- [ ] Exordium answer gap — prinner is cadential, so exordium has only one non-cadential phrase.
- [ ] Bass stasis in chorale bars 1–3.
- [ ] Sarabande spacing bar 5: gap of 40 semitones.
- [ ] Mechanical figuration: invention bars 11–16, fantasia bars 1–13 — relentless sixteenths.
- [ ] Whole-note held structural tones (gavotte bar 18).
- [ ] Mixed-rhythm semiquaver templates (dotted 16th + 32nd, Lombard patterns) for note counts 10–16.
- [ ] Restore validate_voice melodic interval assert.
- [ ] Inner voices.
- [ ] Figurenlehre labelling for training data.
- [ ] Figuration strong-beat consonance.
- [ ] Figuration metric alignment.

---

## Completed

### IMP — Imitative Composition Path (2026-02-15)

Separate pipeline for subject-driven genres. Design: `workflow/imitative_design.md`.

- [x] IMP-1: Infrastructure (composition_model field, folder, branch)
- [x] IMP-2: Subject Planner (entry_sequence → SubjectPlan)
- [x] IMP-3: Entry Layout (SubjectPlan → PhrasePlans)
- [x] IMP-4: Episode Auto-Insertion (section boundary detection, key-distance, exposition exemption)
- [x] IMP-5a.1: Pedal + Double Episodes
- [x] IMP-5a.2: Stretto
- [x] IMP-5b: Texture & Pairing — deferred (pairing useless without FREE companions)
- [x] IMP-6: Cadence Reform (2-bar cadenza_composta 4/4)
- [x] IMP-7: Listening Gate. Maurice accepted.

### Earlier work

- [x] HRL-1/2 — Harmonic Grid Infrastructure + Integration
- [x] TD-1 through TD-3 — Thematic Planning Layer (superseded by IMP)
- [x] TD-1t — Thematic Trace Instrumentation
- [x] INV-1/2/3 — Countersubject, Episodes, Stretto (superseded by IMP)
- [x] VG1/2/3 — Viterbi voice generation, soft costs, hard constraints
- [x] BV1 — Bass Viterbi
- [x] V9 — Viterbi cost function rebalancing
- [x] Phases 10–12 — Cross-relation prevention, sarabande weight, figuration fixes
