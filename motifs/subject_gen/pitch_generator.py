"""Pitch generation engine for baroque fugue subjects.

Delegates to melody_generator.generate_pitched_subjects.
Cache key is built from cell names, mode, n_bars, and bar_ticks
(tonic_midi excluded: generation is diatonic, MIDI conversion is downstream).
"""
import logging

from motifs.subject_gen.cache import _load_cache, _save_cache
from motifs.subject_gen.melody_generator import generate_pitched_subjects
from motifs.subject_gen.models import _ScoredPitch
from motifs.subject_gen.rhythm_cells import Cell

logger: logging.Logger = logging.getLogger(__name__)

# In-memory layer avoids redundant disk I/O within a single run.
_pitch_mem_cache: dict[str, list[_ScoredPitch]] = {}


def _cached_validated_pitch_for_cells(
    cell_sequence: tuple[Cell, ...],
    tonic_midi: int,
    mode: str,
    n_bars: int,
    bar_ticks: int,
    verbose: bool = False,
) -> list[_ScoredPitch]:
    """Generate and cache pitched subjects for a given cell sequence.

    Cache is keyed by cell names, mode, n_bars, and bar_ticks.
    tonic_midi is passed through to generate_pitched_subjects but does not
    affect the diatonic result and is excluded from the cache key.
    """
    cell_key: str = "_".join(c.name for c in cell_sequence)
    key: str = f"melody_pitch_v2_{cell_key}_{mode}_{n_bars}b_{bar_ticks}t.pkl"
    if key in _pitch_mem_cache:
        return _pitch_mem_cache[key]
    cached = _load_cache(key)
    if cached is not None:
        _pitch_mem_cache[key] = cached
        return cached

    result: list[_ScoredPitch] = generate_pitched_subjects(
        cell_sequence=cell_sequence,
        mode=mode,
        tonic_midi=tonic_midi,
        n_bars=n_bars,
        bar_ticks=bar_ticks,
    )
    _pitch_mem_cache[key] = result
    _save_cache(key, result)
    if verbose:
        logger.info(
            "    pitch cells=%s mode=%s n_bars=%d bar_ticks=%d -> %d",
            cell_key, mode, n_bars, bar_ticks, len(result),
        )
    return result
