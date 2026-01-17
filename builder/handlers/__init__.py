"""Handler-based dispatch for tree elaboration."""
from builder.handlers.core import HANDLERS, register, get_handler, include, elaborate

# Import handler modules to register handlers
from builder.handlers import structure

__all__ = [
    'HANDLERS',
    'register',
    'get_handler',
    'include',
    'elaborate',
]
