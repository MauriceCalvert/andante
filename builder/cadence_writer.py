"""Cadential voice-leading from fixed templates.

Cadential schemas use predetermined note sequences, not generation.
This guarantees correct resolution.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from builder.types import Note
from shared.constants import PHRASE_VOICE_BASS, TRACK_SOPRANO, VALID_DURATIONS
from shared.key import Key

DATA_DIR: Path = Path(__file__).parent.parent / "data"
VALID_DURATIONS_SET: frozenset[Fraction] = frozenset(VALID_DURATIONS)
METRE_BAR_LENGTH: dict[str, Fraction] = {
    "3/4": Fraction(3, 4),
    "4/4": Fraction(1),
}


@dataclass(frozen=True)
class CadenceTemplate:
    """Fixed voice-leading template for a cadential schema."""
    schema_name: str
    metre: str
    bars: int
    soprano_degrees: tuple[int, ...]
    soprano_durations: tuple[Fraction, ...]
    bass_degrees: tuple[int, ...]
    bass_durations: tuple[Fraction, ...]


_cache: dict[tuple[str, str], CadenceTemplate] | None = None


def _degree_to_nearest_midi(
    degree: int,
    key: Key,
    target_midi: int,
    midi_range: tuple[int, int],
    ceiling: int | None = None,
) -> int:
    """Place degree in octave nearest to target_midi, within range and below ceiling."""
    candidates: list[int] = [
        key.degree_to_midi(degree=degree, octave=octave) for octave in range(2, 7)
    ]
    valid: list[int] = [
        m for m in candidates if midi_range[0] <= m <= midi_range[1]
    ]
    if ceiling is not None:
        below: list[int] = [m for m in valid if m < ceiling]
        if below:
            valid = below
    assert len(valid) > 0, (
        f"No valid octave for degree {degree} in range {midi_range}"
    )
    return min(valid, key=lambda m: abs(m - target_midi))


def _parse_fraction(s: str) -> Fraction:
    """Parse fraction string like '1/4' or '1' to Fraction."""
    if "/" in s:
        num, denom = s.split("/")
        return Fraction(int(num), int(denom))
    return Fraction(int(s))


def _validate_template(
    schema_name: str,
    metre: str,
    bars: int,
    soprano_degrees: tuple[int, ...],
    soprano_durations: tuple[Fraction, ...],
    bass_degrees: tuple[int, ...],
    bass_durations: tuple[Fraction, ...],
) -> None:
    """Validate template invariants."""
    assert metre in METRE_BAR_LENGTH, (
        f"Template '{schema_name}/{metre}': unknown metre"
    )
    bar_length: Fraction = METRE_BAR_LENGTH[metre]
    expected_duration: Fraction = bar_length * bars
    soprano_sum: Fraction = sum(soprano_durations, Fraction(0))
    bass_sum: Fraction = sum(bass_durations, Fraction(0))
    assert soprano_sum == expected_duration, (
        f"Template '{schema_name}/{metre}': soprano durations sum to "
        f"{soprano_sum}, expected {expected_duration}"
    )
    assert bass_sum == expected_duration, (
        f"Template '{schema_name}/{metre}': bass durations sum to "
        f"{bass_sum}, expected {expected_duration}"
    )
    for dur in soprano_durations:
        assert dur in VALID_DURATIONS_SET, (
            f"Template '{schema_name}/{metre}': soprano duration {dur} invalid"
        )
    for dur in bass_durations:
        assert dur in VALID_DURATIONS_SET, (
            f"Template '{schema_name}/{metre}': bass duration {dur} invalid"
        )
    for deg in soprano_degrees:
        assert 1 <= deg <= 7, (
            f"Template '{schema_name}/{metre}': soprano degree {deg} invalid"
        )
    for deg in bass_degrees:
        assert 1 <= deg <= 7, (
            f"Template '{schema_name}/{metre}': bass degree {deg} invalid"
        )
    if schema_name in ("cadenza_semplice", "cadenza_composta", "comma"):
        assert soprano_degrees[-1] == 1, (
            f"Template '{schema_name}': soprano must end on degree 1"
        )
        assert bass_degrees[-1] == 1, (
            f"Template '{schema_name}': bass must end on degree 1"
        )
    if schema_name == "half_cadence":
        assert bass_degrees[-1] == 5, (
            f"Template '{schema_name}': bass must end on degree 5"
        )


def load_cadence_templates() -> dict[tuple[str, str], CadenceTemplate]:
    """Load templates keyed by (schema_name, metre). Cached."""
    global _cache
    if _cache is not None:
        return _cache
    path: Path = DATA_DIR / "cadence_templates" / "templates.yaml"
    assert path.exists(), f"Cadence templates file not found: {path}"
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)
    result: dict[tuple[str, str], CadenceTemplate] = {}
    for schema_name, metres in raw.items():
        for metre, data in metres.items():
            bars: int = data["bars"]
            soprano_degrees: tuple[int, ...] = tuple(data["soprano"]["degrees"])
            soprano_durations: tuple[Fraction, ...] = tuple(
                _parse_fraction(s=d) for d in data["soprano"]["durations"]
            )
            bass_degrees: tuple[int, ...] = tuple(data["bass"]["degrees"])
            bass_durations: tuple[Fraction, ...] = tuple(
                _parse_fraction(s=d) for d in data["bass"]["durations"]
            )
            _validate_template(
                schema_name=schema_name,
                metre=metre,
                bars=bars,
                soprano_degrees=soprano_degrees,
                soprano_durations=soprano_durations,
                bass_degrees=bass_degrees,
                bass_durations=bass_durations,
            )
            template: CadenceTemplate = CadenceTemplate(
                schema_name=schema_name,
                metre=metre,
                bars=bars,
                soprano_degrees=soprano_degrees,
                soprano_durations=soprano_durations,
                bass_degrees=bass_degrees,
                bass_durations=bass_durations,
            )
            result[(schema_name, metre)] = template
    _cache = result
    return result


def get_schema_bars(
    schema_name: str,
    schema_def: Any,
    metre: str | None = None,
) -> int:
    """Canonical bar count for any schema. Single source of truth."""
    if schema_def.position == "cadential" and metre is not None:
        templates = load_cadence_templates()
        key = (schema_name, metre)
        assert key in templates, (
            f"No cadence template for '{schema_name}' in metre '{metre}'"
        )
        return templates[key].bars
    if schema_def.sequential:
        segments = schema_def.segments or (2,)
        return max(segments) if isinstance(segments, (list, tuple)) else segments
    return len(schema_def.soprano_degrees)


def write_cadence(
    schema_name: str,
    metre: str,
    local_key: Key,
    start_offset: Fraction,
    prev_upper_midi: int | None,
    prev_lower_midi: int | None,
    upper_range: tuple[int, int],
    lower_range: tuple[int, int],
    upper_median: int,
    lower_median: int,
) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
    """Write soprano and bass notes for a cadential schema."""
    templates: dict[tuple[str, str], CadenceTemplate] = load_cadence_templates()
    key: tuple[str, str] = (schema_name, metre)
    assert key in templates, (
        f"No cadence template for '{schema_name}' in metre '{metre}'"
    )
    template: CadenceTemplate = templates[key]
    soprano_notes: list[Note] = []
    bass_notes: list[Note] = []
    soprano_offset: Fraction = start_offset
    upper_target: int = prev_upper_midi if prev_upper_midi is not None else upper_median
    for deg, dur in zip(template.soprano_degrees, template.soprano_durations):
        midi: int = _degree_to_nearest_midi(degree=deg, key=local_key, target_midi=upper_target, midi_range=upper_range)
        soprano_notes.append(Note(
            offset=soprano_offset,
            pitch=midi,
            duration=dur,
            voice=TRACK_SOPRANO,
        ))
        soprano_offset += dur
        upper_target = midi
    bass_offset: Fraction = start_offset
    lower_target: int = prev_lower_midi if prev_lower_midi is not None else lower_median
    for deg, dur in zip(template.bass_degrees, template.bass_durations):
        # Find soprano pitch sounding at this bass offset
        soprano_ceiling: int | None = None
        for sn in soprano_notes:
            if sn.offset <= bass_offset < sn.offset + sn.duration:
                soprano_ceiling = sn.pitch
                break
        midi = _degree_to_nearest_midi(
            degree=deg,
            key=local_key,
            target_midi=lower_target,
            midi_range=lower_range,
            ceiling=soprano_ceiling,
        )
        bass_notes.append(Note(
            offset=bass_offset,
            pitch=midi,
            duration=dur,
            voice=PHRASE_VOICE_BASS,
        ))
        bass_offset += dur
        lower_target = midi
    return tuple(soprano_notes), tuple(bass_notes)
