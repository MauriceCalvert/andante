## Task: V1 — Key-aware pitch sets and step distances

Read these files first:
- `viterbi/scale.py`
- `viterbi/corridors.py`
- `viterbi/pipeline.py`
- `viterbi/demo.py`
- `shared/key.py`

### Goal

The prototype is hardcoded to C major. Generalise it to accept any key
so it can process real music in arbitrary keys.

### Implementation

**scale.py:**

Add a `KeyInfo` dataclass (lightweight, no dependency on the real Key class):

```python
@dataclass(frozen=True)
class KeyInfo:
    """Minimal key representation for the viterbi solver."""
    pitch_class_set: frozenset[int]   # e.g. {0,2,4,5,7,9,11} for C major
    tonic_pc: int                      # e.g. 0 for C
```

Add a factory:

```python
CMAJ = KeyInfo(pitch_class_set=frozenset({0, 2, 4, 5, 7, 9, 11}), tonic_pc=0)
```

Change `build_pitch_set` signature:

```python
def build_pitch_set(low_midi: int, high_midi: int, key: KeyInfo = CMAJ) -> list[int]:
```

Filter by `key.pitch_class_set` instead of `CMAJ_OFFSETS`.

Change `scale_degree_distance` signature:

```python
def scale_degree_distance(pitch_a: int, pitch_b: int, key: KeyInfo = CMAJ) -> int:
```

Count pitches whose `midi % 12` is in `key.pitch_class_set` between the
two pitches.

Change `is_diatonic`:

```python
def is_diatonic(midi: int, key: KeyInfo = CMAJ) -> bool:
```

Keep `CMAJ_OFFSETS` as a module constant for backward compatibility but
mark it as deprecated. All actual logic uses `KeyInfo`.

`is_consonant`, `is_perfect`, `interval_name` are key-independent
(semitone-based) — leave unchanged.

**corridors.py:**

`build_corridors` gains a `key` parameter (default `CMAJ`), passes it
through to `build_pitch_set`.

**costs.py:**

`step_cost` and `scale_degree_distance` calls gain `key` parameter.
Thread `key` through `transition_cost` signature (default `CMAJ`).

**pathfinder.py:**

`find_path` gains a `key` parameter (default `CMAJ`), threads it to
`transition_cost` calls. `scale_degree_distance` calls in `_print_path`
gain `key`.

**pipeline.py:**

`solve_phrase` gains a `key` parameter (default `CMAJ`), passes to
`build_corridors` and `find_path`.

**demo.py:**

All existing examples continue to work unchanged (C major default). Add
one call variant that explicitly passes `CMAJ` to verify the parameter
threads correctly.

### Constraints

- Default `CMAJ` everywhere — existing code and tests must work without
  modification.
- Do not import from `shared/key.py`. The `KeyInfo` dataclass is local
  to the viterbi package. Integration with the real Key class happens in
  V4.
- Do not change any cost weights or algorithm logic.

### Checkpoint

Run `python -m viterbi.demo`. All examples produce identical output
(same paths, same costs) as before V1. Run `python -m viterbi.test_brute 5 20`
— all pass.
