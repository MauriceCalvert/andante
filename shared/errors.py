"""Exception hierarchy for Andante.

All domain exceptions derive from AndanteError.
Validation errors derive from ValidationError.
"""


class AndanteError(Exception):
    """Base for all Andante errors."""


class ValidationError(AndanteError):
    """Input validation failed."""


class InvalidDurationError(ValidationError):
    """Duration is invalid or out of range."""


class InvalidPitchError(ValidationError):
    """Pitch is out of range."""


class MissingContextError(ValidationError):
    """Required context not found in tree."""


class InvalidRomanNumeralError(ValidationError):
    """Unknown Roman numeral chord symbol."""
