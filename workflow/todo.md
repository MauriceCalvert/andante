# TODO

Items tracked here, ticked off when done. Conductor reads at chat start.

## Open architectural questions

- [ ] Voice generation endgame: should Viterbi generate bass too (making WalkingFill/PillarFill/PatternedFill unnecessary), or does bass stay span-by-span because its textures are too idiom-specific for a cost function? Answer after V9 cost function tuning. If Viterbi can produce idiomatic bass, the endgame is Viterbi for all voices with shared validate/audit. If not, it's a mixed architecture: Viterbi soprano, voice_writer strategies for bass. The bass_writer refactoring (Phase 17 in voice_writer_plan.md) should wait until this is resolved.

## Deferred work

- [ ] Cadence breath rests: cadence templates fill the bar completely (e.g. cadenza_semplice 4/4 = two minims). The arrival note should be shorter (crotchet) with a rest filling the remainder, so phrases have audible silence between them. Requires either rest support in cadence templates or a trim mechanism in compose.py. Noticed by ear on invention bars 4 and 16.

- [ ] Harmonic rhythm layer: per-beat chord grid between schema degree landmarks, sitting between L4 planning and surface generation. Solver cost function then penalises non-chord-tones on strong beats, permits them as passing tones on weak beats. Build after V1–V6 complete so the gap is audible and drives design. Bach comparison (bach_compare.py) shows ~22% exact match / ~35% direction match — consistent with melodic interpolation without harmonic data.
- [x] Viterbi cost function V9: zigzag/leap rebalancing, contour shaping, dissonance classification, anti-oscillation (V9a-V9d complete)
- [ ] Viterbi cost function future: motivic coherence (echo leader material), suspension preparation discount, period-3 oscillation suppression
- [ ] Subject development (inversion, augmentation, stretto)
- [ ] Episode derivation from subject fragments
- [ ] CS in later invention entries
- [ ] Inner voices
- [ ] Figurenlehre labelling for training data
- [ ] bass_writer refactor (three texture branches → three functions)
- [ ] Figuration strong-beat consonance: coordinate generated degrees with accent patterns
- [ ] Figuration metric alignment: chord roots on strong beats when arpeggiating large intervals
- [ ] Whole-note held structural tones (gavotte bar 18) — single structural tone spanning full bar
- [ ] Add mixed-rhythm semiquaver templates (dotted 16th + 32nd, Lombard patterns) for note counts 10-16
- [ ] Restore validate_voice melodic interval assert (relaxed to warning in V6; V9 added graduated leap costs but octave+ intervals may still occur at phrase boundaries)

## Done

- [x] Semiquaver runs (Phase 12)
- [x] Figuration padding / sparse melodic material (Phase 12)
- [x] Low soprano register in gavottes (Phase 12)
- [x] Sarabande beat-2 weight (Phase 11c)
- [x] Parallel octave gavotte bar 19.1 (Phase 11b)
- [x] Invention exordium min_non_cadential (Phase 11a)
- [x] Cross-relation prevention in soprano (Phase 10)
