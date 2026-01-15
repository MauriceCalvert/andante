"""Walking bass generation for continuous bass motion."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import yaml

from shared.pitch import FloatingNote, Pitch, wrap_degree
from shared.timed_material import TimedMaterial

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class WalkingPattern:
    """Walking bass pattern configuration."""
    name: str
    motion: str       # stepwise, chromatic, arpeggiated
    direction: str    # ascending, descending, alternating, toward_target
    notes_per_bar: int


def load_walking_patterns() -> dict[str, WalkingPattern]:
    """Load walking bass pattern definitions from YAML."""
    with open(DATA_DIR / "walking_patterns.yaml", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    result: dict[str, WalkingPattern] = {}
    for name, defn in data.items():
        pattern: WalkingPattern = WalkingPattern(
            name=name,
            motion=defn["motion"],
            direction=defn["direction"],
            notes_per_bar=defn["notes_per_bar"],
        )
        result[name] = pattern
    return result


WALKING_PATTERNS: dict[str, WalkingPattern] = load_walking_patterns()


def generate_walking_bass(
    start_degree: int,
    target_degree: int,
    pattern_name: str,
    bars: int,
    bar_duration: Fraction,
) -> TimedMaterial:
    """Generate walking bass line between harmonic targets.

    Args:
        start_degree: Starting scale degree (1-7)
        target_degree: Target scale degree for final beat
        pattern_name: Name of walking pattern to use
        bars: Number of bars to fill
        bar_duration: Duration of one bar

    Returns:
        TimedMaterial with bass degrees and durations
    """
    assert pattern_name in WALKING_PATTERNS, f"Unknown pattern: {pattern_name}"
    pattern: WalkingPattern = WALKING_PATTERNS[pattern_name]
    total_notes: int = pattern.notes_per_bar * bars
    budget: Fraction = bar_duration * bars
    note_dur: Fraction = budget / total_notes
    pitches: list[Pitch] = []
    if pattern.motion == "stepwise":
        pitches = _generate_stepwise(start_degree, target_degree, total_notes, pattern.direction)
    elif pattern.motion == "chromatic":
        pitches = _generate_chromatic_approach(start_degree, target_degree, total_notes)
    elif pattern.motion == "arpeggiated":
        pitches = _generate_arpeggiated(start_degree, target_degree, total_notes)
    else:
        pitches = _generate_stepwise(start_degree, target_degree, total_notes, "alternating")
    durations: tuple[Fraction, ...] = tuple([note_dur] * total_notes)
    return TimedMaterial(pitches=tuple(pitches), durations=durations, budget=budget)


def _generate_stepwise(
    start: int,
    target: int,
    total_notes: int,
    direction: str,
) -> list[Pitch]:
    """Generate stepwise motion between degrees."""
    pitches: list[Pitch] = []
    current: int = start
    for i in range(total_notes):
        pitches.append(FloatingNote(wrap_degree(current)))
        if i == total_notes - 1:
            break
        remaining: int = total_notes - i - 1
        dist: int = _degree_distance(current, target)
        if direction == "toward_target" or remaining <= abs(dist):
            step: int = 1 if dist > 0 else -1
        elif direction == "ascending":
            step = 1
        elif direction == "descending":
            step = -1
        else:
            step = 1 if i % 2 == 0 else -1
        current = wrap_degree(current + step)
    pitches[-1] = FloatingNote(wrap_degree(target))
    return pitches


def _generate_chromatic_approach(
    start: int,
    target: int,
    total_notes: int,
) -> list[Pitch]:
    """Generate chromatic approach to target in final notes."""
    pitches: list[Pitch] = []
    approach_notes: int = min(3, total_notes - 1)
    diatonic_notes: int = total_notes - approach_notes
    current: int = start
    for i in range(diatonic_notes):
        pitches.append(FloatingNote(wrap_degree(current)))
        if i < diatonic_notes - 1:
            current = wrap_degree(current + 1)
    approach_start: int = wrap_degree(target - approach_notes)
    for i in range(approach_notes):
        pitches.append(FloatingNote(wrap_degree(approach_start + i)))
    pitches[-1] = FloatingNote(wrap_degree(target))
    return pitches


def _generate_arpeggiated(
    start: int,
    target: int,
    total_notes: int,
) -> list[Pitch]:
    """Generate arpeggiated motion using chord tones."""
    chord_degrees: list[int] = [start, wrap_degree(start + 2), wrap_degree(start + 4)]
    pitches: list[Pitch] = []
    for i in range(total_notes - 1):
        deg: int = chord_degrees[i % len(chord_degrees)]
        pitches.append(FloatingNote(deg))
    pitches.append(FloatingNote(wrap_degree(target)))
    return pitches


def _degree_distance(from_deg: int, to_deg: int) -> int:
    """Calculate signed distance between degrees (shortest path)."""
    from_norm: int = wrap_degree(from_deg)
    to_norm: int = wrap_degree(to_deg)
    direct: int = to_norm - from_norm
    if abs(direct) <= 3:
        return direct
    if direct > 0:
        return direct - 7
    return direct + 7
