# Continue: generated_by tagging + polyphony asserts

## Context

Chat crashed while implementing `generated_by` tagging on all Note creation
sites, plus asserts to catch notes being placed in wrong bar/beat positions
(the root cause of polyphony at bar 2 in fuguec.note).

## Problem

Two generators were writing notes to the same bar/beat/track in bar 2.
The `generated_by` field exists on Note (`builder/types.py:28`, default `""`)
but most creation sites don't set it, making it impossible to trace which
module produced the conflicting notes.

## What's done

These files already stamp `generated_by`:

- `builder/imitation.py` — stamps "subject", "answer", "cs" (via `replace()` at return)
- `builder/cadence_writer.py` — stamps "cadence" (lines 279-280, 524-525)
- `builder/galant/bass_writer.py` — stamps "galant_bass" (line 1060)
- `builder/galant/soprano_writer.py` — stamps "structural" (line 42)
- `viterbi/generate.py` — stamps "viterbi" (last line, via `replace()`)

## What's not done

These files create Note objects without setting `generated_by`:

### Must tag

1. **`builder/hold_writer.py`** — 2 × `Note()` calls (lines 294, 343).
   Tag: `"hold"`

2. **`builder/phrase_writer.py`** — 1 × `Note()` call (line 668, bass in `_write_pedal`).
   Tag: `"pedal"`

3. **`builder/thematic_renderer.py`** — 1 × `Note()` call (line 195, in `_render_episode_fragment`).
   Tag: `"episode_fragment"`

4. **`builder/cadence_writer.py`** — 10 × `Note()` calls (lines 226, 250, 272, 357, 370, 430, 450, 466, 497, 516).
   These are the *creation* sites inside cadence functions. The `replace(..., generated_by="cadence")`
   at lines 279-280 and 524-525 stamps them at return — but only for the two main cadence functions.
   Check whether all paths go through those return stamps. If any `Note()` escapes unstamped, tag it.

5. **`builder/strategies/diminution.py`** — 4 × `Note()` calls (lines 271, 281, 401, 440).
   Tag: `"diminution"`. NOTE: this file appears to be dead code — no import found anywhere
   in the builder. Verify before spending time on it. If dead, delete or ignore.

6. **`builder/galant/bass_writer.py`** — 5 × `Note()` calls (lines 399, 448, 566, 657, 1051).
   The `replace(..., generated_by="galant_bass")` at line 1060 stamps them at return.
   Same question as cadence_writer: do all paths go through that return stamp?
   If yes, already covered. If any early-return or branch escapes, tag at creation.

7. **`builder/galant/soprano_writer.py`** — 1 × `Note()` call (line 36).
   The `replace(..., generated_by="structural")` at line 42 stamps at return. Likely covered.

### Viterbi callers (already covered by viterbi/generate.py stamp)

These call `generate_voice()` which returns notes already stamped `"viterbi"`:
- `builder/bass_viterbi.py`
- `builder/soprano_viterbi.py`
- `builder/cs_writer.py`

No action needed unless they create Notes independently (they don't — verified).

### free_fill.py

Calls `generate_soprano_viterbi` and `generate_bass_viterbi` which return
pre-stamped notes. No `Note()` calls of its own. No action needed.

## Second task: polyphony assert

After tagging, add a polyphony check in `builder/compose.py` at the end of
`compose_phrases()`, before the return. For each voice separately:

```python
def _assert_no_polyphony(notes: tuple[Note, ...], voice_name: str) -> None:
    """Assert no two notes overlap in the same voice."""
    sorted_notes = sorted(notes, key=lambda n: (n.offset, -n.duration))
    for i in range(len(sorted_notes) - 1):
        a = sorted_notes[i]
        b = sorted_notes[i + 1]
        if a.offset + a.duration > b.offset:
            assert False, (
                f"Polyphony in {voice_name}: "
                f"{a.pitch}@{float(a.offset)} dur={float(a.duration)} "
                f"(generated_by={a.generated_by!r}) overlaps "
                f"{b.pitch}@{float(b.offset)} dur={float(b.duration)} "
                f"(generated_by={b.generated_by!r})"
            )
```

Call for both voices before returning the Composition.

## Third task: bar-range assert

In `_write_thematic` in `phrase_writer.py`, after each entry renders notes,
assert that every note's offset falls within the entry's time window
[entry_start_offset, next_entry_start_offset). This catches the forward/backward
shift bug. The assert message must include `generated_by` so the offending
module is immediately identified.

```python
for n in entry_notes:
    assert entry_start_offset <= n.offset < next_entry_start_offset, (
        f"Note outside entry window: offset={float(n.offset)} "
        f"window=[{float(entry_start_offset)}, {float(next_entry_start_offset)}) "
        f"generated_by={n.generated_by!r} pitch={n.pitch}"
    )
```

## Dead code check

`builder/strategies/diminution.py` — no imports found. Likely dead. Verify
with `grep -rn "from builder.strategies" --include="*.py"` and delete if unused.

## After implementation

Run `python scripts/run_pipeline.py briefs/builder` on invention. If the
polyphony assert fires, `generated_by` will identify which two modules
collided at bar 2. Fix the root cause (likely double-rendering from
overlapping entry windows in `_segment_into_entries`).
