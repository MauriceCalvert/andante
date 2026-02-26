# BM-3b Result

## Changes made

### `motifs/subject_gen/constants.py`
- Added `W_HARMONIC_VARIETY: float = 1.0`

### `motifs/subject_gen/scoring.py`
- Added `_harmonic_variety(degrees)`: computes `degree % 7` for each pitch,
  intersects with chord-tone sets for I ({0,2,4}), IV ({3,5,0}), V ({4,6,1}),
  ii ({1,3,5}); score = `(touched - 1) / 3.0` clamped to [0, 1]
- Functions reordered alphabetically: `_direction_commitment`, `_harmonic_variety`,
  `_intervallic_range`, `_repetition_penalty`, `_rhythmic_contrast`, `_signature_interval`
- `score_subject`: includes `W_HARMONIC_VARIETY * _harmonic_variety(degrees)`;
  docstring updated to "Returns 0–6"
- `subject_features`: 7th dimension added (`f_harmonic_variety`);
  docstring updated to "7D feature vector"

### Dead files deleted
- `motifs/subject_gen/head_enumerator.py`
- `motifs/subject_gen/cpsat_generator.py`
- `motifs/subject_gen/cpsat_prototype.py`

No import references remain (the one hit in `melody_generator.py` is a
comment in the module docstring, not an import statement).
