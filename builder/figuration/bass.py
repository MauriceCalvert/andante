"""Bass pattern realisation.

Loads bass accompaniment patterns from YAML and realises them
using degree-based pitch calculation.

Bass treatment is explicit per genre:
- contrapuntal: bass uses same figuration system as soprano
- patterned: bass uses accompaniment patterns from this module
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from shared.constants import (
    BEAT_SENTINEL_HALF,
    DURATION_SENTINEL_BAR,
    DURATION_SENTINEL_HALF,
    MAX_BASS_LEAP,
    MIN_BASS_MIDI,
    SKIP_SEMITONES,
    TRITONE_SEMITONES,
    VALID_BASS_MODES,
    VALID_BASS_TREATMENTS,
    VALID_HARMONIC_RHYTHMS,
    VALID_TEXTURES,
)
from shared.key import Key
from shared.pitch import place_degree, select_octave

DATA_PATH: Path = Path(__file__).parent.parent.parent / "data" / "figuration" / "bass_patterns.yaml"


@dataclass(frozen=True)
class BassPatternBeat:
    """Single beat in a bass pattern."""
    beat: Fraction
    degree_offset: int
    duration: Fraction
    bar: int = 1
    semitone_offset: int = 0


@dataclass(frozen=True)
class BassPattern:
    """Bass accompaniment pattern."""
    name: str
    texture: str
    harmonic_rhythm: str
    metre: str
    description: str
    beats: tuple[BassPatternBeat, ...]
    multi_bar: int = 1
    chromatic: bool = False


@dataclass(frozen=True)
class RhythmBeat:
    """Single beat in a rhythm-only pattern."""
    beat: Fraction
    duration: Fraction
    use_next: bool = False  # True = use next anchor's degree


@dataclass(frozen=True)
class RhythmPattern:
    """Rhythm-only bass pattern (pitches from schema)."""
    name: str
    metre: str
    description: str
    beats: tuple[RhythmBeat, ...]


def _parse_duration(
    dur: str | int | float,
    metre: str,
) -> Fraction:
    """Parse duration token to Fraction."""
    if dur == "bar":
        return DURATION_SENTINEL_BAR
    if dur == "half":
        return DURATION_SENTINEL_HALF
    return Fraction(dur)


def _parse_beat_position(
    beat: str | int | float,
    metre: str,
) -> Fraction:
    """Parse beat position, handling 'half' token."""
    if beat == "half":
        if metre == "any":
            return BEAT_SENTINEL_HALF
        beats_per_bar = _get_beats_per_bar(metre=metre)
        return Fraction(beats_per_bar // 2 + 1)
    return Fraction(beat)


def load_bass_patterns(path: Path | None = None) -> dict[str, BassPattern]:
    """Load bass patterns from YAML."""
    if path is None:
        path = DATA_PATH
    assert path.exists(), f"Bass patterns file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)
    result: dict[str, BassPattern] = {}
    for name, data in raw.items():
        metre = data.get("metre", "any")
        texture = data.get("texture", "continuo")
        harmonic_rhythm = data.get("harmonic_rhythm", "per_bar")
        assert texture in VALID_TEXTURES, f"Invalid texture '{texture}' in pattern '{name}'"
        assert harmonic_rhythm in VALID_HARMONIC_RHYTHMS, f"Invalid harmonic_rhythm '{harmonic_rhythm}' in pattern '{name}'"
        beats: list[BassPatternBeat] = []
        for beat_data in data.get("beats", []):
            beat_pos = _parse_beat_position(beat=beat_data["beat"], metre=metre)
            dur = _parse_duration(dur=beat_data["duration"], metre=metre)
            beats.append(BassPatternBeat(
                beat=beat_pos,
                degree_offset=int(beat_data["degree_offset"]),
                duration=dur,
                bar=int(beat_data.get("bar", 1)),
                semitone_offset=int(beat_data.get("semitone_offset", 0)),
            ))
        result[name] = BassPattern(
            name=name,
            texture=texture,
            harmonic_rhythm=harmonic_rhythm,
            metre=metre,
            description=data.get("description", ""),
            beats=tuple(beats),
            multi_bar=int(data.get("multi_bar", 1)),
            chromatic=bool(data.get("chromatic", False)),
        )
    return result


_patterns_cache: dict[str, BassPattern] | None = None
_rhythm_cache: dict[str, RhythmPattern] | None = None


def load_rhythm_patterns(path: Path | None = None) -> dict[str, RhythmPattern]:
    """Load rhythm-only patterns from YAML."""
    if path is None:
        path = DATA_PATH.parent / "rhythm_patterns.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    result: dict[str, RhythmPattern] = {}
    for name, data in raw.items():
        metre = data.get("metre", "any")
        beats: list[RhythmBeat] = []
        for beat_data in data.get("beats", []):
            beat_pos = _parse_beat_position(beat=beat_data["beat"], metre=metre)
            dur = _parse_duration(dur=beat_data["duration"], metre=metre)
            beats.append(RhythmBeat(
                beat=beat_pos,
                duration=dur,
                use_next=bool(beat_data.get("use_next", False)),
            ))
        result[name] = RhythmPattern(
            name=name,
            metre=metre,
            description=data.get("description", ""),
            beats=tuple(beats),
        )
    return result


def get_rhythm_patterns() -> dict[str, RhythmPattern]:
    """Get cached rhythm patterns."""
    global _rhythm_cache
    if _rhythm_cache is None:
        _rhythm_cache = load_rhythm_patterns()
    return _rhythm_cache


def get_rhythm_pattern(name: str) -> RhythmPattern | None:
    """Get a specific rhythm pattern by name."""
    patterns = get_rhythm_patterns()
    return patterns.get(name)


def get_bass_patterns() -> dict[str, BassPattern]:
    """Get cached bass patterns."""
    global _patterns_cache
    if _patterns_cache is None:
        _patterns_cache = load_bass_patterns()
    return _patterns_cache


def get_bass_pattern(name: str) -> BassPattern | None:
    """Get a specific bass pattern by name."""
    patterns = get_bass_patterns()
    return patterns.get(name)


def get_patterns_by_texture(texture: str) -> list[BassPattern]:
    """Get all patterns of a given texture type."""
    assert texture in VALID_TEXTURES, f"Invalid texture: {texture}"
    patterns = get_bass_patterns()
    return [p for p in patterns.values() if p.texture == texture]


def get_patterns_for_metre(metre: str) -> list[BassPattern]:
    """Get all patterns compatible with a metre."""
    patterns = get_bass_patterns()
    return [p for p in patterns.values() if p.metre == metre or p.metre == "any"]


def validate_bass_treatment(
    bass_treatment: str | None,
    bass_mode: str,
    bass_pattern: str | None,
    genre_name: str,
) -> None:
    """Validate bass treatment configuration."""
    assert bass_treatment is not None, (
        f"Genre '{genre_name}' must specify bass_treatment: 'contrapuntal' or 'patterned'"
    )
    assert bass_treatment in VALID_BASS_TREATMENTS, (
        f"Genre '{genre_name}' has invalid bass_treatment '{bass_treatment}'; "
        f"must be one of: {', '.join(sorted(VALID_BASS_TREATMENTS))}"
    )
    assert bass_mode in VALID_BASS_MODES, (
        f"Genre '{genre_name}' has invalid bass_mode '{bass_mode}'; "
        f"must be one of: {', '.join(sorted(VALID_BASS_MODES))}"
    )
    if bass_treatment == "patterned":
        assert bass_pattern is not None, (
            f"Genre '{genre_name}' with bass_treatment='patterned' must specify bass_pattern"
        )
        patterns = get_bass_patterns()
        rhythm_patterns = get_rhythm_patterns()
        all_patterns = set(patterns.keys()) | set(rhythm_patterns.keys())
        assert bass_pattern in all_patterns, (
            f"Genre '{genre_name}' specifies unknown bass_pattern '{bass_pattern}'; "
            f"available: {', '.join(sorted(all_patterns))}"
        )


_TRITONE_PENALTY: float = 100.0
_LARGE_LEAP_PENALTY: float = 50.0
_CONSECUTIVE_LEAP_PENALTY: float = 30.0
_INTERVAL_WEIGHT: float = 0.5
_MEDIAN_WEIGHT: float = 0.1


def _select_bass_pitch(
    key: Key,
    degree: int,
    bass_median: int,
    prev_pitch: int | None,
    prev_prev_pitch: int | None,
    alter: int = 0,
    is_bar_start: bool = False,
) -> int:
    """Select best bass pitch via candidate scoring.

    Evaluates the default placement and its octave neighbours,
    picking the candidate with the lowest penalty. Penalties cover:
    - Tritone intervals from prev_pitch
    - Leaps exceeding MAX_BASS_LEAP
    - Consecutive same-direction leaps (bar boundaries only)
    - Distance from median (mild gravity)
    """
    base: int = place_degree(key=key, degree=degree, median=bass_median, prev_pitch=prev_pitch, alter=alter)
    candidates: list[int] = [c for c in (base - 12, base, base + 12) if c >= MIN_BASS_MIDI and c <= bass_median + 12]
    if not candidates:
        return max(base, MIN_BASS_MIDI)
    best: int = candidates[0]
    best_penalty: float = float("inf")
    for cand in candidates:
        penalty: float = abs(cand - bass_median) * _MEDIAN_WEIGHT
        if prev_pitch is not None:
            interval: int = abs(cand - prev_pitch)
            if interval == TRITONE_SEMITONES:
                penalty += _TRITONE_PENALTY
            if interval > MAX_BASS_LEAP:
                penalty += _LARGE_LEAP_PENALTY
            penalty += interval * _INTERVAL_WEIGHT
            if is_bar_start and prev_prev_pitch is not None:
                int1: int = prev_pitch - prev_prev_pitch
                int2: int = cand - prev_pitch
                if abs(int1) > SKIP_SEMITONES and abs(int2) > SKIP_SEMITONES:
                    if (int1 > 0) == (int2 > 0):
                        penalty += _CONSECUTIVE_LEAP_PENALTY
        if penalty < best_penalty:
            best_penalty = penalty
            best = cand
    return best


def realise_bass_pattern(
    pattern: BassPattern,
    bass_degree: int,
    key: Key,
    bar_offset: Fraction,
    bar_duration: Fraction,
    bass_median: int,
    metre: str,
    prev_pitch: int | None = None,
    prev_prev_pitch: int | None = None,
) -> list[tuple[Fraction, int, Fraction]]:
    """Realise a bass pattern into (offset, midi, duration) tuples.

    Uses select_octave for canonical pitch placement with voice-leading.
    Avoids tritone leaps and consecutive same-direction leaps.

    Args:
        pattern: Bass pattern to realise
        bass_degree: Anchor bass degree (1-7)
        key: Musical key for pitch calculation
        bar_offset: Start offset of the bar (whole notes)
        bar_duration: Duration of the bar (whole notes)
        bass_median: Median pitch for bass voice
        metre: Actual metre of the piece (used when pattern.metre is 'any')
        prev_pitch: Previous bass pitch for voice-leading (None for first bar)
        prev_prev_pitch: Pitch before prev_pitch for consecutive leap detection

    Returns:
        List of (offset, midi_pitch, duration) tuples.
    """
    result: list[tuple[Fraction, int, Fraction]] = []
    effective_metre: str = metre if pattern.metre == "any" else pattern.metre
    beats_per_bar = _get_beats_per_bar(metre=effective_metre)
    beat_duration = bar_duration / beats_per_bar
    current_prev: int | None = prev_pitch
    for beat_idx, pattern_beat in enumerate(pattern.beats):
        bar_index = pattern_beat.bar - 1
        resolved_beat = _resolve_beat_position(beat=pattern_beat.beat, beats_per_bar=beats_per_bar)
        beat_offset = (resolved_beat - 1) * beat_duration
        note_offset = bar_offset + (bar_index * bar_duration) + beat_offset
        target_degree = _wrap_degree(degree=bass_degree + pattern_beat.degree_offset)
        midi_pitch = _select_bass_pitch(
            key=key,
            degree=target_degree,
            bass_median=bass_median,
            prev_pitch=current_prev,
            prev_prev_pitch=prev_prev_pitch if beat_idx == 0 else None,
            alter=pattern_beat.semitone_offset,
            is_bar_start=beat_idx == 0,
        )
        current_prev = midi_pitch
        if pattern_beat.duration == DURATION_SENTINEL_BAR:
            note_duration = bar_duration
        elif pattern_beat.duration == DURATION_SENTINEL_HALF:
            note_duration = bar_duration / 2
        else:
            note_duration = pattern_beat.duration * beat_duration
        result.append((note_offset, midi_pitch, note_duration))
    return result


def _get_beats_per_bar(metre: str) -> int:
    """Extract beats per bar from metre string."""
    assert metre != "any", (
        "Cannot derive beats_per_bar from metre='any'; "
        "caller must resolve the actual metre before calling"
    )
    parts = metre.split("/")
    return int(parts[0])


def _resolve_beat_position(
    beat: Fraction,
    beats_per_bar: int,
) -> Fraction:
    """Resolve deferred beat sentinels to actual positions."""
    if beat == BEAT_SENTINEL_HALF:
        return Fraction(beats_per_bar // 2 + 1)
    return beat


def _wrap_degree(degree: int) -> int:
    """Wrap scale degree to 1-7 range."""
    return ((degree - 1) % 7) + 1


def realise_bass_schema(
    pattern: RhythmPattern,
    current_degree: int,
    next_degree: int | None,
    key: Key,
    bar_offset: Fraction,
    bar_duration: Fraction,
    bass_median: int,
    metre: str,
    prev_pitch: int | None = None,
) -> list[tuple[Fraction, int, Fraction]]:
    """Realise bass from schema degrees with rhythm pattern.

    Pitches come from schema (current_degree, next_degree).
    Pattern only controls timing.

    Args:
        pattern: Rhythm-only pattern specifying beat positions
        current_degree: Current anchor's bass degree
        next_degree: Next anchor's bass degree (None if final)
        key: Musical key for pitch calculation
        bar_offset: Start offset of the bar (whole notes)
        bar_duration: Duration of the bar (whole notes)
        bass_median: Median pitch for bass voice
        metre: Actual metre of the piece (used when pattern.metre is 'any')
        prev_pitch: Previous bass pitch for voice-leading

    Returns:
        List of (offset, midi_pitch, duration) tuples.
    """
    result: list[tuple[Fraction, int, Fraction]] = []
    effective_metre: str = metre if pattern.metre == "any" else pattern.metre
    beats_per_bar = _get_beats_per_bar(metre=effective_metre)
    beat_duration = bar_duration / beats_per_bar
    current_prev: int | None = prev_pitch
    for rhythm_beat in pattern.beats:
        resolved_beat = _resolve_beat_position(beat=rhythm_beat.beat, beats_per_bar=beats_per_bar)
        beat_offset = (resolved_beat - 1) * beat_duration
        note_offset = bar_offset + beat_offset
        if rhythm_beat.use_next and next_degree is not None:
            degree = next_degree
        else:
            degree = current_degree
        midi_pitch = select_octave(key=key, degree=degree, median=bass_median, prev_pitch=current_prev)
        if midi_pitch < MIN_BASS_MIDI:
            midi_pitch += 12
        current_prev = midi_pitch
        if rhythm_beat.duration == DURATION_SENTINEL_BAR:
            note_duration = bar_duration
        elif rhythm_beat.duration == DURATION_SENTINEL_HALF:
            note_duration = bar_duration / 2
        else:
            note_duration = rhythm_beat.duration * beat_duration
        result.append((note_offset, midi_pitch, note_duration))
    return result


def clear_cache() -> None:
    """Clear the patterns cache."""
    global _patterns_cache, _rhythm_cache
    _patterns_cache = None
    _rhythm_cache = None
