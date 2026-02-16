## Task: F3 — Fragen as a stateful class

Read these files first:
- motifs/fragen.py (all public functions and data types)
- builder/phrase_writer.py (the EPISODE branch in _write_thematic, and _build_fragen_catalogue)
- builder/compose.py (to understand where per-composition state lives)

### Musical Goal

All three episodes in the invention use the identical fragment. The ear
hears the same two bars pasted three times — no variety, no development,
no sense of the music going anywhere. Episodes should use different
fragments, or at minimum different transpositions and voicings, so each
episode sounds like a fresh conversation derived from the subject.

### Idiomatic Model

**What the listener hears:** Each episode is a brief dialogue where one
voice leads with a subject-derived motive and the other responds. Across
the piece, episodes vary: the first might use the subject's head in the
soprano over a running bass; the second might invert the leader, or use
the tail instead; the third might return to the head but in a new register
or with the voices exchanged. The listener recognises the subject material
in each episode but hears variety and development.

**What a competent musician does:** A keyboard player improvising a
two-part invention draws from a small vocabulary of subject-derived cells
but deploys them differently each time. The primary variety mechanism is
fragment selection — different cells from the subject in different episodes.
Secondary variety comes from leader-voice alternation (soprano leads one
episode, bass the next). The musician avoids repeating the same fragment
verbatim.

**Rhythm:** Preserved from the fragment catalogue. Episodes provide
rhythmic contrast to the surrounding subject entries (slow thirds vs fast
running sixteenths, or vice versa). The variety between episodes adds
further rhythmic interest.

**Genre character:** Invention — episodes are breathing spaces between
subject entries. They should feel lighter, more playful, less rhetorical
than the entries. But each should have its own character.

**Phrase arc:** Within a 2-bar episode, the first bar states the fragment
and the second steps it down (sequence). Across the piece, later episodes
can intensify — tighter intervals, faster cells, more chromatic.

### What Bad Sounds Like

- **Carbon-copy episodes (current state):** Three identical episodes.
  The ear stops listening. No development, no variety. (Principle 9 —
  absence of error is not presence of music.)
- **Uniform behaviour:** Same fragment, same leader voice, same register
  in every episode. (Principle 5 — same behaviour at all phrase positions.)

### Known Limitations

1. **Soprano-led fragments may not exist.** The current call_response
   subject produces mostly bass-led fragments. If the catalogue has no
   soprano-led candidates, F3 cannot create them — it can only report the
   gap. The fragment extraction algorithm (extract_cells, build_chains)
   would need reform to produce soprano-range material, which is out of
   scope.

2. **Proximity at entry — FIXED THIS PHASE.** `_find_start` currently
   maximises range margin, using proximity only as tiebreaker on equal
   margin. A candidate with margin 15 / proximity 12 beats margin 8 /
   proximity 2. The musician doesn't care about being centred; they care
   about smooth connection to the preceding material.

   **What the code does now:** Selects the candidate with the largest
   minimum distance from any range boundary. Proximity breaks ties only.

   **What a musician would do:** Pick any start that keeps the voices
   comfortably inside the range, then optimise for stepwise connection
   to whatever came before.

   **Fix:** Threshold-gate the margin, then select by proximity. Add
   constant `_MIN_RANGE_MARGIN = 3` (semitones — a minor 3rd from any
   range edge is ample room). Any candidate with margin >= threshold
   qualifies. Among qualifying candidates, pick the one with smallest
   proximity to `prefer_upper_pitch` / `prefer_lower_pitch`. If no
   preferred pitches are given, fall back to margin-maximisation as now.
   See Implementation §4a.

3. **Cross-relation at boundaries — FIXED THIS PHASE.** `_find_start`
   already computes the first upper and lower MIDI pitches for the
   proximity calculation. It just needs to check those pitch classes
   against `prefer_upper_pitch` / `prefer_lower_pitch` for cross-relation
   pairs and reject offending candidates.

   **What the code does now:** Cross-relations are checked within a
   fragment (in `_consonance_score`) but not between the fragment's first
   notes and the preceding material's last notes.

   **What a musician would do:** Before starting an episode, glance at
   the last note in each voice and avoid chromatic clashes (F# against
   F♮, C# against C♮) at the join.

   **Fix:** In `_find_start`, after computing the first upper/lower MIDI
   pitches (already done for proximity), check each against the
   corresponding `prefer_*_pitch` for membership in
   `CROSS_RELATION_PAIRS`. If either pair matches, reject the candidate
   (`ok = False`). Also check cross-voice: first upper vs prior lower,
   first lower vs prior upper. See Implementation §4b.

4. **Beat-1 gap — FIXED THIS PHASE.** When `fragment.offset > 0`, the
   follower voice starts late in every iteration, leaving a silent gap of
   `offset` duration at each iteration boundary (e.g. beat 1 of bar 2
   in a 2-bar episode with offset = 1/4).

   **What the code does now:** `_emit_notes` calls `_emit_voice_notes`
   with `time_offset=fragment.offset` for every iteration. Iteration 0
   is correct (staggered entry). Iteration 1+ produces a gap between
   the end of the previous iteration's follower and the start of the
   next.

   **What a musician would do:** The follower sustains its last note
   through the boundary until the next cell begins — no silence.

   **Fix:** In `_emit_notes`, after generating all notes, run a gap-fill
   pass per voice. For each voice, sort notes by offset. Where
   `notes[i+1].offset > notes[i].offset + notes[i].duration`, extend
   `notes[i].duration` to close the gap. The extension is always exactly
   `fragment.offset` (typically 1/8 or 1/4) — musically natural as a
   sustained tone at the phrase boundary. See Implementation §4c.

### Implementation

**Two files: motifs/fragen.py and builder/phrase_writer.py.**

**1. motifs/fragen.py — Add FragenProvider class**

Create a class that owns the fragment catalogue and manages selection state:

```
class FragenProvider:
    """Stateful episode fragment provider.
    
    Created once per composition. Tracks which fragments have been used
    to ensure variety across episodes.
    """
    
    def __init__(self, fugue: LoadedFugue, bar_length: Fraction):
        # Build catalogue once
        cells = extract_cells(fugue=fugue, bar_length=bar_length)
        chains = build_chains(cells=cells, bar_length=bar_length)
        fragments = build_fragments(
            cells=chains,
            tonic_midi=fugue.tonic_midi,
            mode=fugue.subject.mode,
            bar_length=bar_length,
        )
        self._catalogue: list[Fragment] = dedup_fragments(fragments=fragments)
        self._used_indices: set[int] = set()
        self._use_count: dict[int, int] = {}  # index -> times used
    
    @property
    def catalogue_size(self) -> int:
        return len(self._catalogue)
    
    def get_fragment(
        self,
        leader_voice: int,
        step: int,
    ) -> Fragment | None:
        """Select a fragment, preferring unused ones.
        
        Selection priority:
        1. Unused fragment matching leader_voice
        2. Least-used fragment matching leader_voice
        3. Unused fragment with any leader (if no match)
        4. None (if catalogue is empty)
        """
        # ... implementation follows priority above
```

Key design:
- `_used_indices` tracks which fragments have been selected (never resets)
- When all matching fragments are used, pick the least-used one
  (via `_use_count`)
- This guarantees variety: with N distinct fragments, the first N
  episodes will all be different
- The class is a plain object, no module-level state, no side effects
  beyond its own tracking

**2. builder/phrase_writer.py — Use FragenProvider**

Remove:
- `_build_fragen_catalogue` function
- `fragen_catalogue` and `used_fragen_indices` local variables in
  `_write_thematic`
- Fragen-related imports that move to the class

Add:
- `fragen_provider: FragenProvider | None` parameter to `_write_thematic`
- In the EPISODE branch, call `fragen_provider.get_fragment(leader, step)`
- The provider is passed in from `write_phrase`, which receives it from
  `compose.py`

**3. Caller chain (compose.py → write_phrase → _write_thematic)**

Add `fragen_provider` parameter to `write_phrase`. In `compose.py`, create
one `FragenProvider` instance when a fugue is loaded, pass it through all
`write_phrase` calls. This is how per-composition state reaches the
episode renderer without module-level globals.

**4. Fixes for Known Limitations 2–4 (motifs/fragen.py)**

**4a. Proximity-first start selection (`_find_start`)**

Add constant:
```
_MIN_RANGE_MARGIN: int = 3  # semitones from range edge to qualify
```

Replace the selection logic at the end of the candidate loop. Current code:
```python
        if (margin > best_margin or
                (margin == best_margin and proximity < best_proximity)):
            best_margin = margin
            best_proximity = proximity
            best = candidate
```

New logic: two-pass selection. First collect all in-range candidates with
their margin and proximity. Then:
- If any preferred pitch is given: among candidates with
  `margin >= _MIN_RANGE_MARGIN`, pick smallest proximity. If no candidate
  meets the threshold, fall back to the candidate with the largest margin
  (current behaviour).
- If no preferred pitches: pick largest margin (current behaviour).

This is cleanest as a post-loop sort rather than inline tracking. Collect
a list of `(candidate, margin, proximity)` tuples, then select after the
loop.

**4b. Cross-relation rejection at boundaries (`_find_start`)**

Inside the candidate loop, after computing `first_upper_midi` and
`first_lower_midi` (already done for proximity), add:

```python
# Reject candidates that create cross-relations with prior material
if prefer_upper_pitch is not None:
    for first, prior in (
        (first_upper_midi, prefer_upper_pitch),
        (first_lower_midi, prefer_upper_pitch),
    ):
        pair = (min(first % 12, prior % 12), max(first % 12, prior % 12))
        if pair in CROSS_RELATION_PAIRS:
            ok = False
if prefer_lower_pitch is not None and ok:
    for first, prior in (
        (first_lower_midi, prefer_lower_pitch),
        (first_upper_midi, prefer_lower_pitch),
    ):
        pair = (min(first % 12, prior % 12), max(first % 12, prior % 12))
        if pair in CROSS_RELATION_PAIRS:
            ok = False
```

This checks all four boundary pairs: upper→upper, lower→lower (same-voice),
and upper→lower, lower→upper (cross-voice). Any cross-relation rejects the
candidate.

**4c. Gap-fill in `_emit_notes`**

After the iteration loop generates all notes, add a gap-fill pass:

```python
# Fill inter-iteration gaps per voice
for voice in (VOICE_SOPRANO, VOICE_BASS):
    voice_indices = [i for i, n in enumerate(notes) if n.voice == voice]
    voice_indices.sort(key=lambda i: notes[i].offset)
    for j in range(len(voice_indices) - 1):
        curr_idx = voice_indices[j]
        next_idx = voice_indices[j + 1]
        curr = notes[curr_idx]
        nxt = notes[next_idx]
        gap = nxt.offset - (curr.offset + curr.duration)
        if gap > Fraction(0):
            notes[curr_idx] = Note(
                offset=curr.offset,
                degree=curr.degree,
                duration=curr.duration + gap,
                voice=curr.voice,
            )
```

Note is a NamedTuple so replacement is via construction, not mutation.
The gap is always exactly `fragment.offset` for follower-voice inter-iteration
boundaries; the upper voice has no gaps (offset=0). The pass is harmless for
gapless voices.

### Constraints

- Do not modify fragen.py's existing functions (extract_cells, build_chains,
  build_fragments, dedup_fragments, realise_to_notes). The class wraps them.
- Do not add module-level state to fragen.py.
- Do not change the Fragment dataclass.
- grep for all callers of write_phrase before adding the parameter, to
  ensure no call site is missed.

### Checkpoint (mandatory)

Run pipeline on seeds 1–10. For each seed:
- Count how many distinct fragments are used across the piece's episodes.
  Log fragment selection.
- For each episode entry, log the leap (semitones) between the prior
  material's last pitch and the episode's first pitch, per voice.
- Check for cross-relations at episode boundaries (pitch class pairs).
- Check for silent gaps at beat 1 of bar 2+ in episodes.

Bob:
1. Do the three episodes sound different from each other? Different
   rhythmic profile, different register, different leader voice?
2. Does each episode still sound like subject-derived material?
3. Are the joins smooth — no jarring leaps into episodes?
4. Any cross-relation clashes at episode boundaries?
5. Any silence mid-episode where a voice drops out?
6. What's still wrong?

Chaz:
For each of Bob's complaints, trace to a code location and propose a fix.

### Acceptance Criteria

- FragenProvider is a class in motifs/fragen.py, not a module-level
  singleton
- No episode fragment index is repeated until all matching candidates are
  exhausted
- All 8 genres pass test suite
- All 10 seeds produce output without assertion errors
- At least 2 distinct fragments used across 3 episodes in seed 42
  (proxy — Bob's ear is the test)
- Episode entry leaps ≤ 7 semitones (a fifth) in at least 8/10 seeds
  (proxy — smooth connection is the test)
- Zero cross-relations at episode boundaries across all 10 seeds
- Zero beat-1 gaps in episodes across all 10 seeds
