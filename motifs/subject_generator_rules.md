Subject generator rules.

---

**Interval (pitch) constraints — `enumerate_intervals`**

1. Interval range: each step is −5 to +5 scale degrees
2. First interval must be non-zero
3. Last interval must be non-zero (final two pitches differ)
4. Cumulative pitch stays within −7 to +7 degrees from start (`PITCH_LO`/`PITCH_HI`)
5. Pitch span (max − min) must be 4–11 degrees (`RANGE_LO`/`RANGE_HI`)
6. Final pitch must land on one of: {0, ±2, ±3, ±4, ±5, +7, −7} (`ALLOWED_FINALS`) — note: subject_gen.py restricts to negative finals only; subject_generator allows positive too
7. At most 1 repeated pitch (`MAX_REPEATS = 1`; interval == 0)
8. At most 4 large leaps (`MAX_LARGE_LEAPS = 4`; |interval| ≥ 3)
9. At least 50% of intervals (excluding the first) must be steps (|interval| ≤ 1) — `MIN_STEP_FRACTION = 0.5`
10. No run of more than 5 consecutive same-sign intervals (`MAX_SAME_SIGN_RUN = 5`)
11. No pitch visited more than 3 times (`max_pitch_freq = 3`)
12. Maximum enumerable length: 14 intervals (`MAX_INTERVALS_ENUMERATE`)

**Duration constraints — per-bar fills**

13. Each bar must fill exactly (no note crosses a bar boundary)
14. Duration vocabulary: semiquaver (2), quaver (4), crotchet (8) in x2-tick units
15. 2–6 notes per bar (`MIN_NOTES_PER_BAR`/`MAX_NOTES_PER_BAR`)
16. No run of more than 4 identical consecutive durations (`MAX_SAME_DUR_RUN = 4`)
17. No leftover smaller than the shortest duration (partial bar impossible)

**Duration constraints — full sequence**

18. Final note at least a minim (8 x2-ticks, `MIN_LAST_DUR_TICKS`)
19. At least 2 distinct duration values
20. First bar must be at least as active as later bars (head mean duration ≤ tail mean duration)

**Melodic validation — post-MIDI-conversion filters**

21. No 7th leaps (10–11 semitones)
22. No tritone leaps (6 semitones)
23. No tritone outline in any 4-note window (first and fourth notes 6 semitones apart)
24. No two consecutive leaps (>2 semitones each) in the same direction

**Scoring — interval sequences**

25. Step fraction closeness to 0.67 ideal (Gaussian, σ = 0.12), weight 0.15
26. Interval variety: count of distinct |interval| values 0–5, normalised to /4, weight 0.10
27. Tail variety: pairwise difference rate among second-half intervals, weight 0.20
28. Opening stability: range of first 3 pitches close to 4.0 (σ = 1.5), weight 0.20
29. Pitch contour fit: RMS distance to interpolated contour waypoints (σ = 2.5), weight 0.35; penalised also against the mirror contour

**Scoring — duration sequences**

30. Shannon entropy of duration distribution, closeness to 0.75 (σ = 0.2), weight 0.10
31. Tail/head mean duration ratio, closeness to 2.5 (σ = 0.6), weight 0.35
32. Change rate (fraction of consecutive durations that differ), closeness to 0.4 (σ = 0.15), weight 0.20
33. Distinct duration count / 3.0, weight 0.10
34. Total ticks closeness to target (σ = 5.0), weight 0.10
35. Final note longer than penultimate (1.0 if longer, 0.5 if equal, 0.0 if shorter), weight 0.15

**Scoring — joint (interval + duration pairing)**

36. Leap–duration coupling: leaps (|iv| ≥ 2) followed by duration ≥ 4 get +1, by duration ≤ 2 get −0.5; normalised, weight 0.30
37. Pre-leap brevity: notes before leaps with duration ≤ 3 get +1; normalised, weight 0.20
38. Stretto potential: count of valid self and inversion stretto offsets / 4.0, weight 0.50

**Stretto consonance rules**

39. Strong beats (tick 0 and bar midpoint): interval mod 7 must be in {0, 2, 5}
40. Weak beats: interval mod 7 must be in {0, 1, 2, 4, 5, 6}; at most 1 weak-beat dissonance per offset
41. No consecutive parallel unisons or 5ths (interval mod 7 in {0, 4})

**Selection pipeline**

42. Top 500 interval sequences per pitch contour (`TOP_K_INTERVALS`)
43. Top 200 duration sequences per rhythm contour (`TOP_K_DURATIONS`)
44. Combined score: 0.4 × interval_score + 0.3 × duration_score + 0.3 × joint_score
45. 6 pitch contours tried: arch, cascade, swoop, valley, dip, ascent (with mirror penalisation)
46. 2 rhythm contours tried: motoric, busy_brake
47. If top candidate fails melodic validation (rules 21–24), scan downward through all candidates until one passes

**Differences from `subject_gen.py`**

- subject_gen.py uses fixed `NUM_NOTES = 9`; subject_generator.py derives note count from bar fills (variable)
- subject_gen.py requires global descent (final pitch < 0); subject_generator.py allows positive finals too
- subject_gen.py requires peak in the head half; subject_generator.py has no peak-position constraint
- subject_gen.py has no scoring, contours, stretto, or melodic validation