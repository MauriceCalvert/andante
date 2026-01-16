"""Octave selection for pitch realisation."""
from fractions import Fraction
from pathlib import Path

import yaml

from shared.parallels import is_parallel_fifth, is_parallel_octave

DATA_DIR: Path = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "predicates.yaml", encoding="utf-8") as _f:
    _P: dict = yaml.safe_load(_f)
_I: dict = _P["intervals"]
_R: dict = _P["registers"]
_RANGES: dict = _P["voice_ranges"]
CONSONANCES: set[int] = set(_P["consonance"]["perfect"] + _P["consonance"]["imperfect"])
OCTAVE: int = _I["octave"]


def voice_range(voice: str) -> tuple[int, int]:
    """Return (low, high) MIDI range for voice."""
    r = _RANGES.get(voice, [48, 84])  # Default to wide range
    return (r[0], r[1])


def register(voice: str) -> int:
    """Center pitch for voice."""
    return _R[voice]


def best_octave(
    midi: int,
    prev_midi: int,
    median: int,
    octave: int,
    voice_range: tuple[int, int] | None = None,
) -> int:
    """Choose octave placement by contour and register gravity.

    Selection by:
    - Minimize interval from previous pitch (contour continuity)
    - Bias toward median (register gravity, weighted 1.0 to prevent drift)
    - If voice_range provided, heavily penalize out-of-range candidates

    Args:
        midi: Base MIDI pitch
        prev_midi: Previous pitch for voice leading
        median: Voice tessitura center
        octave: Octave interval (12)
        voice_range: Optional (min, max) MIDI range for voice
    """
    candidates: list[int] = [midi, midi + octave, midi - octave]

    def score(m: int) -> float:
        interval: float = abs(m - prev_midi)
        register_dist: float = abs(m - median) * 1.0  # Equal weight to prevent drift
        base_score = interval + register_dist
        # Strongly penalize out-of-range pitches
        if voice_range is not None:
            if m < voice_range[0]:
                base_score += (voice_range[0] - m) * 10
            elif m > voice_range[1]:
                base_score += (m - voice_range[1]) * 10
        return base_score

    return min(candidates, key=score)


def best_octave_contrapuntal(
    midi: int,
    prev_midi: int,
    median: int,
    octave: int,
    soprano_midi: int | None,
    consonances: set[int],
) -> int:
    """Choose octave placement ensuring consonance with soprano.

    For two-voice counterpoint, consonance is primary constraint.
    Selection by:
    1. Must be consonant with soprano (if soprano sounding)
    2. Minimize interval from previous pitch (contour continuity)
    3. Bias toward median (register gravity)
    """
    candidates: list[int] = [midi, midi + octave, midi - octave]
    def is_consonant(m: int) -> bool:
        if soprano_midi is None:
            return True
        interval: int = abs(soprano_midi - m) % 12
        return interval in consonances
    def score(m: int) -> float:
        interval: float = abs(m - prev_midi)
        register_dist: float = abs(m - median) * 0.5
        # Consonance is critical - dissonance must be avoided
        consonance_penalty: float = 0.0 if is_consonant(m) else 1000.0
        return consonance_penalty + interval + register_dist
    return min(candidates, key=score)


def best_octave_against(
    midi: int,
    prev_midi: int,
    median: int,
    octave: int,
    ref_pitches: list[tuple[int | None, int | None]],
    consonances: set[int],
    voice_range: tuple[int, int] | None = None,
    skip_parallels: bool = False,
) -> int:
    """Choose octave avoiding parallels with all reference voices.

    Args:
        midi: Target pitch class (pre-octave)
        prev_midi: Previous pitch in this voice
        median: Register center for this voice
        octave: Octave interval (12)
        ref_pitches: List of (prev_pitch, curr_pitch) for each reference voice
        consonances: Consonant intervals for vertical check
        voice_range: Optional (min, max) MIDI range for voice
        skip_parallels: If True, don't penalize parallel motion (for imitative textures)

    Selection priorities:
    1. Avoid parallel fifths/octaves with all reference voices (unless skip_parallels)
    2. Consonance with highest reference voice (soprano)
    3. Stay within voice range
    4. Minimize interval from previous pitch
    5. Bias toward median (stronger pull to prevent register drift)
    """
    candidates: list[int] = [midi, midi + octave, midi - octave]

    def parallel_count(m: int) -> int:
        count: int = 0
        for ref_prev, ref_curr in ref_pitches:
            if ref_prev is None or ref_curr is None:
                continue
            if is_parallel_fifth(ref_prev, prev_midi, ref_curr, m):
                count += 1
            elif is_parallel_fifth(prev_midi, ref_prev, m, ref_curr):
                count += 1
            if is_parallel_octave(ref_prev, prev_midi, ref_curr, m):
                count += 1
            elif is_parallel_octave(prev_midi, ref_prev, m, ref_curr):
                count += 1
        return count

    def is_consonant(m: int) -> bool:
        if not ref_pitches:
            return True
        soprano_curr: int | None = ref_pitches[0][1]
        if soprano_curr is None:
            return True
        interval: int = abs(soprano_curr - m) % 12
        return interval in consonances

    def score(m: int) -> float:
        parallels: int = parallel_count(m)
        parallel_penalty: float = 0.0 if skip_parallels else parallels * 200.0
        # Consonance is critical - dissonance must be avoided at all costs
        consonance_penalty: float = 0.0 if is_consonant(m) else 1000.0
        interval: float = abs(m - prev_midi)
        # For imitative textures (skip_parallels), reduce register weight
        # so melodic contour is prioritized over register drift
        register_weight: float = 0.3 if skip_parallels else 1.0
        register_dist: float = abs(m - median) * register_weight
        # Penalize crossing above soprano (bass should stay below)
        crossing_penalty: float = 0.0
        if ref_pitches:
            soprano_curr: int | None = ref_pitches[0][1]
            if soprano_curr is not None and m > soprano_curr:
                crossing_penalty = 100.0  # Strong penalty for crossing
        # Penalize out-of-range pitches
        range_penalty: float = 0.0
        if voice_range is not None:
            if m < voice_range[0]:
                range_penalty = (voice_range[0] - m) * 10
            elif m > voice_range[1]:
                range_penalty = (m - voice_range[1]) * 10
        return parallel_penalty + consonance_penalty + interval + register_dist + crossing_penalty + range_penalty

    return min(candidates, key=score)


def best_octave_interleaved(
    midi: int,
    prev_midi: int,
    median: int,
    octave: int,
    other_voice_midi: int | None,
    prev_other_midi: int | None,
    consonances: set[int],
) -> int:
    """Choose octave for interleaved counterpoint (Goldberg-style).

    In interleaved mode, voice crossing is REWARDED, not penalized.
    Both voices share the same median (tessitura overlap).

    Selection priorities:
    1. Consonance with other voice
    2. Avoid parallel fifths/octaves (still bad)
    3. Minimize interval from previous pitch (contour continuity)
    4. Light reward for crossing (encourages voice exchange)
    5. Bias toward shared median (keep both voices in same register)
    """
    candidates: list[int] = [midi, midi + octave, midi - octave]

    def has_parallel(m: int) -> bool:
        if other_voice_midi is None or prev_other_midi is None:
            return False
        # Check parallels in both directions (this voice vs other)
        if is_parallel_fifth(prev_other_midi, prev_midi, other_voice_midi, m):
            return True
        if is_parallel_fifth(prev_midi, prev_other_midi, m, other_voice_midi):
            return True
        if is_parallel_octave(prev_other_midi, prev_midi, other_voice_midi, m):
            return True
        if is_parallel_octave(prev_midi, prev_other_midi, m, other_voice_midi):
            return True
        return False

    def is_consonant(m: int) -> bool:
        if other_voice_midi is None:
            return True
        interval: int = abs(other_voice_midi - m) % 12
        return interval in consonances

    def score(m: int) -> float:
        parallel_penalty: float = 200.0 if has_parallel(m) else 0.0
        # Consonance is critical - dissonance must be avoided
        consonance_penalty: float = 0.0 if is_consonant(m) else 1000.0
        interval: float = abs(m - prev_midi)
        register_dist: float = abs(m - median) * 0.5  # Lighter pull - allow crossing
        # REWARD crossing (negative penalty) - encourages Goldberg-style weaving
        crossing_bonus: float = 0.0
        if other_voice_midi is not None:
            # Small reward for being on opposite side of other voice vs previous
            if prev_other_midi is not None:
                was_above: bool = prev_midi > prev_other_midi
                is_above: bool = m > other_voice_midi
                if was_above != is_above:
                    crossing_bonus = -20.0  # Reward voice crossing
        return parallel_penalty + consonance_penalty + interval + register_dist + crossing_bonus

    return min(candidates, key=score)
