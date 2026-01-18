# Treatment Rules: Constraint-Based Planning

## Goal

Replace hardcoded `bar_continuation` cycle with a rule system. Planner selects transforms per bar based on constraints; builder executes what planner decided.

**Current flow (rigid):**
```
brief → planner → plan (phrase treatment only) → builder (hardcoded bar cycle)
```

**Target flow (flexible):**
```
brief → planner (applies rules) → plan (explicit bar transforms) → builder (executes plan)
```

## Files Involved

```
builder/data/treatment_cycles.yaml  — DELETE or gut
data/treatment_rules.yaml           — NEW: constraint definitions
planner/treatment_generator.py      — UPDATE: apply rules per bar
builder/handlers/material_handler.py — UPDATE: read bar transforms from plan
```

## Task 1: Create treatment_rules.yaml

**Location:** `D:\projects\Barok\barok\source\andante\data\treatment_rules.yaml`

```yaml
# Constraints for treatment selection
# Planner picks within bounds; builder executes

# What transforms are compatible with each phrase treatment
compatibility:
  statement:
    allowed: [statement, transposition, head, tail]
    preferred: [transposition]
    forbidden: [inversion, retrograde]
    
  inversion:
    allowed: [inversion, transposition, head]
    preferred: [inversion]
    forbidden: [statement]
    
  sequence:
    allowed: [transposition, head, tail]
    preferred: [transposition]
    forbidden: [retrograde, inversion]
    
  retrograde:
    allowed: [retrograde, transposition, head]
    preferred: [retrograde]
    forbidden: [statement]
    
  stretto:
    allowed: [stretto, head, diminution]
    preferred: [stretto, head]
    forbidden: [augmentation]
    
  augmentation:
    allowed: [augmentation, statement, transposition]
    preferred: [augmentation]
    forbidden: [diminution, stretto]
    
  fragmentation:
    allowed: [head, tail, transposition]
    preferred: [head]
    forbidden: [augmentation]

# Shift bounds by tonal motion
shift_rules:
  ascending:
    min: 0
    max: 4
  descending:
    min: -4
    max: 0
  static:
    min: -2
    max: 2

# Energy modifiers
energy_rules:
  moderate:
    max_shift: 2
    prefer_simple: true
  rising:
    max_shift: 3
    prefer_direction: ascending
  peak:
    max_shift: 4
    allow_extremes: true

# Bar position weights (probabilities, sum needn't be 1)
position_weights:
  bar_0:
    statement: 1.0
    transposition: 0.2
    head: 0.1
  bar_1:
    transposition: 0.8
    head: 0.3
    statement: 0.2
  bar_2:
    transposition: 0.5
    head: 0.5
    tail: 0.2
  bar_3_plus:
    head: 0.7
    tail: 0.3
    transposition: 0.2

# Cadence approach (bars before cadence)
cadence_rules:
  distance_1:
    prefer: [statement, head]
    avoid: [inversion, retrograde]
  distance_2:
    prefer: [transposition]
    shift_toward_tonic: true
```

## Task 2: Create Rule Applier

**Location:** `D:\projects\Barok\barok\source\andante\planner\treatment_rules.py`

Pure functions to select transforms based on rules.

```python
"""Treatment rule application — selects bar transforms from constraints."""
from pathlib import Path
from typing import Any
import yaml

RULES_PATH: Path = Path(__file__).parent.parent / "data" / "treatment_rules.yaml"

def load_rules() -> dict[str, Any]:
    """Load treatment rules from YAML."""
    with open(RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_allowed_transforms(
    phrase_treatment: str,
    rules: dict[str, Any],
) -> list[str]:
    """Get transforms allowed for this phrase treatment."""
    # Parse base treatment from "inversion[circulatio]" -> "inversion"
    base: str = phrase_treatment.split("[")[0]
    compat: dict[str, Any] = rules.get("compatibility", {})
    entry: dict[str, Any] = compat.get(base, compat.get("statement", {}))
    return entry.get("allowed", ["statement"])

def get_preferred_transforms(
    phrase_treatment: str,
    rules: dict[str, Any],
) -> list[str]:
    """Get preferred transforms for this phrase treatment."""
    base: str = phrase_treatment.split("[")[0]
    compat: dict[str, Any] = rules.get("compatibility", {})
    entry: dict[str, Any] = compat.get(base, compat.get("statement", {}))
    return entry.get("preferred", ["statement"])

def get_shift_bounds(
    tonal_direction: str,
    energy: str,
    rules: dict[str, Any],
) -> tuple[int, int]:
    """Get min/max shift for context."""
    shift_rules: dict[str, Any] = rules.get("shift_rules", {})
    direction_entry: dict[str, int] = shift_rules.get(tonal_direction, {"min": -2, "max": 2})
    base_min: int = direction_entry.get("min", -2)
    base_max: int = direction_entry.get("max", 2)
    energy_rules: dict[str, Any] = rules.get("energy_rules", {})
    energy_entry: dict[str, Any] = energy_rules.get(energy, {})
    max_shift: int = energy_entry.get("max_shift", 3)
    return (max(base_min, -max_shift), min(base_max, max_shift))

def get_position_weights(
    bar_index: int,
    rules: dict[str, Any],
) -> dict[str, float]:
    """Get transform weights for bar position."""
    pos_weights: dict[str, Any] = rules.get("position_weights", {})
    if bar_index == 0:
        return pos_weights.get("bar_0", {"statement": 1.0})
    elif bar_index == 1:
        return pos_weights.get("bar_1", {"transposition": 0.8})
    elif bar_index == 2:
        return pos_weights.get("bar_2", {"transposition": 0.5})
    else:
        return pos_weights.get("bar_3_plus", {"head": 0.7})

def select_bar_transform(
    phrase_treatment: str,
    bar_index: int,
    tonal_direction: str,
    energy: str,
    bars_to_cadence: int | None,
    rules: dict[str, Any],
) -> tuple[str, int]:
    """Select transform and shift for one bar.
    
    Returns:
        (transform_name, shift)
    """
    allowed: list[str] = get_allowed_transforms(phrase_treatment, rules)
    preferred: list[str] = get_preferred_transforms(phrase_treatment, rules)
    weights: dict[str, float] = get_position_weights(bar_index, rules)
    
    # Filter weights to allowed transforms
    candidates: dict[str, float] = {
        t: weights.get(t, 0.1) for t in allowed
    }
    # Boost preferred
    for t in preferred:
        if t in candidates:
            candidates[t] *= 1.5
    
    # Cadence approach adjustments
    if bars_to_cadence is not None and bars_to_cadence <= 2:
        cadence_rules: dict[str, Any] = rules.get("cadence_rules", {})
        key: str = f"distance_{bars_to_cadence}"
        if key in cadence_rules:
            for t in cadence_rules[key].get("prefer", []):
                if t in candidates:
                    candidates[t] *= 2.0
            for t in cadence_rules[key].get("avoid", []):
                if t in candidates:
                    candidates[t] *= 0.1
    
    # Pick highest weighted
    transform: str = max(candidates, key=lambda t: candidates[t])
    
    # Select shift
    min_shift, max_shift = get_shift_bounds(tonal_direction, energy, rules)
    # Simple heuristic: bar_index determines magnitude
    if bar_index == 0:
        shift: int = 0
    else:
        shift = max(min_shift, min(max_shift, -bar_index))
    
    return (transform, shift)
```

## Task 3: Update Planner to Generate Bar Transforms

**File:** `D:\projects\Barok\barok\source\andante\planner\treatment_generator.py`

Add function to generate bar-level transforms for each phrase:

```python
def generate_bar_transforms(
    phrase: dict[str, Any],
    phrase_index: int,
    total_phrases: int,
) -> list[dict[str, Any]]:
    """Generate transform specs for each bar in phrase.
    
    Args:
        phrase: Phrase dict with treatment, bars, harmony, energy, cadence
        phrase_index: Position in piece
        total_phrases: Total phrase count
        
    Returns:
        List of {bar_index, transform, shift} dicts
    """
    from planner.treatment_rules import load_rules, select_bar_transform
    
    rules: dict[str, Any] = load_rules()
    bar_count: int = phrase.get("bars", 1)
    treatment: str = phrase.get("treatment", "statement")
    energy: str = phrase.get("energy", "moderate")
    harmony: list[str] = phrase.get("harmony", [])
    cadence: str | None = phrase.get("cadence")
    
    # Determine tonal direction from harmony
    tonal_direction: str = _infer_tonal_direction(harmony)
    
    result: list[dict[str, Any]] = []
    for bar_idx in range(bar_count):
        # Distance to cadence (if this phrase has one)
        bars_to_cadence: int | None = None
        if cadence:
            bars_to_cadence = bar_count - bar_idx
        
        transform, shift = select_bar_transform(
            treatment,
            bar_idx,
            tonal_direction,
            energy,
            bars_to_cadence,
            rules,
        )
        result.append({
            "bar_index": bar_idx,
            "transform": transform,
            "shift": shift,
        })
    
    return result

def _infer_tonal_direction(harmony: list[str]) -> str:
    """Infer direction from harmony progression."""
    if len(harmony) < 2:
        return "static"
    # Simple heuristic based on root motion
    # Could be more sophisticated
    return "descending"  # Most baroque sequences descend
```

**Then update serializer** to include bar transforms in plan YAML:

```yaml
phrases:
  - index: 0
    treatment: inversion[circulatio]
    bars: 2
    bar_transforms:
      - bar_index: 0
        transform: inversion
        shift: 0
      - bar_index: 1
        transform: transposition
        shift: -2
```

## Task 4: Update Builder to Read Bar Transforms

**File:** `D:\projects\Barok\barok\source\andante\builder\handlers\material_handler.py`

Remove hardcoded `BAR_TREATMENT_CYCLE`. Instead:

1. Look for `bar_transforms` in phrase node
2. Find entry matching current `bar_index`
3. Apply that transform and shift

```python
def _get_bar_transform(context: BarContext, node: Node) -> tuple[str, int]:
    """Get transform for this bar from plan, or default."""
    # Walk up to find phrase node
    phrase_node: Node | None = _find_ancestor(node, "phrases")
    if phrase_node is None:
        return ("statement", 0)
    
    # Look for bar_transforms list
    if "bar_transforms" not in phrase_node:
        # Fallback: use phrase treatment for bar 0, statement otherwise
        if context.bar_index == 0:
            return (context.phrase_treatment.split("[")[0], 0)
        return ("statement", 0)
    
    transforms_node: Node = phrase_node["bar_transforms"]
    for child in transforms_node.children:
        if "bar_index" in child:
            idx: int = child["bar_index"].value
            if idx == context.bar_index:
                transform: str = child["transform"].value if "transform" in child else "statement"
                shift: int = child["shift"].value if "shift" in child else 0
                return (transform, shift)
    
    return ("statement", 0)
```

## Task 5: Update tree_reader to Extract Bar Transforms

**File:** `D:\projects\Barok\barok\source\andante\builder\adapters\tree_reader.py`

Add to `BarContext`:
```python
bar_transform: str | None = None
bar_shift: int = 0
```

Extract from tree in `extract_bar_context()`.

## Task 6: Delete or Simplify treatment_cycles.yaml

**File:** `D:\projects\Barok\barok\source\andante\builder\data\treatment_cycles.yaml`

Either delete entirely or reduce to just `treatment_mapping` if still needed:

```yaml
# Mapping from plan treatment names to transforms.yaml names
treatment_mapping:
  statement: statement
  transposition: transposition
  inversion: inversion
  retrograde: retrograde
  head: head
  tail: tail
  stretto: stretto
  augmentation: augmentation
  diminution: diminution
```

## Testing

After changes:

```
cd D:\projects\Barok\barok\source\andante
python -m scripts.run_builder freude_invention.brief -v
```

Check `output/builder/freude_invention.plan.yaml`:
- Each phrase should have `bar_transforms` list
- Transforms should vary based on phrase treatment, not arbitrary cycle

Check `.note` output:
- Bar 0 and bar 1 should differ
- Differences should relate to phrase treatment (inversion stays inverted, etc.)

## Coding Standards

- Pure functions in `planner/treatment_rules.py`
- Type hints on all parameters
- Assert preconditions
- No blank lines inside functions
- ≤100 lines per module

## Summary

| File | Action |
|------|--------|
| `data/treatment_rules.yaml` | CREATE — constraint definitions |
| `planner/treatment_rules.py` | CREATE — rule application functions |
| `planner/treatment_generator.py` | UPDATE — call rule applier |
| `planner/serializer.py` | UPDATE — emit bar_transforms |
| `builder/adapters/tree_reader.py` | UPDATE — extract bar_transform |
| `builder/handlers/material_handler.py` | UPDATE — use plan transforms |
| `builder/data/treatment_cycles.yaml` | DELETE or gut |
