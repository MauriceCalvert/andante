"""Stage 1: Exhaustive pitch generation and validation."""

from motifs.head_generator import degrees_to_midi
from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.cpsat_generator import generate_cpsat_degrees
from motifs.subject_gen.contour import _derive_shape_name
from motifs.subject_gen.models import _ScoredPitch
from motifs.subject_gen.validator import is_melodically_valid


def _degrees_to_ivs(degrees: tuple[int, ...]) -> tuple[int, ...]:
    """Convert degree sequence to interval sequence."""
    return tuple(degrees[i + 1] - degrees[i] for i in range(len(degrees) - 1))


def _cached_validated_pitch(
    num_notes: int,
    tonic_midi: int,
    mode: str,
) -> list[_ScoredPitch]:
    """All validated+classified pitch sequences, cached to disk."""
    stretto_k = num_notes // 2
    key = f"cpsat_pitch_{num_notes}n_{mode}_k{stretto_k}.pkl"
    cached = _load_cache(key)
    if cached is not None:
        return cached
    degree_sequences = generate_cpsat_degrees(
        num_notes=num_notes,
        mode=mode,
        stretto_k=stretto_k,
    )
    result: list[_ScoredPitch] = []
    for degs in degree_sequences:
        midi = degrees_to_midi(degrees=degs, tonic_midi=tonic_midi, mode=mode)
        if not is_melodically_valid(midi):
            continue
        ivs = _degrees_to_ivs(degs)
        shape = _derive_shape_name(list(degs))
        result.append(_ScoredPitch(score=0.0, ivs=ivs, degrees=degs, shape=shape))
    _save_cache(key, result)
    return result
