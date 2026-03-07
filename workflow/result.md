# Result: BUG-1 — Fix AttributeError: EpisodeDialogue has no _episode_count

## Code Change

**`builder/phrase_writer.py` line 416** — one line:

```python
# Before
ep_label: str = f"episode {get_tracer()._episode_count}"
# After
ep_label: str = f"episode@{entry_first_bar}"
```

`_episode_count` is a private attribute on `Tracer`, not on `EpisodeDialogue`. `entry_first_bar` is already in scope and uniquely identifies each episode by its start bar.

## Chaz checkpoint

Pipeline completed without `AttributeError`. Output: `output\invention.midi`.

Episode lyric labels now read `episode@<bar>` (e.g. `episode@8`), which is sufficient for trace identification and requires no external state.

Please listen to the MIDI and let me know what you hear.
