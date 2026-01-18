"""Andante shared types and constants."""
from shared.errors import (
    AndanteError,
    InvalidDurationError,
    InvalidPitchError,
    InvalidRomanNumeralError,
    MissingContextError,
    ValidationError,
)
from shared.key import Key
from shared.pitch import FloatingNote, MidiPitch, Pitch, Rest, is_rest
from shared.types import ExpandedVoices, Frame, Motif, VoiceMaterial
from shared.validate import (
    require_known_roman,
    require_positive_duration,
    require_valid_diatonic,
    require_valid_midi,
)

__all__ = [
    # Errors
    "AndanteError",
    "InvalidDurationError",
    "InvalidPitchError",
    "InvalidRomanNumeralError",
    "MissingContextError",
    "ValidationError",
    # Types
    "ExpandedVoices",
    "FloatingNote",
    "Frame",
    "Key",
    "MidiPitch",
    "Motif",
    "Pitch",
    "Rest",
    "VoiceMaterial",
    # Functions
    "is_rest",
    "require_known_roman",
    "require_positive_duration",
    "require_valid_diatonic",
    "require_valid_midi",
]
