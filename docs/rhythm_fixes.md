# Rhythm Fixes: Offsets, Durations, Pedal Points

## Overview

Three fixes to make output more Bach-like. No musical knowledge required — follow instructions mechanically.

**Working directory:** `D:\projects\Barok\barok\source\andante`

**Three fixes:**
- Fix 1: Shift all offsets to eliminate negative values
- Fix 2: Replace duration scaling with note-count selection (soprano only)
- Fix 3: Replace static pedal patterns with neighbor motion

---

## Fix 1: Eliminate Negative Offsets

### Problem

Anacrusis notes have negative offsets (-0.25 to -0.0625). MIDI converters delete or pile up these notes.

### Solution

Shift ALL notes forward by the anacrusis duration. If anacrusis is 0.25 (four sixteenths), then:
- Anacrusis notes: -0.25 → 0.0, -0.1875 → 0.0625, etc.
- Bar 1 notes: 0.0 → 0.25, 0.125 → 0.375, etc.

### Implementation

In `builder/realisation.py`, in function `realise_with_figuration()`:

**Step 1:** After generating all soprano_notes and bass_notes, before returning, add:

Find the return statement:
```python
    return NoteFile(
        soprano=tuple(soprano_notes),
        bass=tuple(bass_notes),
        metre=genre_config.metre,
        tempo=tempo,
        upbeat=genre_config.upbeat,
    )
```

**Before** that return, add this block:

```python
    # Shift all offsets to eliminate negative values
    min_offset = Fraction(0)
    for note in soprano_notes:
        if note.offset < min_offset:
            min_offset = note.offset
    for note in bass_notes:
        if note.offset < min_offset:
            min_offset = note.offset
    if min_offset < 0:
        shift = -min_offset  # Convert negative to positive shift
        soprano_notes = [
            Note(
                offset=n.offset + shift,
                pitch=n.pitch,
                duration=n.duration,
                voice=n.voice,
                lyric=n.lyric,
            )
            for n in soprano_notes
        ]
        bass_notes = [
            Note(
                offset=n.offset + shift,
                pitch=n.pitch,
                duration=n.duration,
                voice=n.voice,
                lyric=n.lyric,
            )
            for n in bass_notes
        ]
```

### Verify Fix 1

After running generation, check that no offsets are negative:
```powershell
Get-Content D:\projects\Barok\barok\source\andante\output\invention.note | Select-String "^-"
```

Should return no matches (no lines starting with minus sign).

---

## Fix 2: Valid Baroque Durations (Soprano Only)

### Problem

Soprano durations include 3/32, 3/16, 5/16 — these create "French Overture" jaggedness.

Bach uses only power-of-2 durations: 1/4, 1/8, 1/16 (and 1/32 rarely).

### Root Cause

Current code scales template durations to fit arbitrary gaps:
```
gap = 3/8, template = 4 notes
result = 3/8 ÷ 4 = 3/32 per note  ← WRONG
```

### Solution

Bach's approach: density determines rhythmic unit, gap determines note count.
```
density = medium → unit = 1/8
gap = 3/8
note_count = 3/8 ÷ 1/8 = 3 notes
result = 3 × 1/8  ← CORRECT
```

### Implementation

**Step 1:** Create new file `builder/figuration/rhythm_calc.py`:

```python
"""Rhythmic calculation for baroque durations.

Bach's approach: density determines rhythmic unit, gap determines note count.
Only power-of-2 durations are valid: 1/4, 1/8, 1/16, 1/32.
"""
from fractions import Fraction

# Valid baroque durations in descending order
VALID_UNITS: tuple[Fraction, ...] = (
    Fraction(1, 4),   # quarter
    Fraction(1, 8),   # eighth
    Fraction(1, 16),  # sixteenth
    Fraction(1, 32),  # thirty-second (rare)
)

# Density to preferred rhythmic unit
DENSITY_TO_UNIT: dict[str, Fraction] = {
    "low": Fraction(1, 4),
    "medium": Fraction(1, 8),
    "high": Fraction(1, 16),
}


def compute_rhythmic_distribution(
    gap: Fraction,
    density: str,
) -> tuple[int, Fraction]:
    """Compute note count and duration for a gap.
    
    Args:
        gap: Duration to fill (in whole notes)
        density: "low", "medium", or "high"
    
    Returns:
        (note_count, duration_each) where duration_each is a valid baroque value.
        All notes get the same duration. note_count * duration_each == gap.
    """
    preferred_unit = DENSITY_TO_UNIT.get(density, Fraction(1, 8))
    # Try preferred unit first
    for unit in VALID_UNITS:
        if unit > preferred_unit:
            continue  # Skip units larger than preferred
        count = gap / unit
        if count == int(count) and count >= 1:
            return (int(count), unit)
    # Fallback: try all units from largest to smallest
    for unit in VALID_UNITS:
        count = gap / unit
        if count == int(count) and count >= 1:
            return (int(count), unit)
    # Last resort: single note for entire gap (shouldn't happen with valid gaps)
    return (1, gap)


def is_valid_duration(d: Fraction) -> bool:
    """Check if duration is a valid baroque value (power of 2)."""
    # Valid if denominator is power of 2 and numerator is 1
    if d.numerator != 1:
        return False
    denom = d.denominator
    return denom > 0 and (denom & (denom - 1)) == 0


def quantize_duration(d: Fraction) -> Fraction:
    """Quantize a duration to nearest valid baroque value.
    
    Used as fallback when other methods produce invalid durations.
    """
    if is_valid_duration(d):
        return d
    # Find nearest valid unit
    best = VALID_UNITS[0]
    best_diff = abs(d - best)
    for unit in VALID_UNITS[1:]:
        diff = abs(d - unit)
        if diff < best_diff:
            best = unit
            best_diff = diff
    return best
```

**Step 2:** Modify `builder/figuration/realiser.py`

Add import at top:
```python
from builder.figuration.rhythm_calc import compute_rhythmic_distribution
```

Find the function `realise_rhythm()`. It currently returns scaled durations.

Add a new function **before** `realise_rhythm()`:

```python
def realise_rhythm_baroque(
    gap_duration: Fraction,
    density: str,
) -> tuple[Fraction, ...]:
    """Realise rhythm using Bach's approach: density→unit, gap→count.
    
    Args:
        gap_duration: Available duration for the figure (in whole notes)
        density: Density level ("low", "medium", "high")
    
    Returns:
        Tuple of equal durations that sum to gap_duration.
        All durations are valid baroque values (1/4, 1/8, 1/16, 1/32).
    """
    note_count, unit = compute_rhythmic_distribution(gap_duration, density)
    return tuple(unit for _ in range(note_count))
```

**Step 3:** Modify `realise_figure_to_bar()` in `realiser.py`

Add `density` parameter and `use_baroque_rhythm` flag:

Change signature from:
```python
def realise_figure_to_bar(
    figure: Figure,
    bar: int,
    start_degree: int,
    gap_duration: Fraction,
    metre: str,
    bar_function: str = "passing",
    rhythmic_unit: Fraction = Fraction(1, 4),
    next_anchor_strength: str = "strong",
    use_hemiola: bool = False,
    overdotted: bool = False,
    start_beat: int = 1,
) -> FiguredBar:
```

To:
```python
def realise_figure_to_bar(
    figure: Figure,
    bar: int,
    start_degree: int,
    gap_duration: Fraction,
    metre: str,
    bar_function: str = "passing",
    rhythmic_unit: Fraction = Fraction(1, 4),
    next_anchor_strength: str = "strong",
    use_hemiola: bool = False,
    overdotted: bool = False,
    start_beat: int = 1,
    density: str = "medium",
    use_baroque_rhythm: bool = False,
) -> FiguredBar:
```

Inside the function, find where durations are computed:
```python
    # Get rhythm durations
    durations = realise_rhythm(
        figure=figure,
        gap_duration=gap_duration,
        metre=metre,
        bar_function=bar_function,
        rhythmic_unit=rhythmic_unit,
        next_anchor_strength=next_anchor_strength,
        use_hemiola=use_hemiola,
        overdotted=overdotted,
    )
```

Replace with:
```python
    # Get rhythm durations
    if use_baroque_rhythm:
        durations = realise_rhythm_baroque(gap_duration, density)
        # Adjust degrees to match duration count
        if len(durations) != len(figure.degrees):
            # Interpolate or truncate degrees to match duration count
            absolute_degrees = _adjust_degrees_to_count(
                absolute_degrees, len(durations)
            )
    else:
        durations = realise_rhythm(
            figure=figure,
            gap_duration=gap_duration,
            metre=metre,
            bar_function=bar_function,
            rhythmic_unit=rhythmic_unit,
            next_anchor_strength=next_anchor_strength,
            use_hemiola=use_hemiola,
            overdotted=overdotted,
        )
```

**Step 4:** Add helper function in `realiser.py`

Add this function somewhere in the file:

```python
def _adjust_degrees_to_count(degrees: list[int], target_count: int) -> list[int]:
    """Adjust degree list to match target count.
    
    If target_count > len(degrees): interpolate intermediate steps
    If target_count < len(degrees): take first and last, distribute middle
    If equal: return as-is
    
    Args:
        degrees: Original absolute degrees (1-7)
        target_count: Desired number of degrees
    
    Returns:
        New list of degrees with target_count elements.
    """
    if target_count == len(degrees):
        return degrees
    if target_count == 1:
        return [degrees[0]]
    if target_count < len(degrees):
        # Take evenly spaced samples including first and last
        step = (len(degrees) - 1) / (target_count - 1)
        return [degrees[round(i * step)] for i in range(target_count)]
    # target_count > len(degrees): interpolate
    result: list[int] = []
    for i in range(target_count):
        # Map i to position in original
        pos = i * (len(degrees) - 1) / (target_count - 1)
        idx = int(pos)
        if idx >= len(degrees) - 1:
            result.append(degrees[-1])
        else:
            # Linear interpolation between degrees[idx] and degrees[idx+1]
            frac = pos - idx
            d1 = degrees[idx]
            d2 = degrees[idx + 1]
            interp = round(d1 + frac * (d2 - d1))
            # Keep in 1-7 range
            while interp < 1:
                interp += 7
            while interp > 7:
                interp -= 7
            result.append(interp)
    return result
```

**Step 5:** Update calls in `figurate.py`

In `figurate.py`, find all calls to `realise_figure_to_bar()` and add the new parameters.

In the main loop, change:
```python
        figured_bar = realise_figure_to_bar(
            figure=figure,
            bar=bar_num,
            start_degree=_get_degree(anchor_a, role),
            gap_duration=effective_gap,
            metre=metre,
            bar_function=bar_function,
            rhythmic_unit=_get_rhythmic_unit(metre),
            next_anchor_strength=next_anchor_strength,
            use_hemiola=use_hemiola,
            overdotted=should_use_overdotted(affect_character, phrase_pos),
            start_beat=start_beat,
        )
```

To:
```python
        figured_bar = realise_figure_to_bar(
            figure=figure,
            bar=bar_num,
            start_degree=_get_degree(anchor_a, role),
            gap_duration=effective_gap,
            metre=metre,
            bar_function=bar_function,
            rhythmic_unit=_get_rhythmic_unit(metre),
            next_anchor_strength=next_anchor_strength,
            use_hemiola=use_hemiola,
            overdotted=should_use_overdotted(affect_character, phrase_pos),
            start_beat=start_beat,
            density=effective_density,
            use_baroque_rhythm=True,
        )
```

Also update calls in `_apply_schema_figuration()` and `figurate_single_bar()` if present.

### Verify Fix 2

After running generation, check for invalid durations:
```powershell
Get-Content D:\projects\Barok\barok\source\andante\output\invention.note | Select-String "3/32|3/16|5/16|3/8"
```

Should return no matches (no non-power-of-2 durations).

Valid durations to see: `1/4`, `1/8`, `1/16`, `1/2`, `1/32`

---

## Fix 3: Replace Pedal Patterns with Neighbor Motion

### Problem

Bass plays C3-C3-C3-C3 (same note repeated) in bars 3 and 6. This halts momentum.

### Solution

Replace static pedal patterns with neighbor motion patterns that stay in the harmonic zone but have melodic movement.

### Implementation

**Step 1:** Edit `data/figuration/bass_diminutions.yaml`

Find the `unison:` section. It currently contains:

```yaml
unison:
  - name: bass_sustained_half
    degrees: [0]
    durations: ["1/2"]
    character: sustained
    direction: static
    motor: false

  - name: bass_repeated_quarters
    degrees: [0, 0]
    durations: ["1/4", "1/4"]
    character: plain
    direction: static
    motor: false

  - name: bass_pedal_eighths
    degrees: [0, 0, 0, 0]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: energetic
    direction: static
    motor: true
```

**Replace** the entire `unison:` section with:

```yaml
# =============================================================================
# UNISON: same target pitch (degree difference = 0)
# Use neighbor motion instead of static repetition
# =============================================================================

unison:
  - name: bass_sustained_half
    degrees: [0]
    durations: ["1/2"]
    character: sustained
    direction: static
    motor: false

  - name: bass_neighbor_quarters
    degrees: [0, 1]
    durations: ["1/4", "1/4"]
    character: plain
    direction: ascending
    motor: false

  - name: bass_oscillation
    degrees: [0, 1, 0, -1]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: plain
    direction: static
    motor: true

  - name: bass_neighbor_up_return
    degrees: [0, 1, 2, 0]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: energetic
    direction: ascending
    motor: true

  - name: bass_neighbor_down_return
    degrees: [0, -1, -2, 0]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: energetic
    direction: descending
    motor: true

  - name: bass_upper_neighbor_16th
    degrees: [0, 1, 0, 1]
    durations: ["1/16", "1/16", "1/16", "1/16"]
    character: energetic
    direction: static
    motor: true

  - name: bass_lower_neighbor_16th
    degrees: [0, -1, 0, -1]
    durations: ["1/16", "1/16", "1/16", "1/16"]
    character: energetic
    direction: static
    motor: true
```

**Key changes:**
- Deleted `bass_repeated_quarters` (was [0, 0])
- Deleted `bass_pedal_eighths` (was [0, 0, 0, 0])
- Added patterns with stepwise neighbor motion
- All motor patterns now have melodic movement

### Verify Fix 3

After running generation, check for repeated pitches in bass:

```powershell
Get-Content D:\projects\Barok\barok\source\andante\output\invention.note | Select-Object -Last 100
```

Look at bass notes (voice 3). Should not see same pitch 4 times in a row at eighth-note intervals.

---

## Full Verification

Run generation:
```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c "cd /d D:\projects\Barok\barok\source\andante && set PYTHONPATH=. && D:\projects\Barok\barok\.venv\Scripts\python.exe main.py briefs/builder/invention.brief" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

Check output:
```powershell
Get-Content D:\projects\Barok\barok\source\andante\output\invention.note
```

**Checklist:**
1. ☐ No negative offsets (all values ≥ 0)
2. ☐ No 3/32, 3/16, 5/16 durations in soprano
3. ☐ No four identical bass pitches in a row
4. ☐ Anacrusis starts at offset 0.0
5. ☐ Bar 1 soprano starts at offset 0.25 (shifted by anacrusis)

---

## Commit

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c ""C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante add -A && "C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante commit -m "fix: valid baroque durations, positive offsets, linear bass"" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

---

## Troubleshooting

### Still seeing 3/32 durations

1. Check `use_baroque_rhythm=True` is passed to `realise_figure_to_bar()`
2. Verify `rhythm_calc.py` exists and is imported
3. Add debug print in `realise_rhythm_baroque()` to see what it returns

### Still seeing negative offsets

1. Check the offset shift code is placed **before** the return statement
2. Check it processes **both** soprano_notes and bass_notes
3. Add debug print to see `min_offset` value

### Bass still repeating notes

1. Verify `bass_diminutions.yaml` was saved correctly
2. Check YAML syntax: run `python -c "import yaml; yaml.safe_load(open('data/figuration/bass_diminutions.yaml'))"`
3. Restart Python to clear cached `_bass_diminutions`

### Import errors

1. Check file paths are correct
2. Check `__init__.py` exists in builder/figuration/

---

## Summary of Changes

### New files:
- `builder/figuration/rhythm_calc.py`

### Modified files:
- `builder/figuration/realiser.py` — add `realise_rhythm_baroque()`, `_adjust_degrees_to_count()`, new parameters
- `builder/figuration/figurate.py` — pass new parameters to `realise_figure_to_bar()`
- `builder/realisation.py` — add offset shift before return
- `data/figuration/bass_diminutions.yaml` — replace unison pedal patterns
