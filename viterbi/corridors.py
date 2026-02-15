"""Corridor builder: given existing voices, compute legal follower pitches per beat."""
from viterbi.mtypes import (
    Corridor,
    ExistingVoice,
    STRONG_BEAT,
    MODERATE_BEAT,
    WEAK_BEAT,
)
from viterbi.scale import (
    build_pitch_set,
    KeyInfo,
    CMAJ,
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
    beat_grid: list[float],
    existing_voices: list[ExistingVoice],
    follower_low: int = FOLLOWER_LOW,
    follower_high: int = FOLLOWER_HIGH,
    key: KeyInfo = CMAJ,
    beats_per_bar: float = 4.0,
) -> list[Corridor]:
    """Build corridor map from existing voices.

    All beats: all diatonic pitches in range (dissonance penalised by cost function).
    """
    candidates = build_pitch_set(follower_low, follower_high, key)
    corridors = []
    for beat in beat_grid:
        strength = beat_strength(beat, beats_per_bar)
        # Diagnostic: first existing voice's pitch at this beat
        diag_pitch: int = existing_voices[0].pitches_at_beat[beat] if existing_voices else 0
        # Collect all existing voice pitches at this beat (for diagnostics)
        other_pitches: list[int] = [
            v.pitches_at_beat[beat] for v in existing_voices
        ]
        legal = list(candidates)
        intervals = {p: abs(p - diag_pitch) for p in candidates}
        corridors.append(Corridor(
            beat=beat,
            leader_pitch=diag_pitch,
            beat_strength=strength,
            legal_pitches=legal,
            intervals=intervals,
        ))
    return corridors
