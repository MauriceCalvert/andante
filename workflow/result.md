# Result: I5+I8 — Rhythmic Independence + Beat-1 Continuity

## Changes Made

### I5 — Soprano Viterbi rhythmic independence

**`builder/soprano_viterbi.py`:**
- Added `avoid_onsets_by_bar: dict[int, frozenset[Fraction]] | None = None` parameter to `generate_soprano_viterbi`.
- When `avoid_onsets_by_bar` is not None, Step 2 replaces `compute_rhythmic_distribution` with bar-by-bar `select_cell` calls (same pattern as `bass_viterbi.py`). Computes bar-relative structural soprano offsets as `required_onsets`. Passes `avoid_onsets` per bar for rhythmic contrast.
- When `avoid_onsets_by_bar` is None, existing behaviour unchanged (span-based `compute_rhythmic_distribution`).
- Added imports: `phrase_bar_duration`, `phrase_bar_start`, `phrase_offset_to_bar`, `select_cell`.

**`builder/free_fill.py`:**
- In the `free_voice_idx == 0` (soprano companion) branch, computes bar-relative bass onset sets from accumulated `bass_notes` within the FREE run's time span.
- Passes the computed `avoid_onsets_by_bar` to `generate_soprano_viterbi`.
- Added imports: `phrase_bar_start`, `phrase_offset_to_bar`.

### I8 — Beat-1 continuity validation

**`builder/compose.py`:**
- Added `_ensure_beat1_coverage(plan, result, prior_upper, prior_lower)` function.
- For each bar in a phrase result, checks if any note (soprano or bass, including prior phrases) covers beat 1.
- If uncovered: finds latest-ending note before bar_start in the current result, prefers bass extension. Extends note duration to cover beat 1 + one beat_unit. Logs warning.
- Called after every `write_phrase` in `compose_phrases`.
- Added `logging` import and `phrase_bar_start` import.

## Evaluation (seed 42, invention Klage, G major, 22 bars)

### Bob

**Beat-1 coverage:** Every bar has at least one voice on the downbeat. No gaps.

**Rhythmic independence:** Bars where one voice runs while the other holds are well contrasted:
- Bar 2: soprano semiquavers, bass crotchets (subject vs answer opening)
- Bars 5-6: soprano semiquaver runs, bass crotchets
- Bars 11-12: soprano holds then semiquaver bursts, bass crotchet-minim
- Bars 17-18: soprano crotchets, bass running figures
- Bars 19-20: soprano continuous semiquavers over bass pedal whole note

**Lockstep fault:** Bars 7-8 have 7 consecutive simultaneous attacks. Both voices in crotchet-crotchet-minim lockstep (bar 7), continuing with overlapping quaver/semiquaver attacks (bar 8). Sounds like a chorale harmonisation, not counterpoint.

**Companion voice:** In bars with density contrast, the companion reads as a supporting line, not a doubled melody. Bar 2 bass grounds the running soprano subject. Bars 19-20 bass pedal anchors the soprano's elaborate figuration.

### Chaz

The bars 7-8 lockstep (7 consecutive simultaneous attacks, exceeding MAX_PARALLEL_RHYTHM_ATTACKS=5) is caused by the thematic renderer producing CS with identical rhythm to the subject. Both voices are thematic (SUBJECT + CS); neither is FREE. The I5 avoid_onsets mechanism does not apply. Fix requires CS rhythm awareness in `builder/thematic_renderer.py` — out of scope per task constraints.

The I5 soprano companion path (`free_voice_idx == 0` in `free_fill.py`) was not exercised by seed 42. This seed's entry layout assigns thematic material to soprano in every bar. The code is wired and ready for seeds that produce soprano-as-FREE bars.

The I8 `_ensure_beat1_coverage` passed through without modifications — all bars already had beat-1 coverage from the thematic layout.

### Faults (from trace)

| Fault | Location | Cause |
|-------|----------|-------|
| unprepared_dissonance | 2.1 | G4/D3 at subject/answer overlap |
| direct_fifth | 5.1 | B4-F#4 leap in episode |
| direct_octave | 5.2 | F#4-C#5 leap in episode |
| direct_fifth | 6.1 | C#5-E4 leap in episode |
| direct_octave | 6.2 | E4-B4 leap in episode |
| parallel_rhythm | 8.2 | 7 consecutive simultaneous attacks (thematic CS lockstep) |

### Open Complaints

1. Parallel rhythm bars 7-8: thematic renderer CS lockstep (out of scope)
2. Pre-existing: unprepared dissonance, direct fifths/octaves in episodes
3. I5 soprano companion untested by this seed (implementation ready)
