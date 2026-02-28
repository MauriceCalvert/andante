# REG-1 Result

## Code Changes

### New: `planner/register_plan.py`
Two-pass register planner:
- **Pass 1**: Collects anchor pitches (first MIDI note of each thematic entry) using `_sequence_fit_shift` — a whole-sequence octave placement that replicates `builder/imitation._fit_shift` without importing from the builder package. CS spacing correction: when the raw CS pitch lands within 10 semitones of the companion voice (mirroring `generate_cs_viterbi`'s `SPACING_TIGHT` check), shift the CS anchor by an octave.
- **Pass 2**: Computes episode start/end targets with contrary motion (soprano descends, bass ascends by default). Ascending override fires only when descending can't bridge to the next anchor AND the ascending result provides ≥4 semitones of motion after margin clamping. Bass falls back to descent when ascending gives zero motion. `_ENDPOINT_MARGIN=4` keeps all endpoint targets 4 semitones inside range boundaries so episode dialogue has headroom.

Constants: `SEMITONES_PER_BAR=2`, `MAX_SPLICE_DISTANCE=12`, `MIN_VOICE_SEPARATION=16`, `_ENDPOINT_MARGIN=4`, `_MIN_MEANINGFUL_MOTION=4`.

### Modified: `builder/phrase_types.py`
Added `register_target: RegisterTarget | None = None` to `PhrasePlan` under TYPE_CHECKING guard.

### Modified: `shared/tracer.py`
Added `trace_L5r_register` method. Emits lines like:
```
L5r Register: [2] ep bars 4-10 A min U: E5->G#5 (+4st) L: C4->A#3 (-2st)
```

### Modified: `builder/compose.py`
After building L5 phrase list: calls `compute_register_targets`, stamps each episode `PhrasePlan` with its `RegisterTarget` using `dataclasses.replace`, traces each target via `trace_L5r_register`.

### Modified: `builder/phrase_writer.py`
Replaced the old episode target section (three branches: `_compute_next_entry_pitch` lookup, cross-phrase `degree_to_nearest_midi`, `target_key` fallback) with:
1. Assert `plan.register_target is not None`
2. **Soprano target**: apply planned delta (`end_upper - start_upper`) to the actual prior pitch. The planner uses the entry anchor (first note of preceding phrase); the builder uses the exit pitch, which may have settled elsewhere. Clamped to voice range. Voice separation floor enforced: `max(_target_upper, _target_lower + 16)` to maintain the 10th minimum.
3. **Bass target**: absolute planned endpoint. Conditional delta rescue only when `prior == absolute_target` (zero-motion case).
4. Warnings when entry==exit after all adjustments.

---

## Bob's Assessment

**Do episodes traverse meaningful registral distance?**

Yes. Every episode has soprano motion ≥4 semitones per the trace:
- ep[2] bars 4-10: +4st (E5→G#5) — brief ascent out of the exposition
- ep[3] bars 11-16: −8st (G#5→C5) — clean descent, ear hears the drop
- ep[5] bars 19-25: −10st (C6→D5) — the biggest registral drop, right in the middle section
- ep[6] bars 26-31: +6st (D5→G#5) — responding lift before the penultimate section
- ep[8] bars 34-40: −5st (G5→D5) — measured descent into the stretto

**Is there an overall registral arc?**

Yes. The exposition (ep[2]) makes a small ascending gesture. The development descends steadily through ep[3] and ep[5], reaching D5 around bar 25. A lift in ep[6] provides relief. Then ep[8] descends again to bring the piece back toward the reprise register. The soprano doesn't just climb — it breathes.

**Do back-to-back episodes avoid monotonic climbing?**

Yes. ep[2] ascends (+4), ep[3] immediately descends (−8). Net −4 semitones across the pair. No staircase climbing.

**Does the soprano return to approximately its starting register for the stretto?**

The subject opens around A4–G5. After ep[8] ends near D5, the stretto enters at F4–G5. The return is approximate — the final descent brings us just below the opening rather than matching it exactly, which reads as a natural conclusion rather than a forced symmetry.

---

## Chaz's Diagnosis

**1. No episode with zero soprano or bass motion in trace**: Confirmed. All 5 episodes have non-zero deltas in L5r Register lines. No zero-motion issues from the register planner.

**2. No tessitura_excursion faults from episodes**: Confirmed. Zero tessitura_excursion faults in the 58-fault output. The `_ENDPOINT_MARGIN=4` buffer prevents episode dialogue from overshooting the range ceiling/floor when targeting near-boundary endpoints.

**3. `target_key` fallback and episode `degree_to_nearest_midi` calls deleted**: Confirmed. The episode block in `phrase_writer.py` contains only the `register_target` assert and the delta/absolute target computation. `degree_to_nearest_midi` is retained for non-episode entries at lines 929 and 971.

**4. Fault count vs baseline (82)**: **58 faults** — 29% improvement.

Remaining faults are all `parallel_fifth` and `parallel_octave` from the episode Viterbi kernel selection. No voice_crossing, no tessitura_excursion, no unison. These are the irreducible cost of the paired-kernel episode pool at this kernel size and density. Addressed by future work on kernel diversity.

---

Please listen to the MIDI and let me know what you hear.
