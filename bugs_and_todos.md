# Andante: Bugs, Fixes, and TODOs

Single source of truth for all bugs, planned fixes, and future work.

---

# Part 1: Active Bugs

## BUG-003: Bass patterns not applied
**Fixed:** 2026-02-04
**Solution:** Wired bass_treatment/bass_pattern from GenreConfig through voice planner into voice writer. Created ArpeggiatedStrategy that realises BassPattern (degree offsets) and RhythmPattern (schema pitches) into notes. Lower voice now uses WritingMode.ARPEGGIATED instead of PILLAR when bass_treatment is "patterned".

---

## BUG-004: Rhythm templates not varied across gaps
**Fixed:** 2026-02-04
**Solution:** Planner now computes `required_note_count` per gap based on interval size. Small intervals (unison, step, third) reduce from the density-derived base count; large intervals keep full density. Moved `DENSITY_TO_UNIT` to shared constants as `DENSITY_RHYTHMIC_UNIT` (L017 single source of truth). Minuet note counts now vary: unison→2, step→3, fourth/sixth→6 (was uniform 6 for all bars).

---

# Part 2: Missing Features

## FEAT-001: Imitation not implemented

**Date:** 2025-02-04
**Status:** Deferred — naive copying approach abandoned

**Problem:** Invention genre expects imitative counterpoint but current architecture cannot support it. Naive transposition of lead voice material creates guaranteed dissonances.

**Why naive copying fails:**
- Lead voice composes figuration without knowledge of what follower will play
- Delayed transposition places notes against incompatible harmonies
- No tonal answer (5th→4th adjustments required to stay in key)
- No countersubject concept

**Proper Baroque imitation requires:**
1. Pre-composed **subject** designed to work contrapuntally with itself
2. **Tonal answer** — not just transposition, needs 5th→4th mutations
3. **Countersubject** composed against the answer using consonance checks
4. Subject/answer/countersubject wired into section composition

**Current workaround:** Invention uses `accompany_texture: walking` instead of imitation. Produces contrapuntal but not imitative texture.

**Implementation plan (future):**

### Step 1: Subject integration
- Use `subject_generator.py` output as lead material
- Store subject as note sequence in genre config or runtime

### Step 2: Tonal answer generation
- Implement answer rules: real answer vs tonal answer
- 5th in subject → 4th in answer (and vice versa) at key boundaries

### Step 3: Countersubject composition
- Compose against answer using existing consonance/parallel checks
- Must be invertible (work as upper or lower voice)

### Step 4: Section assembly
- Bar 1: subject in lead voice, rest in follower
- Bar 2+: answer in follower, countersubject in lead
- Episodes: free figuration using subject fragments

**Files:**
- `motifs/subject_generator.py` — already exists
- `planner/answer_generator.py` — new, tonal answer logic
- `planner/countersubject.py` — new, countersubject composition
- `builder/imitative_strategy.py` — new, replaces naive copying

**Effort:** Large — requires subject-aware architecture

**References:**
- Bach Two-Part Inventions analysis
- Fux Gradus ad Parnassum species counterpoint

---

## FEAT-002: Figuration variety (reduce blandness)

**Date:** 2025-02-04

**Problem:** Figuration is correct but anonymous. Each gap filled with locally-optimal diminution, but no sense of style or character across the piece.

**Symptoms:**
- All gaps use similar figures regardless of position
- No preference for genre-typical patterns
- No motivic consistency (same interval filled differently each time)
- Figure selection purely by constraint satisfaction

**Expected:**
- Genre profiles bias figure selection (gavotte prefers X, minuet prefers Y)
- First occurrence of an interval establishes a "house style" for that piece
- Cadential approaches use distinct vocabulary
- Character parameter actually influences selection

**Implementation plan:**

### Step 1: Verify figuration_profiles.yaml is used
- File exists: `data/figuration/figuration_profiles.yaml`
- Check if `get_figuration_profiles()` is called anywhere
- Wire profile selection to genre config

### Step 2: Add genre → profile mapping
```yaml
# In genre YAML
figuration_profile: galant_dance
```

### Step 3: Implement figure memory
- Track which figures were used for each interval
- On subsequent same-interval gaps, prefer previously-used figure (weight boost)
- Implement in `FigurationStrategy.fill_gap()`

### Step 4: Character differentiation
- Currently `character` field filters figures but loosely (±2 ranks)
- Tighten to ±1 for stronger character enforcement
- Add character escalation: plain → expressive → energetic across sections

**Files:**
- `data/genres/*.yaml` — add figuration_profile
- `builder/figuration_strategy.py` — profile loading, figure memory
- `builder/figuration/loader.py` — profile lookup

**Effort:** Medium

## FEAT-003: Suspensions (4-3, 7-6)

**Date:** 2026-02-05
**Status:** Deferred — not needed for current dance/chorale genres

**Problem:** No suspension mechanism. Output sounds correct but lacks the tension-release cycles characteristic of expressive Baroque writing.

**What's needed:**
- New `WritingMode.SUSPENDED` (or equivalent)
- Planning-layer decisions on suspension placement (typically cadential/pre-cadential points)
- `candidate_filter` must recognise prepared dissonance as intentional
- `faults.py` must exempt prepared suspensions from dissonance flags
- Suspension requires: preparation (consonant on weak beat), suspension (held over strong beat), resolution (step down)

**When:** After pipeline produces clean output across existing genres. First reach for this when results sound "correct but bland," especially in trio sonata slow movements or fugue episodes.

**Effort:** Medium-large — cuts across planner, builder, and guard systems

---

# Part 3: Architectural TODOs

## TODO-001: Replace voice indices with named roles

**Priority:** Medium

**Problem:** Voices identified by integer indices (0, 3) with implicit semantics.

**Solution:** Use named roles ("soprano", "bass") mapped to track numbers.

---

## TODO-002: Support chromatic alterations in schema degrees

**Priority:** Low

**Problem:** Schema degrees are plain integers. No ♭7 or ♯7.

**Solution:** Extend notation: `{"degree": 7, "alter": -1}` or string `"b7"`.

---

## TODO-003: Generalise to N voices

**Priority:** Deferred

**Problem:** System hardcoded for 2 voices.

**Solution:** Voice-indexed dict, generalised parallel checks.

---

# Part 4: Fixed Bugs (Archive)

## BUG-001: Parallel fifths/octaves in 4-voice textures
**Fixed:** 2026-01-09
**Solution:** Unified paths into phrase-level branch-and-bound search.

## BUG-002: Broken backtracking for inner voice parallel motion
**Fixed:** 2026-01-09
**Solution:** Proper backtracking tree, chord tone fallback.

## BUG-003: Bass patterns not applied
**Fixed:** 2026-02-04
**Solution:** Wired bass_treatment/bass_pattern from GenreConfig through voice planner into voice writer. Created ArpeggiatedStrategy that realises BassPattern (degree offsets) and RhythmPattern (schema pitches) into notes.

## BUG-004: Rhythm templates not varied across gaps
**Fixed:** 2026-02-04
**Solution:** Planner computes `required_note_count` per gap from interval size. Small intervals reduce from base; large intervals keep full density.

---

# Part 5: Deferred Items

## Voice-leading fixes from old plan
The detailed fix plans for parallels, dissonance, tessitura, and ugly leaps are retained but not currently active. These apply to 4-voice textures which are out of scope for current 2-voice work.

Reference: git history, commit "voice-leading fix plan".
