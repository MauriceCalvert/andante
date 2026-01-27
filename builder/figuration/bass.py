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

from shared.key import Key
from shared.pitch import select_octave

DATA_PATH: Path = Path(__file__).parent.parent.parent / "data" / "figuration" / "bass_patterns.yaml"
MIN_BASS_MIDI: int = 36  # C2 - lowest acceptable bass note
VALID_BASS_TREATMENTS: frozenset[str] = frozenset({"contrapuntal", "patterned"})
VALID_TEXTURES: frozenset[str] = frozenset({"continuo", "arpeggiated", "ostinato", "pedal"})
VALID_HARMONIC_RHYTHMS: frozenset[str] = frozenset({"per_bar", "per_half", "per_beat", "none"})


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


def _parse_duration(
    dur: str | int | float,
    metre: str,
) -> Fraction:
    """Parse duration token to Fraction."""
    if dur == "bar":
        return Fraction(-1)
    if dur == "half":
        return Fraction(-2)
    return Fraction(dur)


def _parse_beat_position(
    beat: str | int | float,
    metre: str,
) -> Fraction:
    """Parse beat position, handling 'half' token."""
    if beat == "half":
        beats_per_bar = _get_beats_per_bar(metre)
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
            beat_pos = _parse_beat_position(beat_data["beat"], metre)
            dur = _parse_duration(beat_data["duration"], metre)
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
    if bass_treatment == "patterned":
        assert bass_pattern is not None, (
            f"Genre '{genre_name}' with bass_treatment='patterned' must specify bass_pattern"
        )
        patterns = get_bass_patterns()
        assert bass_pattern in patterns, (
            f"Genre '{genre_name}' specifies unknown bass_pattern '{bass_pattern}'; "
            f"available: {', '.join(sorted(patterns.keys()))}"
        )


def realise_bass_pattern(
    pattern: BassPattern,
    bass_degree: int,
    key: Key,
    bar_offset: Fraction,
    bar_duration: Fraction,
    bass_median: int,
    prev_pitch: int | None = None,
) -> list[tuple[Fraction, int, Fraction]]:
    """Realise a bass pattern into (offset, midi, duration) tuples.

    Uses select_octave for canonical pitch placement with voice-leading.

    Args:
        pattern: Bass pattern to realise
        bass_degree: Anchor bass degree (1-7)
        key: Musical key for pitch calculation
        bar_offset: Start offset of the bar (whole notes)
        bar_duration: Duration of the bar (whole notes)
        bass_median: Median pitch for bass voice
        prev_pitch: Previous bass pitch for voice-leading (None for first bar)

    Returns:
        List of (offset, midi_pitch, duration) tuples.
    """
    result: list[tuple[Fraction, int, Fraction]] = []
    beats_per_bar = _get_beats_per_bar(pattern.metre) if pattern.metre != "any" else 4
    beat_duration = bar_duration / beats_per_bar
    current_prev: int | None = prev_pitch
    for pattern_beat in pattern.beats:
        bar_index = pattern_beat.bar - 1
        beat_offset = (pattern_beat.beat - 1) * beat_duration
        note_offset = bar_offset + (bar_index * bar_duration) + beat_offset
        target_degree = _wrap_degree(bass_degree + pattern_beat.degree_offset)
        midi_pitch = select_octave(
            key, target_degree, bass_median, current_prev, pattern_beat.semitone_offset,
        )
        if midi_pitch < MIN_BASS_MIDI:
            midi_pitch += 12
        current_prev = midi_pitch
        if pattern_beat.duration == Fraction(-1):
            note_duration = bar_duration
        elif pattern_beat.duration == Fraction(-2):
            note_duration = bar_duration / 2
        else:
            note_duration = pattern_beat.duration * beat_duration
        result.append((note_offset, midi_pitch, note_duration))
    return result


def _get_beats_per_bar(metre: str) -> int:
    """Extract beats per bar from metre string."""
    if metre == "any":
        return 4
    parts = metre.split("/")
    return int(parts[0])


def _wrap_degree(degree: int) -> int:
    """Wrap scale degree to 1-7 range."""
    return ((degree - 1) % 7) + 1


def clear_cache() -> None:
    """Clear the patterns cache."""
    global _patterns_cache
    _patterns_cache = None
