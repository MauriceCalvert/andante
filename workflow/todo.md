# TODO

Conductor reads at chat start.

---

## Now: The notes are wrong and the texture is drivel

The invention output has two fatal pitch bugs and four texture failures.
The pitch bugs must be fixed first because everything downstream depends
on correct pitches.

### Pitch bugs (blocking)

- [x] **CP1 — Fix plumbing.** Phantom bass, missing episodes, bar duplication.
- [x] **CP2 — Context-aware countersubject.** CS via Viterbi against companion.
- [x] **CP3 — Musical hold-exchange.** Subject-cell spine in running voice.
- [x] **F1 — Fragen consonance hardening.** Pipeline adapter.
- [x] **F2 — Episode integration via fragen.** Paired two-voice episodes.
- [x] **CP4 — Fix answer transposition + mode.** Real answer used same
      degrees with dominant_midi. Minor entries now use natural minor.

### Texture failures

- [x] **F3 — Fragen as a class.** Same episode repeated 3 times because
      used_fragen_indices resets per phrase. Fragen should be a class owning
      its catalogue and tracking used fragments across the entire composition.
      Also fixes: proximity-first start selection, cross-relation at
      boundaries, beat-1 gap fill. See task_f3_holding.md.

After F3, re-evaluate: the hold-exchange (bars 11–12), pedal (bars 21–22),
and final cadence (bars 23–24) are also weak but may improve once the
surrounding material is correct. Listen before briefing further.

---

## Parked

### Must-do (after current sequence)

- Invertible counterpoint enforcement: CS is optimised per-entry by Viterbi, not composed once to work both above and below the subject. True double counterpoint requires a single CS that is consonant in both orientations, then placed by register at render time.
- Hold-exchange cross-bar descent: dispatcher sends hold-exchange as two separate 1-bar entries, so cell_iteration>0 never activates. Each bar sequences independently.
- Pedal soprano tension: `_write_pedal` gives soprano only two boundary knots. Viterbi produces identical bars. Need cadential-approach contour with mid-phrase knots.
- Final cadence bass formula: cadenza_composta bass is three repeated dominants then bare tonic. No cadential formula (IV–V–I, ii6–V–I).
- Cadence length reform (remaining): semplice, half, comma in 4/4; all in 3/4; hemiola; grand cadence
- Structural knot consonance: tritones between voice knots from degree + octave selection

### Later

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
- Figurenlehre labelling
- Figuration strong-beat consonance / metric alignment
- Thematic cadence 3/4
- Thematic cadence bass

---

## Completed

### Bach Invention Targets (2026-02-15/16)

All closed. B1–B8 infrastructure in place. Musical quality gated by CP sequence.

### IMP — Imitative Composition Path (2026-02-15)

IMP-1 through IMP-7 complete. Listening gate passed.

### Earlier work

HRL-1/2, TD-1–3, TD-1t, INV-1/2/3, VG1/2/3, BV1, V9, Phases 10–12.
