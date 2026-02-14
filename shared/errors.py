"""Exception hierarchy for Andante.

All domain exceptions derive from AndanteError.
Validation errors derive from ValidationError.

Law: when a composition falls back because the genre YAML or brief made
something impossible, emit a kind sarcastic warning via brief_warning().
The message should be helpful (say what went wrong and what to fix)
with a gentle needle (the human should have known better).
Algorithmic fallbacks (Viterbi soft-only, stepwise fill, etc.) are
normal runtime and do NOT use this function.
"""
import logging

_brief_logger: logging.Logger = logging.getLogger("andante.brief")


def brief_warning(what_failed: str, why: str, suggestion: str) -> None:
    """Log a kind sarcastic warning when a brief/YAML config causes a fallback."""
    _brief_logger.warning(
        "%s — %s. Suggestion: %s",
        what_failed,
        why,
        suggestion,
    )


class AndanteError(Exception):
    """Base for all Andante errors."""


class ValidationError(AndanteError):
    """Input validation failed."""


class InvalidDurationError(ValidationError):
    """Duration is invalid or out of range."""


class InvalidPitchError(ValidationError):
    """Pitch is out of range."""


class InvalidRomanNumeralError(ValidationError):
    """Unknown Roman numeral chord symbol."""


class SolverTimeoutError(AndanteError):
    """CP-SAT solver exceeded time limit."""


class SolverInfeasibleError(AndanteError):
    """No solution satisfies all hard constraints."""
