# Rhythm Implementation Instructions (Revised)

## Overview

This document provides step-by-step implementation instructions for the rhythm fix. Follow these instructions exactly in order. No musical knowledge required.

**Working directory:** `D:\projects\Barok\barok\source\andante`

**Three phases:**
- Phase A: Refactor modules (no behaviour change)
- Phase B: Bass vocabulary replacement (fix what bass plays)
- Phase C: Beat-class timing + anacrusis (fix when bass plays)

---

## Phase A: Module Refactoring

### A1. Create `builder/figuration/phrase.py`

Create new file. Copy these functions from `figurate.py`, removing the leading underscore:

```python
"""Phrase structure analysis for figuration."""
import random
from typing import Sequence

from builder.figuration.selector import determine_phrase_position
from builder.figuration.types import PhrasePosition
from builder.types import Anchor

MIN_SCHEMA_SECTION_ANCHORS: int = 2
MAX_SCHEMA_SECTION_ANCHORS: int = 4
DEFORMATION_PROBABILITY: float = 0.15


def detect_schema_sections(anchors: Sequence[Anchor]) -> list[tuple[int, int]]:
    """Detect contiguous schema sections in anchor sequence."""
    # Copy body from figurate.py _detect_schema_sections
    sections: list[tuple[int, int]] = []
    i = 0
    while i < len(anchors):
        schema = anchors[i].schema.lower() if anchors[i].schema else ""
        if not schema:
            i += 1
            continue
        start = i
        while i < len(anchors) and anchors[i].schema and anchors[i].schema.lower() == schema:
            if i - start >= MAX_SCHEMA_SECTION_ANCHORS:
                break
            i += 1
        if i - start >= MIN_SCHEMA_SECTION_ANCHORS:
            sections.append((start, i))
    return sections


def in_schema_section(idx: int, sections: list[tuple[int, int]]) -> tuple[int, int] | None:
    """Check if index is start of a schema section."""
    # Copy body from figurate.py _in_schema_section
    for start, end in sections:
        if idx == start:
            return (start, end)
    return None


def select_phrase_deformation(rng: random.Random, total_bars: int) -> str | None:
    """Select phrase deformation type with low probability."""
    # Copy body from figurate.py _select_phrase_deformation
    if total_bars < 6:
        return None
    if rng.random() > DEFORMATION_PROBABILITY:
        return None
    return rng.choice(["early_cadence", "extended_continuation"])


def determine_position_with_deformation(
    bar: int,
    total_bars: int,
    schema_type: str | None,
    deformation: str | None,
) -> PhrasePosition:
    """Determine phrase position accounting for deformation."""
    # Copy body from figurate.py _determine_position_with_deformation
    base_pos = determine_phrase_position(bar, total_bars, schema_type)
    if deformation is None:
        return base_pos
    if deformation == "early_cadence":
        cadence_start = max(2, (3 * total_bars) // 4)
        if bar == cadence_start - 1:
            return PhrasePosition(
                position="cadence",
                bars=(cadence_start - 1, total_bars),
                character="plain",
                sequential=False,
            )
    elif deformation == "extended_continuation":
        cadence_start = max(2, (3 * total_bars) // 4)
        if bar == cadence_start:
            return PhrasePosition(
                position="continuation",
                bars=(base_pos.bars[0], cadence_start),
                character="energetic",
                sequential=base_pos.sequential,
            )
    return base_pos
```

### A2. Create `builder/figuration/bar_context.py`

Create new file:

```python
"""Per-bar context computation for figuration."""
from fractions import Fraction
from typing import Sequence

from builder.figuration.types import PhrasePosition
from builder.types import Anchor, PassageAssignment, Role


def compute_harmonic_tension(
    anchor_a: Anchor,
    phrase_pos: PhrasePosition,
    role: Role,
) -> str:
    """Compute harmonic tension from schema type, bass degree, and bar function."""
    if phrase_pos.position == "cadence":
        base_tension = "low"
    elif phrase_pos.position == "continuation":
        base_tension = "medium"
    else:
        base_tension = "low"
    bass = anchor_a.lower_degree
    if bass in (2, 4, 7):
        if base_tension == "low":
            return "medium"
        return "high"
    if bass in (5,):
        return "medium"
    schema = anchor_a.schema.lower() if anchor_a.schema else ""
    if schema in ("monte", "fonte"):
        return "medium"
    return base_tension


def compute_bar_function(phrase_pos: PhrasePosition, bar_num: int, total_bars: int) -> str:
    """Compute bar function for rhythm realisation."""
    if phrase_pos.position == "cadence":
        return "cadential"
    if phrase_pos.sequential:
        return "schema_arrival"
    if bar_num == total_bars - 2:
        return "preparatory"
    return "passing"


def compute_next_anchor_strength(
    idx: int,
    anchors: Sequence[Anchor],
    total_bars: int,
) -> str:
    """Compute strength of next anchor for anacrusis handling."""
    if idx + 2 >= len(anchors):
        return "strong"
    bar_beat = anchors[idx + 1].bar_beat
    parts = bar_beat.split(".")
    next_bar = int(parts[0])
    if next_bar == 1 or next_bar == (total_bars // 2) + 1:
        return "strong"
    if next_bar >= total_bars - 1:
        return "strong"
    return "weak"


def should_use_hemiola(bar_num: int, total_bars: int, metre: str, deformation: str | None) -> bool:
    """Determine if hemiola should be used for this bar."""
    if metre != "3/4":
        return False
    if total_bars < 6:
        return False
    hemiola_bar = total_bars - 2
    if bar_num == hemiola_bar or bar_num == hemiola_bar + 1:
        if deformation == "early_cadence":
            return False
        return True
    return False


def should_use_overdotted(affect_character: str, phrase_pos: PhrasePosition) -> bool:
    """Determine if overdotted rhythms should be used."""
    return affect_character == "ornate"


def get_lead_voice_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
) -> int | None:
    """Look up lead voice for a given bar number.
    
    Returns:
        0 if upper voice leads, 1 if lower voice leads, None if equal.
    """
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.lead_voice
    return None


def get_function_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
) -> str | None:
    """Look up passage function for a given bar number."""
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.function
    return None


def compute_beat_class(
    voice: str,
    bar: int,
    passage_assignments: Sequence[PassageAssignment] | None,
) -> int:
    """Compute which beat this voice starts on for a given bar.
    
    Args:
        voice: "soprano" or "bass"
        bar: Bar number
        passage_assignments: Passage assignments with lead_voice info
    
    Returns:
        1 if voice leads or equal, 2 if voice accompanies.
    """
    lead_voice = get_lead_voice_for_bar(bar, passage_assignments)
    voice_index = 0 if voice == "soprano" else 1
    if lead_voice is None:
        return 1
    if lead_voice == voice_index:
        return 1
    return 2


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

### A3. Create `builder/figuration/cadential.py`

Create new file:

```python
"""Cadential figure selection."""
import random

from builder.figuration.loader import get_cadential
from builder.figuration.types import CadentialFigure, Figure

CADENTIAL_UNDERSTATEMENT_PROBABILITY: float = 0.10


def select_cadential_figure(
    to_degree: int,
    interval: str,
    is_minor: bool,
    seed: int,
    rng: random.Random,
) -> Figure | None:
    """Select from cadential table for phrase endings."""
    if rng.random() < CADENTIAL_UNDERSTATEMENT_PROBABILITY:
        return None
    cadential = get_cadential()
    if to_degree == 1:
        target = "target_1"
    elif to_degree == 5:
        target = "target_5"
    else:
        return None
    if target not in cadential:
        return None
    approaches = cadential[target]
    approach_key = interval_to_approach_key(interval)
    if approach_key not in approaches:
        if "unison" in approaches:
            approach_key = "unison"
        else:
            return None
    cadential_figures = approaches[approach_key]
    if not cadential_figures:
        return None
    if is_minor:
        cadential_figures = [cf for cf in cadential_figures if cadential_minor_safe(cf)]
        if not cadential_figures:
            cadential_figures = approaches[approach_key]
    rng_local = random.Random(seed)
    selected_cf = rng_local.choice(cadential_figures)
    return cadential_to_figure(selected_cf)


def cadential_to_figure(cf: CadentialFigure) -> Figure:
    """Convert CadentialFigure to regular Figure for realisation."""
    return Figure(
        name=cf.name,
        degrees=cf.degrees,
        contour=cf.contour,
        polarity="balanced",
        arrival="stepwise" if len(cf.degrees) > 2 else "direct",
        placement="end",
        character="plain",
        harmonic_tension="low",
        max_density="high" if len(cf.degrees) > 4 else "medium",
        cadential_safe=True,
        repeatable=False,
        requires_compensation=False,
        compensation_direction=None,
        is_compound=False,
        minor_safe=True,
        requires_leading_tone=cf.contour in ("trilled_resolution", "leading_tone_resolution"),
        weight=1.0,
    )


def cadential_minor_safe(cf: CadentialFigure) -> bool:
    """Check if cadential figure is safe in minor key."""
    return cf.contour not in ("trilled_resolution",)


def interval_to_approach_key(interval: str) -> str:
    """Map interval name to cadential approach key."""
    mapping = {
        "unison": "unison",
        "step_up": "step_up",
        "step_down": "step_down",
        "third_up": "third_up",
        "third_down": "third_down",
        "fourth_up": "fourth_up",
        "fourth_down": "fourth_down",
        "fifth_up": "fifth_up",
        "fifth_down": "fifth_down",
    }
    return mapping.get(interval, "step_down")
```

### A4. Create `builder/figuration/selection.py`

Create new file:

```python
"""Figure selection logic."""
import random

from builder.figuration.types import Figure
from shared.constants import MISBEHAVIOUR_PROBABILITY


def apply_misbehaviour(
    candidates: list[Figure],
    all_figures: list[Figure],
    seed: int,
) -> list[Figure]:
    """Apply controlled misbehaviour to relax filters occasionally."""
    if not candidates:
        return candidates
    rng = random.Random(seed)
    if rng.random() < MISBEHAVIOUR_PROBABILITY:
        return all_figures if all_figures else candidates
    return candidates


def sort_by_weight(figures: list[Figure]) -> list[Figure]:
    """Sort figures by weight descending, then by name for determinism."""
    return sorted(figures, key=lambda f: (-f.weight, f.name))


def select_figure(
    figures: list[Figure],
    seed: int,
    weight_overrides: list[float] | None = None,
) -> Figure | None:
    """Select a figure using weighted random selection."""
    if not figures:
        return None
    if len(figures) == 1:
        return figures[0]
    rng = random.Random(seed)
    if weight_overrides is not None:
        weights = weight_overrides
    else:
        weights = [f.weight for f in figures]
    total = sum(weights)
    if total <= 0:
        return rng.choice(figures)
    r = rng.random() * total
    cumulative = 0.0
    for i, w in enumerate(weights):
        cumulative += w
        if r <= cumulative:
            return figures[i]
    return figures[-1]
```

### A5. Create `builder/realisation_util.py`

Create new file:

```python
"""Utility functions for realisation."""
from fractions import Fraction
from typing import Sequence

from builder.config_loader import get_expansion_for_function, load_expansions
from builder.types import Anchor, GenreConfig, PassageAssignment, VoiceExpansionConfig
from shared.constants import STACCATO_DURATION_THRESHOLD


def get_function_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
) -> str | None:
    """Look up passage function for a given bar number."""
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.function
    return None


def get_lead_voice_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
) -> int | None:
    """Look up lead voice for a given bar number."""
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.lead_voice
    return None


def get_passage_end_offset(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
    beats_per_bar: int,
) -> Fraction | None:
    """Return offset where current passage ends."""
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            end_offset = Fraction(assignment.end_bar * beats_per_bar, 4)
            return end_offset
    return None


def get_expansion_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
    genre_config: GenreConfig,
    expansions: dict[str, VoiceExpansionConfig],
) -> VoiceExpansionConfig:
    """Get voice expansion config for a given bar."""
    function: str | None = get_function_for_bar(bar, assignments)
    if function is None:
        function = "episode"
    return get_expansion_for_function(
        function=function,
        function_map=genre_config.function_map,
        expansions=expansions,
    )


def build_stacked_lyric(
    section: str | None,
    schema: str | None,
    function: str | None,
    figure: str | None,
) -> str:
    """Build stacked lyric from section, schema, passage function, and figure name."""
    parts: list[str] = []
    if section:
        parts.append(section)
    if schema:
        parts.append(schema)
    if function:
        parts.append(function)
    if figure:
        parts.append(figure)
    return "/".join(parts)


def get_bass_articulation(
    duration: Fraction,
    is_run: bool,
) -> str:
    """Determine articulation marking for bass note."""
    # removed, ugly
    # if duration <= STACCATO_DURATION_THRESHOLD and is_run:
    #     return "stacc"
    return ""


def anchor_sort_key(anchor: Anchor) -> tuple[float, int]:
    """Sort key for anchors: by time, then by upper degree."""
    parts: list[str] = anchor.bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar + beat / 10.0, anchor.upper_degree)


def get_beats_per_bar(metre: str) -> int:
    """Extract beats per bar from metre string."""
    num_str: str = metre.split("/")[0]
    return int(num_str)


def bar_beat_to_offset(bar_beat: str, beats_per_bar: int) -> Fraction:
    """Convert bar.beat string to Fraction offset in whole notes."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    offset_in_beats: Fraction = Fraction(bar - 1) * beats_per_bar + Fraction(beat) - 1
    return offset_in_beats / 4
```

### A6. Create `builder/realisation_bass.py`

Create new file:

```python
"""Bass voice realisation."""
from fractions import Fraction

from builder.types import Note
from shared.constants import CONSONANT_INTERVALS, STRONG_BEAT_DISSONANT


def is_dissonant_interval(soprano_midi: int, bass_midi: int) -> bool:
    """Check if vertical interval between soprano and bass is dissonant."""
    interval = abs(soprano_midi - bass_midi) % 12
    return interval in STRONG_BEAT_DISSONANT


def find_consonant_bass(
    soprano_midi: int,
    bass_midi: int,
    bass_range: tuple[int, int],
) -> int:
    """Find nearest consonant bass pitch by adjusting up or down."""
    interval = abs(soprano_midi - bass_midi) % 12
    if interval not in STRONG_BEAT_DISSONANT:
        return bass_midi
    low, high = bass_range
    for delta in [1, -1, 2, -2]:
        candidate = bass_midi + delta
        if candidate < low or candidate > high:
            continue
        new_interval = abs(soprano_midi - candidate) % 12
        if new_interval in CONSONANT_INTERVALS:
            return candidate
    return bass_midi


def pitch_sounding_at(notes: list[Note], offset: Fraction) -> int | None:
    """Get the pitch sounding at a given offset."""
    for note in notes:
        if note.offset <= offset < note.offset + note.duration:
            return note.pitch
    return None


def adjust_downbeat_consonance(
    soprano_notes: list[Note],
    bass_notes: list[Note],
    beats_per_bar: int,
    total_bars: int,
    bass_range: tuple[int, int],
) -> list[Note]:
    """Adjust bass notes at downbeats to ensure consonance with soprano."""
    downbeats: list[tuple[Fraction, int]] = []
    for bar in range(1, total_bars + 1):
        offset = Fraction((bar - 1) * beats_per_bar, 4)
        downbeats.append((offset, bar))
    adjusted: list[Note] = list(bass_notes)
    for offset, bar in downbeats:
        s_pitch = pitch_sounding_at(soprano_notes, offset)
        if s_pitch is None:
            continue
        for i, note in enumerate(adjusted):
            if note.offset == offset:
                if is_dissonant_interval(s_pitch, note.pitch):
                    new_pitch = find_consonant_bass(s_pitch, note.pitch, bass_range)
                    if new_pitch != note.pitch:
                        adjusted[i] = Note(
                            offset=note.offset,
                            pitch=new_pitch,
                            duration=note.duration,
                            voice=note.voice,
                            lyric=note.lyric,
                        )
                break
    return adjusted
```

### A7. Update imports in `figurate.py`

At top of file, add:

```python
from builder.figuration.bar_context import (
    compute_bar_function,
    compute_harmonic_tension,
    compute_next_anchor_strength,
    should_use_hemiola,
    should_use_overdotted,
)
from builder.figuration.cadential import select_cadential_figure
from builder.figuration.phrase import (
    detect_schema_sections,
    determine_position_with_deformation,
    in_schema_section,
    select_phrase_deformation,
)
from builder.figuration.selection import apply_misbehaviour, select_figure, sort_by_weight
```

Delete these functions from `figurate.py`:
- `_detect_schema_sections`
- `_in_schema_section`
- `_select_phrase_deformation`
- `_determine_position_with_deformation`
- `_compute_harmonic_tension`
- `_compute_bar_function`
- `_compute_next_anchor_strength`
- `_should_use_hemiola`
- `_should_use_overdotted`
- `_select_cadential_figure`
- `_cadential_to_figure`
- `_cadential_minor_safe`
- `_interval_to_approach_key`

Delete these constants from `figurate.py` (now in phrase.py and cadential.py):
- `MIN_SCHEMA_SECTION_ANCHORS`
- `MAX_SCHEMA_SECTION_ANCHORS`
- `DEFORMATION_PROBABILITY`
- `CADENTIAL_UNDERSTATEMENT_PROBABILITY`

Update all function calls to remove underscore prefix.

### A8. Update imports in `selector.py`

Delete these functions from `selector.py` (now in selection.py):
- `apply_misbehaviour`
- `sort_by_weight`
- `select_figure`

Keep all `filter_*` functions, `get_figures_for_interval`, `compute_interval`, `determine_phrase_position`.

### A9. Update imports in `realisation.py`

At top of file, add:

```python
from builder.realisation_bass import adjust_downbeat_consonance
from builder.realisation_util import (
    anchor_sort_key,
    bar_beat_to_offset,
    build_stacked_lyric,
    get_bass_articulation,
    get_beats_per_bar,
    get_expansion_for_bar,
    get_function_for_bar,
    get_lead_voice_for_bar,
    get_passage_end_offset,
)
```

Delete these functions from `realisation.py`:
- `_get_function_for_bar`
- `_get_lead_voice_for_bar`
- `_get_passage_end_offset`
- `_get_expansion_for_bar`
- `_build_stacked_lyric`
- `_get_bass_articulation`
- `_anchor_sort_key`
- `_get_beats_per_bar`
- `_bar_beat_to_offset`
- `_is_dissonant_interval`
- `_find_consonant_bass`
- `_pitch_sounding_at`
- `_adjust_downbeat_consonance`

Update all function calls to remove underscore prefix.

### A10. Verify refactoring

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c "cd /d D:\projects\Barok\barok\source\andante && set PYTHONPATH=. && D:\projects\Barok\barok\.venv\Scripts\python.exe -c "from builder.realisation import realise_with_figuration; print(\"OK\")"" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

### A11. Commit

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c ""C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante add -A && "C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante commit -m "refactor: extract figuration and realisation modules"" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

---

## Phase B: Bass Vocabulary Replacement

### B1. Create `data/figuration/bass_diminutions.yaml`

Create new file with bass-appropriate figures. Key differences from soprano diminutions:
- Fixed durations (always valid baroque values: 1/4, 1/8, 1/16)
- Stepwise motion (scalar runs)
- Continuous patterns (no isolated stabs)

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
    durations: [1/16, 1/16, 1/16, 1/16]
    character: energetic
    direction: ascending
    motor: true

  - name: bass_scalar_up_8th
    degrees: [0, 1, 2, 3]
    durations: [1/8, 1/8, 1/8, 1/8]
    character: plain
    direction: ascending
    motor: true

  - name: bass_step_quarter
    degrees: [0, 1]
    durations: [1/4, 1/4]
    character: sustained
    direction: ascending
    motor: false

  - name: bass_run_up_6
    degrees: [0, 1, 2, 3, 4, 5]
    durations: [1/16, 1/16, 1/16, 1/16, 1/16, 1/16]
    character: energetic
    direction: ascending
    motor: true

# =============================================================================
# STEP_DOWN: descending by step (degree difference = -1 or -2)
# =============================================================================

step_down:
  - name: bass_scalar_down_16th
    degrees: [0, -1, -2, -3]
    durations: [1/16, 1/16, 1/16, 1/16]
    character: energetic
    direction: descending
    motor: true

  - name: bass_scalar_down_8th
    degrees: [0, -1, -2, -3]
    durations: [1/8, 1/8, 1/8, 1/8]
    character: plain
    direction: descending
    motor: true

  - name: bass_step_down_quarter
    degrees: [0, -1]
    durations: [1/4, 1/4]
    character: sustained
    direction: descending
    motor: false

  - name: bass_run_down_6
    degrees: [0, -1, -2, -3, -4, -5]
    durations: [1/16, 1/16, 1/16, 1/16, 1/16, 1/16]
    character: energetic
    direction: descending
    motor: true

# =============================================================================
# THIRD_UP: ascending by third (degree difference = +2 or +3)
# =============================================================================

third_up:
  - name: bass_arpeggio_up_8th
    degrees: [0, 2, 4, 2]
    durations: [1/8, 1/8, 1/8, 1/8]
    character: plain
    direction: ascending
    motor: true

  - name: bass_filled_third_up
    degrees: [0, 1, 2]
    durations: [1/8, 1/8, 1/4]
    character: plain
    direction: ascending
    motor: false

  - name: bass_leap_third_sustained
    degrees: [0, 2]
    durations: [1/4, 1/4]
    character: sustained
    direction: ascending
    motor: false

# =============================================================================
# THIRD_DOWN: descending by third (degree difference = -2 or -3)
# =============================================================================

third_down:
  - name: bass_arpeggio_down_8th
    degrees: [0, -2, -4, -2]
    durations: [1/8, 1/8, 1/8, 1/8]
    character: plain
    direction: descending
    motor: true

  - name: bass_filled_third_down
    degrees: [0, -1, -2]
    durations: [1/8, 1/8, 1/4]
    character: plain
    direction: descending
    motor: false

  - name: bass_leap_third_down_sustained
    degrees: [0, -2]
    durations: [1/4, 1/4]
    character: sustained
    direction: descending
    motor: false

# =============================================================================
# FOURTH_UP / FOURTH_DOWN: fourths
# =============================================================================

fourth_up:
  - name: bass_scalar_fourth_up
    degrees: [0, 1, 2, 3]
    durations: [1/8, 1/8, 1/8, 1/8]
    character: plain
    direction: ascending
    motor: true

  - name: bass_fourth_sustained
    degrees: [0, 3]
    durations: [1/4, 1/4]
    character: sustained
    direction: ascending
    motor: false

fourth_down:
  - name: bass_scalar_fourth_down
    degrees: [0, -1, -2, -3]
    durations: [1/8, 1/8, 1/8, 1/8]
    character: plain
    direction: descending
    motor: true

  - name: bass_fourth_down_sustained
    degrees: [0, -3]
    durations: [1/4, 1/4]
    character: sustained
    direction: descending
    motor: false

# =============================================================================
# FIFTH_UP / FIFTH_DOWN: fifths
# =============================================================================

fifth_up:
  - name: bass_arpeggio_fifth_up
    degrees: [0, 2, 4]
    durations: [1/8, 1/8, 1/4]
    character: plain
    direction: ascending
    motor: false

  - name: bass_scalar_fifth_up
    degrees: [0, 1, 2, 3, 4]
    durations: [1/16, 1/16, 1/16, 1/16, 1/8]
    character: energetic
    direction: ascending
    motor: true

  - name: bass_fifth_sustained
    degrees: [0, 4]
    durations: [1/4, 1/4]
    character: sustained
    direction: ascending
    motor: false

fifth_down:
  - name: bass_arpeggio_fifth_down
    degrees: [0, -2, -4]
    durations: [1/8, 1/8, 1/4]
    character: plain
    direction: descending
    motor: false

  - name: bass_scalar_fifth_down
    degrees: [0, -1, -2, -3, -4]
    durations: [1/16, 1/16, 1/16, 1/16, 1/8]
    character: energetic
    direction: descending
    motor: true

  - name: bass_fifth_down_sustained
    degrees: [0, -4]
    durations: [1/4, 1/4]
    character: sustained
    direction: descending
    motor: false

# =============================================================================
# UNISON: same pitch (degree difference = 0)
# =============================================================================

unison:
  - name: bass_sustained_half
    degrees: [0]
    durations: [1/2]
    character: sustained
    direction: static
    motor: false

  - name: bass_repeated_quarters
    degrees: [0, 0]
    durations: [1/4, 1/4]
    character: plain
    direction: static
    motor: false

  - name: bass_pedal_eighths
    degrees: [0, 0, 0, 0]
    durations: [1/8, 1/8, 1/8, 1/8]
    character: energetic
    direction: static
    motor: true

# =============================================================================
# SIXTH_UP / SIXTH_DOWN / OCTAVE: larger intervals
# =============================================================================

sixth_up:
  - name: bass_scalar_sixth_up
    degrees: [0, 1, 2, 3, 4, 5]
    durations: [1/16, 1/16, 1/16, 1/16, 1/8, 1/8]
    character: energetic
    direction: ascending
    motor: true

  - name: bass_sixth_sustained
    degrees: [0, 5]
    durations: [1/4, 1/4]
    character: sustained
    direction: ascending
    motor: false

sixth_down:
  - name: bass_scalar_sixth_down
    degrees: [0, -1, -2, -3, -4, -5]
    durations: [1/16, 1/16, 1/16, 1/16, 1/8, 1/8]
    character: energetic
    direction: descending
    motor: true

  - name: bass_sixth_down_sustained
    degrees: [0, -5]
    durations: [1/4, 1/4]
    character: sustained
    direction: descending
    motor: false

octave_up:
  - name: bass_octave_arpeggio_up
    degrees: [0, 2, 4, 7]
    durations: [1/8, 1/8, 1/8, 1/8]
    character: plain
    direction: ascending
    motor: true

  - name: bass_octave_sustained
    degrees: [0, 7]
    durations: [1/4, 1/4]
    character: sustained
    direction: ascending
    motor: false

octave_down:
  - name: bass_octave_arpeggio_down
    degrees: [0, -2, -4, -7]
    durations: [1/8, 1/8, 1/8, 1/8]
    character: plain
    direction: descending
    motor: true

  - name: bass_octave_down_sustained
    degrees: [0, -7]
    durations: [1/4, 1/4]
    character: sustained
    direction: descending
    motor: false
```

### B2. Create `builder/figuration/bass_figurate.py`

Create new file for bass-specific figuration:

```python
"""Bass-specific figuration using bass_diminutions.yaml.

Unlike soprano figuration which uses scaled durations, bass figuration
uses fixed durations from bass_diminutions.yaml to ensure valid baroque
note values and continuous motor rhythm.
"""
from fractions import Fraction
from typing import Sequence

import yaml

from builder.figuration.bar_context import (
    compute_beat_class,
    get_function_for_bar,
    get_lead_voice_for_bar,
    is_motor_context,
    reduce_density,
)
from builder.figuration.phrase import detect_schema_sections
from builder.figuration.selector import compute_interval
from builder.figuration.types import FiguredBar
from builder.types import Anchor, PassageAssignment

# Cache for loaded bass diminutions
_bass_diminutions: dict | None = None


def _load_bass_diminutions() -> dict:
    """Load bass_diminutions.yaml, caching result."""
    global _bass_diminutions
    if _bass_diminutions is None:
        with open("data/figuration/bass_diminutions.yaml", "r") as f:
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
        # Try to find a fallback
        if interval.endswith("_up"):
            interval = "step_up"
        elif interval.endswith("_down"):
            interval = "step_down"
        else:
            interval = "unison"
    figures = diminutions.get(interval, [])
    if not figures:
        return None
    # Filter by motor context
    if is_motor:
        motor_figures = [f for f in figures if f.get("motor", False)]
        if motor_figures:
            figures = motor_figures
    # Filter by character based on density
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
    # Select deterministically based on seed
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
    # Convert relative degrees to absolute (1-7 range)
    absolute_degrees: list[int] = []
    for rel in relative_degrees:
        absolute = start_degree + rel
        while absolute < 1:
            absolute += 7
        while absolute > 7:
            absolute -= 7
        absolute_degrees.append(absolute)
    # Parse durations from strings like "1/16" to Fraction
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
        # Determine beat class
        start_beat = compute_beat_class("bass", bar_num, passage_assignments)
        # Reduce density for accompanying voice
        effective_density = density
        if start_beat == 2:
            effective_density = reduce_density(density)
        # Check if we're in motor context
        is_motor = is_motor_context(bar_num, schema_sections, sorted_anchors)
        # Compute interval
        degree_a = _get_degree(anchor_a)
        degree_b = _get_degree(anchor_b)
        interval = compute_interval(degree_a, degree_b)
        # Select figure
        figure = _select_bass_figure(
            interval=interval,
            is_motor=is_motor,
            density=effective_density,
            seed=seed + i,
        )
        if figure is None:
            # Fallback: sustained note
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

### B3. Update `FiguredBar` in `types.py`

Add `start_beat` field with default value:

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

    def get_onsets(self, bar_offset: Fraction) -> set[Fraction]:
        """Return onset positions (absolute offsets) for this bar's notes."""
        onsets: set[Fraction] = set()
        current: Fraction = bar_offset
        for dur in self.durations:
            onsets.add(current)
            current += dur
        return onsets
```

### B4. Update `realisation.py` to use `figurate_bass`

In the `if genre_config.bass_treatment == "contrapuntal":` block, replace the `figurate()` call with `figurate_bass()`:

Find this code:
```python
    if genre_config.bass_treatment == "contrapuntal":
        bass_figured_bars = figurate(
            anchors=anchors,
            key=key,
            metre=genre_config.metre,
            seed=seed + 1000,
            density=density,
            affect_character=character,
            voice="bass",
            soprano_figured_bars=figured_bars,
        )
```

Replace with:
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

### B5. Update bass note generation to use `start_beat`

In the bass loop within `realise_with_figuration()`, update the offset calculation.

Find this code:
```python
            bar_offset: Fraction = _bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            lead_voice: int | None = _get_lead_voice_for_bar(bar, passage_assignments)
            # Bass staggers when soprano leads
            bass_stagger: Fraction = RHYTHM_STAGGER_OFFSET if lead_voice == 0 else Fraction(0)
            current_offset = bar_offset + bass_stagger
```

Replace with:
```python
            bar_offset: Fraction = bar_beat_to_offset(anchor.bar_beat, beats_per_bar)
            # Use start_beat from figuration
            beat_value = Fraction(1, 4)  # Quarter note in 4/4
            current_offset = bar_offset + (figured_bar.start_beat - 1) * beat_value
```

Also remove the `RHYTHM_STAGGER_OFFSET` import if not used elsewhere.

### B6. Verify Phase B

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
3. Bass notes in accompanying bars start on beat 2 (offset 0.25, 1.25, etc.)

### B7. Commit Phase B

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c ""C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante add -A && "C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante commit -m "fix: bass vocabulary with fixed durations and motor rhythm"" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

---

## Phase C: Soprano Beat-Class + Anacrusis

### C1. Update `figurate()` signature

In `figurate.py`, add `passage_assignments` parameter:

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

Add import at top:
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

### C2. Update `figurate()` main loop for beat-class

Inside the main loop, after computing `bar_num`, add beat-class logic:

```python
        bar_num = _parse_bar_beat(anchor_a.bar_beat)[0]
        
        # Compute beat class for soprano
        start_beat = compute_beat_class(voice, bar_num, passage_assignments)
        
        # Compute effective gap (reduced if accompanying)
        offset_a = _bar_beat_to_offset(anchor_a.bar_beat, metre)
        offset_b = _bar_beat_to_offset(anchor_b.bar_beat, metre)
        raw_gap = offset_b - offset_a
        effective_gap = compute_effective_gap(raw_gap, start_beat, metre)
        
        # Reduce density for accompanying voice
        effective_density = density
        if start_beat == 2:
            effective_density = reduce_density(density)
```

Update all uses of `gap` to use `effective_gap`.
Update all uses of `density` in figure selection to use `effective_density`.

### C3. Update `realise_figure_to_bar` in `realiser.py`

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

Update the return statement:
```python
    return FiguredBar(
        bar=bar,
        degrees=tuple(absolute_degrees),
        durations=durations,
        figure_name=figure.name,
        start_beat=start_beat,
    )
```

### C4. Update all calls to `realise_figure_to_bar` in `figurate.py`

Pass `start_beat` to every call:

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
            overdotted=_should_use_overdotted(affect_character, phrase_pos),
            start_beat=start_beat,
        )
```

Also update calls in `_apply_schema_figuration()`.

### C5. Update soprano note generation in `realisation.py`

Find this code in the soprano loop:
```python
        lead_voice: int | None = _get_lead_voice_for_bar(bar, passage_assignments)
        # Soprano staggers when bass leads
        soprano_stagger: Fraction = RHYTHM_STAGGER_OFFSET if lead_voice == 1 else Fraction(0)
        current_offset = bar_offset + soprano_stagger
```

Replace with:
```python
        # Use start_beat from figuration
        beat_value = Fraction(1, 4)  # Quarter note
        current_offset = bar_offset + (figured_bar.start_beat - 1) * beat_value
```

### C6. Update soprano `figurate()` call in `realisation.py`

Pass `passage_assignments`:

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

### C7. Add anacrusis generation

In `builder/figuration/bar_context.py`, add:

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

### C8. Implement anacrusis in `bass_figurate.py`

Update `figurate_bass()` to generate anacrusis:

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
        # ... rest of existing loop ...
```

Add anacrusis generator:

```python
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
    # Decide direction: approach from below or above
    if rng.random() < 0.6:
        # Approach from below (more common)
        degrees = [target_degree - 3, target_degree - 2, target_degree - 1, target_degree]
    else:
        # Approach from above
        degrees = [target_degree + 3, target_degree + 2, target_degree + 1, target_degree]
    # Normalize to 1-7 range
    normalized: list[int] = []
    for d in degrees:
        while d < 1:
            d += 7
        while d > 7:
            d -= 7
        normalized.append(d)
    return FiguredBar(
        bar=0,  # Anacrusis bar
        degrees=tuple(normalized),
        durations=(Fraction(1, 16), Fraction(1, 16), Fraction(1, 16), Fraction(1, 16)),
        figure_name="anacrusis_run",
        start_beat=1,  # Anacrusis starts on beat 4 of previous bar conceptually
    )
```

### C9. Handle anacrusis in realisation

In `realisation.py`, when processing figured bars, handle bar 0 specially:

In the soprano loop, before processing:
```python
    for i, figured_bar in enumerate(figured_bars):
        if figured_bar.bar == 0:
            # Anacrusis: place in last beat of "bar 0" (negative offset)
            # Actually: place at offset -0.25 (beat 4 of conceptual bar 0)
            beat_value = Fraction(1, 4)
            anacrusis_duration = sum(figured_bar.durations)
            current_offset = -anacrusis_duration  # Start before bar 1
            # ... generate notes ...
            continue
        # Normal bar processing
        if i >= len(sorted_anchors):
            break
        anchor = sorted_anchors[i]
        # ... rest of loop ...
```

Similar handling needed in bass loop.

### C10. Remove `RHYTHM_STAGGER_OFFSET`

In `shared/constants.py`, delete:
```python
RHYTHM_STAGGER_OFFSET: Fraction = Fraction(1, 8)
```

Remove any remaining imports of `RHYTHM_STAGGER_OFFSET`.

### C11. Verify Phase C

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c "cd /d D:\projects\Barok\barok\source\andante && set PYTHONPATH=. && D:\projects\Barok\barok\.venv\Scripts\python.exe main.py briefs/builder/invention.brief" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

Check output:
```powershell
Get-Content D:\projects\Barok\barok\source\andante\output\invention.note | Select-Object -First 100
```

**Verify:**
1. Soprano notes in lead bars (1-6) start on beat 1 (offset 0.0, 1.0, 2.0)
2. Soprano notes in accompany bars (7+) start on beat 2 (offset 6.25, 7.25)
3. Bass anacrusis appears before bar 1 (negative offset or offset near 0)
4. No fractional offsets like 0.125 (the old stagger)

### C12. Commit Phase C

```powershell
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c ""C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante add -A && "C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante commit -m "fix: beat-class timing and anacrusis for rhythm complementarity"" > D:\temp_output.txt 2>&1' -WindowStyle Hidden -Wait
Get-Content D:\temp_output.txt
```

---

## Summary of Files

### New files created:
- `builder/figuration/phrase.py`
- `builder/figuration/bar_context.py`
- `builder/figuration/cadential.py`
- `builder/figuration/selection.py`
- `builder/figuration/bass_figurate.py`
- `builder/realisation_util.py`
- `builder/realisation_bass.py`
- `data/figuration/bass_diminutions.yaml`

### Modified files:
- `builder/figuration/types.py` — add `start_beat` field
- `builder/figuration/figurate.py` — extract functions, add beat-class logic
- `builder/figuration/realiser.py` — add `start_beat` parameter
- `builder/figuration/selector.py` — remove moved functions
- `builder/realisation.py` — use `figurate_bass`, use `start_beat`, remove stagger
- `shared/constants.py` — remove `RHYTHM_STAGGER_OFFSET`

---

## Troubleshooting

### YAML parsing errors

If bass_diminutions.yaml fails to parse:
1. Check indentation (2 spaces, no tabs)
2. Check fraction format: `"1/16"` not `1/16` (must be string)
3. Run: `python -c "import yaml; yaml.safe_load(open('data/figuration/bass_diminutions.yaml'))"`

### Import errors

If `ModuleNotFoundError`:
1. Verify file exists in correct location
2. Check `__init__.py` exists (can be empty)
3. Verify import path matches file path

### Duration errors

If durations are still fractional (3/32):
1. Verify `figurate_bass()` is being called (not `figurate()`)
2. Check bass_diminutions.yaml has string durations like `"1/16"`
3. Add debug print in `_figure_to_figured_bar()` to see parsed durations

### Beat position errors

If notes still appear on wrong beats:
1. Verify `figured_bar.start_beat` is set correctly
2. Check formula: `offset = bar_offset + (start_beat - 1) * beat_value`
3. Add debug print to see `start_beat` values

### Anacrusis not appearing

If no anacrusis in output:
1. Check `should_generate_anacrusis()` returns True for bar 1
2. Verify passage_assignments has function "subject" or "answer"
3. Check anacrusis bar has bar=0 in FiguredBar
