"""Answer generator: create tonal or real answer from a fugue subject.

The answer is the subject transposed to the dominant, with tonal mutations
where the subject crosses the tonic-dominant boundary.

Tonal mutation rules:
- Subject 1→5 becomes answer 5→1 (not 5→2)
- Subject 5→1 becomes answer 1→5 (not 1→4)
- All other intervals use real transposition (+4 scale degrees)
"""
from dataclasses import dataclass
from typing import Tuple

from motifs.head_generator import degrees_to_midi
from motifs.subject_generator import GeneratedSubject


REAL_TRANSPOSITION = 4  # Transpose up a 5th = 4 scale degrees


@dataclass(frozen=True)
class GeneratedAnswer:
    """Result of answer generation."""
    scale_indices: Tuple[int, ...]
    durations: Tuple[float, ...]
    midi_pitches: Tuple[int, ...]
    answer_type: str  # "real" or "tonal"
    mutation_points: Tuple[int, ...]  # Indices where tonal mutation applied


def _normalise_degree(degree: int) -> int:
    """Normalise degree to 0-6 range (within one octave)."""
    return degree % 7


def _is_tonic_region(degree: int) -> bool:
    """Check if degree is in tonic region (1, 2, 3 = indices 0, 1, 2)."""
    return _normalise_degree(degree=degree) in (0, 1, 2)


def _is_dominant_region(degree: int) -> bool:
    """Check if degree is in dominant region (5, 6, 7 = indices 4, 5, 6)."""
    return _normalise_degree(degree=degree) in (4, 5, 6)


def _crosses_boundary(from_degree: int, to_degree: int) -> bool:
    """Check if motion crosses the tonic-dominant boundary."""
    from_norm = _normalise_degree(degree=from_degree)
    to_norm = _normalise_degree(degree=to_degree)
    # 1→5 crossing (tonic to dominant)
    if from_norm == 0 and to_norm == 4:
        return True
    # 5→1 crossing (dominant to tonic)
    if from_norm == 4 and to_norm == 0:
        return True
    return False


def _get_mutation_type(from_degree: int, to_degree: int) -> str | None:
    """Determine mutation type for a boundary crossing.
    
    Returns:
        "1to5" if subject moves tonic→dominant
        "5to1" if subject moves dominant→tonic
        None if no boundary crossing
    """
    from_norm = _normalise_degree(degree=from_degree)
    to_norm = _normalise_degree(degree=to_degree)
    if from_norm == 0 and to_norm == 4:
        return "1to5"
    if from_norm == 4 and to_norm == 0:
        return "5to1"
    return None


def detect_boundary_crossings(degrees: tuple[int, ...]) -> list[int]:
    """Return indices where subject crosses tonic-dominant boundary.
    
    Only checks the head region (first half of subject or first 4 notes,
    whichever is smaller) since boundary crossings in the tail are rare
    and typically use real transposition.
    """
    if len(degrees) < 2:
        return []
    head_end = min(len(degrees) // 2 + 1, 5)
    crossings = []
    for i in range(head_end - 1):
        if _crosses_boundary(from_degree=degrees[i], to_degree=degrees[i + 1]):
            crossings.append(i)
    return crossings


def _apply_tonal_mutation(
    subject_degrees: tuple[int, ...],
    mutation_indices: list[int],
) -> tuple[int, ...]:
    """Apply tonal mutation at specified indices, identity elsewhere.

    For a real answer, we would just return subject_degrees unchanged.
    For a tonal answer, we mutate only at boundary crossings.
    The transposition to dominant happens in degrees_to_midi via dominant_midi.
    """
    answer = []
    for i, deg in enumerate(subject_degrees):
        if i > 0 and (i - 1) in mutation_indices:
            mutation = _get_mutation_type(
                from_degree=subject_degrees[i - 1],
                to_degree=deg,
            )
            if mutation == "1to5":
                # Subject 5th up (1→5) becomes answer 4th up (5→1): shift down 1
                answer.append(deg - 1)
            elif mutation == "5to1":
                # Subject 5th down (5→1) becomes answer 4th down (1→5): shift up 1
                answer.append(deg + 1)
            else:
                answer.append(deg)
        else:
            # Not a mutation point: use original degree
            answer.append(deg)
    return tuple(answer)


def generate_answer(
    subject: GeneratedSubject,
    tonic_midi: int = 60,
) -> GeneratedAnswer:
    """Generate tonal or real answer for a subject.
    
    Args:
        subject: The fugue subject
        tonic_midi: MIDI pitch of the tonic (for pitch conversion)
        
    Returns:
        GeneratedAnswer with scale indices in the dominant key
    """
    degrees = subject.scale_indices
    mutation_indices = detect_boundary_crossings(degrees=degrees)
    if mutation_indices:
        answer_degrees = _apply_tonal_mutation(
            subject_degrees=degrees,
            mutation_indices=mutation_indices,
        )
        answer_type = "tonal"
    else:
        # Real answer: use subject degrees unchanged. Transposition happens
        # in degrees_to_midi by passing dominant_midi as tonic.
        answer_degrees = degrees
        answer_type = "real"
    # Convert to MIDI (answer is in dominant key, so tonic is a 5th up)
    dominant_midi = tonic_midi + 7  # Up a perfect 5th
    midi_pitches = degrees_to_midi(
        degrees=answer_degrees,
        tonic_midi=dominant_midi,
        mode=subject.mode,
    )
    return GeneratedAnswer(
        scale_indices=answer_degrees,
        durations=subject.durations,
        midi_pitches=midi_pitches,
        answer_type=answer_type,
        mutation_points=tuple(mutation_indices),
    )


def answer_to_str(
    answer: GeneratedAnswer,
    tonic_midi: int = 60,
) -> str:
    """Format answer as readable string."""
    from shared.constants import NOTE_NAMES
    dominant_midi = tonic_midi + 7
    pitch_str = ' '.join(
        f"{NOTE_NAMES[m % 12]}{m // 12 - 1}" for m in answer.midi_pitches
    )
    mutation_str = f", mutations at {list(answer.mutation_points)}" if answer.mutation_points else ""
    return f"{answer.answer_type} answer: {pitch_str}{mutation_str}"


if __name__ == "__main__":
    from motifs.subject_generator import generate_subject
    # Test with a subject that should require tonal answer
    print("Testing answer generation...")
    print("=" * 60)
    # Generate subjects and their answers
    for seed in [42, 123, 456, 789, 1001]:
        print(f"\nSeed {seed}:")
        try:
            subject = generate_subject(
                mode="minor",
                metre=(4, 4),
                seed=seed,
                tonic_midi=67,  # G
                verbose=False,
            )
            print(f"  Subject degrees: {subject.scale_indices}")
            print(f"  Subject: leap {subject.leap_direction} {subject.leap_size}")
            answer = generate_answer(subject=subject, tonic_midi=67)
            print(f"  Answer degrees: {answer.scale_indices}")
            print(f"  Answer type: {answer.answer_type}")
            if answer.mutation_points:
                print(f"  Mutation at indices: {answer.mutation_points}")
        except RuntimeError as e:
            print(f"  Failed: {e}")
    # Test Little Fugue pattern manually
    print("\n" + "=" * 60)
    print("Little Fugue BWV 578 pattern test:")
    print("Subject opens G->D (1->5), should require tonal mutation")
    # Simulate Little Fugue subject degrees (simplified)
    # G=0, D=4, Bb=2, G=0, Bb=2, A=1, G=0, F#=6, A=1, D=-3
    little_fugue_degrees = (0, 4, 2, 0, 2, 1, 0, 6, 1, -3)
    crossings = detect_boundary_crossings(degrees=little_fugue_degrees)
    print(f"  Boundary crossings at: {crossings}")
    if crossings:
        mutated = _apply_tonal_mutation(
            subject_degrees=little_fugue_degrees,
            mutation_indices=crossings,
        )
        print(f"  Subject degrees: {little_fugue_degrees}")
        print(f"  Answer degrees:  {mutated}")
        print(f"  First interval - subject: {little_fugue_degrees[1] - little_fugue_degrees[0]}")
        print(f"  First interval - answer:  {mutated[1] - mutated[0]}")
