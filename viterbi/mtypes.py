"""Data types for the viterbi prototype."""
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Musical constants
# ---------------------------------------------------------------------------

MIDI_C3 = 48
MIDI_C4 = 60
MIDI_C5 = 72

# Beat strength: downbeats/half-bars are strong, beat boundaries moderate, sub-beats weak
STRONG_BEAT = "strong"
MODERATE_BEAT = "moderate"
WEAK_BEAT = "weak"


@dataclass(frozen=True)
class Knot:
    """A structural tone the path must pass through."""
    beat: float
    midi_pitch: int

    def __repr__(self) -> str:
        return f"Knot(beat={self.beat}, pitch={pitch_name(self.midi_pitch)})"


@dataclass(frozen=True)
class LeaderNote:
    """One note of the already-realised leader voice."""
    beat: float
    midi_pitch: int


@dataclass
class Corridor:
    """Legal follower pitches at one grid position."""
    beat: float
    leader_pitch: int
    beat_strength: str
    legal_pitches: list[int] = field(default_factory=list)
    intervals: dict[int, int] = field(default_factory=dict)

    def __repr__(self) -> str:
        names = [pitch_name(p) for p in sorted(self.legal_pitches)]
        return (f"Corridor(beat={self.beat}, leader={pitch_name(self.leader_pitch)}, "
                f"{self.beat_strength}, legal={names})")


@dataclass
class PhraseResult:
    """Complete solved phrase from single Viterbi pass."""
    leader_notes: list[LeaderNote]
    follower_knots: list[Knot]
    corridors: list[Corridor]
    beats: list[float]
    pitches: list[int]
    total_cost: float


# ---------------------------------------------------------------------------
# Pitch naming utility
# ---------------------------------------------------------------------------

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def pitch_name(midi: int) -> str:
    """MIDI number to readable name, e.g. 60 -> 'C4'."""
    octave = (midi // 12) - 1
    note = NOTE_NAMES[midi % 12]
    return f"{note}{octave}"
