"""Domain types for Andante builder.

All types are frozen dataclasses for immutability.
Durations are Fraction. Pitches are MIDI integers.
"""
from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING, Any
from shared.constants import INTERVAL_DISPLAY_NAMES
if TYPE_CHECKING:
    from shared.key import Key
@dataclass
class FigureRejection:
    """Record of why a figure was rejected."""
    figure_name: str
    note_index: int
    pitch: str
    offset: str
    reason: str


def _expand_reason(reason: str) -> str:
    """Convert terse reason code to readable explanation."""
    if reason == "voice_overlap":
        return "voice crossing or overlap with other voice"
    if reason.startswith("range("):
        inner: str = reason[6:-1]
        return f"pitch outside instrument range ({inner})"
    if reason.startswith("melodic_interval("):
        inner = reason[17:-1]
        return f"melodic leap too large: {inner}"
    if reason.startswith("internal_melodic("):
        inner = reason[17:-1]
        return f"internal melodic leap too large: {inner} semitones"
    if reason.startswith("strong_beat_dissonance("):
        inner = reason[23:-1]
        return f"dissonance on strong beat: {inner}"
    if reason.startswith("parallel("):
        inner = reason[9:-1]
        return f"parallel motion to {inner}"
    if reason.startswith("direct_motion_to("):
        inner = reason[17:-1]
        return f"direct (similar) motion to {inner}"
    if reason.startswith("exit_mismatch("):
        inner = reason[14:-1]
        return f"figure exit degree wrong: {inner}"
    return reason


def _format_offset(offset_str: str) -> str:
    """Convert offset string to readable form."""
    if offset_str == "end":
        return "end of figure"
    if offset_str == "0":
        return "start of figure"
    return f"offset {offset_str}"


class FigureRejectionError(Exception):
    """Raised when all figures rejected at a gap."""

    def __init__(
        self,
        bar_num: int,
        interval: str,
        writing_mode: str,
        rejections: list[FigureRejection],
    ) -> None:
        self.bar_num: int = bar_num
        self.interval: str = interval
        self.writing_mode: str = writing_mode
        self.rejections: list[FigureRejection] = rejections
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        interval_readable: str = INTERVAL_DISPLAY_NAMES.get(self.interval, self.interval)
        lines: list[str] = [
            "",
            "=" * 70,
            f"FIGURE REJECTION at bar {self.bar_num}",
            f"  Mode: {self.writing_mode}",
            f"  Interval: {interval_readable}",
            f"  Attempted {len(self.rejections)} figure(s), all rejected:",
            "-" * 70,
        ]
        reason_groups: dict[str, list[FigureRejection]] = {}
        for rej in self.rejections:
            expanded: str = _expand_reason(reason=rej.reason)
            reason_groups.setdefault(expanded, []).append(rej)
        for reason, group in reason_groups.items():
            lines.append(f"\n  {reason}:")
            shown: int = 0
            for rej in group:
                if shown >= 5:
                    remaining: int = len(group) - shown
                    lines.append(f"      ... and {remaining} more with this reason")
                    break
                offset_readable: str = _format_offset(offset_str=rej.offset)
                lines.append(
                    f"    - {rej.figure_name}: note {rej.note_index} "
                    f"({rej.pitch}) at {offset_readable}"
                )
                shown += 1
        lines.append("=" * 70)
        return "\n".join(lines)


from shared.voice_types import (  # noqa: E402 — canonical source (voices.md)
    Actuator,
    Instrument,
    InstrumentDef,
    Range,
    Role,
    ScoringAssignment,
    TrackAssignment,
    Voice,
)


# =============================================================================
# Core Builder Types
# =============================================================================


@dataclass(frozen=True)
class Note:
    """Single note with timing and pitch."""
    offset: Fraction
    pitch: int
    duration: Fraction
    voice: int
    lyric: str = ""


@dataclass(frozen=True)
class CollectedNote:
    """Note collected for dissonance analysis."""
    offset: Fraction
    duration: Fraction
    diatonic: int
    role: str


@dataclass(frozen=True)
class Composition:
    """Complete composed output, voice-indexed."""
    voices: dict[str, tuple[Note, ...]]
    metre: str
    tempo: int
    upbeat: Fraction = Fraction(0)


@dataclass(frozen=True)
class Anchor:
    """Schema arrival constraint at specific bar.beat position.
    
    Degrees are 1-7 (scale degrees). Direction hints indicate approach:
    - up: ascending motion to reach this degree
    - down: descending motion to reach this degree  
    - same: unison (repeat)
    - None: first anchor, no previous context
    
    MIDI resolution is deferred to fill time (phrase_writer) when the
    previous pitch is known, avoiding premature octave decisions.
    """
    bar_beat: str
    upper_degree: int
    lower_degree: int
    local_key: "Key"
    schema: str
    stage: int
    upper_direction: str | None = None
    lower_direction: str | None = None
    section: str = ""


@dataclass(frozen=True)
class MotiveWeights:
    """Motive cost weights from affect."""
    step: float = 0.2
    skip: float = 0.4
    leap: float = 0.8
    large_leap: float = 1.5


@dataclass(frozen=True)
class Solution:
    """Solver output with pitch sequences and cost."""
    soprano_pitches: tuple[int, ...]
    bass_pitches: tuple[int, ...]
    soprano_durations: tuple[Fraction, ...]
    bass_durations: tuple[Fraction, ...]
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
    soprano_directions: tuple[str | None, ...]  # up/down/same/None per degree
    bass_degrees: tuple[int, ...]
    bass_directions: tuple[str | None, ...]  # up/down/same/None per degree
    entry_soprano: int  # derived from soprano_degrees[0]
    entry_bass: int  # derived from bass_degrees[0]
    exit_soprano: int  # derived from soprano_degrees[-1]
    exit_bass: int  # derived from bass_degrees[-1]
    bars_min: int
    bars_max: int
    position: str
    cadential_state: str
    sequential: bool = False
    segments: tuple[int, ...] = (1,)
    direction: str | None = None
    segment_direction: str | None = None  # up/down between segments for sequential
    typical_keys: tuple[str, ...] | None = None


@dataclass(frozen=True)
class GenreConfig:
    """Genre definition from YAML."""
    name: str
    voices: int
    form: str
    metre: str
    rhythmic_unit: str
    tempo: int
    bass_treatment: str  # 'contrapuntal' or 'patterned'
    bass_mode: str  # 'schema' or 'pattern'
    bass_pattern: str | None
    sections: tuple[dict[str, Any], ...]
    upbeat: Fraction = Fraction(0)  # Anacrusis duration in whole notes


@dataclass(frozen=True)
class KeyConfig:
    """Key definition with computed pitch sets."""
    name: str
    pitch_class_set: frozenset[int]
    bridge_pitch_set: frozenset[int]


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
    direction_limit: int
    density_minimum: float
    rhythm_states: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class FormConfig:
    """Form template from YAML."""
    name: str


@dataclass(frozen=True)
class SectionTonalPlan:
    """Tonal plan for a single section."""
    name: str
    key_area: str
    cadence_type: str


@dataclass(frozen=True)
class TonalPlan:
    """Output of Layer 2: tonal regions and cadence allocation."""
    sections: tuple[SectionTonalPlan, ...]
    home_key: str
    modality: str
    density: str


@dataclass(frozen=True)
class SchemaChain:
    """Output of Layer 3: Ordered schema sequence with key areas."""
    schemas: tuple[str, ...]
    key_areas: tuple[str, ...]
    free_passages: frozenset[tuple[int, int]]
    cadences: tuple[str | None, ...] = ()
    section_boundaries: tuple[int, ...] = ()

