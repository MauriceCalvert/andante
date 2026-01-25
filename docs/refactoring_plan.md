# Andante Refactoring Plan

## Document Status

**Version:** 1.0.0  
**Target:** architecture.md v1.3.2  
**Created:** 2025-01-20

> **⚠️ PARTIALLY OUTDATED:** This document predates the following architectural changes:
> - Keys are computed from (tonic, mode), no keys/*.yaml files
> - Voice ranges replaced by tessituras (medians) per L003
> - Registers removed from KeyConfig; tessitura moved to GenreConfig
> See architecture.md for current specification.

---

## Executive Summary

This plan transforms Andante from its current multi-file legacy architecture to a clean 6-layer system conforming to architecture.md v1.3.2. The goal is 100% deterministic, note-for-note identical output for 2-voice Invention in C Major with Confident affect.

**Key changes:**
1. DELETE `engine/` folder entirely (~60 files)
2. CREATE `builder/` with 5 modules matching architecture
3. UPDATE `planner/` to emit Layer 1-3 outputs
4. RESTRUCTURE `data/` → `config/` with new YAML schemas
5. VERIFY against `freude_sonata.note` reference

---

## 1. File-by-File Plan

### 1.1 Files to DELETE (entire engine/ folder)

| Path | Action | Rationale |
|------|--------|-----------|
| `engine/__init__.py` | DELETE | Legacy module |
| `engine/__main__.py` | DELETE | Legacy entry point |
| `engine/annotate.py` | DELETE | Not in architecture |
| `engine/arc_loader.py` | DELETE | Replaced by config loader |
| `engine/backtrack.py` | DELETE | CP-SAT replaces backtracking |
| `engine/cadence.py` | DELETE | Absorbed into realisation |
| `engine/cadenza.py` | DELETE | Absorbed into schemas.yaml |
| `engine/cpsat_slice_solver.py` | DELETE | Replaced by new solver.py |
| `engine/diatonic_solver/` | DELETE | Replaced by new solver.py |
| `engine/energy.py` | DELETE | Not in minimal spec |
| `engine/engine_types.py` | DELETE | Replaced by builder/types.py |
| `engine/episode.py` | DELETE | Free passages in realisation |
| `engine/episode_registry.py` | DELETE | Not needed |
| `engine/expander.py` | DELETE | Not in architecture |
| `engine/expander_util.py` | DELETE | Not in architecture |
| `engine/expand_phrase.py` | DELETE | Not in architecture |
| `engine/figuration.py` | DELETE | Realisation handles this |
| `engine/figured_bass.py` | DELETE | Not in minimal spec |
| `engine/formatter.py` | DELETE | io.py handles output |
| `engine/guards/` | DELETE | Replaced by counterpoint.py |
| `engine/guard_backtrack.py` | DELETE | Not needed |
| `engine/harmonic_context.py` | DELETE | Simplified in new design |
| `engine/hemiola.py` | DELETE | Not in minimal spec |
| `engine/inner_voice.py` | DELETE | 2-voice only in minimal |
| `engine/key.py` | DELETE | Replaced by config/keys/*.yaml |
| `engine/metrics.py` | DELETE | Not in minimal spec |
| `engine/motif_expander.py` | DELETE | Not in architecture |
| `engine/note.py` | DELETE | Replaced by builder/types.py |
| `engine/n_voice_expander.py` | DELETE | 2-voice only in minimal |
| `engine/octave.py` | DELETE | Registers in config/keys/ |
| `engine/ornament.py` | DELETE | Not in minimal spec |
| `engine/output.py` | DELETE | Replaced by io.py |
| `engine/passage.py` | DELETE | Free passages in realisation |
| `engine/pedal.py` | DELETE | Not in minimal spec |
| `engine/phrase_builder.py` | DELETE | Not in architecture |
| `engine/phrase_expander.py` | DELETE | Not in architecture |
| `engine/pipeline.py` | DELETE | Replaced by generate() |
| `engine/pitch.py` | DELETE | Replaced by shared/pitch.py |
| `engine/plan_parser.py` | DELETE | Config loading simplified |
| `engine/progress.md` | DELETE | Documentation only |
| `engine/realiser.py` | DELETE | Replaced by realisation.py |
| `engine/realiser_guards.py` | DELETE | In counterpoint.py |
| `engine/realiser_passes.py` | DELETE | Simplified design |
| `engine/schema.py` | DELETE | Replaced by config loading |
| `engine/sequence.py` | DELETE | Monte/Fonte in schemas.yaml |
| `engine/serializer.py` | DELETE | Replaced by io.py |
| `engine/slice_solver.py` | DELETE | Replaced by solver.py |
| `engine/subdivision.py` | DELETE | Not in architecture |
| `engine/surprise.py` | DELETE | Not in minimal spec |
| `engine/suspension.py` | DELETE | In counterpoint.py |
| `engine/texture.py` | DELETE | Simplified in L6 |
| `engine/transform.py` | DELETE | Not in architecture |
| `engine/treatment_caps.py` | DELETE | Not in architecture |
| `engine/validate.py` | DELETE | In counterpoint.py |
| `engine/vocabulary.py` | DELETE | Config-driven |
| `engine/voice_checks.py` | DELETE | In counterpoint.py |
| `engine/voice_config.py` | DELETE | Config-driven |
| `engine/voice_entry.py` | DELETE | Not in architecture |
| `engine/voice_expander.py` | DELETE | Not in architecture |
| `engine/voice_material.py` | DELETE | Not in architecture |
| `engine/voice_pair.py` | DELETE | Simplified |
| `engine/voice_pipeline.py` | DELETE | Not in architecture |
| `engine/voice_realiser.py` | DELETE | In realisation.py |
| `engine/walking_bass.py` | DELETE | Not in minimal spec |
| `engine/bob/` | DELETE | Diagnostic tool, not core |

### 1.2 Files to CREATE (builder/ modules)

| Path | Action | Purpose |
|------|--------|---------|
| `builder/__init__.py` | CREATE | Package init with generate() |
| `builder/counterpoint.py` | CREATE | Hard rules checker |
| `builder/solver.py` | CREATE | CP-SAT wrapper |
| `builder/cost.py` | CREATE | Weight evaluator |
| `builder/realisation.py` | CREATE | Fills decoration |
| `builder/io.py` | CREATE | MIDI/note output |
| `builder/config_loader.py` | CREATE | YAML loading utilities |
| `builder/types.py` | MODIFY | Domain types (already exists) |

### 1.3 Files to CREATE (config/ folder)

| Path | Action | Purpose |
|------|--------|---------|
| `config/__init__.py` | CREATE | Package marker |
| `config/genres/invention.yaml` | CREATE | Genre definition |
| `config/schemas/core.yaml` | CREATE | Do-Re-Mi, Prinner, Monte, Fonte, Cadenza |
| `config/keys/c_major.yaml` | CREATE | Key with arrivals table |
| `config/affects/confident.yaml` | CREATE | Affect parameters |
| `config/forms/through_composed.yaml` | CREATE | Form template |

### 1.4 Files to MODIFY (planner/)

| Path | Action | Purpose |
|------|--------|---------|
| `planner/__init__.py` | MODIFY | Export layer functions |
| `planner/rhetorical.py` | CREATE | Layer 1: Genre → Trajectory |
| `planner/tonal.py` | CREATE | Layer 2: Affect → Tonal plan |
| `planner/schematic.py` | CREATE | Layer 3: Schema chain |
| `planner/thematic.py` | CREATE | Layer 4: Subject generation |
| `planner/metric.py` | CREATE | Layer 5: Bar assignments |
| `planner/textural.py` | CREATE | Layer 6: Treatment sequence |
| `planner/planner.py` | MODIFY | Orchestrate 6 layers |
| `planner/schema_loader.py` | MODIFY | Load from config/schemas/ |
| `planner/types.py` | MODIFY | Add layer output types |

### 1.5 Files to KEEP (shared/)

| Path | Action | Purpose |
|------|--------|---------|
| `shared/__init__.py` | KEEP | Package marker |
| `shared/constants.py` | KEEP | Global constants |
| `shared/errors.py` | KEEP | Exception types |
| `shared/key.py` | KEEP | Key class |
| `shared/midi_writer.py` | KEEP | MIDI export |
| `shared/music_math.py` | KEEP | Duration arithmetic |
| `shared/parallels.py` | KEEP | Parallel checker |
| `shared/pitch.py` | KEEP | Pitch utilities |
| `shared/types.py` | KEEP | Shared types |
| `shared/validate.py` | KEEP | Validation utilities |

---

## 2. Module Specifications

### 2.1 builder/counterpoint.py

**Purpose:** Hard rules checker for vertical intervals and parallel motion.

```python
"""Counterpoint hard rules checker.

Validates:
- Vertical consonance on strong beats
- Prepared/resolved dissonances
- No parallel 5ths/8ves/unisons
- Voice range constraints
- Diatonic pitch-class membership
"""
from typing import Sequence

from builder.types import Note, Interval


def check_consonance(
    soprano: int,
    bass: int,
    is_strong_beat: bool,
) -> bool:
    """Check if vertical interval is consonant.
    
    Consonances: P1, m3, M3, P5, m6, M6, P8, compounds.
    Dissonances allowed on weak beats or if prepared.
    """
    ...


def check_parallels(
    prev_soprano: int,
    prev_bass: int,
    curr_soprano: int,
    curr_bass: int,
) -> bool:
    """Check for forbidden parallel motion.
    
    Forbidden: P5→P5, P8→P8, P1→P1.
    Returns True if valid (no parallels).
    """
    ...


def check_voice_range(
    pitch: int,
    voice: str,
    registers: dict[str, tuple[int, int]],
) -> bool:
    """Check if pitch is within voice range."""
    ...


def check_pitch_class(
    pitch: int,
    pitch_class_set: set[int],
) -> bool:
    """Check if pitch belongs to diatonic set."""
    ...


def validate_passage(
    soprano_notes: Sequence[Note],
    bass_notes: Sequence[Note],
    pitch_class_set: set[int],
    registers: dict[str, tuple[int, int]],
    metre: str,
) -> list[str]:
    """Validate entire passage against all hard rules.
    
    Returns list of violation messages (empty if valid).
    """
    ...
```

**Dependencies:** `builder.types`  
**Config reads:** None (rules are universal)

---

### 2.2 builder/solver.py

**Purpose:** CP-SAT wrapper for enumerating valid pitch sequences.

```python
"""CP-SAT solver for Layer 4 (Thematic).

Enumerates all valid subjects satisfying:
- Schema arrival constraints (anchors)
- Melodic rules (step/leap balance)
- Counterpoint rules
- Motive weights from affect

Determinism rules:
- Lexicographic tie-breaking (lowest MIDI sum first)
- Enumerate soprano before bass, bar 1 before bar 2
- No randomisation
"""
from typing import Sequence
from ortools.sat.python import cp_model

from builder.types import Anchor, MotiveWeights, Solution


def solve(
    slots: int,
    anchors: Sequence[Anchor],
    pitch_set: set[int],
    weights: MotiveWeights,
    voice_count: int,
    registers: dict[str, tuple[int, int]],
) -> Solution:
    """Find minimum-cost valid pitch sequence.
    
    Args:
        slots: Total time slots (bars * slots_per_bar)
        anchors: Hard-coded pitch-pairs at specific positions
        pitch_set: Allowed pitch classes (diatonic)
        weights: Motive weights for cost function
        voice_count: Number of voices (2 for invention)
        registers: Voice range constraints
        
    Returns:
        Solution with soprano and bass pitch sequences.
        
    Raises:
        ValueError: If no valid solution exists.
    """
    ...


def _create_model(
    slots: int,
    anchors: Sequence[Anchor],
    pitch_set: set[int],
    registers: dict[str, tuple[int, int]],
) -> cp_model.CpModel:
    """Create CP-SAT model with variables and hard constraints."""
    ...


def _add_cost_function(
    model: cp_model.CpModel,
    weights: MotiveWeights,
) -> cp_model.LinearExpr:
    """Add soft constraint cost function for motive preferences."""
    ...


def _extract_solution(
    solver: cp_model.CpSolver,
    model: cp_model.CpModel,
    slots: int,
    voice_count: int,
) -> Solution:
    """Extract pitch values from solved model."""
    ...
```

**Dependencies:** `ortools.sat.python.cp_model`, `builder.types`, `builder.counterpoint`  
**Config reads:** None (weights passed in)

---

### 2.3 builder/cost.py

**Purpose:** Weight evaluator for motive scoring.

```python
"""Cost function evaluator for melodic motion.

Implements Layer 4.5 motive constraints:
- Stepwise preference (weight 0.2)
- Skip acceptable (weight 0.4)
- Leap penalised (weight 0.8)
- Large leap strongly penalised (weight 1.5)
"""
from builder.types import MotiveWeights


def motion_cost(
    prev_pitch: int,
    curr_pitch: int,
    weights: MotiveWeights,
) -> float:
    """Calculate cost for melodic motion between two pitches.
    
    Args:
        prev_pitch: Previous MIDI pitch
        curr_pitch: Current MIDI pitch
        weights: Motive weights from affect config
        
    Returns:
        Cost value (lower is better).
    """
    ...


def direction_penalty(
    pitches: list[int],
    direction_limit: int,
) -> float:
    """Penalty for exceeding direction limit.
    
    After direction_limit consecutive steps in one direction,
    apply penalty unless direction changes.
    """
    ...


def leap_recovery_penalty(
    prev_pitch: int,
    curr_pitch: int,
    next_pitch: int | None,
) -> float:
    """Penalty if leap > 3rd not resolved by contrary step."""
    ...


def counter_motion_bonus(
    soprano_motion: int,
    bass_motion: int,
) -> float:
    """Bonus for contrary motion between voices.
    
    Similar motion: +0.3 penalty
    Contrary motion: -0.2 bonus
    """
    ...


def total_cost(
    soprano_pitches: list[int],
    bass_pitches: list[int],
    weights: MotiveWeights,
) -> float:
    """Calculate total cost for complete pitch sequences."""
    ...
```

**Dependencies:** `builder.types`  
**Config reads:** None (weights passed in)

---

### 2.4 builder/realisation.py

**Purpose:** Fill decoration between schema arrivals.

```python
"""Realisation: Turn abstract structure into notes.

Inputs:
- Schema arrivals (soprano/bass pairs at strong beats)
- Bar assignments
- Subject (if active)
- Metre, local key, affect, texture

Process:
1. Place schema arrivals at designated strong beats
2. Fill weak beats with decoration
3. Verify all hard constraints
4. Apply surface rhythm
"""
from fractions import Fraction
from typing import Sequence

from builder.types import (
    Anchor, Note, NoteFile, RhythmState, 
    SchemaChain, Solution, TextureSequence,
)


def realise(
    solution: Solution,
    texture: TextureSequence,
    config: dict,
) -> NoteFile:
    """Convert solver solution to note file.
    
    Args:
        solution: Pitch sequences from solver
        texture: Treatment sequence from Layer 6
        config: Combined configuration
        
    Returns:
        NoteFile ready for export.
    """
    ...


def place_arrivals(
    arrivals: Sequence[Anchor],
    metre: str,
) -> list[Note]:
    """Place schema arrivals at designated beats."""
    ...


def fill_decoration(
    arrivals: list[Note],
    pitch_set: set[int],
    rhythm_state: RhythmState,
    metre: str,
) -> list[Note]:
    """Fill weak beats between arrivals.
    
    Uses rhythmic state machine:
    - RUN: high density (75%+ semiquaver slots)
    - HOLD: medium density (arrival beats)
    - CADENCE: low density (final 2 bars)
    - TRANSITION: mixed (schema boundaries)
    """
    ...


def apply_surface_rhythm(
    notes: list[Note],
    affect_density: str,
    metre: str,
) -> list[Note]:
    """Apply duration values based on affect density."""
    ...


def generate_free_passage(
    exit_pitch: tuple[int, int],
    entry_pitch: tuple[int, int],
    duration_beats: int,
    bridge_pitch_set: set[int],
    metre: str,
) -> tuple[list[Note], list[Note]]:
    """Generate free passage between schemas.
    
    Uses bridge pitch set (pentatonic) to avoid premature tonicisation.
    Ends with lead-in motion (step below entry).
    """
    ...


def generate_countersubject(
    subject: list[Note],
    home_key_midi: int,
) -> list[Note]:
    """Generate countersubject for Answer.
    
    Rules:
    - Contrary motion skeleton
    - Rhythmic complement
    - Invertible at 10th
    - Arrival synchronisation
    """
    ...
```

**Dependencies:** `builder.types`, `builder.counterpoint`, `builder.cost`  
**Config reads:** `config/affects/*.yaml` (density)

---

### 2.5 builder/io.py

**Purpose:** MIDI and note file output.

```python
"""I/O utilities for MIDI and note file export.

Note file format:
offset,midinote,duration,track,length,bar,beat,notename,lyric
"""
from pathlib import Path
from fractions import Fraction

from builder.types import Note, NoteFile
from shared.midi_writer import MidiWriter


def write_note_file(
    notes: NoteFile,
    path: Path,
    metre: str,
) -> None:
    """Write notes to .note CSV file.
    
    Format: offset,midinote,duration,track,length,bar,beat,notename,lyric
    Comments start with #
    """
    ...


def write_midi_file(
    notes: NoteFile,
    path: Path,
    tempo: int,
) -> None:
    """Write notes to MIDI file."""
    ...


def note_name(midi: int) -> str:
    """Convert MIDI number to note name (e.g., 60 → C4)."""
    ...


def bar_beat(
    offset: Fraction,
    metre: str,
) -> tuple[int, Fraction]:
    """Convert offset to bar number and beat position."""
    ...
```

**Dependencies:** `builder.types`, `shared.midi_writer`  
**Config reads:** None

---

### 2.6 builder/config_loader.py

**Purpose:** Load and validate YAML configuration files.

```python
"""Configuration loader for YAML files.

Loads from config/ directory structure:
- genres/*.yaml
- schemas/*.yaml  
- keys/*.yaml
- affects/*.yaml
- forms/*.yaml
"""
from pathlib import Path
from typing import Any

import yaml

from builder.types import (
    AffectConfig, FormConfig, GenreConfig, 
    KeyConfig, SchemaConfig,
)


CONFIG_DIR: Path = Path(__file__).parent.parent / "config"


def load_genre(name: str) -> GenreConfig:
    """Load genre configuration.
    
    Args:
        name: Genre name (e.g., "invention")
        
    Returns:
        Validated GenreConfig.
        
    Raises:
        FileNotFoundError: If genre file not found.
        ValueError: If validation fails.
    """
    ...


def load_schema(name: str) -> SchemaConfig:
    """Load schema definition."""
    ...


def load_key(name: str) -> KeyConfig:
    """Load key configuration with arrivals table."""
    ...


def load_affect(name: str) -> AffectConfig:
    """Load affect configuration."""
    ...


def load_form(name: str) -> FormConfig:
    """Load form template."""
    ...


def load_configs(
    genre: str,
    key: str,
    affect: str,
) -> dict[str, Any]:
    """Load all required configurations.
    
    Returns combined config dict with:
    - genre: GenreConfig
    - key: KeyConfig
    - affect: AffectConfig
    - form: FormConfig (from genre.form)
    - schemas: dict[str, SchemaConfig]
    """
    ...


def _validate_genre(data: dict) -> GenreConfig:
    """Validate genre YAML against schema."""
    ...


def _validate_key(data: dict) -> KeyConfig:
    """Validate key YAML against schema."""
    ...


def _validate_affect(data: dict) -> AffectConfig:
    """Validate affect YAML against schema."""
    ...
```

**Dependencies:** `builder.types`, `yaml`  
**Config reads:** All config/*.yaml files

---

### 2.7 builder/types.py (MODIFY existing)

**Purpose:** Domain types for the builder module.

```python
"""Domain types for Andante builder.

All types are frozen dataclasses for immutability.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence


@dataclass(frozen=True)
class Note:
    """Single note with timing and pitch."""
    offset: Fraction
    pitch: int  # MIDI number
    duration: Fraction
    voice: int  # 0=soprano, 1=bass
    lyric: str = ""


@dataclass(frozen=True)
class NoteFile:
    """Collection of notes for export."""
    soprano: tuple[Note, ...]
    bass: tuple[Note, ...]
    metre: str
    tempo: int


@dataclass(frozen=True)
class Anchor:
    """Schema arrival constraint."""
    bar_beat: str  # e.g., "1.1", "2.3"
    soprano_midi: int
    bass_midi: int
    schema: str
    stage: int


@dataclass(frozen=True)
class MotiveWeights:
    """Motive cost weights from affect."""
    step: float = 0.2
    skip: float = 0.4
    leap: float = 0.8
    large_leap: float = 1.5
    direction_limit: int = 4


@dataclass(frozen=True)
class Solution:
    """Solver output."""
    soprano_pitches: tuple[int, ...]
    bass_pitches: tuple[int, ...]
    cost: float


@dataclass(frozen=True)
class RhythmState:
    """Rhythmic state machine state."""
    state: str  # RUN, HOLD, CADENCE, TRANSITION
    density: float  # 0.0 to 1.0


@dataclass(frozen=True)
class SchemaConfig:
    """Schema definition from YAML."""
    name: str
    soprano_degrees: tuple[int, ...]
    bass_degrees: tuple[int, ...]
    entry: tuple[int, int]  # (soprano, bass)
    exit: tuple[int, int]
    bars: tuple[int, int]  # (min, max)
    position: str
    cadential_state: str
    sequential: bool = False
    segments: tuple[int, ...] = (1,)


@dataclass(frozen=True)
class GenreConfig:
    """Genre definition from YAML."""
    name: str
    voices: int
    form: str
    metre: str
    primary_value: str
    sections: tuple[dict, ...]
    imitation: str


@dataclass(frozen=True)
class KeyConfig:
    """Key definition with arrivals table."""
    name: str
    pitch_class_set: frozenset[int]
    bridge_pitch_set: frozenset[int]
    registers: dict[str, tuple[int, int]]
    arrivals: dict[str, tuple[Anchor, ...]]


@dataclass(frozen=True)
class AffectConfig:
    """Affect definition from YAML."""
    name: str
    density: str
    articulation: str
    tempo_modifier: int
    tonal_path: dict[str, tuple[str, ...]]
    answer_interval: int
    anacrusis: bool
    motive_weights: MotiveWeights


@dataclass(frozen=True)
class FormConfig:
    """Form template from YAML."""
    name: str
    sections: tuple[dict, ...]


@dataclass(frozen=True)
class SchemaChain:
    """Output of Layer 3."""
    schemas: tuple[str, ...]
    key_areas: tuple[str, ...]
    free_passages: tuple[tuple[int, int], ...]  # indices


@dataclass(frozen=True)
class TextureSequence:
    """Output of Layer 6."""
    treatments: tuple[str, ...]  # S, A, episode, S', etc.
    voice_assignments: tuple[int, ...]  # which voice has subject
```

---

## 3. YAML Schema Definitions

### 3.1 config/genres/invention.yaml

```yaml
# Genre: Two-Part Invention
# Version: 1.0.0 (matches architecture.md v1.3.2)

name: invention
voices: 2
form: through_composed
metre: "4/4"
primary_value: "1/16"
imitation: mandatory

sections:
  - name: exordium
    bars: [1, 4]
    schema_sequence: [do_re_mi, do_re_mi]  # S then A
    texture: imitative
    
  - name: narratio
    bars: [5, 12]
    schema_sequence: [episode, monte, monte, monte]
    texture: free
    
  - name: confirmatio
    bars: [13, 16]
    schema_sequence: [prinner]
    texture: schematic
    
  - name: peroratio
    bars: [17, 20]
    schema_sequence: [episode, cadenza_semplice]
    texture: cadential

# Subject constraints
subject_constraints:
  min_notes: 4
  max_notes: 12
  max_bars: 2
  require_invertible: true
  require_answerable: true
  first_degree: [1, 3, 5]
  last_degree: [2, 3, 5, 7]

# Rhythmic vocabulary
rhythmic_vocabulary:
  primary: "1/16"
  characteristic_figures:
    - "running_scales"
    - "turns"
  tempo_range: [72, 88]  # Allegretto

# Treatment sequence (L6)
treatment_sequence:
  - {symbol: S, description: "Subject in soprano", duration: [2, 4]}
  - {symbol: A, description: "Answer in bass", duration: [2, 4]}
  - {symbol: episode_1, description: "Free passage", duration: [2, 4]}
  - {symbol: "S'/A'", description: "Subject/Answer new key", duration: [2, 4]}
  - {symbol: episode_2, description: "Second episode", duration: [2, 4]}
  - {symbol: "S''", description: "Subject return tonic", duration: [2, 4]}
  - {symbol: coda, description: "Cadential confirmation", duration: [2, 4]}
```

### 3.2 config/schemas/core.yaml

```yaml
# Core Schemas for Invention
# Version: 1.0.0 (matches architecture.md v1.3.2)

do_re_mi:
  description: "Opening gambit with stepwise soprano ascent"
  soprano_degrees: [1, 2, 3]
  bass_degrees: [1, 7, 1]
  bass_alt: [1, 5, 1]
  entry: {soprano: 1, bass: 1}
  exit: {soprano: 3, bass: 1}
  bars: [1, 2]
  cadential_state: open
  position: opening
  source: "Gjerdingen Ch.6"

prinner:
  description: "Archetypal riposte; parallel tenths descending"
  soprano_degrees: [6, 5, 4, 3]
  bass_degrees: [4, 3, 2, 1]
  entry: {soprano: 6, bass: 4}
  exit: {soprano: 3, bass: 1}
  bars: [1, 2]
  cadential_state: closed
  position: riposte
  source: "Gjerdingen Ch.3"

monte:
  description: "Ascending sequence; clausula cantizans per segment"
  segment:
    soprano_degrees: [4, 3]
    bass_degrees: [7, 1]
  segments: [2, 3, 4]
  direction: ascending
  typical_keys: "IV -> V (-> vi)"
  entry: {soprano: 4, bass: 7}  # Approach (passing)
  exit: {soprano: 3, bass: 1}   # Arrival (consonant)
  bars: [2, 4]
  cadential_state: open
  position: continuation
  sequential: true
  source: "Gjerdingen Ch.7"

fonte:
  description: "Descending sequence; clausula cantizans per segment"
  segment:
    soprano_degrees: [4, 3]
    bass_degrees: [7, 1]
  segments: [2, 3, 4]
  direction: descending
  typical_keys: "ii -> I"
  entry: {soprano: 4, bass: 7}
  exit: {soprano: 3, bass: 1}
  bars: [2, 4]
  cadential_state: open
  position: continuation
  sequential: true
  source: "Gjerdingen Ch.8"

cadenza_semplice:
  description: "Simple authentic cadence"
  soprano_degrees: [2, 7, 1]
  bass_degrees: [5, 5, 1]
  entry: {soprano: 2, bass: 5}
  exit: {soprano: 1, bass: 1}
  bars: [1, 1]
  cadential_state: closed
  position: cadential
  source: "Partimento tradition"
```

### 3.3 config/keys/c_major.yaml

```yaml
# Key: C Major with Confident Affect Arrivals
# Version: 1.0.0 (matches architecture.md v1.3.2)

name: "C Major"

pitch_class_set: [0, 2, 4, 5, 7, 9, 11]  # C, D, E, F, G, A, B

bridge_pitch_set: [0, 2, 4, 7, 9]  # C, D, E, G, A (pentatonic)

registers:
  soprano: [60, 79]  # C4 to G5
  bass: [36, 60]     # C2 to C4

preferred_tessitura:
  soprano: [64, 76]  # E4 to E5
  bass: [43, 55]     # G2 to G3

# Schema arrivals for Confident affect
# Format: bar.beat, soprano MIDI, bass MIDI
arrivals:
  confident:
    # Exordium: Do-Re-Mi (Subject)
    - {bar_beat: "1.1", schema: do_re_mi, stage: 1, soprano: 60, bass: 48}
    - {bar_beat: "1.3", schema: do_re_mi, stage: 2, soprano: 62, bass: 47}
    - {bar_beat: "2.1", schema: do_re_mi, stage: 3, soprano: 64, bass: 48}
    
    # Exordium: Do-Re-Mi (Answer in V)
    - {bar_beat: "3.1", schema: do_re_mi, stage: 1, soprano: 67, bass: 55}
    - {bar_beat: "3.3", schema: do_re_mi, stage: 2, soprano: 69, bass: 54}  # F#3 for V
    - {bar_beat: "4.1", schema: do_re_mi, stage: 3, soprano: 71, bass: 55}
    
    # Narratio: Monte segments
    - {bar_beat: "9.1", schema: monte, stage: 1, soprano: 69, bass: 53}   # IV
    - {bar_beat: "10.1", schema: monte, stage: 2, soprano: 71, bass: 55}  # V
    - {bar_beat: "11.1", schema: monte, stage: 3, soprano: 72, bass: 57}  # vi
    
    # Confirmatio: Prinner
    - {bar_beat: "13.1", schema: prinner, stage: 1, soprano: 69, bass: 53}  # 6/4
    - {bar_beat: "14.1", schema: prinner, stage: 2, soprano: 67, bass: 52}  # 5/3
    - {bar_beat: "15.1", schema: prinner, stage: 3, soprano: 65, bass: 50}  # 4/2
    - {bar_beat: "16.1", schema: prinner, stage: 4, soprano: 64, bass: 48}  # 3/1
    
    # Peroratio: Cadenza semplice
    - {bar_beat: "19.1", schema: cadenza_semplice, stage: 1, soprano: 62, bass: 55}  # 2/5
    - {bar_beat: "19.3", schema: cadenza_semplice, stage: 2, soprano: 59, bass: 55}  # 7/5
    - {bar_beat: "20.1", schema: cadenza_semplice, stage: 3, soprano: 60, bass: 48}  # PAC
```

### 3.4 config/affects/confident.yaml

```yaml
# Affect: Confident
# Version: 1.0.0 (matches architecture.md v1.3.2)

name: confident
density: high
articulation: detached
tempo_modifier: 5  # +5 BPM from genre base

tonal_path:
  narratio: [I, V, vi]
  confirmatio: [vi, IV, I]

answer_interval: 5  # 5th above (tonal answer)
anacrusis: false    # Subject begins on beat 1

motive_weights:
  step: 0.2         # Preferred (80% of semiquaver motion)
  skip: 0.4         # Acceptable
  leap: 0.8         # Penalised
  large_leap: 1.5   # Strongly penalised

direction_limit: 4  # Max consecutive steps in one direction

# Rhythmic profile
rhythmic_profile:
  pattern: ["1/16", "1/16", "1/16", "1/16", "1/8", "1/8"]
  arrival_duration: ["1/8", "1/4"]
  decoration: ["semiquaver_runs", "neighbour_tones"]

# High-density rule
density_minimum: 0.75  # ≥75% of semiquaver slots filled

# Rhythmic state transitions
rhythm_states:
  RUN:
    density: 0.75
    values: ["1/16"]
  HOLD:
    density: 0.5
    values: ["1/8", "1/4"]
  CADENCE:
    density: 0.25
    values: ["1/4", "1/2"]
  TRANSITION:
    density: 0.5
    values: ["1/8", "1/16"]
```

### 3.5 config/forms/through_composed.yaml

```yaml
# Form: Through-Composed (for Invention)
# Version: 1.0.0 (matches architecture.md v1.3.2)

name: through_composed

description: "No formal repeats; continuous development"

minimum_bars: 20
typical_range: [20, 32]

# Proportion allocator (20-bar invention, Confident affect)
bar_allocation:
  exordium: [1, 4]
  episode_1: [5, 8]
  narratio: [9, 12]
  confirmatio: [13, 16]
  episode_2: [17, 18]
  peroratio: [19, 20]

# Schema allocation per section
schema_allocation:
  exordium:
    schemas: [do_re_mi, do_re_mi]
    treatment: [S, A]
  episode_1:
    schemas: []  # Free passage
    treatment: [episode]
  narratio:
    schemas: [monte]
    segments: 3
    treatment: [development]
  confirmatio:
    schemas: [prinner]
    treatment: [schematic]
  episode_2:
    schemas: []
    treatment: [episode]
  peroratio:
    schemas: [cadenza_semplice]
    treatment: [cadential]

# Phrase boundaries
phrase_boundaries:
  - bar: 4
    type: half_cadence
  - bar: 8
    type: half_cadence
  - bar: 12
    type: half_cadence
  - bar: 16
    type: authentic_cadence
  - bar: 20
    type: perfect_authentic_cadence
```

---

## 4. Planner Updates

### 4.1 Files to KEEP unchanged

| File | Reason |
|------|--------|
| `planner/types.py` | Base types still needed |
| `planner/koch_rules.py` | Phrase structure rules |
| `planner/constraints.py` | Constraint definitions |

### 4.2 Files to MODIFY

#### planner/planner.py

**Before:** Monolithic planning with mixed concerns  
**After:** Orchestrate 6 layers sequentially

```python
"""Main planner orchestrating 6 layers.

generate() is the public entry point matching architecture.md.
"""
from builder.config_loader import load_configs
from builder.realisation import realise
from builder.solver import solve
from builder.types import NoteFile
from planner.rhetorical import layer_1_rhetorical
from planner.tonal import layer_2_tonal
from planner.schematic import layer_3_schematic
from planner.thematic import layer_4_thematic
from planner.metric import layer_5_metric
from planner.textural import layer_6_textural


def generate(
    genre: str,
    key: str,
    affect: str,
) -> NoteFile:
    """Generate composition from genre, key, affect.
    
    This is the main entry point per architecture.md.
    """
    config = load_configs(genre, key, affect)
    
    # Layer 1: Rhetorical
    trajectory, rhythm_vocab, tempo = layer_1_rhetorical(config)
    
    # Layer 2: Tonal  
    tonal_plan, density, modality = layer_2_tonal(config, affect)
    
    # Layer 3: Schematic
    schema_chain = layer_3_schematic(tonal_plan, config)
    
    # Layer 4: Thematic
    subject = layer_4_thematic(schema_chain, rhythm_vocab, density, config)
    
    # Layer 5: Metric
    bar_assignments, arrivals = layer_5_metric(schema_chain, config)
    
    # Layer 6: Textural
    texture_sequence = layer_6_textural(genre, schema_chain, subject, config)
    
    # Solve and realise
    solution = solve(
        slots=config["total_slots"],
        anchors=arrivals,
        pitch_set=config["key"].pitch_class_set,
        weights=config["affect"].motive_weights,
        voice_count=config["genre"].voices,
        registers=config["key"].registers,
    )
    
    return realise(solution, texture_sequence, config)
```

#### planner/schema_loader.py

**Before:** Load from data/schemas.yaml  
**After:** Load from config/schemas/core.yaml

```python
"""Schema loader for config/schemas/*.yaml."""
from pathlib import Path
import yaml

from builder.types import SchemaConfig


CONFIG_DIR = Path(__file__).parent.parent / "config" / "schemas"


def load_all_schemas() -> dict[str, SchemaConfig]:
    """Load all schema definitions from core.yaml."""
    ...


def load_schema(name: str) -> SchemaConfig:
    """Load single schema by name."""
    ...
```

### 4.3 Files to CREATE

#### planner/rhetorical.py (Layer 1)

```python
"""Layer 1: Rhetorical.

Input: Genre
Output: Trajectory + rhythmic vocabulary + tempo

Fixed per genre - no enumeration.
"""
from builder.types import GenreConfig


def layer_1_rhetorical(
    config: dict,
) -> tuple[list[str], dict, int]:
    """Execute Layer 1.
    
    Returns:
        trajectory: List of section names
        rhythm_vocab: Dict of rhythmic parameters
        tempo: Base tempo in BPM
    """
    genre: GenreConfig = config["genre"]
    
    trajectory = [s["name"] for s in genre.sections]
    
    rhythm_vocab = {
        "primary_value": genre.primary_value,
        "characteristic_figures": genre.rhythmic_vocabulary.get(
            "characteristic_figures", []
        ),
    }
    
    tempo_range = genre.rhythmic_vocabulary.get("tempo_range", [72, 88])
    tempo = (tempo_range[0] + tempo_range[1]) // 2
    
    return trajectory, rhythm_vocab, tempo
```

#### planner/tonal.py (Layer 2)

```python
"""Layer 2: Tonal.

Input: Affect
Output: Tonal plan + density + modality

Lookup table, expandable.
"""
from builder.types import AffectConfig


def layer_2_tonal(
    config: dict,
    affect_name: str,
) -> tuple[dict[str, list[str]], str, str]:
    """Execute Layer 2.
    
    Returns:
        tonal_plan: Dict mapping section to key areas
        density: "high", "medium", or "low"
        modality: "diatonic" or "chromatic"
    """
    affect: AffectConfig = config["affect"]
    
    tonal_plan = dict(affect.tonal_path)
    density = affect.density
    modality = "diatonic"  # Default for Confident
    
    return tonal_plan, density, modality
```

#### planner/schematic.py (Layer 3)

```python
"""Layer 3: Schematic.

Input: Tonal plan
Output: Schema chain

Enumerate all valid chains from rules.
"""
from builder.types import SchemaChain, SchemaConfig


def layer_3_schematic(
    tonal_plan: dict[str, list[str]],
    config: dict,
) -> SchemaChain:
    """Execute Layer 3.
    
    Returns:
        SchemaChain with schemas, key areas, free passage markers.
    """
    ...


def check_connection(
    exit_schema: SchemaConfig,
    entry_schema: SchemaConfig,
) -> bool:
    """Check if two schemas can connect directly.
    
    Valid connections:
    1. Identity: exit.bass == entry.bass
    2. Step: |exit.bass - entry.bass| == 1
    3. Dominant: exit.bass == 5 and entry.bass == 1
    """
    ...


def enumerate_valid_chains(
    tonal_plan: dict[str, list[str]],
    schemas: dict[str, SchemaConfig],
) -> list[SchemaChain]:
    """Enumerate all valid schema chains for tonal plan."""
    ...
```

#### planner/thematic.py (Layer 4)

```python
"""Layer 4: Thematic.

Input: Opening schema + rhythmic vocabulary + density
Output: Subject (pitches + durations)

CP-SAT enumerates all valid subjects.
"""
from builder.types import SchemaConfig, Solution


def layer_4_thematic(
    schema_chain: SchemaChain,
    rhythm_vocab: dict,
    density: str,
    config: dict,
) -> Solution:
    """Execute Layer 4.
    
    Returns:
        Solution with subject pitches and durations.
    """
    ...
```

#### planner/metric.py (Layer 5)

```python
"""Layer 5: Metric.

Input: Schema chain
Output: Bar assignments + arrival beat positions

Enumerate all valid assignments.
"""
from builder.types import Anchor, SchemaChain


def layer_5_metric(
    schema_chain: SchemaChain,
    config: dict,
) -> tuple[dict[str, tuple[int, int]], list[Anchor]]:
    """Execute Layer 5.
    
    Returns:
        bar_assignments: Dict mapping schema to (start_bar, end_bar)
        arrivals: List of Anchor constraints for solver
    """
    ...


def distribute_arrivals(
    schema: str,
    stages: int,
    start_bar: int,
    end_bar: int,
    metre: str,
) -> list[str]:
    """Distribute arrival beats across bars.
    
    Strong beats: 1 and 3 in 4/4; 1 in 3/4.
    First arrival on bar 1 beat 1.
    """
    ...
```

#### planner/textural.py (Layer 6)

```python
"""Layer 6: Textural.

Input: Genre + schema chain + subject
Output: Treatment sequence mapped to schema chain

Lookup by genre convention.
"""
from builder.types import SchemaChain, Solution, TextureSequence


def layer_6_textural(
    genre: str,
    schema_chain: SchemaChain,
    subject: Solution,
    config: dict,
) -> TextureSequence:
    """Execute Layer 6.
    
    Returns:
        TextureSequence with treatments and voice assignments.
    """
    if genre == "invention":
        return _invention_texture(schema_chain, subject, config)
    else:
        raise ValueError(f"Unknown genre: {genre}")


def _invention_texture(
    schema_chain: SchemaChain,
    subject: Solution,
    config: dict,
) -> TextureSequence:
    """Generate texture sequence for invention.
    
    Sequence: S → A → episode₁ → S'/A' → episode₂ → S'' → coda
    """
    ...
```

---

## 5. Implementation Order

| Step | Files | Prerequisites | Validation |
|------|-------|---------------|------------|
| 1 | `config/__init__.py` | None | Directory exists |
| 2 | `config/schemas/core.yaml` | Step 1 | YAML parses, 5 schemas present |
| 3 | `config/keys/c_major.yaml` | Step 1 | YAML parses, arrivals match spec |
| 4 | `config/affects/confident.yaml` | Step 1 | YAML parses, weights correct |
| 5 | `config/genres/invention.yaml` | Step 1 | YAML parses, sections match |
| 6 | `config/forms/through_composed.yaml` | Step 1 | YAML parses |
| 7 | `builder/types.py` | None | Types instantiate without error |
| 8 | `builder/config_loader.py` | Steps 2-6, 7 | All configs load and validate |
| 9 | `builder/counterpoint.py` | Step 7 | Unit tests pass for all rules |
| 10 | `builder/cost.py` | Step 7 | Unit tests for weights |
| 11 | `builder/solver.py` | Steps 9, 10 | Solver finds valid solution |
| 12 | `builder/realisation.py` | Steps 9, 10, 11 | Notes generated |
| 13 | `builder/io.py` | Step 7 | Output matches format |
| 14 | `planner/rhetorical.py` | Step 8 | L1 output correct |
| 15 | `planner/tonal.py` | Step 8 | L2 output matches spec |
| 16 | `planner/schematic.py` | Steps 8, 14, 15 | Valid chain generated |
| 17 | `planner/thematic.py` | Steps 11, 16 | Subject matches spec |
| 18 | `planner/metric.py` | Steps 8, 16 | Bar assignments correct |
| 19 | `planner/textural.py` | Steps 16, 17 | Treatment sequence correct |
| 20 | `planner/planner.py` | Steps 14-19, 12, 13 | Full pipeline runs |
| 21 | DELETE `engine/` | Step 20 passes | No import errors |
| 22 | Integration test | Step 21 | Output matches `freude_sonata.note` |

---

## 6. Test Specification

### 6.1 Unit Tests

#### tests/builder/test_counterpoint.py

```python
"""Unit tests for counterpoint rules."""

def test_consonance_perfect_fifth():
    """P5 is consonant."""
    assert check_consonance(67, 60, True)  # G4/C4 = P5

def test_consonance_tritone_dissonant():
    """Tritone is dissonant."""
    assert not check_consonance(66, 60, True)  # F#4/C4 = tritone

def test_parallels_fifths_forbidden():
    """Parallel fifths are forbidden."""
    assert not check_parallels(67, 60, 69, 62)  # P5 → P5

def test_parallels_contrary_ok():
    """Contrary motion to fifth is OK."""
    assert check_parallels(64, 60, 67, 60)  # M3 → P5 with contrary

def test_voice_range_soprano():
    """Soprano must be C4-G5."""
    registers = {"soprano": (60, 79), "bass": (36, 60)}
    assert check_voice_range(72, "soprano", registers)  # C5 OK
    assert not check_voice_range(80, "soprano", registers)  # Ab5 out

def test_pitch_class_diatonic():
    """Only diatonic pitches allowed."""
    c_major = {0, 2, 4, 5, 7, 9, 11}
    assert check_pitch_class(60, c_major)  # C
    assert not check_pitch_class(61, c_major)  # C#
```

#### tests/builder/test_cost.py

```python
"""Unit tests for cost function."""

def test_stepwise_motion_low_cost():
    weights = MotiveWeights()
    assert motion_cost(60, 62, weights) == 0.2  # M2 = step

def test_leap_high_cost():
    weights = MotiveWeights()
    assert motion_cost(60, 67, weights) == 0.8  # P5 = leap

def test_direction_penalty_after_four():
    pitches = [60, 62, 64, 65, 67]  # 4 ascending steps
    assert direction_penalty(pitches, 4) > 0

def test_contrary_motion_bonus():
    assert counter_motion_bonus(2, -2) < 0  # Bonus (negative)
    assert counter_motion_bonus(2, 2) > 0   # Penalty (positive)
```

#### tests/builder/test_solver.py

```python
"""Unit tests for CP-SAT solver."""

def test_solver_respects_anchors():
    anchors = [
        Anchor("1.1", 60, 48, "do_re_mi", 1),
        Anchor("2.1", 64, 48, "do_re_mi", 3),
    ]
    solution = solve(
        slots=32,
        anchors=anchors,
        pitch_set={0, 2, 4, 5, 7, 9, 11},
        weights=MotiveWeights(),
        voice_count=2,
        registers={"soprano": (60, 79), "bass": (36, 60)},
    )
    assert solution.soprano_pitches[0] == 60
    assert solution.soprano_pitches[16] == 64

def test_solver_deterministic():
    """Same inputs produce same outputs."""
    args = {...}
    sol1 = solve(**args)
    sol2 = solve(**args)
    assert sol1 == sol2

def test_solver_no_solution_raises():
    """Impossible constraints raise ValueError."""
    anchors = [
        Anchor("1.1", 60, 80, "test", 1),  # Bass out of range
    ]
    with pytest.raises(ValueError):
        solve(slots=16, anchors=anchors, ...)
```

#### tests/builder/test_realisation.py

```python
"""Unit tests for realisation."""

def test_place_arrivals_correct_offsets():
    arrivals = [
        Anchor("1.1", 60, 48, "do_re_mi", 1),
        Anchor("1.3", 62, 47, "do_re_mi", 2),
    ]
    notes = place_arrivals(arrivals, "4/4")
    assert notes[0].offset == Fraction(0)
    assert notes[1].offset == Fraction(1, 2)

def test_free_passage_uses_bridge_pitches():
    bridge_set = {0, 2, 4, 7, 9}  # Pentatonic
    soprano, bass = generate_free_passage(
        exit_pitch=(64, 48),
        entry_pitch=(69, 53),
        duration_beats=4,
        bridge_pitch_set=bridge_set,
        metre="4/4",
    )
    for note in soprano:
        assert note.pitch % 12 in bridge_set

def test_countersubject_contrary_motion():
    subject = [Note(...), ...]  # Ascending
    cs = generate_countersubject(subject, 60)
    # Check general descending tendency
    ...
```

### 6.2 Integration Tests

#### tests/test_integration.py

```python
"""Integration test against freude_sonata.note."""
from pathlib import Path
from builder import generate
from builder.io import write_note_file


def test_full_pipeline_matches_reference():
    """Generated output matches reference exactly."""
    result = generate(
        genre="invention",
        key="c_major",
        affect="confident",
    )
    
    # Write to temp file
    temp_path = Path("/tmp/test_output.note")
    write_note_file(result, temp_path, "4/4")
    
    # Compare with reference
    reference = Path("output/freude_sonata.note")
    
    # Parse both files
    result_notes = parse_note_file(temp_path)
    ref_notes = parse_note_file(reference)
    
    # Compare note-for-note
    assert len(result_notes) == len(ref_notes)
    for r, ref in zip(result_notes, ref_notes):
        assert r.offset == ref.offset
        assert r.pitch == ref.pitch
        assert r.duration == ref.duration
        assert r.voice == ref.voice


def test_determinism_across_runs():
    """Multiple runs produce identical output."""
    result1 = generate("invention", "c_major", "confident")
    result2 = generate("invention", "c_major", "confident")
    
    assert result1.soprano == result2.soprano
    assert result1.bass == result2.bass
```

### 6.3 Layer Tests

#### tests/planner/test_layers.py

```python
"""Tests for each layer in isolation."""

def test_layer1_rhetorical_output():
    config = load_configs("invention", "c_major", "confident")
    trajectory, rhythm, tempo = layer_1_rhetorical(config)
    
    assert trajectory == ["exordium", "narratio", "confirmatio", "peroratio"]
    assert rhythm["primary_value"] == "1/16"
    assert 72 <= tempo <= 93  # Base + confident modifier

def test_layer2_tonal_confident():
    config = load_configs("invention", "c_major", "confident")
    tonal_plan, density, modality = layer_2_tonal(config, "confident")
    
    assert tonal_plan["narratio"] == ["I", "V", "vi"]
    assert density == "high"
    assert modality == "diatonic"

def test_layer3_schema_chain_valid():
    tonal_plan = {"narratio": ["I", "V", "vi"], "confirmatio": ["vi", "IV", "I"]}
    config = load_configs("invention", "c_major", "confident")
    chain = layer_3_schematic(tonal_plan, config)
    
    # Check connections are valid
    schemas = config["schemas"]
    for i in range(len(chain.schemas) - 1):
        if (i, i+1) not in chain.free_passages:
            assert check_connection(
                schemas[chain.schemas[i]],
                schemas[chain.schemas[i+1]]
            )

def test_layer5_bar_assignments():
    chain = SchemaChain(...)
    config = load_configs("invention", "c_major", "confident")
    bars, arrivals = layer_5_metric(chain, config)
    
    # Check arrivals match spec
    assert arrivals[0] == Anchor("1.1", 60, 48, "do_re_mi", 1)
    assert arrivals[-1] == Anchor("20.1", 60, 48, "cadenza_semplice", 3)

def test_layer6_texture_sequence():
    chain = SchemaChain(...)
    subject = Solution(...)
    config = load_configs("invention", "c_major", "confident")
    texture = layer_6_textural("invention", chain, subject, config)
    
    assert texture.treatments[0] == "S"
    assert texture.treatments[1] == "A"
    assert texture.voice_assignments[0] == 0  # Soprano
    assert texture.voice_assignments[1] == 1  # Bass
```

---

## 7. Success Criteria Checklist

- [ ] Every module in architecture.md has a corresponding file specification
- [ ] Every YAML config has a complete schema
- [ ] Every public function has a full signature with types
- [ ] Implementation order has no circular dependencies
- [ ] Test cases cover all hard constraints from architecture
- [ ] Running the implementation produces identical output to `freude_sonata.note`
- [ ] `engine/` folder deleted with no import errors
- [ ] All unit tests pass
- [ ] Integration test passes
- [ ] Determinism verified (same input → same output)

---

## 8. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| CP-SAT performance | Start with small search space (20 bars, 320 slots) |
| Arrival table errors | Cross-check all MIDI values against `freude_sonata.note` |
| Connection logic bugs | Unit test every entry/exit pair from schema spec |
| Import circular deps | Strict layering: types → config → counterpoint → cost → solver → realisation |
| Reference mismatch | Parse `freude_sonata.note` programmatically for comparison |

---

## 9. Post-Implementation

After achieving 100% conformance:

1. Add test for `sonata1.note` (second reference)
2. Enable additional affects (lyrical, grounded)
3. Add G Major and A minor keys
4. Implement minuet genre (YAML only, verify bass pattern generator)
5. Document lessons learned in `docs/lessons.yaml`

---

*End of refactoring plan.*
