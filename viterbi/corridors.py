"""Corridor builder: given leader surface, compute legal follower pitches per beat."""
from viterbi.scale import (
    build_pitch_set,
    is_consonant,
    KeyInfo,
    CMAJ,
)
from viterbi.mtypes import (
    Corridor,
    LeaderNote,
    STRONG_BEAT,
    MODERATE_BEAT,
    WEAK_BEAT,
)

# Follower pitch range (soprano)
FOLLOWER_LOW = 60   # C4
FOLLOWER_HIGH = 84  # C6


def beat_strength(position: float, beats_per_bar: float = 4.0) -> str:
    """Classify beat strength from position.

    - Downbeat (position % beats_per_bar == 0): STRONG_BEAT
    - Half-bar (position % beats_per_bar == beats_per_bar/2): STRONG_BEAT
    - Beat boundary (position % 1.0 == 0): MODERATE_BEAT
    - Everything else: WEAK_BEAT
    """
    bar_pos = position % beats_per_bar
    if abs(bar_pos - 0.0) < 1e-9:
        return STRONG_BEAT
    if abs(bar_pos - beats_per_bar / 2.0) < 1e-9:
        return STRONG_BEAT
    if abs(position % 1.0) < 1e-9:
        return MODERATE_BEAT
    return WEAK_BEAT


def build_corridors(
    leader_notes: list[LeaderNote],
    follower_low: int = FOLLOWER_LOW,
    follower_high: int = FOLLOWER_HIGH,
    key: KeyInfo = CMAJ,
    beats_per_bar: float = 4.0,
) -> list[Corridor]:
    """Build corridor map from leader surface.

    Strong beats: consonances only.
    Moderate and weak beats: all diatonic pitches (dissonance penalised by cost function).
    """
    candidates = build_pitch_set(follower_low, follower_high, key)
    corridors = []
    for ln in leader_notes:
        strength = beat_strength(ln.beat, beats_per_bar)
        legal = []
        intervals = {}
        for p in candidates:
            interval = abs(p - ln.midi_pitch)
            if strength == STRONG_BEAT:
                if is_consonant(interval):
                    legal.append(p)
                    intervals[p] = interval
            else:
                legal.append(p)
                intervals[p] = interval
        corridors.append(Corridor(
            beat=ln.beat,
            leader_pitch=ln.midi_pitch,
            beat_strength=strength,
            legal_pitches=legal,
            intervals=intervals,
        ))
    return corridors
