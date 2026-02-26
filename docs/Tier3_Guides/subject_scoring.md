Now let me grab the weight values:Here's how subject scoring works. There are 10 criteria, each returning 0–1. They're multiplied by weights and summed, giving a theoretical range of 0–12.5 (since most weights are 1.0, but scalic monotony is 2.5 and head character is 1.5).

**The criteria, in plain terms:**

1. **Intervallic range** (weight 1.0) — How much pitch space the subject covers. A 5th scores 0.5, an octave scores 1.0, anything beyond is clipped to 1.0. Subjects confined to a 3rd or less score 0.

2. **Signature interval** (weight 1.0) — Whether the subject contains at least one distinctive leap. Steps score 0; a 3rd scores 0.4; a 4th, 0.6; a 5th, 0.8; a 6th or more, 1.0. The idea is that memorable subjects have at least one characteristic leap.

3. **Rhythmic contrast** (weight 1.0) — The ratio between the longest and shortest note. If all notes are the same length, 0. A 2:1 ratio (quaver vs semiquaver) scores 0.33; a 4:1 ratio (crotchet vs semiquaver) scores 1.0.

4. **Direction commitment** (weight 1.0) — Whether the first half of the subject goes somewhere decisively, rather than oscillating around the starting pitch. It measures net displacement in the first half as a fraction of total range. Oscillating subjects score low; subjects that commit to a direction score high.

5. **Repetition penalty** (weight 1.0) — Penalises consecutive pairs of degrees that repeat or oscillate (e.g. 0,1,0,1). Returns 1.0 for no repetition, 0.0 for heavy repetition. So it's actually a *reward for non-repetition*, despite the name.

6. **Harmonic variety** (weight 1.0) — How many of four standard chords (I, IV, V, ii) the degree sequence touches. Touching 1 chord scores 0; all 4 scores 1.0. This ensures the subject isn't harmonically static.

7. **Fast note density** (weight 1.0) — Proportion of notes that are semiquavers. If 40%+ are semiquavers, score is 1.0. This rewards subjects with rhythmic energy.

8. **Duration variety** (weight 1.0) — How many distinct note lengths appear. One value scores 0; four or more distinct values scores 1.0.

9. **Scalic monotony** (weight **2.5**) — Penalises subjects where too many intervals are steps (±1). If 55% or fewer intervals are steps, full score (1.0). If 80%+ are steps, score is 0. Linear interpolation between. The high weight (2.5) means this is the single most influential criterion — it strongly pushes against bland scale-run subjects.

10. **Head character** (weight **1.5**) — Whether the opening motif (Kopfmotiv, first 4 notes) contains a characteristic leap. Steps only = 0; a 3rd = 0.5; a 4th = 0.8; a 5th or more = 1.0. Weighted 1.5 because a strong opening interval is essential for fugue subject identity.

**The selection threshold:** Candidates scoring below 7.0 (`MIN_AESTHETIC_SCORE`) are excluded before diversity selection. Since the max is 12.5, this means roughly the top 55% of the scoring range passes.

**Separate from scoring:** There's also an 11-dimensional feature vector (`subject_features`) used not for ranking but for diversity selection — it extracts things like climax position, leap fraction, and net direction so that the greedy max-min Hamming selector can pick subjects that are genuinely different from each other, not just high-scoring variations of the same shape.