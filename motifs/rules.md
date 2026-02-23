Let me pull together every filter, constraint, and scoring weight in the pipeline.Here's every rule in the pipeline, end to end:

---

**1. CP-SAT hard constraints** (`cpsat_generator.py` → `_build_model`)

| Rule | Value | Effect |
|---|---|---|
| Pitch range | degrees −7 to +7 | 15-degree span max |
| First note | degree 0 | Always starts on tonic |
| No repeated notes | `ivs[i] != 0` | Every interval non-zero |
| Interval range | −5 to +5 | Max leap = fifth |
| Span (range) | 4–11 degrees | `RANGE_LO`–`RANGE_HI` |
| Final note | must be in {0, 2, 4} | `ALLOWED_FINALS` |
| Step fraction | ≥50% of intervals have |iv|≤1 | `MIN_STEP_FRACTION` |
| Large leaps (|iv|≥3) | ≤4 | `MAX_LARGE_LEAPS` |
| Same-sign run | ≤5 consecutive | Automaton, `MAX_SAME_SIGN_RUN` |
| Pitch frequency | any degree ≤3 times | `MAX_PITCH_FREQ` |
| Stretto consonance | at primary offset k=n//2 | All overlapping pairs must be in `CONSONANT_INTERVALS` |

**2. Melodic validator** (`validator.py` → `is_melodically_valid`)

| Rule | Effect |
|---|---|
| No tritone leaps | |semitones| = 6 → reject |
| No 7th leaps | |semitones| ∈ {10, 11} → reject |
| No consecutive same-direction leaps | two |iv|>2 same sign → reject |
| No tritone outline | any 4-note span with |semitones| = 6 → reject |

**3. Pitch scorer** (`pitch_generator.py` → `score_pitch_sequence`, weights sum to 1.0 + bonus)

| Component | Weight | What it rewards |
|---|---|---|
| Signature leap | 25% | Has a leap ≥3 degrees, placed in first 40% |
| Leap recovery | 20% | Contrary-motion step within 2 notes after each leap |
| Run penalty | 20% | Longest same-direction stepwise run ≤3 |
| Interval variety | 15% | ≥3 distinct |interval| values |
| Climax placement | 20% | Unique extreme outside the 30–60% window scores higher (!?) |
| Direction changes | +0.05 bonus | 1 change = +0.05, 2 = +0.03 |

**4. Duration enumerator** (`duration_generator.py` → `enumerate_durations`)

| Rule | Value | Effect |
|---|---|---|
| Vocabulary | semiquaver(1), quaver(2), crotchet(4), minim(8) | Only 4 durations |
| Notes per bar | 2–8 | `MIN/MAX_NOTES_PER_BAR` |
| Max subject notes | 16 | `MAX_SUBJECT_NOTES` |
| Same-duration run | ≤4 consecutive | `MAX_SAME_DUR_RUN` |
| Last note | ≥crotchet | `MIN_LAST_DUR_TICKS = 4` |
| No isolated semiquavers | semiquaver must have adjacent semiquaver | |
| ≥2 distinct durations | `len(set(seq)) < 2` → reject | |
| Bar 1 density ≥ bar 2 | mean tick bar1 ≥ mean tick bar2 → reject if not | Head denser than tail |

**5. Duration scorer** (`duration_generator.py` → `score_duration_sequence`)

| Component | Weight | What it rewards |
|---|---|---|
| Duration variety | 25% | ≥3 distinct duration values |
| Semiquaver presence | 20% | 2–4 semiquavers = 1.0 |
| Long-short contrast | 20% | ratio longest/shortest ≥4 |
| Final > penultimate | 15% | Last note longer than second-to-last |
| Opening ≤ crotchet | 10% | First note not too long |
| No monotony | 10% | Same-duration run ≤3 |

**6. Selection filters** (`selector.py`)

| Rule | Value | Effect |
|---|---|---|
| Quality floor | 85% of best combined score | `QUALITY_FLOOR_FRACTION` |
| Dedup cap | 2500 entries | `DIVERSITY_POOL_CAP` |
| Stretto minimum | ≥3 viable offsets | `MIN_STRETTO_OFFSETS` |
| Contour | +0.05 bonus for preferred shape | Not a gate |

**7. Stretto evaluation** (`stretto_constraints.py`)

| Rule | Effect |
|---|---|
| Strong-beat dissonance | instant reject for that offset |
| Weak-beat tritone | instant reject for that offset |
| Quality floor | consonant/total < 0.6 → not viable |
| Max offset | first half of subject only |

---

The **zigzag bias** comes from the pitch scorer: it penalises stepwise runs >3, rewards direction changes, and gives 25% weight to having a signature leap. A Bach-like subject that steps C-D-E-F-G-A-G-F-E-D would be penalised on runs, score zero on direction-change bonus, and possibly zero on signature leap. The scorer is actively hostile to the subjects you want.

The **rhythmic sameness** comes from the duration scorer demanding long-short contrast (ratio ≥4) and semiquaver presence simultaneously. A subject in even quavers — perfectly normal for Bach — scores 0 on contrast, 0 on semiquaver presence, and low on variety. Dead on arrival.

These scorers were designed when the pool was tiny and needed quality filtering. Now that CP-SAT + stretto gives you a large pool of structurally valid subjects, the scorers are the bottleneck. They enforce a narrow aesthetic that excludes most baroque idioms.

Do you want to rethink the scorers, or strip them down to just hard constraints and let stretto quality + diversity selection do the ranking?