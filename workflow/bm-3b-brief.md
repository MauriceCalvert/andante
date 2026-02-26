# BM-3b — Scoring extension and dead code removal

Read these files first:
- `docs/baroque_melody.md` (§7 step 7, §9)
- `motifs/subject_gen/scoring.py`
- `motifs/subject_gen/constants.py`

## Goal

Add harmonic variety scoring.  Remove dead code left over from the
old head+CP-SAT pipeline.

## Files to modify

### 1. `motifs/subject_gen/constants.py`

Add: `W_HARMONIC_VARIETY: float = 1.0`

### 2. `motifs/subject_gen/scoring.py`

Add a new criterion:

```python
def _harmonic_variety(degrees: tuple[int, ...]) -> float:
    """Score 0-1 for how many distinct chords the degree sequence touches."""
```

Implementation: for each degree in the sequence, compute `degree % 7`
and check membership in each of the four chord-tone sets (I, IV, V, ii
in major — use {0,2,4}, {3,5,0}, {4,6,1}, {1,3,5}).  Count how many
distinct chords have at least one member present.

Score = `(touched - 1) / 3.0` clamped to [0.0, 1.0].  A subject
touching only I scores 0.  One touching all four scores 1.

Update `score_subject` to include the new term.  Max score becomes 6.0.

Update `subject_features` to return a 7th dimension: the harmonic
variety score itself (0–1).

### 3. Delete dead files

- `motifs/subject_gen/head_enumerator.py`
- `motifs/subject_gen/cpsat_generator.py`
- `motifs/subject_gen/cpsat_prototype.py`

Verify no remaining imports reference them.  Run:

```
grep -r "head_enumerator\|cpsat_generator\|cpsat_prototype" motifs/ --include="*.py" -l
```

The only hits should be `__pycache__` files (ignore) or this brief.

## Constraints

- Do not modify selector.py, pitch_generator.py, melody_generator.py,
  harmonic_grid.py, rhythm_cells.py.
- All laws apply.
- Functions sorted alphabetically in scoring.py.

## Checkpoint

```
python -c "
from motifs.subject_gen.scoring import score_subject, subject_features
# Subject touching I and V
s1 = score_subject(degrees=(0, 2, 4, 4, 2, 0, 4, 2, 0, 2), ivs=(2,2,0,-2,-2,4,-2,-2,2), dur_indices=(1,1,1,1,1,1,1,1,1,1))
print(f'Score (I+V): {s1:.2f}')
f1 = subject_features(degrees=(0, 2, 4, 4, 2, 0, 4, 2, 0, 2), ivs=(2,2,0,-2,-2,4,-2,-2,2), dur_indices=(1,1,1,1,1,1,1,1,1,1))
print(f'Features: {len(f1)} dimensions (expect 7)')
assert len(f1) == 7, f'Expected 7 features, got {len(f1)}'
print('OK')
"
```

Then run the full pipeline:

```
python -m scripts.run_pipeline invention neutral -trace
```

Report pipeline completion, subject count, and any errors.

Verify dead code is gone:

```
python -c "
import importlib, sys
for name in ['head_enumerator', 'cpsat_generator', 'cpsat_prototype']:
    try:
        importlib.import_module(f'motifs.subject_gen.{name}')
        print(f'FAIL: {name} still importable')
    except ImportError:
        print(f'OK: {name} removed')
"
```
