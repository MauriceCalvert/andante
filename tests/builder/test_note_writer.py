"""Comprehensive tests for builder/note_writer.py.

Tests every public and private function with hand-built fixtures.
No full pipeline execution — minimal objects only.
"""
import pytest
from fractions import Fraction
from pathlib import Path
from builder.note_writer import (
    CADENCE_ABBREV,
    DEGREE_LABELS_MAJOR,
    DEGREE_LABELS_MINOR,
    DEGREE_ROMAN_MAJOR,
    DEGREE_ROMAN_MINOR,
    HEADER,
    _build_cadence_map,
    _build_harmony_map,
    _build_key_map,
    _build_phrase_map,
    _degree_label,
    _degree_to_roman,
    _format_metadata,
    _format_row,
    _key_label,
    write_note_file,
)
from builder.phrase_types import BeatPosition, PhrasePlan
from builder.types import Composition, Note
from shared.key import Key
from shared.voice_types import Range


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

C_MAJOR: Key = Key(tonic="C", mode="major")
A_MINOR: Key = Key(tonic="A", mode="minor")
G_MAJOR: Key = Key(tonic="G", mode="major")
D_MINOR: Key = Key(tonic="D", mode="minor")
Eb_MAJOR: Key = Key(tonic="Eb", mode="major")


def _make_note(
    offset: Fraction = Fraction(0),
    pitch: int = 60,
    duration: Fraction = Fraction(1, 4),
    voice: int = 0,
) -> Note:
    """Build a minimal Note."""
    return Note(
        offset=offset,
        pitch=pitch,
        duration=duration,
        voice=voice,
    )


def _make_plan(
    schema_name: str = "do_re_mi",
    local_key: Key = C_MAJOR,
    bar_span: int = 4,
    start_bar: int = 1,
    start_offset: Fraction = Fraction(0),
    section_name: str = "A",
    is_cadential: bool = False,
    cadence_type: str | None = None,
) -> PhrasePlan:
    """Build a minimal PhrasePlan with only fields note_writer reads."""
    return PhrasePlan(
        schema_name=schema_name,
        degrees_upper=(1, 2, 3),
        degrees_lower=(1, 7, 1),
        degree_positions=(
            BeatPosition(bar=1, beat=1),
            BeatPosition(bar=2, beat=1),
            BeatPosition(bar=3, beat=1),
        ),
        local_key=local_key,
        bar_span=bar_span,
        start_bar=start_bar,
        start_offset=start_offset,
        phrase_duration=Fraction(bar_span),
        metre="4/4",
        rhythm_profile="default",
        is_cadential=is_cadential,
        cadence_type=cadence_type,
        prev_exit_upper=None,
        prev_exit_lower=None,
        section_name=section_name,
        upper_range=Range(low=60, high=84),
        lower_range=Range(low=36, high=62),
        upper_median=72,
        lower_median=48,
    )


def _make_comp(
    soprano_notes: tuple[Note, ...] = (),
    bass_notes: tuple[Note, ...] = (),
    metre: str = "4/4",
    tempo: int = 120,
    upbeat: Fraction = Fraction(0),
) -> Composition:
    """Build a minimal Composition."""
    return Composition(
        voices={"soprano": soprano_notes, "bass": bass_notes},
        metre=metre,
        tempo=tempo,
        upbeat=upbeat,
    )


# ---------------------------------------------------------------------------
# _degree_label: exhaustive major
# ---------------------------------------------------------------------------

_MAJOR_CASES: list[tuple[int, str]] = [
    (0, "1"), (1, "b2"), (2, "2"), (3, "b3"), (4, "3"), (5, "4"),
    (6, "#4"), (7, "5"), (8, "b6"), (9, "6"), (10, "b7"), (11, "7"),
]


@pytest.mark.parametrize("semitones,expected", _MAJOR_CASES)
def test_degree_label_c_major_exhaustive(semitones: int, expected: str) -> None:
    """Every pitch class in C major maps to the correct degree label."""
    midi: int = 60 + semitones  # C4 = tonic
    assert _degree_label(key=C_MAJOR, midi=midi) == expected


# ---------------------------------------------------------------------------
# _degree_label: exhaustive minor
# ---------------------------------------------------------------------------

_MINOR_CASES: list[tuple[int, str]] = [
    (0, "1"), (1, "b2"), (2, "2"), (3, "3"), (4, "#3"), (5, "4"),
    (6, "#4"), (7, "5"), (8, "6"), (9, "#6"), (10, "7"), (11, "#7"),
]


@pytest.mark.parametrize("semitones,expected", _MINOR_CASES)
def test_degree_label_a_minor_exhaustive(semitones: int, expected: str) -> None:
    """Every pitch class in A minor maps to the correct degree label."""
    midi: int = 57 + semitones  # A3 = tonic
    assert _degree_label(key=A_MINOR, midi=midi) == expected


def test_degree_label_g_major_tonic() -> None:
    """G major tonic (G4=67) labels as '1'."""
    assert _degree_label(key=G_MAJOR, midi=67) == "1"


def test_degree_label_g_major_fifth() -> None:
    """G major fifth (D5=74) labels as '5'."""
    assert _degree_label(key=G_MAJOR, midi=74) == "5"


def test_degree_label_eb_major_tonic() -> None:
    """Eb major tonic labels as '1'."""
    assert _degree_label(key=Eb_MAJOR, midi=63) == "1"


def test_degree_label_low_midi() -> None:
    """Very low MIDI (C1=24) still computes correct degree in C major."""
    assert _degree_label(key=C_MAJOR, midi=24) == "1"


def test_degree_label_high_midi() -> None:
    """Very high MIDI (C8=108) still computes correct degree in C major."""
    assert _degree_label(key=C_MAJOR, midi=108) == "1"


# ---------------------------------------------------------------------------
# _degree_to_roman: exhaustive major
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("degree,expected", list(DEGREE_ROMAN_MAJOR.items()))
def test_degree_to_roman_major_exhaustive(degree: str, expected: str) -> None:
    """Every degree in DEGREE_ROMAN_MAJOR maps correctly."""
    assert _degree_to_roman(degree=degree, mode="major") == expected


# ---------------------------------------------------------------------------
# _degree_to_roman: exhaustive minor
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("degree,expected", list(DEGREE_ROMAN_MINOR.items()))
def test_degree_to_roman_minor_exhaustive(degree: str, expected: str) -> None:
    """Every degree in DEGREE_ROMAN_MINOR maps correctly."""
    assert _degree_to_roman(degree=degree, mode="minor") == expected


def test_degree_to_roman_unknown_returns_question_mark() -> None:
    """Unknown degree string returns '?'."""
    assert _degree_to_roman(degree="##5", mode="major") == "?"
    assert _degree_to_roman(degree="##5", mode="minor") == "?"


# ---------------------------------------------------------------------------
# _key_label
# ---------------------------------------------------------------------------

def test_key_label_major() -> None:
    """Major keys return bare tonic."""
    assert _key_label(key=C_MAJOR) == "C"
    assert _key_label(key=G_MAJOR) == "G"
    assert _key_label(key=Eb_MAJOR) == "Eb"


def test_key_label_minor() -> None:
    """Minor keys return tonic + 'm'."""
    assert _key_label(key=A_MINOR) == "Am"
    assert _key_label(key=D_MINOR) == "Dm"


# ---------------------------------------------------------------------------
# _build_key_map
# ---------------------------------------------------------------------------

def test_build_key_map_single_phrase() -> None:
    """Single phrase maps all its bars to local_key."""
    plan: PhrasePlan = _make_plan(bar_span=4, start_bar=1, local_key=G_MAJOR)
    key_map: dict[int, Key] = _build_key_map(
        phrase_plans=(plan,),
        home_key=C_MAJOR,
    )
    for bar in (1, 2, 3, 4):
        assert key_map[bar] is G_MAJOR


def test_build_key_map_multiple_phrases() -> None:
    """Two phrases with different keys produce correct bar mapping."""
    plan_a: PhrasePlan = _make_plan(
        bar_span=3, start_bar=1, local_key=C_MAJOR,
    )
    plan_b: PhrasePlan = _make_plan(
        bar_span=2, start_bar=4, local_key=G_MAJOR,
        start_offset=Fraction(3),
    )
    key_map: dict[int, Key] = _build_key_map(
        phrase_plans=(plan_a, plan_b),
        home_key=C_MAJOR,
    )
    assert key_map[1] is C_MAJOR
    assert key_map[2] is C_MAJOR
    assert key_map[3] is C_MAJOR
    assert key_map[4] is G_MAJOR
    assert key_map[5] is G_MAJOR


def test_build_key_map_empty_plans() -> None:
    """Empty phrase_plans returns empty map."""
    key_map: dict[int, Key] = _build_key_map(
        phrase_plans=(),
        home_key=C_MAJOR,
    )
    assert key_map == {}


# ---------------------------------------------------------------------------
# _build_phrase_map
# ---------------------------------------------------------------------------

def test_build_phrase_map_home_key() -> None:
    """Phrase in home key: label is just section_name."""
    plan: PhrasePlan = _make_plan(
        section_name="A", local_key=C_MAJOR, start_offset=Fraction(0),
    )
    phrase_map: dict[Fraction, str] = _build_phrase_map(
        phrase_plans=(plan,),
        home_key=C_MAJOR,
    )
    assert phrase_map[Fraction(0)] == "A"


def test_build_phrase_map_foreign_key() -> None:
    """Phrase in foreign key: label includes key suffix."""
    plan: PhrasePlan = _make_plan(
        section_name="B", local_key=G_MAJOR, start_offset=Fraction(4),
    )
    phrase_map: dict[Fraction, str] = _build_phrase_map(
        phrase_plans=(plan,),
        home_key=C_MAJOR,
    )
    assert phrase_map[Fraction(4)] == "B [G]"


def test_build_phrase_map_foreign_minor_key() -> None:
    """Foreign minor key uses 'm' suffix."""
    plan: PhrasePlan = _make_plan(
        section_name="B", local_key=D_MINOR, start_offset=Fraction(4),
    )
    phrase_map: dict[Fraction, str] = _build_phrase_map(
        phrase_plans=(plan,),
        home_key=C_MAJOR,
    )
    assert phrase_map[Fraction(4)] == "B [Dm]"


def test_build_phrase_map_multiple_offsets() -> None:
    """Multiple phrases produce entries at their start offsets."""
    plan_a: PhrasePlan = _make_plan(
        section_name="A", start_offset=Fraction(0), local_key=C_MAJOR,
    )
    plan_b: PhrasePlan = _make_plan(
        section_name="B", start_offset=Fraction(4), local_key=G_MAJOR,
    )
    phrase_map: dict[Fraction, str] = _build_phrase_map(
        phrase_plans=(plan_a, plan_b),
        home_key=C_MAJOR,
    )
    assert len(phrase_map) == 2
    assert Fraction(0) in phrase_map
    assert Fraction(4) in phrase_map


# ---------------------------------------------------------------------------
# _build_cadence_map
# ---------------------------------------------------------------------------

def test_build_cadence_map_authentic() -> None:
    """Cadential phrase with 'authentic' maps to 'PAC' at final bar."""
    plan: PhrasePlan = _make_plan(
        bar_span=3, start_bar=5, is_cadential=True, cadence_type="authentic",
    )
    cadence_map: dict[int, str] = _build_cadence_map(phrase_plans=(plan,))
    assert cadence_map[7] == "PAC"  # start_bar(5) + bar_span(3) - 1 = 7


def test_build_cadence_map_half() -> None:
    """Cadential phrase with 'half' maps to 'HC'."""
    plan: PhrasePlan = _make_plan(
        bar_span=2, start_bar=1, is_cadential=True, cadence_type="half",
    )
    cadence_map: dict[int, str] = _build_cadence_map(phrase_plans=(plan,))
    assert cadence_map[2] == "HC"


def test_build_cadence_map_non_cadential() -> None:
    """Non-cadential phrase produces no entry."""
    plan: PhrasePlan = _make_plan(is_cadential=False, cadence_type=None)
    cadence_map: dict[int, str] = _build_cadence_map(phrase_plans=(plan,))
    assert len(cadence_map) == 0


def test_build_cadence_map_all_types() -> None:
    """All known cadence types produce their abbreviation."""
    for ctype, abbrev in CADENCE_ABBREV.items():
        plan: PhrasePlan = _make_plan(
            bar_span=2, start_bar=1, is_cadential=True, cadence_type=ctype,
        )
        cadence_map: dict[int, str] = _build_cadence_map(phrase_plans=(plan,))
        assert cadence_map[2] == abbrev, f"cadence_type={ctype}"


def test_build_cadence_map_unknown_type_passes_through() -> None:
    """Unknown cadence type passes through as raw string."""
    plan: PhrasePlan = _make_plan(
        bar_span=2, start_bar=1, is_cadential=True, cadence_type="exotic",
    )
    cadence_map: dict[int, str] = _build_cadence_map(phrase_plans=(plan,))
    assert cadence_map[2] == "exotic"


# ---------------------------------------------------------------------------
# _build_harmony_map
# ---------------------------------------------------------------------------

def _harmony_comp(
    bass_offsets_pitches: list[tuple[Fraction, int]],
    metre: str = "4/4",
    upbeat: Fraction = Fraction(0),
) -> Composition:
    """Build a Composition with bass notes at specified offsets."""
    bass: tuple[Note, ...] = tuple(
        _make_note(offset=off, pitch=p, voice=1)
        for off, p in bass_offsets_pitches
    )
    return _make_comp(bass_notes=bass, metre=metre, upbeat=upbeat)


def test_build_harmony_map_basic() -> None:
    """Bass C then G produces I then V."""
    comp: Composition = _harmony_comp(
        bass_offsets_pitches=[
            (Fraction(0), 48),   # C3 = degree 1 in C major
            (Fraction(1), 55),   # G3 = degree 5 in C major
        ],
    )
    key_map: dict[int, Key] = {1: C_MAJOR, 2: C_MAJOR}
    harmony: dict[Fraction, str] = _build_harmony_map(
        comp=comp,
        key_map=key_map,
        home_key=C_MAJOR,
        metre="4/4",
        upbeat=Fraction(0),
    )
    assert harmony[Fraction(0)] == "I"
    assert harmony[Fraction(1)] == "V"


def test_build_harmony_map_suppresses_repeated() -> None:
    """Same harmony on consecutive onsets writes only at first change."""
    comp: Composition = _harmony_comp(
        bass_offsets_pitches=[
            (Fraction(0), 48),       # C3 = I
            (Fraction(1, 4), 60),    # C4 = I (same harmony)
            (Fraction(1, 2), 55),    # G3 = V
        ],
    )
    key_map: dict[int, Key] = {1: C_MAJOR}
    harmony: dict[Fraction, str] = _build_harmony_map(
        comp=comp,
        key_map=key_map,
        home_key=C_MAJOR,
        metre="4/4",
        upbeat=Fraction(0),
    )
    assert Fraction(0) in harmony
    assert Fraction(1, 4) not in harmony  # suppressed — same Roman
    assert Fraction(1, 2) in harmony


def test_build_harmony_map_uses_local_key() -> None:
    """Harmony map uses local key from key_map, not home_key."""
    # D3 (MIDI 50) in G major: D is degree 5 -> V
    comp: Composition = _harmony_comp(
        bass_offsets_pitches=[(Fraction(0), 50)],
    )
    key_map: dict[int, Key] = {1: G_MAJOR}
    harmony: dict[Fraction, str] = _build_harmony_map(
        comp=comp,
        key_map=key_map,
        home_key=C_MAJOR,
        metre="4/4",
        upbeat=Fraction(0),
    )
    assert harmony[Fraction(0)] == "V"


def test_build_harmony_map_lowest_pitch_wins() -> None:
    """When soprano and bass sound together, lowest pitch defines harmony."""
    soprano: tuple[Note, ...] = (_make_note(offset=Fraction(0), pitch=72, voice=0),)  # C5
    bass: tuple[Note, ...] = (_make_note(offset=Fraction(0), pitch=55, voice=1),)     # G3
    comp: Composition = _make_comp(soprano_notes=soprano, bass_notes=bass)
    key_map: dict[int, Key] = {1: C_MAJOR}
    harmony: dict[Fraction, str] = _build_harmony_map(
        comp=comp,
        key_map=key_map,
        home_key=C_MAJOR,
        metre="4/4",
        upbeat=Fraction(0),
    )
    assert harmony[Fraction(0)] == "V"  # G in bass, not C from soprano


def test_build_harmony_map_with_upbeat() -> None:
    """Upbeat offset computes correct bar for key_map lookup."""
    # With upbeat=1/2, offset 0 is bar 0 (anacrusis)
    comp: Composition = _harmony_comp(
        bass_offsets_pitches=[(Fraction(0), 48)],
        upbeat=Fraction(1, 2),
    )
    key_map: dict[int, Key] = {0: C_MAJOR, 1: C_MAJOR}
    harmony: dict[Fraction, str] = _build_harmony_map(
        comp=comp,
        key_map=key_map,
        home_key=C_MAJOR,
        metre="4/4",
        upbeat=Fraction(1, 2),
    )
    assert Fraction(0) in harmony


# ---------------------------------------------------------------------------
# _format_metadata
# ---------------------------------------------------------------------------

def test_format_metadata_standard() -> None:
    """Standard metadata has key, time, genre, voices."""
    comp: Composition = _make_comp(metre="3/4", tempo=110)
    lines: list[str] = _format_metadata(comp=comp, home_key=C_MAJOR, genre="minuet")
    assert "## key: C major" in lines
    assert "## time: 3/4" in lines
    assert "## genre: minuet" in lines
    assert "## voices: 2" in lines


def test_format_metadata_with_upbeat() -> None:
    """Upbeat > 0 adds anacrusis line."""
    comp: Composition = _make_comp(upbeat=Fraction(1, 2))
    lines: list[str] = _format_metadata(comp=comp, home_key=G_MAJOR, genre="gavotte")
    anacrusis_lines: list[str] = [l for l in lines if "anacrusis" in l]
    assert len(anacrusis_lines) == 1
    assert "## anacrusis: 1/2" in anacrusis_lines[0]


def test_format_metadata_no_upbeat() -> None:
    """Upbeat == 0 produces no anacrusis line."""
    comp: Composition = _make_comp(upbeat=Fraction(0))
    lines: list[str] = _format_metadata(comp=comp, home_key=C_MAJOR, genre="minuet")
    assert not any("anacrusis" in l for l in lines)


# ---------------------------------------------------------------------------
# _format_row
# ---------------------------------------------------------------------------

def test_format_row_columns() -> None:
    """Row has 11 comma-separated columns."""
    note: Note = _make_note(offset=Fraction(1, 2), pitch=64, duration=Fraction(1, 4))
    row: str = _format_row(
        note=note,
        bar=1,
        beat=Fraction(3),
        local_key=C_MAJOR,
        harmony="I",
        phrase="A",
        cadence="PAC",
    )
    cols: list[str] = row.split(",")
    assert len(cols) == 11


def test_format_row_values() -> None:
    """Row values are correctly ordered and formatted."""
    note: Note = _make_note(offset=Fraction(0), pitch=60, duration=Fraction(1, 4), voice=0)
    row: str = _format_row(
        note=note,
        bar=1,
        beat=Fraction(1),
        local_key=C_MAJOR,
        harmony="I",
        phrase="A",
        cadence="",
    )
    cols: list[str] = row.split(",")
    assert cols[0] == "0.0"        # offset as float
    assert cols[1] == "60"         # midinote
    assert cols[2] == "1/4"        # duration
    assert cols[3] == "0"          # track/voice
    assert cols[4] == "1"          # bar
    assert cols[5] == "1.0"        # beat as float
    assert cols[6] == "C4"         # notename
    assert cols[7] == "1"          # degree
    assert cols[8] == "I"          # harmony
    assert cols[9] == "A"          # phrase
    assert cols[10] == ""          # cadence (empty)


def test_format_row_empty_optional_fields() -> None:
    """Empty harmony/phrase/cadence produce empty columns."""
    note: Note = _make_note(offset=Fraction(0), pitch=60)
    row: str = _format_row(
        note=note,
        bar=1,
        beat=Fraction(1),
        local_key=C_MAJOR,
        harmony="",
        phrase="",
        cadence="",
    )
    cols: list[str] = row.split(",")
    assert cols[8] == ""
    assert cols[9] == ""
    assert cols[10] == ""


# ---------------------------------------------------------------------------
# write_note_file: integration
# ---------------------------------------------------------------------------

def test_write_note_file_basic(tmp_path: Path) -> None:
    """Write and read back a basic note file."""
    soprano: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=72, voice=0),
        _make_note(offset=Fraction(1, 4), pitch=74, voice=0),
    )
    bass: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=48, voice=1),
        _make_note(offset=Fraction(1, 2), pitch=55, voice=1),
    )
    comp: Composition = _make_comp(soprano_notes=soprano, bass_notes=bass)
    plan: PhrasePlan = _make_plan(
        bar_span=2, start_bar=1, local_key=C_MAJOR, section_name="A",
    )
    out: Path = tmp_path / "test.note"
    write_note_file(
        comp=comp,
        path=out,
        home_key=C_MAJOR,
        genre="minuet",
        phrase_plans=(plan,),
    )
    text: str = out.read_text(encoding="utf-8")
    lines: list[str] = text.strip().split("\n")
    # Metadata lines
    metadata: list[str] = [l for l in lines if l.startswith("##")]
    assert len(metadata) >= 4
    # Header
    header_idx: int = next(i for i, l in enumerate(lines) if l == HEADER)
    assert header_idx == len(metadata)  # header immediately after metadata
    # Data rows: one per note (4 notes total)
    data_lines: list[str] = lines[header_idx + 1:]
    assert len(data_lines) == 4


def test_write_note_file_harmony_at_change_only(tmp_path: Path) -> None:
    """Harmony column appears only when Roman numeral changes."""
    bass: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=48, voice=1),       # C3 -> I
        _make_note(offset=Fraction(1, 4), pitch=60, voice=1),    # C4 -> I (same)
        _make_note(offset=Fraction(1, 2), pitch=55, voice=1),    # G3 -> V
    )
    comp: Composition = _make_comp(bass_notes=bass)
    plan: PhrasePlan = _make_plan(bar_span=2, start_bar=1, local_key=C_MAJOR)
    out: Path = tmp_path / "test.note"
    write_note_file(
        comp=comp,
        path=out,
        home_key=C_MAJOR,
        genre="minuet",
        phrase_plans=(plan,),
    )
    text: str = out.read_text(encoding="utf-8")
    lines: list[str] = text.strip().split("\n")
    data: list[str] = [l for l in lines if not l.startswith("##") and l != HEADER]
    harmonies: list[str] = [l.split(",")[8] for l in data]
    assert harmonies[0] == "I"
    assert harmonies[1] == ""   # suppressed
    assert harmonies[2] == "V"


def test_write_note_file_phrase_at_start_only(tmp_path: Path) -> None:
    """Phrase label appears only on first note at phrase start offset."""
    soprano: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=72, voice=0),
        _make_note(offset=Fraction(1, 4), pitch=74, voice=0),
    )
    bass: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=48, voice=1),
    )
    comp: Composition = _make_comp(soprano_notes=soprano, bass_notes=bass)
    plan: PhrasePlan = _make_plan(
        start_offset=Fraction(0), section_name="A", local_key=C_MAJOR,
    )
    out: Path = tmp_path / "test.note"
    write_note_file(
        comp=comp,
        path=out,
        home_key=C_MAJOR,
        genre="minuet",
        phrase_plans=(plan,),
    )
    text: str = out.read_text(encoding="utf-8")
    lines: list[str] = text.strip().split("\n")
    data: list[str] = [l for l in lines if not l.startswith("##") and l != HEADER]
    phrases: list[str] = [l.split(",")[9] for l in data]
    # First note at offset 0 gets the label
    assert phrases[0] == "A"
    # Second note at same offset gets empty (already seen)
    assert phrases[1] == ""
    # Third note at different offset gets empty (not phrase start)
    assert phrases[2] == ""


def test_write_note_file_cadence_once_per_bar(tmp_path: Path) -> None:
    """Cadence label appears only on first note of the cadential bar."""
    soprano: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=72, voice=0),
        _make_note(offset=Fraction(1), pitch=71, voice=0),   # bar 2
    )
    bass: tuple[Note, ...] = (
        _make_note(offset=Fraction(1), pitch=55, voice=1),    # bar 2
    )
    comp: Composition = _make_comp(soprano_notes=soprano, bass_notes=bass)
    plan: PhrasePlan = _make_plan(
        bar_span=2, start_bar=1, is_cadential=True, cadence_type="authentic",
    )
    out: Path = tmp_path / "test.note"
    write_note_file(
        comp=comp,
        path=out,
        home_key=C_MAJOR,
        genre="minuet",
        phrase_plans=(plan,),
    )
    text: str = out.read_text(encoding="utf-8")
    lines: list[str] = text.strip().split("\n")
    data: list[str] = [l for l in lines if not l.startswith("##") and l != HEADER]
    cadences: list[str] = [l.split(",")[10] for l in data]
    # Bar 1 notes: no cadence
    assert cadences[0] == ""
    # Bar 2 first note: cadence label
    pac_count: int = sum(1 for c in cadences if c == "PAC")
    assert pac_count == 1


def test_write_note_file_empty_phrase_plans(tmp_path: Path) -> None:
    """Empty phrase_plans: harmony derived from home_key, no phrase/cadence labels."""
    soprano: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=60, voice=0),
    )
    comp: Composition = _make_comp(soprano_notes=soprano)
    out: Path = tmp_path / "test.note"
    write_note_file(
        comp=comp,
        path=out,
        home_key=C_MAJOR,
        genre="minuet",
        phrase_plans=(),
    )
    text: str = out.read_text(encoding="utf-8")
    lines: list[str] = text.strip().split("\n")
    data: list[str] = [l for l in lines if not l.startswith("##") and l != HEADER]
    assert len(data) == 1
    cols: list[str] = data[0].split(",")
    assert cols[8] == "I"  # harmony still derived from home_key
    assert cols[9] == ""   # no phrase
    assert cols[10] == ""  # no cadence


def test_write_note_file_with_upbeat(tmp_path: Path) -> None:
    """Upbeat composition includes anacrusis in metadata."""
    bass: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=48, voice=1),
    )
    comp: Composition = _make_comp(bass_notes=bass, upbeat=Fraction(1, 2))
    out: Path = tmp_path / "test.note"
    write_note_file(
        comp=comp,
        path=out,
        home_key=G_MAJOR,
        genre="gavotte",
        phrase_plans=(),
    )
    text: str = out.read_text(encoding="utf-8")
    assert "## anacrusis: 1/2" in text


def test_write_note_file_notes_sorted_by_offset_then_pitch_desc(tmp_path: Path) -> None:
    """Notes are sorted by offset ascending, then MIDI descending."""
    soprano: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=72, voice=0),
    )
    bass: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=48, voice=1),
    )
    comp: Composition = _make_comp(soprano_notes=soprano, bass_notes=bass)
    out: Path = tmp_path / "test.note"
    write_note_file(
        comp=comp,
        path=out,
        home_key=C_MAJOR,
        genre="minuet",
        phrase_plans=(),
    )
    text: str = out.read_text(encoding="utf-8")
    lines: list[str] = text.strip().split("\n")
    data: list[str] = [l for l in lines if not l.startswith("##") and l != HEADER]
    pitches: list[int] = [int(l.split(",")[1]) for l in data]
    assert pitches == [72, 48]  # soprano (higher) first at same offset


def test_write_note_file_multiple_phrases_different_keys(tmp_path: Path) -> None:
    """Two phrases in different keys: degree column reflects local key."""
    soprano: tuple[Note, ...] = (
        _make_note(offset=Fraction(0), pitch=67, voice=0),    # G4
        _make_note(offset=Fraction(4), pitch=67, voice=0),    # G4
    )
    comp: Composition = _make_comp(soprano_notes=soprano)
    plan_a: PhrasePlan = _make_plan(
        bar_span=4, start_bar=1, local_key=C_MAJOR,
        start_offset=Fraction(0), section_name="A",
    )
    plan_b: PhrasePlan = _make_plan(
        bar_span=4, start_bar=5, local_key=G_MAJOR,
        start_offset=Fraction(4), section_name="B",
    )
    out: Path = tmp_path / "test.note"
    write_note_file(
        comp=comp,
        path=out,
        home_key=C_MAJOR,
        genre="minuet",
        phrase_plans=(plan_a, plan_b),
    )
    text: str = out.read_text(encoding="utf-8")
    lines: list[str] = text.strip().split("\n")
    data: list[str] = [l for l in lines if not l.startswith("##") and l != HEADER]
    # G4 in C major = degree 5; G4 in G major = degree 1
    degrees: list[str] = [l.split(",")[7] for l in data]
    assert degrees[0] == "5"
    assert degrees[1] == "1"


# ---------------------------------------------------------------------------
# Table completeness checks
# ---------------------------------------------------------------------------

def test_degree_labels_major_has_12_entries() -> None:
    """DEGREE_LABELS_MAJOR covers all 12 pitch classes."""
    assert len(DEGREE_LABELS_MAJOR) == 12


def test_degree_labels_minor_has_12_entries() -> None:
    """DEGREE_LABELS_MINOR covers all 12 pitch classes."""
    assert len(DEGREE_LABELS_MINOR) == 12


def test_degree_roman_major_has_12_entries() -> None:
    """DEGREE_ROMAN_MAJOR covers all 12 degree labels."""
    assert len(DEGREE_ROMAN_MAJOR) == 12


def test_degree_roman_minor_has_12_entries() -> None:
    """DEGREE_ROMAN_MINOR covers all 12 degree labels."""
    assert len(DEGREE_ROMAN_MINOR) == 12


def test_roman_major_keys_match_degree_labels() -> None:
    """Every key in DEGREE_ROMAN_MAJOR is a valid major degree label."""
    for key in DEGREE_ROMAN_MAJOR:
        assert key in DEGREE_LABELS_MAJOR


def test_roman_minor_keys_match_degree_labels() -> None:
    """Every key in DEGREE_ROMAN_MINOR is a valid minor degree label."""
    for key in DEGREE_ROMAN_MINOR:
        assert key in DEGREE_LABELS_MINOR


def test_header_has_11_columns() -> None:
    """HEADER constant has exactly 11 comma-separated column names."""
    assert len(HEADER.split(",")) == 11
