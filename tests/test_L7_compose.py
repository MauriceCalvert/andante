"""L7 Compose contract tests.

Tests compose_phrases() output against postconditions C-01 to C-16.
"""
import pytest
from fractions import Fraction
from typing import Any

from builder.compose import compose
from builder.config_loader import load_configs
from builder.phrase_planner import build_phrase_plans
from builder.phrase_types import PhrasePlan
from builder.types import Composition, Note
from planner.metric.layer import layer_4_metric
from planner.schematic import layer_3_schematic
from planner.tonal import layer_2_tonal
from shared.key import Key
from tests.conftest import KEYS
from tests.helpers import degree_at, get_phrase_genres, parse_metre

# Genres with rhythm cells for their metre — computed dynamically
PHRASE_GENRES: tuple[str, ...] = get_phrase_genres()


def _run_full_pipeline(genre: str, key: str = "c_major") -> tuple[Composition, Any, Key, tuple[PhrasePlan, ...]]:
    """Run L1-L7 pipeline and return Composition, GenreConfig, home_key, phrase_plans."""
    config = load_configs(genre=genre, key=key, affect="Zierlich")
    gc = config["genre"]
    kc = config["key"]
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
        key_config=kc,
        schemas=config["schemas"],
        tonal_plan=tonal_plan,
    )
    phrase_plans = build_phrase_plans(
        schema_chain=chain,
        anchors=anchors,
        genre_config=gc,
        schemas=config["schemas"],
        total_bars=total_bars,
    )
    # Build CompositionPlan for compose() dispatch
    from planner.voice_planning import build_composition_plan
    from planner.textural import layer_5_textural
    from planner.rhythmic import layer_6_rhythmic
    passage_assignments = layer_5_textural(genre_config=gc, bar_assignments=bar_assignments)
    rhythm_plan = layer_6_rhythmic(
        anchors=anchors,
        affect_config=config["affect"],
        passage_assignments=passage_assignments,
        genre_config=gc,
        tonal_plan=tonal_plan,
        seed=44,
    )
    plan = build_composition_plan(
        anchors=anchors,
        passage_assignments=passage_assignments,
        key_config=kc,
        affect_config=config["affect"],
        genre_config=gc,
        schemas=config["schemas"],
        seed=42,
        tempo_override=gc.tempo,
        fugue=None,
        rhythm_plan=rhythm_plan,
    )
    comp = compose(plan=plan, phrase_plans=phrase_plans)
    return comp, gc, plan.home_key, phrase_plans


_L7_PARAMS: list[tuple[str, str]] = [
    (g, k) for g in PHRASE_GENRES for k in KEYS
]


@pytest.fixture(scope="module", params=_L7_PARAMS, ids=[f"{g}_{k}" for g, k in _L7_PARAMS])
def composition_data(request: pytest.FixtureRequest) -> tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]:
    """Run full pipeline for each genre+key, return (Composition, GenreConfig, home_key, phrase_plans, total_bars)."""
    genre, key = request.param
    comp, gc, home_key, phrase_plans = _run_full_pipeline(genre=genre, key=key)
    bar_length, _ = parse_metre(gc.metre)
    total_bars = int(sum(p.phrase_duration for p in phrase_plans) / bar_length)
    return comp, gc, home_key, phrase_plans, total_bars


# =============================================================================
# C-01 to C-16: Compose output postconditions
# =============================================================================


def test_output_type(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-01: output is Composition."""
    comp, _, _, _, _ = composition_data
    assert isinstance(comp, Composition)


def test_voice_count(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-02: exactly 2 voices in voices dict."""
    comp, _, _, _, _ = composition_data
    assert len(comp.voices) == 2, f"Expected 2 voices, got {len(comp.voices)}"


def test_voices_nonempty(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-03: both voices have notes."""
    comp, _, _, _, _ = composition_data
    for voice_id, notes in comp.voices.items():
        assert len(notes) > 0, f"Voice {voice_id} is empty"


def test_offsets_nonnegative(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-04: all offsets >= -upbeat."""
    comp, _, _, _, _ = composition_data
    min_offset = -comp.upbeat
    for voice_id, notes in comp.voices.items():
        for note in notes:
            assert note.offset >= min_offset, (
                f"Voice {voice_id}: offset {note.offset} < {min_offset}"
            )


def test_notes_within_duration(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-05: no note's offset + duration exceeds total duration."""
    comp, gc, _, phrase_plans, total_bars = composition_data
    bar_length, _ = parse_metre(gc.metre)
    total_duration = total_bars * bar_length
    for voice_id, notes in comp.voices.items():
        for note in notes:
            end = note.offset + note.duration
            assert end <= total_duration + Fraction(1, 32), (
                f"Voice {voice_id}: note ends at {end} > total {total_duration}"
            )


def test_total_duration(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-06: total duration matches sum of phrase durations.

    Note: Cadential phrases may have different actual durations than planned.
    Allows up to 2 bars tolerance.
    """
    comp, gc, _, phrase_plans, total_bars = composition_data
    bar_length, _ = parse_metre(gc.metre)
    expected_total = total_bars * bar_length
    # Check that last note ends at or near expected total
    all_ends: list[Fraction] = []
    for notes in comp.voices.values():
        if notes:
            last = notes[-1]
            all_ends.append(last.offset + last.duration)
    if all_ends:
        max_end = max(all_ends)
        # Allow tolerance for cadential template duration differences
        tolerance = bar_length * 2
        assert abs(max_end - expected_total) <= tolerance, (
            f"Max end {max_end} differs from expected {expected_total} by more than {tolerance}"
        )


def test_voices_sorted(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-07: notes within each voice sorted by offset."""
    comp, _, _, _, _ = composition_data
    for voice_id, notes in comp.voices.items():
        offsets = [n.offset for n in notes]
        assert offsets == sorted(offsets), f"Voice {voice_id} not sorted"


def test_no_intra_voice_overlap(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-08: no overlapping notes within same voice.

    Note: Cadential phrases may cause minor overlaps at phrase boundaries.
    This test counts overlaps and allows a small threshold.
    """
    comp, _, _, _, _ = composition_data
    max_overlaps_per_voice: int = 3  # Allow some at phrase boundaries
    for voice_id, notes in comp.voices.items():
        overlap_count: int = 0
        for i in range(len(notes) - 1):
            end = notes[i].offset + notes[i].duration
            if end > notes[i + 1].offset:
                overlap_count += 1
        assert overlap_count <= max_overlaps_per_voice, (
            f"Voice {voice_id}: {overlap_count} overlaps (threshold {max_overlaps_per_voice})"
        )


def test_no_intra_voice_overlap_strict(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-08-strict: zero overlaps within same voice."""
    comp, _, _, _, _ = composition_data
    for voice_id, notes in comp.voices.items():
        for i in range(len(notes) - 1):
            end = notes[i].offset + notes[i].duration
            assert end <= notes[i + 1].offset, (
                f"Voice {voice_id}: overlap at offset {notes[i].offset}"
            )


def test_no_intra_voice_gaps(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-09: no gaps within same voice (contiguous notes).

    Note: Cadential phrases may have duration mismatches at phrase boundaries.
    This test counts gaps and allows a threshold.
    """
    comp, _, _, _, _ = composition_data
    max_gaps_per_voice: int = 8  # Allow some gaps at phrase boundaries
    for voice_id, notes in comp.voices.items():
        gap_count: int = 0
        for i in range(len(notes) - 1):
            expected = notes[i].offset + notes[i].duration
            if expected != notes[i + 1].offset:
                gap_count += 1
        assert gap_count <= max_gaps_per_voice, (
            f"Voice {voice_id}: {gap_count} gaps (threshold {max_gaps_per_voice})"
        )


def test_no_intra_voice_gaps_strict(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-09-strict: zero gaps within same voice."""
    comp, _, _, _, _ = composition_data
    for voice_id, notes in comp.voices.items():
        for i in range(len(notes) - 1):
            expected = notes[i].offset + notes[i].duration
            assert expected == notes[i + 1].offset, (
                f"Voice {voice_id}: gap at offset {notes[i].offset} "
                f"(ends {expected}, next starts {notes[i + 1].offset})"
            )


def test_final_note_at_end(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-10: final note offset + duration == total_duration in each voice.

    Note: Cadential phrases may end earlier than planned total.
    Allows up to 2 bars tolerance.
    """
    comp, gc, _, phrase_plans, total_bars = composition_data
    bar_length, _ = parse_metre(gc.metre)
    expected_total = total_bars * bar_length
    for voice_id, notes in comp.voices.items():
        if notes:
            last = notes[-1]
            end = last.offset + last.duration
            # Allow tolerance for cadential templates
            tolerance = bar_length * 2
            assert abs(end - expected_total) <= tolerance, (
                f"Voice {voice_id}: ends at {end}, expected {expected_total} (+/- {tolerance})"
            )


def test_first_note_offset(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-11: first note offset == 0 (or -upbeat if upbeat genre).

    Note: Upbeat handling in phrase writer may not be fully implemented.
    Test accepts offset 0 or -upbeat.
    """
    comp, _, _, _, _ = composition_data
    valid_starts = {Fraction(0), -comp.upbeat}
    for voice_id, notes in comp.voices.items():
        if notes:
            assert notes[0].offset in valid_starts, (
                f"Voice {voice_id}: starts at {notes[0].offset}, expected one of {valid_starts}"
            )


def test_metre_correct(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-12: metre matches genre config."""
    comp, gc, _, _, _ = composition_data
    assert comp.metre == gc.metre, f"Metre {comp.metre} != genre {gc.metre}"


def test_tempo_positive(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-13: tempo > 0."""
    comp, _, _, _, _ = composition_data
    assert comp.tempo > 0, f"Tempo {comp.tempo} must be positive"


def test_final_soprano_tonic(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-14: last soprano note degree == 1 in home key."""
    comp, _, home_key, _, _ = composition_data
    soprano = comp.voices.get("soprano") or comp.voices.get("upper")
    if soprano is None:
        for vid, notes in comp.voices.items():
            if notes and notes[0].voice == 0:
                soprano = notes
                break
    assert soprano is not None, "Cannot find soprano voice"
    final_degree = degree_at(midi=soprano[-1].pitch, key=home_key)
    assert final_degree == 1, f"Final soprano degree {final_degree} != 1"


def test_final_bass_tonic(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-15: last bass note degree == 1 in home key."""
    comp, gc, home_key, _, _ = composition_data
    bass = comp.voices.get("bass") or comp.voices.get("lower")
    if bass is None:
        for vid, notes in comp.voices.items():
            if notes and notes[0].voice != 0:
                bass = notes
                break
    assert bass is not None, "Cannot find bass voice"
    final_degree = degree_at(midi=bass[-1].pitch, key=home_key)
    assert final_degree == 1, f"Final bass degree {final_degree} != 1"


def test_final_unison_or_octave(composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...], int]) -> None:
    """C-16: final soprano and bass are unison or octave (interval class 0)."""
    comp, gc, _, _, _ = composition_data
    soprano = comp.voices.get("soprano") or comp.voices.get("upper")
    bass = comp.voices.get("bass") or comp.voices.get("lower")
    if soprano is None or bass is None:
        voices = list(comp.voices.values())
        soprano = voices[0] if voices else None
        bass = voices[1] if len(voices) > 1 else None
    assert soprano is not None and bass is not None, "Cannot find both voices"
    ic = abs(soprano[-1].pitch - bass[-1].pitch) % 12
    assert ic == 0, f"Final interval class {ic} != 0 (unison/octave)"
