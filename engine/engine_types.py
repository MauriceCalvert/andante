"""Engine types: AST nodes and intermediate representations."""
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Any

from shared.pitch import Pitch
from shared.types import ExpandedVoices, VoiceMaterial

if TYPE_CHECKING:
    from planner.subject import Subject


@dataclass(frozen=True)
class PhraseAST:
    """Parsed phrase from YAML."""
    index: int
    bars: int
    tonal_target: str
    cadence: str | None
    treatment: str
    surprise: str | None
    is_climax: bool = False
    articulation: str | None = None
    rhythm: str | None = None
    device: str | None = None
    gesture: str | None = None
    energy: str | None = None
    texture: str | None = None  # Phrase-level texture override (inherits from episode if None)
    voice_assignments: tuple[str, ...] | None = None


@dataclass(frozen=True)
class EpisodeAST:
    """Parsed episode from YAML."""
    type: str
    bars: int
    texture: str
    phrases: tuple[PhraseAST, ...]
    is_transition: bool = False


@dataclass(frozen=True)
class SectionAST:
    """Parsed section from YAML."""
    label: str
    tonal_path: tuple[str, ...]
    final_cadence: str
    episodes: tuple[EpisodeAST, ...]


@dataclass(frozen=True)
class MotifAST:
    """Parsed motif from YAML."""
    pitches: tuple[Pitch, ...]
    durations: tuple[Fraction, ...]
    bars: int


@dataclass(frozen=True)
class PieceAST:
    """Complete parsed piece."""
    key: str
    mode: str
    metre: str
    tempo: str
    voices: int
    subject: Any  # Subject from planner (TYPE_CHECKING)
    sections: tuple[SectionAST, ...]
    arc: str
    upbeat: Fraction = Fraction(0)
    form: str = "through_composed"
    virtuosic: bool = False
    bass_source: str = "subject"  # Genre-specific: accompaniment, counter_subject, etc.


@dataclass(frozen=True)
class ExpandedPhrase:
    """Phrase expanded to bar-level pitches for N voices."""
    index: int
    bars: int
    voices: ExpandedVoices
    cadence: str | None
    tonal_target: str
    is_climax: bool = False
    articulation: str | None = None
    gesture: str | None = None
    energy: str | None = None
    surprise: str | None = None
    texture: str = "polyphonic"
    episode_type: str | None = None
    treatment: str | None = None

    @property
    def soprano_pitches(self) -> tuple[Pitch, ...]:
        return tuple(self.voices.soprano.pitches)

    @property
    def soprano_durations(self) -> tuple[Fraction, ...]:
        return tuple(self.voices.soprano.durations)

    @property
    def bass_pitches(self) -> tuple[Pitch, ...]:
        return tuple(self.voices.bass.pitches)

    @property
    def bass_durations(self) -> tuple[Fraction, ...]:
        return tuple(self.voices.bass.durations)


@dataclass(frozen=True)
class RealisedNote:
    """Concrete note with MIDI pitch."""
    offset: Fraction
    pitch: int
    duration: Fraction
    voice: str


@dataclass(frozen=True)
class RealisedVoice:
    """Concrete notes for a single voice."""
    voice_index: int
    notes: list[RealisedNote]

    @property
    def note_count(self) -> int:
        return len(self.notes)


@dataclass(frozen=True)
class RealisedPhrase:
    """Phrase with concrete MIDI pitches for N voices."""
    index: int
    voices: list[RealisedVoice]
    treatment: str | None = None
    texture: str | None = None

    @property
    def soprano(self) -> tuple[RealisedNote, ...]:
        return tuple(self.voices[0].notes)

    @property
    def bass(self) -> tuple[RealisedNote, ...]:
        return tuple(self.voices[-1].notes)


@dataclass(frozen=True)
class Annotation:
    """Text annotation at a specific offset."""
    offset: Fraction
    text: str
    level: str


@dataclass(frozen=True)
class PieceMetrics:
    """Proportion tracking for thematic vs free material."""
    total_bars: int
    subject_bars: int
    derived_bars: int
    episode_bars: int
    free_bars: int

    @property
    def thematic_ratio(self) -> float:
        """Ratio of thematic (subject + derived) to total material."""
        if self.total_bars == 0:
            return 0.0
        return (self.subject_bars + self.derived_bars) / self.total_bars

    @property
    def variety_ratio(self) -> float:
        """Ratio of non-subject material to total."""
        if self.total_bars == 0:
            return 0.0
        return (self.derived_bars + self.episode_bars + self.free_bars) / self.total_bars


__all__ = [
    "Annotation",
    "EpisodeAST",
    "ExpandedPhrase",
    "ExpandedVoices",
    "MotifAST",
    "PhraseAST",
    "PieceAST",
    "PieceMetrics",
    "RealisedNote",
    "RealisedPhrase",
    "RealisedVoice",
    "SectionAST",
    "VoiceMaterial",
]
