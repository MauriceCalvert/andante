"""Constraint-relaxation pitch selection."""
from fractions import Fraction
from typing import TYPE_CHECKING

from builder.types import Note

if TYPE_CHECKING:
    from builder.voice_types import VoiceConfig, VoiceContext


def select_best_pitch(
    candidates: tuple[int, ...],
    offset: Fraction,
    config: "VoiceConfig",
    context: "VoiceContext",
    own_previous: tuple[Note, ...],
) -> int:
    """Select candidate pitch with fewest/least-severe violations.

    Constraint relaxation priority (strictest last to relax):

    | Priority | Constraint                          | Relax?           |
    |----------|-------------------------------------|------------------|
    | 0        | Hard invariants (range, duration)   | Never            |
    | 1        | Voice crossing                      | Never            |
    | 2        | Parallel perfect intervals          | Last resort only |
    | 3        | Cross-relations                     | Before parallels |
    | 4        | Cross-bar repetition                | Before cross-rel |
    | 5        | Ugly melodic intervals              | Before cross-bar |
    | 6        | Consecutive same-direction leaps    | Before ugly      |
    | 7        | Step recovery                       | First to relax   |

    Scores each candidate against the constraint set using the priority table.
    Returns the candidate with the lowest total penalty. Never fails — always
    returns something within hard invariants.

    Candidates must all be within range (priority 0). The caller is responsible
    for generating only in-range candidates.

    TODO Phase 16c: Implement scoring logic when VoiceConfig/VoiceContext available.
    For now, returns first candidate as placeholder.
    """
    assert len(candidates) > 0, "candidates must not be empty"
    # Placeholder: return first candidate
    return candidates[0]
