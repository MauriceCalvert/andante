"""Pedal point generation - sustained bass with melodic activity above."""
from fractions import Fraction

from shared.pitch import FloatingNote, Pitch
from shared.timed_material import TimedMaterial

# Pedal type to scale degree mapping
PEDAL_DEGREES: dict[str, int] = {
    "tonic": 1,
    "dominant": 5,
}


def generate_pedal_bass(
    pedal_type: str,
    budget: Fraction,
    pulse: Fraction = Fraction(1, 2),
) -> TimedMaterial:
    """Generate sustained bass pedal point.

    Args:
        pedal_type: "tonic" or "dominant"
        budget: Total duration to fill
        pulse: Duration of each repeated bass note (default half note)

    Returns:
        TimedMaterial with repeated pedal degree
    """
    assert pedal_type in PEDAL_DEGREES, f"Unknown pedal type: {pedal_type}"
    degree: int = PEDAL_DEGREES[pedal_type]
    pitches: list[Pitch] = []
    durations: list[Fraction] = []
    remaining: Fraction = budget
    while remaining > Fraction(0):
        use_dur: Fraction = min(pulse, remaining)
        pitches.append(FloatingNote(degree))
        durations.append(use_dur)
        remaining -= use_dur
    return TimedMaterial(tuple(pitches), tuple(durations), budget)


def generate_inverted_pedal(
    pedal_degree: int,
    bass_material: TimedMaterial,
    budget: Fraction,
) -> tuple[TimedMaterial, TimedMaterial]:
    """Generate inverted pedal (soprano holds, bass moves).

    Args:
        pedal_degree: Scale degree for soprano pedal (1 or 5)
        bass_material: Pre-generated bass melodic material
        budget: Total duration

    Returns:
        Tuple of (soprano_pedal, bass_melodic)
    """
    pulse: Fraction = Fraction(1, 2)
    pitches: list[Pitch] = []
    durations: list[Fraction] = []
    remaining: Fraction = budget
    while remaining > Fraction(0):
        use_dur: Fraction = min(pulse, remaining)
        pitches.append(FloatingNote(pedal_degree))
        durations.append(use_dur)
        remaining -= use_dur
    soprano: TimedMaterial = TimedMaterial(tuple(pitches), tuple(durations), budget)
    return soprano, bass_material


def is_pedal_treatment(treatment_name: str) -> bool:
    """Check if treatment uses pedal bass."""
    return treatment_name.startswith("pedal_")


def get_pedal_type(treatment_name: str) -> str | None:
    """Extract pedal type from treatment name."""
    if treatment_name == "pedal_tonic":
        return "tonic"
    elif treatment_name == "pedal_dominant":
        return "dominant"
    return None
