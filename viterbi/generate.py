"""Unified voice generation via Viterbi pathfinding.

All voices (soprano, bass, inner voices) use the same generation function.
Differences are parametric, not algorithmic.
"""
from fractions import Fraction

from builder.types import Note
from viterbi.mtypes import ContourShape, ExistingVoice, Knot
from viterbi.pipeline import solve_phrase
from viterbi.scale import KeyInfo


def generate_voice(
    structural_knots: list[Knot],
    rhythm_grid: list[tuple[Fraction, Fraction]],   # (onset, duration)
    existing_voices: list[ExistingVoice],
    range_low: int,
    range_high: int,
    key: KeyInfo,
    voice_id: int,
    beats_per_bar: float,
    chord_pcs_per_beat: list[frozenset[int]] | None = None,
    contour: ContourShape | None = None,
) -> tuple[Note, ...]:
    """Generate one voice via Viterbi pathfinding against existing voices.

    Args:
        structural_knots: Schema degree positions the path must pass through (may be empty)
        rhythm_grid: Onset/duration pairs for this voice's rhythm
        existing_voices: All voices composed so far (for pairwise evaluation)
        range_low: Instrument lower bound (MIDI)
        range_high: Instrument upper bound (MIDI)
        key: Current key context
        voice_id: Track identifier (TRACK_SOPRANO, TRACK_BASS, etc.)
        beats_per_bar: Metre denominator (e.g. 4.0 for 4/4)
        chord_pcs_per_beat: Optional chord pitch-class sets per beat (for H3 harmony)

    Returns:
        Tuple of Notes for this voice.
    """
    # a. Extract beat_grid from rhythm_grid
    beat_grid: list[float] = [float(onset) for onset, _ in rhythm_grid]

    # b. Use knots as-is (caller handles alignment for voice-specific logic)
    aligned_knots: list[Knot] = structural_knots

    # c. Call solve_phrase
    result = solve_phrase(
        beat_grid=beat_grid,
        existing_voices=existing_voices,
        follower_knots=aligned_knots,
        follower_low=range_low,
        follower_high=range_high,
        verbose=False,
        key=key,
        chord_pcs_per_beat=chord_pcs_per_beat,
        beats_per_bar=beats_per_bar,
        contour=contour,
    )

    # d. Convert solver result to Notes
    notes: list[Note] = []
    for (onset, duration), pitch in zip(rhythm_grid, result.pitches):
        # Handle final marker (duration < 0): extend previous note instead of creating new one
        if duration < 0:
            # This is the final endpoint marker; extend the previous note to phrase_end
            if len(notes) > 0:
                prev_note: Note = notes[-1]
                extended_dur: Fraction = onset - prev_note.offset
                notes[-1] = Note(
                    offset=prev_note.offset,
                    pitch=prev_note.pitch,
                    duration=extended_dur,
                    voice=voice_id,
                )
            # Don't create a new note for the marker
            continue
        # Regular note
        notes.append(Note(
            offset=onset,
            pitch=pitch,
            duration=duration,
            voice=voice_id,
        ))

    # e. Return tuple
    return tuple(notes)
