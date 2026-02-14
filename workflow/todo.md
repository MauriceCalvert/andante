# TODO

Items tracked here, ticked off when done. Conductor reads at chat start.

## Blocking

- [x] **Listening gate** — Maurice listened, accepted (2026-02-13). Proceed to structural knot consonance.

## In progress

- [x] **HRL-1 — Harmonic Grid Infrastructure** — harmony.py, Schema.harmony field, parse_roman, HarmonicGrid. Done.
- [x] **HRL-2 — Harmonic Grid Integration** — grid wired into phrase_writer, H3 bypassed in soprano_writer, chord_pcs wired to bass_viterbi. Done.

## Next — Invention Imitative Architecture (INV)

Three-phase plan to fill invention compositional gaps. Each phase
is self-contained with a listening gate. Briefs in `workflow/inv[1-3]_brief.md`.

- [x] **INV-1 — Countersubject in all subject entries** — CS wired into
  every non-monophonic subject entry. Done 2026-02-14.
- [x] **INV-2 — Episodes from subject fragments** — head fragment
  placed in lead voice during sequential schemas. Done 2026-02-14.
- [x] **INV-3 — Stretto** — both voices state subject with 1-beat
  delay in peroratio. Done 2026-02-14. Peroratio YAML expanded
  (fenaroli prepended) to give stretto enough bars.

## Later

- [ ] **Subject generator reform** — current generator produces rhythmically flat subjects (uniform eighths/quarters). Subjects need both rhythmic and pitch drama: long notes that build anticipation, bursts of sixteenths that release it, dotted rhythms for character. Curated subjects in output/subjects/ demonstrate the target quality. Generator should produce subjects with comparable rhythmic contrast and melodic arc.
- [ ] **Structural knot consonance** — schema degree + octave selection produces tritones between voice knots at the same offset. Affects gavotte (6), minuet (5), chorale (3), sarabande (3), trio_sonata (3), invention (3), fantasia (2). Upstream of solver; HC4 blocks fill tritones but cannot override pinned knots.
- [ ] **VG4 — Rewrite phrase_writer** — call `generate_voice()` in genre-determined composition order. Delete bass_writer.py, soprano_writer.py, bass_viterbi.py.
- [ ] **VG5 — Style as weights from YAML** — cost weights externalised, weight envelopes from phrase position / affect / genre.

## Deferred work

- [ ] Exordium answer gap — prinner is cadential, so exordium has only one non-cadential phrase (do_re_mi = subject). Answer+CS never fires. Fix: add non-cadential schema to invention.yaml exordium sequence.
- [ ] Cadence breath rests (non-final): arrival note should be shorter with a rest filling the remainder, so phrases have audible silence between them. Final cadence breath fixed (VG3.1 session); intermediate cadences still hold to bar end.
- [ ] HRL Phase 2: Harmonic interpolation — densify_grid inserts conventional approach chords when gap between schema positions exceeds one bar.
- [ ] HRL Phase 3: Cadential acceleration — one chord per beat in cadential approach zones.
- [ ] HRL Phase 4: Bass inversion preference — derive inversion from bass degree vs chord root, apply as cost bonus.
- [ ] HRL Phase 5: Secondary dominants — V/x for sequential schemas with local tonicisations.
- [ ] HRL Phase 6: Note writer integration — chord + chord_role columns in .note file.
- [ ] Viterbi cost function future: motivic coherence (echo leader material), suspension preparation discount, period-3 oscillation suppression
- [ ] Subject development (inversion, augmentation, stretto)
- [ ] Episode derivation from subject fragments
- [ ] CS in later invention entries
- [ ] Inner voices
- [ ] Figurenlehre labelling for training data
- [ ] Figuration strong-beat consonance: coordinate generated degrees with accent patterns
- [ ] Figuration metric alignment: chord roots on strong beats when arpeggiating large intervals
- [ ] Whole-note held structural tones (gavotte bar 18) — single structural tone spanning full bar
- [ ] Add mixed-rhythm semiquaver templates (dotted 16th + 32nd, Lombard patterns) for note counts 10-16
- [ ] Restore validate_voice melodic interval assert (relaxed to warning in V6; V9 added graduated leap costs but octave+ intervals may still occur at phrase boundaries)
- [ ] Bass stasis in chorale bars 1–3: 4× D3 quarter notes from rhythm cells expanding a single structural pitch. HC1 fires in Viterbi fill but stasis comes from upstream.
- [ ] Sarabande spacing bar 5: gap of 40 semitones (G2 vs B5). HC2 blocks in fill but positions are structural knots.
- [ ] Mechanical figuration: invention bars 11–16, fantasia bars 1–13 — relentless sixteenths, no rhythmic relief. Rhythm cell / phrase arc problem.

## Done

- [x] VG3.1 — Hard counterpoint constraints in Viterbi solver (HC1–HC6), zero fallbacks all genres
- [x] VG3 — Unified `generate_voice()` in `viterbi/generate.py`
- [x] VG2.1 — COST_UNPREPARED_STRONG_DISS raised to 120.0
- [x] VG2 — Hard filters removed, soft costs only
- [x] VG1 — N-voice pairwise solver (LeaderNote → ExistingVoice)
- [x] BV1 — Bass Viterbi for walking texture
- [x] Tritone surcharge (COST_TRITONE = 80.0) on weak/moderate beats
- [x] measure_consonance.py fixed: tritones always classified as unprepared
- [x] Final cadence breath fix (hold to bar end, no rest)
- [x] COST_STEP_UNISON raised to 15.0
- [x] Viterbi cost function V9: zigzag/leap rebalancing, contour shaping, dissonance classification, anti-oscillation (V9a–V9d)
- [x] Semiquaver runs (Phase 12)
- [x] Figuration padding / sparse melodic material (Phase 12)
- [x] Low soprano register in gavottes (Phase 12)
- [x] Sarabande beat-2 weight (Phase 11c)
- [x] Parallel octave gavotte bar 19.1 (Phase 11b)
- [x] Invention exordium min_non_cadential (Phase 11a)
- [x] Cross-relation prevention in soprano (Phase 10)
