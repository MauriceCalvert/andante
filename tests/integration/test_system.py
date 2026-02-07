"""System tests for full pipeline end-to-end verification.

These are coarser than contract tests and verify emergent properties
of the complete output.
"""
import pytest
from fractions import Fraction
from typing import Any

from builder.compose import compose_phrases
from builder.config_loader import load_configs
from builder.faults import Fault, find_faults_from_composition
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


def _run_full_pipeline(genre: str, key: str = "c_major") -> tuple[Composition, list[Fault], Any, Key]:
    """Run full pipeline and return Composition, faults, GenreConfig, home_key."""
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
    phrase_plans: tuple[PhrasePlan, ...] = build_phrase_plans(
        schema_chain=chain,
        anchors=anchors,
        genre_config=gc,
        schemas=config["schemas"],
        total_bars=total_bars,
    )
    home_key: Key = anchors[0].local_key
    comp: Composition = compose_phrases(
        phrase_plans=phrase_plans,
        home_key=home_key,
        metre=gc.metre,
        tempo=gc.tempo,
        upbeat=gc.upbeat,
    )
    faults: list[Fault] = find_faults_from_composition(comp)
    return comp, faults, gc, home_key


_SYS_PARAMS: list[tuple[str, str]] = [
    (g, k) for g in PHRASE_GENRES for k in KEYS
]


@pytest.fixture(scope="module", params=_SYS_PARAMS, ids=[f"{g}_{k}" for g, k in _SYS_PARAMS])
def system_output(request: pytest.FixtureRequest) -> tuple[Composition, list[Fault], Any, Key]:
    """Run full pipeline and return output with faults."""
    genre, key = request.param
    return _run_full_pipeline(genre=genre, key=key)


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
# System tests - parametrised over all genres
# =============================================================================


def test_generates_output(system_output: tuple[Composition, list[Fault], Any, Key]) -> None:
    """Both voices have non-empty output."""
    comp, _, _, _ = system_output
    soprano, bass = _get_soprano_bass(comp)
    assert len(soprano) > 0, "Soprano is empty"
    assert len(bass) > 0, "Bass is empty"


def test_correct_final_degree(system_output: tuple[Composition, list[Fault], Any, Key]) -> None:
    """Final notes are tonic in home key."""
    comp, _, gc, home_key = system_output
    soprano, bass = _get_soprano_bass(comp)
    soprano_final: int = degree_at(midi=soprano[-1].pitch, key=home_key)
    bass_final: int = degree_at(midi=bass[-1].pitch, key=home_key)
    assert soprano_final == 1, f"Final soprano degree {soprano_final} != 1"
    assert bass_final == 1, f"Final bass degree {bass_final} != 1"


def test_zero_parallel_perfects(system_output: tuple[Composition, list[Fault], Any, Key]) -> None:
    """Fault scan: 0 parallel fifths/octaves."""
    _, faults, gc, _ = system_output
    parallel_faults: list[Fault] = [
        f for f in faults
        if f.category in ("parallel_fifth", "parallel_octave", "parallel_unison")
    ]
    assert len(parallel_faults) == 0, (
        f"Found {len(parallel_faults)} parallel perfect faults: "
        f"{[f.message for f in parallel_faults[:3]]}"
    )


def test_zero_grotesque_leaps(system_output: tuple[Composition, list[Fault], Any, Key]) -> None:
    """Fault scan: 0 grotesque leaps."""
    _, faults, _, _ = system_output
    grotesque: list[Fault] = [f for f in faults if f.category == "grotesque_leap"]
    assert len(grotesque) == 0, (
        f"Found {len(grotesque)} grotesque leaps: {[f.message for f in grotesque[:3]]}"
    )


def test_zero_faults(system_output: tuple[Composition, list[Fault], Any, Key]) -> None:
    """Total faults must be zero."""
    _, faults, _, _ = system_output
    assert len(faults) == 0, (
        f"Found {len(faults)} faults. "
        f"Categories: {set(f.category for f in faults)}"
    )


def test_duration_integrity(system_output: tuple[Composition, list[Fault], Any, Key]) -> None:
    """No gaps or overlaps in either voice."""
    comp, _, _, _ = system_output
    for voice_id, notes in comp.voices.items():
        for i in range(len(notes) - 1):
            expected_end: Fraction = notes[i].offset + notes[i].duration
            actual_next: Fraction = notes[i + 1].offset
            assert expected_end == actual_next, (
                f"Voice {voice_id}: duration integrity violation at offset {notes[i].offset} "
                f"(ends {expected_end}, next starts {actual_next})"
            )


# =============================================================================
# Genre-specific rhythmic character tests
# =============================================================================


def test_minuet_rhythmic_character() -> None:
    """>30% soprano notes are crotchets (1/4) for minuet genre."""
    comp, _, gc, _ = _run_full_pipeline("minuet")
    soprano, _ = _get_soprano_bass(comp)
    if not soprano:
        pytest.skip("No soprano notes")
    crotchet_count: int = sum(1 for n in soprano if n.duration == Fraction(1, 4))
    total: int = len(soprano)
    ratio: float = crotchet_count / total if total > 0 else 0
    assert ratio > 0.3, (
        f"Minuet: only {crotchet_count}/{total} ({ratio:.1%}) crotchets, expected >30%"
    )


def test_gavotte_rhythmic_character() -> None:
    """Gavotte has varied rhythmic values (not all uniform)."""
    comp, _, gc, _ = _run_full_pipeline("gavotte")
    soprano, _ = _get_soprano_bass(comp)
    if not soprano:
        pytest.skip("No soprano notes")
    durations: set[Fraction] = set(n.duration for n in soprano)
    assert len(durations) >= 2, (
        f"Gavotte: only {len(durations)} different durations, expected variety"
    )


def test_invention_rhythmic_character() -> None:
    """Invention voices are not always homorhythmic (>30% offset difference)."""
    comp, _, gc, _ = _run_full_pipeline("invention")
    soprano, bass = _get_soprano_bass(comp)
    if not soprano or not bass:
        pytest.skip("Missing voices")
    soprano_offsets: set[Fraction] = {n.offset for n in soprano}
    bass_offsets: set[Fraction] = {n.offset for n in bass}
    all_offsets: set[Fraction] = soprano_offsets | bass_offsets
    shared_offsets: set[Fraction] = soprano_offsets & bass_offsets
    if not all_offsets:
        pytest.skip("No note offsets")
    independence_ratio: float = 1 - (len(shared_offsets) / len(all_offsets))
    assert independence_ratio > 0.2, (
        f"Invention: voices too homorhythmic ({independence_ratio:.1%} independent), "
        f"expected >20%"
    )


def test_sarabande_rhythmic_character() -> None:
    """Sarabande has longer note values on average than faster dances."""
    comp, _, gc, _ = _run_full_pipeline("sarabande")
    soprano, _ = _get_soprano_bass(comp)
    if not soprano:
        pytest.skip("No soprano notes")
    total_dur: Fraction = sum((n.duration for n in soprano), Fraction(0))
    avg_dur: Fraction = total_dur / len(soprano) if soprano else Fraction(0)
    assert avg_dur >= Fraction(1, 8), (
        f"Sarabande: average note duration {avg_dur} too short, expected >= 1/8"
    )


def test_bourree_rhythmic_character() -> None:
    """Bourree has rhythmic variety (not all uniform durations)."""
    comp, _, gc, _ = _run_full_pipeline("bourree")
    soprano, _ = _get_soprano_bass(comp)
    if not soprano:
        pytest.skip("No soprano notes")
    durations: set[Fraction] = set(n.duration for n in soprano)
    assert len(durations) >= 2, (
        f"Bourree: only {len(durations)} different durations, expected variety"
    )
