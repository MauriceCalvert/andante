"""Suspension system for baroque voice-leading.

Phase 3.3 implementation (baroque_plan.md):
- Suspension types: 4-3, 7-6, 9-8, 2-3
- Generation and validation
- Dual mode: explicit in YAML or auto-generated based on context
"""
from dataclasses import dataclass
from fractions import Fraction

from shared.pitch import FloatingNote, Pitch, wrap_degree


@dataclass(frozen=True)
class SuspensionType:
    """Definition of a suspension type."""
    name: str
    suspended_interval: int  # Interval above bass at dissonance
    resolution_interval: int  # Interval above bass at resolution
    preparation_intervals: tuple[int, ...]  # Valid preparation intervals
    resolution_direction: str  # "down" or "up" (bass motion for 2-3)
    accompanying_intervals: tuple[int, ...]  # Required accompanying intervals


# Standard suspension types
SUSPENSION_TYPES: dict[str, SuspensionType] = {
    "4-3": SuspensionType(
        name="4-3",
        suspended_interval=4,  # 4th above bass
        resolution_interval=3,  # Resolves to 3rd
        preparation_intervals=(8, 3, 5, 6),  # Octave, 3rd, 5th, 6th
        resolution_direction="down",  # Soprano descends
        accompanying_intervals=(5,),  # 5th should be present
    ),
    "7-6": SuspensionType(
        name="7-6",
        suspended_interval=7,  # 7th above bass
        resolution_interval=6,  # Resolves to 6th
        preparation_intervals=(8, 3, 5, 6),
        resolution_direction="down",
        accompanying_intervals=(3,),  # 3rd should be present
    ),
    "9-8": SuspensionType(
        name="9-8",
        suspended_interval=9,  # 9th above bass (octave + step)
        resolution_interval=8,  # Resolves to octave
        preparation_intervals=(3, 5),  # More limited preparations
        resolution_direction="down",
        accompanying_intervals=(3, 5),  # 3rd and 5th
    ),
    "2-3": SuspensionType(
        name="2-3",
        suspended_interval=2,  # 2nd above bass
        resolution_interval=3,  # Resolves to 3rd
        preparation_intervals=(3, 5, 6, 8),  # Any consonance
        resolution_direction="bass_up",  # Bass moves up, not soprano
        accompanying_intervals=(5, 6),
    ),
}

# Affects that favor suspensions
SUSPENSION_FAVORING_AFFECTS: frozenset[str] = frozenset({
    "Sehnsucht",  # Longing - suspensions create yearning
    "Klage",      # Lament - dissonance expresses sorrow
    "Dolore",     # Pain - suspended dissonance
})


@dataclass(frozen=True)
class Suspension:
    """A concrete suspension instance."""
    type: str  # "4-3", "7-6", etc.
    offset: Fraction  # When the suspension occurs
    preparation_pitch: int  # MIDI pitch of preparation
    suspended_pitch: int  # MIDI pitch of suspension (same as preparation)
    resolution_pitch: int  # MIDI pitch of resolution
    bass_pitch: int  # MIDI pitch of bass during suspension


@dataclass(frozen=True)
class SuspensionViolation:
    """Violation of suspension rules."""
    type: str
    offset: Fraction
    message: str


def generate_suspension(
    suspension_type: str,
    bass_degree: int,
    preparation_degree: int,
    key_offset: int = 0,
) -> tuple[int, int, int]:
    """Generate degrees for a suspension.

    Args:
        suspension_type: One of "4-3", "7-6", "9-8", "2-3"
        bass_degree: Scale degree of bass note (1-7)
        preparation_degree: Scale degree of preparation note
        key_offset: Offset for transposition

    Returns:
        Tuple of (preparation_degree, suspended_degree, resolution_degree)
    """
    susp_def = SUSPENSION_TYPES[suspension_type]

    # Suspended pitch is same as preparation (held over)
    suspended_degree = preparation_degree

    # Resolution pitch depends on suspension type
    if susp_def.resolution_direction == "down":
        # Soprano descends by step
        resolution_degree = wrap_degree(suspended_degree - 1)
    elif susp_def.resolution_direction == "bass_up":
        # 2-3 suspension: bass moves up, soprano stays
        resolution_degree = suspended_degree
    else:
        resolution_degree = wrap_degree(suspended_degree - 1)

    return (
        wrap_degree(preparation_degree + key_offset),
        wrap_degree(suspended_degree + key_offset),
        wrap_degree(resolution_degree + key_offset),
    )


def validate_suspension(
    preparation_pitch: int,
    suspended_pitch: int,
    resolution_pitch: int,
    bass_pitch: int,
    suspension_type: str,
) -> list[SuspensionViolation]:
    """Validate that a suspension follows the rules.

    Args:
        preparation_pitch: MIDI pitch of preparation
        suspended_pitch: MIDI pitch during suspension
        resolution_pitch: MIDI pitch at resolution
        bass_pitch: MIDI pitch of bass
        suspension_type: Type of suspension

    Returns:
        List of violations (empty if valid)
    """
    violations: list[SuspensionViolation] = []
    susp_def = SUSPENSION_TYPES[suspension_type]

    # Rule 1: Preparation must equal suspension (tied over)
    if preparation_pitch != suspended_pitch:
        violations.append(SuspensionViolation(
            type="preparation_not_tied",
            offset=Fraction(0),
            message=f"Preparation ({preparation_pitch}) must equal suspension ({suspended_pitch})",
        ))

    # Rule 2: Suspension interval must match type
    suspended_interval = (suspended_pitch - bass_pitch) % 12
    expected_interval = susp_def.suspended_interval
    # Convert scale degree interval to semitones (approximate)
    expected_semitones = {4: 5, 7: 10, 9: 14, 2: 2}  # 4th=5, 7th=10/11, 9th=14, 2nd=2
    if suspension_type in expected_semitones:
        # Allow some flexibility for minor/major variants
        if abs(suspended_interval - expected_semitones[expected_interval]) > 1:
            violations.append(SuspensionViolation(
                type="wrong_suspension_interval",
                offset=Fraction(0),
                message=f"Suspension interval {suspended_interval} doesn't match {suspension_type}",
            ))

    # Rule 3: Resolution must be by step
    if susp_def.resolution_direction == "down":
        motion = suspended_pitch - resolution_pitch
        if motion < 1 or motion > 2:
            violations.append(SuspensionViolation(
                type="resolution_not_stepwise",
                offset=Fraction(0),
                message=f"Resolution must be down by step, got motion of {motion}",
            ))
    elif susp_def.resolution_direction == "bass_up":
        # For 2-3, soprano stays, bass moves up
        if resolution_pitch != suspended_pitch:
            violations.append(SuspensionViolation(
                type="resolution_not_held",
                offset=Fraction(0),
                message="2-3 suspension: soprano should hold while bass moves",
            ))

    return violations


def should_auto_generate_suspension(
    is_cadence_approach: bool,
    energy: str,
    affect: str | None,
    phrase_index: int,
) -> bool:
    """Determine if a suspension should be auto-generated.

    Suspensions are appropriate for:
    - Cadential approaches (especially authentic cadences)
    - High-tension phrases
    - Affects that favor dissonance (Sehnsucht, Klage)

    Args:
        is_cadence_approach: Whether this is approaching a cadence
        energy: Energy level ("low", "medium", "high")
        affect: Current affect or None
        phrase_index: Index of the phrase

    Returns:
        True if a suspension should be generated
    """
    # Cadential 4-3 suspension is very common
    if is_cadence_approach:
        return True

    # High-tension phrases benefit from suspensions
    if energy == "high":
        return True

    # Certain affects favor suspensions
    if affect in SUSPENSION_FAVORING_AFFECTS:
        # Don't suspend every phrase, use phrase_index for variety
        return phrase_index % 2 == 0

    return False


def select_suspension_type(
    is_cadence: bool,
    bass_degree: int,
    prev_soprano_degree: int | None,
) -> str:
    """Select appropriate suspension type for context.

    Args:
        is_cadence: Whether this is a cadential context
        bass_degree: Current bass scale degree
        prev_soprano_degree: Previous soprano degree (for preparation check)

    Returns:
        Suspension type string
    """
    # 4-3 is the most common cadential suspension
    if is_cadence and bass_degree == 5:  # Dominant bass
        return "4-3"

    # 7-6 works well over stepwise descending bass
    if bass_degree in (6, 3):  # Common 7-6 chain positions
        return "7-6"

    # 9-8 for climactic moments
    if bass_degree == 1:  # Over tonic
        return "9-8"

    # Default to 4-3 as most versatile
    return "4-3"


def apply_suspension(
    soprano_degrees: list[int],
    soprano_durations: list[Fraction],
    bass_degree: int,
    suspension_position: int,
    suspension_type: str,
) -> tuple[list[int], list[Fraction]]:
    """Apply a suspension to a soprano line.

    Modifies the soprano to include preparation-suspension-resolution.

    Args:
        soprano_degrees: Original soprano degrees
        soprano_durations: Original soprano durations
        bass_degree: Bass degree at suspension point
        suspension_position: Index in soprano where suspension occurs
        suspension_type: Type of suspension to apply

    Returns:
        Tuple of (modified degrees, modified durations)
    """
    if suspension_position >= len(soprano_degrees):
        return soprano_degrees, soprano_durations

    susp_def = SUSPENSION_TYPES[suspension_type]

    # Get the note that will become the resolution
    resolution_degree = soprano_degrees[suspension_position]

    # Suspended note is one step above resolution (for down-resolving suspensions)
    if susp_def.resolution_direction == "down":
        suspended_degree = wrap_degree(resolution_degree + 1)
    else:
        suspended_degree = resolution_degree

    # Insert the suspension (replaces the original note with suspension pattern)
    new_degrees = list(soprano_degrees)
    new_durations = list(soprano_durations)

    # Split the original duration for suspension-resolution
    orig_dur = new_durations[suspension_position]
    half_dur = orig_dur / 2

    # Replace single note with suspension + resolution
    new_degrees[suspension_position] = suspended_degree
    new_durations[suspension_position] = half_dur

    # Insert resolution
    new_degrees.insert(suspension_position + 1, resolution_degree)
    new_durations.insert(suspension_position + 1, half_dur)

    return new_degrees, new_durations
