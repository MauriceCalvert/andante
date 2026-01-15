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
    genre: str = "",
    affect: str | None = None,
    seed: int | None = None,
) -> Material:
    """Acquire material: use user motif, generate affect-driven, or use fallback.

    Args:
        frame: Frame with key, mode, metre, etc.
        user_motif: User-provided motif (takes priority)
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

    # Generate counter-subject using CP-SAT solver
    subj: Subject = Subject(motif.degrees, motif.durations, motif.bars, frame.mode, genre)
    cs: Motif = subj.counter_subject

    # Compute derived motifs
    derived: tuple[DerivedMotif, ...] = compute_derived_motifs(motif, cs)

    return Material(subject=motif, counter_subject=cs, derived_motifs=derived)
