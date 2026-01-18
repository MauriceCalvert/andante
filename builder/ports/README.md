# ports/

Interface definitions using Python Protocols.

Ports define contracts that adapters implement. Domain code can depend on these
protocols without knowing the concrete implementations.

## Modules

| Module | Purpose |
|--------|---------|
| interfaces.py | ContextReader, NoteWriter, NoteExporter protocols |

## Usage

```python
from builder.ports.interfaces import ContextReader

def process(reader: ContextReader) -> None:
    context = reader.get_frame_context()
    # Works with any implementation
```
