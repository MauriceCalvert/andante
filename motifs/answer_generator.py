"""Answer generator: create tonal answer from a fugue subject.

The answer is the subject transposed to the dominant with tonal mutations.
Real answers are forbidden — all answers are tonal.

Tonal mutation rule (per-note):
- Subject notes in the tonic region (scale degrees 1,2,3,4 = indices 0,1,2,3)
  transpose up a 4th (+ 3 scale degrees).
- Subject notes in the dominant region (scale degrees 5,6,7 = indices 4,5,6)
  transpose up a 5th (+ 4 scale degrees).

This produces the standard tonal answer where 1↔5 and the surrounding
notes warp accordingly. The answer is notated in the tonic key, not the
dominant key — the transposition is built into the degree mapping.

The answer preserves the subject's rhythm exactly — tonal answers in
Bach always use the same rhythm as the subject.
"""
from dataclasses import dataclass
from typing import Tuple

from motifs.head_generator import degrees_to_midi
from motifs.subject_generator import GeneratedSubject


TONIC_TRANSPOSITION = 3      # Tonic region notes: up a 4th
DOMINANT_TRANSPOSITION = 4   # Dominant region notes: up a 5th


@dataclass(frozen=True)
class GeneratedAnswer:
    """Result of answer generation."""
    scale_indices: Tuple[int, ...]
    durations: Tuple[float, ...]
    midi_pitches: Tuple[int, ...]
    answer_type: str  # Always "tonal"
    mutation_points: Tuple[int, ...]  # Indices where transposition amount changes


def _is_tonic_region(degree: int) -> bool:
    """Check if degree is in tonic region (indices 0,1,2,3 mod 7)."""
    return (degree % 7) in (0, 1, 2, 3)


def _transposition_for_degree(degree: int) -> int:
    """Return transposition amount for a given subject degree."""
    if _is_tonic_region(degree=degree):
        return TONIC_TRANSPOSITION
    return DOMINANT_TRANSPOSITION


def _find_mutation_points(degrees: tuple[int, ...]) -> list[int]:
    """Find indices where transposition amount changes between adjacent notes."""
    mutations = []
    for i in range(len(degrees) - 1):
        t_curr = _transposition_for_degree(degree=degrees[i])
        t_next = _transposition_for_degree(degree=degrees[i + 1])
        if t_curr != t_next:
            mutations.append(i)
    return mutations


def _apply_tonal_transposition(degrees: tuple[int, ...]) -> tuple[int, ...]:
    """Transpose each degree by its region-appropriate amount."""
    return tuple(
        deg + _transposition_for_degree(degree=deg)
        for deg in degrees
    )


def generate_answer(
    subject: GeneratedSubject,
    tonic_midi: int = 60,
) -> GeneratedAnswer:
    """Generate tonal answer for a subject."""
    degrees = subject.scale_indices
    answer_degrees = _apply_tonal_transposition(degrees=degrees)
    mutation_points = _find_mutation_points(degrees=degrees)
    answer_durations = subject.durations
    midi_pitches = degrees_to_midi(
        degrees=answer_degrees,
        tonic_midi=tonic_midi,
        mode=subject.mode,
    )
    return GeneratedAnswer(
        scale_indices=answer_degrees,
        durations=answer_durations,
        midi_pitches=midi_pitches,
        answer_type="tonal",
        mutation_points=tuple(mutation_points),
    )


def answer_to_str(
    answer: GeneratedAnswer,
    tonic_midi: int = 60,
) -> str:
    """Format answer as readable string."""
    from shared.constants import NOTE_NAMES
    pitch_str = ' '.join(
        f"{NOTE_NAMES[m % 12]}{m // 12 - 1}" for m in answer.midi_pitches
    )
    mutation_str = f", mutations at {list(answer.mutation_points)}" if answer.mutation_points else ""
    return f"tonal answer: {pitch_str}{mutation_str}"


if __name__ == "__main__":
    from motifs.subject_generator import select_subject
    print("Testing tonal answer generation...")
    print("=" * 60)
    for seed in [42, 123, 456, 789, 1001]:
        print(f"\nSeed {seed}:")
        try:
            subject = select_subject(
                mode="minor",
                metre=(4, 4),
                tonic_midi=67,
                target_bars=2,
            )
            print(f"  Subject degrees: {subject.scale_indices}")
            answer = generate_answer(subject=subject, tonic_midi=67)
            print(f"  Answer degrees:  {answer.scale_indices}")
            print(f"  Subject durs: {subject.durations}")
            print(f"  Answer durs:  {answer.durations}")
            if answer.mutation_points:
                print(f"  Mutations at: {list(answer.mutation_points)}")
                for mp in answer.mutation_points:
                    s_deg = subject.scale_indices[mp]
                    s_next = subject.scale_indices[mp + 1]
                    print(f"    [{mp}] deg {s_deg} (T={_transposition_for_degree(s_deg)}) "
                          f"-> deg {s_next} (T={_transposition_for_degree(s_next)})")
        except RuntimeError as e:
            print(f"  Failed: {e}")
