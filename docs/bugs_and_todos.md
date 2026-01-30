# Andante: Bugs, Fixes, and TODOs

Single source of truth for all bugs, planned fixes, and future work.

---

# Part 1: Fixed Bugs

## BUG-001: Parallel fifths/octaves in 4-voice polyphonic textures

**Date:** 2026-01-09

**Symptom:** 4-voice polyphonic pieces failed guard checks with parallel fifths/octaves between inner voices and outer voices.

**Root cause:** Two separate code paths existed for inner voice resolution:
- `_fill_inner_with_chords()` for homophonic texture - used slice solver with proper `filter_candidates()`
- `_adjust_voice_leading()` for polyphonic texture - bypassed constraint filtering, only did octave displacement

The polyphonic path did not use the slice solver's `filter_candidates()` function, which checks for parallel motion against all previously-placed voices.

**Fix:** Unified both paths into a phrase-level branch-and-bound search (`_branch_and_bound_search()`) that evaluates full phrase combinations.

**Files changed:**
- `engine/slice_solver.py` - Added `get_thematic_candidates()`
- `engine/inner_voice.py` - Replaced legacy slice-by-slice resolution with phrase-level `_branch_and_bound_search()`

---

## BUG-002: Broken backtracking for inner voice parallel motion

**Date:** 2026-01-09

**Symptom:** `run_exercises.py` failed with "Guard check failed: 7 blocker(s)" due to parallel octaves/fifths. The backtracking mechanism ran 1000 iterations without finding a solution.

**Root cause:** Three-part failure:
1. Flat proposal mechanism instead of proper backtracking tree
2. Architecture mismatch between slice solver and guards (different offset models)
3. Missing fallback to chord tones when thematic material creates parallels

**Fix:** 
1. Proper backtracking with per-slice choice indices
2. Inner-to-outer parallel filtering at candidate generation time
3. Chord tone fallback in `get_thematic_candidates()`

**Files changed:**
- `engine/inner_voice.py` - Added `add_inner_voices_with_backtracking()`, `_branch_and_bound_search()`
- `engine/slice_solver.py` - Updated `filter_candidates()`, `get_thematic_candidates()`
- `engine/expander.py` - Uses `add_inner_voices_cpsat()` with backtracking fallback

---

# Part 2: Active Fix Plan (Voice-Leading Issues)

## Problem Summary

After implementing rhythm stagger, parallel rhythm faults are eliminated. Six fault categories remain:

1. Polyphonic bass overlap at passage boundaries
2. Unprepared dissonance on strong beats
3. Parallel fifths/octaves
4. Tessitura excursions
5. Ugly leaps (minor 7th)
6. Direct fifths/octaves

## Musical Definitions (Semitone Reference)

| Semitones | Name | Consonant? |
|-----------|------|------------|
| 0 | Unison | Yes |
| 1 | Minor 2nd | No |
| 2 | Major 2nd | No |
| 3 | Minor 3rd | Yes |
| 4 | Major 3rd | Yes |
| 5 | Perfect 4th | Yes |
| 6 | Tritone | No |
| 7 | Perfect 5th | Yes (but parallel forbidden) |
| 8 | Minor 6th | Yes |
| 9 | Major 6th | Yes |
| 10 | Minor 7th | No |
| 11 | Major 7th | No |
| 12 | Octave | Yes (but parallel forbidden) |

```python
CONSONANT_INTERVALS: frozenset[int] = frozenset({0, 3, 4, 5, 7, 8, 9, 12})
DISSONANT_INTERVALS: frozenset[int] = frozenset({1, 2, 6, 10, 11})
PERFECT_INTERVALS: frozenset[int] = frozenset({0, 7, 12})  # unison, fifth, octave
STEP_THRESHOLD: int = 2  # semitones; >2 = leap
```

```python
def classify_motion(soprano_delta: int, bass_delta: int) -> str:
    """soprano_delta/bass_delta: pitch2 - pitch1 (signed)"""
    if soprano_delta == 0 and bass_delta == 0:
        return "static"
    if soprano_delta == 0 or bass_delta == 0:
        return "oblique"
    if (soprano_delta > 0) == (bass_delta > 0):
        return "similar"
    return "contrary"
```

---

## Fix 1: Polyphonic Overlap at Passage Boundaries

**File:** `builder/realisation.py`

**Algorithm:**

```python
def _get_passage_end_offset(
    bar: int,
    assignments: Sequence[PassageAssignment],
    beats_per_bar: int,
) -> Fraction | None:
    """Return offset where current passage ends."""
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return Fraction(assignment.end_bar * beats_per_bar, 4)
    return None

# In bass note loop:
passage_end = _get_passage_end_offset(bar, passage_assignments, beats_per_bar)
if passage_end is not None:
    max_duration = passage_end - current_offset
    if max_duration > 0 and dur > max_duration:
        dur = max_duration  # truncate
```

---

## Fix 2: Unprepared Dissonance on Strong Beats

**File:** `builder/realisation.py` or `shared/pitch.py`

**Detection:**

```python
def is_dissonant_interval(soprano_midi: int, bass_midi: int) -> bool:
    interval = abs(soprano_midi - bass_midi) % 12
    return interval in {1, 2, 6, 10, 11}
```

**Fix:**

```python
def adjust_bass_for_consonance(bass_midi: int, soprano_midi: int, key: Key) -> int:
    current_interval = abs(soprano_midi - bass_midi) % 12
    if current_interval not in {1, 2, 6, 10, 11}:
        return bass_midi
    for delta in [1, -1, 2, -2]:
        candidate = bass_midi + delta
        new_interval = abs(soprano_midi - candidate) % 12
        if new_interval not in {1, 2, 6, 10, 11}:
            if _is_diatonic(candidate, key):
                return candidate
    return bass_midi
```

---

## Fix 3+6: Parallel and Direct Fifths/Octaves

**File:** `builder/figuration/selector.py`, `builder/figuration/figurate.py`

```python
def prevent_parallel_or_direct_perfect(
    soprano_figure_degrees: tuple[int, ...],
    bass_candidate_degrees: tuple[int, ...],
    start_soprano_midi: int,
    start_bass_midi: int,
) -> bool:
    """Return True if bass candidate creates parallel OR direct 5ths/8ves."""
    for i in range(len(soprano_figure_degrees) - 1):
        if i >= len(bass_candidate_degrees) - 1:
            break
        s1 = start_soprano_midi + soprano_figure_degrees[i]
        s2 = start_soprano_midi + soprano_figure_degrees[i + 1]
        b1 = start_bass_midi + bass_candidate_degrees[i]
        b2 = start_bass_midi + bass_candidate_degrees[i + 1]
        
        interval1 = abs(s1 - b1) % 12
        interval2 = abs(s2 - b2) % 12
        s_delta = s2 - s1
        b_delta = b2 - b1
        
        if s_delta == 0 or b_delta == 0:
            continue
        if (s_delta > 0) != (b_delta > 0):
            continue
        
        # Parallel: same perfect interval maintained
        if interval1 in {0, 7} and interval1 == interval2:
            return True
        # Direct: arrive at perfect interval with soprano leap
        if interval2 in {0, 7} and abs(s_delta) > 2:
            return True
    return False
```

**Requires:** Pass soprano figured bar to bass figuration.

---

## Fix 4: Tessitura Excursions

**File:** `shared/pitch.py`, `shared/constants.py`

**IMPORTANT:** No clamping. Clamping violates "fix at source" law.

```python
VOICE_RANGES: dict[str, tuple[int, int]] = {
    "soprano": (60, 81),  # C4-A5
    "bass": (40, 62),     # E2-D4
}

def select_octave(
    key: Key,
    degree: int,
    median: int,
    prev_pitch: int | None,
    voice_range: tuple[int, int] | None = None,
) -> int:
    """Select octave, constrained to voice range at source."""
    pitch_class: int = _degree_to_pitch_class(key, degree)
    
    # Generate all octave placements (MIDI 24-96)
    candidates: list[int] = [
        pitch_class + octave * 12
        for octave in range(2, 9)
    ]
    
    # Filter to range BEFORE selection
    if voice_range is not None:
        low, high = voice_range
        candidates = [p for p in candidates if low <= p <= high]
    
    assert candidates, f"No valid octave for degree {degree} in range {voice_range}"
    
    target: int = prev_pitch if prev_pitch is not None else median
    return min(candidates, key=lambda p: abs(p - target))
```

---

## Fix 5: Ugly Leaps (Minor 7th)

**File:** `builder/figuration/selector.py`, `shared/constants.py`

```python
UGLY_LEAP_THRESHOLD: int = 10  # semitones (minor 7th)

def filter_by_max_leap(
    figures: list[Figure],
    max_leap_semitones: int = 9,
) -> list[Figure]:
    result = []
    for fig in figures:
        max_leap = _compute_max_internal_leap(fig.degrees)
        if max_leap <= max_leap_semitones:
            result.append(fig)
    return result if result else figures

def _compute_max_internal_leap(degrees: tuple[int, ...]) -> int:
    if len(degrees) < 2:
        return 0
    max_leap = 0
    for i in range(len(degrees) - 1):
        leap = abs(degrees[i + 1] - degrees[i]) * 2  # approx semitones
        max_leap = max(max_leap, leap)
    return max_leap
```

Also reduce `MISBEHAVIOUR_PROBABILITY` from 0.05 to 0.02.

---

## Implementation Order

| Priority | Fix | Files |
|----------|-----|-------|
| 1 | Fix 4 - Tessitura | `shared/pitch.py`, `shared/constants.py`, `builder/realisation.py` |
| 2 | Fix 1 - Overlap | `builder/realisation.py` |
| 3 | Fix 5 - Ugly leaps | `builder/figuration/selector.py`, `shared/constants.py` |
| 4 | Fix 2 - Dissonance | `builder/realisation.py` or `shared/pitch.py` |
| 5 | Fix 3+6 - Parallels | `builder/figuration/selector.py`, `builder/figuration/figurate.py` |

---

# Part 3: Architectural TODOs

## TODO-001: Replace voice indices with named roles

**Priority:** High

**Problem:** Voices identified by integer indices with implicit semantics. Magic index arithmetic throughout (`voice_count - 1` for bass).

**Solution:** Use named roles ("soprano", "bass", "alto", "tenor") instead of indices. Realiser maps roles to score positions.

**Files:** `VoiceMaterial`, `inner_voice.py`, `slice_solver.py`, `realiser.py`

---

## TODO-002: Support chromatic alterations in schema degrees

**Priority:** Medium

**Problem:** Schema degrees are plain integers (1-7). No way to specify ♭7 or ♯7.

**Solution:** Extend notation: `b7` = lowered 7th, `#7` = raised 7th. Or `{"degree": 7, "alter": -1}`.

**Files:** `data/schemas.yaml`, `engine/schema.py`, `shared/pitch.py`

---

## TODO-003: Voice expansion - use actual subject material

**Priority:** High

**Problem:** `soprano_source: subject` and `bass_source: counter_subject` in VoiceExpansionConfig are ignored.

**Solution:** Store generated subject after motif generation. In realisation, use stored material when `expansion.soprano_source == "subject"`.

**Files:** `builder/realisation.py`, `planner/`

---

## TODO-004: Voice expansion - bass imitation with delay

**Priority:** High

**Problem:** `bass_derivation: imitation` and `bass_delay: 1` are loaded but ignored.

**Solution:** When `expansion.bass_derivation == "imitation"`, copy soprano material to bass with offset and interval transposition.

**Files:** `builder/realisation.py`

---

## TODO-005: Voice expansion - respect interdictions

**Priority:** Medium

**Problem:** `interdictions: ["ornaments", "inner_voice_gen"]` are loaded but ignored.

**Solution:** Check interdictions before calling subsystems. Skip ornaments or inner voice solver when interdicted.

**Files:** `builder/realisation.py`, `builder/figuration/figurate.py`, `engine/inner_voice.py`

---

## TODO-006: Generalise to N Voices

**Priority:** Deferred (until fugue/chorale/trio sonata needed)

**Problem:** System hardcoded for 2 voices (soprano, bass).

| Component | Current | Required |
|-----------|---------|----------|
| `NoteFile` | `soprano`, `bass` tuples | `voices: dict[int, tuple]` |
| `lead_voice` | `0`, `1`, or `None` | N valid indices |
| Rhythm stagger | Binary | Per-voice offsets |
| `VOICE_RANGES` | soprano, bass | Add alto (53-72), tenor (48-67) |
| Parallel checks | Soprano-bass only | All N×(N-1)/2 pairs |

**Approach:**
1. Replace named voice variables with voice-indexed dict
2. Generalise `PassageAssignment.lead_voice`
3. Compute stagger as `voice_index * stagger_unit`
4. Loop all voice pairs for interval checks

**Effort:** Medium-high

---

## TODO-007: Period Style Support (Classical/Romantic)

**Priority:** Low (future expansion)

**Problem:** Hardcoded baroque assumptions throughout.

**Solution:** Extract to `StyleProfile` loaded from YAML:

```python
@dataclass
class StyleProfile:
    name: str
    period: str  # "baroque", "classical", "romantic"
    step_bonus: float
    leap_tolerance: int
    parallel_fifth_penalty: float
    hidden_fifth_ok: bool
    bass_assumes_root: bool
    # ... etc
```

**Classical additions:**
- Alberti bass patterns
- Cadential 6/4 chord
- Periodic phrase structure (4+4 bars)

**Romantic additions:**
- Chromatic mediants
- Augmented sixth chords
- Reduced parallel penalties
- Thick voicings (5-6 notes)

**Files:** New `engine/style_profile.py`, `data/styles/*.yaml`, updates throughout scoring code.

---

## TODO-008: Configurable stagger_beats for accompany_texture

**Priority:** Low

**Problem:** Staggered entry delay is hardcoded to 1 beat.

**Solution:** Add `stagger_beats` field to section YAML, default 1.

```yaml
sections:
  - name: exordium
    lead_voice: 0
    accompany_texture: staggered
    stagger_beats: 1          # optional, default 1
```

Values: 0.5 (tight imitation), 1 (standard), 2 (dramatic separation).

Offset computed: `delay = stagger_beats * beat_value`

**Files:** `builder/figuration/bar_context.py`, genre YAMLs

---

# Part 4: Open Bugs

(none)
