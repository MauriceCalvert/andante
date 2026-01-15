"""Episode generator registry - eliminates if/elif chains for episode types.

Each episode type registers a generator function that produces soprano material.
The expander looks up the generator by episode_type and calls it.
"""
from fractions import Fraction
from typing import Callable

from shared.pitch import Pitch
from engine.engine_types import MotifAST
from shared.timed_material import TimedMaterial


# Type for episode generator functions
EpisodeGenerator = Callable[
    [MotifAST, Fraction, int, int, bool],  # subject, budget, root, phrase_idx, virtuosic
    TimedMaterial | None  # None means use default treatment-based expansion
]

# Registry of episode generators
_GENERATORS: dict[str, EpisodeGenerator] = {}


def register_episode(episode_type: str) -> Callable[[EpisodeGenerator], EpisodeGenerator]:
    """Decorator to register an episode generator."""
    def decorator(func: EpisodeGenerator) -> EpisodeGenerator:
        _GENERATORS[episode_type] = func
        return func
    return decorator


def get_episode_generator(episode_type: str | None) -> EpisodeGenerator | None:
    """Get generator for episode type, or None if not registered."""
    if episode_type is None:
        return None
    return _GENERATORS.get(episode_type)


def generate_episode_soprano(
    episode_type: str | None,
    subject: MotifAST,
    budget: Fraction,
    root: int,
    phrase_index: int,
    virtuosic: bool = False,
) -> TimedMaterial | None:
    """Generate soprano material for episode type, or None to use treatment."""
    generator: EpisodeGenerator | None = get_episode_generator(episode_type)
    if generator is None:
        return None
    return generator(subject, budget, root, phrase_index, virtuosic)


# Register built-in episode generators
@register_episode("cadenza")
def _generate_cadenza(
    subject: MotifAST,
    budget: Fraction,
    root: int,
    phrase_index: int,
    virtuosic: bool,
) -> TimedMaterial | None:
    """Cadenza: virtuosic passage work."""
    from engine.cadenza import generate_cadenza
    patterns: list[str] = ["flourish_a", "flourish_b", "steady", "rubato"]
    pattern: str = patterns[phrase_index % len(patterns)]
    return generate_cadenza(budget, root, pattern)


@register_episode("scalar")
def _generate_scalar(
    subject: MotifAST,
    budget: Fraction,
    root: int,
    phrase_index: int,
    virtuosic: bool,
) -> TimedMaterial | None:
    """Scalar: running passages based on subject intervals."""
    from engine.episode import extract_intervals, generate_interval_episode
    intervals: tuple[int, ...] = extract_intervals(subject.pitches)
    bars: int = int(budget)
    return generate_interval_episode(intervals, root, "running", bars, phrase_index)


@register_episode("arpeggiated")
def _generate_arpeggiated(
    subject: MotifAST,
    budget: Fraction,
    root: int,
    phrase_index: int,
    virtuosic: bool,
) -> TimedMaterial | None:
    """Arpeggiated: passage work from passage library."""
    from engine.passage import generate_passage, get_passage_for_episode
    passage_name: str | None = get_passage_for_episode("arpeggiated", phrase_index, virtuosic)
    if passage_name is None:
        return None
    return generate_passage(passage_name, budget, root, phrase_index)


@register_episode("turbulent")
def _generate_turbulent(
    subject: MotifAST,
    budget: Fraction,
    root: int,
    phrase_index: int,
    virtuosic: bool,
) -> TimedMaterial | None:
    """Turbulent: dramatic passage work."""
    from engine.passage import generate_passage, get_passage_for_episode
    passage_name: str | None = get_passage_for_episode("turbulent", phrase_index, virtuosic)
    if passage_name is None:
        return None
    return generate_passage(passage_name, budget, root, phrase_index)
