"""Port interfaces for builder module.
Protocols define the contracts that adapters must implement.
Domain code can depend on these protocols without knowing implementations.
"""
from typing import Any, Protocol
from builder.types import BarContext, CollectedNote, FrameContext, Notes, Subject

class ContextReader(Protocol):
    """Read musical context from infrastructure."""

    def get_frame_context(self) -> FrameContext:
        """Extract frame context."""
        ...

    def get_bar_context(self, identifier: Any) -> BarContext:
        """Extract bar context for a specific location."""
        ...

    def get_subject(self) -> Subject | None:
        """Extract subject material if present."""
        ...

class NoteWriter(Protocol):
    """Write notes back to infrastructure."""

    def write_notes(self, notes: Notes, target: Any) -> Any:
        """Write notes to target location."""
        ...

class NoteExporter(Protocol):
    """Export notes to file formats."""

    def export_midi(
        self,
        notes: list[CollectedNote],
        path: str,
        key_offset: int,
        tempo: int,
        time_signature: tuple[int, int],
    ) -> bool:
        """Export to MIDI file."""
        ...

    def export_note(
        self,
        notes: list[CollectedNote],
        path: str,
        key_offset: int,
        time_signature: tuple[int, int],
    ) -> bool:
        """Export to .note CSV file."""
        ...
