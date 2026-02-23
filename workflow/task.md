## Task: SUBDUR — Multi-duration pairing + stretto cache

Read these files first:
- `motifs/subject_gen/constants.py`
- `motifs/subject_gen/selector.py`
- `motifs/subject_gen/cache.py`
- `motifs/stretto_constraints.py` (read-only context, do not modify)

### Musical Goal

Every subject of a given note count currently gets the same rhythm —
the single highest-scoring duration pattern. This is why every subject
has two minims: the duration scorer maximises long-short contrast, and
minim endings win. The pitch varies between subjects but the rhythm
never does.

A fugue subject's character comes as much from rhythm as pitch. A
subject in quavers with a crotchet ending has a completely different
drive from one ending on a minim. We need rhythmic variety in the pool
so subjects can differ in both pitch and rhythm.

Separately, stretto evaluation takes ~200s on every run because it is
not cached. It must be a one-off cost.

### Idiomatic Model

Bach invention subjects show wide rhythmic variety. BWV 772 opens with
a semiquaver run ending on a crotchet. BWV 775 uses dotted rhythms.
BWV 779 has even semiquavers throughout. No single rhythmic profile
dominates. A generator locked to one duration pattern per note count
cannot produce this variety.

### What Bad Sounds Like

- **Rhythmic uniformity**: every subject ends the same way (two minims),
  every subject has the same internal rhythm for its note count. All
  subjects sound like they came from the same mould.
- **Slow regeneration**: 542s per run is unusable for iterative work.

### Known Limitations

1. **Pool size increase**: with K durations per note count, the raw pool
   grows K-fold. The quality floor + dedup cap (500) limits what reaches
   stretto evaluation, so cost stays bounded.

2. **Diversity metric is pitch-only**: the greedy selector uses Hamming
   distance on degrees. It does not measure rhythmic distance. This means
   if two entries share the same pitch but differ in rhythm, the selector
   treats them as distance-0. This is acceptable: pitch variety is the
   primary goal, and different note counts naturally produce different
   rhythms. Rhythmic distance is a future refinement.

3. **Duration scorer bias**: the scorer still rewards long-short contrast.
   Minim-heavy patterns score higher. By including multiple durations
   per note count (not just the best), patterns without minims now enter
   the pool — they just rank slightly lower. This is sufficient: the
   stretto filter and diversity selector can promote them.

### Implementation

#### 1. `motifs/subject_gen/constants.py`

Add:
```python
DURATIONS_PER_NOTE_COUNT: int = 5
```

#### 2. `motifs/subject_gen/selector.py`

**a) Import the new constant:**

Add `DURATIONS_PER_NOTE_COUNT` to the imports from `constants`.

**b) Replace single-best duration with top-K:**

Currently:
```python
best_dur_by_count: dict[int, tuple[float, tuple[int, ...]]] = {}
for nc, scored_list in all_scored_durs.items():
    if scored_list:
        best_dur_by_count[nc] = scored_list[0]
```

Replace with:
```python
top_durs_by_count: dict[int, list[tuple[float, tuple[int, ...]]]] = {}
for nc, scored_list in all_scored_durs.items():
    if scored_list:
        top_durs_by_count[nc] = scored_list[:DURATIONS_PER_NOTE_COUNT]
```

**c) Build pool by pairing each pitch with each of the K durations:**

Currently:
```python
for nc in sorted(best_dur_by_count.keys()):
    if note_counts is not None and nc not in note_counts:
        continue
    best_d_sc, best_d_seq = best_dur_by_count[nc]
    all_pitch = _cached_validated_pitch(...)
    ...
    for sp in all_pitch:
        combined = 0.50 * sp.score + 0.50 * best_d_sc
        pool.append((combined, sp, best_d_seq))
```

Replace with:
```python
for nc in sorted(top_durs_by_count.keys()):
    if note_counts is not None and nc not in note_counts:
        continue
    dur_options = top_durs_by_count[nc]
    all_pitch = _cached_validated_pitch(...)
    ...
    for sp in all_pitch:
        for d_sc, d_seq in dur_options:
            combined = 0.50 * sp.score + 0.50 * d_sc
            pool.append((combined, sp, d_seq))
```

**d) Fix dedup key to include duration pattern:**

Currently the dedup key is `entry[1].degrees` (pitch only). Same pitch
with different rhythm is deduped away. Change the `seen` set and dedup
key to `(degrees, dur_pattern)`:

```python
seen: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
...
    dedup_key = (entry[1].degrees, entry[2])
    if dedup_key not in seen:
        seen.add(dedup_key)
        candidates.append(entry)
```

**e) Cache stretto evaluation results:**

The stretto filter loop is the 200s bottleneck. Cache it to disk.

After the quality-floor + dedup step and before the stretto filter
loop, attempt to load a stretto cache. Cache key name:
`stretto_eval_{mode}_{target_bars}b_{bar_ticks}t.pkl`

The cache is a dict mapping
`(degrees_tuple, dur_pattern_tuple)` → `tuple[OffsetResult, ...]`
(the full viable offsets, not just the count — needed by `_build_subject`).

Logic:
1. Load cache dict (or empty dict if missing).
2. In the stretto filter loop, check cache first. On cache miss,
   evaluate and store in the dict.
3. After the loop, save the updated cache dict if any new entries
   were added.

Import `_load_cache` and `_save_cache` from `motifs.subject_gen.cache`.

Import `OffsetResult` from `motifs.stretto_constraints`.

**f) Use cached stretto results in `_build_subject` too:**

Currently `_build_subject` calls `evaluate_all_offsets` again for each
picked subject. Pass the cached viable offsets through instead, to avoid
redundant evaluation.

Add a `cached_viable_offsets` parameter to `_build_subject`:
```python
def _build_subject(
    sp: _ScoredPitch,
    best_durs: tuple[int, ...],
    tonic_midi: int,
    mode: str,
    metre: tuple[int, int],
    bar_ticks: int,
    final_score: float,
    cached_viable_offsets: tuple | None = None,
) -> GeneratedSubject:
```

If `cached_viable_offsets` is provided, use it instead of calling
`evaluate_all_offsets`. Update the call site in the picks loop to
pass the cached offsets from the stretto cache.

Store the viable offsets alongside each stretto-filtered candidate so
they're available at pick time. Change `stretto_filtered` entries to
include the offsets — either as a 4-tuple
`(score, sp, dur_seq, viable_offsets)` or by storing a side dict
keyed by `(degrees, dur_pattern)`.

#### 3. Delete stretto cache on first run

The stretto cache file does not exist yet, so no deletion needed.
However, the existing pitch caches are still valid (they don't include
duration info). Do NOT delete the CP-SAT pitch caches — those took
6 minutes to generate and are unchanged.

### Constraints

- Do not modify `cpsat_generator.py`, `pitch_generator.py`,
  `duration_generator.py`, `stretto_constraints.py`, `scoring.py`,
  or `contour.py`.
- Do not modify the scoring weights or quality floor.
- Do not add new files (use existing `cache.py` utilities).
- Do not change `select_subject` signature or `_degree_distance`.

### Checkpoint (mandatory)

After implementation, delete only the stretto cache file if it exists
(NOT the cpsat_pitch caches), then run:

```
python -m motifs.subject_generator --bars 2 --verbose
```

First run will evaluate stretto (~200s) and cache it. Second run
should load from cache and complete in under 5s.

Bob:
1. Do the 6 selected subjects show rhythmic variety? Are there
   different ending patterns (not all minim endings)?
2. How many candidates pass the ≥3 stretto filter now vs. the
   28 from before?
3. What note counts and contour shapes appear?

Chaz:
1. Verify `DURATIONS_PER_NOTE_COUNT` is 5.
2. Verify dedup key is `(degrees, dur_pattern)`.
3. Verify stretto cache loads/saves correctly — second run < 5s.
4. Verify `_build_subject` uses cached offsets, not re-evaluation.

### Acceptance Criteria

- All 6 subjects have ≥3 stretto offsets.
- At least 2 different rhythmic endings among the 6 (not all minim).
- ≥40 candidates pass stretto filter (proxy — more rhythm options
  should expand the pool beyond the previous 28).
- Second run completes in under 5 seconds (stretto cache working).
