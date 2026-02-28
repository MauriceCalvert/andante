"""Types for the imitative composition path.

Frozen dataclasses defining the structural plan for subject-driven
genres (invention, fugue). No logic — just data definitions.
"""
from dataclasses import dataclass

from shared.key import Key


@dataclass(frozen=True)
class VoiceAssignment:
    """What one voice does in one bar."""
    role: str          # "subject", "answer", "cs", "episode", "free", "cadence", "pedal"
    material_key: Key  # key for transposition
    texture: str       # "plain", "bariolage_single", etc.
    pairing: str       # "independent", "parallel_10ths", etc.
    fragment: str | None        # "head", "tail", None
    fragment_iteration: int     # sequential transposition index; 0 for episodes (trajectory computed at render time)


@dataclass(frozen=True)
class BarAssignment:
    """What happens in one bar."""
    bar: int              # 1-based
    section: str          # "exposition", "development", etc.
    function: str         # "entry", "episode", "cadence", "stretto", "pedal"
    local_key: Key
    voices: dict[int, VoiceAssignment]
    entry_index: int = 0           # monotonically increasing per logical entry
    cadence_schema: str | None = None  # cadence template name; None for non-cadence bars


@dataclass(frozen=True)
class SubjectPlan:
    """Complete structural plan for an imitative piece."""
    bars: tuple[BarAssignment, ...]
    total_bars: int
    home_key: Key
    metre: str
    answer_offset_beats: int = 0
    cadence_schema: str = "cadenza_composta"
