"""Handler-based dispatch for tree elaboration."""
from builder.handlers.core import HANDLERS, elaborate, get_handler, include, register

# Import handler modules to register handlers
from builder.handlers import material_handler, structure

__all__ = [
    "HANDLERS",
    "elaborate",
    "get_handler",
    "include",
    "register",
]
