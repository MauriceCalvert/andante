# BM-3a — Wire melody generator into pipeline

Read these files first:
- `motifs/subject_gen/melody_generator.py` (created in BM-2)
- `motifs/subject_gen/duration_generator.py` (return type change)
- `motifs/subject_gen/pitch_generator.py` (rewrite)
- `motifs/subject_gen/selector.py` (update loop)
- `motifs/subject_gen/rhythm_cells.py` (Cell dataclass)
- `motifs/subject_gen/constants.py`

## Goal

Wire the new melody generator into the pipeline so that
`select_diverse_subjects` uses harmonic-grid pitch generation.
Three files modified.

## Files to modify

### 1. `motifs/subject_gen/duration_generator.py`

The new pitch generator needs the cell sequence, not just duration
indices.  Change `_cached_scored_durations` to return cell metadata.

**Return type change:**
- Old: `dict[int, list[tuple[int, ...]]]`
- New: `dict[int, list[tuple[tuple[int, ...], tuple[Cell, ...]]]]`

Each entry becomes `(dur_indices, cell_sequence)` instead of just
`dur_indices`.

Change `_generate_sequences` to yield `(indices, cells, score)` instead
of `(indices, score)`.

Update the sorting/capping to carry the cell tuple through.

**Cache key must change** (different data shape): use prefix
`cell_dur_v2_*`.

### 2. `motifs/subject_gen/pitch_generator.py`

Rewrite.  Remove all imports from head_enumerator, cpsat_generator,
validator.  The module now delegates to melody_generator.

New function:

```python
def _cached_validated_pitch_for_cells(
    cell_sequence: tuple[Cell, ...],
    tonic_midi: int,
    mode: str,
    n_bars: int,
    bar_ticks: int,
    verbose: bool = False,
) -> list[_ScoredPitch]:
```

This calls `generate_pitched_subjects` from melody_generator and
caches the result.  Cache key: a string built from the cell names,
mode, n_bars, and bar_ticks.

Delete the old `_cached_validated_pitch` function entirely — it will
have no callers after selector.py is updated.

### 3. `motifs/subject_gen/selector.py`

Update the pitch-generation loop in `select_diverse_subjects`.

Currently:
```python
for nc in sorted(all_durs_by_count.keys()):
    dur_options = all_durs_by_count[nc]
    all_pitch = _cached_validated_pitch(num_notes=nc, ...)
    for sp in all_pitch:
        for d_seq in dur_options:
            pool.append((sp, d_seq))
```

New:
```python
for nc in sorted(all_durs_by_count.keys()):
    dur_options = all_durs_by_count[nc]
    for d_seq, cells in dur_options:
        all_pitch = _cached_validated_pitch_for_cells(
            cell_sequence=cells,
            tonic_midi=tonic_midi,
            mode=mode,
            n_bars=target_bars,
            bar_ticks=bar_ticks,
            verbose=verbose,
        )
        for sp in all_pitch:
            pool.append((sp, d_seq))
```

Update all other places in selector.py that unpack `dur_options` to
handle the new `(dur_indices, cells)` tuple format.  Grep for
`all_durs_by_count` and `dur_options` to find all sites.

Update the import: replace `_cached_validated_pitch` with
`_cached_validated_pitch_for_cells` from pitch_generator.

The `fixed_midi` branch also needs updating — it iterates dur_options
and must unpack `(d_seq, cells)`.

## Constraints

- Do not modify rhythm_cells.py, models.py, contour.py, stretto_gpu.py,
  harmonic_grid.py, melody_generator.py.
- `select_diverse_subjects` and `select_subject` signatures unchanged.
- `GeneratedSubject` unchanged.
- Maintain HEAD_SIZE / MIN_HEAD_FINAL_DUR_TICKS filter in selector.py.
- All laws apply.

## Checkpoint

```
python -c "
from motifs.subject_gen.selector import select_diverse_subjects
results = select_diverse_subjects(n=3, mode='major', verbose=True)
print(f'Selected {len(results)} subjects')
for i, s in enumerate(results):
    print(f'  [{i}] {s.head_name} {len(s.scale_indices)}n score={s.score:.2f}')
"
```

This must complete without errors and produce at least 1 subject.
Report the number of subjects, timing, and any warnings.
