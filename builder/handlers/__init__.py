"""Handler-based dispatch for tree elaboration."""
from builder.handlers.core import HANDLERS, register, get_handler, include, elaborate

# Import handler modules to register handlers
from builder.handlers import structure
from builder.handlers import material

__all__ = [
    'HANDLERS',
    'register',
    'get_handler',
    'include',
    'elaborate',
]
