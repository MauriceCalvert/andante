# TODO

Items tracked here, ticked off when done. Conductor reads at chat start.

## Deferred work

- [ ] Viterbi cost function future: motivic coherence (echo leader material), suspension preparation discount, period-3 oscillation suppression
- [ ] Accented neighbour fix: dissonance_at_departure strong-beat branch rejects accented neighbours (step-step with direction reversal) by requiring same-direction motion. Should cost COST_ACCENTED_PASSING_TONE, not COST_UNPREPARED_STRONG_DISS. Only affects soprano-as-follower (bass corridors filter strong beats to consonances).
- [ ] Direct (hidden) perfects: motion_cost misses similar motion into a perfect interval when the upper voice leaps. Needs scale_degree_distance ≥ 2 check (not raw semitones) and must identify which voice is upper — current function doesn't know. Requires adding a voice-role parameter or convention.
- [ ] Subject development (inversion, augmentation, stretto)
- [ ] Episode derivation from subject fragments
- [ ] CS in later invention entries
- [ ] Inner voices
- [ ] Figurenlehre labelling for training data
- [ ] bass_writer cleanup: remove walking-texture branch (now dead code, replaced by bass_viterbi.py). Pillar/patterned branches remain.
- [ ] Bass Viterbi for pillar/patterned textures (BV2): arpeggiated_3_4, half_bar, continuo_sustained. Requires chord-tone incentive costs or pattern-as-knot constraints.
- [ ] Figuration strong-beat consonance: coordinate generated degrees with accent patterns
- [ ] Figuration metric alignment: chord roots on strong beats when arpeggiating large intervals
- [ ] Whole-note held structural tones (gavotte bar 18) — single structural tone spanning full bar
- [ ] Add mixed-rhythm semiquaver templates (dotted 16th + 32nd, Lombard patterns) for note counts 10-16
- [ ] Restore validate_voice melodic interval assert (relaxed to warning in V6; V9 added graduated leap costs but octave+ intervals may still occur at phrase boundaries)
- [ ] Viterbi bass: repeated-pitch penalty in cost function (walking bass occasionally holds pitch across beats)
- [ ] Viterbi bass: patterned texture evaluation (can Viterbi produce arpeggio/sustained patterns with appropriate cost terms?)
