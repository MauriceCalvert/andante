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

**Problem:** Invention genre expects imitative counterpoint but only produces parallel figuration. The `VoiceWriter._compose_imitative_section()` method exists but is never called.

**Current behaviour:**
- `_build_sections()` only assigns `Role.SCHEMA_UPPER` or `Role.SCHEMA_LOWER`
- `Role.IMITATIVE` is never assigned
- Genre config `lead_voice` only affects which voice gets FIGURATION vs PILLAR
- Both voices fill gaps independently from schema anchors

**Expected behaviour:**
- Lead voice composes first (already works)
- Follow voice copies lead material, transposed and delayed
- Delay specified by `follow_delay` in SectionPlan
- Interval specified by `follow_interval` (e.g., -7 for octave below, -4 for fifth below)

**Implementation plan:**

### Step 1: Extend genre config
```yaml
sections:
  - name: exordium
    lead_voice: 0
    follow_voice: 1
    follow_delay: "1/4"      # quarter note delay
    follow_interval: -7      # octave below (diatonic steps)
    follow_mode: strict      # strict | free
```

### Step 2: Update `_build_sections()` in `voice_planning.py`
- When section has `follow_voice`, create SectionPlan with `Role.IMITATIVE`
- Set `follows`, `follow_interval`, `follow_delay` fields

### Step 3: Wire up in `compose_voices()` in `compose.py`
- Compose lead voice section first
- Pass lead notes to follow voice writer via `update_prior_voices()`
- Follow voice calls `_compose_imitative_section()`

### Step 4: Fix `_compose_imitative_section()` in `voice_writer.py`
- Currently broken: filters by section offset but source notes use different offset model
- Needs: proper offset alignment, octave adjustment for range

**Files:**
- `data/genres/invention.yaml` — add imitation config
- `planner/voice_planning.py` — assign Role.IMITATIVE
- `builder/compose.py` — section-by-section voice scheduling
- `builder/voice_writer.py` — fix imitation logic

**Effort:** Medium

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
