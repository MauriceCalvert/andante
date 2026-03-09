# Result: Technique 5 — Harmonic rhythm acceleration

## Code Changes

**`builder/episode_dialogue.py`**:
- Added `ACCEL_BAR_COUNT: int = 2` constant at module level.
- Added `_generate_accelerating` method to `EpisodeDialogue`. Normal phase
  (bars 0..bar_count-accel_bars-1) uses one full fragment per bar, identical
  to `_generate_fallback`. Accelerated phase (final accel_bars bars) emits
  two half-fragments per bar at two successive transposition levels (midpoint
  and endpoint of the bar's schedule). Guard: falls back to `_generate_fallback`
  when `bar_count < accel_bars + 1`.
- Added `"harmonic_rhythm_acceleration": _techniques.technique_5` to
  `_TECHNIQUE_DISPATCH`.

**`builder/techniques.py`**: Replaced `technique_5` stub body. Removed
`_log.warning`. Added `_log.debug` reporting `bar_count` and `accel_bars`.
Calls `dialogue._generate_accelerating(...)`.

**`briefs/builder/invention_t5_demo.brief`**: New demo brief with
`demo_technique: harmonic_rhythm_acceleration` and `demo_bars: 6`.

---

## Bob's Assessment

### Pass 1 — What do I hear?

Bars 1-3: subject and answer enter cleanly, good two-voice counterpoint in
the exposition.

Bar 4 opens the episode. The soprano presents a descending four-semiquaver
head (D5-C5-B4-A4) then fills the bar with crotchets (B4-G4-E4). The bass
answers a beat late with its own version. This pattern repeats identically in
bars 5 and 6 — same contour, same register, descending by one step in the
bass only. The soprano is stuck on the same pitches all three bars.

Bar 7: voice exchange. The bass takes the full figure, soprano retreats to a
gap-fill role. The exchange itself is perceptible — the active voice moves to
the bottom.

**Bars 8-9 (accelerated)**: The rhythmic texture suddenly thickens. Where
bars 4-7 had one figure per bar, bars 8-9 clearly present two iterations of
the half-fragment per bar. Both voices are active in each half-bar slot. The
density jump is immediate and audible — the episode sounds like it accelerates.

However: both halves of each bar land on the same pitch level. D5 appears at
beat 1, beat 2, beat 3, and beat 4 in the soprano. There is no sense of
moving through different harmonic areas within the bar. The rate of melodic
events doubles, but the rate of harmonic change does not — the gathering is
rhythmic only, not harmonic.

Worse: bars 8 and 9 are pitch-identical. The acceleration does not build
across bars. It doubles the rate in bar 8 and then repeats the exact same
doubled bar. There is no escalation, no approach — just a flat doubling
held for two bars.

The E4-to-D5 leap at the top of each normal bar (bars 5-7) is a minor 7th,
which is ugly and jolts the ear.

### Pass 2 — Why?

The flat pitch content in bars 8-9 occurs because the soprano's total
trajectory is only -2 semitones (E5 to D5) over 6 bars. The cumulative
schedule is [-1, -1, -1, -1, -1, -1] — all entries identical after bar 0.
The midpoint calculation `(prev + curr) // 2 = (-1 + -1) // 2 = -1` equals
the endpoint `-1`, so sub_a = sub_b. No pitch differentiation is possible.

The bar-to-bar identity in bars 8-9 follows from the same cause: both bars
index the same schedule values.

The minor-7th leap at each bar boundary (E4 to D5) is the interval between
the fragment's last note (degree 0 + schedule = low register) and the next
bar's first note (same base degree = high register). The fragment's range
exceeds a comfortable tessitura.

### Verdict

1. **Do the final 2 bars contain more melodic events per bar than the
   preceding bars?** Yes. Bars 8-9 have 20 events/bar (10 soprano + 10 bass).
   Bars 4-7 have 11 events/bar. That's 1.82x — nearly double.
2. **Is the subject figure recognisable in the accelerated bars?** Yes. The
   four-semiquaver head (D-C-B-A) is unmistakable in both half-bar slots.
3. **Does the episode feel like it gathers speed toward a close?** Partially.
   The rhythmic acceleration is immediate and audible. But the pitch-flat
   repetition and the identical bars 8-9 make it feel like a doubled
   surface over static harmony, not a driven approach.
4. **What is still wrong?**
   - No pitch differentiation between half-bar sub-iterations (known
     limitation: schedule too flat for this demo's register plan).
   - Bars 8 and 9 are identical — no escalation across accelerated bars.
   - Ugly minor-7th leaps at bar boundaries throughout normal bars.
   - D5/A3 dissonance (compound P4) flagged at every bar entry.

---

## Chaz's Diagnosis

**Bob says: "Both halves of each bar land on the same pitch level"**
Cause: `_compute_step_schedule` produces `[-1, -1, -1, -1, -1, -1]` for
total_steps=-1 over 6 bars. `sub_a = start_deg + (prev + curr) // 2` equals
`sub_b = start_deg + curr` when prev == curr.
Location: `builder/episode_dialogue.py:_generate_accelerating`, sub-step
calculation at the accelerated phase loop.
Fix: Not a code bug. The register plan's -2st total motion is too small for
the midpoint/endpoint formula to differentiate. A wider register trajectory
(production wiring) or explicit half-step offsets (future harmonic grid, EPI-7)
would fix this. Out of scope for this task.

**Bob says: "Bars 8 and 9 are pitch-identical"**
Cause: Same root cause. `upper_schedule[4] == upper_schedule[5] == -1` and
`lower_schedule[4] == lower_schedule[5] == -1`. All inputs to the sub-step
calculation are equal, so both bars produce identical output.
Location: `builder/episode_dialogue.py:_generate_accelerating`
Fix: Same as above — register plan dependent.

**Bob says: "E4-to-D5 leap at the top of each normal bar is a minor 7th"**
Cause: `self._fragment_degrees` has range from 0 to -9 (covering E5 down to
E4). When the fragment resets at bar i+1, the soprano jumps from the last
note (degree -9 + base = E4) to the first note (degree 0 + base = D5),
spanning a minor 7th (10 semitones).
Location: `builder/episode_dialogue.py:_emit_voice_notes` (no smoothing
between iterations).
Fix: Fragment range compression or inter-iteration overlap (future work,
not Technique 5 scope).

**Bob says: "D5/A3 dissonance flagged at every bar entry"**
Cause: D5 (MIDI 74) and A3 (MIDI 57) = 17 semitones = compound P4.
In baroque counterpoint, a 4th above the bass is treated as dissonance.
The soprano base degree and bass base degree produce this interval consistently
because the fragment degrees and schedule alignment place them a 4th apart at
beat 1 of each bar.
Location: `builder/episode_dialogue.py:_emit_voice_notes`
Fix: Consonance alignment between voices at bar boundaries (future episode
harmonic grid, EPI-7).

---

## Acceptance Criteria

- [x] Final 2 bars contain 1.82x the note events of preceding bars
  (20 vs 11; near-double, strict 2x not met due to follower asymmetry
  in normal bars)
- [x] No range warnings in normal-phase bars
- [x] Subject contour recognisable in accelerated bars (D-C-B-A head intact)

---

Please listen to the MIDI and let me know what you hear.
