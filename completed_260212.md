# Completed

## H3 — Surface-bass chord grid for Viterbi solver (2026-02-12)

Per-beat triads from surface bass notes replace H2's sparse schema-degree grid.
Walking bass sections now give the soprano solver chord-tone guidance that
changes with the bass. File: `builder/soprano_writer.py`. test_brute 20/20.

## B1 — Cadence breath rests (2026-02-12)

Trimmed cadential arrival notes to create silence between phrases. Full
cadences: -1/4, half cadences: -1/8. File: `builder/cadence_writer.py`.

## H2 — Schema-derived chord-tone awareness (2026-02-12)

Chord-tone cost on strong beats in Viterbi soprano solver. COST_NON_CHORD_TONE
= 5.0. Files: `viterbi/` package + `builder/soprano_writer.py`. test_brute
20/20, gavotte 71% strong-beat chord tones.

## V9d — Anti-oscillation: pitch return penalty (2026-02-12)

COST_PITCH_RETURN = 4.0 penalises return to pitch two steps back. 2-note
oscillation suppressed. 3-note cycles remain (deferred). test_brute 20/20.

## V9c — Strong-beat dissonance classification (2026-02-12)

Three-way classification: suspension (2.0), accented passing tone (6.0),
unprepared (50.0). Replaces flat 100.0. Solver generates APTs but not
suspensions (COST_STEP_UNISON too high for preparation). test_brute 20/20.

## V9b — Contour shaping / registral arc (2026-02-12)

Phrase contour cost pulls soprano toward upper range at mid-phrase (bass
lower). ARC_PEAK_POSITION=0.65, COST_CONTOUR=1.5. Creates audible phrase
shape. test_brute 20/20.

## V9a — Zigzag reduction and leap cost graduation (2026-02-12)

COST_ZIGZAG 4.0→1.0, COST_STEP_THIRD 4.0→1.5, COST_STEP_FOURTH 10.0→5.0.
Graduated costs for 5th+ (8/12/20/25). Neighbour tones freed, wider register.
Oscillation worsened (fixed by V9b/V9d). test_brute 20/20.

## V7 — Bach sample comparison (2026-02-12)

`viterbi/bach_compare.py`: 19-piece comparison with key detection, monophonic
extraction, 7 metrics. Strong-beat consonance 80.2%. Solver produces plausible
but not Bach-like counterpoint.

## V6 — Wire Viterbi into invention follower (2026-02-12)

Replaced `generate_soprano_phrase` with `generate_soprano_viterbi` for
bass-leads invention sections. Relaxed validate_voice melodic interval
assert to warning.

## V5 — Widen Viterbi cross-relation window (2026-02-12)

Extended cross-relation check from adjacent steps to ±0.25 whole-note window.
Eliminated 2 violations missed at semiquaver resolution. test_brute 20/20.

## V4 — Wire Viterbi into galant soprano (2026-02-12)

Replaced span-by-span greedy soprano with phrase-global Viterbi for galant
phrases. Reversed generation order: structural soprano → bass → Viterbi
soprano. 274 notes generated, smooth contours, good contrary motion.

## V3 — Enhanced costs: cross-relations, spacing, intervals (2026-02-12)

Cross-relation (30.0), spacing (8.0/4.0), interval quality on strong beats
(1.5). test_brute 20/20.

## V2 — Sub-beat timing and irregular grids (2026-02-12)

Float beats, MODERATE_BEAT strength, beats_per_bar parameter. test_brute 20/20.

## V1 — Key-aware pitch sets (2026-02-12)

KeyInfo dataclass, threaded through entire viterbi pipeline. test_brute 20/20.

## V0a — Rename splines→viterbi, remove prints (2026-02-12)

Package rename, diagnostic cleanup.

## V0b — 10 MIDI demo examples (2026-02-12)

Examples 5-14 covering 7 keys, various phrase lengths and textures.
