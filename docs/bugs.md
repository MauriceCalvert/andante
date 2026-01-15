# Andante Bug Tracking

**This file must always be kept up to date.** Document all bugs discovered and their fixes here.

---

## Fixed Bugs

### BUG-001: Parallel fifths/octaves in 4-voice polyphonic textures

**Date:** 2026-01-09

**Symptom:** 4-voice polyphonic pieces failed guard checks with parallel fifths/octaves between inner voices and outer voices.

**Root cause:** Two separate code paths existed for inner voice resolution:
- `_fill_inner_with_chords()` for homophonic texture - used slice solver with proper `filter_candidates()`
- `_adjust_voice_leading()` for polyphonic texture - bypassed constraint filtering, only did octave displacement

The polyphonic path did not use the slice solver's `filter_candidates()` function, which checks for parallel motion against all previously-placed voices. When thematic material in inner voices moved in parallel with outer voices (same scale degrees), the octave-only adjustment could not resolve the parallels.

**Fix:** Unified both paths into a phrase-level branch-and-bound search (`_branch_and_bound_search()`) that evaluates full phrase combinations. The only difference is candidate generation:
- Polyphonic: `get_thematic_candidates()` generates octave variants of thematic pitch, filtered by `filter_candidates()`, with chord-tone fallback if all variants rejected
- Homophonic: `get_inner_voice_candidates()` generates chord tones directly

Both paths now use the same constraint filtering (steps 2-3 in the architecture), matching the design principle: "Steps 2-3 are identical regardless of texture."

**Files changed:**
- `engine/slice_solver.py` - Added `get_thematic_candidates()`
- `engine/inner_voice.py` - Replaced legacy slice-by-slice resolution with phrase-level `_branch_and_bound_search()`

**Verification:** `four_voice_allegro.yaml` exercise now passes without parallel motion blockers.

---

### BUG-002: Broken backtracking for inner voice parallel motion

**Date:** 2026-01-09

**Symptom:** `run_exercises.py` failed with "Guard check failed: 7 blocker(s)" due to parallel octaves/fifths. The backtracking mechanism ran 1000 iterations without finding a solution.

**Root cause:** Two-part failure:

1. **Flat proposal mechanism instead of proper backtracking.** The `proposal_index` was a single integer incremented uniformly. At each slice, candidate selection used `proposal_index % len(candidates)`. This meant proposals 0, 3, 6, 9... all picked the same candidate when there were 3 candidates. The mechanism cycled through the same small set of choices rather than exploring the combinatorial space.

   Proper backtracking requires: each slice has its own choice index. When a failure occurs at slice K, increment K's index and reset slices K+1..N to 0. If K exhausts all candidates, backtrack to K-1.

2. **Architecture mismatch between slice solver and guards.** The slice solver checked parallels slice-by-slice at every attack point. Guards checked at COMMON offsets per voice pair. When one voice sustained while another attacked, the timelines diverged. The slice solver would update `prev_pitches` at the sustaining voice's attack, but guards checked at the attacking voice's offset where the sustain was still active.

   Rather than try to reconcile these models, the fix separated concerns:
   - **Inner-to-outer parallels:** Filter at candidate generation time (deterministic, well-defined since outer voices are fixed)
   - **Inner-to-inner parallels:** Handle via guards + backtracking (post-hoc)

3. **Missing fallback to chord tones.** When all thematic octave variants created parallels with outer voices, `get_thematic_candidates()` returned them anyway (via the crossing-only fallback). The proper behavior is to fall back to chord tones when thematic material is incompatible.

**Fix:** Three-part solution:

1. **Proper backtracking in `add_inner_voices_with_backtracking()`:**
   - Each slice has its own `choice_indices[slice_idx]`
   - On guard failure, map violation offset to slice index
   - Increment failing slice's choice, reset subsequent slices to 0
   - If slice exhausts candidates, backtrack to previous slice
   - Track actual `candidate_counts` per slice for accurate exhaustion detection

2. **Inner-to-outer parallel filtering in `filter_candidates()`:**
   ```python
   def creates_outer_parallel(c: int) -> bool:
       # For each outer voice (soprano idx=0, bass idx=voice_count-1)
       # Check if candidate creates parallel 5th/8ve with that outer voice
       # Using prev_inner, prev_outer, candidate, curr_outer
   ```
   This is well-defined because outer voice pitches are fixed before inner voice resolution.

3. **Chord tone fallback in `get_thematic_candidates()`:**
   ```python
   # If filtered == crossing_only, all candidates create parallels
   if filtered and filtered != crossing_only:
       return rank_candidates(filtered, ...)
   # Fall back to chord tones
   return get_inner_voice_candidates(...)
   ```

**Architecture after fix:**

| Check | When | Mechanism |
|-------|------|-----------|
| Voice crossing | Candidate generation | `filter_candidates()` |
| Inner-to-outer parallel | Candidate generation | `filter_candidates()` |
| Inner-to-inner parallel | Post-generation | Guards + backtracking |

The slice solver no longer attempts to check inner-to-inner parallels. This avoids the timeline mismatch issue entirely.

**Files changed:**
- `engine/inner_voice.py` - Added `add_inner_voices_with_backtracking()`, `_branch_and_bound_search()`, `_make_phrase_with_voices()`
- `engine/slice_solver.py` - Updated `filter_candidates()` to check inner-to-outer parallels, updated `get_thematic_candidates()` to properly fall back to chord tones
- `engine/expander.py` - Uses `add_inner_voices_cpsat()` which falls back to `add_inner_voices_with_backtracking()`

**Verification:** All exercises pass. All phrases solve with 0-3 backtracks (previously exhausted at 1000).

**Key insight:** Backtracking is not "try random variations" - it's systematic exploration of a choice tree. Each choice point needs its own index that can be incremented independently when that choice fails.

---

## Open Bugs

(none)

---

## Architectural TODOs

### TODO-001: Replace voice indices with named roles

**Priority:** High (interface design issue)

**Current state:** Voices are identified by integer indices with implicit semantics:
- Score order: 0=soprano, 1=alto, 2=tenor, 3=bass
- Generation order: soprano first, bass second, then inner voices

This creates problems:
1. Magic index arithmetic throughout (`voice_count - 1` for bass)
2. Breaks for >4 voices (what's index 4? 5?)
3. Conflates two unrelated orderings (score display vs generation dependency)

**Proposed fix:** Use named roles instead of indices:

```python
@dataclass
class VoiceResult:
    role: str  # "soprano", "bass", "alto", "tenor", "inner_1", etc.
    pitches: list[Pitch]
    durations: list[Fraction]
```

**Internal generation order** (matches dependency chain):
- 0: soprano (fixed - defines melody)
- 1: bass (fixed - defines harmony)
- 2+: inner voices (searched - fit soprano+bass)

**Output mapping:** Realiser maps roles to score positions based on output format (SATB for choral, treble/bass for keyboard).

**Benefits:**
- No magic index arithmetic
- Scales to any voice count
- Clear separation: generation order vs display order
- Self-documenting code

**Files affected:**
- `VoiceMaterial` / `ExpandedVoices` - role field instead of voice_index
- `inner_voice.py` - generation-order indexing
- `slice_solver.py` - voice range lookups by role
- `realiser.py` - role-to-score-position mapping
- Tests throughout

**Scope:** Significant refactor across entire pipeline.

---

### TODO-002: Support chromatic alterations in schema degrees

**Priority:** Medium (limits schema expressiveness)

**Current state:** `soprano_degrees` and `bass_degrees` in schemas are plain integers (1-7), representing diatonic scale degrees. No way to specify chromatic alterations like ♭7 or ♯7.

**Problem:** Schemas like Quiescenza require chromatic motion (♭7 → 6 → ♯7 → 1). Currently approximated with diatonic 7, losing the characteristic semitone inflections.

**Proposed fix:** Extend degree notation:
- `7` = diatonic 7th (leading tone in major, subtonic in minor)
- `b7` or `-7` = lowered 7th
- `#7` or `+7` = raised 7th (rare, but possible in minor)

Alternatively, use a modifier syntax: `{"degree": 7, "alter": -1}` for ♭7.

**Files affected:**
- `data/schemas.yaml` - degree notation
- `engine/schema.py` - parsing and pitch resolution
- `shared/pitch.py` - chromatic offset handling

**Source:** Gjerdingen, "Music in the Galant Style" — Quiescenza and other schemas require chromatic voice-leading.
