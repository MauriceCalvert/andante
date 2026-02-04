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

from shared.constants import SKIP_SEMITONES
from shared.key import Key
from shared.pitch import select_octave

DATA_PATH: Path = Path(__file__).parent.parent.parent / "data" / "figuration" / "bass_patterns.yaml"
MIN_BASS_MIDI: int = 40  # E2 - lowest acceptable bass note (matches VOICE_RANGES)
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


VALID_BASS_MODES: frozenset[str] = frozenset({"schema", "pattern"})


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


# Tritone interval in semitones
TRITONE_SEMITONES: int = 6
# Maximum acceptable leap in bass (octave)
MAX_BASS_LEAP: int = 12


def realise_bass_pattern(
    pattern: BassPattern,
    bass_degree: int,
    key: Key,
    bar_offset: Fraction,
    bar_duration: Fraction,
    bass_median: int,
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
        prev_pitch: Previous bass pitch for voice-leading (None for first bar)
        prev_prev_pitch: Pitch before prev_pitch for consecutive leap detection

    Returns:
        List of (offset, midi_pitch, duration) tuples.
    """
    result: list[tuple[Fraction, int, Fraction]] = []
    beats_per_bar = _get_beats_per_bar(metre=pattern.metre) if pattern.metre != "any" else 4
    beat_duration = bar_duration / beats_per_bar
    current_prev: int | None = prev_pitch
    first_note_midi: int | None = None
    for beat_idx, pattern_beat in enumerate(pattern.beats):
        bar_index = pattern_beat.bar - 1
        beat_offset = (pattern_beat.beat - 1) * beat_duration
        note_offset = bar_offset + (bar_index * bar_duration) + beat_offset
        target_degree = _wrap_degree(degree=bass_degree + pattern_beat.degree_offset)
        midi_pitch = select_octave(
            key=key, degree=target_degree, median=bass_median, prev_pitch=current_prev, alter=pattern_beat.semitone_offset,
        )
        if midi_pitch < MIN_BASS_MIDI:
            midi_pitch += 12
        # Check for consecutive same-direction leaps (on first note of bar only)
        if beat_idx == 0 and prev_pitch is not None and prev_prev_pitch is not None:
            int1 = prev_pitch - prev_prev_pitch
            int2 = midi_pitch - prev_pitch
            # Both must be leaps (> SKIP_SEMITONES) in same direction
            if abs(int1) > SKIP_SEMITONES and abs(int2) > SKIP_SEMITONES:
                if (int1 > 0) == (int2 > 0):
                    # Try octave shift to create contrary motion
                    if int2 > 0:
                        alt_pitch = midi_pitch - 12
                    else:
                        alt_pitch = midi_pitch + 12
                    if MIN_BASS_MIDI <= alt_pitch <= bass_median + 12:
                        new_int2 = alt_pitch - prev_pitch
                        # Verify contrary motion and no grotesque leap
                        if (int1 > 0) != (new_int2 > 0) and abs(new_int2) <= MAX_BASS_LEAP:
                            midi_pitch = alt_pitch
        # Check for tritone - octave shifts don't help since tritone is pitch-class based
        if current_prev is not None:
            interval = abs(midi_pitch - current_prev)
            # Tritone detected - try octave shifts first
            if interval == TRITONE_SEMITONES:
                alt_up = midi_pitch + 12
                alt_down = midi_pitch - 12 if midi_pitch - 12 >= MIN_BASS_MIDI else midi_pitch
                int_up = abs(alt_up - current_prev)
                int_down = abs(alt_down - current_prev)
                # Tritone persists across octaves, so pick the smaller interval
                # (perfect fourth = 5 semitones vs tritone = 6)
                if int_up < interval and int_up <= MAX_BASS_LEAP:
                    midi_pitch = alt_up
                elif int_down < interval and alt_down >= MIN_BASS_MIDI:
                    midi_pitch = alt_down
                else:
                    # Still tritone - hold previous note instead
                    if first_note_midi is not None and beat_idx > 0:
                        midi_pitch = first_note_midi
            elif interval > MAX_BASS_LEAP:
                alt_up = midi_pitch + 12
                alt_down = midi_pitch - 12
                int_up = abs(alt_up - current_prev)
                int_down = abs(alt_down - current_prev)
                if int_up <= MAX_BASS_LEAP:
                    midi_pitch = alt_up
                elif alt_down >= MIN_BASS_MIDI and int_down <= MAX_BASS_LEAP:
                    midi_pitch = alt_down
        if beat_idx == 0:
            first_note_midi = midi_pitch
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


def realise_bass_schema(
    pattern: RhythmPattern,
    current_degree: int,
    next_degree: int | None,
    key: Key,
    bar_offset: Fraction,
    bar_duration: Fraction,
    bass_median: int,
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
        prev_pitch: Previous bass pitch for voice-leading

    Returns:
        List of (offset, midi_pitch, duration) tuples.
    """
    result: list[tuple[Fraction, int, Fraction]] = []
    beats_per_bar = _get_beats_per_bar(metre=pattern.metre) if pattern.metre != "any" else 4
    beat_duration = bar_duration / beats_per_bar
    current_prev: int | None = prev_pitch
    for rhythm_beat in pattern.beats:
        beat_offset = (rhythm_beat.beat - 1) * beat_duration
        note_offset = bar_offset + beat_offset
        if rhythm_beat.use_next and next_degree is not None:
            degree = next_degree
        else:
            degree = current_degree
        midi_pitch = select_octave(key=key, degree=degree, median=bass_median, prev_pitch=current_prev)
        if midi_pitch < MIN_BASS_MIDI:
            midi_pitch += 12
        current_prev = midi_pitch
        if rhythm_beat.duration == Fraction(-1):
            note_duration = bar_duration
        elif rhythm_beat.duration == Fraction(-2):
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
