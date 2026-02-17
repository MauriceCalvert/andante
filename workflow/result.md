# Result: Task D — Parametric contour + pedal descent

## Status: Implementation complete

---

## D1 — Replace Gaussian contour with parametric three-point contour

### Changes made

**`viterbi/mtypes.py`**
Added `ContourShape` frozen dataclass after existing dataclasses:
```python
@dataclass(frozen=True)
class ContourShape:
    start: float = 0.0
    apex: float = 4.0
    apex_pos: float = 0.65
    end: float = 0.0
```
Default values approximate the former Gaussian arc (rise to +4 degrees at 65%, return to 0).

**`viterbi/costs.py`**
Removed `ARC_PEAK_POSITION`, `ARC_SIGMA`, `ARC_REACH`. `COST_CONTOUR` retained.

**`viterbi/pathfinder.py`**
- Removed `import math` (no longer needed).
- Removed `ARC_*` from costs import; added `ContourShape` to mtypes import.
- Replaced `compute_contour_targets` with piecewise-linear implementation:
  - Accepts `contour: ContourShape | None = None` and `key: KeyInfo = CMAJ`.
  - Computes `avg_step = 12 / len(key.pitch_class_set)` for degree→semitone conversion.
  - For `apex_pos <= 0.0`: entire phrase is the descent segment (start → end at p=0 → 1).
  - For `p <= apex_pos`: interpolates start → apex.
  - For `p > apex_pos`: interpolates apex → end.
  - Target = `range_mid + round(offset * avg_step)`, clamped to `[range_low, range_high]`.
- Added `contour: ContourShape | None = None` to `find_path`; passes to `compute_contour_targets`.
- Both soft-only recursive fallback calls in `find_path` now pass `contour=contour`.

**`viterbi/pipeline.py`**
Added `ContourShape` import and `contour: ContourShape | None = None` to `solve_phrase`; passes to `find_path`.

**`viterbi/generate.py`**
Added `ContourShape` import and `contour: ContourShape | None = None` to `generate_voice`; passes to `solve_phrase`.

---

## D2 — Wire pedal to use descending contour

**`builder/soprano_viterbi.py`**
Added `ContourShape` import and `contour: ContourShape | None = None` to `generate_soprano_viterbi`; passes to `generate_voice`.

**`builder/phrase_writer.py`**
Added `ContourShape` import (from `viterbi.mtypes`). In `_write_pedal`, before calling `generate_soprano_viterbi`, creates:
```python
pedal_contour = ContourShape(
    start=3.0,    # 3 degrees above mid
    apex=3.0,     # apex = start → pure ramp
    apex_pos=0.0, # apex at phrase start → immediate descent
    end=-3.0,     # 3 degrees below mid
)
```
Passes `contour=pedal_contour` to `generate_soprano_viterbi`.

---

## Contour mathematics

**Default (ContourShape())**: Rises from 0 to +4 degrees at p=0.65, returns to 0.
With avg_step ≈ 1.71 st/degree: peak is ~+7 semitones above mid. Approximates old Gaussian.

**Pedal (apex_pos=0.0)**: offset = 3.0 − 6.0·p (linear descent).
- p=0.0: +3 degrees (+5 st above mid)
- p=0.5: 0 degrees (at mid)
- p=1.0: −3 degrees (−5 st below mid)

Total swing: ~10 semitones. Acceptance criterion: ≥4 st. Satisfied.

---

## Call chain

```
_write_pedal (phrase_writer.py)
  → generate_soprano_viterbi(contour=pedal_contour)   [soprano_viterbi.py]
    → generate_voice(contour=pedal_contour)             [generate.py]
      → solve_phrase(contour=pedal_contour)             [pipeline.py]
        → find_path(contour=pedal_contour)              [pathfinder.py]
          → compute_contour_targets(contour=..., key=...) [pathfinder.py]
```

All other callers pass `contour=None` → `ContourShape()` → default arc behaviour.

---

## Chaz pre-evaluation

1. Default ContourShape produces targets structurally similar to old Gaussian: rises toward 65%, returns to 0. Coefficient differs (piecewise-linear vs bell) but same shape and magnitude at the peak.
2. Pedal contour with `apex_pos=0.0`: targets are monotonically non-increasing (`offset = 3.0 - 6.0·p`, strictly decreasing). Acceptance criterion satisfied analytically.
3. No new assertion paths added. Existing contour_cost function unchanged. No other Viterbi logic touched.
