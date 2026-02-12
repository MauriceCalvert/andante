## Task: V0a — Rename splines→viterbi and remove diagnostic prints

Read these files first:
- `viterbi/mtypes.py`
- `viterbi/scale.py`
- `viterbi/corridors.py`
- `viterbi/costs.py`
- `viterbi/pathfinder.py`
- `viterbi/pipeline.py`
- `viterbi/demo.py`
- `viterbi/test_brute.py`
- `viterbi/midi_out.py`
- `viterbi/__init__.py`
- `viterbi/_readme.md`

### Goal

Two mechanical changes:

**1. Rename all `splines` references to `viterbi`.**

Every file in `viterbi/` currently imports from `splines.xxx` (e.g.
`from splines.scale import ...`). The directory is already called `viterbi`.
Change every `splines` import, module reference, docstring mention, and
`python -m splines.xxx` invocation to use `viterbi` instead.

Specifically:
- All `from splines.xxx import` → `from viterbi.xxx import`
- All `import splines.xxx` → `import viterbi.xxx`
- The `python -m splines.demo` instruction in demo.py docstring → `python -m viterbi.demo`
- The `python -m splines.test_brute` instruction in test_brute.py docstring → `python -m viterbi.test_brute`
- The `__init__.py` comment: update to mention viterbi not spline
- The `_readme.md` title: change "Splines" to "Viterbi" (keep subtitle)

Do NOT rename the directory itself — it is already `viterbi/`.

**2. Remove all print statements except minimal diagnostics.**

Strip every `print()` and `print_xxx()` function from the production path.
The only prints that survive are:

- In `pathfinder.py`: the `_print_path` function stays but is only called
  when `verbose=True`. Keep it — it's the primary diagnostic tool.
- In `pipeline.py`: `_print_phrase_summary` stays (same rule, verbose only).
  The warning print in `_validate_knots` stays (it flags genuine problems).
  Remove `print_corridors` call in `solve_phrase`.
- In `corridors.py`: delete the entire `print_corridors` function.
- In `demo.py`: the `_describe_inputs` print function stays (it documents
  what the demo does). Remove any other bare prints.
- In `midi_out.py`: remove the "MIDI written to" print and the
  "midiutil not installed" print (return empty string silently, or raise).
- In `test_brute.py`: keep the progress/result prints (they're test output).

Default `verbose=False` in `solve_phrase` and `find_path` signatures.
The demo explicitly passes `verbose=True`.

### Files to modify

All `.py` files in `viterbi/`. Also `_readme.md` and `__init__.py`.

### Constraints

- Do not change any algorithm logic, cost weights, or data types.
- Do not rename the `viterbi/` directory.
- Do not add any new files.
- Verify all internal imports resolve correctly after renaming.

### Checkpoint

Run `python -m viterbi.demo 1` from the andante directory. It must
produce output without ImportError. Run `python -m viterbi.test_brute 5 20`
— all trials must pass. Confirm verbose output appears only when
`verbose=True`.
