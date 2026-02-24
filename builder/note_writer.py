"""Note file writer with analytical annotations.

Writes enriched .note CSV with degree, harmony, phrase, and cadence columns.
Piece-level constants go in ## metadata headers; per-note analysis in columns.
Harmony is derived from actual bass notes (figured-bass convention), not
from the planner's abstract harmony.
"""
from fractions import Fraction
from pathlib import Path

from builder.io import all_notes_sorted, bar_beat, note_name
from builder.phrase_types import PhrasePlan
from builder.types import Composition, Note
from shared.key import Key

MANDATORY_COLS: tuple[str, ...] = ("offset", "midinote", "duration")
OPTIONAL_COLS: tuple[str, ...] = ("track", "bar", "beat", "notename", "degree", "harmony", "phrase", "cadence")
LABELS_HEADER: str = "offset,track,bar,beat,label"

# Degree labels for all 12 pitch classes relative to tonic
# Index = semitones above tonic
DEGREE_LABELS_MAJOR: tuple[str, ...] = (
    "1", "b2", "2", "b3", "3", "4", "#4", "5", "b6", "6", "b7", "7",
)
DEGREE_LABELS_MINOR: tuple[str, ...] = (
    "1", "b2", "2", "3", "#3", "4", "#4", "5", "6", "#6", "7", "#7",
)

# Bass degree -> Roman numeral (figured-bass convention: bass defines chord)
DEGREE_ROMAN_MAJOR: dict[str, str] = {
    "1": "I", "b2": "bII", "2": "ii", "b3": "bIII", "3": "iii",
    "4": "IV", "#4": "V/V", "5": "V", "b6": "bVI", "6": "vi",
    "b7": "bVII", "7": "viio",
}
DEGREE_ROMAN_MINOR: dict[str, str] = {
    "1": "i", "b2": "bII", "2": "iio", "3": "III", "#3": "V/vi",
    "4": "iv", "#4": "V/V", "5": "V", "6": "VI", "#6": "V/iv",
    "7": "VII", "#7": "viio",
}

CADENCE_ABBREV: dict[str, str] = {
    "authentic": "PAC",
    "half": "HC",
    "imperfect": "IAC",
    "deceptive": "DC",
    "plagal": "PC",
    "phrygian": "PHR",
}


def _degree_label(key: Key, midi: int) -> str:
    """Scale degree label for a MIDI pitch relative to key."""
    pc: int = (midi - key.tonic_pc) % 12
    labels: tuple[str, ...] = DEGREE_LABELS_MAJOR if key.mode == "major" else DEGREE_LABELS_MINOR
    return labels[pc]


def _degree_to_roman(degree: str, mode: str) -> str:
    """Roman numeral for a bass scale degree."""
    table: dict[str, str] = DEGREE_ROMAN_MAJOR if mode == "major" else DEGREE_ROMAN_MINOR
    return table.get(degree, "?")


def _build_key_map(
    phrase_plans: tuple[PhrasePlan, ...],
    home_key: Key,
) -> dict[int, Key]:
    """Map bar numbers to local keys from phrase plans."""
    key_map: dict[int, Key] = {}
    for plan in phrase_plans:
        for i in range(plan.bar_span):
            key_map[plan.start_bar + i] = plan.local_key
    return key_map


def _build_phrase_map(
    phrase_plans: tuple[PhrasePlan, ...],
    home_key: Key,
) -> dict[Fraction, str]:
    """Map phrase start offsets to section labels."""
    phrase_map: dict[Fraction, str] = {}
    for plan in phrase_plans:
        label: str = plan.section_name
        if plan.local_key != home_key:
            label = f"{label} [{_key_label(key=plan.local_key)}]"
        phrase_map[plan.start_offset] = label
    return phrase_map


def _build_cadence_map(
    phrase_plans: tuple[PhrasePlan, ...],
) -> dict[int, str]:
    """Map cadential bar numbers to cadence abbreviations."""
    cadence_map: dict[int, str] = {}
    for plan in phrase_plans:
        if plan.is_cadential and plan.cadence_type:
            final_bar: int = plan.start_bar + plan.bar_span - 1
            cadence_map[final_bar] = CADENCE_ABBREV.get(plan.cadence_type, plan.cadence_type)
    return cadence_map


def _build_harmony_map(
    comp: Composition,
    key_map: dict[int, Key],
    home_key: Key,
    metre: str,
    upbeat: Fraction,
) -> dict[Fraction, str]:
    """Derive Roman numeral harmony from bass note at each onset.

    Follows figured-bass convention: each new bass note defines the
    harmony. Only writes a label when the harmony changes.
    """
    # Find the lowest pitch at each unique offset
    bass_at_offset: dict[Fraction, int] = {}
    for voice_notes in comp.voices.values():
        for note in voice_notes:
            existing: int | None = bass_at_offset.get(note.offset)
            if existing is None or note.pitch < existing:
                bass_at_offset[note.offset] = note.pitch
    harmony_map: dict[Fraction, str] = {}
    prev_roman: str = ""
    for offset in sorted(bass_at_offset.keys()):
        midi: int = bass_at_offset[offset]
        bar_num, _ = bar_beat(offset=offset, metre=metre, upbeat=upbeat)
        local_key: Key = key_map.get(bar_num, home_key)
        degree: str = _degree_label(key=local_key, midi=midi)
        roman: str = _degree_to_roman(degree=degree, mode=local_key.mode)
        if roman != prev_roman:
            harmony_map[offset] = roman
            prev_roman = roman
    return harmony_map


def _format_metadata(
    comp: Composition,
    home_key: Key,
    genre: str,
) -> list[str]:
    """Build ## metadata header lines."""
    lines: list[str] = [
        f"## key: {home_key.tonic} {home_key.mode}",
        f"## time: {comp.metre}",
        f"## genre: {genre}",
        f"## voices: {len(comp.voices)}",
    ]
    if comp.upbeat > 0:
        lines.append(f"## anacrusis: {comp.upbeat}")
    return lines


def _build_row(
    note: Note,
    bar: int,
    beat: Fraction,
    local_key: Key,
    harmony: str,
    phrase: str,
    cadence: str,
) -> dict[str, str]:
    """Build a note row as a dict of column name → value."""
    degree: str = _degree_label(key=local_key, midi=note.pitch)
    return {
        "offset": str(float(note.offset)),
        "midinote": str(note.pitch),
        "duration": str(note.duration),
        "track": str(note.voice),
        "bar": str(bar),
        "beat": str(float(beat)),
        "notename": note_name(midi=note.pitch),
        "degree": degree,
        "harmony": harmony,
        "phrase": phrase,
        "cadence": cadence,
    }


def _key_label(key: Key) -> str:
    """Compact key label: 'D' for D major, 'Dm' for D minor."""
    if key.mode == "minor":
        return f"{key.tonic}m"
    return key.tonic


def write_note_file(
    comp: Composition,
    path: Path,
    home_key: Key,
    genre: str,
    phrase_plans: tuple[PhrasePlan, ...] = (),
) -> None:
    """Write enriched .note CSV file with analytical annotations."""
    key_map: dict[int, Key] = _build_key_map(
        phrase_plans=phrase_plans,
        home_key=home_key,
    )
    phrase_map: dict[Fraction, str] = _build_phrase_map(
        phrase_plans=phrase_plans,
        home_key=home_key,
    )
    cadence_map: dict[int, str] = _build_cadence_map(phrase_plans=phrase_plans)
    harmony_map: dict[Fraction, str] = _build_harmony_map(
        comp=comp,
        key_map=key_map,
        home_key=home_key,
        metre=comp.metre,
        upbeat=comp.upbeat,
    )
    # Collect all rows as dicts so we can inspect which optional columns have data
    rows: list[dict[str, str]] = []
    seen_harmony_offsets: set[Fraction] = set()
    seen_phrase_offsets: set[Fraction] = set()
    seen_cadence_bars: set[int] = set()
    for note in all_notes_sorted(comp=comp):
        bar_num, beat_val = bar_beat(offset=note.offset, metre=comp.metre, upbeat=comp.upbeat)
        # Harmony: first note at each offset where harmony changes
        harmony: str = ""
        if note.offset not in seen_harmony_offsets and note.offset in harmony_map:
            harmony = harmony_map[note.offset]
            seen_harmony_offsets.add(note.offset)
        # Phrase: first note at phrase start offset
        phrase: str = ""
        if note.offset not in seen_phrase_offsets and note.offset in phrase_map:
            phrase = phrase_map[note.offset]
            seen_phrase_offsets.add(note.offset)
        # Cadence: first note at cadential bar
        cadence: str = ""
        if bar_num not in seen_cadence_bars and bar_num in cadence_map:
            cadence = cadence_map[bar_num]
            seen_cadence_bars.add(bar_num)
        local_key: Key = key_map.get(bar_num, home_key)
        rows.append(_build_row(
            note=note,
            bar=bar_num,
            beat=beat_val,
            local_key=local_key,
            harmony=harmony,
            phrase=phrase,
            cadence=cadence,
        ))
    # Drop optional columns that carry no data in any row
    active_optional: tuple[str, ...] = tuple(
        col for col in OPTIONAL_COLS
        if any(row[col] for row in rows)
    )
    active_cols: tuple[str, ...] = MANDATORY_COLS + active_optional
    lines: list[str] = _format_metadata(comp=comp, home_key=home_key, genre=genre)
    lines.append(",".join(active_cols))
    for row in rows:
        lines.append(",".join(row[col] for col in active_cols))
    path.write_text("\n".join(lines), encoding="utf-8")
    # Write separate .labels file for Chaz (thematic role labels)
    label_lines: list[str] = [LABELS_HEADER]
    for note in all_notes_sorted(comp=comp):
        if note.lyric:
            bar_num, beat_val = bar_beat(offset=note.offset, metre=comp.metre, upbeat=comp.upbeat)
            label_lines.append(
                f"{float(note.offset)},{note.voice},{bar_num},{float(beat_val)},{note.lyric}"
            )
    labels_path: Path = path.with_suffix(".labels")
    labels_path.write_text("\n".join(label_lines), encoding="utf-8")
