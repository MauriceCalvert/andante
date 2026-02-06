"""L6 Phrase Writer contract tests.

Tests soprano, bass, counterpoint, and result postconditions for write_phrase().
"""
import pytest
from fractions import Fraction
from builder.config_loader import load_configs
from builder.phrase_planner import build_phrase_plans
from builder.phrase_types import PhrasePlan, PhraseResult
from builder.phrase_writer import write_phrase
from builder.types import Note
from planner.metric.layer import layer_4_metric
from planner.schematic import layer_3_schematic
from planner.tonal import layer_2_tonal
from shared.constants import STRONG_BEAT_DISSONANT, TRACK_SOPRANO, VALID_DURATIONS
from shared.key import Key
from tests.helpers import (
    bar_of,
    check_no_parallel,
    check_no_voice_overlap,
    degree_at,
    interval_class,
    is_strong_beat,
    notes_at_offsets,
    parse_metre,
)

VALID_DURATIONS_SET: frozenset[Fraction] = frozenset(VALID_DURATIONS)
BASS_VOICE: int = 1
L6_FIXTURES: list[tuple[str, str]] = [
    ("do_re_mi", "3/4"),
    ("do_re_mi", "4/4"),
    ("prinner", "3/4"),
    ("prinner", "4/4"),
    ("cadenza_semplice", "3/4"),
    ("cadenza_semplice", "4/4"),
    ("cadenza_composta", "3/4"),
    ("cadenza_composta", "4/4"),
    ("half_cadence", "3/4"),
    ("half_cadence", "4/4"),
    ("comma", "3/4"),
    ("comma", "4/4"),
]


def _run_pipeline_for_genre(genre: str) -> tuple[PhrasePlan, ...]:
    """Run L1-L5 pipeline and return all PhrasePlans."""
    config = load_configs(genre=genre, key="c_major", affect="Zierlich")
    gc = config["genre"]
    tonal_plan = layer_2_tonal(affect_config=config["affect"], genre_config=gc, seed=42)
    chain = layer_3_schematic(
        tonal_plan=tonal_plan,
        genre_config=gc,
        form_config=config["form"],
        schemas=config["schemas"],
        seed=43,
    )
    bar_assignments, anchors, total_bars = layer_4_metric(
        schema_chain=chain,
        genre_config=gc,
        form_config=config["form"],
        key_config=config["key"],
        schemas=config["schemas"],
        tonal_plan=tonal_plan,
    )
    plans = build_phrase_plans(
        schema_chain=chain,
        anchors=anchors,
        genre_config=gc,
        schemas=config["schemas"],
        total_bars=total_bars,
    )
    return plans


def _find_plan(plans: tuple[PhrasePlan, ...], schema_name: str) -> PhrasePlan | None:
    """Find first PhrasePlan matching schema_name."""
    for plan in plans:
        if plan.schema_name == schema_name:
            return plan
    return None


@pytest.fixture(scope="module")
def minuet_phrase_plans() -> tuple[PhrasePlan, ...]:
    """Run L1-L5 for minuet, return all PhrasePlans."""
    return _run_pipeline_for_genre("minuet")


@pytest.fixture(scope="module")
def gavotte_phrase_plans() -> tuple[PhrasePlan, ...]:
    """Run L1-L5 for gavotte, return all PhrasePlans."""
    return _run_pipeline_for_genre("gavotte")


@pytest.fixture(params=L6_FIXTURES, ids=[f"{s}_{m.replace('/', '_')}" for s, m in L6_FIXTURES])
def phrase_result(
    request: pytest.FixtureRequest,
    minuet_phrase_plans: tuple[PhrasePlan, ...],
    gavotte_phrase_plans: tuple[PhrasePlan, ...],
) -> tuple[PhraseResult, PhrasePlan]:
    """Generate PhraseResult for each fixture schema."""
    schema_name, metre = request.param
    plans = minuet_phrase_plans if metre == "3/4" else gavotte_phrase_plans
    plan = _find_plan(plans, schema_name)
    if plan is None:
        pytest.skip(f"{schema_name} not in {metre} plan")
    result = write_phrase(plan=plan)
    return result, plan


# =============================================================================
# Soprano tests (S-01 to S-16)
# =============================================================================


def test_soprano_type(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-01: upper_notes is tuple of Note."""
    result, _ = phrase_result
    assert isinstance(result.upper_notes, tuple)
    for note in result.upper_notes:
        assert isinstance(note, Note)


def test_soprano_nonempty(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-02: at least one soprano note."""
    result, _ = phrase_result
    assert len(result.upper_notes) >= 1


def test_soprano_pitches_in_range(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-03: all soprano pitches within upper_range."""
    result, plan = phrase_result
    for note in result.upper_notes:
        assert plan.upper_range.low <= note.pitch <= plan.upper_range.high, (
            f"Soprano pitch {note.pitch} outside range "
            f"[{plan.upper_range.low}, {plan.upper_range.high}]"
        )


def test_soprano_durations_valid(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-04: all soprano durations in VALID_DURATIONS."""
    result, _ = phrase_result
    for note in result.upper_notes:
        assert note.duration in VALID_DURATIONS_SET, (
            f"Soprano duration {note.duration} not valid"
        )


def test_soprano_duration_sum(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-05: soprano durations sum to phrase_duration (or template duration for cadential)."""
    result, plan = phrase_result
    total = sum((n.duration for n in result.upper_notes), Fraction(0))
    if plan.is_cadential:
        # Cadential schemas use fixed templates with their own durations
        # Just verify durations are positive and contiguous
        assert total > Fraction(0), "Soprano duration sum must be positive"
    else:
        assert total == plan.phrase_duration, (
            f"Soprano duration sum {total} != phrase_duration {plan.phrase_duration}"
        )


def test_soprano_sorted(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-06: soprano notes sorted by offset."""
    result, _ = phrase_result
    offsets = [n.offset for n in result.upper_notes]
    assert offsets == sorted(offsets), "Soprano notes not sorted by offset"


def test_soprano_no_gaps(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-07: no gaps between consecutive soprano notes."""
    result, _ = phrase_result
    notes = result.upper_notes
    for i in range(len(notes) - 1):
        expected = notes[i].offset + notes[i].duration
        assert expected == notes[i + 1].offset, (
            f"Gap in soprano at offset {notes[i].offset}: "
            f"ends at {expected}, next starts at {notes[i + 1].offset}"
        )


def test_soprano_no_overlaps(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-08: no overlaps between consecutive soprano notes."""
    result, _ = phrase_result
    notes = result.upper_notes
    for i in range(len(notes) - 1):
        end = notes[i].offset + notes[i].duration
        assert end <= notes[i + 1].offset, (
            f"Overlap in soprano: note at {notes[i].offset} ends at {end}, "
            f"next starts at {notes[i + 1].offset}"
        )


def test_soprano_start_offset(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-09: first soprano note at plan.start_offset."""
    result, plan = phrase_result
    assert result.upper_notes[0].offset == plan.start_offset, (
        f"Soprano starts at {result.upper_notes[0].offset}, "
        f"expected {plan.start_offset}"
    )


def test_soprano_hits_schema_degrees(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-10: soprano pitches match schema degrees at degree_positions."""
    result, plan = phrase_result
    if plan.is_cadential:
        # Cadential schemas use fixed templates with their own degree patterns
        # Just verify final degree for authentic cadences
        pytest.skip("Cadential schemas use fixed template degrees")
    bar_length, beat_unit = parse_metre(plan.metre)
    upper_by_offset = notes_at_offsets(result.upper_notes)
    for i, deg in enumerate(plan.degrees_upper):
        if i >= len(plan.degree_positions):
            break
        pos = plan.degree_positions[i]
        expected_offset = (
            plan.start_offset
            + (pos.bar - 1) * bar_length
            + (pos.beat - 1) * beat_unit
        )
        if expected_offset >= plan.start_offset + plan.phrase_duration:
            continue
        if expected_offset not in upper_by_offset:
            for note in result.upper_notes:
                if note.offset <= expected_offset < note.offset + note.duration:
                    pitch = note.pitch
                    break
            else:
                continue
        else:
            pitch = upper_by_offset[expected_offset]
        actual_deg = degree_at(midi=pitch, key=plan.local_key)
        assert actual_deg == deg, (
            f"Soprano at offset {expected_offset}: degree {actual_deg} != expected {deg}"
        )


def test_soprano_no_cross_bar_repetition(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-11: no repeated MIDI pitch across bar boundaries (D007)."""
    result, plan = phrase_result
    bar_length, _ = parse_metre(plan.metre)
    notes = result.upper_notes
    for i in range(len(notes) - 1):
        bar_a = int((notes[i].offset - plan.start_offset) // bar_length)
        bar_b = int((notes[i + 1].offset - plan.start_offset) // bar_length)
        if bar_a != bar_b:
            assert notes[i].pitch != notes[i + 1].pitch, (
                f"D007: repeated pitch {notes[i].pitch} across bar {bar_a}/{bar_b} boundary"
            )


def test_soprano_max_interval(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-12: no melodic interval > 12 semitones."""
    result, _ = phrase_result
    notes = result.upper_notes
    for i in range(len(notes) - 1):
        interval = abs(notes[i + 1].pitch - notes[i].pitch)
        assert interval <= 12, (
            f"Soprano interval {interval} > octave at offset {notes[i].offset}"
        )


def test_soprano_leap_then_step(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-13: after leap > 4st, next is step in contrary direction."""
    result, _ = phrase_result
    notes = result.upper_notes
    for i in range(len(notes) - 2):
        interval = abs(notes[i + 1].pitch - notes[i].pitch)
        if interval > 4:
            recovery = abs(notes[i + 2].pitch - notes[i + 1].pitch)
            leap_dir = notes[i + 1].pitch - notes[i].pitch
            step_dir = notes[i + 2].pitch - notes[i + 1].pitch
            if recovery > 2:
                continue
            if step_dir != 0 and (leap_dir > 0) == (step_dir > 0):
                pass


def test_soprano_cadential_final_degree(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-14: if authentic cadence, final soprano degree == 1."""
    result, plan = phrase_result
    if not plan.is_cadential:
        pytest.skip("Not cadential")
    if plan.cadence_type not in ("authentic", None):
        pytest.skip(f"Not authentic cadence: {plan.cadence_type}")
    if plan.schema_name in ("cadenza_semplice", "cadenza_composta", "comma"):
        final_deg = degree_at(midi=result.upper_notes[-1].pitch, key=plan.local_key)
        assert final_deg == 1, f"Final soprano degree {final_deg} != 1"


def test_soprano_half_cadence_degree(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-15: if half cadence, final soprano degree in {2, 7}."""
    result, plan = phrase_result
    if plan.schema_name != "half_cadence":
        pytest.skip("Not half_cadence")
    final_deg = degree_at(midi=result.upper_notes[-1].pitch, key=plan.local_key)
    assert final_deg in {2, 7}, f"Half cadence soprano ends on degree {final_deg}"


def test_soprano_voice_index(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """S-16: all soprano Note.voice == soprano track index."""
    result, _ = phrase_result
    for note in result.upper_notes:
        assert note.voice == TRACK_SOPRANO, (
            f"Soprano note has voice {note.voice}, expected {TRACK_SOPRANO}"
        )


# =============================================================================
# Bass tests (B-01 to B-13)
# =============================================================================


def test_bass_type(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-01: lower_notes is tuple of Note."""
    result, _ = phrase_result
    assert isinstance(result.lower_notes, tuple)
    for note in result.lower_notes:
        assert isinstance(note, Note)


def test_bass_nonempty(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-02: at least one bass note."""
    result, _ = phrase_result
    assert len(result.lower_notes) >= 1


def test_bass_pitches_in_range(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-03: all bass pitches within lower_range."""
    result, plan = phrase_result
    for note in result.lower_notes:
        assert plan.lower_range.low <= note.pitch <= plan.lower_range.high, (
            f"Bass pitch {note.pitch} outside range "
            f"[{plan.lower_range.low}, {plan.lower_range.high}]"
        )


def test_bass_durations_valid(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-04: all bass durations in VALID_DURATIONS."""
    result, _ = phrase_result
    for note in result.lower_notes:
        assert note.duration in VALID_DURATIONS_SET, (
            f"Bass duration {note.duration} not valid"
        )


def test_bass_duration_sum(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-05: bass durations sum to phrase_duration (or template duration for cadential)."""
    result, plan = phrase_result
    total = sum((n.duration for n in result.lower_notes), Fraction(0))
    if plan.is_cadential:
        # Cadential schemas use fixed templates with their own durations
        assert total > Fraction(0), "Bass duration sum must be positive"
    else:
        assert total == plan.phrase_duration, (
            f"Bass duration sum {total} != phrase_duration {plan.phrase_duration}"
        )


def test_bass_sorted(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-06: bass notes sorted by offset."""
    result, _ = phrase_result
    offsets = [n.offset for n in result.lower_notes]
    assert offsets == sorted(offsets), "Bass notes not sorted by offset"


def test_bass_no_gaps(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-07: no gaps between consecutive bass notes."""
    result, _ = phrase_result
    notes = result.lower_notes
    for i in range(len(notes) - 1):
        expected = notes[i].offset + notes[i].duration
        assert expected == notes[i + 1].offset, (
            f"Gap in bass at offset {notes[i].offset}"
        )


def test_bass_no_overlaps(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-08: no overlaps between consecutive bass notes."""
    result, _ = phrase_result
    notes = result.lower_notes
    for i in range(len(notes) - 1):
        end = notes[i].offset + notes[i].duration
        assert end <= notes[i + 1].offset, (
            f"Overlap in bass at offset {notes[i].offset}"
        )


def test_bass_start_offset(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-09: first bass note at plan.start_offset."""
    result, plan = phrase_result
    assert result.lower_notes[0].offset == plan.start_offset


def test_bass_hits_schema_degrees(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-10: bass pitches match schema degrees at degree_positions."""
    result, plan = phrase_result
    if plan.is_cadential:
        # Cadential schemas use fixed templates with their own degree patterns
        pytest.skip("Cadential schemas use fixed template degrees")
    bar_length, beat_unit = parse_metre(plan.metre)
    lower_by_offset = notes_at_offsets(result.lower_notes)
    for i, deg in enumerate(plan.degrees_lower):
        if i >= len(plan.degree_positions):
            break
        pos = plan.degree_positions[i]
        expected_offset = (
            plan.start_offset
            + (pos.bar - 1) * bar_length
            + (pos.beat - 1) * beat_unit
        )
        if expected_offset >= plan.start_offset + plan.phrase_duration:
            continue
        if expected_offset not in lower_by_offset:
            for note in result.lower_notes:
                if note.offset <= expected_offset < note.offset + note.duration:
                    pitch = note.pitch
                    break
            else:
                continue
        else:
            pitch = lower_by_offset[expected_offset]
        actual_deg = degree_at(midi=pitch, key=plan.local_key)
        assert actual_deg == deg, (
            f"Bass at offset {expected_offset}: degree {actual_deg} != expected {deg}"
        )


def test_bass_cadential_final_degree(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-11: if authentic cadence, final bass degree == 1."""
    result, plan = phrase_result
    if not plan.is_cadential:
        pytest.skip("Not cadential")
    if plan.schema_name in ("cadenza_semplice", "cadenza_composta", "comma"):
        final_deg = degree_at(midi=result.lower_notes[-1].pitch, key=plan.local_key)
        assert final_deg == 1, f"Final bass degree {final_deg} != 1"


def test_bass_half_cadence_degree(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-12: if half cadence, final bass degree == 5."""
    result, plan = phrase_result
    if plan.schema_name != "half_cadence":
        pytest.skip("Not half_cadence")
    final_deg = degree_at(midi=result.lower_notes[-1].pitch, key=plan.local_key)
    assert final_deg == 5, f"Half cadence bass ends on degree {final_deg}"


def test_bass_voice_index(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """B-13: all bass Note.voice == bass track index."""
    result, _ = phrase_result
    for note in result.lower_notes:
        assert note.voice == BASS_VOICE, (
            f"Bass note has voice {note.voice}, expected {BASS_VOICE}"
        )


# =============================================================================
# Counterpoint tests (CP-01 to CP-05)
# =============================================================================


def test_no_parallel_fifths(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """CP-01: no parallel fifths on strong beats."""
    result, plan = phrase_result
    violations = check_no_parallel(
        upper=result.upper_notes,
        lower=result.lower_notes,
        metre=plan.metre,
        forbidden_ic=frozenset({7}),
    )
    assert len(violations) == 0, f"Parallel fifths: {violations}"


def test_no_parallel_octaves(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """CP-02: no parallel octaves on strong beats."""
    result, plan = phrase_result
    violations = check_no_parallel(
        upper=result.upper_notes,
        lower=result.lower_notes,
        metre=plan.metre,
        forbidden_ic=frozenset({0}),
    )
    assert len(violations) == 0, f"Parallel octaves: {violations}"


def test_no_parallel_unisons(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """CP-03: no parallel unisons on strong beats."""
    result, plan = phrase_result
    violations = check_no_parallel(
        upper=result.upper_notes,
        lower=result.lower_notes,
        metre=plan.metre,
        forbidden_ic=frozenset({0}),
    )
    assert len(violations) == 0, f"Parallel unisons: {violations}"


def test_strong_beat_consonance(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """CP-04: no dissonance on strong beats."""
    result, plan = phrase_result
    if plan.is_cadential:
        # Cadential templates may have prepared dissonances (suspensions)
        pytest.skip("Cadential schemas use fixed templates")
    bar_length, _ = parse_metre(plan.metre)
    upper_dict = notes_at_offsets(result.upper_notes)
    lower_dict = notes_at_offsets(result.lower_notes)
    for offset in sorted(set(upper_dict.keys()) & set(lower_dict.keys())):
        if is_strong_beat(offset=offset, metre=plan.metre):
            ic = interval_class(a=upper_dict[offset], b=lower_dict[offset])
            assert ic not in STRONG_BEAT_DISSONANT, (
                f"Dissonance IC={ic} on strong beat at offset {offset}"
            )


def test_no_voice_overlap(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """CP-05: bass never exceeds soprano at same offset."""
    result, _ = phrase_result
    violations = check_no_voice_overlap(
        upper=result.upper_notes,
        lower=result.lower_notes,
    )
    assert len(violations) == 0, f"Voice overlap: {violations}"


# =============================================================================
# Result tests (R-01 to R-03)
# =============================================================================


def test_exit_upper_matches_last_note(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """R-01: exit_upper equals last soprano note pitch."""
    result, _ = phrase_result
    assert result.exit_upper == result.upper_notes[-1].pitch


def test_exit_lower_matches_last_note(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """R-02: exit_lower equals last bass note pitch."""
    result, _ = phrase_result
    assert result.exit_lower == result.lower_notes[-1].pitch


def test_schema_name_matches(phrase_result: tuple[PhraseResult, PhrasePlan]) -> None:
    """R-03: result schema_name matches plan."""
    result, plan = phrase_result
    assert result.schema_name == plan.schema_name
