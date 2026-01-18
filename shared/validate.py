"""Validation functions — raise typed exceptions.

Category B orchestrators call these before invoking Category A functions.
Category A functions assume valid input; they never call these.
"""
from fractions import Fraction

from shared.errors import (
    InvalidDurationError,
    InvalidPitchError,
    InvalidRomanNumeralError,
)


def require_positive_duration(duration: Fraction, name: str = "duration") -> None:
    """Raise InvalidDurationError if duration is not positive."""
    if duration <= 0:
        raise InvalidDurationError(f"{name} must be positive, got {duration}")


def require_valid_midi(pitch: int, name: str = "pitch") -> None:
    """Raise InvalidPitchError if pitch is not 0-127."""
    if not 0 <= pitch <= 127:
        raise InvalidPitchError(f"{name} must be 0-127, got {pitch}")


def require_valid_diatonic(pitch: int, name: str = "diatonic") -> None:
    """Raise InvalidPitchError if diatonic pitch is negative."""
    if pitch < 0:
        raise InvalidPitchError(f"{name} must be non-negative, got {pitch}")


def require_known_roman(roman: str, valid: set[str], name: str = "roman") -> None:
    """Raise InvalidRomanNumeralError if roman not in valid set."""
    if roman not in valid:
        raise InvalidRomanNumeralError(
            f"Unknown {name}: '{roman}'. Valid: {sorted(valid)}"
        )
