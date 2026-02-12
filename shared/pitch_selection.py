"""Constraint-relaxation pitch selection."""
from fractions import Fraction
from typing import TYPE_CHECKING
from builder.types import Note
from shared.counterpoint import (
    has_consecutive_leaps,
    has_cross_relation,
    has_parallel_perfect,
    is_cross_bar_repetition,
    is_ugly_melodic_interval,
    needs_step_recovery,
    would_cross_voice,
)
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
    """
    assert len(candidates) > 0, "candidates must not be empty"
    if len(candidates) == 1:
        return candidates[0]
    best_pitch: int = candidates[0]
    best_penalty: int = _score_pitch(
        pitch=candidates[0],
        offset=offset,
        config=config,
        context=context,
        own_previous=own_previous,
    )
    for candidate in candidates[1:]:
        penalty: int = _score_pitch(
            pitch=candidate,
            offset=offset,
            config=config,
            context=context,
            own_previous=own_previous,
        )
        if penalty < best_penalty:
            best_penalty = penalty
            best_pitch = candidate
    return best_pitch

def _score_pitch(
        pitch: int,
        offset: Fraction,
        config: "VoiceConfig",
        context: "VoiceContext",
        own_previous: tuple[Note, ...],
) -> int:
    """Score a candidate pitch based on constraint violations.
    Returns total penalty (sum of weighted violations).
    """
    # 1. Resolve melodic history (current <- prev <- prev_prev)
    prev_note: Note | None = own_previous[-1] if own_previous else context.prior_phrase_tail
    # Construct a historical pool to safely fetch the note before the previous one
    history_pool = ([context.prior_phrase_tail] if context.prior_phrase_tail else []) + list(own_previous)
    prev_prev_pitch = history_pool[-2].pitch if len(history_pool) >= 2 else None
    # 2. Define Violations
    # Boolean checks for melodic constraints
    violation_step = needs_step_recovery(
        previous_notes=own_previous,
        candidate_pitch=pitch,
        structural_offsets=context.structural_offsets,
    )
    violation_leaps = (
            prev_prev_pitch is not None
            and prev_note is not None
            and has_consecutive_leaps(
        prev_prev_pitch=prev_prev_pitch,
        prev_pitch=prev_note.pitch,
        candidate_pitch=pitch,
    )
    )
    violation_ugly = (
            prev_note is not None
            and is_ugly_melodic_interval(from_pitch=prev_note.pitch, to_pitch=pitch)
    )
    violation_repetition = (
            prev_note is not None
            and is_cross_bar_repetition(
        pitch=pitch,
        offset=offset,
        previous_note=prev_note,
        bar_length=config.bar_length,
        phrase_start=config.phrase_start,
        structural_offsets=context.structural_offsets,
    )
    )
    # Generator checks for harmonic/polyphonic constraints
    violation_cross_relation = any(
        has_cross_relation(pitch, notes, offset, config.beat_unit)
        for notes in context.other_voices.values()
    )
    violation_parallels = any(
        has_parallel_perfect(
            pitch, offset, notes, prev_note, config.guard_tolerance
        )
        for notes in context.other_voices.values()
    )
    violation_voice_crossing = any(
        would_cross_voice(pitch, other_note.pitch, config.voice_id, other_id)
        for other_id, notes in context.other_voices.items()
        for other_note in notes
        if other_note.offset == offset
    )
    # 3. Calculate weighted sum
    # Python treats True as 1 and False as 0 in arithmetic operations.
    return sum((
        1 * violation_step,
        2 * violation_leaps,
        4 * violation_ugly,
        8 * violation_repetition,
        16 * violation_cross_relation,
        32 * violation_parallels,
        64 * violation_voice_crossing,
    ))
