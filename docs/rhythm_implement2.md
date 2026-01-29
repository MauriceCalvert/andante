# Rhythm Implementation Instructions - New Work Only

## Overview

This document provides step-by-step instructions for the bass vocabulary fix and beat-class timing. Assumes Phase A refactoring is already complete.

**Working directory:** `D:\projects\Barok\barok\source\andante`

**Two phases:**
- Phase B: Bass vocabulary replacement (fix what bass plays)
- Phase C: Beat-class timing + anacrusis (fix when bass plays)

---

## Phase B: Bass Vocabulary Replacement

### B1. Create `data/figuration/bass_diminutions.yaml`

Create new file:

```yaml
# Bass Diminutions - Continuous patterns for accompanying bass
# Unlike soprano diminutions, these have FIXED durations (not scaled to gap)
# and emphasize stepwise motion for baroque style.
#
# Fields:
#   name: unique identifier
#   degrees: relative scale degrees from start (0 = start pitch)
#   durations: fixed durations in whole notes (1/4 = quarter, 1/8 = eighth, 1/16 = sixteenth)
#   character: plain | energetic | sustained
#   direction: ascending | descending | static
#   motor: true if this is a continuous "motor rhythm" pattern

# =============================================================================
# STEP_UP: ascending by step (degree difference = +1 or +2)
# =============================================================================

step_up:
  - name: bass_scalar_up_16th
    degrees: [0, 1, 2, 3]
    durations: ["1/16", "1/16", "1/16", "1/16"]
    character: energetic
    direction: ascending
    motor: true

  - name: bass_scalar_up_8th
    degrees: [0, 1, 2, 3]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: plain
    direction: ascending
    motor: true

  - name: bass_step_quarter
    degrees: [0, 1]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: ascending
    motor: false

  - name: bass_run_up_6
    degrees: [0, 1, 2, 3, 4, 5]
    durations: ["1/16", "1/16", "1/16", "1/16", "1/16", "1/16"]
    character: energetic
    direction: ascending
    motor: true

# =============================================================================
# STEP_DOWN: descending by step (degree difference = -1 or -2)
# =============================================================================

step_down:
  - name: bass_scalar_down_16th
    degrees: [0, -1, -2, -3]
    durations: ["1/16", "1/16", "1/16", "1/16"]
    character: energetic
    direction: descending
    motor: true

  - name: bass_scalar_down_8th
    degrees: [0, -1, -2, -3]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: plain
    direction: descending
    motor: true

  - name: bass_step_down_quarter
    degrees: [0, -1]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: descending
    motor: false

  - name: bass_run_down_6
    degrees: [0, -1, -2, -3, -4, -5]
    durations: ["1/16", "1/16", "1/16", "1/16", "1/16", "1/16"]
    character: energetic
    direction: descending
    motor: true

# =============================================================================
# THIRD_UP: ascending by third (degree difference = +2 or +3)
# =============================================================================

third_up:
  - name: bass_arpeggio_up_8th
    degrees: [0, 2, 4, 2]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: plain
    direction: ascending
    motor: true

  - name: bass_filled_third_up
    degrees: [0, 1, 2]
    durations: ["1/8", "1/8", "1/4"]
    character: plain
    direction: ascending
    motor: false

  - name: bass_leap_third_sustained
    degrees: [0, 2]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: ascending
    motor: false

# =============================================================================
# THIRD_DOWN: descending by third (degree difference = -2 or -3)
# =============================================================================

third_down:
  - name: bass_arpeggio_down_8th
    degrees: [0, -2, -4, -2]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: plain
    direction: descending
    motor: true

  - name: bass_filled_third_down
    degrees: [0, -1, -2]
    durations: ["1/8", "1/8", "1/4"]
    character: plain
    direction: descending
    motor: false

  - name: bass_leap_third_down_sustained
    degrees: [0, -2]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: descending
    motor: false

# =============================================================================
# FOURTH_UP / FOURTH_DOWN: fourths
# =============================================================================

fourth_up:
  - name: bass_scalar_fourth_up
    degrees: [0, 1, 2, 3]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: plain
    direction: ascending
    motor: true

  - name: bass_fourth_sustained
    degrees: [0, 3]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: ascending
    motor: false

fourth_down:
  - name: bass_scalar_fourth_down
    degrees: [0, -1, -2, -3]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: plain
    direction: descending
    motor: true

  - name: bass_fourth_down_sustained
    degrees: [0, -3]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: descending
    motor: false

# =============================================================================
# FIFTH_UP / FIFTH_DOWN: fifths
# =============================================================================

fifth_up:
  - name: bass_arpeggio_fifth_up
    degrees: [0, 2, 4]
    durations: ["1/8", "1/8", "1/4"]
    character: plain
    direction: ascending
    motor: false

  - name: bass_scalar_fifth_up
    degrees: [0, 1, 2, 3, 4]
    durations: ["1/16", "1/16", "1/16", "1/16", "1/8"]
    character: energetic
    direction: ascending
    motor: true

  - name: bass_fifth_sustained
    degrees: [0, 4]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: ascending
    motor: false

fifth_down:
  - name: bass_arpeggio_fifth_down
    degrees: [0, -2, -4]
    durations: ["1/8", "1/8", "1/4"]
    character: plain
    direction: descending
    motor: false

  - name: bass_scalar_fifth_down
    degrees: [0, -1, -2, -3, -4]
    durations: ["1/16", "1/16", "1/16", "1/16", "1/8"]
    character: energetic
    direction: descending
    motor: true

  - name: bass_fifth_down_sustained
    degrees: [0, -4]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: descending
    motor: false

# =============================================================================
# UNISON: same pitch (degree difference = 0)
# =============================================================================

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

# =============================================================================
# SIXTH_UP / SIXTH_DOWN / OCTAVE: larger intervals
# =============================================================================

sixth_up:
  - name: bass_scalar_sixth_up
    degrees: [0, 1, 2, 3, 4, 5]
    durations: ["1/16", "1/16", "1/16", "1/16", "1/8", "1/8"]
    character: energetic
    direction: ascending
    motor: true

  - name: bass_sixth_sustained
    degrees: [0, 5]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: ascending
    motor: false

sixth_down:
  - name: bass_scalar_sixth_down
    degrees: [0, -1, -2, -3, -4, -5]
    durations: ["1/16", "1/16", "1/16", "1/16", "1/8", "1/8"]
    character: energetic
    direction: descending
    motor: true

  - name: bass_sixth_down_sustained
    degrees: [0, -5]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: descending
    motor: false

octave_up:
  - name: bass_octave_arpeggio_up
    degrees: [0, 2, 4, 7]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: plain
    direction: ascending
    motor: true

  - name: bass_octave_sustained
    degrees: [0, 7]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: ascending
    motor: false

octave_down:
  - name: bass_octave_arpeggio_down
    degrees: [0, -2, -4, -7]
    durations: ["1/8", "1/8", "1/8", "1/8"]
    character: plain
    direction: descending
    motor: true

  - name: bass_octave_down_sustained
    degrees: [0, -7]
    durations: ["1/4", "1/4"]
    character: sustained
    direction: descending
    motor: false
```

### B2. Add functions to `bar_context.py`

Add these functions to `builder/figuration/bar_context.py`:

```python
def reduce_density(density: str) -> str:
    """Reduce density by one level for accompanying voice.
    
    Args:
        density: "high", "medium", or "low"
    
    Returns:
        One level sparser: high->medium, medium->low, low->low
    """
    if density == "high":
        return "medium"
    return "low"


def is_motor_context(
    bar: int,
    schema_sections: list[tuple[int, int]],
    anchors: Sequence[Anchor],
) -> bool:
    """Determine if this bar is within a motor rhythm context.
    
    Motor rhythm continues within schema sections.
    
    Args:
        bar: Current bar number
        schema_sections: List of (start_idx, end_idx) for schema sections
        anchors: Full anchor sequence
    
    Returns:
        True if bass should use continuous motor rhythm.
    """
    for start_idx, end_idx in schema_sections:
        if start_idx < len(anchors) and end_idx <= len(anchors):
            start_bar_beat = anchors[start_idx].bar_beat
            end_bar_beat = anchors[end_idx - 1].bar_beat
            start_bar = int(start_bar_beat.split(".")[0])
            end_bar = int(end_bar_beat.split(".")[0])
            if start_bar <= bar <= end_bar:
                return True
    return False
```

### B3. Update `FiguredBar` in `types.py`

Add `start_beat` field. Find the `FiguredBar` class and modify:

```python
@dataclass(frozen=True)
class FiguredBar:
    """Output of figuration for one bar."""
    bar: int
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    figure_name: str
    start_beat: int = 1  # 1 for lead voice, 2 for accompanying voice

    def __post_init__(self) -> None:
        assert self.bar >= 0, f"bar must be >= 0, got {self.bar}"
        assert len(self.degrees) == len(self.durations), \
            f"degrees length {len(self.degrees)} != durations length {len(self.durations)}"
        assert all(1 <= d <= 7 for d in self.degrees), \
            f"All degrees must be in range 1-7, got {self.degrees}"
        assert all(d > 0 for d in self.durations), "All durations must be positive"
        assert self.start_beat in (1, 2), f"start_beat must be 1 or 2, got {self.start_beat}"
```

Note: Keep the existing `get_onsets` method unchanged.

### B4. Create `builder/figuration/bass_figurate.py`

Create new file:

```python
"""Bass-specific figuration using bass_diminutions.yaml.

Unlike soprano figuration which uses scaled durations, bass figuration
uses fixed durations from bass_diminutions.yaml to ensure valid baroque
note values and continuous motor rhythm.
"""
from fractions import Fraction
from pathlib import Path
from typing import Sequence

import yaml

from builder.figuration.bar_context import (
    compute_beat_class,
    is_motor_context,
    reduce_density,
)
from builder.figuration.phrase import detect_schema_sections
from builder.figuration.selector import compute_interval
from builder.figuration.types import FiguredBar
from builder.types import Anchor, PassageAssignment

_bass_diminutions: dict | None = None


def _load_bass_diminutions() -> dict:
    """Load bass_diminutions.yaml, caching result."""
    global _bass_diminutions
    if _bass_diminutions is None:
        path = Path(__file__).parent.parent.parent / "data" / "figuration" / "bass_diminutions.yaml"
        with open(path, "r") as f:
            _bass_diminutions = yaml.safe_load(f)
    return _bass_diminutions


def _parse_bar_beat(bar_beat: str) -> tuple[int, float]:
    """Parse bar.beat string into (bar, beat) tuple."""
    parts = bar_beat.split(".")
    bar = int(parts[0])
    beat = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar, beat)


def _get_degree(anchor: Anchor) -> int:
    """Get bass degree from anchor."""
    return anchor.lower_degree


def _select_bass_figure(
    interval: str,
    is_motor: bool,
    density: str,
    seed: int,
) -> dict | None:
    """Select a bass figure based on interval and context.
    
    Args:
        interval: Interval name (step_up, third_down, etc.)
        is_motor: Whether we're in motor rhythm context
        density: Density level (high, medium, low)
        seed: Random seed for selection
    
    Returns:
        Figure dict from bass_diminutions.yaml, or None.
    """
    import random
    diminutions = _load_bass_diminutions()
    if interval not in diminutions:
        if interval.endswith("_up"):
            interval = "step_up"
        elif interval.endswith("_down"):
            interval = "step_down"
        else:
            interval = "unison"
    figures = diminutions.get(interval, [])
    if not figures:
        return None
    if is_motor:
        motor_figures = [f for f in figures if f.get("motor", False)]
        if motor_figures:
            figures = motor_figures
    if density == "high":
        preferred_chars = ["energetic", "plain"]
    elif density == "medium":
        preferred_chars = ["plain", "sustained"]
    else:
        preferred_chars = ["sustained", "plain"]
    char_figures = [f for f in figures if f.get("character", "plain") in preferred_chars]
    if char_figures:
        figures = char_figures
    if not figures:
        return None
    rng = random.Random(seed)
    return rng.choice(figures)


def _figure_to_figured_bar(
    figure: dict,
    bar: int,
    start_degree: int,
    start_beat: int,
) -> FiguredBar:
    """Convert a bass figure dict to FiguredBar.
    
    Args:
        figure: Figure dict from bass_diminutions.yaml
        bar: Bar number
        start_degree: Starting scale degree (1-7)
        start_beat: Which beat to start on (1 or 2)
    
    Returns:
        FiguredBar with absolute degrees and fixed durations.
    """
    relative_degrees = figure["degrees"]
    absolute_degrees: list[int] = []
    for rel in relative_degrees:
        absolute = start_degree + rel
        while absolute < 1:
            absolute += 7
        while absolute > 7:
            absolute -= 7
        absolute_degrees.append(absolute)
    durations: list[Fraction] = []
    for dur_str in figure["durations"]:
        if isinstance(dur_str, str):
            parts = dur_str.split("/")
            durations.append(Fraction(int(parts[0]), int(parts[1])))
        else:
            durations.append(Fraction(dur_str))
    return FiguredBar(
        bar=bar,
        degrees=tuple(absolute_degrees),
        durations=tuple(durations),
        figure_name=figure["name"],
        start_beat=start_beat,
    )


def figurate_bass(
    anchors: Sequence[Anchor],
    metre: str,
    seed: int,
    density: str = "medium",
    passage_assignments: Sequence[PassageAssignment] | None = None,
) -> list[FiguredBar]:
    """Figurate bass voice using bass-specific patterns.
    
    Unlike soprano figuration, this uses:
    - Fixed durations from bass_diminutions.yaml (no scaling)
    - Motor rhythm detection for continuous patterns
    - Beat-class for accompanying voice timing
    
    Args:
        anchors: Schema anchors
        metre: Time signature string like "4/4"
        seed: Random seed
        density: Density level from affect
        passage_assignments: Passage assignments with lead_voice info
    
    Returns:
        List of FiguredBar for bass voice.
    """
    if len(anchors) < 2:
        return []
    sorted_anchors = sorted(anchors, key=lambda a: _parse_bar_beat(a.bar_beat))
    schema_sections = detect_schema_sections(sorted_anchors)
    figured_bars: list[FiguredBar] = []
    for i in range(len(sorted_anchors) - 1):
        anchor_a = sorted_anchors[i]
        anchor_b = sorted_anchors[i + 1]
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
        start_beat = compute_beat_class("bass", bar_num, passage_assignments)
        effective_density = density
        if start_beat == 2:
            effective_density = reduce_density(density)
        is_motor = is_motor_context(bar_num, schema_sections, sorted_anchors)
        degree_a = _get_degree(anchor_a)
        degree_b = _get_degree(anchor_b)
        interval = compute_interval(degree_a, degree_b)
        figure = _select_bass_figure(
            interval=interval,
            is_motor=is_motor,
            density=effective_density,
            seed=seed + i,
        )
        if figure is None:
            figure = {
                "name": "bass_fallback",
                "degrees": [0],
                "durations": ["1/2"],
                "character": "sustained",
                "direction": "static",
                "motor": False,
            }
        figured_bar = _figure_to_figured_bar(
            figure=figure,
            bar=bar_num,
            start_degree=degree_a,
            start_beat=start_beat,
        )
        figured_bars.append(figured_bar)
    return figured_bars
```

### B5. Update `realisation.py` to use `figurate_bass`

In `realisation.py`, find the contrapuntal bass block. It starts with:

```python
    if genre_config.bass_treatment == "contrapuntal":
        bass_figured_bars = figurate(
```

Replace the `figurate()` call with `figurate_bass()`:

```python
    if genre_config.bass_treatment == "contrapuntal":
        from builder.figuration.bass_figurate import figurate_bass
        bass_figured_bars = figurate_bass(
            anchors=anchors,
            metre=genre_config.metre,
            seed=seed + 1000,
            density=density,
            passage_assignments=passage_assignments,
        )
```

### B6. Update bass offset calculation in `realisation.py`

In the bass loop (inside the `if genre_config.bass_treatment == "contrapuntal":` block), find:

```python
            bar_offset: Fraction = bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            lead_voice: int | None = get_lead_voice_for_bar(bar, passage_assignments)
            # Bass staggers when soprano leads
            bass_stagger: Fraction = RHYTHM_STAGGER_OFFSET if lead_voice == 0 else Fraction(0)
            current_offset = bar_offset + bass_stagger
```

Replace with:

```python
            bar_offset: Fraction = bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            # Use start_beat from figuration
            beat_value = Fraction(1, 4)  # Quarter note
            current_offset = bar_offset + (figured_bar.start_beat - 1) * beat_value
```

### B7. Verify Phase B

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c "cd /d D:\projects\Barok\barok\source\andante && set PYTHONPATH=. && D:\projects\Barok\barok\.venv\Scripts\python.exe main.py briefs/builder/invention.brief" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

Check output:
```powershell
Get-Content D:\projects\Barok\barok\source\andante\output\invention.note | Select-Object -First 80
```

**Verify:**
1. Bass durations are valid values (1/4, 1/8, 1/16) — no 3/32 or other fractions
2. Bass has continuous motion within schema sections
3. Bass notes in accompanying bars start on beat 2 (offset ends in .25)

### B8. Commit Phase B

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c ""C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante add -A && "C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante commit -m "fix: bass vocabulary with fixed durations and motor rhythm"" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

---

## Phase C: Soprano Beat-Class + Anacrusis

### C1. Add `compute_effective_gap` to `bar_context.py`

Add this function to `builder/figuration/bar_context.py`:

```python
def compute_effective_gap(
    gap_duration: Fraction,
    start_beat: int,
    metre: str,
) -> Fraction:
    """Compute effective gap duration based on start beat.
    
    Args:
        gap_duration: Original gap between anchors (whole notes)
        start_beat: 1 or 2
        metre: Time signature string like "4/4"
    
    Returns:
        Adjusted gap duration. If start_beat is 2, reduces by one beat.
    """
    if start_beat == 1:
        return gap_duration
    parts = metre.split("/")
    beat_value = Fraction(1, int(parts[1]))
    reduced = gap_duration - beat_value
    if reduced < beat_value:
        reduced = beat_value
    return reduced
```

### C2. Add anacrusis function to `bar_context.py`

Add this function to `builder/figuration/bar_context.py`:

```python
def should_generate_anacrusis(
    bar: int,
    voice: str,
    passage_assignments: Sequence[PassageAssignment] | None,
) -> bool:
    """Determine if anacrusis should be generated for this bar.
    
    Anacrusis is generated when:
    - This voice is accompanying (beat class = 2)
    - The passage function is 'subject' or 'answer'
    
    Args:
        bar: Bar number
        voice: "soprano" or "bass"
        passage_assignments: Passage assignments
    
    Returns:
        True if anacrusis should be generated.
    """
    if passage_assignments is None:
        return False
    beat_class = compute_beat_class(voice, bar, passage_assignments)
    if beat_class != 2:
        return False
    function = get_function_for_bar(bar, passage_assignments)
    return function in ("subject", "answer")
```

### C3. Update `figurate()` signature in `figurate.py`

Add `passage_assignments` parameter to the function signature:

```python
def figurate(
    anchors: Sequence[Anchor],
    key: "Key",
    metre: str,
    seed: int,
    density: str = "medium",
    affect_character: str = "plain",
    voice: str = "soprano",
    soprano_figured_bars: list[FiguredBar] | None = None,
    passage_assignments: Sequence[PassageAssignment] | None = None,
) -> list[FiguredBar]:
```

Add import at top of file:
```python
from builder.figuration.bar_context import (
    compute_bar_function,
    compute_beat_class,
    compute_effective_gap,
    compute_harmonic_tension,
    compute_next_anchor_strength,
    reduce_density,
    should_use_hemiola,
    should_use_overdotted,
)
from builder.types import PassageAssignment
```

### C4. Update `figurate()` main loop for beat-class

Inside the main `while i < len(sorted_anchors) - 1:` loop, after the line:

```python
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
```

Add:

```python
        # Compute beat class for this voice
        start_beat = compute_beat_class(voice, bar_num, passage_assignments)
        
        # Reduce density for accompanying voice
        effective_density = density
        if start_beat == 2:
            effective_density = reduce_density(density)
```

Then find where `gap` is computed:

```python
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        gap = offset_b - offset_a
```

Change to:

```python
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        raw_gap = offset_b - offset_a
        effective_gap = compute_effective_gap(raw_gap, start_beat, metre)
```

Update all references to `gap` to use `effective_gap` instead.
Update all references to `density` in figure selection to use `effective_density` instead.

### C5. Update `realise_figure_to_bar` in `realiser.py`

Add `start_beat` parameter:

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

Update the return statement at the end:

```python
    return FiguredBar(
        bar=bar,
        degrees=tuple(absolute_degrees),
        durations=durations,
        figure_name=figure.name,
        start_beat=start_beat,
    )
```

### C6. Update calls to `realise_figure_to_bar` in `figurate.py`

Find all calls to `realise_figure_to_bar` and add `start_beat=start_beat`:

In the main loop:
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

In `_apply_schema_figuration()`:
```python
        figured_bar = realise_figure_to_bar(
            figure=figure,
            bar=bar_num,
            start_degree=_get_degree(anchor_a, role),
            gap_duration=gap,
            metre=metre,
            start_beat=1,  # Schema figuration uses beat 1
        )
```

### C7. Update soprano offset calculation in `realisation.py`

In the soprano loop, find:

```python
        bar_offset: Fraction = bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
        lead_voice: int | None = get_lead_voice_for_bar(bar, passage_assignments)
        # Soprano staggers when bass leads
        soprano_stagger: Fraction = RHYTHM_STAGGER_OFFSET if lead_voice == 1 else Fraction(0)
        current_offset = bar_offset + soprano_stagger
```

Replace with:

```python
        bar_offset: Fraction = bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
        # Use start_beat from figuration
        beat_value = Fraction(1, 4)  # Quarter note
        current_offset = bar_offset + (figured_bar.start_beat - 1) * beat_value
```

### C8. Update soprano `figurate()` call in `realisation.py`

Find the soprano figuration call:

```python
    figured_bars = figurate(
        anchors=anchors,
        key=key,
        metre=genre_config.metre,
        seed=seed,
        density=density,
        affect_character=character,
    )
```

Add `passage_assignments`:

```python
    figured_bars = figurate(
        anchors=anchors,
        key=key,
        metre=genre_config.metre,
        seed=seed,
        density=density,
        affect_character=character,
        passage_assignments=passage_assignments,
    )
```

### C9. Add anacrusis generation to `bass_figurate.py`

Update `figurate_bass()` in `bass_figurate.py`:

```python
def figurate_bass(
    anchors: Sequence[Anchor],
    metre: str,
    seed: int,
    density: str = "medium",
    passage_assignments: Sequence[PassageAssignment] | None = None,
) -> list[FiguredBar]:
    """Figurate bass voice using bass-specific patterns."""
    from builder.figuration.bar_context import should_generate_anacrusis
    
    if len(anchors) < 2:
        return []
    sorted_anchors = sorted(anchors, key=lambda a: _parse_bar_beat(a.bar_beat))
    schema_sections = detect_schema_sections(sorted_anchors)
    figured_bars: list[FiguredBar] = []
    
    # Check if first bar needs anacrusis
    first_bar = _parse_bar_beat(sorted_anchors[0].bar_beat)[0]
    if should_generate_anacrusis(first_bar, "bass", passage_assignments):
        anacrusis_bar = _generate_anacrusis(
            target_degree=_get_degree(sorted_anchors[0]),
            seed=seed,
        )
        figured_bars.append(anacrusis_bar)
    
    for i in range(len(sorted_anchors) - 1):
        anchor_a = sorted_anchors[i]
        anchor_b = sorted_anchors[i + 1]
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
        start_beat = compute_beat_class("bass", bar_num, passage_assignments)
        effective_density = density
        if start_beat == 2:
            effective_density = reduce_density(density)
        is_motor = is_motor_context(bar_num, schema_sections, sorted_anchors)
        degree_a = _get_degree(anchor_a)
        degree_b = _get_degree(anchor_b)
        interval = compute_interval(degree_a, degree_b)
        figure = _select_bass_figure(
            interval=interval,
            is_motor=is_motor,
            density=effective_density,
            seed=seed + i,
        )
        if figure is None:
            figure = {
                "name": "bass_fallback",
                "degrees": [0],
                "durations": ["1/2"],
                "character": "sustained",
                "direction": "static",
                "motor": False,
            }
        figured_bar = _figure_to_figured_bar(
            figure=figure,
            bar=bar_num,
            start_degree=degree_a,
            start_beat=start_beat,
        )
        figured_bars.append(figured_bar)
    return figured_bars


def _generate_anacrusis(
    target_degree: int,
    seed: int,
) -> FiguredBar:
    """Generate a 4-note anacrusis leading to target degree.
    
    The anacrusis is a scalar run of 16th notes leading up or down
    to the target degree, placed in bar 0 (the upbeat bar).
    
    Args:
        target_degree: The degree to arrive at on beat 1 of bar 1
        seed: Random seed
    
    Returns:
        FiguredBar for bar 0 with anacrusis.
    """
    import random
    rng = random.Random(seed)
    if rng.random() < 0.6:
        degrees = [target_degree - 3, target_degree - 2, target_degree - 1, target_degree]
    else:
        degrees = [target_degree + 3, target_degree + 2, target_degree + 1, target_degree]
    normalized: list[int] = []
    for d in degrees:
        while d < 1:
            d += 7
        while d > 7:
            d -= 7
        normalized.append(d)
    return FiguredBar(
        bar=0,
        degrees=tuple(normalized),
        durations=(Fraction(1, 16), Fraction(1, 16), Fraction(1, 16), Fraction(1, 16)),
        figure_name="anacrusis_run",
        start_beat=1,
    )
```

### C10. Handle anacrusis bar in `realisation.py`

In the bass loop, add handling for bar 0 at the start of the loop:

```python
        for i, figured_bar in enumerate(bass_figured_bars):
            # Handle anacrusis (bar 0)
            if figured_bar.bar == 0:
                anacrusis_duration = sum(figured_bar.durations)
                current_offset = -anacrusis_duration  # Negative offset before bar 1
                for j, (degree, dur) in enumerate(zip(figured_bar.degrees, figured_bar.durations)):
                    b_midi: int = select_octave(
                        sorted_anchors[0].local_key, degree, bass_median,
                        prev_pitch=prev_bass,
                        voice_range=VOICE_RANGES[3],
                    )
                    prev_bass = b_midi
                    bass_notes.append(Note(
                        offset=current_offset,
                        pitch=b_midi,
                        duration=dur,
                        voice=3,
                        lyric="anacrusis" if j == 0 else "",
                    ))
                    tracer.note_output("bass", current_offset, b_midi, dur)
                    current_offset += dur
                continue
            
            # Normal bar processing
            if i >= len(sorted_anchors):
                break
            # ... rest of existing loop ...
```

Note: The anacrusis bar needs special handling because it doesn't correspond to an anchor.

### C11. Remove `RHYTHM_STAGGER_OFFSET`

In `shared/constants.py`, delete these lines:

```python
# Rhythmic stagger for non-lead voice (one eighth note in whole-note units)
RHYTHM_STAGGER_OFFSET: Fraction = Fraction(1, 8)
```

Remove any remaining imports of `RHYTHM_STAGGER_OFFSET` from `realisation.py`.

### C12. Verify Phase C

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c "cd /d D:\projects\Barok\barok\source\andante && set PYTHONPATH=. && D:\projects\Barok\barok\.venv\Scripts\python.exe main.py briefs/builder/invention.brief" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

Check output:
```powershell
Get-Content D:\projects\Barok\barok\source\andante\output\invention.note | Select-Object -First 100
```

**Verify:**
1. Soprano notes in lead bars start on beat 1 (offset 0.0, 1.0, 2.0)
2. Soprano notes in accompany bars start on beat 2 (offset ends in .25)
3. Bass anacrusis appears with negative offset (before bar 1)
4. No fractional offsets like 0.125 (the old stagger)

### C13. Commit Phase C

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c ""C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante add -A && "C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante commit -m "fix: beat-class timing and anacrusis for rhythm complementarity"" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

---

## Summary of New Files

### New files created:
- `data/figuration/bass_diminutions.yaml`
- `builder/figuration/bass_figurate.py`

### Modified files:
- `builder/figuration/bar_context.py` — add `reduce_density`, `is_motor_context`, `compute_effective_gap`, `should_generate_anacrusis`
- `builder/figuration/types.py` — add `start_beat` field to `FiguredBar`
- `builder/figuration/figurate.py` — add `passage_assignments` param, beat-class logic
- `builder/figuration/realiser.py` — add `start_beat` parameter
- `builder/realisation.py` — use `figurate_bass`, use `start_beat`, handle anacrusis, remove stagger
- `shared/constants.py` — remove `RHYTHM_STAGGER_OFFSET`

---

## Troubleshooting

### YAML parsing errors

If bass_diminutions.yaml fails to parse:
1. Check indentation (2 spaces, no tabs)
2. Check fraction format: `"1/16"` with quotes (must be string)
3. Test: `python -c "import yaml; yaml.safe_load(open('data/figuration/bass_diminutions.yaml'))"`

### Import errors

If `ModuleNotFoundError`:
1. Verify file exists in correct location
2. Check import path matches file path

### Duration errors

If durations are still fractional (3/32):
1. Verify `figurate_bass()` is being called (not `figurate()`)
2. Check bass_diminutions.yaml has string durations like `"1/16"`

### Beat position errors

If notes still on wrong beats:
1. Verify `figured_bar.start_beat` is set correctly
2. Check formula: `offset = bar_offset + (start_beat - 1) * beat_value`

### Anacrusis not appearing

If no anacrusis:
1. Check `should_generate_anacrusis()` returns True
2. Verify passage function is "subject" or "answer"
3. Check anacrusis FiguredBar has bar=0
