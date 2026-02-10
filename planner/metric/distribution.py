"""Bar and beat distribution utilities."""


def bar_beat_to_float(bar_beat: str) -> float:
    """Convert bar.beat string to float for sorting."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    return bar + (beat - 1) / 4.0
