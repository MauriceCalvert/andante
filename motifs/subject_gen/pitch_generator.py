"""Stage 1: Head enumeration + tail generation + validation."""

from motifs.head_generator import degrees_to_midi
from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.constants import HEAD_LENGTHS
from motifs.subject_gen.contour import _derive_shape_name
from motifs.subject_gen.cpsat_generator import build_consonant_pairs, generate_tails_for_head
from motifs.subject_gen.head_enumerator import enumerate_heads
from motifs.subject_gen.models import _ScoredPitch
from motifs.subject_gen.validator import is_melodically_valid
from shared.pitch import degrees_to_intervals as _degrees_to_ivs


def _cached_validated_pitch(
    num_notes: int,
    tonic_midi: int,
    mode: str,
    verbose: bool = False,
) -> list[_ScoredPitch]:
    """All validated+classified pitch sequences, cached to disk."""
    stretto_k: int = num_notes // 2
    hl_tag: str = "_".join(str(h) for h in HEAD_LENGTHS)
    key: str = f"cpsat_pitch_{num_notes}n_{mode}_k{stretto_k}_hl{hl_tag}.pkl"
    cached = _load_cache(key)
    if cached is not None:
        return cached
    consonant_pairs = build_consonant_pairs(mode)
    all_sequences: set[tuple[int, ...]] = set()
    for head_size in HEAD_LENGTHS:
        assert num_notes - head_size >= 2, (
            f"Head {head_size} too long for {num_notes} notes"
        )
        heads: list[tuple[int, ...]] = enumerate_heads(head_size)
        if verbose:
            print(f"  Heads(len={head_size}): {len(heads)} enumerated")
        fertile: int = 0
        for head in heads:
            tails = generate_tails_for_head(
                head=head,
                num_notes=num_notes,
                stretto_k=stretto_k,
                consonant_pairs=consonant_pairs,
            )
            if tails:
                fertile += 1
            all_sequences.update(tails)
        if verbose:
            print(f"  Heads(len={head_size}): {fertile}/{len(heads)} fertile, "
                  f"{len(all_sequences)} sequences so far")
    result: list[_ScoredPitch] = []
    for degs in sorted(all_sequences):
        midi = degrees_to_midi(degrees=degs, tonic_midi=tonic_midi, mode=mode)
        if not is_melodically_valid(midi):
            continue
        ivs = _degrees_to_ivs(degs)
        shape: str = _derive_shape_name(list(degs))
        result.append(_ScoredPitch(score=0.0, ivs=ivs, degrees=degs, shape=shape))
    _save_cache(key, result)
    return result
