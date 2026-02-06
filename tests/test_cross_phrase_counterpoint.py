"""Cross-phrase counterpoint tests.

Verifies invariants that span phrase boundaries (XP-01 to XP-06).
These catch issues the per-phrase L6 tests cannot detect.
"""
import pytest
from fractions import Fraction
from typing import Any

from builder.compose import compose_phrases
from builder.config_loader import load_configs
from builder.phrase_planner import build_phrase_plans
from builder.phrase_types import PhrasePlan
from builder.types import Composition, Note
from planner.metric.layer import layer_4_metric
from planner.schematic import layer_3_schematic
from planner.tonal import layer_2_tonal
from shared.key import Key
from tests.helpers import (
    check_no_parallel,
    check_no_voice_overlap,
    get_phrase_genres,
    parse_metre,
)


# Genres with rhythm cells for their metre — computed dynamically
PHRASE_GENRES: tuple[str, ...] = get_phrase_genres()
GROTESQUE_LEAP_SEMITONES: int = 19


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
    home_key = anchors[0].local_key
    comp = compose_phrases(
        phrase_plans=phrase_plans,
        home_key=home_key,
        metre=gc.metre,
        tempo=gc.tempo,
        upbeat=gc.upbeat,
    )
    return comp, gc, home_key, phrase_plans


@pytest.fixture(scope="module", params=PHRASE_GENRES)
def composition_data(request: pytest.FixtureRequest) -> tuple[Composition, Any, Key, tuple[PhrasePlan, ...]]:
    """Run full pipeline for each genre."""
    genre = request.param
    return _run_full_pipeline(genre)


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
    composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...]]
) -> None:
    """XP-01: no parallel fifths on any strong beat across entire piece."""
    comp, gc, _, _ = composition_data
    soprano, bass = _get_soprano_bass(comp)
    violations = check_no_parallel(
        upper=soprano,
        lower=bass,
        metre=gc.metre,
        forbidden_ic=frozenset({7}),
    )
    assert len(violations) == 0, f"Parallel fifths found: {violations[:5]}"


def test_whole_piece_no_parallel_octaves(
    composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...]]
) -> None:
    """XP-02: no parallel octaves on any strong beat across entire piece."""
    comp, gc, _, _ = composition_data
    soprano, bass = _get_soprano_bass(comp)
    violations = check_no_parallel(
        upper=soprano,
        lower=bass,
        metre=gc.metre,
        forbidden_ic=frozenset({0}),
    )
    assert len(violations) == 0, f"Parallel octaves found: {violations[:5]}"


def test_whole_piece_no_voice_overlap(
    composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...]]
) -> None:
    """XP-03: no voice overlap at any offset across entire piece."""
    comp, _, _, _ = composition_data
    soprano, bass = _get_soprano_bass(comp)
    violations = check_no_voice_overlap(upper=soprano, lower=bass)
    assert len(violations) == 0, f"Voice overlap found: {violations[:5]}"



def test_whole_piece_no_grotesque_leaps(
    composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...]]
) -> None:
    """XP-05: no melodic interval > 19 semitones in either voice."""
    comp, _, _, _ = composition_data
    soprano, bass = _get_soprano_bass(comp)
    violations: list[str] = []
    for voice_name, notes in [("soprano", soprano), ("bass", bass)]:
        for i in range(len(notes) - 1):
            interval = abs(notes[i + 1].pitch - notes[i].pitch)
            if interval > GROTESQUE_LEAP_SEMITONES:
                violations.append(
                    f"{voice_name} leap of {interval}st at offset {notes[i].offset}"
                )
    assert len(violations) == 0, f"Grotesque leaps: {violations[:5]}"


def test_phrase_join_intervals(
    composition_data: tuple[Composition, Any, Key, tuple[PhrasePlan, ...]]
) -> None:
    """XP-06: no melodic interval > octave at phrase joins."""
    comp, gc, _, phrase_plans = composition_data
    if len(phrase_plans) < 2:
        pytest.skip("Less than 2 phrases")
    soprano, bass = _get_soprano_bass(comp)
    # Build index of notes by offset for each voice
    soprano_by_offset = {n.offset: n for n in soprano}
    bass_by_offset = {n.offset: n for n in bass}
    bar_length, _ = parse_metre(gc.metre)
    violations: list[str] = []
    for i in range(len(phrase_plans) - 1):
        current_plan = phrase_plans[i]
        next_plan = phrase_plans[i + 1]
        # Find last note of current phrase and first note of next phrase
        current_end = current_plan.start_offset + current_plan.phrase_duration
        next_start = next_plan.start_offset
        # Allow small tolerance for boundary alignment
        if abs(current_end - next_start) > Fraction(1, 32):
            continue  # Phrases not adjacent
        # Find notes at phrase boundary
        for voice_name, by_offset in [("soprano", soprano_by_offset), ("bass", bass_by_offset)]:
            # Find last note ending at or before current_end
            last_note = None
            for note in (soprano if voice_name == "soprano" else bass):
                if note.offset < current_end:
                    last_note = note
                else:
                    break
            # Find first note at or after next_start
            first_note = None
            for note in (soprano if voice_name == "soprano" else bass):
                if note.offset >= next_start - Fraction(1, 32):
                    first_note = note
                    break
            if last_note is not None and first_note is not None:
                interval = abs(first_note.pitch - last_note.pitch)
                if interval > 12:
                    violations.append(
                        f"{voice_name} phrase join at offset {next_start}: "
                        f"interval {interval} > octave"
                    )
    assert len(violations) == 0, f"Large phrase join intervals: {violations[:5]}"
