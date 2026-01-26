"""Direction-aware melodic minor pitch mapper.

Handles raised 6th and 7th in ascending minor, natural forms in descending.
Enforces augmented 2nd prohibition and tritone checks.
"""
from shared.key import Key


class MelodicMinorMapper:
    """Maps scale degrees to pitches with direction-aware minor inflections.

    In minor mode:
    - Ascending to tonic (8): raise 6 and 7
    - Descending to dominant (5): natural 6 and 7
    - Static/turning: natural 6 and 7 (unless neighbor to tonic)
    """

    def __init__(self, key: Key) -> None:
        """Initialize mapper with key.

        Args:
            key: Key object (may be major or minor)
        """
        self.key = key
        self.is_minor = key.mode == "minor"

    def degree_to_pitch(
        self,
        degree: int,
        octave: int,
        direction: str,
        context: str = "melodic",
    ) -> int:
        """Convert scale degree to MIDI pitch with minor inflections.

        Args:
            degree: Scale degree (1-7)
            octave: Octave number
            direction: Melodic direction ("ascending", "descending", "static")
            context: Harmonic context ("melodic", "cadential", "neighbor_to_tonic")

        Returns:
            MIDI pitch number.
        """
        assert 1 <= degree <= 7, f"Degree must be 1-7, got {degree}"

        if not self.is_minor:
            # Major mode: no inflections needed
            return self.key.degree_to_midi(degree, octave)

        # Minor mode: check for raised 6 and 7
        raised_6 = self._should_raise_6(degree, direction, context)
        raised_7 = self._should_raise_7(degree, direction, context)

        # Get base pitch from natural minor
        base_pitch = self.key.degree_to_midi(degree, octave)

        # Apply raising if needed
        if degree == 6 and raised_6:
            base_pitch += 1  # Raise by semitone
        elif degree == 7 and raised_7:
            base_pitch += 1  # Raise by semitone

        return base_pitch

    def _should_raise_6(self, degree: int, direction: str, context: str) -> bool:
        """Determine if degree 6 should be raised.

        Raised when:
        - Ascending to tonic
        - Degree 7 is also raised (to avoid augmented 2nd)
        """
        if degree != 6:
            return False

        if direction == "ascending":
            # Ascending: raise 6 (melodic minor ascending)
            return True
        elif context == "neighbor_to_tonic":
            # Neighbor to tonic: may raise
            return True

        return False

    def _should_raise_7(self, degree: int, direction: str, context: str) -> bool:
        """Determine if degree 7 should be raised.

        Raised when:
        - Ascending to tonic
        - Cadential context (leading tone)
        - Neighbor to tonic
        """
        if degree != 7:
            return False

        if direction == "ascending":
            # Ascending: raise 7 (leading tone)
            return True
        elif context in ("cadential", "neighbor_to_tonic"):
            # Cadential or neighbor: raise for resolution
            return True

        return False

    def check_augmented_2nd(
        self,
        degree_from: int,
        degree_to: int,
        raised_6: bool,
        raised_7: bool,
    ) -> bool:
        """Check if motion creates forbidden augmented 2nd.

        Augmented 2nd occurs between natural 6 and raised 7.

        Args:
            degree_from: Starting degree
            degree_to: Ending degree
            raised_6: Whether degree 6 is raised
            raised_7: Whether degree 7 is raised

        Returns:
            True if augmented 2nd would occur.
        """
        if not self.is_minor:
            return False

        # Augmented 2nd: natural 6 to raised 7
        if degree_from == 6 and degree_to == 7:
            if not raised_6 and raised_7:
                return True

        # Or: raised 7 to natural 6 (descending)
        if degree_from == 7 and degree_to == 6:
            if raised_7 and not raised_6:
                return True

        return False

    def is_tritone(self, degree_from: int, degree_to: int) -> bool:
        """Check if melodic motion creates a tritone.

        Tritone: degree 4 to raised degree 7 (augmented 4th).

        Args:
            degree_from: Starting degree
            degree_to: Ending degree

        Returns:
            True if motion is a tritone.
        """
        if not self.is_minor:
            # In major, 4 to 7 is also a tritone
            if (degree_from == 4 and degree_to == 7) or (degree_from == 7 and degree_to == 4):
                return True
            return False

        # In minor, 4 to raised 7 is a tritone
        # This check assumes 7 would be raised in ascending context
        if (degree_from == 4 and degree_to == 7) or (degree_from == 7 and degree_to == 4):
            return True

        return False

    def validate_motion(
        self,
        degree_from: int,
        degree_to: int,
        direction: str,
        context: str = "melodic",
    ) -> tuple[bool, str | None]:
        """Validate melodic motion between degrees.

        Checks for:
        - Augmented 2nd prohibition
        - Tritone prohibition (unless dominant 7th arpeggio)

        Args:
            degree_from: Starting degree
            degree_to: Ending degree
            direction: Melodic direction
            context: Harmonic context

        Returns:
            Tuple of (is_valid, error_message or None).
        """
        if not self.is_minor:
            # Major mode: check tritone only
            if self.is_tritone(degree_from, degree_to):
                if context != "dominant_arpeggio":
                    return False, f"Tritone motion {degree_from}->{degree_to} forbidden"
            return True, None

        # Minor mode: check both
        raised_6 = self._should_raise_6(6, direction, context)
        raised_7 = self._should_raise_7(7, direction, context)

        if self.check_augmented_2nd(degree_from, degree_to, raised_6, raised_7):
            return False, f"Augmented 2nd between degrees {degree_from} and {degree_to}"

        if self.is_tritone(degree_from, degree_to):
            if context != "dominant_arpeggio":
                return False, f"Tritone motion {degree_from}->{degree_to} forbidden"

        return True, None

    def get_inflected_scale(self, direction: str) -> tuple[int, ...]:
        """Get scale semitones with appropriate inflections.

        Args:
            direction: "ascending" or "descending"

        Returns:
            Tuple of semitone offsets from tonic.
        """
        if not self.is_minor:
            return self.key.scale

        if direction == "ascending":
            # Melodic minor ascending: raise 6 and 7
            # Natural minor: 0, 2, 3, 5, 7, 8, 10
            # Melodic asc:   0, 2, 3, 5, 7, 9, 11
            return (0, 2, 3, 5, 7, 9, 11)
        else:
            # Melodic minor descending: natural minor
            return self.key.scale  # Natural minor: 0, 2, 3, 5, 7, 8, 10


def determine_direction(degrees: tuple[int, ...]) -> str:
    """Determine overall melodic direction from degree sequence.

    Args:
        degrees: Sequence of scale degrees

    Returns:
        "ascending", "descending", or "static"
    """
    if len(degrees) < 2:
        return "static"

    first = degrees[0]
    last = degrees[-1]

    if last > first:
        return "ascending"
    elif last < first:
        return "descending"
    else:
        return "static"


def filter_minor_unsafe_figures(
    figures: list,
    is_minor: bool,
) -> list:
    """Filter figures that are unsafe in minor mode.

    This is a pre-selection filter to avoid figures that would
    create melodic minor problems.

    Args:
        figures: List of Figure objects
        is_minor: Whether key is minor

    Returns:
        Filtered figure list.
    """
    if not is_minor:
        return figures

    return [f for f in figures if f.minor_safe]
