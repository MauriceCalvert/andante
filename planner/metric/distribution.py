"""Bar and beat distribution utilities."""


def bar_beat_to_float(bar_beat: str) -> float:
    """Convert bar.beat string to float for sorting."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    return bar + (beat - 1) / 4.0


def distribute_arrivals(
    stages: int,
    start_bar: int,
    end_bar: int,
    metre: str,
) -> list[str]:
    """Distribute arrival beats across bars."""
    arrivals: list[str] = []
    beats_per_bar: int = get_beats_per_bar(metre)
    strong_beats: list[int] = get_strong_beats(metre)
    total_strong_beats: int = (end_bar - start_bar + 1) * len(strong_beats)
    if stages <= total_strong_beats:
        beat_idx: int = 0
        for _ in range(stages):
            bar: int = start_bar + beat_idx // len(strong_beats)
            beat: int = strong_beats[beat_idx % len(strong_beats)]
            arrivals.append(f"{bar}.{beat}")
            beat_idx += 1
    else:
        for stage in range(stages):
            bar: int = start_bar + stage // beats_per_bar
            beat: int = (stage % beats_per_bar) + 1
            arrivals.append(f"{bar}.{beat}")
    return arrivals


def get_beats_per_bar(metre: str) -> int:
    """Extract beats per bar from metre string."""
    num_str: str = metre.split("/")[0]
    return int(num_str)


def get_final_strong_beat(metre: str) -> int:
    """Get the final strong beat for given metre."""
    if metre == "4/4":
        return 3
    if metre == "3/4":
        return 3
    return 1


def get_strong_beats(metre: str) -> list[int]:
    """Get strong beats for given metre."""
    if metre == "4/4":
        return [1, 3]
    if metre == "3/4":
        return [1]
    return [1]
