"""Cadential voice-leading from fixed templates.

Cadential schemas use predetermined note sequences, not generation.
This guarantees correct resolution.
"""
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from builder.types import Note
from motifs.fragment_catalogue import extract_head, extract_sixteenth_cell
from motifs.fugue_loader import LoadedFugue
from motifs.head_generator import degrees_to_midi
from shared.constants import METRE_BAR_LENGTH, TRACK_BASS, TRACK_SOPRANO, VALID_DURATIONS_SET
from shared.key import Key
from shared.music_math import parse_fraction
from shared.pitch import degree_to_nearest_midi

DATA_DIR: Path = Path(__file__).parent.parent / "data"

# Breath silence after cadential arrival notes
FULL_CADENCE_BREATH: Fraction = Fraction(1, 4)   # crotchet rest
HALF_CADENCE_BREATH: Fraction = Fraction(1, 8)   # quaver rest


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
                parse_fraction(s=d) for d in data["soprano"]["durations"]
            )
            bass_degrees: tuple[int, ...] = tuple(data["bass"]["degrees"])
            bass_durations: tuple[Fraction, ...] = tuple(
                parse_fraction(s=d) for d in data["bass"]["durations"]
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
        return max(schema_def.segments)
    return len(schema_def.soprano_degrees)


def cadence_entry_degree(
    schema_name: str,
    metre: str,
    fugue: LoadedFugue | None = None,
) -> int:
    """First soprano degree (1-based) that a cadence will produce."""
    if (fugue is not None
            and schema_name == "cadenza_composta"
            and metre == "4/4"):
        return fugue.subject.degrees[0] + 1  # 0-based -> 1-based
    templates: dict[tuple[str, str], CadenceTemplate] = load_cadence_templates()
    tpl_key: tuple[str, str] = (schema_name, metre)
    assert tpl_key in templates, (
        f"No cadence template for '{schema_name}' in metre '{metre}'"
    )
    return templates[tpl_key].soprano_degrees[0]


def write_cadence(
    schema_name: str,
    metre: str,
    local_key: Key,
    start_offset: Fraction,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    upper_range: tuple[int, int],
    lower_range: tuple[int, int],
    upper_median: int,
    lower_median: int,
    is_final: bool = False,
) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
    """Write soprano and bass notes for a cadential schema."""
    prev_upper_midi: int | None = prior_upper[-1].pitch if prior_upper else None
    prev_lower_midi: int | None = prior_lower[-1].pitch if prior_lower else None
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
    # Descent guard: simulate template trajectory without range clamping.
    # If any predicted pitch falls below range floor, raise target by shortfall.
    pilot_midis: list[int] = [degree_to_nearest_midi(
        degree=template.soprano_degrees[0],
        key=local_key,
        target_midi=upper_target,
        midi_range=upper_range,
    )]
    for pilot_deg in template.soprano_degrees[1:]:
        pilot_candidates: list[int] = [
            local_key.degree_to_midi(degree=pilot_deg, octave=octave)
            for octave in range(2, 7)
        ]
        pilot_midis.append(min(
            pilot_candidates,
            key=lambda m: abs(m - pilot_midis[-1]),
        ))
    lowest_predicted: int = min(pilot_midis)
    if lowest_predicted < upper_range[0]:
        upper_target += (upper_range[0] - lowest_predicted)
    for deg, dur in zip(template.soprano_degrees, template.soprano_durations):
        midi: int = degree_to_nearest_midi(degree=deg, key=local_key, target_midi=upper_target, midi_range=upper_range)
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
        midi = degree_to_nearest_midi(
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
            voice=TRACK_BASS,
        ))
        bass_offset += dur
        lower_target = midi
    # Trim arrival notes to create breath silence between phrases
    # Final cadence: no breath — hold to bar end
    if not is_final:
        breath: Fraction = (
            HALF_CADENCE_BREATH if schema_name == "half_cadence"
            else FULL_CADENCE_BREATH
        )
        for notes in (soprano_notes, bass_notes):
            last: Note = notes[-1]
            trimmed: Fraction = last.duration - breath
            assert trimmed > Fraction(0), (
                f"Cadence '{schema_name}/{metre}': breath {breath} >= "
                f"arrival duration {last.duration}"
            )
            notes[-1] = Note(
                offset=last.offset,
                pitch=last.pitch,
                duration=trimmed,
                voice=last.voice,
            )
    return (
        tuple(replace(n, creator="cadence") for n in soprano_notes),
        tuple(replace(n, creator="cadence") for n in bass_notes),
    )


def write_thematic_cadence(
    schema_name: str,
    metre: str,
    local_key: Key,
    start_offset: Fraction,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
    upper_range: tuple[int, int],
    lower_range: tuple[int, int],
    upper_median: int,
    lower_median: int,
    fugue: LoadedFugue,
    is_final: bool = False,
) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
    """Write soprano and bass for cadenza_composta 4/4 using subject fragments.

    Bar 1: subject head gesture in soprano approach
    Bar 2 beat 1: ascending cell (sixteenth notes)
    Bar 2 beat 2: degree 2 (1-based) transition
    Bar 2 beats 3-4: degree 1 (1-based) resolution
    Bass: unchanged from template (V-pedal through approach, I on resolution)
    """
    assert metre in METRE_BAR_LENGTH, f"Unknown metre: {metre}"
    bar_length: Fraction = METRE_BAR_LENGTH[metre]
    prev_upper_midi: int | None = prior_upper[-1].pitch if prior_upper else None
    prev_lower_midi: int | None = prior_lower[-1].pitch if prior_lower else None

    # Extract fragments
    head_fragment = extract_head(fugue=fugue, bar_length=bar_length)
    cell_fragment = extract_sixteenth_cell(fugue=fugue, bar_length=bar_length)

    # Bar 1 — Subject head gesture
    # Convert head degrees (0-based) to MIDI in local key
    # Use middle C (octave 4) as reference; will be octave-shifted later
    tonic_midi: int = 60 + local_key.tonic_pc
    head_midi_pitches: tuple[int, ...] = degrees_to_midi(
        degrees=head_fragment.degrees,
        tonic_midi=tonic_midi,
        mode=fugue.subject.mode,
    )

    # Octave-shift entire head to fit within upper_range, preferring proximity to prev_upper_midi
    target_midi: int = prev_upper_midi if prev_upper_midi is not None else upper_median
    head_midpoint_idx: int = len(head_midi_pitches) // 2
    head_midpoint: int = head_midi_pitches[head_midpoint_idx]

    # Find octave shift to bring head_midpoint closest to target_midi
    shift: int = 0
    best_distance: int = abs(head_midpoint - target_midi)
    for candidate_shift in range(-48, 49, 12):
        shifted_midpoint: int = head_midpoint + candidate_shift
        if upper_range[0] <= shifted_midpoint <= upper_range[1]:
            distance: int = abs(shifted_midpoint - target_midi)
            if distance < best_distance:
                best_distance = distance
                shift = candidate_shift

    head_midi_shifted: tuple[int, ...] = tuple(p + shift for p in head_midi_pitches)

    # Descent guard: if lowest pitch below range floor, shift up by 12
    lowest_head: int = min(head_midi_shifted)
    if lowest_head < upper_range[0]:
        head_midi_shifted = tuple(p + 12 for p in head_midi_shifted)

    # Assert head fits in range
    assert all(upper_range[0] <= p <= upper_range[1] for p in head_midi_shifted), (
        f"Head MIDI pitches {head_midi_shifted} outside upper_range {upper_range}"
    )

    # Build bar 1 soprano notes with head's own durations
    soprano_notes: list[Note] = []
    offset: Fraction = start_offset
    for pitch, dur in zip(head_midi_shifted, head_fragment.durations):
        soprano_notes.append(Note(
            offset=offset,
            pitch=pitch,
            duration=dur,
            voice=TRACK_SOPRANO,
        ))
        offset += dur

    # Pad bar 1 if head duration < bar_length
    head_total_duration: Fraction = sum(head_fragment.durations)
    if head_total_duration < bar_length:
        remainder: Fraction = bar_length - head_total_duration
        last_pitch: int = head_midi_shifted[-1]
        soprano_notes.append(Note(
            offset=offset,
            pitch=last_pitch,
            duration=remainder,
            voice=TRACK_SOPRANO,
        ))
        offset += remainder

    assert offset == start_offset + bar_length, (
        f"Bar 1 soprano duration mismatch: offset={offset}, expected={start_offset + bar_length}"
    )

    # Bar 2 beat 1 — Ascending cell (4 sixteenth notes)
    # Take first 4 notes from cell (truncate if longer, repeat last degree if shorter)
    cell_degrees: list[int] = list(cell_fragment.degrees[:4])
    while len(cell_degrees) < 4:
        cell_degrees.append(cell_degrees[-1] if cell_degrees else 0)
    cell_degrees = cell_degrees[:4]

    # Transpose cell so last note lands on degree 1 (0-based, = scale degree 2 in 1-based)
    # cell_degrees[-1] + transposition = 1
    transposition: int = 1 - cell_degrees[-1]
    cell_degrees_transposed: tuple[int, ...] = tuple(deg + transposition for deg in cell_degrees)

    # Convert to MIDI
    cell_midi: tuple[int, ...] = degrees_to_midi(
        degrees=cell_degrees_transposed,
        tonic_midi=tonic_midi,
        mode=fugue.subject.mode,
    )

    # Octave-select so cell's first note is close to head's last MIDI pitch and in range
    head_last_pitch: int = soprano_notes[-1].pitch
    cell_first: int = cell_midi[0]
    cell_shift: int = 0
    best_cell_distance: int = 999
    best_all_in_range: bool = False
    for candidate_shift in range(-48, 49, 12):
        shifted: tuple[int, ...] = tuple(p + candidate_shift for p in cell_midi)
        all_in_range: bool = all(upper_range[0] <= p <= upper_range[1] for p in shifted)
        distance: int = abs(shifted[0] - head_last_pitch)
        # Prefer: all in range + close; then all in range; then close
        if all_in_range and not best_all_in_range:
            best_cell_distance = distance
            best_all_in_range = True
            cell_shift = candidate_shift
        elif all_in_range == best_all_in_range and distance < best_cell_distance:
            best_cell_distance = distance
            cell_shift = candidate_shift

    cell_midi_shifted: tuple[int, ...] = tuple(p + cell_shift for p in cell_midi)

    # Assert cell fits in range
    assert all(upper_range[0] <= p <= upper_range[1] for p in cell_midi_shifted), (
        f"Cell MIDI pitches {cell_midi_shifted} outside upper_range {upper_range}"
    )

    # Build bar 2 beat 1 notes (4 sixteenths = 1/4 bar)
    sixteenth: Fraction = Fraction(1, 16)
    for pitch in cell_midi_shifted:
        soprano_notes.append(Note(
            offset=offset,
            pitch=pitch,
            duration=sixteenth,
            voice=TRACK_SOPRANO,
        ))
        offset += sixteenth

    # Bar 2 beat 2 — Transition (degree 2 in 1-based = degree 1 in 0-based)
    # Wait, the task says "degree 2 (1-based)" which is the penultimate scale degree before tonic
    # In 1-based notation: degree 1 = tonic, degree 2 = supertonic
    # So I need degree 2 in 1-based notation
    transition_degree: int = 2  # 1-based
    cell_last_pitch: int = soprano_notes[-1].pitch
    transition_midi: int = degree_to_nearest_midi(
        degree=transition_degree,
        key=local_key,
        target_midi=cell_last_pitch,
        midi_range=upper_range,
    )
    soprano_notes.append(Note(
        offset=offset,
        pitch=transition_midi,
        duration=Fraction(1, 4),
        voice=TRACK_SOPRANO,
    ))
    offset += Fraction(1, 4)

    # Bar 2 beats 3-4 — Resolution (degree 1 in 1-based)
    resolution_degree: int = 1  # 1-based
    resolution_midi: int = degree_to_nearest_midi(
        degree=resolution_degree,
        key=local_key,
        target_midi=transition_midi,
        midi_range=upper_range,
    )
    soprano_notes.append(Note(
        offset=offset,
        pitch=resolution_midi,
        duration=Fraction(1, 2),
        voice=TRACK_SOPRANO,
    ))
    offset += Fraction(1, 2)

    # Bass: generate from template (unchanged)
    templates: dict[tuple[str, str], CadenceTemplate] = load_cadence_templates()
    template: CadenceTemplate = templates[(schema_name, metre)]

    bass_notes: list[Note] = []
    bass_offset: Fraction = start_offset
    lower_target: int = prev_lower_midi if prev_lower_midi is not None else lower_median

    for deg, dur in zip(template.bass_degrees, template.bass_durations):
        # Find soprano pitch sounding at this bass offset
        soprano_ceiling: int | None = None
        for sn in soprano_notes:
            if sn.offset <= bass_offset < sn.offset + sn.duration:
                soprano_ceiling = sn.pitch
                break

        midi: int = degree_to_nearest_midi(
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
            voice=TRACK_BASS,
        ))
        bass_offset += dur
        lower_target = midi

    # Trim arrival notes to create breath silence between phrases
    if not is_final:
        breath: Fraction = FULL_CADENCE_BREATH
        for notes in (soprano_notes, bass_notes):
            last: Note = notes[-1]
            trimmed: Fraction = last.duration - breath
            assert trimmed > Fraction(0), (
                f"Cadence '{schema_name}/{metre}': breath {breath} >= "
                f"arrival duration {last.duration}"
            )
            notes[-1] = Note(
                offset=last.offset,
                pitch=last.pitch,
                duration=trimmed,
                voice=last.voice,
            )

    return (
        tuple(replace(n, creator="cadence") for n in soprano_notes),
        tuple(replace(n, creator="cadence") for n in bass_notes),
    )
