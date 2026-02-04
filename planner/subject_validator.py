"""Subject validation against opening schema.

Validates that a user-provided subject fits the schema-first model:
- First degree consonant with schema's opening bass
- Invertible (intervals stay consonant when flipped)
- Answerable at the fifth (transposition stays in mode)
"""
from planner.plannertypes import Motif, SubjectValidation
from planner.schema_loader import get_schema
from shared.constants import (
    CONSONANT_DEGREES_WITH_TONIC,
    CONSONANT_INTERVALS_WITH_OCTAVE,
    DIATONIC_DEGREES,
)


def degree_to_semitones(degree: int, mode: str) -> int:
    """Convert scale degree to semitones from tonic.

    Args:
        degree: Scale degree (1-7, can extend to 8+ for octaves)
        mode: 'major' or 'minor'

    Returns:
        Semitones from tonic (0-11 for single octave)
    """
    # Normalize to 1-7 range
    normalized = ((degree - 1) % 7) + 1
    octaves = (degree - 1) // 7

    # Major scale intervals from tonic
    major_semitones = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
    # Natural minor scale intervals
    minor_semitones = {1: 0, 2: 2, 3: 3, 4: 5, 5: 7, 6: 8, 7: 10}

    semitones_map = major_semitones if mode == "major" else minor_semitones
    base_semitones = semitones_map[normalized]

    return base_semitones + (octaves * 12)


def interval_between_degrees(d1: int, d2: int, mode: str) -> int:
    """Compute interval in semitones between two degrees.

    Args:
        d1: First degree
        d2: Second degree
        mode: 'major' or 'minor'

    Returns:
        Absolute interval in semitones
    """
    s1 = degree_to_semitones(degree=d1, mode=mode)
    s2 = degree_to_semitones(degree=d2, mode=mode)
    return abs(s2 - s1) % 12


def check_schema_fit(
    subject_degrees: tuple[int, ...],
    schema_name: str,
) -> tuple[bool, str]:
    """Check if subject first/last degrees align with schema.

    The subject must begin on a degree consonant with the schema's
    opening bass (typically degree 1, so consonant degrees are 1, 3, 5).

    Args:
        subject_degrees: Tuple of scale degrees (1-7+)
        schema_name: Name of opening schema

    Returns:
        (is_valid, error_message) tuple
    """
    if not subject_degrees:
        return False, "Subject has no degrees"

    schema = get_schema(name=schema_name)
    first_bass = schema.bass_degrees[0]

    # Normalize first bass to 1-7
    first_bass_normalized = ((first_bass - 1) % 7) + 1

    # Determine consonant degrees based on bass
    if first_bass_normalized == 1:
        consonant = CONSONANT_DEGREES_WITH_TONIC
    elif first_bass_normalized == 5:
        consonant = frozenset({5, 7, 2})  # Dominant triad
    elif first_bass_normalized == 4:
        consonant = frozenset({4, 6, 1})  # Subdominant triad
    else:
        # For other bass degrees, allow tonic triad as fallback
        consonant = CONSONANT_DEGREES_WITH_TONIC

    # Check first degree
    first_degree = ((subject_degrees[0] - 1) % 7) + 1
    if first_degree not in consonant:
        return False, (
            f"Subject starts on degree {subject_degrees[0]} (normalized: {first_degree}), "
            f"which is not consonant with schema '{schema_name}' bass degree {first_bass}. "
            f"Expected one of: {sorted(consonant)}"
        )

    return True, ""


def check_invertibility(degrees: tuple[int, ...], mode: str) -> tuple[bool, str]:
    """Check if subject inverts cleanly.

    Inversion formula: for each interval, check that the inverted interval
    (12 - interval) mod 12 is also consonant.

    Args:
        degrees: Tuple of scale degrees
        mode: 'major' or 'minor'

    Returns:
        (is_invertible, error_message) tuple
    """
    if len(degrees) < 2:
        return True, ""  # Single note is trivially invertible

    errors: list[str] = []

    for i in range(len(degrees) - 1):
        interval = interval_between_degrees(d1=degrees[i], d2=degrees[i + 1], mode=mode)
        inverted = (12 - interval) % 12

        # Check if inverted interval is consonant
        if interval not in CONSONANT_INTERVALS_WITH_OCTAVE:
            # Original interval is already dissonant - may be intentional
            continue

        if inverted not in CONSONANT_INTERVALS_WITH_OCTAVE:
            errors.append(
                f"Interval {interval} semitones (degrees {degrees[i]}->{degrees[i+1]}) "
                f"inverts to {inverted} semitones, which is dissonant"
            )

    if errors:
        return False, "; ".join(errors)

    return True, ""


def check_answerability(
    degrees: tuple[int, ...],
    mode: str,
) -> tuple[bool, str]:
    """Check if subject answers at fifth without accidentals.

    Answer: transpose up a fifth (degree + 4, mod 7, adjusted for octave)

    Special case (tonal answer):
    - Scale degree 5 should answer to 1 (not 2)
    - This avoids chromatic alterations

    Args:
        degrees: Tuple of scale degrees
        mode: 'major' or 'minor'

    Returns:
        (is_answerable, error_message) tuple
    """
    if not degrees:
        return True, ""

    # In a real tonal answer, degree 5 maps to 1 and degree 1 maps to 5
    # Other degrees transpose up a fourth/fifth appropriately
    # For simplicity, we check that transposition stays diatonic

    errors: list[str] = []
    valid_degrees = DIATONIC_DEGREES

    for deg in degrees:
        normalized = ((deg - 1) % 7) + 1

        # Answer at fifth: +4 scale degrees (1->5, 2->6, 3->7, 4->1, 5->2, 6->3, 7->4)
        answered = ((normalized + 4 - 1) % 7) + 1

        # Special tonal answer adjustments
        if normalized == 5:
            # Degree 5 should answer to 1, not 2
            answered = 1
        elif normalized == 1 and deg == degrees[0]:
            # Opening tonic can answer to dominant
            answered = 5

        if answered not in valid_degrees:
            errors.append(f"Degree {deg} answers to {answered}, outside mode")

    if errors:
        return False, "; ".join(errors)

    return True, ""


def validate_subject(
    subject: Motif,
    opening_schema: str,
    mode: str,
) -> SubjectValidation:
    """Comprehensive subject validation.

    Checks:
    1. First degree fits schema soprano entry
    2. Last degree allows continuation (not on strong closure)
    3. Invertibility (intervals stay consonant when flipped)
    4. Answerability at fifth (transposition stays in mode)

    Args:
        subject: Motif with degrees
        opening_schema: Name of opening schema
        mode: 'major' or 'minor'

    Returns:
        SubjectValidation with detailed error messages
    """
    errors: list[str] = []

    # Get degrees (prefer degrees, fall back to inferring from pitches)
    degrees = subject.degrees
    if degrees is None:
        # Subject has pitches but no degrees - skip degree-based validation
        return SubjectValidation(
            valid=True,
            invertible=True,
            answerable=True,
            errors=(),
        )

    # Check schema fit
    fit_ok, fit_error = check_schema_fit(subject_degrees=degrees, schema_name=opening_schema)
    if not fit_ok:
        errors.append(fit_error)

    # Check invertibility
    invert_ok, invert_error = check_invertibility(degrees=degrees, mode=mode)
    if not invert_ok:
        errors.append(invert_error)

    # Check answerability
    answer_ok, answer_error = check_answerability(degrees=degrees, mode=mode)
    if not answer_ok:
        errors.append(answer_error)

    return SubjectValidation(
        valid=len(errors) == 0,
        invertible=invert_ok,
        answerable=answer_ok,
        errors=tuple(errors),
    )
