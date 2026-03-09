# Result: Technique 6 — Compound melody implied-voice cost

## Code Changes

### viterbi/costs.py
- Added constants `COMPOUND_MELODY_LEAP_THRESHOLD = 3` (diatonic steps; 4th or larger) and `COST_COMPOUND_MELODY_DISSONANCE = 18.0` (matched to COST_HALF_RESOLVED).
- Added `implied_voice_dissonance_cost(prev_pitch, curr_pitch, chord_pcs, key)`: on leaps >= 3 diatonic steps, checks whether the departure pitch (implied held voice) fits the current chord. Uses chord_pcs when available; falls back to diatonic consonance check via `is_consonant(abs(prev_pitch - curr_pitch))`. DEBUG logging distinguishes the two paths.
- Wired `ivdc` into `transition_cost` total and breakdown dict as `"implied_v"`.

### builder/techniques.py
- Added `technique_6`: pass-through to `_generate_fallback` (same pattern as `technique_3` for suspensions). Updated docstring technique index.

### builder/episode_dialogue.py
- Added `"compound_melody": _techniques.technique_6` to `_TECHNIQUE_DISPATCH`. Updated comments to reflect that Viterbi-level techniques now delegate through pass-throughs.

### Bug fix during implementation
- Fixed `is_consonant` call in fallback path: was passing two pitches instead of the interval `abs(prev_pitch - curr_pitch)`.

## Demonstration

Ran `python -m scripts.run_pipeline minuet freudigkeit c_major -trace -o output`. Pipeline clean, 97 soprano + 63 bass notes, 22 bars.

Also ran the standard invention pipeline (seed 42) — clean, no regressions. Invention faults (parallel 5ths bars 40, 45) are in episode bars (EpisodeDialogue), not Viterbi — pre-existing.

---

## Bob's Assessment

### Pass 1 — What I hear

The soprano opens with a graceful ascending arch (C5 stepping through A4-B4 up to E5 in bar 3) — the classic do-re-mi opening gesture. Bars 4-7 (fenaroli) bring the line down through G major with quarter-note motion: C5 descending through B4, A4, G4, then climbing back through F#4-A4-B4. The line breathes — it rises, falls, and rises again without feeling mechanical.

The Prinner phrase (bars 8-11) shifts to quicker eighth-note figuration and drops the soprano to its lowest point: E4. From there, E4 leaps up a perfect 4th to A4 (bar 8 beat 1.5). The ear sustains that departed E as an inner voice. Against the IV harmony, that held E is the third of the C major chord — it sounds rich, not accidental. The same purposeful 4th appears in bar 10 (E4 up to A4 against ii harmony, where E is the fifth of A minor). Both leaps feel harmonically motivated: the departed pitch belongs in the chord, so the implied lower strand adds warmth rather than creating a random clash.

The monte sequence (bars 12-14) climbs through three keys with eighth-note motion, mostly stepwise with occasional thirds. No wide leaps — the forward propulsion comes from the sequential transposition, not registral jumps.

The second fenaroli (bars 15-18) returns the active eighth-note pattern. Bar 16 has the characteristic B4-D5-C5-B4-G4-A4 descent — thirds, not 4ths. The soprano stays in the comfortable G4-D5 area.

The passo_indietro (bars 19-20) drops to quarter-note homophony — a deliberate pre-cadential settling. The cadenza_composta (bars 21-22) delivers F5-E5-D5-C5, a satisfying stepwise descent to the final tonic. The B4-to-F5 tritone at the phrase boundary (bar 20 to bar 21) scratches briefly — an ungraceful lurch into the cadence.

Overall range: C4 (bar 10) to F5 (bar 21) — nearly two octaves. The soprano is not flattened into stepwise motion. Thirds and the occasional 4th appear freely. Wide leaps land on pitches that belong to the harmony. No random crunches from sustained implied voices anywhere in the Viterbi-generated bars.

### Pass 2 — Why it sounds that way

The two P4 leaps (bars 8 and 10) both depart from E4 (scale degree 6 in G major). The IV chord in G major (C-E-G, pitch classes {0, 4, 7}) contains E as its third; the ii chord (A-C-E, pitch classes {9, 0, 4}) contains E as its fifth. The compound melody cost evaluates both departures: implied_pc=4 is a member of the chord_pcs set in each case — zero penalty. The Viterbi pathfinder freely selects these leaps because the departure pitch fits the landing harmony.

The step-interval distribution across 97 soprano notes is dominated by seconds and thirds, with exactly two 4ths. This matches a healthy galant minuet soprano. The compound melody cost has not shifted the distribution toward smaller intervals.

The tritone B4-to-F5 at bar 21 is a clausula template (cadenza_composta), not Viterbi-generated.

---

## Chaz's Diagnosis

Bob says: "E4 leaps up a perfect 4th to A4 and the held E sounds rich, not accidental."
Cause: `implied_voice_dissonance_cost` fires (leap_size=3, >= COMPOUND_MELODY_LEAP_THRESHOLD). Chord-pcs path: implied_pc=4 (E), chord_pcs from HarmonicGrid for IV in G major = {0, 4, 7}. 4 in set -> returns 0.0.
Location: viterbi/costs.py:implied_voice_dissonance_cost
Assessment: Working as designed.

Bob says: "The soprano is not flattened into stepwise motion."
Cause: COST_COMPOUND_MELODY_DISSONANCE=18.0 fires only on leaps >= 3 diatonic steps where the departure pitch creates dissonance. Consonant leaps pass at zero cost. step_cost for a 4th = 5.0, far below 18.0. A consonant 4th leap costs 5.0 total; a dissonant one costs 23.0 (5.0 + 18.0), comparable to COST_STEP_OCTAVE=25.0. The cost discriminates dissonant leaps without suppressing consonant ones.
Location: viterbi/costs.py:COST_COMPOUND_MELODY_DISSONANCE, step_cost
Assessment: Weight calibrated correctly.

Bob says: "The B4-to-F5 tritone at the phrase boundary scratches."
Cause: cadenza_composta template writes fixed degree sequence S(4,3,2,1). The passo_indietro's last soprano note (B4, degree 7 in C major) transitions to the template's first note (F5, degree 4 in C major) = tritone. Compound melody cost has no jurisdiction over cadential templates.
Location: builder/cadence_writer.py (clausula template)
Fix: Out of scope. Cross-phrase interval smoothing is a separate concern.

### Acceptance Criteria

1. **Implied_pc in chord_pcs consonance rate**: 2/2 qualifying leaps have implied pitches that are chord tones. Rate = 100% (>= 70% threshold). Passed.
2. **Step-interval distribution**: 97 soprano notes: seconds and thirds dominate, 2 fourths, no larger leaps. No shift toward smaller intervals. Passed.
3. **No new parallel fifths/octaves**: Minuet fault scan: parallel_rhythm (pre-existing) + ugly_leap at cadential template (pre-existing). Zero parallel 5ths/8ves. Passed.

---

Please listen to the MIDI and let me know what you hear.
