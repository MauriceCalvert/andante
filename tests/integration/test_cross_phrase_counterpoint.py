"""Cross-phrase counterpoint tests.

Verifies invariants that span phrase boundaries (XP-01 to XP-06).
These catch issues the per-phrase L6 tests cannot detect.
"""
from fractions import Fraction

import pytest

from builder.phrase_types import PhrasePlan
from builder.types import Composition, GenreConfig, Note
from shared.key import Key
from tests.helpers import (
    check_no_parallel,
    check_no_voice_overlap,
    get_phrase_genres,
    parse_metre,
    run_pipeline_l7,
)

# Genres with rhythm cells for their metre — computed dynamically
PHRASE_GENRES: tuple[str, ...] = get_phrase_genres()
GROTESQUE_LEAP_SEMITONES: int = 19


@pytest.fixture(scope="module", params=PHRASE_GENRES)
def composition_data(
    request: pytest.FixtureRequest,
) -> tuple[Composition, GenreConfig, Key, tuple[PhrasePlan, ...]]:
    """Run full pipeline for each genre."""
    genre: str = request.param
    return run_pipeline_l7(genre=genre)


def _get_soprano_bass(comp: Composition) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
    """Extract soprano and bass note tuples from Composition."""
    soprano = comp.voices.get("soprano") or comp.voices.get("upper")
    bass = comp.voices.get("bass") or comp.voices.get("lower")
    if soprano is None or bass is None:
        voices = list(comp.voices.values())
        soprano = voices[0] if voices else ()
        bass = voices[1] if len(voices) > 1 else ()
    return soprano, bass


# =============================================================================
# XP-01 to XP-06: Cross-phrase counterpoint postconditions
# =============================================================================


def test_whole_piece_no_parallel_fifths(
    composition_data: tuple[Composition, GenreConfig, Key, tuple[PhrasePlan, ...]],
) -> None:
    """XP-01: no parallel fifths on any strong beat across entire piece."""
    comp, gc, _, _ = composition_data
    soprano, bass = _get_soprano_bass(comp)
    violations: list[str] = check_no_parallel(
        upper=soprano,
        lower=bass,
        metre=gc.metre,
        forbidden_ic=frozenset({7}),
    )
    assert len(violations) == 0, f"Parallel fifths found: {violations[:5]}"


def test_whole_piece_no_parallel_octaves(
    composition_data: tuple[Composition, GenreConfig, Key, tuple[PhrasePlan, ...]],
) -> None:
    """XP-02: no parallel octaves on any strong beat across entire piece."""
    comp, gc, _, _ = composition_data
    soprano, bass = _get_soprano_bass(comp)
    violations: list[str] = check_no_parallel(
        upper=soprano,
        lower=bass,
        metre=gc.metre,
        forbidden_ic=frozenset({0}),
    )
    assert len(violations) == 0, f"Parallel octaves found: {violations[:5]}"


def test_whole_piece_no_voice_overlap(
    composition_data: tuple[Composition, GenreConfig, Key, tuple[PhrasePlan, ...]],
) -> None:
    """XP-03: no voice overlap at any offset across entire piece."""
    comp, _, _, _ = composition_data
    soprano, bass = _get_soprano_bass(comp)
    violations: list[str] = check_no_voice_overlap(upper=soprano, lower=bass)
    assert len(violations) == 0, f"Voice overlap found: {violations[:5]}"


def test_whole_piece_no_grotesque_leaps(
    composition_data: tuple[Composition, GenreConfig, Key, tuple[PhrasePlan, ...]],
) -> None:
    """XP-05: no melodic interval > 19 semitones in either voice."""
    comp, _, _, _ = composition_data
    soprano, bass = _get_soprano_bass(comp)
    violations: list[str] = []
    for voice_name, notes in [("soprano", soprano), ("bass", bass)]:
        for i in range(len(notes) - 1):
            interval: int = abs(notes[i + 1].pitch - notes[i].pitch)
            if interval > GROTESQUE_LEAP_SEMITONES:
                violations.append(
                    f"{voice_name} leap of {interval}st at offset {notes[i].offset}"
                )
    assert len(violations) == 0, f"Grotesque leaps: {violations[:5]}"


def test_phrase_join_intervals(
    composition_data: tuple[Composition, GenreConfig, Key, tuple[PhrasePlan, ...]],
) -> None:
    """XP-06: no melodic interval > octave at phrase joins."""
    comp, gc, _, phrase_plans = composition_data
    if len(phrase_plans) < 2:
        pytest.skip("Less than 2 phrases")
    soprano, bass = _get_soprano_bass(comp)
    soprano_by_offset: dict[Fraction, Note] = {n.offset: n for n in soprano}
    bass_by_offset: dict[Fraction, Note] = {n.offset: n for n in bass}
    bar_length, _ = parse_metre(gc.metre)
    violations: list[str] = []
    for i in range(len(phrase_plans) - 1):
        current_plan: PhrasePlan = phrase_plans[i]
        next_plan: PhrasePlan = phrase_plans[i + 1]
        current_end: Fraction = current_plan.start_offset + current_plan.phrase_duration
        next_start: Fraction = next_plan.start_offset
        if abs(current_end - next_start) > Fraction(1, 32):
            continue  # Phrases not adjacent
        for voice_name, all_notes in [("soprano", soprano), ("bass", bass)]:
            last_note: Note | None = None
            for note in all_notes:
                if note.offset < current_end:
                    last_note = note
                else:
                    break
            first_note: Note | None = None
            for note in all_notes:
                if note.offset >= next_start - Fraction(1, 32):
                    first_note = note
                    break
            if last_note is not None and first_note is not None:
                interval: int = abs(first_note.pitch - last_note.pitch)
                if interval > 12:
                    violations.append(
                        f"{voice_name} phrase join at offset {next_start}: "
                        f"interval {interval} > octave"
                    )
    assert len(violations) == 0, f"Large phrase join intervals: {violations[:5]}"
