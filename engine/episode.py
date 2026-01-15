"""Episode handler: apply episode-specific treatment and rhythm overrides."""
from fractions import Fraction
from itertools import cycle
from pathlib import Path

import yaml

from shared.pitch import FloatingNote, Pitch, wrap_degree
from shared.timed_material import TimedMaterial

DATA_DIR = Path(__file__).parent.parent / "data"
EPISODES: dict = yaml.safe_load(open(DATA_DIR / "episodes.yaml", encoding="utf-8"))


def get_episode(name: str) -> dict:
    """Get episode definition by name."""
    assert name in EPISODES, f"Unknown episode: {name}"
    return EPISODES[name]


def resolve_treatment(phrase_treatment: str, episode: str | None) -> str:
    """Resolve treatment: phrase takes priority, episode provides default.

    Only falls back to episode treatment if phrase treatment is generic 'statement'.
    This allows planner to specify augmentation, sequence, etc. that won't be overridden.
    """
    if phrase_treatment != "statement":
        return phrase_treatment
    if episode is None:
        return phrase_treatment
    ep_def: dict = get_episode(episode)
    return ep_def.get("treatment", phrase_treatment)


def resolve_rhythm(phrase_rhythm: str | None, episode: str | None) -> str | None:
    """Resolve rhythm: episode provides default if phrase has none."""
    if phrase_rhythm is not None:
        return phrase_rhythm
    if episode is None:
        return None
    ep_def: dict = get_episode(episode)
    return ep_def.get("rhythm")


def get_energy_profile(episode: str | None) -> str:
    """Get energy profile for episode."""
    if episode is None:
        return "stable"
    ep_def: dict = get_episode(episode)
    return ep_def.get("energy_profile", "stable")


def extract_intervals(pitches: tuple[Pitch, ...]) -> tuple[int, ...]:
    """Extract melodic interval sequence from pitch degrees."""
    intervals: list[int] = []
    for i in range(len(pitches) - 1):
        d1: int = pitches[i].degree if hasattr(pitches[i], 'degree') else 1
        d2: int = pitches[i + 1].degree if hasattr(pitches[i + 1], 'degree') else 1
        intervals.append(d2 - d1)
    return tuple(intervals)


def notes_for_bars(bars: int, rhythm: str) -> int:
    """Calculate note count for given bars and rhythm type.

    Notes per bar based on rhythm pattern durations:
    - running: 16 sixteenths = 16 notes
    - dotted: 4 pairs of (3/16 + 1/16) = 8 notes
    - straight: 4 quarters = 4 notes
    - lombardic: 4 pairs of (1/16 + 3/16) = 8 notes
    """
    notes_per_bar: dict[str, int] = {
        "running": 16,
        "dotted": 8,
        "straight": 4,
        "lombardic": 8,
    }
    return bars * notes_per_bar.get(rhythm, 8)


def get_rhythm_durations(rhythm: str, bars: int) -> tuple[Fraction, ...]:
    """Get duration pattern for rhythm type."""
    rhythm_patterns: dict[str, tuple[Fraction, ...]] = {
        "running": (Fraction(1, 16),),
        "dotted": (Fraction(3, 16), Fraction(1, 16)),
        "straight": (Fraction(1, 4),),
        "lombardic": (Fraction(1, 16), Fraction(3, 16)),
    }
    pattern: tuple[Fraction, ...] = rhythm_patterns.get(rhythm, (Fraction(1, 8),))
    budget: Fraction = Fraction(bars)
    result: list[Fraction] = []
    remaining: Fraction = budget
    idx: int = 0
    while remaining > Fraction(0):
        dur: Fraction = pattern[idx % len(pattern)]
        use_dur: Fraction = min(dur, remaining)
        result.append(use_dur)
        remaining -= use_dur
        idx += 1
    return tuple(result)


def generate_interval_episode(
    intervals: tuple[int, ...],
    start_degree: int,
    rhythm: str,
    bars: int,
    phrase_index: int = 0,
) -> TimedMaterial:
    """Generate scalar passage following subject interval pattern.

    Cycles through intervals, building degrees from start_degree.
    Varies start position and direction based on phrase_index.
    Adds periodic displacement every 12 notes to prevent 16-note duplications.
    """
    note_count: int = notes_for_bars(bars, rhythm)
    start_offset: int = phrase_index % len(intervals) if intervals else 0
    direction: int = 1 if phrase_index % 2 == 0 else -1
    # Use phrase_index to offset the starting degree more aggressively
    seed_offset: int = ((phrase_index * 5) % 7) - 3  # -3 to +3
    degrees: list[int] = [start_degree + (phrase_index % 7) + seed_offset]
    interval_iter = cycle(intervals) if intervals else cycle([1])
    for _ in range(start_offset):
        next(interval_iter)
    # Displacement patterns to break up 16-note sequences
    displacements: tuple[int, ...] = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 2, -1)
    for note_idx in range(note_count - 1):
        interval: int = next(interval_iter) * direction
        # Add periodic displacement to prevent exact 16-note repetitions
        displacement: int = displacements[(note_idx + phrase_index) % len(displacements)]
        next_deg: int = degrees[-1] + interval + displacement
        degrees.append(next_deg)
    pitches: tuple[Pitch, ...] = tuple(FloatingNote(wrap_degree(d)) for d in degrees)
    durations: tuple[Fraction, ...] = get_rhythm_durations(rhythm, bars)
    if len(durations) < len(pitches):
        durations = durations + (durations[-1],) * (len(pitches) - len(durations))
    elif len(durations) > len(pitches):
        durations = durations[:len(pitches)]
    budget: Fraction = Fraction(bars)
    return TimedMaterial(pitches, durations, budget)
