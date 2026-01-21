"""Builder package for Andante.

Transforms planning output into playable notes via 6-layer architecture.
"""
from builder.config_loader import load_configs
from builder.realisation import realise
from builder.solver import solve, Anchor, Slot, SolverConfig, Solution
from builder.slice import Slice, SlicePair, extract_slices, extract_slice_pairs
from builder.constraints import check_all_hard_constraints
from builder.costs import VoiceMode, compute_total_cost
from builder.types import NoteFile


__all__ = [
    # Config loading
    "load_configs",
    # Realisation
    "realise",
    # Solver
    "solve",
    "Anchor",
    "Slot",
    "SolverConfig",
    "Solution",
    # Slice analysis
    "Slice",
    "SlicePair",
    "extract_slices",
    "extract_slice_pairs",
    # Constraints
    "check_all_hard_constraints",
    # Costs
    "VoiceMode",
    "compute_total_cost",
    # Types
    "NoteFile",
]
