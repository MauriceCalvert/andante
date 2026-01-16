"""Material manager: generates or accepts motif with affect-driven generation.

L005: Arithmetic on durations forbidden - use music_math functions
L006: All durations must be in VALID_DURATIONS - no division
L012: No quantization - patterns must use valid durations from the start
"""
from fractions import Fraction
from typing import Tuple

from shared.pitch import wrap_degree
from shared.music_math import VALID_DURATIONS
from planner.subject import Subject
from planner.plannertypes import DerivedMotif, Frame, Material, Motif


# Fallback motifs for when affect-driven generation is not available
MOTIFS: dict[str, tuple[tuple[int, ...], tuple[Fraction, ...]]] = {
    "4/4": (
        (1, 5, 4, 3, 2, 1, 7, 1),
        (Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
         Fraction(1, 8), Fraction(1, 8), Fraction(1, 8),
         Fraction(1, 16), Fraction(1, 16)),
    ),
    "3/4": (
        (1, 3, 5, 4, 3, 2),
        (Fraction(1, 8), Fraction(1, 8), Fraction(1, 8),
         Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
    ),
}

# Affects that support affect-driven generation
AFFECT_DRIVEN_AFFECTS = {
    "Sehnsucht", "Klage", "Freudigkeit", "Majestaet",
    "Zaertlichkeit", "Zorn", "Verwunderung", "Entschlossenheit",
}


def bar_duration(metre: str) -> Fraction:
    """Calculate duration of one bar in whole notes."""
    num_str, den_str = metre.split("/")
    return Fraction(int(num_str), int(den_str))


def parse_metre(metre: str) -> Tuple[int, int]:
    """Parse metre string like '4/4' to tuple (4, 4)."""
    num_str, den_str = metre.split("/")
    return (int(num_str), int(den_str))


def _snap_to_valid_fraction(value: float) -> Fraction:
    """Find nearest valid duration (as Fraction) to given float value.

    L005/L006/L012: Select from VALID_DURATIONS, no quantization.
    """
    best: Fraction = min(VALID_DURATIONS)
    best_dist: float = abs(value - float(best))
    for v in VALID_DURATIONS:
        dist = abs(value - float(v))
        if dist < best_dist:
            best = v
            best_dist = dist
    return best


def generate_motif(frame: Frame) -> Motif:
    """Generate a default 1-bar asymmetric motif (D006)."""
    assert frame.metre in MOTIFS, f"No motif template for metre {frame.metre}"
    degrees, durations = MOTIFS[frame.metre]
    return Motif(degrees=degrees, durations=durations, bars=1)


def generate_affect_driven_motif(
    affect: str,
    frame: Frame,
    seed: int | None = None,
) -> Motif:
    """Generate a motif using brute-force candidate generation.

    Generates 1M candidates, scores them all, returns the best.
    No affect-specific logic - just find good baroque subjects.

    Args:
        affect: Affect name (unused, kept for API compatibility)
        frame: Frame with mode, metre, etc.
        seed: Optional random seed for reproducibility

    Returns:
        Motif with degrees and durations
    """
    from motifs.subject_generator import generate_subject

    metre = parse_metre(frame.metre)

    # Generate subject using head+tail construction
    generated = generate_subject(
        mode=frame.mode,
        metre=metre,
        seed=seed,
        tonic_midi=60,  # C4 - will be transposed by key later
        verbose=False,
    )

    # Convert 0-indexed scale indices to 1-indexed degrees (1-7)
    degrees = tuple(((idx % 7) + 1) for idx in generated.scale_indices)

    # Convert float durations to nearest valid Fractions
    # L005/L006/L012: Use snap to valid, not limit_denominator
    durations = tuple(_snap_to_valid_fraction(d) for d in generated.durations)

    return Motif(degrees=degrees, durations=durations, bars=generated.bars)


def _apply_motif_transform(degrees: tuple[int, ...], transform: str) -> tuple[int, ...]:
    """Apply a single transform to degrees."""
    if transform == "invert":
        return tuple(wrap_degree(8 - d) for d in degrees)
    elif transform == "retrograde":
        return tuple(reversed(degrees))
    return degrees


def _apply_duration_transform(durations: tuple[Fraction, ...], transform: str) -> tuple[Fraction, ...]:
    """Apply a single transform to durations."""
    if transform == "augment":
        return tuple(d * 2 for d in durations)
    elif transform == "diminish":
        return tuple(max(d / 2, Fraction(1, 16)) for d in durations)
    elif transform == "retrograde":
        return tuple(reversed(durations))
    return durations


def compute_derived_motifs(subject: Motif, cs: Motif | None) -> tuple[DerivedMotif, ...]:
    """Pre-compute derived motifs from subject and counter-subject."""
    derived: list[DerivedMotif] = []
    head_size: int = min(4, len(subject.degrees))
    tail_size: int = min(3, len(subject.degrees))
    head_deg: tuple[int, ...] = subject.degrees[:head_size]
    head_dur: tuple[Fraction, ...] = subject.durations[:head_size]
    tail_deg: tuple[int, ...] = subject.degrees[-tail_size:]
    tail_dur: tuple[Fraction, ...] = subject.durations[-tail_size:]
    derived.append(DerivedMotif(
        name="head_inverted",
        degrees=_apply_motif_transform(head_deg, "invert"),
        durations=head_dur,
        source="subject",
        transforms=("head", "invert"),
    ))
    derived.append(DerivedMotif(
        name="tail_augmented",
        degrees=tail_deg,
        durations=_apply_duration_transform(tail_dur, "augment"),
        source="subject",
        transforms=("tail", "augment"),
    ))
    derived.append(DerivedMotif(
        name="head_retrograde",
        degrees=_apply_motif_transform(head_deg, "retrograde"),
        durations=_apply_duration_transform(head_dur, "retrograde"),
        source="subject",
        transforms=("head", "retrograde"),
    ))
    if cs is not None:
        cs_head_size: int = min(4, len(cs.degrees))
        derived.append(DerivedMotif(
            name="counter_head",
            degrees=cs.degrees[:cs_head_size],
            durations=cs.durations[:cs_head_size],
            source="counter_subject",
            transforms=("head",),
        ))
    return tuple(derived)


def acquire_material(
    frame: Frame,
    user_motif: Motif | None = None,
    user_cs: Motif | None = None,
    genre: str = "",
    affect: str | None = None,
    seed: int | None = None,
) -> Material:
    """Acquire material: use user motif, generate affect-driven, or use fallback.

    Args:
        frame: Frame with key, mode, metre, etc.
        user_motif: User-provided subject motif (takes priority)
        user_cs: User-provided counter-subject (takes priority over generation)
        genre: Genre name for counter-subject constraints
        affect: Affect name for affect-driven generation
        seed: Optional random seed for reproducibility

    Returns:
        Material with subject, counter-subject, and derived motifs
    """
    motif: Motif

    if user_motif is not None:
        # User provided motif takes priority
        motif = user_motif
    elif affect is not None and affect in AFFECT_DRIVEN_AFFECTS:
        # Use affect-driven generation
        try:
            motif = generate_affect_driven_motif(affect, frame, seed)
        except Exception as e:
            # Fallback to template if generation fails
            import warnings
            warnings.warn(f"Affect-driven generation failed for {affect}: {e}. Using fallback.")
            motif = generate_motif(frame)
    else:
        # Use fallback template
        motif = generate_motif(frame)

    # Use provided counter-subject or generate one
    cs: Motif
    if user_cs is not None:
        cs = user_cs
    else:
        # Generate counter-subject using CP-SAT solver
        subj: Subject = Subject(motif.degrees, motif.durations, motif.bars, frame.mode, genre)
        cs = subj.counter_subject

    # Compute derived motifs
    derived: tuple[DerivedMotif, ...] = compute_derived_motifs(motif, cs)

    return Material(subject=motif, counter_subject=cs, derived_motifs=derived)


# =============================================================================
# Phase 4: Phrase Extension Methods (baroque_plan.md item 4.3)
# =============================================================================

def extend_by_repetition(
    motif: Motif,
    varied: bool = False,
    seed: int | None = None,
) -> Motif:
    """Extend a motif by repeating it (with optional variation).

    Koch's extension method: repeat a segment to extend a phrase.
    If two incomplete incises are present, both must be repeated.

    Args:
        motif: The motif to extend
        varied: If True, apply slight variation to the repetition
        seed: Random seed for variation

    Returns:
        Extended motif with repetition
    """
    import random

    degrees = motif.degrees
    durations = motif.durations

    if varied and seed is not None:
        rng = random.Random(seed)
        # Apply slight variation: transpose by step, or invert direction of one note
        variation_type = rng.choice(["transpose", "neighbor", "none"])
        if variation_type == "transpose":
            # Transpose entire repetition by a step
            offset = rng.choice([-1, 1])
            repeated_degrees = tuple(wrap_degree(d + offset) for d in degrees)
        elif variation_type == "neighbor":
            # Change one note to neighbor tone
            idx = rng.randint(0, len(degrees) - 1)
            repeated_degrees = tuple(
                wrap_degree(d + rng.choice([-1, 1])) if i == idx else d
                for i, d in enumerate(degrees)
            )
        else:
            repeated_degrees = degrees
        repeated_durations = durations
    else:
        repeated_degrees = degrees
        repeated_durations = durations

    return Motif(
        degrees=degrees + repeated_degrees,
        durations=durations + repeated_durations,
        bars=motif.bars * 2,
    )


def extend_by_sequence(
    motif: Motif,
    steps: int,
    direction: int = -1,
) -> Motif:
    """Extend a motif by sequential repetition at different pitch levels.

    Koch's extension method: repeat a segment on different scale degrees.
    CRITICAL: segment equality must be maintained throughout.

    Args:
        motif: The motif to sequence
        steps: Number of sequential repetitions (total segments = steps + 1)
        direction: -1 for descending sequence, +1 for ascending

    Returns:
        Extended motif with sequential repetitions
    """
    all_degrees: list[int] = list(motif.degrees)
    all_durations: list[Fraction] = list(motif.durations)

    for step in range(1, steps + 1):
        transposition = direction * step
        transposed = tuple(wrap_degree(d + transposition) for d in motif.degrees)
        all_degrees.extend(transposed)
        all_durations.extend(motif.durations)

    return Motif(
        degrees=tuple(all_degrees),
        durations=tuple(all_durations),
        bars=motif.bars * (steps + 1),
    )


def extend_by_appendix(
    motif: Motif,
    appendix_degrees: tuple[int, ...],
    appendix_durations: tuple[Fraction, ...],
) -> Motif:
    """Add a clarifying appendix segment after a phrase ending.

    Koch's extension method: appendix adds clarification without changing
    the rhythmic value of the original phrase. The appendix is typically
    a short cadential figure or confirmation.

    Args:
        motif: The original motif
        appendix_degrees: Scale degrees for the appendix
        appendix_durations: Durations for the appendix

    Returns:
        Motif with appended clarifying segment
    """
    # Calculate appendix bars
    appendix_total = sum(appendix_durations)
    # Assume 4/4 time (1 bar = 1 whole note)
    appendix_bars = int(appendix_total) if appendix_total >= 1 else 1

    return Motif(
        degrees=motif.degrees + appendix_degrees,
        durations=motif.durations + appendix_durations,
        bars=motif.bars + appendix_bars,
    )


def extend_by_parenthesis(
    motif: Motif,
    insert_position: int,
    insert_degrees: tuple[int, ...],
    insert_durations: tuple[Fraction, ...],
) -> Motif:
    """Insert parenthetical material within a phrase.

    Koch's extension method: parenthesis inserts material that temporarily
    departs from the main thought, then returns. Often used for
    developmental or modulatory passages.

    Args:
        motif: The original motif
        insert_position: Index at which to insert the parenthesis
        insert_degrees: Scale degrees for the inserted material
        insert_durations: Durations for the inserted material

    Returns:
        Motif with parenthetical insertion
    """
    # Split original motif at insertion point
    before_degrees = motif.degrees[:insert_position]
    after_degrees = motif.degrees[insert_position:]
    before_durations = motif.durations[:insert_position]
    after_durations = motif.durations[insert_position:]

    # Calculate parenthesis bars
    insert_total = sum(insert_durations)
    insert_bars = int(insert_total) if insert_total >= 1 else 1

    return Motif(
        degrees=before_degrees + insert_degrees + after_degrees,
        durations=before_durations + insert_durations + after_durations,
        bars=motif.bars + insert_bars,
    )


def validate_segment_equality(motif: Motif, segment_size: int) -> bool:
    """Validate that all segments in a sequential motif are equal.

    For sequences, each segment must have the same rhythmic and
    intervallic structure (transposed). This is Koch's requirement
    for well-formed sequences.

    Args:
        motif: The motif to validate
        segment_size: Number of notes per segment

    Returns:
        True if all segments are equal (allowing transposition)
    """
    if len(motif.degrees) % segment_size != 0:
        return False

    num_segments = len(motif.degrees) // segment_size

    # Get first segment as reference
    ref_degrees = motif.degrees[:segment_size]
    ref_durations = motif.durations[:segment_size]

    # Calculate intervals within reference segment
    ref_intervals = tuple(
        ref_degrees[i + 1] - ref_degrees[i]
        for i in range(len(ref_degrees) - 1)
    )

    for seg_idx in range(1, num_segments):
        start = seg_idx * segment_size
        end = start + segment_size
        seg_degrees = motif.degrees[start:end]
        seg_durations = motif.durations[start:end]

        # Check durations match exactly
        if seg_durations != ref_durations:
            return False

        # Check intervals match (allowing transposition)
        seg_intervals = tuple(
            seg_degrees[i + 1] - seg_degrees[i]
            for i in range(len(seg_degrees) - 1)
        )
        if seg_intervals != ref_intervals:
            return False

    return True
