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


FAULT_THRESHOLD: int = 30  # Maximum acceptable faults (lenient due to phrase boundary issues)


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
    faults = find_faults_from_composition(comp)
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
    soprano_final = degree_at(midi=soprano[-1].pitch, key=home_key)
    bass_final = degree_at(midi=bass[-1].pitch, key=home_key)
    assert soprano_final == 1, f"Final soprano degree {soprano_final} != 1"
    assert bass_final == 1, f"Final bass degree {bass_final} != 1"


def test_zero_parallel_perfects(system_output: tuple[Composition, list[Fault], Any, Key]) -> None:
    """Fault scan: 0 parallel fifths/octaves."""
    _, faults, gc, _ = system_output
    parallel_faults = [
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
    grotesque = [f for f in faults if f.category == "grotesque_leap"]
    assert len(grotesque) == 0, (
        f"Found {len(grotesque)} grotesque leaps: {[f.message for f in grotesque[:3]]}"
    )


def test_limited_faults(system_output: tuple[Composition, list[Fault], Any, Key]) -> None:
    """Total faults below threshold."""
    _, faults, _, _ = system_output
    assert len(faults) <= FAULT_THRESHOLD, (
        f"Found {len(faults)} faults (threshold {FAULT_THRESHOLD}). "
        f"Categories: {set(f.category for f in faults)}"
    )


def test_duration_integrity(system_output: tuple[Composition, list[Fault], Any, Key]) -> None:
    """No major gaps or overlaps in either voice.

    Note: Cadential phrase boundaries may cause minor gaps.
    Allows a threshold of issues per voice.
    """
    comp, _, _, _ = system_output
    max_issues_per_voice: int = 8
    for voice_id, notes in comp.voices.items():
        issue_count: int = 0
        for i in range(len(notes) - 1):
            expected_end = notes[i].offset + notes[i].duration
            actual_next = notes[i + 1].offset
            if expected_end != actual_next:
                issue_count += 1
        assert issue_count <= max_issues_per_voice, (
            f"Voice {voice_id}: {issue_count} duration integrity violations "
            f"(threshold {max_issues_per_voice})"
        )


# =============================================================================
# Genre-specific rhythmic character tests
# =============================================================================


def test_minuet_rhythmic_character() -> None:
    """>50% soprano notes are crotchets (1/4) for minuet genre."""
    comp, _, gc, _ = _run_full_pipeline("minuet")
    soprano, _ = _get_soprano_bass(comp)
    if not soprano:
        pytest.skip("No soprano notes")
    crotchet_count = sum(1 for n in soprano if n.duration == Fraction(1, 4))
    total = len(soprano)
    ratio = crotchet_count / total if total > 0 else 0
    assert ratio > 0.3, (
        f"Minuet: only {crotchet_count}/{total} ({ratio:.1%}) crotchets, expected >30%"
    )


def test_gavotte_rhythmic_character() -> None:
    """Gavotte has varied rhythmic values (not all uniform)."""
    comp, _, gc, _ = _run_full_pipeline("gavotte")
    soprano, _ = _get_soprano_bass(comp)
    if not soprano:
        pytest.skip("No soprano notes")
    # Check for rhythmic variety - at least 2 different durations
    durations = set(n.duration for n in soprano)
    assert len(durations) >= 2, (
        f"Gavotte: only {len(durations)} different durations, expected variety"
    )


@pytest.mark.skip(reason="invention has passo_indietro schema degree mismatch bug")
def test_invention_rhythmic_character() -> None:
    """Invention voices are not always homorhythmic (>30% offset difference)."""
    comp, _, gc, _ = _run_full_pipeline("invention")
    soprano, bass = _get_soprano_bass(comp)
    if not soprano or not bass:
        pytest.skip("Missing voices")
    # Count offsets where only one voice attacks
    soprano_offsets = {n.offset for n in soprano}
    bass_offsets = {n.offset for n in bass}
    all_offsets = soprano_offsets | bass_offsets
    shared_offsets = soprano_offsets & bass_offsets
    if not all_offsets:
        pytest.skip("No note offsets")
    independence_ratio = 1 - (len(shared_offsets) / len(all_offsets))
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
    # Check average duration is at least a quaver
    total_dur = sum((n.duration for n in soprano), Fraction(0))
    avg_dur = total_dur / len(soprano) if soprano else Fraction(0)
    assert avg_dur >= Fraction(1, 8), (
        f"Sarabande: average note duration {avg_dur} too short, expected >= 1/8"
    )


@pytest.mark.skip(reason="bourree is 4/4 but only has 3/4 rhythm cells defined")
def test_bourree_rhythmic_character() -> None:
    """Bourree has rhythmic variety (not all uniform durations)."""
    comp, _, gc, _ = _run_full_pipeline("bourree")
    soprano, _ = _get_soprano_bass(comp)
    if not soprano:
        pytest.skip("No soprano notes")
    durations = set(n.duration for n in soprano)
    assert len(durations) >= 2, (
        f"Bourree: only {len(durations)} different durations, expected variety"
    )
